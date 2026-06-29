import json
import re
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple


BASE_DIR = Path(__file__).resolve().parents[1]
RULES_PATH = BASE_DIR / "config" / "classifier_rules.json"


PHRASE_SCORE = 14
EXACT_PHRASE_BONUS = 10
TOKEN_SCORE = 1
STEM_SCORE = 2
INTENT_SCORE = 6


def load_classifier_rules() -> Dict[str, Any]:
    with open(
        RULES_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def normalize_for_matching(text: str) -> str:
    text = (text or "").lower().replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize_text(text: str) -> Set[str]:
    normalized_text = normalize_for_matching(text)
    tokens = re.findall(
        r"[а-яa-z0-9]+",
        normalized_text,
    )

    return {
        token
        for token in tokens
        if len(token) > 1
    }


def term_matches(
    term: str,
    normalized_query: str,
    query_tokens: Set[str],
) -> bool:
    """
    Поддерживает:
    - точные слова: "нир";
    - фразы: "структура нир";
    - основы слов: "структур*", "раздел*".
    """
    normalized_term = normalize_for_matching(term)

    if not normalized_term:
        return False

    if normalized_term.endswith("*"):
        prefix = normalized_term[:-1]

        if " " in prefix:
            return prefix in normalized_query

        return any(
            token.startswith(prefix)
            for token in query_tokens
        )

    if " " in normalized_term:
        return normalized_term in normalized_query

    return normalized_term in query_tokens


def groups_match(
    groups: List[List[str]],
    normalized_query: str,
    query_tokens: Set[str],
) -> bool:
    """Каждая группа должна иметь хотя бы одно совпадение."""
    for group in groups:
        if not any(
            term_matches(
                term,
                normalized_query,
                query_tokens,
            )
            for term in group
        ):
            return False

    return True


def excluded_groups_match(
    groups: List[List[str]],
    normalized_query: str,
    query_tokens: Set[str],
) -> bool:
    """
    Возвращает True, если полностью совпала хотя бы одна
    запрещающая группа.
    """
    for group in groups:
        if group and all(
            term_matches(
                term,
                normalized_query,
                query_tokens,
            )
            for term in group
        ):
            return True

    return False


def calculate_rule_score(
    normalized_query: str,
    query_tokens: Set[str],
    intent: str,
    rule: Dict[str, Any],
) -> Tuple[int, Dict[str, Any]]:
    required_groups = rule.get(
        "required_groups",
        [],
    )
    excluded_groups = rule.get(
        "excluded_groups",
        [],
    )

    if required_groups and not groups_match(
        required_groups,
        normalized_query,
        query_tokens,
    ):
        return 0, {
            "matched_phrases": [],
            "matched_tokens": [],
            "matched_stems": [],
            "required_groups_matched": False,
        }

    if excluded_groups and excluded_groups_match(
        excluded_groups,
        normalized_query,
        query_tokens,
    ):
        return 0, {
            "matched_phrases": [],
            "matched_tokens": [],
            "matched_stems": [],
            "required_groups_matched": True,
            "excluded": True,
        }

    score = 0
    matched_phrases: List[str] = []
    matched_tokens: List[str] = []
    matched_stems: List[str] = []

    for phrase in rule.get("phrases", []):
        normalized_phrase = normalize_for_matching(
            phrase
        )

        if (
            normalized_phrase
            and normalized_phrase in normalized_query
        ):
            score += PHRASE_SCORE
            matched_phrases.append(phrase)

            if normalized_phrase == normalized_query:
                score += EXACT_PHRASE_BONUS

    for token in rule.get("tokens", []):
        normalized_token = normalize_for_matching(
            token
        )

        if (
            normalized_token
            and normalized_token in query_tokens
        ):
            score += TOKEN_SCORE
            matched_tokens.append(token)

    for stem in rule.get("stems", []):
        normalized_stem = (
            normalize_for_matching(stem)
            .rstrip("*")
        )

        if normalized_stem and any(
            token.startswith(normalized_stem)
            for token in query_tokens
        ):
            score += STEM_SCORE
            matched_stems.append(stem)

    supported_intents = rule.get(
        "intents",
        [],
    )

    if intent and intent in supported_intents:
        score += INTENT_SCORE

    minimum_score = rule.get(
        "min_rule_score",
        1,
    )

    if score < minimum_score:
        score = 0

    return score, {
        "matched_phrases": matched_phrases,
        "matched_tokens": matched_tokens,
        "matched_stems": matched_stems,
        "required_groups_matched": True,
    }


def build_search_params(
    rule: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "source_filter": rule.get(
            "source_filter",
            [],
        ),
        "document_type_filter": rule.get(
            "document_type_filter",
            [],
        ),
        "knowledge_category_filter": rule.get(
            "knowledge_category_filter",
            [],
        ),
        "is_normative": rule.get("is_normative"),
        "top_k": rule.get("top_k", 5),
        "min_score": rule.get(
            "min_score",
            0.45,
        ),
        "search_multiplier": rule.get(
            "search_multiplier",
            4,
        ),
        "max_chunks_per_document": rule.get(
            "max_chunks_per_document"
        ),
    }


def classify_query(
    prepared_request: Dict[str, Any],
) -> Dict[str, Any]:
    rules = load_classifier_rules()

    query_for_classification = (
        prepared_request.get("classification_query")
        or prepared_request.get("standalone_query")
        or prepared_request.get("normalized_query")
        or prepared_request.get("raw_query", "")
    )

    normalized_query = normalize_for_matching(
        query_for_classification
    )
    query_tokens = tokenize_text(
        normalized_query
    )
    intent = prepared_request.get(
        "intent",
        "question",
    )

    best_class = None
    best_score = 0
    best_priority = -1
    best_details: Dict[str, Any] = {}

    for class_rule in rules["classes"]:
        score, details = calculate_rule_score(
            normalized_query=normalized_query,
            query_tokens=query_tokens,
            intent=intent,
            rule=class_rule,
        )

        priority = class_rule.get(
            "priority",
            0,
        )

        if score > best_score or (
            score == best_score
            and score > 0
            and priority > best_priority
        ):
            best_score = score
            best_priority = priority
            best_class = class_rule
            best_details = details

    if best_class is None or best_score == 0:
        default = rules["default"]

        return {
            "class_name": default["class_name"],
            "display_name": default["display_name"],
            "belongs_to_knowledge_base": False,
            "matched_score": 0,
            "intent": intent,
            "match_details": {},
            "search_params": build_search_params(
                default
            ),
        }

    return {
        "class_name": best_class["class_name"],
        "display_name": best_class["display_name"],
        "belongs_to_knowledge_base": True,
        "matched_score": best_score,
        "intent": intent,
        "match_details": best_details,
        "search_params": build_search_params(
            best_class
        ),
    }