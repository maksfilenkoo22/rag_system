from typing import List

from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"

_embedding_model_instance = None


def get_sentence_transformer() -> SentenceTransformer:
    """
    Возвращает единый экземпляр SentenceTransformer.

    Модель сначала загружается из локального кэша.
    Это нужно, чтобы во время обработки /ask backend не пытался
    каждый раз обращаться к HuggingFace Hub.
    """
    global _embedding_model_instance

    if _embedding_model_instance is None:
        try:
            _embedding_model_instance = SentenceTransformer(
                EMBEDDING_MODEL_NAME,
                local_files_only=True
            )

        except Exception:
            _embedding_model_instance = SentenceTransformer(
                EMBEDDING_MODEL_NAME
            )

    return _embedding_model_instance


class EmbeddingModel:
    """
    Обёртка над embedding-моделью.

    Используется для создания векторов пользовательских запросов
    и текстовых фрагментов документов.
    """

    def __init__(self):
        self.model = get_sentence_transformer()

    def encode_query(self, query: str) -> List[float]:
        """
        Создаёт embedding-вектор для пользовательского запроса.
        """
        prepared_query = f"query: {query}"

        vector = self.model.encode(
            prepared_query,
            normalize_embeddings=True
        )

        return vector.tolist()

    def encode_text(self, text: str) -> List[float]:
        """
        Создаёт embedding-вектор для одного текстового фрагмента.
        """
        prepared_text = f"passage: {text}"

        vector = self.model.encode(
            prepared_text,
            normalize_embeddings=True
        )

        return vector.tolist()

    def encode_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Создаёт embedding-векторы для списка текстовых фрагментов.
        """
        prepared_texts = [
            f"passage: {text}"
            for text in texts
        ]

        vectors = self.model.encode(
            prepared_texts,
            normalize_embeddings=True,
            show_progress_bar=True
        )

        return [
            vector.tolist()
            for vector in vectors
        ]

    def encode_passages(self, passages: List[str]) -> List[List[float]]:
        """
        Создаёт embedding-векторы для списка фрагментов документов.

        Метод добавлен для совместимости с index_documents.py,
        где используется название encode_passages().
        """
        return self.encode_texts(passages)