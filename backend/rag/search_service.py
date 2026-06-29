import re
from collections import defaultdict
from typing import Dict, Any, List, Optional

from qdrant_client.http import models

from backend.rag.embeddings import EmbeddingModel
from backend.rag.qdrant_store import (
    get_qdrant_client,
    COLLECTION_NAME,
)


SEARCH_STOP_WORDS = {
    "покажи", "перечисли", "назови", "выведи", "найди",
    "расскажи", "объясни", "опиши", "сравни", "составь",
    "приведи", "укажи", "дай", "какие", "какая", "какой",
    "что", "это", "для", "мне", "нужно", "надо",
    "show", "list", "name", "find", "tell", "explain",
    "describe", "compare", "give", "provide", "what",
    "which", "the", "for", "me", "please",
}


def tokenize_for_search(text: str) -> List[str]:
    """Токенизация для лексической части поиска."""
    normalized = (
        (text or "")
        .lower()
        .replace("ё", "е")
    )

    tokens = re.findall(
        r"[а-яa-z0-9]+",
        normalized,
    )

    return [
        token
        for token in tokens
        if (
            len(token) > 2
            and token not in SEARCH_STOP_WORDS
        )
    ]


def build_qdrant_filter(
    search_params: Dict[str, Any],
) -> Optional[models.Filter]:
    """Формирует фильтр Qdrant на основе класса запроса."""
    must_conditions = []

    source_filter = search_params.get(
        "source_filter",
        [],
    )

    if source_filter:
        must_conditions.append(
            models.FieldCondition(
                key="file_name",
                match=models.MatchAny(
                    any=source_filter
                ),
            )
        )

    document_type_filter = search_params.get(
        "document_type_filter",
        [],
    )

    if document_type_filter:
        must_conditions.append(
            models.FieldCondition(
                key="document_type",
                match=models.MatchAny(
                    any=document_type_filter
                ),
            )
        )

    knowledge_category_filter = search_params.get(
        "knowledge_category_filter",
        [],
    )

    if knowledge_category_filter:
        must_conditions.append(
            models.FieldCondition(
                key="knowledge_category",
                match=models.MatchAny(
                    any=knowledge_category_filter
                ),
            )
        )

    is_normative = search_params.get(
        "is_normative"
    )

    if is_normative is not None:
        must_conditions.append(
            models.FieldCondition(
                key="is_normative",
                match=models.MatchValue(
                    value=is_normative
                ),
            )
        )

    if not must_conditions:
        return None

    return models.Filter(
        must=must_conditions
    )


def _tokens_are_morphologically_close(
    query_token: str,
    chunk_token: str,
) -> bool:
    """
    Простая проверка совпадения русских и английских слов
    по начальной части основы.
    """
    if query_token == chunk_token:
        return True

    min_length = min(
        len(query_token),
        len(chunk_token),
    )

    if min_length < 5:
        return False

    stem_length = (
        5
        if min_length >= 7
        else 4
    )

    return (
        query_token[:stem_length]
        == chunk_token[:stem_length]
    )


def calculate_lexical_score(
    query_tokens: List[str],
    chunk_text: str,
) -> float:
    """
    Считает долю предметных токенов запроса,
    найденных во фрагменте.
    """
    unique_query_tokens = list(
        dict.fromkeys(query_tokens)
    )

    if not unique_query_tokens:
        return 0.0

    chunk_tokens = set(
        tokenize_for_search(chunk_text)
    )

    matched_weight = 0.0

    for query_token in unique_query_tokens:
        if query_token in chunk_tokens:
            matched_weight += 1.0
            continue

        if any(
            _tokens_are_morphologically_close(
                query_token,
                chunk_token,
            )
            for chunk_token in chunk_tokens
        ):
            matched_weight += 0.7

    return (
        matched_weight
        / len(unique_query_tokens)
    )


def qdrant_vector_search(
    query_vector: List[float],
    search_params: Dict[str, Any],
):
    """Выполняет векторный поиск по Qdrant."""
    client = get_qdrant_client()

    top_k = search_params.get(
        "top_k",
        5,
    )
    search_multiplier = search_params.get(
        "search_multiplier",
        4,
    )

    search_limit = max(
        top_k * search_multiplier,
        top_k,
    )

    query_filter = build_qdrant_filter(
        search_params
    )

    try:
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=search_limit,
            with_payload=True,
        )

        return response.points

    except AttributeError:
        return client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=search_limit,
            with_payload=True,
        )


