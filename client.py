import sys
import socket
import threading
from PyQt6 import QtWidgets, QtCore


class LoginRegisterWindow(QtWidgets.QWidget):
    login_successful = QtCore.pyqtSignal(socket.socket)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход / Регистрация")
        self.setGeometry(100, 100, 300, 200)

        self.layout = QtWidgets.QVBoxLayout()

        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Имя пользователя")
        self.layout.addWidget(self.username_input)

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.password_input)

        self.login_button = QtWidgets.QPushButton("Войти")
        self.login_button.clicked.connect(self.login)
        self.layout.addWidget(self.login_button)

        self.register_button = QtWidgets.QPushButton("Регистрация")
        self.register_button.clicked.connect(self.register)
        self.layout.addWidget(self.register_button)

        self.setLayout(self.layout)

        # Подключение к серверу
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('127.0.0.1', 5555))

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        threading.Thread(target=self.check_login_response, args=(f"/login {username} {password}",), daemon=True).start()

    def register(self):
        username = self.username_input.text()
        password = self.password_input.text()
        threading.Thread(target=self.check_register_response, args=(f"/register {username} {password}",), daemon=True).start()

    def check_login_response(self, message):
        self.client_socket.send(message.encode('utf-8'))
        response = self.client_socket.recv(1024).decode('utf-8').strip()
        print(f"Login response: {response}")  # Отладочный вывод
        if response == "Успешный вход!":
            self.login_successful.emit(self.client_socket)  # Эмитируем сигнал при успешном входе
        else:
            self.show_error_message(response)

    def check_register_response(self, message):
        self.client_socket.send(message.encode('utf-8'))
        response = self.client_socket.recv(1024).decode('utf-8').strip()
        print(f"Register response: {response}")  # Отладочный вывод
        if response == "Успешная регистрация!":
            self.show_error_message("Регистрация успешна. Теперь вы можете войти.")
        else:
            self.show_error_message(response)

    def show_error_message(self, message):
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        error_dialog.setText(message)
        error_dialog.setWindowTitle("Ошибка")
        error_dialog.exec()

    def open_chat(self, client_socket):
        # Создаем окно чата в основном потоке
        self.chat_window = ChatWindow(client_socket)
        self.chat_window.show()
        self.close()  # Закрываем окно входа/регистрации


class ChatWindow(QtWidgets.QWidget):
    def __init__(self, client_socket):
        super().__init__()
        self.setWindowTitle("Чат")
        self.setGeometry(100, 100, 400, 300)

        self.layout = QtWidgets.QVBoxLayout()

        self.chat_area = QtWidgets.QTextEdit()
        self.chat_area.setReadOnly(True)
        self.layout.addWidget(self.chat_area)

        self.message_input = QtWidgets.QLineEdit()
        self.message_input.setPlaceholderText("Введите сообщение")
        self.layout.addWidget(self.message_input)

        self.send_button = QtWidgets.QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)

        self.setLayout(self.layout)

        self.client_socket = client_socket

        # Запуск потока для получения сообщений
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def send_message(self):
        message = self.message_input.text()
        if message:
            self.client_socket.send(message.encode('utf-8'))
            self.message_input.clear()

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    self.add_message_to_chat(message)
            except Exception as e:
                print(f"Ошибка при получении сообщения: {e}")
                break

    def add_message_to_chat(self, message):
        # Добавляем сообщение в область чата в основном потоке
        self.chat_area.append(message)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    login_register_window = LoginRegisterWindow()
    login_register_window.login_successful.connect(login_register_window.open_chat)  # Подключаем сигнал к методу
    login_register_window.show()

    sys.exit(app.exec())
