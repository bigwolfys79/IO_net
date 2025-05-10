import os
import time
import json
import requests
import uuid
import subprocess
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QTextEdit, QLineEdit, QScrollArea,
    QMenu, QFileDialog, QMessageBox, QDialog, QFormLayout, QRadioButton, QFontComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QShortcut, QKeySequence, QAction
from pygments.lexers import PythonLexer
from dotenv import load_dotenv
from collections import deque
from datetime import datetime
import base64
from PIL import Image
from urllib.parse import urlparse
import logging
from cryptography.fernet import Fernet
from local_server_handler import LocalServerHandler
from config import (
    API_SETTINGS_FILE, THEME_SETTINGS_FILE, THEMES, LOGGING, SERVER_LOGGING, 
    BASE_URL, API_REQUEST_TIMEOUT, TEMPERATURE, MAX_COMPLETION_TOKENS, SEED, SYSTEM_PROMPT,
    CHAT_HISTORY_FILE, API_LOGS_DIR, MAX_FILE_SIZE, MIN_IMAGE_RESOLUTION, SUPPORTED_IMAGE_FORMATS, SUPPORTED_FILE_FORMATS, MAX_IMAGE_RESOLUTION,
    VISION_MODELS, COLORS, CHAT_HISTORY_MAXLEN, DATE_FORMAT, EXPORT_TIMESTAMP_FORMAT, MESSAGES_PER_PAGE
)
from encrypt import save_api_key, load_api_key
from text_editors import NonScrollableTextEdit, EnterKeyTextEdit, SyntaxHighlighter
from chat_message import ChatMessage
from worker import Worker, WorkerSignals
from logging_config import configure_logging, save_logging_config
from utils import _is_valid_url, _process_images_task, _save_chat_history_task, _load_models_task, _handle_embedding_task, _log_api_request, _log_api_response
from ui import setup_ui, setup_clipboard, prompt_for_api_key, prompt_for_api_settings, prompt_for_theme, prompt_for_font_settings, prompt_for_logging_settings

load_dotenv()
configure_logging()

# Инициализация логгеров
app_logger = logging.getLogger('app')
server_logger = logging.getLogger('server')

