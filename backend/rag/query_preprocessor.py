import re
from typing import Dict, Any, Optional


MAX_QUERY_LENGTH = 500


RU_COMMAND_PREFIXES = [
    "покажи",
    "перечисли",
    "назови",
    "выведи",
    "найди",
    "расскажи",
    "объясни",
    "опиши",
    "сравни",
    "составь",
    "подготовь",
    "приведи",
    "укажи",
    "дай",
]

EN_COMMAND_PREFIXES = [
    "show",
    "list",
    "name",
    "find",
    "tell",
    "explain",
    "describe",
    "compare",
    "compose",
    "create",
    "provide",
    "give",
]


RETRIEVAL_STOP_WORDS = {
    "покажи", "перечисли", "назови", "выведи", "найди", "расскажи",
    "объясни", "опиши", "сравни", "составь", "подготовь", "приведи",
    "укажи", "дай", "пожалуйста", "мне", "можешь", "нужно", "надо",
    "show", "list", "name", "find", "tell", "explain", "describe",
    "compare", "compose", "create", "provide", "give", "please", "me",
}


INTENT_LABELS_RU = {
    "list": "перечисление или показ структуры",
    "find": "поиск сведений",
    "explain": "краткое объяснение",
    "compare": "сравнение",
    "summarize": "краткое изложение",
    "compose": "составление материала по данным источников",
    "question": "ответ на вопрос",
}

INTENT_LABELS_EN = {
    "list": "list or structure output",
    "find": "information retrieval",
    "explain": "brief explanation",
    "compare": "comparison",
    "summarize": "summary",
    "compose": "composition based on the sources",
    "question": "question answering",
}


RESPONSE_FORMATS_RU = {
    "list": (
        "Дай нумерованный список. Каждый пункт должен быть коротким "
        "и содержать один элемент."
    ),
    "find": (
        "Сначала дай прямой ответ, затем кратко перечисли найденные сведения."
    ),
    "explain": "Дай краткое объяснение в 1–3 абзацах или пунктах.",
    "compare": (
        "Сравни объекты по одинаковым критериям. "
        "Используй короткие пункты или компактную таблицу."
    ),
    "summarize": (
        "Дай краткое структурированное резюме без второстепенных деталей."
    ),
    "compose": (
        "Составь запрошенный материал только из фактов, "
        "содержащихся в контексте."
    ),
    "question": "Дай прямой, краткий и структурированный ответ.",
}

RESPONSE_FORMATS_EN = {
    "list": (
        "Return a numbered list. Keep every item short "
        "and limited to one element."
    ),
    "find": (
        "Give the direct answer first, then briefly list the retrieved facts."
    ),
    "explain": "Give a brief explanation in 1–3 paragraphs or bullet points.",
    "compare": (
        "Compare the items using the same criteria. "
        "Use short bullets or a compact table."
    ),
    "summarize": (
        "Give a concise structured summary without secondary details."
    ),
    "compose": (
        "Create the requested material using only facts contained "
        "in the context."
    ),
    "question": "Give a direct, concise and structured answer.",
}


def normalize_query(raw_query: str) -> str:
    """
    Нормализует пользовательский запрос без изменения его смысла.
    """
    query = (raw_query or "").strip().lower().replace("ё", "е")
    query = re.sub(r"\s+", " ", query)
    query = re.sub(r"[!?]{2,}", "?", query)
    return query


def tokenize_query(normalized_query: str) -> list[str]:
    """Выделяет слова, числа и сокращения."""
    return re.findall(r"[а-яa-z0-9]+", normalized_query)


