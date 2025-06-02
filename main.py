import sys
import keyboard
import time
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLineEdit, QCheckBox, QLabel, 
                             QDialog, QMessageBox, QInputDialog, QGroupBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class CommandThread(QThread):
    command_executed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, commands, loop_enabled, delay, typing_speed):
        super().__init__()
        self.commands = commands
        self.loop_enabled = loop_enabled
        self.delay = delay
        self.typing_speed = typing_speed
        self.running = True
        self.paused = False

    def run(self):
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
                
            # Выполнение команд в обратном порядке (снизу вверх)
            for cmd in reversed(self.commands):
                if not self.running or self.paused:
                    break
                    
                self.execute_command(cmd)
                time.sleep(self.delay)
                
            if not self.loop_enabled:
                break
                
        self.finished.emit()

    def execute_command(self, command):
        keyboard.press_and_release('t')
        keyboard.write(command, delay=1/self.typing_speed)
        keyboard.press_and_release('enter')
        self.command_executed.emit(f"Выполнено: {command}")

    def pause(self):
        self.paused = True
        
    def resume(self):
        self.paused = False
        
    def stop(self):
        self.running = False

class AddCommandDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить команду")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        
        self.command_input = QLineEdit(self)
        self.command_input.setPlaceholderText("Введите команду...")
        layout.addWidget(self.command_input)
        
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Добавить", self)
        self.add_button.clicked.connect(self.accept)
        button_layout.addWidget(self.add_button)
        
        self.cancel_button = QPushButton("Отмена", self)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_command(self):
        return self.command_input.text().strip()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Командный исполнитель")
        self.setFixedSize(600, 500)
        
        # Настройки по умолчанию
        self.delay = 3.0
        self.typing_speed = 100
        self.loop_enabled = False
        self.hotkey = 'f1'
        self.commands = []
        self.thread = None
        
        # Загрузка сохраненных данных
        self.load_settings()
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Секция настроек
        settings_group = QGroupBox("Настройки")
        settings_layout = QVBoxLayout()
        
        # Настройка горячей клавиши
        hotkey_layout = QHBoxLayout()
        self.hotkey_button = QPushButton(f"Горячая клавиша: {self.hotkey}", self)
        self.hotkey_button.clicked.connect(self.set_hotkey)
        hotkey_layout.addWidget(self.hotkey_button)
        settings_layout.addLayout(hotkey_layout)
        
        # Настройки скорости
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Задержка между командами (сек):"))
        
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.01, 600.0)
        self.delay_spin.setValue(self.delay)
        self.delay_spin.setSingleStep(0.01)
        speed_layout.addWidget(self.delay_spin)
        
        speed_layout.addWidget(QLabel("Скорость набора (симв/сек):"))
        
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(1, 1000)
        self.speed_spin.setValue(self.typing_speed)
        speed_layout.addWidget(self.speed_spin)
        
        settings_layout.addLayout(speed_layout)
        
        # Чекбокс повтора
        self.loop_checkbox = QCheckBox("Включить повтор (цикл)", self)
        self.loop_checkbox.setChecked(self.loop_enabled)
        settings_layout.addWidget(self.loop_checkbox)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # Секция команд
        commands_group = QGroupBox("Команды")
        commands_layout = QVBoxLayout()
        
        # Список команд
        self.command_list = QListWidget()
        self.update_command_list()
        commands_layout.addWidget(self.command_list)
        
        # Кнопки управления командами
        buttons_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Добавить команду", self)
        self.add_button.clicked.connect(self.add_command)
        buttons_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton("Изменить команду", self)
        self.edit_button.clicked.connect(self.edit_command)
        buttons_layout.addWidget(self.edit_button)
        
        self.remove_button = QPushButton("Удалить команду", self)
        self.remove_button.clicked.connect(self.remove_command)
        buttons_layout.addWidget(self.remove_button)
        
        commands_layout.addLayout(buttons_layout)
        commands_group.setLayout(commands_layout)
        main_layout.addWidget(commands_group)
        
        # Статус
        self.status_label = QLabel("Статус: Остановлено")
        main_layout.addWidget(self.status_label)
        
        central_widget.setLayout(main_layout)
        
        # Регистрация горячей клавиши
        self.register_hotkey()
        
    def add_command(self):
        dialog = AddCommandDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            command = dialog.get_command()
            if command:
                self.commands.append(command)
                self.update_command_list()
                self.save_settings()
    
    def edit_command(self):
        selected = self.command_list.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите команду для редактирования")
            return
            
        command, ok = QInputDialog.getText(
            self, 
            "Изменить команду", 
            "Введите новую команду:", 
            text=self.commands[selected]
        )
        
        if ok and command.strip():
            self.commands[selected] = command.strip()
            self.update_command_list()
            self.save_settings()
    
    def remove_command(self):
        selected = self.command_list.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите команду для удаления")
            return
            
        reply = QMessageBox.question(
            self, 
            "Подтверждение", 
            f"Удалить команду '{self.commands[selected]}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.commands[selected]
            self.update_command_list()
            self.save_settings()
    
    def update_command_list(self):
        self.command_list.clear()
        for command in self.commands:
            self.command_list.addItem(command)
    
    def set_hotkey(self):
        self.hotkey_button.setText("Нажмите новую клавишу...")
        keyboard.on_press(self.on_hotkey_press)
    
    def on_hotkey_press(self, event):
        keyboard.unhook_all()
        self.hotkey = event.name
        self.hotkey_button.setText(f"Горячая клавиша: {self.hotkey}")
        self.register_hotkey()
        self.save_settings()
    
    def register_hotkey(self):
        try:
            keyboard.remove_hotkey(self.hotkey)
        except:
            pass
        
        keyboard.add_hotkey(self.hotkey, self.toggle_execution)
    
    def toggle_execution(self):
        if self.thread and self.thread.isRunning():
            # Если выполнение активно - останавливаем
            self.thread.stop()
            self.thread.wait()
            self.thread = None
            self.status_label.setText("Статус: Остановлено")
        else:
            # Если не активно - запускаем
            if not self.commands:
                QMessageBox.warning(self, "Ошибка", "Нет команд для выполнения")
                return
                
            self.status_label.setText("Статус: Выполнение...")
            self.thread = CommandThread(
                self.commands,
                self.loop_checkbox.isChecked(),
                self.delay_spin.value(),
                self.speed_spin.value()
            )
            self.thread.command_executed.connect(self.status_label.setText)
            self.thread.finished.connect(lambda: self.status_label.setText("Статус: Завершено"))
            self.thread.start()
    
    def save_settings(self):
        data = {
            "hotkey": self.hotkey,
            "delay": self.delay_spin.value(),
            "typing_speed": self.speed_spin.value(),
            "loop_enabled": self.loop_checkbox.isChecked(),
            "commands": self.commands
        }
        
        try:
            with open("command_runner.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def load_settings(self):
        if not os.path.exists("command_runner.json"):
            return
            
        try:
            with open("command_runner.json", "r") as f:
                data = json.load(f)
                self.hotkey = data.get("hotkey", "f1")
                self.delay = data.get("delay", 3.0)
                self.typing_speed = data.get("typing_speed", 100.0)
                self.loop_enabled = data.get("loop_enabled", False)
                self.commands = data.get("commands", [])
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
    
    def closeEvent(self, event):
        # Остановка потока при закрытии
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait()
        
        # Сохранение настроек
        self.save_settings()
        event.accept()

if __name__ == "__main__":
    # Проверка прав администратора
    try:
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()
    except:
        pass
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
