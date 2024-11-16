import socket
import threading
import time
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

server_name = "Meetlook SMS Server"

# Загрузка плохих слов из файла
def load_bad_words():
    with open('badwords.txt', 'r', encoding='utf-8') as file:
        return [line.strip() for line in file.readlines()]

# Фильтрация плохих слов
def filter_message(message):
    bad_words = load_bad_words()
    for word in bad_words:
        censored_word = '*' * len(word)  # Создание цензурированного слова
        message = message.replace(word, censored_word)
    return message

# Подгрузка старых сообщений
def load_old_messages():
    cursor.execute("SELECT username, message FROM messages ORDER BY timestamp DESC LIMIT 50")  # получаем последние 50 сообщений
    return cursor.fetchall()

# Автоудаление сообщений
def auto_delete_old_messages():
    while True:
        cursor.execute("DELETE FROM messages WHERE timestamp < NOW() - INTERVAL 2 DAY")
        db.commit()
        time.sleep(86400)  # запускается каждые 24 часа

def handle_client(client_socket):
    username = None
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')

            if message == "/get_server_name":
                client_socket.send(server_name.encode('utf-8'))
                client_socket.close()
                return

            if message.startswith("/login"):
                _, username, password = message.split(" ")
                if login(username, password):
                    username = username
                    client_socket.send("Успешный вход!".encode('utf-8'))

                    # Подгрузка старых сообщений после успешного входа
                    old_messages = load_old_messages()
                    for user, msg in old_messages:
                        client_socket.send(f"{user}: {msg}\n".encode('utf-8'))

                else:
                    client_socket.send("Неверные учетные данные.".encode('utf-8'))
            elif message.startswith("/register"):
                _, username, password = message.split(" ")
                if register(username, password):
                    client_socket.send("Успешная регистрация!".encode('utf-8'))
                else:
                    client_socket.send("Ошибка регистрации.".encode('utf-8'))
            elif username:
                if message.strip() == "/load_old_messages":
                    continue  # Пропускаем это сообщение
                else:
                    # Фильтруем сообщение перед сохранением
                    filtered_message = filter_message(message)
                    save_message(username, filtered_message)
                    broadcast(f"{username}: {filtered_message}")
            else:
                client_socket.send("Сначала выполните вход.".encode('utf-8'))
        except:
            break

    client_socket.close()
    clients.remove(client_socket)

# Запуск автоудаления сообщений в отдельном потоке
auto_delete_thread = threading.Thread(target=auto_delete_old_messages)
auto_delete_thread.start()

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
