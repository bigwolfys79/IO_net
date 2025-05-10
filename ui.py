from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QTextEdit, QLineEdit, QScrollArea,
    QMenu, QFileDialog, QMessageBox, QDialog, QFormLayout, QRadioButton, QFontComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QShortcut, QKeySequence, QAction
from config import COLORS, THEMES, LOGGING, SERVER_LOGGING, API_SETTINGS_FILE
from logging_config import configure_logging
import logging
import json
import os
from text_editors import NonScrollableTextEdit, EnterKeyTextEdit
from encrypt import save_api_key

# Инициализация логгера
app_logger = logging.getLogger('app')

def setup_ui(app):
    """Настраивает пользовательский интерфейс приложения."""
    app_logger.debug("Начало настройки UI")
    central_widget = QWidget()
    app.setCentralWidget(central_widget)
    central_widget.setStyleSheet(f"background-color: {COLORS['background']};")
    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(10, 10, 10, 10)
    top_layout = QHBoxLayout()
    top_layout.setSpacing(10)
    menu_button = QPushButton("Меню")
    menu_button.setMinimumWidth(100)
    menu_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    menu = QMenu(menu_button)
    menu.addAction("Сохранить чат", app.save_chat)
    menu.addAction("Загрузить чат", app.load_chat_from_file)
    menu.addAction("Экспорт в файл", app.export_chat)
    menu.addAction("Ввести API-ключ", lambda: prompt_for_api_key(app))
    menu.addAction("Настройки API", lambda: prompt_for_api_settings(app))
    menu.addAction("Настройки логирования", lambda: prompt_for_logging_settings(app))
    menu.addAction("Выбрать тему", lambda: prompt_for_theme(app))
    menu.addAction("Настройки шрифта", lambda: prompt_for_font_settings(app))
    menu_button.setMenu(menu)
    top_layout.addWidget(menu_button)
    model_label = QLabel("Выберите модель:")
    model_label.setMinimumWidth(120)
    model_label.setStyleSheet(f"color: {COLORS['text']}; background-color: {COLORS['background']};")
    top_layout.addWidget(model_label)
    app.model_combobox = QComboBox()
    app.model_combobox.setMinimumWidth(300)
    app.model_combobox.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    top_layout.addWidget(app.model_combobox)
    clear_button = QPushButton("Очистить чат")
    clear_button.setMinimumWidth(120)
    clear_button.clicked.connect(app.clear_chat)
    clear_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    top_layout.addWidget(clear_button)
    main_layout.addLayout(top_layout)
    app.chat_area = QScrollArea()
    app.chat_area.setWidgetResizable(True)
    app.chat_area.setMinimumHeight(400)
    app.messages_widget = QWidget()
    app.messages_widget.setStyleSheet(f"background-color: {COLORS['background']};")
    app.messages_layout = QVBoxLayout(app.messages_widget)
    app.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    # Добавляем кнопку "Загрузить еще" в messages_layout
    app.load_more_button = QPushButton("Загрузить еще")
    app.load_more_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    app.load_more_button.clicked.connect(app.load_more_messages)
    app.load_more_button.setVisible(False)
    app.messages_layout.addWidget(app.load_more_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)  # Явно добавляем в messages_layout
    app.chat_area.setWidget(app.messages_widget)
    app.chat_area.setStyleSheet(f"""
        QScrollArea {{
            background-color: {COLORS['background']};
            border: 1px solid {COLORS['border']};
        }}
        QScrollBar:vertical {{
            border: none;
            background: {COLORS['widget_background']};
            width: 10px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLORS['border']};
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical {{
            background: {COLORS['widget_background']};
            height: 0px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }}
        QScrollBar::sub-line:vertical {{
            background: {COLORS['widget_background']};
            height: 0px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
    """)
    main_layout.addWidget(app.chat_area)
    input_layout = QVBoxLayout()
    input_layout.setSpacing(5)
    app.file_path_edit = QLineEdit()
    app.file_path_edit.setReadOnly(True)
    app.file_path_edit.setMinimumHeight(30)
    app.file_path_edit.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    input_layout.addWidget(app.file_path_edit)
    select_file_button = QPushButton("Загрузить файл")
    select_file_button.setMinimumHeight(30)
    select_file_button.clicked.connect(app.select_file)
    select_file_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    input_layout.addWidget(select_file_button)
    clear_file_button = QPushButton("Очистить файл")
    clear_file_button.setMinimumHeight(30)
    clear_file_button.clicked.connect(app.clear_file)
    clear_file_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    input_layout.addWidget(clear_file_button)
    image_layout = QHBoxLayout()
    image_layout.setSpacing(5)
    image_label = QLabel("URL изображения:")
    image_label.setMinimumWidth(100)
    image_label.setStyleSheet(f"color: {COLORS['text']}; background-color: {COLORS['background']};")
    image_layout.addWidget(image_label)
    app.image_url_edit = QLineEdit()
    app.image_url_edit.setMinimumHeight(30)
    app.image_url_edit.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    image_layout.addWidget(app.image_url_edit)
    select_image_button = QPushButton("Файл")
    select_image_button.setMinimumWidth(50)
    select_image_button.clicked.connect(app.select_image)
    select_image_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    clear_image_button = QPushButton("×")
    clear_image_button.setMinimumWidth(30)
    clear_image_button.clicked.connect(app.clear_image_data)
    clear_image_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    image_layout.addWidget(select_image_button)
    image_layout.addWidget(clear_image_button)
    input_layout.addLayout(image_layout)
    app.prompt_text = EnterKeyTextEdit(app)
    app.prompt_text.setFixedHeight(80)
    app.prompt_text.setStyleSheet(f"background-color: {COLORS['widget_background']}; border: 1px solid {COLORS['border']}; color: {COLORS['text']};")
    input_layout.addWidget(app.prompt_text)
    send_button = QPushButton("Отправить")
    send_button.setMinimumHeight(40)
    send_button.clicked.connect(app.send_request)
    send_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    input_layout.addWidget(send_button)
    main_layout.addLayout(input_layout)
    app.status_label.setMinimumHeight(20)
    app.status_label.setStyleSheet(f"color: {COLORS['text']}; background-color: {COLORS['background']};")
    main_layout.addWidget(app.status_label)
    app_logger.debug("UI успешно настроен")

