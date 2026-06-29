from typing import Dict, Any


def build_api_integration_status() -> Dict[str, Any]:
    """
    Описывает реализацию API и фактический маршрут передачи данных
    между React-интерфейсом, FastAPI backend и внутренними модулями RAG-системы.
    """

    return {
        "status": "ok",
        "message": "API для обмена данными между frontend и backend реализовано",
        "important_note": (
            "HTTP API используется для обмена данными между React и FastAPI. "
            "Внутри backend модули взаимодействуют через вызовы Python-функций."
        ),
        "frontend_backend_api": {
            "POST /login": {
                "description": "Авторизация пользователя и получение JWT-токена",
                "frontend_sends": {
                    "email": "student@test.local",
                    "password": "student123"
                },
                "backend_calls": [
                    "authenticate_user(email, password)",
                    "users_repository.get_user_by_email(email)",
                    "verify_password(password, password_hash)",
                    "create_access_token(user)"
                ],
                "backend_returns_to_frontend": {
                    "success": True,
                    "access_token": "JWT-token",
                    "token_type": "bearer",
                    "user": {
                        "user_id": 1,
                        "email": "student@test.local",
                        "role": "student"
                    }
                },
                "frontend_action_after_response": (
                    "React сохраняет access_token и использует его "
                    "в заголовке Authorization при запросе /ask"
                )
            },
            "POST /ask": {
                "description": "Обработка пользовательского вопроса через RAG-пайплайн",
                "frontend_sends_headers": {
                    "Authorization": "Bearer JWT-token",
                    "Content-Type": "application/json"
                },
                "frontend_sends_body": {
                    "query": "Какие разделы должны быть в пояснительной записке?",
                    "request_id": "req_001"
                },
                "backend_returns_to_frontend": {
                    "answer": "Итоговый ответ LLM на основе найденного контекста",
                    "sources": [
                        {
                            "source_id": 1,
                            "document_name": "Название документа",
                            "file_name": "Имя файла",
                            "chunk_number": 1,
                            "score": 0.8,
                            "is_normative": True
                        }
                    ],
                    "request_id": "req_001",
                    "classification": {
                        "class_name": "pz_structure",
                        "display_name": "Структура ПЗ",
                        "matched_score": 10
                    },
                    "search": {
                        "found": True,
                        "message": "Релевантные фрагменты найдены.",
                        "chunks_count": 5
                    }
                }
            }
        },
        "ask_internal_data_flow": [
            {
                "step": 1,
                "module": "FastAPI endpoint /ask",
                "input": {
                    "query": "текст вопроса пользователя",
                    "request_id": "идентификатор запроса",
                    "Authorization": "JWT-токен"
                },
                "output": "передача токена в модуль авторизации"
            },
            {
                "step": 2,
                "module": "auth_service.check_access_by_token",
                "input": {
                    "token": "JWT-токен"
                },
                "output": {
                    "access_status": "allowed",
                    "user_id": 1,
                    "role": "student"
                }
            },
            {
                "step": 3,
                "module": "query_preprocessor.build_prepared_request",
                "input": {
                    "raw_query": "исходный вопрос пользователя",
                    "user_id": 1,
                    "role": "student",
                    "request_id": "req_001"
                },
                "output": {
                    "raw_query": "Какие разделы должны быть в пояснительной записке?",
                    "normalized_query": "какие разделы должны быть в пояснительной записке?",
                    "tokens": ["какие", "разделы", "должны", "быть", "пояснительной", "записке"],
                    "user_id": 1,
                    "role": "student",
                    "request_id": "req_001"
                }
            },
            {
                "step": 4,
                "module": "classifier.classify_query",
                "input": {
                    "normalized_query": "нормализованный вопрос",
                    "tokens": "токены вопроса"
                },
                "output": {
                    "class_name": "pz_structure",
                    "display_name": "Структура ПЗ",
                    "belongs_to_knowledge_base": True,
                    "search_params": {
                        "source_filter": "список допустимых источников",
                        "top_k": 5,
                        "min_score": 0.45
                    }
                }
            },
            {
                "step": 5,
                "module": "embeddings.EmbeddingModel",
                "input": {
                    "query": "нормализованный вопрос пользователя"
                },
                "output": {
                    "query_vector": "embedding-вектор размерности 384"
                }
            },
            {
                "step": 6,
                "module": "search_service.search_relevant_chunks",
                "input": {
                    "query_vector": "embedding-вектор запроса",
                    "search_params": "параметры поиска из классификатора"
                },
                "output": {
                    "found": True,
                    "chunks": "список релевантных фрагментов из Qdrant",
                    "message": "Релевантные фрагменты найдены."
                }
            },
            {
                "step": 7,
                "module": "context_filter",
                "input": {
                    "chunks": "найденные фрагменты документов"
                },
                "output": {
                    "filtered_chunks": "отобранные фрагменты для передачи в LLM",
                    "sources": "список источников для ответа"
                }
            },
            {
                "step": 8,
                "module": "prompt_builder.build_rag_messages",
                "input": {
                    "user_query": "исходный вопрос пользователя",
                    "context": "отобранные фрагменты базы знаний",
                    "sources": "список источников"
                },
                "output": {
                    "messages": "system и user сообщения для LLM"
                }
            },
            {
                "step": 9,
                "module": "llm_client.generate_llm_answer",
                "input": {
                    "messages": "prompt с вопросом, контекстом и источниками"
                },
                "external_call": {
                    "provider": "Ollama",
                    "url": "http://127.0.0.1:11434/api/chat",
                    "model": "qwen2.5:1.5b"
                },
                "output": {
                    "answer": "сгенерированный ответ языковой модели"
                }
            },
            {
                "step": 10,
                "module": "answer_generator.generate_answer",
                "input": {
                    "answer": "ответ LLM",
                    "sources": "источники",
                    "request_id": "идентификатор запроса"
                },
                "output": {
                    "answer_result": {
                        "answer": "итоговый ответ",
                        "sources": "список источников",
                        "request_id": "req_001"
                    }
                }
            },
            {
                "step": 11,
                "module": "FastAPI endpoint /ask",
                "input": {
                    "answer_result": "результат генерации",
                    "classification_result": "результат классификации",
                    "search_result": "результат поиска"
                },
                "output_to_frontend": {
                    "answer": "итоговый ответ",
                    "sources": "источники",
                    "classification": "класс запроса",
                    "search": "статус поиска",
                    "request_id": "req_001"
                }
            }
        ],
        "summary": {
            "api_level": (
                "На уровне API данные передаются между React и FastAPI "
                "в формате JSON по endpoint /login и /ask."
            ),
            "backend_level": (
                "Внутри backend данные последовательно передаются между Python-модулями: "
                "авторизация, предобработка, классификация, векторизация, поиск, "
                "фильтрация контекста, LLM и формирование ответа."
            ),
            "external_services": (
                "FastAPI обращается к Qdrant для поиска фрагментов и к Ollama API "
                "для генерации ответа языковой моделью."
            )
        }
    }