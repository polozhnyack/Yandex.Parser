import sys
import traceback
from PyQt6.QtWidgets import QMessageBox


def global_exception_hook(exc_type, exc_value, exc_traceback):
    """Обработчик глобальных исключений для PyQt"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"❌ Глобальная ошибка:\n{tb}")

    QMessageBox.critical(None, "Ошибка", f"{exc_value}")