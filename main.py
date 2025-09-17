from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QMessageBox, QCheckBox
from PyQt6.QtGui import QIcon
import csv
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QSettings, QTimer, QThread

from PyQt6.QtWidgets import QHeaderView

from worker import ParserWorker
from console import ConsoleOutput

import sys

class ParserWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Парсер Яндекс.Услуг")

        self.settings = QSettings("Rogovoy", "YandexParser")

        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Поля ввода
        self.number_input = QLineEdit()
        self.limit_input = QLineEdit()
        self.url_input = QLineEdit()
        self.headless_checkbox = QCheckBox("Запускать браузер в фоновом режиме")

        # Загружаем сохранённые значения (если есть)
        self.number_input.setText(self.settings.value("number", ""))
        self.limit_input.setText(self.settings.value("limit", ""))
        self.url_input.setText(self.settings.value("url", ""))
        self.headless_checkbox.setChecked(self.settings.value("headless", False, type=bool))

        
        layout.addWidget(QLabel("Номер (П-61100XXX):"))
        layout.addWidget(self.number_input)
        layout.addWidget(QLabel("Предельное число (p):"))
        layout.addWidget(self.limit_input)
        layout.addWidget(QLabel("Ссылка: *"))
        layout.addWidget(self.url_input)

        layout.addWidget(self.headless_checkbox)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Запустить парсер")
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;  /* красивый зелёный */
                color: white;               /* текст белый */
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;  /* чуть темнее при наведении */
            }
        """)
        button_layout.addWidget(self.run_button)
        layout.addLayout(button_layout)

        hlayout = QHBoxLayout()
        hlayout.addStretch()
        self.counter_label = QLabel("Записей: 0")
        hlayout.addWidget(self.counter_label)
        layout.addLayout(hlayout)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Имя", "Телефон", "Гео"])
        header = self.table.horizontalHeader()
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked
        )
        self.table.setAlternatingRowColors(True)
        self.table.resizeRowsToContents()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)
        self.setLayout(layout)
        
        button_layout = QHBoxLayout()
        self.export_button = QPushButton("Экспорт в CSV")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;  /* синий */
                color: white;               /* текст белый */
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0069d9;  /* чуть темнее при наведении */
            }
        """)
        button_layout.addWidget(self.export_button)


        self.console = ConsoleOutput()
        layout.addWidget(QLabel("Консоль:"))
        layout.addWidget(self.console)

        sys.stdout = self.console
        sys.stderr = self.console

        layout.addLayout(button_layout)
        
        
        # Сигналы
        self.run_button.clicked.connect(self.run_parser)
        self.export_button.clicked.connect(self.export_to_csv)

    def closeEvent(self, event):
        self.settings.setValue("number", self.number_input.text())
        self.settings.setValue("limit", self.limit_input.text())
        self.settings.setValue("url", self.url_input.text())
        self.settings.setValue("headless", self.headless_checkbox.isChecked())
        super().closeEvent(event)


    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить как",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        with open(file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file, delimiter=";")

            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount() - 1)]
            writer.writerow(headers)

            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount() - 1):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                writer.writerow(row_data)

        print(f"Таблица сохранена в {file_path}")



    def run_parser(self):
        number = self.number_input.text()
        limit = self.limit_input.text()
        url = self.url_input.text()
        headless = self.headless_checkbox.isChecked()

        if not url:
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля!")
            return

        if limit:
            try:
                limit = int(limit)
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Предельное число должно быть числом!")
                return
        else:
            limit = None

        # создаём поток
        self.thread: QThread = QThread()
        self.worker = ParserWorker(url, limit, headless, number)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_parsing_done)
        self.worker.error.connect(self.on_parsing_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_parsing_done(self, table_data):
        self.table.setRowCount(len(table_data))
        for row_idx, row_data in enumerate(table_data):
            for col_idx, item in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(item))

        self.counter_label.setText(f"Записей: {len(table_data)}")
        QMessageBox.information(self, "Парсинг завершен", "Таблица обновлена!")

    def on_parsing_error(self, error_msg):
        QMessageBox.critical(self, "Ошибка парсинга", error_msg)



if __name__ == "__main__":
    app = QApplication([])
    window = ParserWindow()
    from errors import global_exception_hook

    sys.excepthook = global_exception_hook

    import os
    icon_path = os.path.join(os.path.dirname(__file__), "icon.icns")
    window.setWindowIcon(QIcon(icon_path))  

    window.show()
    app.exec()
