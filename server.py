import socket
import threading
import mysql.connector
import bcrypt

# Подключение к базе данных
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="fucking_bd"
)
cursor = db.cursor()

def handle_client(client_socket):
    username = None
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message.startswith("/login"):
                _, username, password = message.split(" ")
                if login(username, password):
                    username = username
                    client_socket.send("Успешный вход!".encode('utf-8'))
                else:
                    client_socket.send("Неверные учетные данные.".encode('utf-8'))
            elif message.startswith("/register"):
                _, username, password = message.split(" ")
                if register(username, password):
                    client_socket.send("Успешная регистрация!".encode('utf-8'))
                else:
                    client_socket.send("Ошибка регистрации.".encode('utf-8'))
            elif username:
                # Сохраняем сообщение в базе данных
                save_message(username, message)
                broadcast(f"{username}: {message}")
            else:
                client_socket.send("Сначала выполните вход.".encode('utf-8'))
        except:
            break

    client_socket.close()
    clients.remove(client_socket)

def broadcast(message):
    for client in clients:
        client.send(message.encode('utf-8'))

def login(username, password):
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):  # Проверка хэша пароля
        return True
    return False

def register(username, password):
    try:
        # Хэширование пароля с добавлением соли
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password.decode('utf-8')))
        db.commit()
        return True
    except mysql.connector.Error:
        return False

def save_message(username, message):
    cursor.execute("INSERT INTO messages (username, message) VALUES (%s, %s)", (username, message))
    db.commit()

# Настройка сервера
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 5555))
server.listen(5)
print("Сервер запущен и ожидает подключения...")

clients = []

while True:
    client_socket, addr = server.accept()
    print(f"Подключен клиент: {addr}")
    clients.append(client_socket)
    thread = threading.Thread(target=handle_client, args=(client_socket,))
    thread.start()
