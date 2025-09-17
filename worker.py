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
            
            table_data = []
            for item in parsed_data:
                try:
                    name = str(item.get('name', ''))
                    phone = str(item.get('phone') or '')
                    geo = str(item.get('geo', ''))
                    table_data.append([f"{self.number} {name}", phone, geo])
                except Exception as e:
                    print(f"⚠️ Ошибка при обработке записи: {e}")
                    continue

            self.finished.emit(table_data)

        except Exception as e:
            import traceback
            traceback.print_exc()  # печатаем в консоль весь стек
            self.error.emit(str(e))