class Application(QMainWindow):
    """Основной класс приложения для взаимодействия с AI-моделями."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Взаимодействие с AI-моделями")
        self.setGeometry(100, 100, 900, 700)
        self.chat_history = deque(maxlen=CHAT_HISTORY_MAXLEN)
        self.image_path = None
        self.image_base64 = None
        self.api_key = load_api_key()
        self.pending_messages = []
        self.workers = []
        self.current_theme = "dark"
        self.local_server = None
        self.uploaded_image_ids = []
        self.server_process = None
        self.api_settings = {
            "BASE_URL": BASE_URL,
            "API_REQUEST_TIMEOUT": API_REQUEST_TIMEOUT,
            "TEMPERATURE": TEMPERATURE,
            "MAX_COMPLETION_TOKENS": MAX_COMPLETION_TOKENS,
            "SEED": SEED,
            "SYSTEM_PROMPT": SYSTEM_PROMPT
        }
        self.load_api_settings()
        self.load_theme_settings()
        self.status_label = QLabel("Готов к работе")
        self.start_local_server()
        self.setup_ui()
        self.setup_signals()
        setup_clipboard(self)
        self.load_chat_history()
        if not self.api_key:
            prompt_for_api_key(self)
        try:
            self.local_server = LocalServerHandler()
            self.status_label.setText("Локальный сервер подключен")
        except Exception as e:
            app_logger.error(f"Ошибка инициализации локального сервера: {str(e)}")
            self.status_label.setText("Ошибка инициализации локального сервера")

    def start_local_server(self):
        """Запускает локальный сервер."""
        try:
            server_path = os.path.join(os.path.dirname(__file__), "local_server.py")
            if not os.path.exists(server_path):
                raise FileNotFoundError("Файл local_server.py не найден")
            python_executable = sys.executable
            self.server_process = subprocess.Popen(
                [python_executable, server_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
            server_logger.info(f"Локальный сервер запущен с PID: {self.server_process.pid}")
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    response = requests.get("http://localhost:5000/health", timeout=2)
                    response.raise_for_status()
                    server_logger.info("Локальный сервер успешно запущен")
                    break
                except requests.RequestException:
                    if attempt == max_attempts - 1:
                        stdout, stderr = self.server_process.communicate()
                        raise RuntimeError(f"Не удалось запустить локальный сервер: {stderr.decode('utf-8')}")
                    time.sleep(2)
        except Exception as e:
            server_logger.error(f"Ошибка запуска локального сервера: {str(e)}")
            self.status_label.setText("Ошибка запуска локального сервера")

    def restart_server(self):
        """Перезапускает локальный сервер."""
        try:
            if self.server_process and self.server_process.poll() is None:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                server_logger.info("Локальный сервер остановлен для перезапуска")
            self.start_local_server()
        except Exception as e:
            server_logger.error(f"Ошибка перезапуска сервера: {str(e)}")
            self.status_label.setText("Ошибка перезапуска сервера")

    def closeEvent(self, event):
        """Обрабатывает закрытие приложения, завершая локальный сервер."""
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                server_logger.info("Локальный сервер успешно завершен")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                server_logger.warning("Локальный сервер принудительно завершен")
        super().closeEvent(event)

    def load_api_settings(self):
        """Загружает настройки API из файла."""
        try:
            if os.path.exists(API_SETTINGS_FILE):
                with open(API_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                for key in self.api_settings:
                    if key in loaded_settings:
                        if key == "API_REQUEST_TIMEOUT":
                            if isinstance(loaded_settings[key], int) and loaded_settings[key] > 0:
                                self.api_settings[key] = loaded_settings[key]
                        elif key == "TEMPERATURE":
                            if isinstance(loaded_settings[key], (int, float)) and 0 <= loaded_settings[key] <= 2:
                                self.api_settings[key] = float(loaded_settings[key])
                        elif key == "MAX_COMPLETION_TOKENS":
                            if isinstance(loaded_settings[key], int) and loaded_settings[key] > 0:
                                self.api_settings[key] = loaded_settings[key]
                        elif key == "SEED":
                            if isinstance(loaded_settings[key], int):
                                self.api_settings[key] = loaded_settings[key]
                        elif key in ["BASE_URL", "SYSTEM_PROMPT"]:
                            if isinstance(loaded_settings[key], str) and loaded_settings[key].strip():
                                self.api_settings[key] = loaded_settings[key]
                app_logger.info("Настройки API успешно загружены")
            else:
                app_logger.info("Файл настроек API не найден, используются значения по умолчанию")
        except Exception as e:
            app_logger.error(f"Ошибка загрузки настроек API: {str(e)}")

    def save_api_settings(self):
        """Сохраняет настройки API в файл."""
        try:
            os.makedirs(os.path.dirname(API_SETTINGS_FILE) or ".", exist_ok=True)
            with open(API_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.api_settings, f, ensure_ascii=False, indent=2)
            app_logger.info("Настройки API успешно сохранены")
        except Exception as e:
            app_logger.error(f"Ошибка сохранения настроек API: {str(e)}")

    def load_theme_settings(self):
        """Загружает настройки темы из файла."""
        try:
            if os.path.exists(THEME_SETTINGS_FILE):
                with open(THEME_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    theme = settings.get("theme", "dark")
                    if theme in THEMES:
                        self.current_theme = theme
                        global COLORS
                        COLORS = THEMES[theme].copy()
                        if "font_family" in settings and settings["font_family"]:
                            COLORS["font_family"] = settings["font_family"]
                        if "font_size" in settings and isinstance(settings["font_size"], int) and 8 <= settings["font_size"] <= 24:
                            COLORS["font_size"] = settings["font_size"]
                        app_logger.info(f"Тема '{theme}' загружена с шрифтом {COLORS['font_family']} {COLORS['font_size']}pt")
                    else:
                        app_logger.warning(f"Тема '{theme}' не найдена, используется 'dark'")
            else:
                app_logger.info("Файл настроек темы не найден, используется тема по умолчанию")
        except Exception as e:
            app_logger.error(f"Ошибка загрузки настроек темы: {str(e)}")

    def save_theme_settings(self):
        """Сохраняет настройки темы в файл."""
        try:
            os.makedirs(os.path.dirname(THEME_SETTINGS_FILE) or ".", exist_ok=True)
            with open(THEME_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "theme": self.current_theme,
                    "font_family": COLORS["font_family"],
                    "font_size": COLORS["font_size"]
                }, f, ensure_ascii=False, indent=2)
            app_logger.info("Настройки темы сохранены")
        except Exception as e:
            app_logger.error(f"Ошибка сохранения настроек темы: {str(e)}")

    def save_logging_config(self):
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
                app_logger.info("Конфигурация логирования сохранена в logging_settings.json")
        except Exception as e:
            if LOGGING["level"] != "OFF":
                app_logger.error(f"Ошибка сохранения конфигурации логирования: {str(e)}")
            raise
    
    def showEvent(self, event):
        """Обрабатывает событие отображения окна."""
        super().showEvent(event)
        QTimer.singleShot(0, self.process_pending_messages)

    def process_pending_messages(self):
        app_logger.debug(f"Обработка {len(self.pending_messages)} отложенных сообщений")
        for content, is_user, timestamp, image_path, image_url in self.pending_messages:
            app_logger.debug(f"Добавление отложенного сообщения: '{content}'")
            self.add_message_to_chat(content, is_user, timestamp, image_path, image_url)
        self.pending_messages.clear()
        app_logger.debug("pending_messages очищен")
        if self.chat_history:
            self.status_label.setText(f"Загружено {len(self.chat_history)} сообщений")

    def cleanup_worker(self, worker):
        """Очищает завершенный фоновый поток."""
        if worker in self.workers:
            self.workers.remove(worker)
            worker.deleteLater()

    def setup_signals(self):
        """Настраивает сигналы для фоновых задач."""
        self.signals = WorkerSignals()
        self.signals.add_message.connect(self.add_message_to_chat)
        self.signals.update_status.connect(self.status_label.setText)
        self.signals.error.connect(self.handle_error_signal)

    def handle_error_signal(self, error_msg):
        """Обрабатывает сигнал ошибки."""
        self._handle_error(error_msg, show_message=True)

    def setup_ui(self):
        """Настраивает пользовательский интерфейс приложения."""
        setup_ui(self)
        self.load_models()   

    def copy_text(self):
        """Копирует выделенный текст или текст выбранного сообщения в буфер обмена."""
        for child in self.messages_widget.children():
            if isinstance(child, ChatMessage):
                if child.message_text.textCursor().hasSelection():
                    selected_text = child.message_text.textCursor().selectedText()
                    QApplication.clipboard().setText(selected_text)
                    self.status_label.setText("Текст скопирован")
                    app_logger.debug(f"Скопирован выделенный текст: {selected_text[:50]}...")
                    return
        selected_msg = next(
            (child for child in self.messages_widget.children() if isinstance(child, ChatMessage) and child.is_selected),
            None
        )
        if selected_msg:
            text = selected_msg.message_text.toPlainText()
            QApplication.clipboard().setText(text)
            self.status_label.setText("Текст скопирован")
            app_logger.debug(f"Скопирован текст сообщения: {text[:50]}...")
        else:
            app_logger.debug("Копирование: нет выделенного текста или сообщения")

    def paste_text(self):
        """Вставляет текст из буфера обмена в активное поле ввода."""
        widget = QApplication.focusWidget()
        if isinstance(widget, (QTextEdit, QLineEdit)):
            text = QApplication.clipboard().text()
            if text:
                widget.insert(text if isinstance(widget, QLineEdit) else text)
                self.status_label.setText("Текст вставлен")
            else:
                self.status_label.setText("Буфер обмена пуст")

    def select_all_messages(self):
        """Выделяет все сообщения в чате."""
        for child in self.messages_widget.children():
            if isinstance(child, ChatMessage):
                child.is_selected = True
                child.update_selection_visuals()

    def clear_image_data(self):
        """Очищает данные изображения."""
        self.image_url_edit.clear()
        self.image_path = None
        self.image_base64 = None
        self.uploaded_image_ids = []
        self.status_label.setText("Данные изображения сброшены")

    def select_image(self):
        self.image_url_edit.clear()
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите изображения",
            "", f"Изображения ({' '.join(f'*.{fmt}' for fmt in SUPPORTED_IMAGE_FORMATS)});;Все файлы (*.*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not filepaths:
            return
        if len(filepaths) > 10:
            QMessageBox.critical(self, "Ошибка", "Максимум 10 изображений за раз")
            return
        worker = Worker(_process_images_task, filepaths)
        worker.signals.finished.connect(self._on_images_processed)
        worker.signals.error.connect(self.signals.error)
        worker.signals.finished.connect(lambda _: self.cleanup_worker(worker))
        self.workers.append(worker)
        worker.start()

    def _on_images_processed(self, results):
        """Обрабатывает результаты обработки изображений."""
        self.image_path = [filepath for filepath, _ in results]
        self.image_base64 = [encoded_image for _, encoded_image in results]
        self.signals.update_status.emit(f"Выбрано {len(results)} изображений")

    def select_file(self):
        """Открывает диалог для выбора файла."""
        self.file_path_edit.clear()
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл",
            "", f"Файлы ({' '.join(SUPPORTED_FILE_FORMATS)});;Все файлы (*.*)"
        )
        if not filepath:
            return
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in SUPPORTED_FILE_FORMATS:
            QMessageBox.critical(self, "Ошибка", "Неподдерживаемый тип файла")
            return
        self.file_path_edit.setText(filepath)
        self.status_label.setText(f"Файл выбран: {os.path.basename(filepath)}")

    def clear_file(self):
        """Очищает выбранный файл."""
        self.file_path_edit.clear()
        self.status_label.setText("Файл сброшен")

    def read_file(self):
        """Читает содержимое выбранного файла."""
        filepath = self.file_path_edit.text()
        if not filepath:
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                content = file.read()
            return content
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл: {str(e)}")
            app_logger.error(f"Ошибка чтения файла: {str(e)}")
            return None

    def clear_chat(self):
        """Очищает чат и историю сообщений."""
        # Сохраняем ссылку на кнопку, чтобы не удалять её
        load_more_button = self.load_more_button
        # Удаляем все элементы, кроме кнопки "Загрузить еще"
        while self.messages_layout.count() > 1:  # Оставляем кнопку (индекс 0)
            item = self.messages_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.chat_history.clear()
        self.current_page = 0
        load_more_button.setVisible(False)  # Устанавливаем видимость после очистки
        self.status_label.setText("Чат очищен")
        self.save_chat_history()

    def add_message_to_chat(self, message, is_user=True, timestamp=None, image_path=None, image_url=None):
        """Добавляет сообщение в чат."""
        app_logger.debug(f"Добавление сообщения в чат: '{message}'")
        msg = ChatMessage(
            self.messages_widget,
            message,
            is_user,
            timestamp,
            image_path,
            image_url,
            self
        )
        self.messages_layout.addWidget(msg)
        QTimer.singleShot(0, lambda: self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()))
    
    def load_chat_history(self):
        """Загружает историю чата из файла постранично."""
        try:
            if not CHAT_HISTORY_FILE:
                app_logger.warning("Не указан файл для загрузки истории чата")
                return
            history_file = os.path.abspath(CHAT_HISTORY_FILE)
            if not os.path.exists(history_file):
                app_logger.info(f"Файл истории чата не найден: {history_file}")
                return
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            self.chat_history.clear()
            self.current_page = 0
            self.pending_messages.clear()
            while self.messages_layout.count() > 1:  # Оставляем кнопку "Загрузить еще"
                item = self.messages_layout.takeAt(1)
                if item.widget():
                    item.widget().deleteLater()
            # Загружаем только последнюю страницу сообщений
            start_idx = max(0, len(history) - MESSAGES_PER_PAGE)
            for msg in history[start_idx:]:
                try:
                    if "timestamp" in msg and isinstance(msg["timestamp"], str):
                        try:
                            msg["timestamp"] = datetime.strptime(msg["timestamp"], DATE_FORMAT)
                        except ValueError:
                            msg["timestamp"] = datetime.now()
                    self.chat_history.append(msg)
                    is_user = msg.get("role") == "user"
                    timestamp = msg.get("timestamp")
                    content = msg.get("content", "")
                    image_path = msg.get("image") if isinstance(msg.get("image"), str) and os.path.exists(msg.get("image")) else None
                    image_url = msg.get("image") if not image_path and isinstance(msg.get("image"), str) and msg.get("image", "").startswith("http") else None
                    self.pending_messages.append((content, is_user, timestamp, image_path, image_url))
                except Exception as e:
                    app_logger.error(f"Ошибка загрузки сообщения: {str(e)}")
                    continue
            QTimer.singleShot(0, self.process_pending_messages)
            # Показываем кнопку "Загрузить еще", если есть еще сообщения
            if len(history) > MESSAGES_PER_PAGE:
                self.load_more_button.setVisible(True)
        except json.JSONDecodeError as e:
            app_logger.error(f"Ошибка декодирования JSON в файле истории: {str(e)}")
        except Exception as e:
            app_logger.error(f"Ошибка загрузки истории чата: {str(e)}")

    def load_more_messages(self):
        """Загружает предыдущую страницу сообщений без смещения скроллбара вверх."""
        try:
            history_file = os.path.abspath(CHAT_HISTORY_FILE)
            if not os.path.exists(history_file):
                app_logger.info(f"Файл истории чата не найден: {history_file}")
                return
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            
            # Сохраняем текущую позицию скроллбара
            scroll_bar = self.chat_area.verticalScrollBar()
            current_scroll_position = scroll_bar.value()
            scroll_max_before = scroll_bar.maximum()

            self.current_page += 1
            start_idx = max(0, len(history) - MESSAGES_PER_PAGE * (self.current_page + 1))
            end_idx = max(0, len(history) - MESSAGES_PER_PAGE * self.current_page)
            if start_idx >= end_idx:
                self.load_more_button.setVisible(False)
                return
            self.pending_messages.clear()
            for msg in history[start_idx:end_idx]:
                try:
                    if "timestamp" in msg and isinstance(msg["timestamp"], str):
                        try:
                            msg["timestamp"] = datetime.strptime(msg["timestamp"], DATE_FORMAT)
                        except ValueError:
                            msg["timestamp"] = datetime.now()
                    is_user = msg.get("role") == "user"
                    timestamp = msg.get("timestamp")
                    content = msg.get("content", "")
                    image_path = msg.get("image") if isinstance(msg.get("image"), str) and os.path.exists(msg.get("image")) else None
                    image_url = msg.get("image") if not image_path and isinstance(msg.get("image"), str) and msg.get("image", "").startswith("http") else None
                    self.pending_messages.append((content, is_user, timestamp, image_path, image_url))
                except Exception as e:
                    app_logger.error(f"Ошибка загрузки сообщения: {str(e)}")
                    continue

            # Подсчитываем высоту добавляемых сообщений
            new_messages = []
            for content, is_user, timestamp, image_path, image_url in reversed(self.pending_messages):
                msg = ChatMessage(
                    self.messages_widget,
                    content,
                    is_user,
                    timestamp,
                    image_path,
                    image_url,
                    self
                )
                new_messages.append(msg)
                self.messages_layout.insertWidget(1, msg)  # Вставляем после кнопки "Загрузить еще"

            self.pending_messages.clear()

            # Корректируем позицию скроллбара
            QTimer.singleShot(0, lambda: self.adjust_scroll_position(scroll_bar, current_scroll_position, new_messages))

            # Если больше нечего загружать, скрываем кнопку
            if start_idx == 0:
                self.load_more_button.setVisible(False)
            self.status_label.setText(f"Загружено {min(MESSAGES_PER_PAGE * (self.current_page + 1), len(history))} сообщений")
        except json.JSONDecodeError as e:
            app_logger.error(f"Ошибка декодирования JSON: {str(e)}")
        except Exception as e:
            app_logger.error(f"Ошибка загрузки сообщений: {str(e)}")        

    def adjust_scroll_position(self, scroll_bar, original_position, new_messages):
        """Корректирует позицию скроллбара после добавления новых сообщений."""
        # Суммируем высоту новых сообщений
        added_height = sum(msg.sizeHint().height() for msg in new_messages if msg)
        
        # Новая позиция скроллбара: старая позиция + высота добавленных сообщений
        new_position = original_position + added_height
        scroll_bar.setValue(new_position)

    def save_chat_history(self):
        """Сохраняет историю чата в файл."""
        worker = Worker(_save_chat_history_task, self.chat_history)
        worker.signals.error.connect(lambda msg: app_logger.error(msg))
        worker.signals.finished.connect(lambda result: self.cleanup_worker(worker))
        self.workers.append(worker)
        worker.start()

    def save_chat(self):
        """Сохраняет полный чат в файл через диалог выбора пути."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Сохранить чат",
            "", "JSON файлы (*.json);;Все файлы (*.*)"
        )
        if not filepath:
            return
        try:
            # Загружаем полную историю чата из файла, если он существует
            full_history = []
            history_file = os.path.abspath(CHAT_HISTORY_FILE)
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    full_history = json.load(f)
            else:
                # Если файла истории нет, используем текущую историю
                full_history = list(self.chat_history)

            # Форматируем временные метки для сохранения
            for msg in full_history:
                if "timestamp" in msg and not isinstance(msg["timestamp"], str):
                    msg["timestamp"] = msg["timestamp"].strftime(DATE_FORMAT)

            # Сохраняем полный чат в выбранный файл
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(full_history, f, ensure_ascii=False, indent=2)
            self.status_label.setText(f"Полный чат сохранен в {os.path.basename(filepath)}")
            app_logger.info(f"Полный чат сохранен в {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить чат: {str(e)}")
            app_logger.error(f"Ошибка сохранения чата: {str(e)}")

    def load_chat_from_file(self):
        """Загружает чат из выбранного файла."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл чата",
            "", "JSON файлы (*.json);;Все файлы (*.*)"
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                history = json.load(f)
            self.chat_history.clear()
            self.current_page = 0
            while self.messages_layout.count() > 1:  # Оставляем кнопку "Загрузить еще"
                item = self.messages_layout.takeAt(1)
                if item.widget():
                    item.widget().deleteLater()
            start_idx = max(0, len(history) - MESSAGES_PER_PAGE)
            for msg in history[start_idx:]:
                if "timestamp" in msg:
                    try:
                        msg["timestamp"] = datetime.fromisoformat(msg["timestamp"])
                    except ValueError:
                        msg["timestamp"] = datetime.now()
                self.chat_history.append(msg)
                is_user = msg["role"] == "user"
                timestamp = msg.get("timestamp")
                image_path = msg.get("image") if os.path.exists(msg.get("image", "")) else None
                image_url = msg.get("image") if not image_path and msg.get("image", "").startswith("http") else None
                self.pending_messages.append((msg["content"], is_user, timestamp, image_path, image_url))
            QTimer.singleShot(0, self.process_pending_messages)
            if len(history) > MESSAGES_PER_PAGE:
                self.load_more_button.setVisible(True)
            self.status_label.setText(f"Чат загружен из {os.path.basename(filepath)}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить чат: {str(e)}")
            app_logger.error(f"Ошибка загрузки чата: {str(e)}")

    def export_chat(self):
        """Экспортирует чат в текстовый файл."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Экспорт чата",
            "", "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for msg in self.chat_history:
                    role = "Вы" if msg["role"] == "user" else "Ассистент"
                    timestamp = msg.get("timestamp", datetime.now()).strftime(EXPORT_TIMESTAMP_FORMAT)
                    f.write(f"[{timestamp}] {role}: {msg['content']}\n")
                    if msg.get("image"):
                        f.write(f"[Изображение]: {msg['image']}\n\n")
                    else:
                        f.write("\n")
            self.status_label.setText(f"Чат экспортирован в {os.path.basename(filepath)}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать чат: {str(e)}")
            app_logger.error(f"Ошибка экспорта чата: {str(e)}")

    def load_models(self):
        worker = Worker(_load_models_task, self.load_chat_models, self.load_embedding_models)
        worker.signals.finished.connect(self._on_models_loaded)
        worker.signals.error.connect(self.handle_error_signal)
        worker.signals.finished.connect(lambda result: self.cleanup_worker(worker))
        self.workers.append(worker)
        worker.start()

    def _on_models_loaded(self, combined_models):
        """Обновляет список моделей в интерфейсе."""
        self.model_combobox.clear()
        self.model_combobox.addItems(combined_models)
        if combined_models:
            self.model_combobox.setCurrentText(combined_models[0])

    def load_chat_models(self):
        """Загружает список чат-моделей с сервера."""
        try:
            models_url = f"{self.api_settings['BASE_URL']}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(models_url, headers=headers, timeout=self.api_settings['API_REQUEST_TIMEOUT'])
            response.raise_for_status()
            return [model['id'] for model in response.json().get('data', [])]
        except Exception as e:
            app_logger.error(f"Ошибка загрузки чат-моделей: {str(e)}")
            return []

    def load_embedding_models(self):
        """Загружает список эмбеддинг-моделей с сервера."""
        try:
            models_url = f"{self.api_settings['BASE_URL']}/embedding-models"
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            response = requests.get(models_url, headers=headers, timeout=self.api_settings['API_REQUEST_TIMEOUT'])
            response.raise_for_status()
            embedding_models_data = response.json()
            return [model['id'] for model in embedding_models_data.get('data', [])]
        except Exception as e:
            app_logger.error(f"Ошибка загрузки моделей эмбеддингов: {str(e)}")
            return []

    def _handle_error(self, error_msg, show_message=False):
        """Обрабатывает ошибки, отображая их в интерфейсе."""
        self.status_label.setText("Ошибка")
        app_logger.error(error_msg)
        if show_message:
            QMessageBox.critical(self, "Ошибка", error_msg)
        self.clear_image_data()

    def send_request(self):
        """Отправляет запрос к AI-модели в фоновом потоке."""
        # Проверяем, есть ли текст, изображение или файл
        prompt = self.prompt_text.toPlainText().strip()
        image_url = self.image_url_edit.text().strip()
        file_content = self.read_file()
        has_image = bool(image_url or self.image_base64)

        if not prompt and not has_image and not file_content:
            self.status_label.setText("Введите сообщение, выберите изображение или файл")
            app_logger.debug("Попытка отправки пустого запроса")
            return  # Прерываем выполнение, не создавая Worker

        worker = Worker(self._send_request_task)
        worker.signals.finished.connect(self._update_ui_after_response)
        worker.signals.error.connect(self.signals.error)
        worker.signals.finished.connect(lambda result: self.cleanup_worker(worker))
        self.workers.append(worker)
        worker.start()

    def _send_request_task(self):
        selected_model = self.model_combobox.currentText()
        if not selected_model:
            raise ValueError("Сначала выберите модель")
        model_id = selected_model.replace("[Чат]", "").replace("[Эмбеддинг]", "").strip()
        model_type = self._get_model_type(model_id)
        if model_type == "embedding":
            prompt = self.prompt_text.toPlainText()
            app_logger.debug(f"Текст для эмбеддинга перед strip: '{prompt}'")
            if not prompt.strip():
                raise ValueError("Введите текст для эмбеддинга")
            # Очищаем поле ввода после извлечения текста
            QTimer.singleShot(0, self.prompt_text.clear)
            return self._handle_embedding_task(model_id, prompt)
        prompt = self.prompt_text.toPlainText()
        app_logger.debug(f"Текст запроса перед обработкой: '{prompt}'")
        # Очищаем поле ввода после извлечения текста
        QTimer.singleShot(0, self.prompt_text.clear)
        prompt = prompt.rstrip()  # Удаляем только конечные пробелы и переносы
        app_logger.debug(f"Текст запроса после обработки: '{prompt}'")
        image_url = self.image_url_edit.text().strip()
        has_image = False
        image_paths = self.image_path if isinstance(self.image_path, list) else [self.image_path] if self.image_path else []
        image_base64s = self.image_base64 if isinstance(self.image_base64, list) else [self.image_base64] if self.image_base64 else []
        image_urls = []
        if image_url:
            if not self._is_valid_url(image_url):
                raise ValueError("Некорректный URL изображения")
            try:
                response = requests.head(image_url, timeout=5)
                if response.status_code != 200:
                    raise ValueError("URL изображения недоступен")
            except requests.RequestException as e:
                raise ValueError(f"Ошибка проверки URL изображения: {str(e)}")
            image_urls.append(image_url)
            has_image = True
        if image_base64s:
            for img_b64 in image_base64s:
                image_urls.append(f"data:image/jpeg;base64,{img_b64}")
                has_image = True
                app_logger.debug(f"Добавлено изображение в формате base64")
        if len(image_urls) > 10:
            raise ValueError("Максимум 10 изображений за запрос")
        file_content = self.read_file()
        file_type = None
        file_path = self.file_path_edit.text()
        if file_content:
            ext = os.path.splitext(file_path)[1][1:].lower()
            file_type = {"py": "python", "txt": "text", "json": "json"}.get(ext)
            if not file_type:
                raise ValueError("Неподдерживаемый тип файла")
        if not prompt and has_image and model_type != "vision":
            raise ValueError("Выбранная модель не поддерживает работу только с изображениями")
        if not prompt and has_image:
            prompt = "Что на этих изображениях?"
        timestamp = datetime.now().replace(microsecond=0)
        message_content = prompt
        content = [{"type": "text", "text": message_content}]
        if has_image:
            message_content += f" [Изображения: {len(image_urls)}]"
            for img_url in image_urls:
                content.append({"type": "image_url", "image_url": {"url": img_url}})
        if file_content:
            message_content += f"\n``` {file_type}\n{file_content}\n```"
            content[0]["text"] += f"\n\nСодержимое файла ({file_type}):\n```\n{file_content}\n```"
        
        app_logger.debug(f"Добавлено в pending_messages: '{message_content}'")
        self.pending_messages.append((message_content, True, timestamp, image_paths[0] if image_paths else None, image_url or None))
        QTimer.singleShot(0, self.process_pending_messages)

        messages = [
            {
                "role": "system",
                "content": self.api_settings["SYSTEM_PROMPT"]
            }
        ]
        for msg in self.chat_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        messages.append({
            "role": "user",
            "content": content
        })
        self._add_to_history(
            "user",
            message_content,
            image_urls[0] if image_urls else file_path
        )
        response = self.create_completion(model_id, messages)        
        return response

    def _update_ui_after_response(self, response):
        """Обновляет интерфейс после получения ответа от модели."""
        try:
            if not response:
                self.signals.update_status.emit("Ошибка при отправке запроса")
                return
            content = response['choices'][0]['message']['content']
            timestamp = datetime.now()
            self._add_to_history("assistant", content)
            self.signals.add_message.emit(content, False, timestamp, None, None)
            self.signals.update_status.emit("Ответ получен")
            if self.uploaded_image_ids and self.local_server:
                all_deleted = True
                for image_id in self.uploaded_image_ids:
                    try:
                        self.local_server.delete_image(image_id)
                    except Exception as e:
                        app_logger.error(f"Ошибка удаления изображения {image_id} с локального сервера: {str(e)}")
                        all_deleted = False
                if all_deleted:
                    self.uploaded_image_ids.clear()
        except (KeyError, IndexError) as e:
            error_msg = f"Ошибка формата ответа: {str(e)}"
            self.signals.error.emit(error_msg)
        finally:
            self.clear_image_data()
            self.clear_file()
            self.save_chat_history()

    def create_completion(self, model_id, messages):
        """Создает запрос на завершение чата к API."""
        completions_url = f"{self.api_settings['BASE_URL']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid.uuid4())
        }
        data = {
            "model": model_id,
            "messages": messages,
            "temperature": self.api_settings['TEMPERATURE'],
            "max_completion_tokens": self.api_settings['MAX_COMPLETION_TOKENS'],
            "seed": self.api_settings['SEED'],
            "user": "user123"
        }
        response = requests.post(completions_url, headers=headers, json=data, timeout=self.api_settings['API_REQUEST_TIMEOUT'])
        response.raise_for_status()
        return response.json()

    def _get_model_type(self, model_id):
        """Определяет тип модели (визионная, эмбеддинг или чат)."""
        if model_id in VISION_MODELS:
            return "vision"
        if "[Эмбеддинг]" in self.model_combobox.currentText():
            return "embedding"
        return "chat"
  
    def _add_to_history(self, role, content, image=None):
        """Добавляет сообщение в историю чата."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().replace(microsecond=0)
        }
        if image:
            message["image"] = image if isinstance(image, str) else image[0] if image else None
        self.chat_history.append(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Application()
    window.show()
    sys.exit(app.exec())