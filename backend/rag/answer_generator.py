import re
from typing import Dict, Any, List

from backend.rag.context_filter import (
    filter_chunks_for_generation,
    build_context_from_chunks,
    build_sources,
)
from backend.rag.prompt_builder import (
    build_rag_messages,
    build_retry_messages,
)
from backend.rag.llm_client import generate_llm_answer


LATIN_TO_CYRILLIC_MAP = {
    "A": "А",
    "B": "В",
    "C": "С",
    "E": "Е",
    "H": "Н",
    "K": "К",
    "M": "М",
    "O": "О",
    "P": "Р",
    "T": "Т",
    "X": "Х",
    "a": "а",
    "c": "с",
    "e": "е",
    "i": "и",
    "k": "к",
    "m": "м",
    "o": "о",
    "p": "р",
    "x": "х",
    "y": "у",
}

RU_NOT_FOUND = (
    "Информация не найдена в базе знаний."
)
EN_NOT_FOUND = (
    "The information was not found in the knowledge base."
)


def normalize_mixed_cyrillic_words(
    text: str,
) -> str:
    if not text:
        return text

    word_pattern = re.compile(
        r"[A-Za-zА-Яа-яЁё]+"
    )

    def replace_word(
        match: re.Match,
    ) -> str:
        word = match.group(0)

        has_cyrillic = bool(
            re.search(
                r"[А-Яа-яЁё]",
                word,
            )
        )
        has_latin = bool(
            re.search(
                r"[A-Za-z]",
                word,
            )
        )

        if not has_cyrillic or not has_latin:
            return word

        return "".join(
            LATIN_TO_CYRILLIC_MAP.get(
                char,
                char,
            )
            for char in word
        )

    return word_pattern.sub(
        replace_word,
        text,
    )


def contains_cyrillic(text: str) -> bool:
    return bool(
        re.search(
            r"[А-Яа-яЁё]",
            text or "",
        )
    )


def force_translate_to_english(
    answer: str,
    sources: List[Dict[str, Any]],
) -> str:
    source_ids = [
        f"[{source.get('source_id')}]"
        for source in sources
        if source.get("source_id") is not None
    ]

    source_text = (
        ", ".join(source_ids)
        if source_ids
        else "[1]"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Translate the given answer into English only. "
                "Do not add new facts. "
                "Keep source references unchanged. "
                "Return only the translated answer."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Answer to translate:\n"
                f"{answer}\n\n"
                f"Available source references: "
                f"{source_text}"
            ),
        },
    ]

    return generate_llm_answer(
        messages
    )


def is_not_found_answer(
    answer: str,
    language: str,
) -> bool:
    normalized = (
        (answer or "")
        .strip()
        .lower()
    )

    if language == "en":
        return (
            "not found in the knowledge base"
            in normalized
        )

    return (
        "информация не найдена в базе знаний"
        in normalized
    )


def has_numbered_or_bulleted_list(
    answer: str,
) -> bool:
    items = re.findall(
        r"(?m)^\s*(?:\d+[.)]|[-–—•])\s+\S+",
        answer or "",
    )

    return len(items) >= 2


def has_source_references(
    answer: str,
    language: str,
) -> bool:
    if language == "en":
        return bool(
            re.search(
                r"Sources\s*:\s*\[\d+\]",
                answer or "",
                re.IGNORECASE,
            )
        )

    return bool(
        re.search(
            r"Источники\s*:\s*\[\d+\]",
            answer or "",
            re.IGNORECASE,
        )
    )


def _count_matching_stems(
    text: str,
    stems: List[str],
) -> int:
    normalized = (
        (text or "")
        .lower()
        .replace("ё", "е")
    )

    return sum(
        1
        for stem in stems
        if stem in normalized
    )


