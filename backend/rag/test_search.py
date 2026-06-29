from backend.rag.query_preprocessor import build_prepared_request
from backend.rag.classifier import classify_query
from backend.rag.search_service import search_relevant_chunks


def main() -> None:
    query = input("Введите вопрос пользователя: ")

    prepared_request = build_prepared_request(
        raw_query=query,
        user_id=1,
        role="student",
        request_id="test_search_001"
    )

    classification_result = classify_query(prepared_request)

    print("\n" + "=" * 100)
    print("PREPARED REQUEST")
    print(prepared_request)

    print("\n" + "=" * 100)
    print("CLASSIFICATION RESULT")
    print(classification_result)

    search_result = search_relevant_chunks(
        prepared_request=prepared_request,
        classification_result=classification_result
    )

    print("\n" + "=" * 100)
    print("SEARCH RESULT")
    print(f"Найдено: {search_result['found']}")
    print(f"Сообщение: {search_result['message']}")

    for index, chunk in enumerate(search_result["chunks"], start=1):
        print("\n" + "-" * 100)
        print(f"Результат #{index}")
        print(f"Score: {chunk['score']}")
        print(f"Vector score: {chunk['vector_score']}")
        print(f"Lexical score: {chunk['lexical_score']}")
        print(f"Документ: {chunk['document_name']}")
        print(f"Файл: {chunk['file_name']}")
        print(f"Тип документа: {chunk['document_type']}")
        print(f"Категория: {chunk['knowledge_category']}")
        print(f"Нормативный источник: {chunk['is_normative']}")
        print(f"Номер чанка: {chunk['chunk_number']}")
        print("\nТекст чанка:")
        print(chunk["chunk_text"][:800])


if __name__ == "__main__":
    main()