def detect_query_intent(normalized_query: str) -> str:
    """
    Определяет, какой формат ответа ожидает пользователь.

    Команда, вопрос и короткая именная фраза считаются
    равноправными запросами.
    """
    query = normalize_query(normalized_query)

    intent_patterns = [
        (
            "compare",
            [
                r"\bсравн",
                r"\bотлич",
                r"\bразниц",
                r"\bcompare\b",
                r"\bdifference",
                r"\bversus\b",
                r"\bvs\b",
            ],
        ),
        (
            "compose",
            [
                r"\bсостав",
                r"\bсформир",
                r"\bсозда",
                r"\bшаблон",
                r"\bcompose\b",
                r"\bcreate\b",
                r"\bdraft\b",
                r"\btemplate\b",
            ],
        ),
        (
            "summarize",
            [
                r"\bкратко излож",
                r"\bрезюм",
                r"\bсократ",
                r"\bsummary\b",
                r"\bsummar",
                r"\bbriefly summarize\b",
            ],
        ),
        (
            "explain",
            [
                r"\bобъясн",
                r"\bрасскаж",
                r"\bопиш",
                r"\bчто такое\b",
                r"\bexplain\b",
                r"\bdescribe\b",
                r"\btell me about\b",
            ],
        ),
        (
            "find",
            [
                r"\bнайд",
                r"\bпоиск",
                r"\bгде указан",
                r"\bfind\b",
                r"\bsearch\b",
                r"\blocate\b",
            ],
        ),
        (
            "list",
            [
                r"\bпокаж",
                r"\bперечисл",
                r"\bназов",
                r"\bвывед",
                r"\bкакие\b",
                r"\bкакая структура\b",
                r"\bструктура\b",
                r"\bраздел",
                r"\bсодержани[ея]\b",
                r"\bshow\b",
                r"\blist\b",
                r"\bname\b",
                r"\bwhat sections\b",
                r"\bstructure\b",
            ],
        ),
    ]

    for intent, patterns in intent_patterns:
        if any(re.search(pattern, query) for pattern in patterns):
            return intent

    return "question"


def remove_command_prefix(
    normalized_query: str,
    language: str,
) -> str:
    """
    Удаляет только вводную команду в начале запроса.

    Смысл команды сохраняется отдельно в поле intent, а поисковая модель
    получает главным образом предметные слова запроса.
    """
    query = normalize_query(normalized_query)

    if language == "en":
        prefixes = EN_COMMAND_PREFIXES
        polite_prefix = r"^(?:please\s+)?"
    else:
        prefixes = RU_COMMAND_PREFIXES
        polite_prefix = r"^(?:пожалуйста[,\s]+)?"

    command_pattern = "|".join(
        re.escape(prefix)
        for prefix in prefixes
    )

    query = re.sub(
        polite_prefix + rf"(?:{command_pattern})\s+",
        "",
        query,
        count=1,
    )

    return query.strip(" ,.:;!?-")


def _contains_any(
    text: str,
    values: list[str],
) -> bool:
    return any(value in text for value in values)


def expand_domain_query(
    query: str,
    language: str,
) -> str:
    """
    Добавляет к поисковому запросу предметные синонимы.

    Расширение влияет только на retrieval. Исходная формулировка пользователя
    передаётся LLM без подмены.
    """
    normalized = normalize_query(query)
    expansions: list[str] = []

    if language == "en":
        is_presentation = _contains_any(
            normalized,
            [
                "presentation",
                "slides",
                "slide deck",
            ],
        )
        is_structure = _contains_any(
            normalized,
            [
                "structure",
                "sections",
                "contents",
                "outline",
            ],
        )
        is_nir = _contains_any(
            normalized,
            [
                "nir",
                "research work",
                "research report",
                "explanatory report",
            ],
        )

        if is_presentation and is_structure:
            expansions.append(
                "NIR presentation structure slide order title relevance "
                "goal tasks architecture implementation testing results "
                "conclusion"
            )
        elif is_structure and is_nir:
            expansions.append(
                "structure of the NIR explanatory report mandatory "
                "top-level sections introduction analytical part software "
                "implementation testing conclusion references"
            )

        if _contains_any(
            normalized,
            [
                "documents",
                "submit",
                "submission",
                "admission",
            ],
        ):
            expansions.append(
                "NIR submission documents report presentation "
                "supervisor review admission"
            )

    else:
        is_presentation = _contains_any(
            normalized,
            [
                "презентац",
                "слайд",
            ],
        )
        is_structure = _contains_any(
            normalized,
            [
                "структур",
                "раздел",
                "содержан",
                "что входит",
            ],
        )
        is_nir = _contains_any(
            normalized,
            [
                "нир",
                "научно-исследовательск",
                "пояснительн",
                "пз",
            ],
        )

        if is_presentation and is_structure:
            expansions.append(
                "структура презентации по НИР порядок слайдов "
                "титульный слайд актуальность цель задачи архитектура "
                "реализация тестирование результаты заключение"
            )
        elif is_structure and is_nir:
            expansions.append(
                "структура пояснительной записки по НИР обязательные "
                "основные разделы введение аналитическая часть "
                "программная часть тестирование заключение список литературы"
            )

        if _contains_any(
            normalized,
            [
                "документ",
                "сдать",
                "допуск",
                "отчетные материалы",
            ],
        ):
            expansions.append(
                "документы для сдачи НИР пояснительная записка отчет "
                "презентация отзыв руководителя допуск"
            )

    if not expansions:
        return normalized

    return f"{normalized} {' '.join(expansions)}".strip()


