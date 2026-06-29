from backend.rag.query_preprocessor import build_prepared_request
from backend.rag.classifier import classify_query
from backend.rag.search_service import search_relevant_chunks
from backend.rag.answer_generator import generate_answer


def print_header(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def print_sources(sources: list[dict]) -> None:
    if not sources:
        print("Источники не найдены.")
        return

    for source in sources:
        print(
            f"[{source['source_id']}] "
            f"{source['document_name']} | "
            f"файл: {source['file_name']} | "
            f"чанк: {source['chunk_number']} | "
            f"score: {source['score']} | "
            f"нормативный: {source['is_normative']}"
        )


def main() -> None:
    query = input("Введите вопрос пользователя: ")

    prepared_request = build_prepared_request(
        raw_query=query,
        user_id=1,
        role="student",
        request_id="test_answer_001"
    )

    classification_result = classify_query(prepared_request)

    search_result = search_relevant_chunks(
        prepared_request=prepared_request,
        classification_result=classification_result
    )

    answer_result = generate_answer(
        prepared_request=prepared_request,
        search_result=search_result
    )

    print_header("ВОПРОС ПОЛЬЗОВАТЕЛЯ")
    print(prepared_request["raw_query"])

    print_header("КЛАССИФИКАЦИЯ ЗАПРОСА")
    print(f"Класс: {classification_result['class_name']}")
    print(f"Описание: {classification_result['display_name']}")
    print(f"Относится к базе знаний: {classification_result['belongs_to_knowledge_base']}")
    print(f"Оценка совпадения правил: {classification_result.get('matched_score')}")

    print_header("РЕЗУЛЬТАТ ПОИСКА")
    print(f"Найдено: {search_result['found']}")
    print(f"Сообщение: {search_result['message']}")

    if search_result["chunks"]:
        best_chunk = search_result["chunks"][0]

        print("\nЛучший найденный фрагмент:")
        print(f"Документ: {best_chunk['document_name']}")
        print(f"Файл: {best_chunk['file_name']}")
        print(f"Score: {best_chunk['score']}")
        print(f"Vector score: {best_chunk['vector_score']}")
        print(f"Lexical score: {best_chunk['lexical_score']}")
        print(f"Нормативный источник: {best_chunk['is_normative']}")

    print_header("ИТОГОВЫЙ ОТВЕТ RAG-СИСТЕМЫ")
    print(answer_result["answer"])

    print_header("ИСТОЧНИКИ")
    print_sources(answer_result["sources"])


if __name__ == "__main__":
    main()