def setup_clipboard(app):
    """Настраивает контекстное меню и горячие клавиши для работы с буфером обмена."""
    app.context_menu = QMenu(app)
    app.copy_action = QAction("Копировать текст", app)
    app.copy_action.triggered.connect(app.copy_text)
    app.select_all_action = QAction("Выделить всё", app)
    app.select_all_action.triggered.connect(app.select_all_messages)
    app.paste_action = QAction("Вставить", app)
    app.paste_action.triggered.connect(app.paste_text)
    app.context_menu.addAction(app.copy_action)
    app.context_menu.addAction(app.select_all_action)
    app.context_menu.addSeparator()
    app.context_menu.addAction(app.paste_action)
    QShortcut(QKeySequence("Ctrl+C"), app, app.copy_text)
    QShortcut(QKeySequence("Ctrl+V"), app, app.paste_text)

def prompt_for_api_key(app):
    """Открывает диалог для ввода API-ключа."""
    dialog = QMainWindow(app)
    dialog.setWindowTitle("Введите API-ключ")
    dialog.setFixedSize(400, 150)
    dialog.setStyleSheet(f"background-color: {COLORS['background']};")
    central_widget = QWidget()
    dialog.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    label = QLabel("Введите ваш API-ключ:")
    label.setStyleSheet(f"color: {COLORS['text']};")
    layout.addWidget(label)
    entry = QLineEdit()
    entry.setEchoMode(QLineEdit.EchoMode.Password)
    entry.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addWidget(entry)
    save_button = QPushButton("Сохранить")
    save_button.clicked.connect(lambda: _save_api_key(app, dialog, entry))
    save_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addWidget(save_button)
    dialog.show()

def _save_api_key(app, dialog, entry):
    """Сохраняет API-ключ из диалога."""
    api_key = entry.text().strip()
    if not api_key:
        QMessageBox.critical(dialog, "Ошибка", "API-ключ не может быть пустым")
        return
    try:
        save_api_key(api_key)
        app.api_key = api_key
        app.status_label.setText("API-ключ успешно сохранен")
        dialog.close()
        app.load_models()
    except Exception as e:
        QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить API-ключ: {str(e)}")
        app_logger.error(f"Ошибка сохранения API-ключа: {str(e)}")

