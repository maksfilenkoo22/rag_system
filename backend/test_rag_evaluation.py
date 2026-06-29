import csv
import json
import time
from pathlib import Path
from typing import Dict, Any, List

import requests


API_URL = "http://127.0.0.1:8000"

EMAIL = "student@test.local"
PASSWORD = "student123"

RESULTS_DIR = Path("backend/data/test_results")
RESULTS_CSV_PATH = RESULTS_DIR / "rag_test_results.csv"
SUMMARY_JSON_PATH = RESULTS_DIR / "rag_test_summary.json"

SPEED_LIMIT_SECONDS = 60.0


TEST_CASES = [
    {
        "id": 1,
        "group": "Пояснительная записка",
        "query": "Какие разделы должны быть в пояснительной записке?",
        "session_id": "test_pz_001",
        "expected_keywords": ["введение", "заключение", "источ"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "metodicheskie_ukazaniya_k_napisaniyu_pz_k_proektnoj_praktike.pdf",
            "struct_rspz_uir.docx"
        ]
    },
    {
        "id": 2,
        "group": "Пояснительная записка",
        "query": "Что должно быть во введении пояснительной записки?",
        "session_id": "test_pz_002",
        "expected_keywords": ["цель", "задач", "актуаль", "вопрос", "метод"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "metodicheskie_ukazaniya_k_napisaniyu_pz_k_proektnoj_praktike.pdf"
        ]
    },
    {
        "id": 3,
        "group": "Пояснительная записка",
        "query": "Какие требования предъявляются к оформлению пояснительной записки?",
        "session_id": "test_pz_003",
        "expected_keywords": ["оформ", "рисунк", "таблиц", "источ", "текст"],
        "min_keyword_matches": 1,
        "expected_sources": [
            "metodicheskie_ukazaniya_k_napisaniyu_pz_k_proektnoj_praktike.pdf"
        ]
    },
    {
        "id": 4,
        "group": "НИР",
        "query": "Какие документы нужно подготовить по НИР?",
        "session_id": "test_nir_001",
        "expected_keywords": ["нир", "отчет", "отчёт", "поясн", "документ"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "Производственная практика (научно-исследовательская работа).pdf",
            "metodicheskie_ukazaniya_k_napisaniyu_pz_k_proektnoj_praktike.pdf"
        ]
    },
    {
        "id": 5,
        "group": "НИР",
        "query": "Что должно быть в промежуточном отчёте по НИР?",
        "session_id": "test_nir_002",
        "expected_keywords": ["результ", "работ", "этап", "план", "цель"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "Производственная практика (научно-исследовательская работа).pdf"
        ]
    },
    {
        "id": 6,
        "group": "Презентация",
        "query": "Покажи пример структуры презентации по НИР",
        "session_id": "test_presentation_001",
        "expected_keywords": ["презентац", "пример", "структур", "заголов", "название"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "нир преза филенко.pptx"
        ]
    },
    {
        "id": 7,
        "group": "Новый источник данных",
        "query": "К какому институту относится дисциплина «Теория нейронных сетей»?",
        "session_id": "test_dialog_neural_001",
        "expected_keywords": ["институт", "интеллектуаль", "кибернет"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "neural.pdf"
        ]
    },
    {
        "id": 8,
        "group": "Новый источник данных",
        "query": "К какой кафедре относится дисциплина «Теория нейронных сетей»?",
        "session_id": "test_neural_002",
        "expected_keywords": ["кафедр", "кибернет"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "neural.pdf"
        ]
    },
    {
        "id": 9,
        "group": "Новый источник данных",
        "query": "К какому направлению подготовки относится дисциплина «Теория нейронных сетей»?",
        "session_id": "test_neural_003",
        "expected_keywords": ["09.03.04", "программ", "инженер"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "neural.pdf"
        ]
    },
    {
        "id": 10,
        "group": "Диалоговый сценарий",
        "query": "А к какой кафедре?",
        "session_id": "test_dialog_neural_001",
        "expected_keywords": ["кафедр", "кибернет"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "neural.pdf"
        ]
    },
    {
        "id": 11,
        "group": "Мультиязычность",
        "query": "Which institute and department does the Neural Networks course belong to?",
        "session_id": "test_multilingual_001",
        "expected_keywords": ["institute", "cybernetic", "department", "cybernetics", "software", "engineering"],
        "min_keyword_matches": 2,
        "expected_sources": [
            "neural.pdf"
        ]
    },
    {
        "id": 12,
        "group": "Нерелевантный запрос",
        "query": "Расскажи прогноз погоды на завтра",
        "session_id": "test_outside_001",
        "expected_keywords": ["не найд", "недоступ", "базе знаний"],
        "min_keyword_matches": 1,
        "expected_sources": []
    }
]


