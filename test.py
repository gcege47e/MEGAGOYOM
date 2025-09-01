import telebot
from telebot import types
import sqlite3
import random
from flask import Flask, request
import os
import jdatetime

API_TOKEN = "8134200098:AAGGapErG9F0ek0lAEdrI53E5gzPDcObTQM"
ADMIN_ID = 7385601641

bot = telebot.TeleBot(API_TOKEN)
server = Flask(__name__)

# ===== دیتابیس =====
conn = sqlite3.connect('mega_goyom.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    name TEXT,
    age INTEGER,
    gender TEXT,
    user_code INTEGER,
    points INTEGER DEFAULT 0
)
''')
conn.commit()

# استیت برای ثبت‌نام موقت
user_state = {}

# ======== استارت و ثبت نام ========
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    user = cursor.fetchone()
    if user:
        send_main_menu(message)
    else:
        msg = bot.send_message(message.chat.id, "سلام 🌸\nلطفا نام خود را وارد کنید:")
        bot.register_next_step_handler(msg, process_name)

def process_name(message):
    user_state[message.from_user.id] = {"name": message.text}
    # کیبورد سن
    markup = types.ReplyKeyboardMarkup(row_width=7, resize_keyboard=True)
    for i in range(13, 71):
        markup.add(types.KeyboardButton(str(i)))
    msg = bot.send_message(message.chat.id, "سن خود را انتخاب کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_age)

def process_age(message):
    if not message.text.isdigit() or int(message.text) < 13 or int(message.text) > 70:
        msg = bot.send_message(message.chat.id, "سن معتبر نیست. لطفا عدد بین 13 تا 70 وارد کنید:")
        bot.register_next_step_handler(msg, process_age)
        return
    user_state[message.from_user.id]["age"] = int(message.text)
    # کیبورد جنسیت
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add("👦 پسر", "👧 دختر", "🌀 دیگر")
    msg = bot.send_message(message.chat.id, "جنسیت خود را انتخاب کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_gender)

def process_gender(message):
    if message.text not in ["👦 پسر", "👧 دختر", "🌀 دیگر"]:
        msg = bot.send_message(message.chat.id, "لطفا یکی از گزینه‌ها را انتخاب کنید:")
        bot.register_next_step_handler(msg, process_gender)
        return
    user_state[message.from_user.id]["gender"] = message.text
    # تولید شناسه رندوم
    user_code = random.randint(10000, 99999)
    user_state[message.from_user.id]["user_code"] = user_code
    data = user_state[message.from_user.id]
    cursor.execute("INSERT INTO users(telegram_id,name,age,gender,user_code) VALUES(?,?,?,?,?)",
                   (message.from_user.id, data["name"], data["age"], data["gender"], data["user_code"]))
    conn.commit()
    del user_state[message.from_user.id]
    bot.send_message(message.chat.id, f"ثبت نام شما با موفقیت انجام شد ✅\nشناسه شما: {user_code}")
    send_main_menu(message)

# ======== منوی اصلی ========
def send_main_menu(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("👤 پروفایل", "📢 دیوار گویم", "😂 جوک‌ها", "🏪 مغازه‌ها", "⭐ گویمی‌های برتر")
    bot.send_message(message.chat.id, "🌟 به مگا گویم خوش آمدید!\nلطفا یک گزینه را انتخاب کنید:", reply_markup=markup)

# ======== پروفایل ========
@bot.message_handler(func=lambda message: message.text == "👤 پروفایل")
def profile(message):
    cursor.execute("SELECT name, age, gender, points, user_code FROM users WHERE telegram_id=?", (message.from_user.id,))
    user = cursor.fetchone()
    if user:
        name, age, gender, points, user_code = user
        text = f"👤 پروفایل شما:\n\nنام: {name}\nسن: {age}\nجنسیت: {gender}\nامتیاز: {points}\nشناسه: {user_code}"
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add("🔙 بازگشت به منوی اصلی")
        bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔙 بازگشت به منوی اصلی")
def back_main(message):
    send_main_menu(message)

# ======== وب هوک ========
@server.route(f"/{API_TOKEN}", methods=['POST'])
def get_message():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://gogogo-mpge.onrender.com/{API_TOKEN}")
    return "Webhook set", 200

# ======== اجرا ========
if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))