def prompt_for_api_settings(app):
    """Открывает диалог для ввода настроек API."""
    dialog = QMainWindow(app)
    dialog.setWindowTitle("Настройки API")
    dialog.setFixedSize(500, 400)
    dialog.setStyleSheet(f"background-color: {COLORS['background']};")
    central_widget = QWidget()
    dialog.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    fields = [
        ("BASE_URL", "Базовый URL API:", QLineEdit, str),
        ("API_REQUEST_TIMEOUT", "Таймаут запроса (сек):", QLineEdit, int),
        ("TEMPERATURE", "Температура (0-2):", QLineEdit, float),
        ("MAX_COMPLETION_TOKENS", "Макс. токенов:", QLineEdit, int),
        ("SEED", "Seed:", QLineEdit, int),
        ("SYSTEM_PROMPT", "Системный промпт:", QTextEdit, str)
    ]
    input_widgets = {}
    for key, label_text, widget_type, value_type in fields:
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(label)
        widget = widget_type()
        if widget_type == QTextEdit:
            widget.setFixedHeight(80)
        widget.setText(str(app.api_settings[key]) if value_type == str else str(app.api_settings[key]))
        widget.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
        layout.addWidget(widget)
        input_widgets[key] = widget
    save_button = QPushButton("Сохранить")
    save_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    save_button.clicked.connect(lambda: _save_api_settings(app, dialog, input_widgets))
    layout.addWidget(save_button)
    dialog.show()

def _save_api_settings(app, dialog, input_widgets):
    """Сохраняет настройки API из диалога."""
    try:
        new_settings = {}
        for key, widget in input_widgets.items():
            value = widget.toPlainText() if isinstance(widget, QTextEdit) else widget.text().strip()
            if not value:
                raise ValueError(f"Поле {key} не может быть пустым")
            if key == "API_REQUEST_TIMEOUT":
                value = int(value)
                if value <= 0:
                    raise ValueError("Таймаут должен быть больше 0")
            elif key == "TEMPERATURE":
                value = float(value)
                if not 0 <= value <= 2:
                    raise ValueError("Температура должна быть от 0 до 2")
            elif key == "MAX_COMPLETION_TOKENS":
                value = int(value)
                if value <= 0:
                    raise ValueError("Количество токенов должно быть больше 0")
            elif key == "SEED":
                value = int(value)
            elif key == "BASE_URL":
                if not value.startswith("http"):
                    raise ValueError("URL должен начинаться с http или https")
            new_settings[key] = value
        app.api_settings.update(new_settings)
        app.save_api_settings()
        app.status_label.setText("Настройки API сохранены")
        dialog.close()
    except ValueError as e:
        QMessageBox.critical(dialog, "Ошибка", str(e))
    except Exception as e:
        QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")
        app_logger.error(f"Ошибка сохранения настроек API: {str(e)}")

def prompt_for_theme(app):
    """Открывает диалог для выбора темы."""
    dialog = QDialog(app)
    dialog.setWindowTitle("Выбор темы")
    dialog.setFixedSize(300, 150)
    dialog.setStyleSheet(f"background-color: {COLORS['background']};")
    layout = QFormLayout(dialog)
    theme_group = QWidget()
    theme_layout = QVBoxLayout(theme_group)
    radio_buttons = {}
    for theme_name in THEMES:
        rb = QRadioButton(theme_name.capitalize())
        rb.setStyleSheet(f"color: {COLORS['text']};")
        if theme_name == app.current_theme:
            rb.setChecked(True)
        radio_buttons[theme_name] = rb
        theme_layout.addWidget(rb)
    layout.addRow("Тема:", theme_group)
    save_button = QPushButton("Сохранить")
    save_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    save_button.clicked.connect(lambda: _save_theme(app, dialog, radio_buttons))
    layout.addWidget(save_button)
    dialog.exec()

