from PyQt6.QtCore import QThread, pyqtSignal, QObject

from parser import parser_data

class ParserWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url, limit, headless, number):
        super().__init__()
        self.url = url
        self.limit = limit
        self.headless = headless
        self.number = number

    def run(self):
        try:
            parsed_data = parser_data(
                target_url=self.url,
                limit=self.limit,
                headless=self.headless,
            )
            table_data = [[f"{self.number} {item['name']}", item['phone'] or '', item['geo']] for item in parsed_data]
            self.finished.emit(table_data)
        except Exception as e:
            self.error.emit(str(e))
