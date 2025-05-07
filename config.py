import os

# Путь к файлам настроек
API_SETTINGS_FILE = "api_settings.json"
THEME_SETTINGS_FILE = "theme_settings.json"

# Настройки API
BASE_URL = "https://api.intelligence.io.solutions/api/v1"
API_REQUEST_TIMEOUT = 60
TEMPERATURE = 0.7
MAX_COMPLETION_TOKENS = 2000
SEED = 42
SYSTEM_PROMPT = "Ты эксперт в области программирования и анализа изображений. Отвечай коротко, внятно и четко на русском языке. Генерация кода, Отладка кода, Рефакторинг кода, Объяснение кода, Анализ кода"

# Пути к файлам
ENCRYPTED_KEY_FILE = "encrypted_api_key.bin"
ENCRYPTION_KEY_FILE = "encryption_key.bin"
CHAT_HISTORY_FILE = "chat_history.json"
API_LOGS_DIR = "api_logs"

# Модели
VISION_MODELS = [
    "meta-llama/Llama-3.2-90B-Vision-Instruct",
    "Qwen/Qwen2-VL-7B-Instruct"
]

UPLOAD_FOLDER = "uploads"  # Папка для хранения загруженных файлов
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}  # Разрешенные расширения файлов

# Обработка файлов
MAX_FILE_SIZE = 20 * 1024 * 1024
SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "webp", "gif"]
SUPPORTED_FILE_FORMATS = [".py", ".txt", ".json"]
IMAGE_THUMBNAIL_SIZE = (200, 200)
MAX_IMAGE_RESOLUTION = (4096, 4096)
MIN_IMAGE_RESOLUTION = (512, 512)

# Цветовые темы и связанные константы
THEMES = {
    "dark": {
        "background": "#2b2b2b",
        "widget_background": "#424242",
        "border": "#555555",
        "text": "#e0e0e0",
        "error": "#ff5555",
        "selection": "#4a6a92",
        "user_message_background": "#3b4a5a",
        "font_family": "Arial",
        "font_size": 14
    },
    "light": {
        "background": "#f7f3e8",
        "widget_background": "#ffffff",
        "border": "#d3c6b0",
        "text": "#4a4a4a",
        "error": "#d32f2f",
        "selection": "#b0c4de",
        "user_message_background": "#d3e3fd",
        "font_family": "Arial",
        "font_size": 14
    }
}

# Настройки интерфейса
COLORS = THEMES["dark"]
CHAT_HISTORY_MAXLEN = 20
MESSAGE_HEIGHT_RULES = {
    1: 1.5,
    2: 2.5,
    3: 3.5,
    4: 4.5,
    5: 5.5
}
COLLAPSED_MESSAGE_LINES = 5

# Форматы даты и времени
TIMESTAMP_FORMAT = "%H:%M:%S"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
EXPORT_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Подсветка синтаксиса
HIGHLIGHT_RULES = {
    "keywords": r'\b(and|as|assert|break|class|continue|def|del|elif|else|except|exec|finally|for|from|global|if|import|in|is|lambda|not|or|pass|print|raise|return|try|while|with|yield)\b',
    "strings": r'\".*?\"|\'.*?\'',
    "comments": r'#.*$',
    "numbers": r'\b\d+\b'
}

# Логирование программы (OFF отключает логирование)
LOGGING = {
    "level": "OFF",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "filename": "app.log",
    "encoding": "utf-8",
    "mode": "append"  # Режим записи: append (дописывать) или recreate (пересоздавать)
}

# Логирование сервера (OFF отключает логирование)
SERVER_LOGGING = {
    "level": "OFF",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "filename": "server.log",
    "encoding": "utf-8",
    "mode": "append"  # Режим записи: append (дописывать) или recreate (пересоздавать)
}
