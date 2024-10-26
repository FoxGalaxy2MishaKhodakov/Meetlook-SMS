import sys
import socket
import threading
from PyQt6 import QtWidgets, QtCore
import os

class ServerSelectionWindow(QtWidgets.QWidget):
    server_selected = QtCore.pyqtSignal(str, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Выбор сервера")
        self.setGeometry(100, 100, 300, 200)

        self.layout = QtWidgets.QVBoxLayout()

        self.server_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.server_list)

        self.add_server_button = QtWidgets.QPushButton("Добавить сервер")
        self.add_server_button.clicked.connect(self.add_server)
        self.layout.addWidget(self.add_server_button)

        self.remove_server_button = QtWidgets.QPushButton("Удалить сервер")
        self.remove_server_button.clicked.connect(self.remove_server)
        self.layout.addWidget(self.remove_server_button)

        self.connect_button = QtWidgets.QPushButton("Подключиться")
        self.connect_button.clicked.connect(self.connect_to_server)
        self.layout.addWidget(self.connect_button)

        self.setLayout(self.layout)
        self.load_servers()

    def get_servers_file_path(self):
        # Получаем путь к файлу servers.txt на одну директорию ниже
        return os.path.join(os.path.dirname(__file__), '../servers.txt')

    def load_servers(self):
        servers_file_path = self.get_servers_file_path()
        if os.path.exists(servers_file_path):
            with open(servers_file_path, "r") as f:
                servers = f.readlines()
                for server in servers:
                    ip, port = server.strip().split(":")
                    self.server_list.addItem(f"{ip}:{port}")

    def add_server(self):
        server_details, ok = QtWidgets.QInputDialog.getText(self, "Добавить сервер", "Введите IP:PORT")
        if ok and server_details:
            ip, port = server_details.split(":")
            self.server_list.addItem(f"{ip}:{port}")
            servers_file_path = self.get_servers_file_path()
            with open(servers_file_path, "a") as f:
                f.write(f"{ip}:{port}\n")

    def remove_server(self):
        selected_item = self.server_list.currentItem()
        if selected_item:
            self.server_list.takeItem(self.server_list.row(selected_item))
            self.save_servers()

    def save_servers(self):
        servers_file_path = self.get_servers_file_path()
        with open(servers_file_path, "w") as f:
            for i in range(self.server_list.count()):
                f.write(self.server_list.item(i).text() + "\n")

    def connect_to_server(self):
        selected_item = self.server_list.currentItem()
        if selected_item:
            ip, port = selected_item.text().split(":")
            self.server_selected.emit(ip, int(port))
            self.close()

class LoginRegisterWindow(QtWidgets.QWidget):
    login_successful = QtCore.pyqtSignal(socket.socket, str)  # Передаем имя пользователя в сигнал
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

        self.client_socket = None
        self.show_message_signal.connect(self.show_error_message)

    def connect_to_server(self, ip, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((ip, port))
            self.show()  # Показываем окно логина после подключения к серверу
        except Exception as e:
            self.show_message_signal.emit(f"Ошибка подключения: {e}")

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
            self.login_successful.emit(self.client_socket, username)
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
    new_message_signal = QtCore.pyqtSignal(str, bool)

    def __init__(self, client_socket, username):
        super().__init__()
        self.setWindowTitle("Чат")
        self.setGeometry(100, 100, 400, 500)

        self.layout = QtWidgets.QVBoxLayout()

        self.chat_area = QtWidgets.QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_area.setStyleSheet("""
            background-color: transparent;  /* Делаем фон прозрачным */
            border: none;                   /* Убираем рамку */
        """)
        self.chat_content = QtWidgets.QWidget()
        self.chat_layout = QtWidgets.QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_area.setWidget(self.chat_content)

        self.chat_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.layout.addWidget(self.chat_area)

        self.message_input = QtWidgets.QLineEdit()
        self.message_input.setPlaceholderText("Введите сообщение")
        self.message_input.setStyleSheet("""
            border: 2px solid #A5D6A7;      
            border-radius: 10px;            
            padding: 5px;                   
        """)
        self.layout.addWidget(self.message_input)

        self.setLayout(self.layout)

        self.client_socket = client_socket
        self.username = username

        self.new_message_signal.connect(self.add_message)

        # Подгружаем старые сообщения
        threading.Thread(target=self.load_old_messages, daemon=True).start()

        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.message_input.returnPressed.connect(self.send_message)

    def send_message(self):
        message = self.message_input.text()
        if message:
            self.client_socket.send(message.encode('utf-8'))
            self.message_input.clear()
            self.new_message_signal.emit(f"{self.username}: {message}", True)

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    if not message.startswith(f"{self.username}:"):
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
            message_layout.addStretch()
            message_layout.addWidget(message_label)
        else:
            message_label.setStyleSheet("background-color: #81D4FA; border-radius: 10px; padding: 10px;")
            message_layout.addWidget(message_label)
            message_layout.addStretch()

        self.chat_layout.addWidget(message_frame)
        self.chat_layout.addStretch(1)
        self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())

    def load_old_messages(self):
        self.client_socket.send("/load_old_messages".encode('utf-8'))
        old_messages = self.client_socket.recv(1024).decode('utf-8').strip().split("\n")
        for message in old_messages:
            self.new_message_signal.emit(message, False)


def main():
    app = QtWidgets.QApplication(sys.argv)
    server_selection_window = ServerSelectionWindow()
    login_register_window = LoginRegisterWindow()

    server_selection_window.server_selected.connect(login_register_window.connect_to_server)
    login_register_window.login_successful.connect(lambda s, u: login_register_window.open_chat(s, u))

    server_selection_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
