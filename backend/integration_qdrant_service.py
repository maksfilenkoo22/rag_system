from typing import Dict, Any

from qdrant_client import QdrantClient

from backend.rag.qdrant_store import get_qdrant_client, COLLECTION_NAME


def get_vector_config(collection_info: Any) -> Dict[str, Any]:
    """
    Извлекает параметры векторного поля из информации о коллекции Qdrant.
    """
    try:
        vectors_config = collection_info.config.params.vectors

        if isinstance(vectors_config, dict):
            first_vector = next(iter(vectors_config.values()))

            vector_size = getattr(first_vector, "size", None)
            distance = getattr(first_vector, "distance", None)

        else:
            vector_size = getattr(vectors_config, "size", None)
            distance = getattr(vectors_config, "distance", None)

        return {
            "vector_size": vector_size,
            "distance": str(distance) if distance is not None else None
        }

    except Exception:
        return {
            "vector_size": None,
            "distance": None
        }


def get_sample_point(client: QdrantClient) -> Dict[str, Any]:
    """
    Получает пример одной записи из Qdrant.

    Важно: сюда передаётся уже созданный client.
    Новый QdrantClient здесь не создаётся, чтобы не блокировать qdrant_storage.
    """
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=1,
        with_payload=True,
        with_vectors=False
    )

    if not points:
        return {
            "found": False,
            "message": "В коллекции нет сохранённых points"
        }

    point = points[0]
    payload = point.payload or {}

    return {
        "found": True,
        "point_id": point.id,
        "payload_fields": list(payload.keys()),
        "document_name": payload.get("document_name"),
        "file_name": payload.get("file_name"),
        "document_type": payload.get("document_type"),
        "knowledge_category": payload.get("knowledge_category"),
        "chunk_number": payload.get("chunk_number"),
        "is_normative": payload.get("is_normative"),
        "chunk_text_preview": str(payload.get("chunk_text", ""))[:300]
    }


def build_qdrant_integration_status() -> Dict[str, Any]:
    """
    Проверяет настройку векторной базы данных Qdrant.
    """
    try:
        client = get_qdrant_client()

        collection_info = client.get_collection(
            collection_name=COLLECTION_NAME
        )

        points_count = client.count(
            collection_name=COLLECTION_NAME,
            exact=True
        ).count

        vector_config = get_vector_config(collection_info)
        sample_point = get_sample_point(client)

        return {
            "status": "ok",
            "message": "Qdrant успешно подключён, коллекция базы знаний доступна",
            "qdrant": {
                "collection_name": COLLECTION_NAME,
                "points_count": points_count,
                "vector_size": vector_config["vector_size"],
                "distance": vector_config["distance"]
            },
            "storage_structure": {
                "point_id": "уникальный идентификатор чанка",
                "vector": "embedding-вектор текстового фрагмента",
                "payload": [
                    "chunk_text",
                    "document_name",
                    "file_name",
                    "document_type",
                    "knowledge_category",
                    "chunk_number",
                    "is_normative"
                ]
            },
            "sample_point": sample_point
        }

    except Exception as error:
        return {
            "status": "error",
            "message": "Ошибка подключения или настройки Qdrant",
            "collection_name": COLLECTION_NAME,
            "error": str(error)
        }