def answer_matches_request(
    answer: str,
    prepared_request: Dict[str, Any],
) -> bool:
    """
    Выполняет лёгкую runtime-проверку ответа.

    Проверка не оценивает истинность каждого утверждения,
    но обнаруживает наиболее частые сбои маленькой LLM:
    ответ не на ту тему и нарушение требуемого формата списка.
    """
    language = prepared_request.get(
        "language",
        "ru",
    )
    intent = prepared_request.get(
        "intent",
        "question",
    )
    class_name = prepared_request.get(
        "classification",
        {},
    ).get(
        "class_name",
        "",
    )

    if not answer or not answer.strip():
        return False

    if is_not_found_answer(
        answer,
        language,
    ):
        return class_name != "pz_structure"

    if (
        intent == "list"
        and not has_numbered_or_bulleted_list(answer)
    ):
        return False

    if class_name == "pz_structure":
        if language == "en":
            structure_terms = [
                "introduction",
                "analytical",
                "software",
                "implementation",
                "testing",
                "conclusion",
                "references",
                "literature",
            ]
            unrelated_terms = [
                "documents to submit",
                "presentation slides",
            ]

        else:
            structure_terms = [
                "введен",
                "аналит",
                "программ",
                "реализац",
                "тестирован",
                "заключен",
                "литератур",
                "источник",
            ]
            unrelated_terms = [
                "документы необходимо подготовить",
                "документы нужно сдать",
                "структура презентации",
            ]

        if (
            _count_matching_stems(
                answer,
                structure_terms,
            )
            < 3
        ):
            return False

        normalized_answer = (
            answer
            .lower()
            .replace("ё", "е")
        )

        if any(
            term in normalized_answer
            for term in unrelated_terms
        ):
            return False

    return True


def append_source_references_if_missing(
    answer: str,
    sources: List[Dict[str, Any]],
    language: str,
) -> str:
    if (
        not answer
        or is_not_found_answer(
            answer,
            language,
        )
    ):
        return answer

    normalized_answer = answer.lower()

    if (
        "не удалось сформировать ответ"
        in normalized_answer
        or "response could not be generated"
        in normalized_answer
    ):
        return answer

    if has_source_references(
        answer,
        language,
    ):
        return answer

    source_ids = [
        f"[{source['source_id']}]"
        for source in sources
        if source.get("source_id") is not None
    ]

    if not source_ids:
        return answer

    prefix = (
        "Sources"
        if language == "en"
        else "Источники"
    )

    return (
        f"{answer.rstrip()}\n\n"
        f"{prefix}: {', '.join(source_ids)}."
    )


def get_generation_error_answer(
    language: str,
) -> str:
    if language == "en":
        return (
            "The response could not be generated. "
            "Please try again."
        )

    return (
        "Не удалось сформировать ответ. "
        "Повторите запрос."
    )


def generate_answer(
    prepared_request: Dict[str, Any],
    search_result: Dict[str, Any],
) -> Dict[str, Any]:
    language = prepared_request.get(
        "language",
        "ru",
    )

    chunks = filter_chunks_for_generation(
        search_result=search_result,
        prepared_request=prepared_request,
    )

    if not chunks:
        return {
            "answer": (
                EN_NOT_FOUND
                if language == "en"
                else RU_NOT_FOUND
            ),
            "sources": [],
            "request_id": prepared_request.get(
                "request_id"
            ),
        }

    context = build_context_from_chunks(
        chunks
    )
    sources = build_sources(
        chunks
    )

    user_query_for_llm = (
        prepared_request.get("standalone_query")
        or prepared_request.get("raw_query")
    )

    classification = prepared_request.get(
        "classification",
        {},
    )

    messages = build_rag_messages(
        user_query=user_query_for_llm,
        context=context,
        sources=sources,
        language=language,
        dialog_context=prepared_request.get(
            "dialog_context",
            "",
        ),
        intent_label=prepared_request.get(
            "intent_label",
            "",
        ),
        response_format=prepared_request.get(
            "response_format",
            "",
        ),
        classification_name=classification.get(
            "display_name",
            "",
        ),
    )

    try:
        answer = generate_llm_answer(
            messages
        )

        if not answer_matches_request(
            answer,
            prepared_request,
        ):
            retry_messages = build_retry_messages(
                base_messages=messages,
                previous_answer=answer,
                language=language,
                intent=prepared_request.get(
                    "intent",
                    "question",
                ),
                class_name=classification.get(
                    "class_name",
                    "",
                ),
            )

            answer = generate_llm_answer(
                retry_messages
            )

    except RuntimeError:
        answer = get_generation_error_answer(
            language
        )

    if language == "ru":
        answer = normalize_mixed_cyrillic_words(
            answer
        )

    if (
        language == "en"
        and contains_cyrillic(answer)
    ):
        try:
            answer = force_translate_to_english(
                answer=answer,
                sources=sources,
            )
        except RuntimeError:
            answer = get_generation_error_answer(
                language
            )

    answer = append_source_references_if_missing(
        answer=answer,
        sources=sources,
        language=language,
    )

    return {
        "answer": answer,
        "sources": sources,
        "request_id": prepared_request.get(
            "request_id"
        ),
    }