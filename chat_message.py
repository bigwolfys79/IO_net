from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QSizePolicy
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont, QFontMetrics
from PIL import Image
import requests
import os
from urllib.parse import urlparse
import logging
from config import (
    COLORS, TIMESTAMP_FORMAT, IMAGE_THUMBNAIL_SIZE, API_REQUEST_TIMEOUT,
    COLLAPSED_MESSAGE_LINES, MESSAGE_HEIGHT_RULES
)
from text_editors import NonScrollableTextEdit, SyntaxHighlighter

class ChatMessage(QWidget):
    """Класс для отображения сообщения в чате."""
    def __init__(self, parent, message, is_user=True, timestamp=None, image_path=None, image_url=None, app=None):
        super().__init__(parent)
        self.is_user = is_user
        self.selected_color = COLORS["selection"]
        self.is_selected = False
        self.expanded = True
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        self.app = app
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 2, 5, 2)
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        label_text = "Вы" if is_user else "Ассистент"
        label = QLabel(label_text)
        label.setFont(QFont(COLORS['font_family'], 8))
        label.setStyleSheet(f"color: {COLORS['text']}; background-color: {COLORS['background']};")
        bubble = QWidget()
        bubble.setStyleSheet(f"background-color: {COLORS['user_message_background'] if is_user else COLORS['widget_background']}; border: 1px solid {COLORS['border']}; padding: 10px;")
        bubble_layout = QVBoxLayout(bubble)
        self.message_text = NonScrollableTextEdit()
        self.message_text.setReadOnly(True)
        self.message_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.message_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.message_text.setFont(QFont(COLORS['font_family'], COLORS['font_size']))
        scrollbar_background = COLORS['user_message_background'] if is_user else COLORS['border']
        self.message_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['user_message_background'] if is_user else COLORS['widget_background']};
                color: {COLORS['text']};
                border: none;
                padding: 2px;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {scrollbar_background};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical {{
                background: {scrollbar_background};
                height: 0px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }}
            QScrollBar::sub-line:vertical {{
                background: {scrollbar_background};
                height: 0px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        self.highlighter = SyntaxHighlighter(self.message_text.document(), self.app)
        self.message_text.setPlainText(message)
        bubble_layout.addWidget(self.message_text)
        self.image_label = None
        if image_path or image_url:
            self._load_image(bubble_layout, image_path, image_url)
        if is_user:
            container_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)
            container_layout.addWidget(bubble)
            container_layout.setStretch(0, 0)
            container_layout.setStretch(1, 1)
        else:
            container_layout.addWidget(bubble)
            container_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignRight)
            container_layout.setStretch(0, 1)
            container_layout.setStretch(1, 0)
        main_layout.addWidget(container)
        if timestamp:
            time_label = QLabel(timestamp.strftime(TIMESTAMP_FORMAT))
            time_label.setFont(QFont(COLORS['font_family'], 7))
            time_label.setStyleSheet(f"color: {COLORS['text']}; background-color: {COLORS['background']};")
            main_layout.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft)
        self.message_text.mousePressEvent = self.handle_single_click
        self.message_text.mouseDoubleClickEvent = self.toggle_expansion
        self._update_height_after_render()

    def _calculate_wrapped_line_count(self):
        """Вычисляет количество строк с учетом переноса."""
        document = self.message_text.document()
        if not document or document.isEmpty():
            return 1
        total_lines = document.blockCount()
        self.message_text.document().setTextWidth(self.message_text.width())
        block = document.begin()
        while block.isValid():
            layout = block.layout()
            if layout:
                total_lines += max(0, layout.lineCount() - 1)
            block = block.next()
        logging.debug(f"Всего строк: {total_lines}")
        return max(1, total_lines)

    def _update_height_after_render(self):
        """Обновляет высоту сообщения после рендеринга."""
        def delayed_update():
            self.wrapped_line_count = self._calculate_wrapped_line_count()
            font_metrics = QFontMetrics(self.message_text.font())
            line_height = font_metrics.lineSpacing()
            margins = self.message_text.contentsMargins()
            extra_height = margins.top() + margins.bottom() + 4
            if self.wrapped_line_count <= COLLAPSED_MESSAGE_LINES and not self.expanded:
                line_multiplier = MESSAGE_HEIGHT_RULES.get(self.wrapped_line_count, COLLAPSED_MESSAGE_LINES + 0.5)
                base_height = line_height * line_multiplier
                final_height = int(base_height + extra_height)
                self.message_text.setFixedHeight(final_height)
                self.message_text.setVerticalScrollBarPolicy(Qt.Scroll.ScrollBarAlwaysOff)
            elif not self.expanded:
                collapsed_height = int(line_height * (COLLAPSED_MESSAGE_LINES + 0.5) + extra_height)
                self.message_text.setFixedHeight(collapsed_height)
                self.message_text.setVerticalScrollBarPolicy(Qt.Scroll.ScrollBarAsNeeded)
            else:
                doc_height = self.message_text.document().size().height()
                self.message_text.setFixedHeight(int(doc_height + extra_height))
            self.message_text.updateGeometry()
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()
        QTimer.singleShot(0, delayed_update)

    def _load_image(self, layout, image_path, image_url):
        """Загружает и отображает изображение в сообщении."""
        try:
            if image_path:
                img = Image.open(image_path)
                img.verify()
                img = Image.open(image_path)
            elif image_url:
                if not self._is_valid_url(image_url):
                    raise ValueError("Некорректный URL изображения")
                if image_url.startswith("http://localhost:5000/uploads/"):
                    filename = image_url.split("/")[-1]
                    file_path = os.path.join("uploads", filename)
                    if not os.path.exists(file_path):
                        raise FileNotFoundError(f"Файл {file_path} не найден на локальном сервере")
                    img = Image.open(file_path)
                else:
                    response = requests.get(image_url, stream=True, timeout=API_REQUEST_TIMEOUT)
                    response.raise_for_status()
                    img = Image.open(response.raw)
            img.thumbnail(IMAGE_THUMBNAIL_SIZE)
            img = img.convert("RGB")
            qimage = QImage(img.size[0], img.size[1], QImage.Format.Format_RGB32)
            for x in range(img.size[0]):
                for y in range(img.size[1]):
                    r, g, b = img.getpixel((x, y))
                    rgb = (r << 16) | (g << 8) | b
                    qimage.setPixel(x, y, rgb)
            pixmap = QPixmap.fromImage(qimage)
            self.image_label = QLabel()
            self.image_label.setPixmap(pixmap)
            layout.addWidget(self.image_label)
        except Exception as e:
            self.message_text.setPlainText(self.message_text.toPlainText() + f"\n[Ошибка загрузки изображения: {str(e)}]")
            logging.error(f"Ошибка загрузки изображения: {str(e)}")

    def _is_valid_url(self, url):
        """Проверяет валидность URL."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def handle_single_click(self, event):
        """Обрабатывает одиночный клик мыши для выделения сообщения."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.is_selected = not self.is_selected
            self.update_selection_visuals()
        else:
            QTextEdit.mousePressEvent(self.message_text, event)

    def toggle_expansion(self, event):
        """Переключает развернутое/свернутое состояние сообщения."""
        if self.wrapped_line_count <= COLLAPSED_MESSAGE_LINES:
            return
        self.expanded = not self.expanded
        if self.expanded:
            doc_height = self.message_text.document().size().height()
            self.message_text.setFixedHeight(min(int(doc_height), 1000))
            self.message_text.setVerticalScrollBarPolicy(Qt.Scroll.ScrollBarAsNeeded)
        else:
            font_metrics = QFontMetrics(self.message_text.font())
            line_height = font_metrics.lineSpacing()
            margins = self.message_text.contentsMargins()
            collapsed_height = int(line_height * (COLLAPSED_MESSAGE_LINES + 0.5) + margins.top() + margins.bottom())
            self.message_text.setFixedHeight(collapsed_height)
        self.message_text.updateGeometry()
        self.updateGeometry()
        self.parent().updateGeometry()
        super(QTextEdit, self.message_text).mouseDoubleClickEvent(event)

    def update_selection_visuals(self):
        """Обновляет визуальное отображение выделения сообщения."""
        if self.is_selected:
            self.setStyleSheet(f"background-color: {self.selected_color};")
            self.message_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {self.selected_color};
                    color: {COLORS['text']};
                    border: none;
                    padding: 2px;
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
        else:
            self.setStyleSheet(f"background-color: {COLORS['background']};")
            self.message_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {COLORS['user_message_background'] if self.is_user else COLORS['widget_background']};
                    color: {COLORS['text']};
                    border: none;
                    padding: 2px;
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