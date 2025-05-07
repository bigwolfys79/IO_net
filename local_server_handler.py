import requests
import os
import logging
# from logging_config import configure_logging

# # Вызываем configure_logging() в начале
# configure_logging()
# # Получаем логгер для сервера
# logging = logging.getLogger('server')

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
                response = requests.get(HEALTH_ENDPOINT, timeout=5)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == max_attempts - 1:
                    raise ValueError(
                        f"Локальный сервер недоступен по адресу {LOCAL_SERVER_URL}. "
                        f"Убедитесь, что сервер запущен (запустите local_server.py). Ошибка: {str(e)}"
                    )
                import time
                time.sleep(2)  # Ждем перед следующей попыткой
    
    def upload_image(self, file_path):
        """Загрузка изображения на локальный сервер."""
        try:
            file_name = os.path.basename(file_path)
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
                logging.info(f"Изображение {file_name} загружено на локальный сервер: {link}")
                return image_id, link
        except Exception as e:
            logging.error(f"Ошибка загрузки изображения на локальный сервер: {str(e)}")
            raise
    
    def delete_image(self, image_id):
        """Удаление изображения с локального сервера."""
        try:
            response = requests.delete(
                f"{DELETE_ENDPOINT}/{image_id}",
                timeout=10
            )
            response.raise_for_status()
            logging.info(f"Изображение с ID {image_id} удалено с локального сервера")
        except Exception as e:
            logging.error(f"Ошибка удаления изображения с локального сервера: {str(e)}")
            raise