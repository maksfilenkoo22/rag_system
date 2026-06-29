from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from backend.auth.auth_service import (
    authenticate_user,
    check_access_by_token,
)

from backend.integration_models_service import (
    build_models_integration_status,
)
from backend.integration_qdrant_service import (
    build_qdrant_integration_status,
)
from backend.integration_api_service import (
    build_api_integration_status,
)
from backend.integration_scalability_service import (
    build_scalability_status,
)

from backend.security.content_filter import (
    check_forbidden_content,
)
from backend.security.security_service import (
    build_security_status,
)

from backend.rag.query_preprocessor import (
    validate_query,
    build_prepared_request,
    enrich_prepared_request,
)
from backend.rag.classifier import classify_query
from backend.rag.search_service import (
    search_relevant_chunks,
)
from backend.rag.answer_generator import (
    generate_answer,
)

from backend.rag.language_service import (
    detect_language,
)
from backend.rag.dialog_manager import (
    get_session_id,
    get_dialog_history,
    filter_history_by_language,
    build_dialog_context,
    build_contextual_search_query,
    build_standalone_query,
    save_dialog_turn,
    build_dialog_status,
)


app = FastAPI(
    title="RAG University Assistant",
    description=(
        "Прототип RAG-системы для поддержки пользователей "
        "по документам НИР, УИР, ПЗ и защиты"
    ),
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security = HTTPBearer()


class LoginRequest(BaseModel):
    email: str
    password: str


class AskRequest(BaseModel):
    query: str
    request_id: Optional[str] = None
    session_id: Optional[str] = None


def normalize_text(text: str) -> str:
    return (
        (text or "")
        .lower()
        .replace("ё", "е")
    )


def is_supported_rag_domain_query(
    query: str,
) -> bool:
    """
    Проверяет, относится ли запрос к предметной области RAG-системы.

    Если запрос явно не относится к базе знаний, система не должна
    запускать общий поиск по Qdrant и возвращать случайные источники.
    """
    normalized_query = normalize_text(query)

    domain_keywords = [
        "пояснительная записка",
        "пз",
        "нир",
        "уир",
        "отчет",
        "отчёт",
        "введение",
        "заключение",
        "раздел",
        "структура",
        "оформление",
        "источники",
        "литература",
        "презентация",
        "слайды",
        "кафедра",
        "институт",
        "направление подготовки",
        "теория нейронных сетей",
        "дисциплина",
        "документы",
        "практика",
        "neural networks",
        "neural networks course",
        "nir",
        "research work",
        "research report",
        "explanatory report",
        "report structure",
        "report sections",
        "presentation structure",
        "institute",
        "department",
        "software engineering",
        "cybernetics",
        "mephi",
    ]

    return any(
        keyword in normalized_query
        for keyword in domain_keywords
    )


def get_not_found_answer(
    language: str,
) -> str:
    if language == "en":
        return (
            "The information was not found "
            "in the knowledge base."
        )

    return (
        "Информация не найдена "
        "в базе знаний."
    )


@app.get("/")
def root():
    return {
        "message": (
            "RAG system backend is running"
        )
    }


@app.get("/integration/models")
def integration_models():
    return build_models_integration_status()


@app.get("/integration/qdrant")
def integration_qdrant():
    return build_qdrant_integration_status()


@app.get("/integration/api")
def integration_api():
    return build_api_integration_status()


@app.get("/integration/security")
def integration_security():
    return build_security_status()


@app.get("/integration/scalability")
def integration_scalability():
    return build_scalability_status()


@app.post("/login")
def login(
    request: LoginRequest,
):
    auth_result = authenticate_user(
        email=request.email,
        password=request.password,
    )

    if not auth_result["success"]:
        raise HTTPException(
            status_code=401,
            detail=auth_result["error"],
        )

    return auth_result


@app.post("/ask")
def ask(
    request: AskRequest,
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
):
    token = credentials.credentials

    access_result = check_access_by_token(
        token
    )

    if (
        access_result["access_status"]
        != "allowed"
    ):
        raise HTTPException(
            status_code=401,
            detail=access_result["error"],
        )

    validation_error = validate_query(
        request.query
    )

    if validation_error is not None:
        raise HTTPException(
            status_code=400,
            detail=validation_error,
        )

    content_check = check_forbidden_content(
        request.query
    )

    if not content_check["allowed"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    content_check["message"]
                ),
                "category": (
                    content_check["category"]
                ),
                "reason": content_check.get(
                    "reason"
                ),
            },
        )

    language_result = detect_language(
        request.query
    )

    session_id = get_session_id(
        provided_session_id=(
            request.session_id
        ),
        user_id=access_result["user_id"],
    )

    full_dialog_history = (
        get_dialog_history(
            session_id=session_id
        )
    )

    dialog_history = (
        filter_history_by_language(
            history=full_dialog_history,
            language=(
                language_result["language"]
            ),
        )
    )

    dialog_context = (
        build_dialog_context(
            history=dialog_history
        )
    )

    standalone_query = (
        build_standalone_query(
            current_query=request.query,
            history=dialog_history,
        )
    )

    contextual_search_query = (
        build_contextual_search_query(
            current_query=request.query,
            history=dialog_history,
        )
    )

    prepared_request = (
        build_prepared_request(
            raw_query=request.query,
            user_id=(
                access_result["user_id"]
            ),
            role=access_result["role"],
            request_id=request.request_id,
        )
    )

    prepared_request[
        "language_info"
    ] = language_result

    prepared_request[
        "session_id"
    ] = session_id

    prepared_request[
        "dialog_context"
    ] = dialog_context

    enrich_prepared_request(
        prepared_request=prepared_request,
        standalone_query=standalone_query,
        contextual_search_query=(
            contextual_search_query
        ),
        language=(
            language_result["language"]
        ),
    )

    classification_result = (
        classify_query(
            prepared_request
        )
    )

    prepared_request[
        "classification"
    ] = classification_result

    domain_supported = (
        is_supported_rag_domain_query(
            contextual_search_query
        )
    )

    if not classification_result[
        "belongs_to_knowledge_base"
    ]:
        if not domain_supported:
            answer = get_not_found_answer(
                language=(
                    language_result[
                        "language"
                    ]
                )
            )

            save_dialog_turn(
                session_id=session_id,
                user_query=request.query,
                assistant_answer=answer,
                sources=[],
                language=(
                    language_result[
                        "language"
                    ]
                ),
                request_id=(
                    prepared_request.get(
                        "request_id"
                    )
                ),
            )

            return {
                "answer": answer,
                "sources": [],
                "request_id": (
                    prepared_request.get(
                        "request_id"
                    )
                ),
                "classification": {
                    "class_name": (
                        classification_result.get(
                            "class_name",
                            (
                                "outside_"
                                "knowledge_base"
                            ),
                        )
                    ),
                    "display_name": (
                        classification_result.get(
                            "display_name",
                            "Вне базы знаний",
                        )
                    ),
                    "matched_score": (
                        classification_result.get(
                            "matched_score"
                        )
                    ),
                    "intent": (
                        prepared_request.get(
                            "intent"
                        )
                    ),
                },
                "search": {
                    "found": False,
                    "message": (
                        "Запрос не относится "
                        "к базе знаний."
                    ),
                    "chunks_count": 0,
                    "retrieval_query": (
                        prepared_request.get(
                            "retrieval_query"
                        )
                    ),
                },
                "language": {
                    "language": (
                        language_result[
                            "language"
                        ]
                    ),
                    "display_name": (
                        language_result[
                            "display_name"
                        ]
                    ),
                    "confidence": (
                        language_result[
                            "confidence"
                        ]
                    ),
                    "reason": (
                        language_result[
                            "reason"
                        ]
                    ),
                },
                "dialog": (
                    build_dialog_status(
                        session_id=session_id,
                        history=dialog_history,
                        standalone_query=(
                            standalone_query
                        ),
                    )
                ),
            }

        classification_result = {
            "class_name": (
                "general_knowledge_base_search"
            ),
            "display_name": (
                "Общий поиск по базе знаний"
            ),
            "belongs_to_knowledge_base": True,
            "matched_score": 0,
            "intent": (
                prepared_request.get(
                    "intent"
                )
            ),
            "search_params": {
                "top_k": 8,
                "min_score": 0.15,
                "search_multiplier": 4,
                "max_chunks_per_document": 3,
                "document_type_filter": [],
                "knowledge_category_filter": [],
                "source_filter": [],
                "is_normative": None,
            },
        }

    prepared_request[
        "classification"
    ] = classification_result

    search_result = (
        search_relevant_chunks(
            prepared_request=(
                prepared_request
            ),
            classification_result=(
                classification_result
            ),
        )
    )

    answer_result = generate_answer(
        prepared_request=prepared_request,
        search_result=search_result,
    )

    save_dialog_turn(
        session_id=session_id,
        user_query=request.query,
        assistant_answer=(
            answer_result["answer"]
        ),
        sources=answer_result["sources"],
        language=(
            language_result["language"]
        ),
        request_id=(
            answer_result["request_id"]
        ),
    )

    return {
        "answer": (
            answer_result["answer"]
        ),
        "sources": (
            answer_result["sources"]
        ),
        "request_id": (
            answer_result["request_id"]
        ),
        "classification": {
            "class_name": (
                classification_result[
                    "class_name"
                ]
            ),
            "display_name": (
                classification_result[
                    "display_name"
                ]
            ),
            "matched_score": (
                classification_result.get(
                    "matched_score"
                )
            ),
            "intent": (
                prepared_request.get(
                    "intent"
                )
            ),
        },
        "search": {
            "found": search_result["found"],
            "message": (
                search_result["message"]
            ),
            "chunks_count": len(
                search_result["chunks"]
            ),
            "retrieval_query": (
                search_result.get(
                    "retrieval_query",
                    prepared_request.get(
                        "retrieval_query"
                    ),
                )
            ),
        },
        "language": {
            "language": (
                language_result["language"]
            ),
            "display_name": (
                language_result[
                    "display_name"
                ]
            ),
            "confidence": (
                language_result[
                    "confidence"
                ]
            ),
            "reason": (
                language_result["reason"]
            ),
        },
        "dialog": build_dialog_status(
            session_id=session_id,
            history=dialog_history,
            standalone_query=standalone_query,
        ),
    }