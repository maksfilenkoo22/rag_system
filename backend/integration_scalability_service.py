from typing import Dict, Any


def build_scalability_status() -> Dict[str, Any]:
    """
    Описывает возможности масштабирования и расширения функциональности RAG-системы.
    """

    return {
        "status": "ok",
        "message": "Архитектура поддерживает расширение базы знаний и добавление новых функций",
        "new_data_sources_support": {
            "status": "ok",
            "supported_formats": [
                "PDF",
                "DOCX",
                "PPTX",
                "HTML",
                "TXT"
            ],
            "current_storage": "backend/data/documents",
            "indexing_script": "backend/rag/index_documents.py",
            "vector_storage": "Qdrant collection mephi_rag_knowledge_base",
            "how_to_add_new_source": [
                "Добавить новый документ в каталог backend/data/documents",
                "При необходимости расширить document_loader.py новым обработчиком формата",
                "Запустить повторную индексацию документов",
                "Система извлечёт текст, разобьёт его на чанки, создаст embedding-векторы и сохранит их в Qdrant"
            ],
            "metadata_support": [
                "document_name",
                "file_name",
                "document_type",
                "knowledge_category",
                "chunk_number",
                "is_normative"
            ]
        },
        "modular_architecture": {
            "status": "ok",
            "modules": {
                "auth": "авторизация и проверка JWT-токена",
                "query_preprocessor": "валидация и нормализация пользовательского запроса",
                "classifier": "определение типа запроса и параметров поиска",
                "embeddings": "создание векторного представления запроса и документов",
                "search_service": "поиск релевантных фрагментов в Qdrant",
                "context_filter": "отбор контекста для передачи в LLM",
                "prompt_builder": "формирование prompt для языковой модели",
                "llm_client": "обращение к локальной LLM через Ollama",
                "answer_generator": "формирование итогового ответа и источников",
                "security": "контроль доступа и фильтрация запрещённых запросов"
            },
            "extension_points": {
                "dialog_scenarios": [
                    "добавление истории сообщений пользователя",
                    "хранение session_id или conversation_id",
                    "передача предыдущего контекста в prompt_builder",
                    "реализация уточняющих вопросов"
                ],
                "multilingual_support": [
                    "определение языка пользовательского запроса",
                    "маршрутизация запроса по языку",
                    "использование multilingual embedding-модели",
                    "добавление prompt-шаблонов для разных языков"
                ],
                "new_document_types": [
                    "добавление нового парсера в document_loader.py",
                    "расширение метаданных документа",
                    "повторная индексация базы знаний"
                ],
                "new_security_rules": [
                    "расширение категорий LLM-классификатора безопасности",
                    "добавление новых правил блокировки запросов",
                    "логирование подозрительных запросов"
                ]
            }
        },
        "scalability_result": {
            "knowledge_base_expansion": "новые документы могут быть добавлены без изменения основного RAG-пайплайна",
            "functional_expansion": "новые функции могут подключаться через отдельные модули",
            "technology_expansion": "LLM, embedding-модель и векторное хранилище могут быть заменены через отдельные сервисные модули",
            "conclusion": "модульная структура снижает связность компонентов и упрощает развитие системы"
        }
    }