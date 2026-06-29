import re
from typing import Dict, Any, List, Optional
from collections import defaultdict


_DIALOG_STORAGE: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

MAX_HISTORY_MESSAGES = 6


def get_session_id(
    provided_session_id: Optional[str],
    user_id: Any
) -> str:
    if provided_session_id and provided_session_id.strip():
        return provided_session_id.strip()

    return f"user_{user_id}_default_session"


def get_dialog_history(
    session_id: str,
    max_messages: int = MAX_HISTORY_MESSAGES
) -> List[Dict[str, Any]]:
    history = _DIALOG_STORAGE.get(session_id, [])
    return history[-max_messages:]


def extract_quoted_entity(text: str) -> Optional[str]:
    """
    Достаёт сущность из кавычек.

    Например:
    дисциплина «Теория нейронных сетей» -> Теория нейронных сетей
    """
    if not text:
        return None

    patterns = [
        r"«([^»]+)»",
        r"\"([^\"]+)\"",
        r"'([^']+)'"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return None


def find_last_entity_from_history(history: List[Dict[str, Any]]) -> Optional[str]:
    """
    Ищет последнюю важную сущность из истории диалога.
    """
    for item in reversed(history):
        user_query = item.get("user_query", "")
        assistant_answer = item.get("assistant_answer", "")

        entity = extract_quoted_entity(user_query)
        if entity:
            return entity

        entity = extract_quoted_entity(assistant_answer)
        if entity:
            return entity

    return None


def build_standalone_query(
    current_query: str,
    history: List[Dict[str, Any]]
) -> str:
    """
    Превращает уточняющий вопрос в самостоятельный вопрос.

    Было:
    "А к какой кафедре?"

    Стало:
    "К какой кафедре относится дисциплина «Теория нейронных сетей»?"
    """
    if not history:
        return current_query

    query_lower = current_query.lower().strip()
    entity = find_last_entity_from_history(history)

    if not entity:
        return current_query

    if "кафедр" in query_lower:
        return f"К какой кафедре относится дисциплина «{entity}»?"

    if "институт" in query_lower:
        return f"К какому институту относится дисциплина «{entity}»?"

    if "направлен" in query_lower or "специальност" in query_lower:
        return f"К какому направлению подготовки относится дисциплина «{entity}»?"

    if "код" in query_lower:
        return f"Какой код направления подготовки указан для дисциплины «{entity}»?"

    return f"{current_query} Контекст уточнения: дисциплина «{entity}»."


def build_dialog_context(history: List[Dict[str, Any]]) -> str:
    if not history:
        return ""

    context_parts = []

    for index, item in enumerate(history, start=1):
        user_query = item.get("user_query", "")
        assistant_answer = item.get("assistant_answer", "")

        context_parts.append(
            f"Сообщение {index}\n"
            f"Вопрос пользователя: {user_query}\n"
            f"Ответ системы: {assistant_answer}"
        )

    return "\n\n".join(context_parts)


def build_contextual_search_query(
    current_query: str,
    history: List[Dict[str, Any]]
) -> str:
    """
    Формирует поисковый запрос с учётом истории.
    """
    standalone_query = build_standalone_query(
        current_query=current_query,
        history=history
    )

    if standalone_query != current_query:
        return standalone_query

    if not history:
        return current_query

    previous_user_queries = [
        item.get("user_query", "")
        for item in history[-3:]
        if item.get("user_query")
    ]

    if not previous_user_queries:
        return current_query

    return (
        "Контекст предыдущих вопросов: "
        + " ".join(previous_user_queries)
        + " Текущий вопрос: "
        + current_query
    )


def save_dialog_turn(
    session_id: str,
    user_query: str,
    assistant_answer: str,
    sources: List[Dict[str, Any]],
    language: str,
    request_id: str
) -> None:
    _DIALOG_STORAGE[session_id].append(
        {
            "request_id": request_id,
            "language": language,
            "user_query": user_query,
            "assistant_answer": assistant_answer,
            "sources": sources
        }
    )


def build_dialog_status(
    session_id: str,
    history: List[Dict[str, Any]],
    standalone_query: Optional[str] = None
) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "history_used": len(history) > 0,
        "history_messages_count": len(history),
        "standalone_query": standalone_query
    }


def clear_dialog_history(session_id: str) -> None:
    if session_id in _DIALOG_STORAGE:
        del _DIALOG_STORAGE[session_id]

def filter_history_by_language(
    history: List[Dict[str, Any]],
    language: str
) -> List[Dict[str, Any]]:
    """
    Оставляет в истории только сообщения на том же языке.

    Это нужно, чтобы русская история диалога не влияла на английский вопрос.
    """
    return [
        item for item in history
        if item.get("language") == language
    ]