def _apply_document_diversity(
    results: List[Dict[str, Any]],
    top_k: int,
    max_chunks_per_document: Optional[int],
) -> List[Dict[str, Any]]:
    if not max_chunks_per_document:
        return results[:top_k]

    selected: List[Dict[str, Any]] = []
    document_counts: Dict[str, int] = defaultdict(int)

    for result in results:
        document_key = (
            result.get("file_name")
            or result.get("document_name")
            or "unknown"
        )

        if (
            document_counts[document_key]
            >= max_chunks_per_document
        ):
            continue

        selected.append(result)
        document_counts[document_key] += 1

        if len(selected) >= top_k:
            break

    if len(selected) < top_k:
        selected_ids = {
            (
                item.get("file_name"),
                item.get("chunk_number"),
                item.get("chunk_id"),
            )
            for item in selected
        }

        for result in results:
            result_id = (
                result.get("file_name"),
                result.get("chunk_number"),
                result.get("chunk_id"),
            )

            if result_id in selected_ids:
                continue

            selected.append(result)
            selected_ids.add(result_id)

            if len(selected) >= top_k:
                break

    return selected


def rerank_search_results(
    points,
    retrieval_query: str,
    search_params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Выполняет векторно-лексическое переранжирование."""
    query_tokens = tokenize_for_search(
        retrieval_query
    )

    min_score = search_params.get(
        "min_score",
        0.55,
    )
    top_k = search_params.get(
        "top_k",
        5,
    )

    results = []

    for point in points:
        payload = point.payload or {}
        chunk_text = payload.get(
            "chunk_text",
            "",
        )

        vector_score = float(
            point.score or 0.0
        )
        lexical_score = calculate_lexical_score(
            query_tokens,
            chunk_text,
        )

        hybrid_score = round(
            0.82 * vector_score
            + 0.18 * lexical_score,
            4,
        )

        if hybrid_score < min_score:
            continue

        results.append(
            {
                "chunk_id": payload.get("chunk_id"),
                "chunk_text": chunk_text,
                "score": hybrid_score,
                "vector_score": round(
                    vector_score,
                    4,
                ),
                "lexical_score": round(
                    lexical_score,
                    4,
                ),
                "document_id": payload.get("document_id"),
                "document_name": payload.get("document_name"),
                "file_name": payload.get("file_name"),
                "document_type": payload.get("document_type"),
                "knowledge_category": payload.get(
                    "knowledge_category"
                ),
                "source_scope": payload.get("source_scope"),
                "source_type": payload.get("source_type"),
                "source_format": payload.get("source_format"),
                "source_path": payload.get("source_path"),
                "metadata_mode": payload.get("metadata_mode"),
                "is_normative": payload.get("is_normative"),
                "chunk_number": payload.get("chunk_number"),
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return _apply_document_diversity(
        results=results,
        top_k=top_k,
        max_chunks_per_document=search_params.get(
            "max_chunks_per_document"
        ),
    )


def search_relevant_chunks(
    prepared_request: Dict[str, Any],
    classification_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Главная функция поискового модуля."""
    if not classification_result[
        "belongs_to_knowledge_base"
    ]:
        return {
            "found": False,
            "chunks": [],
            "message": (
                "Запрос не относится к базе знаний."
            ),
        }

    retrieval_query = (
        prepared_request.get("retrieval_query")
        or prepared_request.get("search_query")
        or prepared_request["normalized_query"]
    )

    search_params = classification_result[
        "search_params"
    ]

    embedding_model = EmbeddingModel()

    query_vector = embedding_model.encode_query(
        retrieval_query
    )

    points = qdrant_vector_search(
        query_vector=query_vector,
        search_params=search_params,
    )

    reranked_chunks = rerank_search_results(
        points=points,
        retrieval_query=retrieval_query,
        search_params=search_params,
    )

    if not reranked_chunks:
        return {
            "found": False,
            "chunks": [],
            "message": (
                "Релевантные фрагменты не найдены."
            ),
            "retrieval_query": retrieval_query,
        }

    return {
        "found": True,
        "chunks": reranked_chunks,
        "message": (
            "Релевантные фрагменты найдены."
        ),
        "retrieval_query": retrieval_query,
    }