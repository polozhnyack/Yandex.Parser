import sys
from PyQt6.QtWidgets import QTextEdit

class ConsoleOutput(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def write(self, text: str):
        self.append(text.strip())

    def flush(self):
        pass