def build_retrieval_query(
    query: str,
    language: str,
    intent: Optional[str] = None,
) -> str:
    """Формирует поисковый запрос для embedding-модели и rerank."""
    normalized = normalize_query(query)
    subject_query = remove_command_prefix(
        normalized,
        language,
    )

    if not subject_query:
        subject_query = normalized

    expanded_query = expand_domain_query(
        subject_query,
        language,
    )

    words = tokenize_query(expanded_query)
    unique_words: list[str] = []
    seen: set[str] = set()

    for word in words:
        if word in RETRIEVAL_STOP_WORDS:
            continue

        if word not in seen:
            seen.add(word)
            unique_words.append(word)

    return " ".join(unique_words) or normalized


def get_intent_label(
    intent: str,
    language: str,
) -> str:
    labels = (
        INTENT_LABELS_EN
        if language == "en"
        else INTENT_LABELS_RU
    )

    return labels.get(
        intent,
        labels["question"],
    )


def get_response_format(
    intent: str,
    language: str,
) -> str:
    formats = (
        RESPONSE_FORMATS_EN
        if language == "en"
        else RESPONSE_FORMATS_RU
    )

    return formats.get(
        intent,
        formats["question"],
    )


def validate_query(raw_query: str) -> Optional[str]:
    if raw_query is None:
        return "Query is missing"

    query = raw_query.strip()

    if not query:
        return "Query is empty"

    if len(query) > MAX_QUERY_LENGTH:
        return (
            f"Query is too long. Maximum length is "
            f"{MAX_QUERY_LENGTH} characters"
        )

    return None


def build_prepared_request(
    raw_query: str,
    user_id: int,
    role: str,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Создаёт базовую структуру запроса."""
    normalized_query = normalize_query(raw_query)

    return {
        "raw_query": raw_query.strip(),
        "normalized_query": normalized_query,
        "tokens": tokenize_query(normalized_query),
        "user_id": user_id,
        "role": role,
        "request_id": request_id,
    }


def enrich_prepared_request(
    prepared_request: Dict[str, Any],
    standalone_query: str,
    contextual_search_query: str,
    language: str,
) -> Dict[str, Any]:
    """
    Добавляет к запросу намерение, формат ответа и отдельную формулировку
    для retrieval.
    """
    classification_query = normalize_query(
        standalone_query
        or prepared_request["raw_query"]
    )

    intent = detect_query_intent(classification_query)

    retrieval_base = (
        contextual_search_query
        or standalone_query
        or prepared_request["raw_query"]
    )

    retrieval_query = build_retrieval_query(
        query=retrieval_base,
        language=language,
        intent=intent,
    )

    standalone_retrieval_query = build_retrieval_query(
        query=(
            standalone_query
            or prepared_request["raw_query"]
        ),
        language=language,
        intent=intent,
    )

    if standalone_retrieval_query not in retrieval_query:
        retrieval_query = (
            f"{standalone_retrieval_query} "
            f"{retrieval_query}"
        ).strip()

    prepared_request.update(
        {
            "language": language,
            "standalone_query": standalone_query,
            "search_query": contextual_search_query,
            "classification_query": classification_query,
            "intent": intent,
            "intent_label": get_intent_label(
                intent,
                language,
            ),
            "response_format": get_response_format(
                intent,
                language,
            ),
            "retrieval_query": retrieval_query,
        }
    )

    return prepared_request