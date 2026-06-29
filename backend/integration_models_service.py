import os
from typing import Dict, Any

import requests
from dotenv import load_dotenv

from backend.rag.embeddings import EmbeddingModel, EMBEDDING_MODEL_NAME


load_dotenv()


def check_embedding_model() -> Dict[str, Any]:
    try:
        embedding_model = EmbeddingModel()

        test_query = "Какие разделы должны быть в пояснительной записке?"
        test_vector = embedding_model.encode_query(test_query)

        return {
            "status": "ok",
            "model_name": EMBEDDING_MODEL_NAME,
            "test_query": test_query,
            "vector_dimension": len(test_vector),
            "message": "Embedding-модель успешно подключена и создаёт вектор запроса"
        }

    except Exception as error:
        return {
            "status": "error",
            "model_name": EMBEDDING_MODEL_NAME,
            "message": str(error)
        }


def check_llm_model() -> Dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "mock")
    api_url = os.getenv("LLM_API_URL", "http://127.0.0.1:11434/api/chat")
    model_name = os.getenv("LLM_MODEL_NAME", "qwen2.5:1.5b")
    timeout = int(os.getenv("LLM_TIMEOUT", "300"))

    if provider != "ollama":
        return {
            "status": "warning",
            "provider": provider,
            "model_name": model_name,
            "message": "Сейчас используется не Ollama. Проверь параметр LLM_PROVIDER в .env"
        }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "Ты проверяешь подключение языковой модели. Отвечай кратко."
            },
            {
                "role": "user",
                "content": "Ответь одним предложением: языковая модель подключена."
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 40
        }
    }

    try:
        response = requests.post(
            api_url,
            json=payload,
            timeout=timeout
        )

        if response.status_code >= 400:
            return {
                "status": "error",
                "provider": "ollama",
                "model_name": model_name,
                "message": f"Ollama вернула ошибку: {response.status_code} {response.text}"
            }

        data = response.json()
        answer = data.get("message", {}).get("content", "").strip()

        return {
            "status": "ok",
            "provider": "ollama",
            "api_url": api_url,
            "model_name": model_name,
            "test_answer": answer,
            "message": "Языковая модель успешно подключена через Ollama"
        }

    except requests.exceptions.ConnectionError as error:
        return {
            "status": "error",
            "provider": "ollama",
            "model_name": model_name,
            "message": "Не удалось подключиться к Ollama. Проверь, что Ollama запущена.",
            "error": str(error)
        }

    except requests.exceptions.ReadTimeout as error:
        return {
            "status": "error",
            "provider": "ollama",
            "model_name": model_name,
            "message": "Ollama не успела ответить за отведённое время.",
            "error": str(error)
        }

    except Exception as error:
        return {
            "status": "error",
            "provider": "ollama",
            "model_name": model_name,
            "message": str(error)
        }


def build_models_integration_status() -> Dict[str, Any]:
    embedding_status = check_embedding_model()
    llm_status = check_llm_model()

    if embedding_status["status"] == "ok" and llm_status["status"] == "ok":
        overall_status = "ok"
        message = "Языковая модель и embedding-модель успешно подключены"
    elif embedding_status["status"] == "error" or llm_status["status"] == "error":
        overall_status = "error"
        message = "Есть ошибка подключения одной из моделей"
    else:
        overall_status = "warning"
        message = "Модели подключены частично, требуется проверка"

    return {
        "overall_status": overall_status,
        "message": message,
        "embedding_model": embedding_status,
        "llm_model": llm_status
    }