def _save_theme(app, dialog, radio_buttons):
    """Сохраняет выбранную тему из диалога."""
    try:
        selected_theme = next(theme for theme, rb in radio_buttons.items() if rb.isChecked())
        app.current_theme = selected_theme
        global COLORS
        COLORS = THEMES[selected_theme].copy()
        COLORS["font_family"] = THEMES[selected_theme]["font_family"]
        COLORS["font_size"] = THEMES[selected_theme]["font_size"]
        app_logger.info(f"Тема изменена на '{selected_theme}'")
        app.save_theme_settings()
        app.centralWidget().deleteLater()
        app.setCentralWidget(QWidget())
        setup_ui(app)
        app.load_chat_history()
        QTimer.singleShot(0, app.process_pending_messages)
        for i in range(app.messages_layout.count()):
            widget = app.messages_layout.itemAt(i).widget()
            if isinstance(widget, app.ChatMessage):
                widget.highlighter.rehighlight()
        app.status_label.setText(f"Тема '{selected_theme}' применена")
        dialog.accept()
    except Exception as e:
        QMessageBox.critical(dialog, "Ошибка", f"Не удалось применить тему: {str(e)}")
        app_logger.error(f"Ошибка применения темы: {str(e)}")

def prompt_for_font_settings(app):
    """Открывает диалог для настройки шрифта."""
    dialog = QDialog(app)
    dialog.setWindowTitle("Настройки шрифта")
    dialog.setFixedSize(300, 200)
    dialog.setStyleSheet(f"background-color: {COLORS['background']};")
    layout = QFormLayout(dialog)
    font_label = QLabel("Шрифт:")
    font_label.setStyleSheet(f"color: {COLORS['text']};")
    font_combo = QFontComboBox()
    font_combo.setCurrentFont(QFont(COLORS['font_family']))
    font_combo.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addRow(font_label, font_combo)
    size_label = QLabel("Размер шрифта:")
    size_label.setStyleSheet(f"color: {COLORS['text']};")
    size_spin = QSpinBox()
    size_spin.setRange(8, 24)
    size_spin.setValue(COLORS['font_size'])
    size_spin.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addRow(size_label, size_spin)
    save_button = QPushButton("Сохранить")
    save_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    save_button.clicked.connect(lambda: _save_font_settings(app, dialog, font_combo, size_spin))
    layout.addWidget(save_button)
    dialog.exec()

def _save_font_settings(app, dialog, font_combo, size_spin):
    """Сохраняет настройки шрифта из диалога."""
    try:
        font_family = font_combo.currentFont().family()
        font_size = size_spin.value()
        global COLORS
        COLORS["font_family"] = font_family
        COLORS["font_size"] = font_size
        app_logger.info(f"Шрифт изменен на '{font_family}' размером {font_size}pt")
        app.save_theme_settings()
        app.centralWidget().deleteLater()
        app.setCentralWidget(QWidget())
        setup_ui(app)
        app.load_chat_history()
        QTimer.singleShot(0, app.process_pending_messages)
        app.status_label.setText(f"Шрифт '{font_family}' {font_size}pt применен")
        dialog.accept()
    except Exception as e:
        QMessageBox.critical(dialog, "Ошибка", f"Не удалось применить шрифт: {str(e)}")
        app_logger.error(f"Ошибка применения шрифта: {str(e)}")

