from PyQt6.QtWidgets import QTextEdit, QCompleter
from PyQt6.QtCore import Qt, QTimer, QStringListModel
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QFont
import re
from config import COLORS, HIGHLIGHT_RULES, LOGGING
import logging
logging.basicConfig(
    level=getattr(logging, LOGGING["level"]),
    format=LOGGING["format"],
    handlers=[
        logging.FileHandler(LOGGING["filename"], encoding=LOGGING["encoding"]),
        logging.StreamHandler()
    ]
)

class NonScrollableTextEdit(QTextEdit):
    """Класс текстового редактора без прокрутки, если скроллбар не виден."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def wheelEvent(self, event):
        """Обрабатывает событие прокрутки колеса мыши."""
        if self.verticalScrollBar().isVisible():
            super().wheelEvent(event)

    def mouseMoveEvent(self, event):
        """Обрабатывает событие перемещения мыши."""
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Обрабатывает событие отпускания кнопки мыши."""
        super().mouseReleaseEvent(event)

class EnterKeyTextEdit(QTextEdit):
    """Класс текстового редактора с автодополнением и обработкой клавиши Enter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.model = QStringListModel()
        self.completer.setModel(self.model)
        self.completer.activated.connect(self.insert_completion)
        self.textChanged.connect(self.update_completions)
        self.setFont(QFont(COLORS['font_family'], COLORS['font_size']))

    def update_completions(self):
        """Обновляет список автодополнений на основе истории чата."""
        if not hasattr(self.parent, 'chat_history'):
            return
        completions = set()
        for msg in self.parent.chat_history:
            if msg.get("role") == "user":
                words = msg.get("content", "").split()
                completions.update(words)
        self.model.setStringList(list(completions))

    def insert_completion(self, completion):
        """Вставляет выбранное автодополнение в текст."""
        cursor = self.textCursor()
        cursor.select(cursor.SelectionType.WordUnderCursor)
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            text = self.toPlainText()
            logging.debug(f"Введенный текст: '{text}' (после strip: '{text.strip()}')")
            if text:  # Проверяем наличие любого текста
                if hasattr(self.parent, 'send_request'):
                    logging.debug("Вызов send_request")
                    self.parent.send_request()
            else:
                logging.debug("Текст пустой, send_request не вызывается")
                self.setStyleSheet(f"background-color: {COLORS['widget_background']}; border: 2px solid {COLORS['error']}; color: {COLORS['text']};")
                QTimer.singleShot(1000, lambda: self.setStyleSheet(f"background-color: {COLORS['widget_background']}; border: 1px solid {COLORS['border']}; color: {COLORS['text']};"))
            event.accept()
        elif event.key() == Qt.Key.Key_Space and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            cursor = self.textCursor()
            cursor.select(cursor.SelectionType.WordUnderCursor)
            self.completer.setCompletionPrefix(cursor.selectedText())
            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.currentIndex())
            cr = self.cursorRect()
            cr.setWidth(popup.sizeHint().width())
            popup.setGeometry(cr)
            popup.show()
            event.accept()
        else:
            super().keyPressEvent(event)

class SyntaxHighlighter(QSyntaxHighlighter):
    """Класс для подсветки синтаксиса текста в редакторе."""
    def __init__(self, document, app):
        super().__init__(document)
        self.app = app
        self.highlighting_rules = []
        self.update_colors()

    def update_colors(self):
        """Обновляет правила подсветки синтаксиса в зависимости от темы."""
        self.highlighting_rules.clear()
        if self.app.current_theme == "dark":
            keyword_format = QTextCharFormat()
            keyword_format.setForeground(Qt.GlobalColor.cyan)
            string_format = QTextCharFormat()
            string_format.setForeground(Qt.GlobalColor.green)
            comment_format = QTextCharFormat()
            comment_format.setForeground(Qt.GlobalColor.gray)
            number_format = QTextCharFormat()
            number_format.setForeground(Qt.GlobalColor.magenta)
        else:
            keyword_format = QTextCharFormat()
            keyword_format.setForeground(Qt.GlobalColor.darkBlue)
            string_format = QTextCharFormat()
            string_format.setForeground(Qt.GlobalColor.darkGreen)
            comment_format = QTextCharFormat()
            comment_format.setForeground(Qt.GlobalColor.darkGray)
            number_format = QTextCharFormat()
            number_format.setForeground(Qt.GlobalColor.darkMagenta)
        self.highlighting_rules.append((HIGHLIGHT_RULES["keywords"], keyword_format))
        self.highlighting_rules.append((HIGHLIGHT_RULES["strings"], string_format))
        self.highlighting_rules.append((HIGHLIGHT_RULES["comments"], comment_format))
        self.highlighting_rules.append((HIGHLIGHT_RULES["numbers"], number_format))

    def highlightBlock(self, text):
        """Применяет правила подсветки к блоку текста."""
        for pattern, format_ in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), format_)

    def rehighlight(self):
        """Перезапускает подсветку синтаксиса."""
        self.update_colors()
        super().rehighlight()