from PyQt6.QtCore import QThread, QObject, pyqtSignal
from datetime import datetime
import logging

class WorkerSignals(QObject):
    """Класс для сигналов фоновых задач."""
    add_message = pyqtSignal(str, bool, datetime, str, str)
    update_status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(object)
    clear_prompt = pyqtSignal()

class Worker(QThread):
    """Класс для выполнения задач в фоновом потоке."""
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        """Запускает выполнение фоновой задачи."""
        try:
            result = self.func(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(f"Ошибка в фоновой задаче: {str(e)}")
            logging.error(f"Ошибка в фоновой задаче: {str(e)}")