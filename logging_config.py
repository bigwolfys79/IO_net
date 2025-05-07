import os
import json
import logging
from config import LOGGING, SERVER_LOGGING 

def configure_logging():
    """Настраивает систему логирования на основе конфигурации из JSON или config."""
    global LOGGING, SERVER_LOGGING
    logging_settings_file = "logging_settings.json"

    # Проверяем наличие JSON-файла с настройками логирования
    if os.path.exists(logging_settings_file):
        try:
            with open(logging_settings_file, "r", encoding="utf-8") as f:
                logging_config = json.load(f)
            # Проверяем наличие и тип ключей
            if not isinstance(logging_config, dict):
                raise ValueError("Файл logging_settings.json должен содержать словарь")
            if "LOGGING" not in logging_config or not isinstance(logging_config["LOGGING"], dict):
                raise ValueError("Ключ 'LOGGING' отсутствует или не является словарем")
            if "SERVER_LOGGING" not in logging_config or not isinstance(logging_config["SERVER_LOGGING"], dict):
                raise ValueError("Ключ 'SERVER_LOGGING' отсутствует или не является словарем")

            # Обновляем глобальные переменные
            LOGGING.clear()
            LOGGING.update(logging_config["LOGGING"])
            SERVER_LOGGING.clear()
            SERVER_LOGGING.update(logging_config["SERVER_LOGGING"])
            print(f"Настройки логирования успешно загружены из {logging_settings_file}: LOGGING={LOGGING}, SERVER_LOGGING={SERVER_LOGGING}")
        except Exception as e:
            print(f"Ошибка загрузки настроек логирования из {logging_settings_file}: {str(e)}")
            logging.getLogger('app').error(f"Ошибка загрузки настроек логирования: {str(e)}")
    else:
        print(f"Файл {logging_settings_file} не найден, используются настройки по умолчанию")

    # Настраиваем логирование для приложения (app.log)
    if LOGGING["level"] != "OFF":
        file_mode = 'w' if LOGGING.get("mode", "recreate") == "recreate" else 'a'
        app_handler = logging.FileHandler(LOGGING["filename"], mode=file_mode, encoding=LOGGING["encoding"])
        app_handler.setFormatter(logging.Formatter(LOGGING["format"]))
        app_logger = logging.getLogger('app')
        app_logger.setLevel(getattr(logging, LOGGING["level"]))
        app_logger.handlers = [app_handler, logging.StreamHandler()]
    else:
        logging.getLogger('app').handlers = []
        logging.getLogger('app').setLevel(logging.CRITICAL + 1)

    # Настраиваем логирование для сервера (server.log)
    if SERVER_LOGGING["level"] != "OFF":
        file_mode = 'w' if SERVER_LOGGING.get("mode", "recreate") == "recreate" else 'a'
        server_handler = logging.FileHandler(SERVER_LOGGING["filename"], mode=file_mode, encoding=SERVER_LOGGING["encoding"])
        server_handler.setFormatter(logging.Formatter(SERVER_LOGGING["format"]))
        server_logger = logging.getLogger('server')
        server_logger.setLevel(getattr(logging, SERVER_LOGGING["level"]))
        server_logger.handlers = [server_handler, logging.StreamHandler()]
    else:
        logging.getLogger('server').handlers = []
        logging.getLogger('server').setLevel(logging.CRITICAL + 1)

def save_logging_config():
    """Сохраняет конфигурацию логирования в JSON-файл."""
    try:
        logging_settings_file = "logging_settings.json"
        os.makedirs(os.path.dirname(logging_settings_file) or ".", exist_ok=True)
        with open(logging_settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "LOGGING": LOGGING,
                "SERVER_LOGGING": SERVER_LOGGING
            }, f, ensure_ascii=False, indent=2)
        if LOGGING["level"] != "OFF":
            logging.info("Конфигурация логирования сохранена в logging_settings.json")
    except Exception as e:
        if LOGGING["level"] != "OFF":
            logging.error(f"Ошибка сохранения конфигурации логирования: {str(e)}")
        raise