# Чтение токенов из файла

f = open("tokens.txt", "r")
tokens = {}
for key in f:
    tokens[key.split("=")[0]] = key.split("=")[1].rstrip("\n")

f.close()

# Инициализация бота

import telebot
import sqlite3
import openai
import requests

openai.api_key = tokens['AI']
bot = telebot.TeleBot(tokens['TG'])

# Подключение к базе данных
conn = sqlite3.connect('users.db')
cursor = conn.cursor()


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Добавление пользователя в базу данных, если его там нет
    if not get_user(message.chat.id):
        add_user(message.chat.id, message.from_user.first_name)



    bot.reply_to(message, "Привет!")


# Функция для добавления пользователя в базу данных
def add_user(user_id, username, role=0):
    # Подключение к базе данных
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Добавление пользователя в базу данных
    cursor.execute(f"INSERT INTO users (user_id, username, role) VALUES ({user_id}, '{username}', {role})")

    # Оповещение о добавлении пользователя
    cursor.execute('SELECT user_id FROM users WHERE role = ?', (2,))
    users = cursor.fetchall()

    for user in users:
        bot.send_message(chat_id=user[0],
                         text=f"Присоединился новый пользователь!\nЕго ник: <b>{username}</b>\nЕго id: <b>{user_id}</b>",
                         parse_mode="HTML")

    # Сохранение изменений в базе данных
    conn.commit()

    # Закрытие подключения к базе данных
    cursor.close()
    conn.close()


# Функция для получения информации о пользователе
def get_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


# Функция для получения роли пользователя
def get_user_role(user_id):
    user = get_user(user_id)
    return user[2] if user else 0


# Обработчик команды /setrole
@bot.message_handler(commands=['setrole'])
def set_user_role(message):
    # Проверка роли администратора
    if get_user_role(message.chat.id) < 2:
        bot.reply_to(message, "У вас нет прав на изменение ролей пользователей.")
        return

    # Разбор аргументов команды
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "Использование: /setrole user_id role")
        return
    user_id, role = args[1], args[2]

    # Обновление роли пользователя в базе данных
    conn = sqlite3.connect('users.db')
    conn.execute('UPDATE users SET role = ? WHERE user_id = ?', (role, user_id))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"Роль пользователя {user_id} изменена на {role}.")

# Обработчик команды /users
@bot.message_handler(commands=['users'])
def list_users(message):
    # Проверка роли администратора
    if get_user_role(message.chat.id) < 2:
        bot.reply_to(message, "У вас нет прав на просмотр списка пользователей.")
        return

    # Получение списка пользователей из базы данных
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    # Отправка списка пользователей в сообщении
    user_list = '\n'.join([f'{user[0]} {user[1]} - роль {user[2]}' for user in users])
    bot.reply_to(message, f'Список пользователей:\n{user_list}')


def get_user_messages(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT message, response FROM messages WHERE user_id = '{user_id}'")
    rows = cursor.fetchall()
    messages = []
    for row in rows:
        messages.append({'role': 'user', 'content': row[0]})
        messages.append({'role': 'assistant', 'content': row[1]})
    return messages


@bot.message_handler(commands=['draw'])
def draw_command(message):
    # Проверка роли пользователя
    if get_user_role(message.chat.id) < 1:
        bot.reply_to(message, "У вас нет прав на генерацию изображений")
        return

    # Получаем текст после команды /draw
    args = message.text.split(maxsplit=2)[1:]
    if len(args) == 1:
        bot.send_message(message.chat.id, "Введите количество изображений и текст для отображения")
        return
    try:
        count = int(args[0])

    except ValueError:
        bot.send_message(message.chat.id, "Количество изображений должно быть целым числом")
        return
    if count <= 0:
        bot.send_message(message.chat.id, "Количество изображений должно быть положительным числом")
        return
    if count > 5:
        bot.send_message(message.chat.id, "Количество изображений не должно превышать 5")
        return
    text = args[1]

    # Отправка ответа на сообщение
    msg = bot.reply_to(message, "Использование нейросети <b>OpenAI DALLE-2</b>\nОбработка запроса...", parse_mode="HTML")

    try:
        image_resp = openai.Image.create(prompt=text, n=count, size="512x512")

        bot.edit_message_text(chat_id=message.chat.id,
                              message_id=msg.id,
                              text=f"Сгенерировано {count} изображений:",
                              parse_mode='HTML')

        for image_url in image_resp['data']:
            # Получаем содержимое изображения по ссылке
            response = requests.get(image_url['url'])
            image_content = response.content

            # Отправляем изображение в чат
            bot.send_photo(chat_id=message.chat.id, photo=image_content)
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.id, text="⚠ Что-то пошло не так с ботом...")
        return

    # Отправляем сообщение пользователю с его вводом
    bot.send_message(chat_id=message.chat.id, text=f"Вы нарисовали: {text}")

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # Проверка роли пользователя
    if get_user_role(message.chat.id) < 1:
        bot.reply_to(message, "У вас нет прав на отправку сообщений.")
        return

    # Отправка ответа на сообщение
    msg = bot.reply_to(message, "Использование нейросети <b>OpenAI ChatGPT</b>\nОбработка запроса...", parse_mode="HTML")
    resp = "Ответ"
    try:
        msgs = [
            {"role": "system", "content": "You are helpful assistant bot, that provides ability of using OpenAI services by Telegram Bot. Current date: 12.05.2020"}
        ]
        msgs.extend(get_user_messages(message.chat.id))
        msgs.append({"role": "user", "content": message.text})
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.id, text="⚠ Что-то пошло не так с базой данных...")
        return

    try:
        completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=msgs)
        resp = completion.choices[0].message.content
        bot.edit_message_text(chat_id=message.chat.id,
                              message_id=msg.id,
                              text=format_code_blocks(resp),
                              parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.id, text="⚠ Что-то пошло не так с ботом...")
        return

    # Сохранение сообщения пользователя и ответа бота в базу данных
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (user_id, message, response) VALUES (?, ?, ?)',
                   (message.chat.id, message.text, resp))
    conn.commit()
    conn.close()

# Замена кода
import re

def format_code_blocks(text):
    # регулярное выражение для поиска блоков кода
    code_regex = r"(```)(.*?)(```)"

    # заменяем блоки кода на соответствующую разметку
    formatted_text = re.sub(code_regex, r"<pre><code>\2</code></pre>", text, flags=re.DOTALL)

    return formatted_text

# Запуск бота
bot.polling()