def prompt_for_logging_settings(app):
    """Открывает диалог для настройки логирования."""
    # Перезагружаем настройки логирования перед открытием диалога
    # configure_logging()

    dialog = QDialog(app)
    dialog.setWindowTitle("Настройки логирования")
    dialog.setFixedSize(500, 400)
    dialog.setStyleSheet(f"background-color: {COLORS['background']};")
    layout = QFormLayout(dialog)

    # Уровень логов программы
    app_log_level_label = QLabel("Уровень логов программы:")
    app_log_level_label.setStyleSheet(f"color: {COLORS['text']};")
    app_log_level_combo = QComboBox()
    app_log_level_combo.addItems(["OFF", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    app_log_level_combo.setCurrentText(LOGGING["level"])
    app_log_level_combo.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addRow(app_log_level_label, app_log_level_combo)

    # Файл логов программы
    app_log_file_label = QLabel("Файл логов программы:")
    app_log_file_label.setStyleSheet(f"color: {COLORS['text']};")
    app_log_file_edit = QLineEdit()
    app_log_file_edit.setText(LOGGING["filename"])
    app_log_file_edit.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addRow(app_log_file_label, app_log_file_edit)

    # Режим записи логов программы
    app_log_mode_label = QLabel("Режим записи логов программы:")
    app_log_mode_label.setStyleSheet(f"color: {COLORS['text']};")
    app_log_mode_combo = QComboBox()
    app_log_mode_combo.addItems(["append", "recreate"])
    app_log_mode_combo.setCurrentText(LOGGING.get("mode", "append"))
    app_log_mode_combo.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addRow(app_log_mode_label, app_log_mode_combo)

    # Уровень логов сервера
    server_log_level_label = QLabel("Уровень логов сервера:")
    server_log_level_label.setStyleSheet(f"color: {COLORS['text']};")
    server_log_level_combo = QComboBox()
    server_log_level_combo.addItems(["OFF", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    server_log_level_combo.setCurrentText(SERVER_LOGGING["level"])
    server_log_level_combo.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addRow(server_log_level_label, server_log_level_combo)

    # Файл логов сервера
    server_log_file_label = QLabel("Файл логов сервера:")
    server_log_file_label.setStyleSheet(f"color: {COLORS['text']};")
    server_log_file_edit = QLineEdit()
    server_log_file_edit.setText(SERVER_LOGGING["filename"])
    server_log_file_edit.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addRow(server_log_file_label, server_log_file_edit)

    # Режим записи логов сервера
    server_log_mode_label = QLabel("Режим записи логов сервера:")
    server_log_mode_label.setStyleSheet(f"color: {COLORS['text']};")
    server_log_mode_combo = QComboBox()
    server_log_mode_combo.addItems(["append", "recreate"])
    server_log_mode_combo.setCurrentText(SERVER_LOGGING.get("mode", "append"))
    server_log_mode_combo.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    layout.addRow(server_log_mode_label, server_log_mode_combo)

    # Кнопка сохранения
    save_button = QPushButton("Сохранить")
    save_button.setStyleSheet(f"background-color: {COLORS['widget_background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
    save_button.clicked.connect(lambda: _save_logging_settings(
        app,
        dialog,
        app_log_level_combo, app_log_file_edit, app_log_mode_combo,
        server_log_level_combo, server_log_file_edit, server_log_mode_combo
    ))
    layout.addWidget(save_button)

    dialog.exec()

def _save_logging_settings(app, dialog, app_log_level_combo, app_log_file_edit, app_log_mode_combo, server_log_level_combo, server_log_file_edit, server_log_mode_combo):
    """Сохраняет настройки логирования из диалога."""
    try:
        new_app_log_file = app_log_file_edit.text().strip()
        new_server_log_file = server_log_file_edit.text().strip()
        app_log_level = app_log_level_combo.currentText()
        server_log_level = server_log_level_combo.currentText()
        app_log_mode = app_log_mode_combo.currentText()
        server_log_mode = server_log_mode_combo.currentText()

        # Валидация
        if app_log_level != "OFF" and not new_app_log_file:
            raise ValueError("Путь к файлу логов программы не может быть пустым, если логирование включено")
        if server_log_level != "OFF" and not new_server_log_file:
            raise ValueError("Путь к файлу логов сервера не может быть пустым, если логирование включено")
        if new_app_log_file and not new_app_log_file.endswith(".log"):
            new_app_log_file += ".log"
        if new_server_log_file and not new_server_log_file.endswith(".log"):
            new_server_log_file += ".log"

        # Обновление конфигурации
        LOGGING.update({
            "level": app_log_level,
            "filename": new_app_log_file,
            "mode": app_log_mode
        })
        SERVER_LOGGING.update({
            "level": server_log_level,
            "filename": new_server_log_file,
            "mode": server_log_mode
        })

        # Сохранение в JSON
        app.save_logging_config()

        # Переконфигурация логирования
        configure_logging()

        # Перезапуск сервера
        app.restart_server()
        app.status_label.setText("Настройки логирования сохранены")
        app_logger.info("Настройки логирования обновлены")
        dialog.accept()
    except Exception as e:
        QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить настройки логирования: {str(e)}")
        app_logger.error(f"Ошибка сохранения настроек логирования: {str(e)}")