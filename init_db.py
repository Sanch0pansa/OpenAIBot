import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Создание таблицы пользователей
cursor.execute('''CREATE TABLE users
                  (user_id INTEGER PRIMARY KEY, username TEXT, role INTEGER)''')

# Создание таблицы сообщений
cursor.execute('''CREATE TABLE messages
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, response TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')

# Сохранение изменений в базе данных
conn.commit()

# Закрытие подключения к базе данных
cursor.close()
conn.close()