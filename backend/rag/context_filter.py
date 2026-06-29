from pathlib import Path
from typing import Dict, Any, List


def is_presentation_structure_query(
    prepared_request: Dict[str, Any],
) -> bool:
    query = (
        prepared_request.get("classification_query")
        or prepared_request.get(
            "normalized_query",
            "",
        )
    ).lower()

    keywords = [
        "структура презентации",
        "какие слайды",
        "слайды должны быть",
        "презентация по нир",
        "пример структуры презентации",
        "пример презентации",
        "как выглядит презентация",
        "presentation structure",
        "what slides",
        "example presentation",
    ]

    return any(
        keyword in query
        for keyword in keywords
    )


def get_chunk_value(
    chunk: Dict[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    value = chunk.get(key)

    if value is not None:
        return value

    metadata = chunk.get("metadata")

    if isinstance(metadata, dict):
        return metadata.get(
            key,
            default,
        )

    return default


def get_file_name(
    chunk: Dict[str, Any],
) -> str:
    file_name = get_chunk_value(
        chunk,
        "file_name",
    )

    if file_name:
        return file_name

    source_path = get_chunk_value(
        chunk,
        "source_path",
    )

    if source_path:
        return Path(source_path).name

    return "unknown"


def get_document_name(
    chunk: Dict[str, Any],
) -> str:
    document_name = get_chunk_value(
        chunk,
        "document_name",
    )

    if document_name:
        return document_name

    file_name = get_file_name(chunk)

    if file_name != "unknown":
        return file_name

    return "Неизвестный документ"


def get_source_label(
    chunk: Dict[str, Any],
) -> str:
    is_normative = get_chunk_value(
        chunk,
        "is_normative",
    )
    document_type = get_chunk_value(
        chunk,
        "document_type",
    )
    metadata_mode = get_chunk_value(
        chunk,
        "metadata_mode",
    )

    if is_normative is True:
        return "Нормативный источник"

    if document_type in [
        "example_report",
        "example_presentation",
    ]:
        return "Пример работы"

    if metadata_mode == "auto":
        return "Дополнительный источник"

    return "Дополнительный источник"


def _deduplicate_chunks(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    unique_chunks: List[Dict[str, Any]] = []
    seen: set[tuple[Any, Any, str]] = set()

    for chunk in chunks:
        text = (
            get_chunk_value(
                chunk,
                "chunk_text",
                "",
            )
            or ""
        ).strip()

        identity = (
            get_file_name(chunk),
            get_chunk_value(
                chunk,
                "chunk_number",
            ),
            text[:160],
        )

        if identity in seen:
            continue

        seen.add(identity)
        unique_chunks.append(chunk)

    return unique_chunks


def filter_chunks_for_generation(
    search_result: Dict[str, Any],
    prepared_request: Dict[str, Any] | None = None,
    max_chunks: int = 4,
) -> List[Dict[str, Any]]:
    """Отбирает и упорядочивает фрагменты для передачи в LLM."""
    if not search_result.get("found"):
        return []

    chunks = [
        chunk
        for chunk in search_result.get(
            "chunks",
            [],
        )
        if get_chunk_value(
            chunk,
            "chunk_text",
        )
    ]

    chunks = _deduplicate_chunks(chunks)

    if not chunks:
        return []

    class_name = ""
    intent = "question"

    if prepared_request:
        class_name = prepared_request.get(
            "classification",
            {},
        ).get(
            "class_name",
            "",
        )

        intent = prepared_request.get(
            "intent",
            "question",
        )

    if class_name == "pz_structure":
        chunks.sort(
            key=lambda chunk: (
                0
                if get_chunk_value(
                    chunk,
                    "document_type",
                ) == "structure"
                else 1,
                -float(
                    get_chunk_value(
                        chunk,
                        "score",
                        0,
                    )
                    or 0
                ),
                get_chunk_value(
                    chunk,
                    "chunk_number",
                    999999,
                ),
            )
        )

        max_chunks = max(
            max_chunks,
            6,
        )

    elif (
        prepared_request
        and is_presentation_structure_query(
            prepared_request
        )
    ):
        chunks.sort(
            key=lambda chunk: (
                get_chunk_value(
                    chunk,
                    "chunk_number",
                ) is None,
                get_chunk_value(
                    chunk,
                    "chunk_number",
                    999999,
                ),
            )
        )

        max_chunks = max(
            max_chunks,
            6,
        )

    else:
        chunks.sort(
            key=lambda chunk: get_chunk_value(
                chunk,
                "score",
                0,
            ),
            reverse=True,
        )

        if intent == "list":
            max_chunks = max(
                max_chunks,
                5,
            )

    return chunks[:max_chunks]


def trim_text(
    text: str,
    max_length: int = 1100,
) -> str:
    if len(text) <= max_length:
        return text

    return (
        text[:max_length].strip()
        + "..."
    )


def build_context_from_chunks(
    chunks: List[Dict[str, Any]],
) -> str:
    context_parts = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        document_name = get_document_name(
            chunk
        )
        file_name = get_file_name(
            chunk
        )
        chunk_number = get_chunk_value(
            chunk,
            "chunk_number",
            "unknown",
        )
        chunk_text = trim_text(
            get_chunk_value(
                chunk,
                "chunk_text",
                "",
            )
        )

        context_parts.append(
            f"[Источник {index}]\n"
            f"Документ: {document_name}\n"
            f"Файл: {file_name}\n"
            f"Номер фрагмента: {chunk_number}\n"
            f"Текст:\n{chunk_text}"
        )

    return "\n\n".join(
        context_parts
    )


def build_sources(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    sources = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        file_name = get_file_name(chunk)
        document_name = get_document_name(
            chunk
        )

        sources.append(
            {
                "source_id": index,
                "document_id": get_chunk_value(
                    chunk,
                    "document_id",
                ),
                "document_name": document_name,
                "file_name": file_name,
                "document_type": get_chunk_value(
                    chunk,
                    "document_type",
                ),
                "knowledge_category": get_chunk_value(
                    chunk,
                    "knowledge_category",
                ),
                "source_scope": get_chunk_value(
                    chunk,
                    "source_scope",
                ),
                "source_type": get_chunk_value(
                    chunk,
                    "source_type",
                ),
                "source_format": get_chunk_value(
                    chunk,
                    "source_format",
                ),
                "source_path": get_chunk_value(
                    chunk,
                    "source_path",
                ),
                "metadata_mode": get_chunk_value(
                    chunk,
                    "metadata_mode",
                ),
                "chunk_number": get_chunk_value(
                    chunk,
                    "chunk_number",
                ),
                "score": get_chunk_value(
                    chunk,
                    "score",
                ),
                "is_normative": get_chunk_value(
                    chunk,
                    "is_normative",
                ),
                "source_label": get_source_label(
                    chunk
                ),
            }
        )

    return sources