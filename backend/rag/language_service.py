import re
from typing import Dict, Any


def detect_language(text: str) -> Dict[str, Any]:
    """
    Определяет язык пользовательского запроса.

    Для прототипа используется простая эвристика:
    - если в тексте преобладают латинские символы, считаем язык английским;
    - иначе считаем язык русским.
    """
    if not text or not text.strip():
        return {
            "language": "ru",
            "display_name": "Русский",
            "confidence": 0.0,
            "reason": "Пустой текст, выбран язык по умолчанию"
        }

    latin_chars = re.findall(r"[a-zA-Z]", text)
    cyrillic_chars = re.findall(r"[а-яА-ЯёЁ]", text)

    latin_count = len(latin_chars)
    cyrillic_count = len(cyrillic_chars)

    if latin_count > cyrillic_count:
        return {
            "language": "en",
            "display_name": "English",
            "confidence": round(latin_count / max(latin_count + cyrillic_count, 1), 2),
            "reason": "В запросе преобладают латинские символы"
        }

    return {
        "language": "ru",
        "display_name": "Русский",
        "confidence": round(cyrillic_count / max(latin_count + cyrillic_count, 1), 2),
        "reason": "В запросе преобладают кириллические символы"
    }


def get_answer_language_instruction(language: str) -> str:
    """
    Возвращает инструкцию для LLM по языку ответа.
    """
    if language == "en":
        return "Answer in English."

    return "Отвечай на русском языке."