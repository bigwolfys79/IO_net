import os
import json
import base64
import requests
from urllib.parse import urlparse
from datetime import datetime
from PIL import Image
import logging
from worker import Worker
from config import (
    SUPPORTED_IMAGE_FORMATS, MAX_FILE_SIZE, MAX_IMAGE_RESOLUTION, MIN_IMAGE_RESOLUTION,
    CHAT_HISTORY_FILE, API_LOGS_DIR, DATE_FORMAT
)

# Инициализация логгера
app_logger = logging.getLogger('app')

def _is_valid_url(url):
    """Проверяет валидность URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def _process_images_task(filepaths):
    """Обрабатывает выбранные изображения в фоновом потоке."""
    results = []
    for filepath in filepaths:
        ext = os.path.splitext(filepath)[1][1:].lower()
        if ext not in SUPPORTED_IMAGE_FORMATS:
            raise ValueError(f"Неподдерживаемый формат: {ext}")
        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"Изображение слишком большое ({file_size//1024//1024} МБ).")
        with Image.open(filepath) as img:
            width, height = img.size
            if width > MAX_IMAGE_RESOLUTION[0] or height > MAX_IMAGE_RESOLUTION[1]:
                raise ValueError(f"Разрешение слишком высокое ({width}x{height}).")
            if width < MIN_IMAGE_RESOLUTION[0] or height < MIN_IMAGE_RESOLUTION[1]:
                raise ValueError(f"Разрешение слишком низкое ({width}x{height}). Минимальное: 512x512.")
        with open(filepath, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        results.append((filepath, encoded_image))
    return results

def _save_chat_history_task(chat_history):
    """Сохраняет историю чата в фоновом потоке."""
    if not CHAT_HISTORY_FILE:
        app_logger.warning("Не указан файл для сохранения истории чата")
        return
    history_file = os.path.abspath(CHAT_HISTORY_FILE)
    history = list(chat_history)
    for msg in history:
        if "timestamp" in msg and not isinstance(msg["timestamp"], str):
            msg["timestamp"] = msg["timestamp"].strftime(DATE_FORMAT)
    os.makedirs(os.path.dirname(history_file) or ".", exist_ok=True)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def _load_models_task(load_chat_models, load_embedding_models):
    """Загружает списки чат- и эмбеддинг-моделей."""
    chat_models = load_chat_models()
    embedding_models = load_embedding_models()
    return (
        [f"[Чат] {model}" for model in chat_models] +
        [f"[Эмбеддинг] {model}" for model in embedding_models]
    )

def _handle_embedding_task(model_id, prompt, api_settings, api_key):
    """Обрабатывает задачу создания эмбеддинга."""
    embeddings_url = f"{api_settings['BASE_URL']}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model_id,
        "input": prompt
    }
    response = requests.post(embeddings_url, headers=headers, json=data, timeout=api_settings['API_REQUEST_TIMEOUT'])
    response.raise_for_status()
    embeddings = response.json()['data'][0]['embedding']
    return {"choices": [{"message": {"content": f"Эмбеддинг: {embeddings[:10]}..."}}]}

def _log_api_request(model_id, data):
    """Логирует API-запрос в файл."""
    os.makedirs(API_LOGS_DIR, exist_ok=True)
    log_file = os.path.join(API_LOGS_DIR, f"api_request_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({"model": model_id, "request": data}, f, ensure_ascii=False, indent=2)

def _log_api_response(response):
    """Логирует API-ответ в файл."""
    os.makedirs(API_LOGS_DIR, exist_ok=True)
    log_file = os.path.join(API_LOGS_DIR, f"api_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=2)