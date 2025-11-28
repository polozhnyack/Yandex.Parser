from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QMessageBox, QCheckBox, QRadioButton
from PyQt6.QtGui import QIcon
import csv
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QSettings, QThread

from PyQt6.QtWidgets import QHeaderView

from worker import ParserWorker
from utils import copy_to_clipboard, merge_csv_records

import sys
from datetime import datetime

class ParserWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Парсер Яндекс.Услуг")

        self.settings = QSettings("Rogovoy", "YandexParser")

        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # === ПАПКА ХРАНЕНИЯ ===
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setText(self.settings.value("storage_folder", ""))
        self.folder_button = QPushButton("Выбрать папку")
        folder_layout.addWidget(QLabel("Папка хранения:"))
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.folder_button)
        layout.addLayout(folder_layout)
        
        # === ВЫБОР РЕЖИМА РАБОТЫ ===
        mode_layout = QHBoxLayout()
        self.mode_accumulate = QRadioButton("Накопить")
        self.mode_extract = QRadioButton("Извлечь")
        self.mode_accumulate.setChecked(True)
        mode_layout.addWidget(QLabel("Режим работы:"))
        mode_layout.addWidget(self.mode_accumulate)
        mode_layout.addWidget(self.mode_extract)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # === ПОЛЯ ВВОДА (видны только в режиме "Накопить") ===
        self.inputs_widget = QWidget()
        inputs_layout = QVBoxLayout(self.inputs_widget)
        
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

        inputs_layout.addWidget(QLabel("Предельное число (p):"))
        inputs_layout.addWidget(self.limit_input)
        inputs_layout.addWidget(QLabel("Ссылка: *"))
        inputs_layout.addWidget(self.url_input)
        inputs_layout.addWidget(self.headless_checkbox)
        
        layout.addWidget(self.inputs_widget)
        
        # === КНОПКИ УПРАВЛЕНИЯ ===
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Запустить парсер")
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;  /* красивый зелёный */
                color: white;               /* текст белый */
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;  /* чуть темнее при наведении */
            }
        """)
        button_layout.addWidget(self.run_button)
        
        self.copy_btn = QPushButton("Скопировать всё")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        button_layout.addWidget(self.copy_btn)
        
        self.export_button = QPushButton("Экспорт в CSV")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;  /* синий */
                color: white;               /* текст белый */
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0069d9;  /* чуть темнее при наведении */
            }
        """)
        button_layout.addWidget(self.export_button)
        
        button_layout.addStretch()
        
        self.counter_label = QLabel("Записей: 0")
        self.counter_label.setStyleSheet("font-weight: bold; color: #333;")
        button_layout.addWidget(self.counter_label)
        
        layout.addLayout(button_layout)
        
        # === ТАБЛИЦА ===
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Имя", "Телефон", "Гео"])
        
        # Стилизация таблицы как в ТЗ
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked
        )
        self.table.setAlternatingRowColors(True)

        
        # Настройка размеров колонок как в примере ТЗ
        self.table.setColumnWidth(0, 300)  # Широкая колонка для Имени
        self.table.setColumnWidth(1, 150)  # Узкая для Телефона
        self.table.setColumnWidth(2, 120)  # Узкая для Гео
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        # === СИГНАЛЫ ===
        # Переключение видимости полей ввода при смене режима
        self.mode_accumulate.toggled.connect(self.toggle_inputs_visibility)
        self.mode_extract.toggled.connect(self.toggle_inputs_visibility)


        self.run_button.clicked.connect(self.on_run_click)


        self.export_button.clicked.connect(self.export_to_csv)

        
        # Обработчик выбора папки
        self.folder_button.clicked.connect(self.select_storage_folder)
        self.copy_btn.clicked.connect(lambda: copy_to_clipboard(self.table))


    def on_run_click(self):
        if self.mode_accumulate.isChecked():
            self.run_parser()
        else:
            self.extract_data()

    def toggle_inputs_visibility(self):
        """Показывает/скрывает поля ввода в зависимости от выбранного режима"""
        if self.mode_accumulate.isChecked():
            self.inputs_widget.show()
            self.run_button.setText("Запустить парсер")
            self.url_input.setPlaceholderText("")
        else:
            self.inputs_widget.hide()
            self.run_button.setText("Извлечь данные")
            self.url_input.setPlaceholderText("Не требуется в режиме извлечения")

        # === Управление колонкой "Гео" ===
        self.table.setColumnHidden(2, self.mode_extract.isChecked())


    def select_storage_folder(self):
        """Диалог выбора папки хранения"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для хранения")
        if folder:
            self.folder_input.setText(folder)
            self.settings.setValue("storage_folder", folder)
        
        

    def closeEvent(self, event):
        self.settings.setValue("number", self.number_input.text())
        self.settings.setValue("limit", self.limit_input.text())
        self.settings.setValue("url", self.url_input.text())
        self.settings.setValue("headless", self.headless_checkbox.isChecked())
        super().closeEvent(event)


    def export_to_csv(self):
        storage_folder = self.folder_input.text().strip()

        if not storage_folder:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите папку хранения!")
            return

        filename = self.number_input.text().strip()
        if not filename:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        file_path = os.path.join(storage_folder, f"{filename}.csv")

        old_rows = []

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f, delimiter=";")
                    next(reader, None)  # пропускаем заголовки
                    for row in reader:
                        if len(row) >= 2:
                            old_rows.append((row[0], row[1]))
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка чтения старого файла:\n{str(e)}")
                return

        new_rows = []

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            phone_item = self.table.item(row, 1)

            name = name_item.text() if name_item else ""
            phone = phone_item.text() if phone_item else ""

            # Пропускаем пустые записи
            if not phone.strip():
                continue

            new_rows.append((name, phone))

        merged = merge_csv_records(old_rows, new_rows)

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Имя", "Телефон"])

                for phone, name in merged.items():
                    writer.writerow([name, phone])

            QMessageBox.information(self, "Успех", f"Таблица сохранена в:\n{file_path}")
            print(f"Таблица сохранена в {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении файла:\n{str(e)}")



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
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(item) if item is not None else ""))

        self.counter_label.setText(f"Записей: {len(table_data)}")
        QMessageBox.information(self, "Парсинг завершен", "Таблица обновлена!")

        # Автоматическое сохранение
        self.export_to_csv()

    def on_parsing_error(self, error_msg):
        QMessageBox.critical(self, "Ошибка парсинга", error_msg)

    def extract_data(self):
        storage_folder = self.folder_input.text().strip()
        number = self.number_input.text().strip()

        if not storage_folder:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите папку хранения!")
            return

        if not number:
            QMessageBox.warning(self, "Ошибка", "Введите номер (П-61100XXX)!")
            return

        file_path = os.path.join(storage_folder, f"{number}.csv")

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Ошибка", f"Файл не найден:\n{file_path}")
            return

        try:
            data = []
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=";")
                next(reader, None)

                for row in reader:
                    if len(row) >= 2:
                        name = row[0]
                        phone = row[1]
                        data.append([name, phone])


            self.table.setRowCount(len(data))
            for i, row in enumerate(data):
                for j, value in enumerate(row):
                    self.table.setItem(i, j, QTableWidgetItem(value))

            self.counter_label.setText(f"Записей: {len(data)}")

            QMessageBox.information(self, "Готово", "Данные успешно извлечены!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка чтения файла:\n{str(e)}")




if __name__ == "__main__":
    app = QApplication([])
    window = ParserWindow()
    from errors import global_exception_hook

    sys.excepthook = global_exception_hook

    import os
    icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    window.setWindowIcon(QIcon(icon_path))  

    window.show()
    app.exec()