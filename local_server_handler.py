import requests
import os
import logging
import time
from logging_config import configure_logging

# Настраиваем логирование
configure_logging()
server_logger = logging.getLogger('server')

# Константы
LOCAL_SERVER_URL = "http://localhost:5000"
UPLOAD_ENDPOINT = f"{LOCAL_SERVER_URL}/upload"
DELETE_ENDPOINT = f"{LOCAL_SERVER_URL}/delete"
HEALTH_ENDPOINT = f"{LOCAL_SERVER_URL}/health"

class LocalServerHandler:
    """Класс для работы с локальным сервером."""
    
    def __init__(self):
        """Инициализация клиента локального сервера."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                server_logger.debug(f"Попытка {attempt + 1} проверки состояния сервера")
                response = requests.get(HEALTH_ENDPOINT, timeout=5)
                response.raise_for_status()
                server_logger.info("Local server health check successful")
                break
            except requests.RequestException as e:
                if attempt == max_attempts - 1:
                    error_msg = (
                        f"Локальный сервер недоступен по адресу {LOCAL_SERVER_URL}. "
                        f"Убедитесь, что сервер запущен (запустите local_server.py). Ошибка: {str(e)}"
                    )
                    server_logger.error(error_msg)
                    raise ValueError(error_msg)
                server_logger.warning(f"Attempt {attempt + 1} failed to connect to local server, retrying...")
                time.sleep(2)
    
    def upload_image(self, file_path):
        """Загрузка изображения на локальный сервер."""
        try:
            file_name = os.path.basename(file_path)
            server_logger.debug(f"Загрузка изображения: {file_name}")
            with open(file_path, "rb") as image_file:
                files = {"image": (file_name, image_file, "image/jpeg")}
                response = requests.post(
                    UPLOAD_ENDPOINT,
                    files=files,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                image_id = data["image_id"]
                link = data["link"]
                server_logger.info(f"Image uploaded to local server: {file_name}, link: {link}")
                return image_id, link
        except Exception as e:
            server_logger.error(f"Error uploading image to local server: {str(e)}")
            raise
    
    def delete_image(self, image_id):
        """Удаление изображения с локального сервера."""
        try:
            server_logger.debug(f"Удаление изображения: {image_id}")
            response = requests.delete(
                f"{DELETE_ENDPOINT}/{image_id}",
                timeout=10
            )
            response.raise_for_status()
            server_logger.info(f"Image deleted from local server: {image_id}")
        except Exception as e:
            server_logger.error(f"Error deleting image from local server: {str(e)}")
            raise