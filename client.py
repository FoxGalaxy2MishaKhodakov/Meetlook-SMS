import sys
import socket
import threading
from PyQt6 import QtWidgets, QtCore


class LoginRegisterWindow(QtWidgets.QWidget):
    login_successful = QtCore.pyqtSignal(socket.socket, str)  # Добавим имя пользователя в сигнал
    show_message_signal = QtCore.pyqtSignal(str)

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

        self.show_message_signal.connect(self.show_error_message)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        threading.Thread(target=self.check_login_response, args=(f"/login {username} {password}", username), daemon=True).start()

    def register(self):
        username = self.username_input.text()
        password = self.password_input.text()
        threading.Thread(target=self.check_register_response, args=(f"/register {username} {password}",), daemon=True).start()

    def check_login_response(self, message, username):
        print(f"Отправка сообщения: {message}")
        self.client_socket.send(message.encode('utf-8'))
        response = self.client_socket.recv(1024).decode('utf-8').strip()
        print(f"Login response: {response}")
        if response == "Успешный вход!":
            self.login_successful.emit(self.client_socket, username)  # Передаем имя пользователя
        else:
            self.show_message_signal.emit(response)

    def check_register_response(self, message):
        print(f"Отправка сообщения: {message}")
        self.client_socket.send(message.encode('utf-8'))
        response = self.client_socket.recv(1024).decode('utf-8').strip()
        print(f"Register response: {response}")
        if response == "Успешная регистрация!":
            self.show_message_signal.emit("Регистрация успешна. Теперь вы можете войти.")
        else:
            self.show_message_signal.emit(response)

    def show_error_message(self, message):
        if message:
            error_dialog = QtWidgets.QMessageBox()
            error_dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            error_dialog.setText(message)
            error_dialog.setWindowTitle("Сообщение")
            error_dialog.exec()

    def open_chat(self, client_socket, username):
        self.chat_window = ChatWindow(client_socket, username)
        self.chat_window.show()
        self.close()


class ChatWindow(QtWidgets.QWidget):
    new_message_signal = QtCore.pyqtSignal(str, bool)  # Добавляем булев флаг для сообщений от пользователя

    def __init__(self, client_socket, username):
        super().__init__()
        self.setWindowTitle("Чат")
        self.setGeometry(100, 100, 400, 500)

        self.layout = QtWidgets.QVBoxLayout()

        # Создаём область чата с прокруткой
        self.chat_area = QtWidgets.QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_content = QtWidgets.QWidget()
        self.chat_layout = QtWidgets.QVBoxLayout(self.chat_content)
        self.chat_area.setWidget(self.chat_content)

        self.layout.addWidget(self.chat_area)

        # Поле ввода сообщения
        self.message_input = QtWidgets.QLineEdit()
        self.message_input.setPlaceholderText("Введите сообщение")
        self.layout.addWidget(self.message_input)

        # Кнопка отправки
        self.send_button = QtWidgets.QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)

        self.setLayout(self.layout)

        self.client_socket = client_socket
        self.username = username

        # Сигнал для добавления сообщений
        self.new_message_signal.connect(self.add_message)

        # Подгружаем старые сообщения
        threading.Thread(target=self.load_old_messages, daemon=True).start()

        # Запуск потока для получения сообщений
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def send_message(self):
        message = self.message_input.text()
        if message:
            # Отправляем сообщение на сервер
            self.client_socket.send(message.encode('utf-8'))
            self.message_input.clear()
            # Отправляем сигнал для отображения собственного сообщения
            self.new_message_signal.emit(f"{self.username}: {message}", True)

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    # Проверяем, не является ли это сообщение отправленным самим пользователем
                    # и не содержит ли оно слово "/load_old_messages"
                    if not message.startswith(f"{self.username}:") and "/load_old_messages" not in message:
                        # Обновляем интерфейс через сигнал (сообщение от других пользователей)
                        self.new_message_signal.emit(message, False)
            except Exception as e:
                print(f"Ошибка при получении сообщения: {e}")
                break


    def add_message(self, message, is_own_message):
        message_frame = QtWidgets.QFrame()
        message_layout = QtWidgets.QHBoxLayout(message_frame)

        message_label = QtWidgets.QLabel(message)
        if is_own_message:
            message_label.setStyleSheet("background-color: #A5D6A7; border-radius: 10px; padding: 10px;")
            message_layout.addStretch()  # Выравниваем по правому краю
            message_layout.addWidget(message_label)
        else:
            message_label.setStyleSheet("background-color: #81D4FA; border-radius: 10px; padding: 10px;")
            message_layout.addWidget(message_label)
            message_layout.addStretch()

        self.chat_layout.addWidget(message_frame)
        self.chat_layout.addStretch(1)
        self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())

    def load_old_messages(self):
        # Допустим, мы запрашиваем старые сообщения с сервера
        self.client_socket.send("/load_old_messages".encode('utf-8'))
        old_messages = self.client_socket.recv(1024).decode('utf-8').split("\n")
        for message in old_messages:
            if message:
                self.new_message_signal.emit(f"{message}", False)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    login_register_window = LoginRegisterWindow()
    login_register_window.login_successful.connect(login_register_window.open_chat)
    login_register_window.show()

    sys.exit(app.exec())
