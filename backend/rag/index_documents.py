from pathlib import Path

from backend.rag.document_loader import load_document
from backend.rag.text_cleaner import clean_text
from backend.rag.chunker import split_text_into_chunks, build_chunk_records
from backend.rag.document_registry import get_document_metadata
from backend.rag.embeddings import EmbeddingModel
from backend.rag.qdrant_store import (
    get_qdrant_client,
    recreate_collection,
    build_qdrant_point,
    upload_points,
    get_collection_count
)


BASE_DIR = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = BASE_DIR / "data" / "documents"


def process_document(file_path: Path) -> list[dict]:
    metadata = get_document_metadata(file_path)

    raw_text = load_document(file_path)
    cleaned_text = clean_text(raw_text)

    chunks = split_text_into_chunks(
        text=cleaned_text,
        chunk_size=1200,
        chunk_overlap=200
    )

    chunk_records = build_chunk_records(
        chunks=chunks,
        document_metadata=metadata
    )

    print("\n" + "=" * 100)
    print(f"Файл: {file_path.name}")
    print(f"Тип документа: {metadata['document_type']}")
    print(f"Категория: {metadata['knowledge_category']}")
    print(f"Нормативный источник: {metadata['is_normative']}")
    print(f"Символов после очистки: {len(cleaned_text)}")
    print(f"Количество чанков: {len(chunk_records)}")

    if chunk_records:
        print("\nПервый чанк:")
        print(chunk_records[0]["chunk_text"][:500])

    return chunk_records


def collect_chunk_records() -> list[dict]:
    print(f"Папка документов: {DOCUMENTS_DIR}")

    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError("Папка documents не найдена.")

    files = [
        file_path
        for file_path in DOCUMENTS_DIR.iterdir()
        if file_path.is_file()
    ]

    if not files:
        raise FileNotFoundError("В папке documents пока нет файлов.")

    all_records = []

    for file_path in files:
        records = process_document(file_path)
        all_records.extend(records)

    print("\n" + "=" * 100)
    print(f"Итого обработано файлов: {len(files)}")
    print(f"Итого подготовлено чанков: {len(all_records)}")

    return all_records


def main() -> None:
    print("Запуск индексации базы знаний RAG-системы")

    chunk_records = collect_chunk_records()

    print("\n" + "=" * 100)
    print("Загрузка модели эмбеддингов...")
    embedding_model = EmbeddingModel()

    chunk_texts = [
        record["chunk_text"]
        for record in chunk_records
    ]

    print("\n" + "=" * 100)
    print("Создание эмбеддингов для чанков...")
    vectors = embedding_model.encode_passages(chunk_texts)

    if len(vectors) != len(chunk_records):
        raise RuntimeError(
            "Количество эмбеддингов не совпадает с количеством чанков."
        )

    print("\n" + "=" * 100)
    print("Подключение к локальной Qdrant базе...")
    client = get_qdrant_client()

    print("Пересоздание коллекции Qdrant...")
    recreate_collection(client)

    print("Формирование Qdrant points...")
    points = [
        build_qdrant_point(record, vector)
        for record, vector in zip(chunk_records, vectors)
    ]

    print("\n" + "=" * 100)
    print("Загрузка points в Qdrant...")
    upload_points(client, points)

    total_points = get_collection_count(client)

    print("\n" + "=" * 100)
    print("Индексация базы знаний завершена успешно.")
    print(f"Коллекция Qdrant: mephi_rag_knowledge_base")
    print(f"Всего загружено points: {total_points}")


if __name__ == "__main__":
    main()