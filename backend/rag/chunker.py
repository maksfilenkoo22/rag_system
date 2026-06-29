from typing import List, Dict, Any


def split_text_into_chunks(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 200
) -> List[str]:
    """
    Делит текст на чанки с перекрытием.
    Для первого прототипа используем разбиение по символам.
    """
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - chunk_overlap

        if start >= text_length:
            break

    return chunks


def build_chunk_records(
    chunks: List[str],
    document_metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Формирует записи чанков с метаданными.
    Позже именно эти записи будут превращаться в Qdrant points.
    """
    records = []

    for chunk_number, chunk_text in enumerate(chunks, start=1):
        chunk_id = f"{document_metadata['document_id']}_chunk_{chunk_number}"

        record = {
            "chunk_id": chunk_id,
            "chunk_number": chunk_number,
            "chunk_text": chunk_text,
            "metadata": {
                **document_metadata,
                "chunk_number": chunk_number
            }
        }

        records.append(record)

    return records