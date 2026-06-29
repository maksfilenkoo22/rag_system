from pathlib import Path
from typing import Dict, Any
import re


DOCUMENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "metodicheskie_ukazaniya_k_napisaniyu_pz_k_proektnoj_praktike.pdf": {
        "document_id": "methodical_pz_project_practice",
        "document_name": "Методические указания к написанию ПЗ к проектной практике",
        "document_type": "methodical_guidelines",
        "knowledge_category": "pz_requirements",
        "source_scope": "kafedra_22",
        "is_normative": True
    },
    "struct_rspz_uir.docx": {
        "document_id": "struct_rspz_uir",
        "document_name": "Структура расширенного содержания ПЗ к УИР и КП",
        "document_type": "structure",
        "knowledge_category": "rspz_structure",
        "source_scope": "kafedra_22",
        "is_normative": True
    },
    "struct_uir2001.docx": {
        "document_id": "struct_uir2001",
        "document_name": "Структура содержания ПЗ к УИР и КП",
        "document_type": "structure",
        "knowledge_category": "pz_structure",
        "source_scope": "kafedra_22",
        "is_normative": True
    },
    "Производственная практика (научно-исследовательская работа).pdf": {
        "document_id": "production_practice_nir",
        "document_name": "Производственная практика (научно-исследовательская работа)",
        "document_type": "work_program",
        "knowledge_category": "nir_requirements",
        "source_scope": "iiks",
        "is_normative": True
    },
    "Учебно-исследовательская работа (курсовой проект в области программной инженерии интеллектуальных систем).pdf": {
        "document_id": "uir_course_project_intelligent_systems",
        "document_name": "Учебно-исследовательская работа",
        "document_type": "work_program",
        "knowledge_category": "uir_requirements",
        "source_scope": "kafedra_22",
        "is_normative": True
    },
    "ПЗ_НИР_Филенко М.В.docx": {
        "document_id": "example_nir_report_filenko",
        "document_name": "Пример пояснительной записки по НИР",
        "document_type": "example_report",
        "knowledge_category": "nir_example",
        "source_scope": "student_previous_nir",
        "is_normative": False
    },
    "нир преза филенко.pptx": {
        "document_id": "example_nir_presentation_filenko",
        "document_name": "Пример презентации по НИР",
        "document_type": "example_presentation",
        "knowledge_category": "nir_example",
        "source_scope": "student_previous_nir",
        "is_normative": False
    }
}


def make_safe_document_id(file_path: Path) -> str:
    """
    Создаёт безопасный document_id для нового файла.

    Используется для документов, которые не описаны вручную
    в DOCUMENT_REGISTRY.
    """
    raw_name = file_path.stem.lower()

    translit_map = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
        "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
        "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
        "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch",
        "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya"
    }

    transliterated = "".join(
        translit_map.get(char, char)
        for char in raw_name
    )

    safe_id = re.sub(r"[^a-z0-9]+", "_", transliterated)
    safe_id = safe_id.strip("_")

    if not safe_id:
        safe_id = "auto_document"

    return safe_id


def detect_document_type(file_path: Path) -> str:
    """
    Автоматически определяет тип документа по расширению файла.
    """
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return "pdf_document"

    if extension in [".docx", ".doc"]:
        return "word_document"

    if extension in [".pptx", ".ppt"]:
        return "presentation"

    if extension in [".html", ".htm"]:
        return "html_page"

    if extension == ".txt":
        return "text_document"

    return "unknown_document"


def detect_knowledge_category(file_path: Path) -> str:
    """
    Автоматически определяет примерную категорию документа по имени файла.
    """
    file_name = file_path.name.lower()

    if "нир" in file_name or "research" in file_name:
        return "research_work"

    if "уир" in file_name:
        return "study_research_work"

    if "пз" in file_name or "поясн" in file_name:
        return "explanatory_note"

    if "през" in file_name or "presentation" in file_name:
        return "presentation_requirements"

    if "практик" in file_name:
        return "practice"

    if "вкр" in file_name:
        return "final_qualification_work"

    if "test" in file_name or "scalability" in file_name:
        return "scalability_test"

    return "additional_source"


def build_auto_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Создаёт автоматические метаданные для нового документа,
    если он не описан вручную в DOCUMENT_REGISTRY.
    """
    return {
        "document_id": make_safe_document_id(file_path),
        "document_name": file_path.stem,
        "document_type": detect_document_type(file_path),
        "knowledge_category": detect_knowledge_category(file_path),
        "source_scope": "additional_source",
        "is_normative": False,
        "metadata_mode": "auto"
    }


def get_document_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Возвращает метаданные документа.

    Если документ описан в DOCUMENT_REGISTRY, используются ручные метаданные.
    Если документ новый и не описан в registry, метаданные создаются автоматически.
    """
    file_name = file_path.name

    if file_name in DOCUMENT_REGISTRY:
        metadata = DOCUMENT_REGISTRY[file_name].copy()
        metadata["metadata_mode"] = "manual"
    else:
        metadata = build_auto_metadata(file_path)

    if "document_id" not in metadata or not metadata["document_id"]:
        metadata["document_id"] = make_safe_document_id(file_path)

    if "document_name" not in metadata or not metadata["document_name"]:
        metadata["document_name"] = file_path.stem

    if "document_type" not in metadata or not metadata["document_type"]:
        metadata["document_type"] = detect_document_type(file_path)

    if "knowledge_category" not in metadata or not metadata["knowledge_category"]:
        metadata["knowledge_category"] = detect_knowledge_category(file_path)

    if "source_scope" not in metadata or not metadata["source_scope"]:
        metadata["source_scope"] = "additional_source"

    if "is_normative" not in metadata:
        metadata["is_normative"] = False

    metadata["file_name"] = file_name
    metadata["source_type"] = "local_file"
    metadata["source_format"] = file_path.suffix.lower().replace(".", "")
    metadata["source_path"] = str(file_path)

    return metadata