def normalize_text(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def login() -> str:
    response = requests.post(
        f"{API_URL}/login",
        json={
            "email": EMAIL,
            "password": PASSWORD
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data["access_token"]


def ask_question(
    token: str,
    test_case: Dict[str, Any]
) -> Dict[str, Any]:
    request_body = {
        "query": test_case["query"],
        "request_id": f"quality_test_{test_case['id']}",
        "session_id": test_case["session_id"]
    }

    start_time = time.perf_counter()

    try:
        response = requests.post(
            f"{API_URL}/ask",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=request_body,
            timeout=180
        )

        elapsed_time = round(time.perf_counter() - start_time, 3)

        try:
            response_data = response.json()
        except Exception:
            response_data = {
                "raw_response": response.text
            }

        return {
            "status_code": response.status_code,
            "elapsed_time": elapsed_time,
            "response_data": response_data,
            "error": None
        }

    except Exception as error:
        elapsed_time = round(time.perf_counter() - start_time, 3)

        return {
            "status_code": None,
            "elapsed_time": elapsed_time,
            "response_data": {},
            "error": str(error)
        }


def count_keyword_matches(
    answer: str,
    expected_keywords: List[str]
) -> int:
    normalized_answer = normalize_text(answer)

    matches = 0

    for keyword in expected_keywords:
        if normalize_text(keyword) in normalized_answer:
            matches += 1

    return matches


def check_keywords(
    answer: str,
    expected_keywords: List[str],
    min_keyword_matches: int
) -> bool:
    if not expected_keywords:
        return True

    matches = count_keyword_matches(
        answer=answer,
        expected_keywords=expected_keywords
    )

    required_matches = min(
        min_keyword_matches,
        len(expected_keywords)
    )

    return matches >= required_matches


def extract_source_file_names(sources: List[Dict[str, Any]]) -> List[str]:
    file_names = []

    for source in sources:
        file_name = source.get("file_name")

        if file_name and file_name not in file_names:
            file_names.append(file_name)

    return file_names


def check_sources(
    actual_sources: List[Dict[str, Any]],
    expected_sources: List[str]
) -> bool:
    actual_file_names = extract_source_file_names(actual_sources)

    if not expected_sources:
        return len(actual_file_names) == 0

    normalized_actual = [
        normalize_text(file_name)
        for file_name in actual_file_names
    ]

    for expected_source in expected_sources:
        expected = normalize_text(expected_source)

        for actual in normalized_actual:
            if expected == actual or expected in actual:
                return True

    return False


def backend_detail_to_text(detail: Any) -> str:
    if detail is None:
        return ""

    if isinstance(detail, str):
        return detail

    try:
        return json.dumps(
            detail,
            ensure_ascii=False
        )
    except Exception:
        return str(detail)


def evaluate_test_case(
    test_case: Dict[str, Any],
    response_result: Dict[str, Any]
) -> Dict[str, Any]:
    response_data = response_result["response_data"]

    answer = response_data.get("answer", "")
    sources = response_data.get("sources", [])
    classification = response_data.get("classification", {})
    search = response_data.get("search", {})
    language = response_data.get("language", {})
    dialog = response_data.get("dialog", {})
    backend_detail = response_data.get("detail")

    status_ok = response_result["status_code"] == 200

    keyword_matches = count_keyword_matches(
        answer=answer,
        expected_keywords=test_case["expected_keywords"]
    ) if status_ok else 0

    keywords_ok = check_keywords(
        answer=answer,
        expected_keywords=test_case["expected_keywords"],
        min_keyword_matches=test_case["min_keyword_matches"]
    ) if status_ok else False

    sources_ok = check_sources(
        actual_sources=sources,
        expected_sources=test_case["expected_sources"]
    ) if status_ok else False

    speed_ok = response_result["elapsed_time"] <= SPEED_LIMIT_SECONDS

    test_ok = status_ok and keywords_ok and sources_ok

    source_file_names = extract_source_file_names(sources)

    return {
        "id": test_case["id"],
        "group": test_case["group"],
        "query": test_case["query"],
        "status_code": response_result["status_code"],
        "elapsed_time_sec": response_result["elapsed_time"],
        "status_ok": status_ok,
        "keywords_ok": keywords_ok,
        "keyword_matches": keyword_matches,
        "keyword_required": test_case["min_keyword_matches"],
        "sources_ok": sources_ok,
        "speed_ok": speed_ok,
        "test_ok": test_ok,
        "answer": answer,
        "source_file_names": "; ".join(source_file_names),
        "expected_sources": "; ".join(test_case["expected_sources"]),
        "classification": classification.get("class_name"),
        "search_found": search.get("found"),
        "chunks_count": search.get("chunks_count"),
        "language": language.get("language"),
        "history_used": dialog.get("history_used"),
        "standalone_query": dialog.get("standalone_query"),
        "backend_detail": backend_detail_to_text(backend_detail),
        "error": response_result["error"]
    }


def calculate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)

    successful_requests = sum(1 for item in results if item["status_ok"])
    correct_answers = sum(1 for item in results if item["test_ok"])
    correct_keywords = sum(1 for item in results if item["keywords_ok"])
    correct_sources = sum(1 for item in results if item["sources_ok"])
    speed_ok_count = sum(1 for item in results if item["speed_ok"])

    elapsed_times = [
        item["elapsed_time_sec"]
        for item in results
        if item["elapsed_time_sec"] is not None
    ]

    average_time = round(sum(elapsed_times) / len(elapsed_times), 3) if elapsed_times else 0
    min_time = round(min(elapsed_times), 3) if elapsed_times else 0
    max_time = round(max(elapsed_times), 3) if elapsed_times else 0

    return {
        "total_queries": total,
        "successful_requests": successful_requests,
        "stability_rate": round(successful_requests / total, 3) if total else 0,
        "correct_answers": correct_answers,
        "accuracy_rate": round(correct_answers / total, 3) if total else 0,
        "keyword_match_count": correct_keywords,
        "keyword_match_rate": round(correct_keywords / total, 3) if total else 0,
        "correct_sources": correct_sources,
        "source_accuracy_rate": round(correct_sources / total, 3) if total else 0,
        "speed_ok_count": speed_ok_count,
        "speed_ok_rate": round(speed_ok_count / total, 3) if total else 0,
        "average_time_sec": average_time,
        "min_time_sec": min_time,
        "max_time_sec": max_time,
        "speed_limit_sec": SPEED_LIMIT_SECONDS
    }


def save_results_to_csv(results: List[Dict[str, Any]]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "group",
        "query",
        "status_code",
        "elapsed_time_sec",
        "status_ok",
        "keywords_ok",
        "keyword_matches",
        "keyword_required",
        "sources_ok",
        "speed_ok",
        "test_ok",
        "source_file_names",
        "expected_sources",
        "classification",
        "search_found",
        "chunks_count",
        "language",
        "history_used",
        "standalone_query",
        "answer",
        "backend_detail",
        "error"
    ]

    with open(RESULTS_CSV_PATH, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";"
        )

        writer.writeheader()

        for item in results:
            writer.writerow(item)


def save_summary_to_json(summary: Dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(SUMMARY_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(
            summary,
            file,
            ensure_ascii=False,
            indent=4
        )


def print_result_row(result: Dict[str, Any]) -> None:
    status = "OK" if result["test_ok"] else "FAIL"

    print(
        f"{result['id']:02d}. "
        f"{status} | "
        f"code={result['status_code']} | "
        f"{result['group']} | "
        f"{result['elapsed_time_sec']} сек | "
        f"sources_ok={result['sources_ok']} | "
        f"keywords_ok={result['keywords_ok']} "
        f"({result['keyword_matches']}/{result['keyword_required']}) | "
        f"source={result['source_file_names']}"
    )

    if result["backend_detail"]:
        print(f"    backend_detail={result['backend_detail']}")

    if result["error"]:
        print(f"    error={result['error']}")


def main() -> None:
    print("Запуск тестирования RAG-системы")
    print(f"Backend: {API_URL}")
    print("=" * 100)

    token = login()

    results = []

    for test_case in TEST_CASES:
        response_result = ask_question(
            token=token,
            test_case=test_case
        )

        evaluation_result = evaluate_test_case(
            test_case=test_case,
            response_result=response_result
        )

        results.append(evaluation_result)

        print_result_row(evaluation_result)

    summary = calculate_summary(results)

    save_results_to_csv(results)
    save_summary_to_json(summary)

    print("=" * 100)
    print("Итоги тестирования:")
    print(f"Всего запросов: {summary['total_queries']}")
    print(f"Успешно обработано: {summary['successful_requests']}")
    print(f"Стабильность: {summary['stability_rate'] * 100:.1f}%")
    print(f"Корректные ответы: {summary['correct_answers']}")
    print(f"Точность ответов: {summary['accuracy_rate'] * 100:.1f}%")
    print(f"Корректность источников: {summary['source_accuracy_rate'] * 100:.1f}%")
    print(f"Среднее время ответа: {summary['average_time_sec']} сек")
    print(f"Минимальное время ответа: {summary['min_time_sec']} сек")
    print(f"Максимальное время ответа: {summary['max_time_sec']} сек")
    print("=" * 100)
    print(f"CSV с результатами: {RESULTS_CSV_PATH}")
    print(f"JSON с итогами: {SUMMARY_JSON_PATH}")


if __name__ == "__main__":
    main()