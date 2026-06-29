import os
import re
from typing import List, Dict

import requests
from dotenv import load_dotenv


load_dotenv()


def clean_llm_answer(answer: str) -> str:
    """
    Удаляет служебные блоки и лишние переносы.
    """
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL)
    answer = re.sub(r"\n{3,}", "\n\n", answer)
    return answer.strip()


def generate_mock_answer(messages: List[Dict[str, str]]) -> str:
    """
    Резервный mock-режим. Используется только если LLM_PROVIDER=mock.
    """
    return (
        "Тестовый ответ mock-генератора. Для полноценной генерации "
        "используйте LLM_PROVIDER=ollama. Источники: [1]."
    )


def generate_ollama_answer(messages: List[Dict[str, str]]) -> str:
    """
    Генерация ответа через локальную LLM Ollama.
    """
    api_url = os.getenv("LLM_API_URL", "http://127.0.0.1:11434/api/chat")
    model_name = os.getenv("LLM_MODEL_NAME", "qwen2.5:1.5b")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    timeout = int(os.getenv("LLM_TIMEOUT", "300"))
    num_ctx = int(os.getenv("LLM_NUM_CTX", "4096"))
    num_predict = int(os.getenv("LLM_NUM_PREDICT", "350"))

    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict
        }
    }

    try:
        response = requests.post(
            api_url,
            json=payload,
            timeout=timeout
        )

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Не удалось подключиться к Ollama. Проверь, что Ollama запущена "
            "и модель скачана командой: ollama pull qwen2.5:1.5b"
        ) from error

    except requests.exceptions.ReadTimeout as error:
        raise RuntimeError(
            "Ollama не успела сформировать ответ за отведённое время. "
            "Используй более лёгкую модель qwen2.5:1.5b, уменьши число найденных чанков "
            "или увеличь LLM_TIMEOUT в .env."
        ) from error

    if response.status_code >= 400:
        raise RuntimeError(
            f"Ошибка Ollama API: {response.status_code} {response.text}"
        )

    data = response.json()

    if "message" not in data or "content" not in data["message"]:
        raise RuntimeError(
            f"Некорректный ответ Ollama API: {data}"
        )

    answer = data["message"]["content"]

    print(f"LLM provider: Ollama | model: {model_name}")

    return clean_llm_answer(answer)


def generate_http_answer(messages: List[Dict[str, str]]) -> str:
    """
    Универсальный режим для внешнего OpenAI-compatible API.
    """
    api_url = os.getenv("LLM_API_URL")
    api_key = os.getenv("LLM_API_KEY")
    model_name = os.getenv("LLM_MODEL_NAME")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    timeout = int(os.getenv("LLM_TIMEOUT", "120"))

    if not api_url:
        raise RuntimeError("Не задан LLM_API_URL в .env")

    if not api_key:
        raise RuntimeError("Не задан LLM_API_KEY в .env")

    if not model_name:
        raise RuntimeError("Не задан LLM_MODEL_NAME в .env")

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        api_url,
        json=payload,
        headers=headers,
        timeout=timeout
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Ошибка LLM API: {response.status_code} {response.text}"
        )

    data = response.json()
    answer = data["choices"][0]["message"]["content"]

    return clean_llm_answer(answer)


def generate_llm_answer(messages: List[Dict[str, str]]) -> str:
    """
    Главная функция генерации ответа.
    """
    provider = os.getenv("LLM_PROVIDER", "mock").lower()

    if provider == "mock":
        return generate_mock_answer(messages)

    if provider == "ollama":
        return generate_ollama_answer(messages)

    if provider == "http":
        return generate_http_answer(messages)

    raise RuntimeError(
        f"Неизвестный LLM_PROVIDER: {provider}. Используй mock, ollama или http."
    )