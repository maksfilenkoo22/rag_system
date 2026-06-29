import re


def clean_text(text: str) -> str:
    """
    Очищает текст после извлечения из PDF / DOCX / PPTX.
    Особенно важно для презентаций, где могут появляться мусорные строки.
    """
    text = text.replace("\xa0", " ")
    text = text.replace("\uf0be", "-")
    text = text.replace("\u200b", "")

    # Убираем длинные бинарные декоративные строки из презентации.
    text = re.sub(r"\b[01]{20,}\b", " ", text)

    # Убираем повторяющиеся служебные футеры.
    text = re.sub(r"www\.kaf22\.ru", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"www\.mephi\.ru", " ", text, flags=re.IGNORECASE)

    # Нормализуем переносы и пробелы.
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()