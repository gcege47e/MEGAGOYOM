```python
import telebot
import sqlite3
import os
import json
import random
import datetime
import jdatetime
from flask import Flask, request, render_template_string, jsonify
from flask_cors import CORS

# تنظیمات
API_TOKEN = "8134200098:AAGGapErG9F0ek0lAEdrI53E5gzPDcObTQM"
ADMIN_ID = 7385601641
WEBHOOK_URL = "https://gogogo-mpge.onrender.com"
PORT = 5000
DB_NAME = "goyim.db"

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")
app = Flask(__name__)
CORS(app)  # فعال‌سازی CORS برای درخواست‌های API

# ==========================
# دیتابیس
# ==========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER,
        gender TEXT,
        score INTEGER DEFAULT 0,
        unique_code INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT,
        title TEXT,
        description TEXT,
        price TEXT,
        address TEXT,
        phone TEXT,
        photo TEXT,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS lost (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        reward TEXT,
        address TEXT,
        phone TEXT,
        photo TEXT,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS jokes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        status TEXT DEFAULT 'pending'
    )""")
    conn.commit()
    conn.close()

init_db()

# ==========================
# هندلرهای ربات
# ==========================
user_states = {}

def get_main_menu(user_id):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("👤 پروفایل", "📢 دیوار گویم")
    keyboard.add("😂 جوک‌ها", "📌 گمشده‌ها")
    if user_id == ADMIN_ID:
        keyboard.add("🛠 مدیریت (ادمین)")
    return keyboard

@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    if user:
        bot.send_message(user_id, "سلام دوباره ✨\nبه منوی اصلی خوش اومدی!", reply_markup=get_main_menu(user_id))
    else:
        msg = bot.send_message(user_id, "👋 سلام! لطفا نام خود را وارد کنید:")
        user_states[user_id] = {"step": "name"}

@bot.message_handler(func=lambda m: m.chat.id in user_states)
def register_steps(message):
    user_id = message.chat.id
    state = user_states.get(user_id, {})

    if state.get("step") == "name":
        user_states[user_id]["name"] = message.text
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        ages = [str(i) for i in range(13, 71)]
        for i in range(0, len(ages), 8):
            markup.row(*ages[i:i+8])
        bot.send_message(user_id, "📅 سن خود را انتخاب کنید:", reply_markup=markup)
        user_states[user_id]["step"] = "age"

    elif state.get("step") == "age":
        if message.text.isdigit() and 13 <= int(message.text) <= 70:
            user_states[user_id]["age"] = int(message.text)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("👦 پسر", "👧 دختر", "🌀 دیگر")
            bot.send_message(user_id, "🚻 جنسیت خود را انتخاب کنید:", reply_markup=markup)
            user_states[user_id]["step"] = "gender"
        else:
            bot.send_message(user_id, "❌ لطفا یک عدد معتبر بین 13 تا 70 وارد کنید.")

    elif state.get("step") == "gender":
        gender = message.text
        if gender in ["👦 پسر", "👧 دختر", "🌀 دیگر"]:
            name = user_states[user_id]["name"]
            age = user_states[user_id]["age"]
            code = random.randint(10000, 99999)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO users (user_id, name, age, gender, unique_code, score) VALUES (?, ?, ?, ?, ?, ?)",
                      (user_id, name, age, gender, code, 0))
            conn.commit()
            conn.close()
            del user_states[user_id]
            bot.send_message(user_id, "✅ ثبت‌نام با موفقیت انجام شد!\nبه منوی اصلی خوش آمدید 🎉",
                             reply_markup=get_main_menu(user_id))
        else:
            bot.send_message(user_id, "❌ لطفا یکی از گزینه‌ها را انتخاب کنید.")

# ==========================
# پروفایل
# ==========================
@bot.message_handler(func=lambda m: m.text == "👤 پروفایل")
def profile_handler(message):
    user_id = message.chat.id
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, age, gender, score, unique_code FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    if user:
        text = f"👤 نام: {user[0]}\n📅 سن: {user[1]}\n🚻 جنسیت: {user[2]}\n⭐ امتیاز: {user[3]}\n🔑 کد: {user[4]}"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✏ تغییر نام", callback_data="edit_name"))
        markup.add(telebot.types.InlineKeyboardButton("✏ تغییر سن", callback_data="edit_age"))
        markup.add(telebot.types.InlineKeyboardButton("✏ تغییر جنسیت", callback_data="edit_gender"))
        bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def edit_profile(call):
    user_id = call.message.chat.id
    if call.data == "edit_name":
        msg = bot.send_message(user_id, "📝 لطفا نام جدید را وارد کنید:")
        user_states[user_id] = {"step": "edit_name"}
    elif call.data == "edit_age":
        msg = bot.send_message(user_id, "📅 لطفا سن جدید را وارد کنید:")
        user_states[user_id] = {"step": "edit_age"}
    elif call.data == "edit_gender":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("👦 پسر", "👧 دختر", "🌀 دیگر")
        bot.send_message(user_id, "🚻 جنسیت جدید خود را انتخاب کنید:", reply_markup=markup)
        user_states[user_id] = {"step": "edit_gender"}

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("step") in ["edit_name", "edit_age", "edit_gender"])
def save_profile_edits(message):
    user_id = message.chat.id
    step = user_states[user_id]["step"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if step == "edit_name":
        c.execute("UPDATE users SET name=? WHERE user_id=?", (message.text, user_id))
    elif step == "edit_age" and message.text.isdigit():
        c.execute("UPDATE users SET age=? WHERE user_id=?", (int(message.text), user_id))
    elif step == "edit_gender" and message.text in ["👦 پسر", "👧 دختر", "🌀 دیگر"]:
        c.execute("UPDATE users SET gender=? WHERE user_id=?", (message.text, user_id))
    conn.commit()
    conn.close()
    del user_states[user_id]
    bot.send_message(user_id, "✅ تغییرات ذخیره شد!", reply_markup=get_main_menu(user_id))

# ==========================
# جوک‌ها
# ==========================
@bot.message_handler(func=lambda m: m.text == "😂 جوک‌ها")
def jokes_handler(message):
    user_id = message.chat.id
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("➕ ارسال جوک", callback_data="send_joke"))
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT text FROM jokes WHERE status='approved' ORDER BY id DESC LIMIT 5")
    jokes = c.fetchall()
    conn.close()
    text = "😂 آخرین جوک‌های تایید شده:\n\n" + "\n\n".join([j[0] for j in jokes]) if jokes else "هیچ جوکی ثبت نشده."
    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "send_joke")
def send_joke_handler(call):
    user_id = call.message.chat.id
    msg = bot.send_message(user_id, "📝 جوک خود را ارسال کنید:")
    user_states[user_id] = {"step": "send_joke"}

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("step") == "send_joke")
def save_joke(message):
    user_id = message.chat.id
    text = message.text
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO jokes (user_id, text, status) VALUES (?, ?, 'pending')", (user_id, text))
    conn.commit()
    conn.close()
    del user_states[user_id]
    bot.send_message(user_id, "✅ جوک شما ارسال شد و پس از تایید نمایش داده می‌شود.")

# ==========================
# دیوار گویم
# ==========================
@bot.message_handler(func=lambda m: m.text == "📢 دیوار گویم")
def goyim_wall_handler(message):
    user_id = message.chat.id
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 باز کردن دیوار گویم", web_app=telebot.types.WebAppInfo(url=WEBHOOK_URL + "/webapp")))
    bot.send_message(user_id, "📢 به دیوار گویم خوش آمدید!", reply_markup=markup)

# ==========================
# گمشده‌ها
# ==========================
@bot.message_handler(func=lambda m: m.text == "📌 گمشده‌ها")
def lost_items_handler(message):
    user_id = message.chat.id
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 باز کردن گمشده‌ها", web_app=telebot.types.WebAppInfo(url=WEBHOOK_URL + "/webapp#/lost")))
    bot.send_message(user_id, "📌 به بخش گمشده‌ها خوش آمدید!", reply_markup=markup)

# ==========================
# پنل ادمین
# ==========================
@bot.message_handler(func=lambda m: m.text == "🛠 مدیریت (ادمین)" and m.chat.id == ADMIN_ID)
def admin_panel(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ مدیریت جوک‌ها", callback_data="admin_jokes"))
    markup.add(telebot.types.InlineKeyboardButton("🗑 مدیریت آگهی‌ها", callback_data="admin_ads"))
    markup.add(telebot.types.InlineKeyboardButton("🌐 باز کردن پنل مدیریت", web_app=telebot.types.WebAppInfo(url=WEBHOOK_URL + "/webapp#/admin")))
    bot.send_message(ADMIN_ID, "🛠 پنل مدیریت:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_jokes" and call.message.chat.id == ADMIN_ID)
def admin_jokes(call):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, text FROM jokes WHERE status='pending'")
    jokes = c.fetchall()
    conn.close()
    if not jokes:
        bot.send_message(ADMIN_ID, "هیچ جوک در انتظاری نیست.")
        return
    for j in jokes:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✔ تایید", callback_data=f"approve_joke_{j[0]}"))
        markup.add(telebot.types.InlineKeyboardButton("❌ رد", callback_data=f"reject_joke_{j[0]}"))
        bot.send_message(ADMIN_ID, f"جوک در انتظار:\n\n{j[1]}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_joke_") or call.data.startswith("reject_joke_"))
def handle_joke_decision(call):
    joke_id = int(call.data.split("_")[-1])
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if call.data.startswith("approve_joke_"):
        c.execute("UPDATE jokes SET status='approved' WHERE id=?", (joke_id,))
        bot.answer_callback_query(call.id, "جوک تایید شد ✅")
    else:
        c.execute("DELETE FROM jokes WHERE id=?", (joke_id,))
        bot.answer_callback_query(call.id, "جوک رد شد ❌")
    conn.commit()
    conn.close()
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.callback_query_handler(func=lambda call: call.data == "admin_ads" and call.message.chat.id == ADMIN_ID)
def admin_ads(call):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, title FROM ads")
    ads = c.fetchall()
    conn.close()
    if not ads:
        bot.send_message(ADMIN_ID, "هیچ آگهی ثبت نشده است.")
        return
    for ad in ads:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_ad_{ad[0]}"))
        bot.send_message(ADMIN_ID, f"آگهی: {ad[1]}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_ad_"))
def handle_ad_deletion(call):
    ad_id = int(call.data.split("_")[-1])
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM ads WHERE id=?", (ad_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "آگهی حذف شد 🗑")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

# ==========================
# APIهای وب‌اپ
# ==========================
@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id, name, age, gender, score, unique_code FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
        conn.close()
        if user:
            return jsonify({
                'user_id': user[0], 'name': user[1], 'age': user[2],
                'gender': user[3], 'score': user[4], 'unique_code': user[5]
            })
        return jsonify({'error': 'کاربر یافت نشد'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.get_json()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET name=?, age=?, gender=? WHERE user_id=?",
                  (data.get('name'), data.get('age'), data.get('gender'), user_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'کاربر به‌روزرسانی شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ads', methods=['GET'])
def get_ads():
    try:
        user_id = request.args.get('user_id')
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if user_id:
            c.execute("SELECT id, user_id, category, title, description, price, address, phone, photo, created_at FROM ads WHERE user_id=?", (user_id,))
        else:
            c.execute("SELECT id, user_id, category, title, description, price, address, phone, photo, created_at FROM ads")
        ads = c.fetchall()
        conn.close()
        return jsonify([{
            'id': ad[0], 'user_id': ad[1], 'category': ad[2], 'title': ad[3], 'description': ad[4],
            'price': ad[5], 'address': ad[6], 'phone': ad[7], 'photo': ad[8], 'created_at': ad[9]
        } for ad in ads])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ads/<int:ad_id>', methods=['GET'])
def get_ad(ad_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, user_id, category, title, description, price, address, phone, photo, created_at FROM ads WHERE id=?", (ad_id,))
        ad = c.fetchone()
        conn.close()
        if ad:
            return jsonify({
                'id': ad[0], 'user_id': ad[1], 'category': ad[2], 'title': ad[3], 'description': ad[4],
                'price': ad[5], 'address': ad[6], 'phone': ad[7], 'photo': ad[8], 'created_at': ad[9]
            })
        return jsonify({'error': 'آگهی یافت نشد'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ads', methods=['POST'])
def create_ad():
    try:
        data = request.get_json()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO ads (user_id, category, title, description, price, address, phone, photo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (data['user_id'], data['category'], data['title'], data['description'], data['price'],
                   data['address'], data['phone'], data['photo'], datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'message': 'آگهی ایجاد شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ads/<int:ad_id>', methods=['PUT'])
def update_ad(ad_id):
    try:
        data = request.get_json()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE ads SET category=?, title=?, description=?, price=?, address=?, phone=?, photo=? WHERE id=?",
                  (data['category'], data['title'], data['description'], data['price'], data['address'], data['phone'], data['photo'], ad_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'آگهی به‌روزرسانی شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ads/<int:ad_id>', methods=['DELETE'])
def delete_ad(ad_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM ads WHERE id=?", (ad_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'آگهی حذف شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lost', methods=['GET'])
def get_lost_items():
    try:
        user_id = request.args.get('user_id')
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if user_id:
            c.execute("SELECT id, user_id, title, description, reward, address, phone, photo, created_at FROM lost WHERE user_id=?", (user_id,))
        else:
            c.execute("SELECT id, user_id, title, description, reward, address, phone, photo, created_at FROM lost")
        items = c.fetchall()
        conn.close()
        return jsonify([{
            'id': item[0], 'user_id': item[1], 'title': item[2], 'description': item[3], 'reward': item[4],
            'address': item[5], 'phone': item[6], 'photo': item[7], 'created_at': item[8]
        } for item in items])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lost/<int:item_id>', methods=['GET'])
def get_lost_item(item_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, user_id, title, description, reward, address, phone, photo, created_at FROM lost WHERE id=?", (item_id,))
        item = c.fetchone()
        conn.close()
        if item:
            return jsonify({
                'id': item[0], 'user_id': item[1], 'title': item[2], 'description': item[3], 'reward': item[4],
                'address': item[5], 'phone': item[6], 'photo': item[7], 'created_at': item[8]
            })
        return jsonify({'error': 'گمشده یافت نشد'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lost', methods=['POST'])
def create_lost_item():
    try:
        data = request.get_json()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO lost (user_id, title, description, reward, address, phone, photo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (data['user_id'], data['title'], data['description'], data['reward'],
                   data['address'], data['phone'], data['photo'], datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'message': 'گمشده ایجاد شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lost/<int:item_id>', methods=['PUT'])
def update_lost_item(item_id):
    try:
        data = request.get_json()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE lost SET title=?, description=?, reward=?, address=?, phone=?, photo=? WHERE id=?",
                  (data['title'], data['description'], data['reward'], data['address'], data['phone'], data['photo'], item_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'گمشده به‌روزرسانی شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lost/<int:item_id>', methods=['DELETE'])
def delete_lost_item(item_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM lost WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'گمشده حذف شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jokes', methods=['GET'])
def get_jokes():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, user_id, text, status FROM jokes WHERE status='approved' ORDER BY id DESC LIMIT 5")
        jokes = c.fetchall()
        conn.close()
        return jsonify([{'id': j[0], 'user_id': j[1], 'text': j[2], 'status': j[3]} for j in jokes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jokes/pending', methods=['GET'])
def get_pending_jokes():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, user_id, text, status FROM jokes WHERE status='pending'")
        jokes = c.fetchall()
        conn.close()
        return jsonify([{'id': j[0], 'user_id': j[1], 'text': j[2], 'status': j[3]} for j in jokes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jokes', methods=['POST'])
def create_joke():
    try:
        data = request.get_json()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO jokes (user_id, text, status) VALUES (?, ?, 'pending')", (data['user_id'], data['text']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'جوک ارسال شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jokes/<int:joke_id>/approve', methods=['POST'])
def approve_joke(joke_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE jokes SET status='approved' WHERE id=?", (joke_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'جوک تایید شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jokes/<int:joke_id>', methods=['DELETE'])
def delete_joke(joke_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM jokes WHERE id=?", (joke_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'جوک حذف شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================
# مسیر وب‌اپ
# ==========================
@app.route('/webapp')
def webapp():
    return render_template_string("""
<!DOCTYPE html>
<html lang="fa">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>دیوار گویم</title>
  <script src="https://cdn.jsdelivr.net/npm/react@18.2.0/umd/react.production.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/react-dom@18.2.0/umd/react-dom.production.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/react-router-dom@6.26.2/dist/umd/react-router-dom.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/axios@1.7.7/dist/axios.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@babel/standalone@7.25.6/babel.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/framer-motion@11.11.7/dist/framer-motion.js"></script>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { font-family: 'Vazir', sans-serif; direction: rtl; }
    @font-face { font-family: 'Vazir'; src: url('https://cdn.fontcdn.ir/Fonts/Vazir/Vazir.woff') format('woff'); }
    .custom-button { @apply bg-green-500 text-white rounded-lg px-4 py-2 hover:bg-green-600 transition-all duration-300; }
    .card { @apply bg-white rounded-lg shadow-md hover:shadow-lg transition-all duration-300; }
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel">
    const { useState, useEffect } = React;
    const { BrowserRouter, Routes, Route, Link, useNavigate, useParams, useLocation } = ReactRouterDOM;
    const { motion } = window.FramerMotion;

    // دسته‌بندی‌های آگهی
    const categories = [
      'املاک', 'وسایل نقلیه', 'لوازم الکترونیکی', 'وسایل شخصی', 'سرگرمی و فراغت',
      'اجتماعی', 'برای کسب و کار', 'خدمات', 'استخدام و کاریابی', 'متفرقه'
    ];

    // کامپوننت اصلی
    function App() {
      const [user, setUser] = useState(null);
      const [search, setSearch] = useState('');
      const [error, setError] = useState(null);

      useEffect(() => {
        const userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 7385601641;
        axios.get(`/api/user/${userId}`)
          .then(res => setUser(res.data))
          .catch(err => {
            console.error('خطا در دریافت اطلاعات کاربر:', err);
            setError('خطا در بارگذاری اطلاعات کاربر');
          });
      }, []);

      return (
        <BrowserRouter>
          <div className="min-h-screen bg-gray-100">
            <nav className="bg-white shadow-md p-4 flex justify-between items-center">
              <Link to="/" className="text-xl font-bold text-green-500">دیوار گویم</Link>
              <div className="flex items-center gap-4">
                <input
                  type="text"
                  placeholder="جستجو در عنوان آگهی‌ها..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="border-2 border-blue-500 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <Link to="/lost" className="text-green-500 font-semibold">گمشده‌ها</Link>
                <Link to="/profile" className="text-green-500 font-semibold">پروفایل</Link>
                <Link to="/jokes" className="text-green-500 font-semibold">جوک‌ها</Link>
                {user?.user_id === 7385601641 && (
                  <Link to="/admin" className="text-green-500 font-semibold">مدیریت</Link>
                )}
              </div>
            </nav>
            {error && <div className="text-red-500 text-center p-4">{error}</div>}
            <Routes>
              <Route path="/" element={<Home search={search} userId={user?.user_id} />} />
              <Route path="/ad/:id" element={<AdDetails />} />
              <Route path="/lost" element={<LostList search={search} userId={user?.user_id} />} />
              <Route path="/lost/:id" element={<LostDetails />} />
              <Route path="/profile" element={<Profile user={user} setUser={setUser} />} />
              <Route path="/jokes" element={<Jokes userId={user?.user_id} />} />
              <Route path="/admin" element={<AdminPanel userId={user?.user_id} />} />
              <Route path="/add-item" element={<AddItemForm categories={categories} userId={user?.user_id} />} />
            </Routes>
          </div>
        </BrowserRouter>
      );
    }

    // صفحه اصلی (لیست آگهی‌ها)
    function Home({ search, userId }) {
      const [ads, setAds] = useState([]);
      const [error, setError] = useState(null);

      useEffect(() => {
        axios.get('/api/ads')
          .then(res => setAds(res.data))
          .catch(err => {
            console.error('خطا در دریافت آگهی‌ها:', err);
            setError('خطا در بارگذاری آگهی‌ها');
          });
      }, []);

      const filteredAds = ads.filter(ad => ad.title.toLowerCase().includes(search.toLowerCase()));

      return (
        <div className="container mx-auto p-4">
          {error && <div className="text-red-500 text-center p-4">{error}</div>}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {filteredAds.map(ad => (
              <Link to={`/ad/${ad.id}`} key={ad.id}>
                <motion.div className="card p-4" whileHover={{ scale: 1.05 }}>
                  <img src={ad.photo || 'https://via.placeholder.com/150'} alt={ad.title} className="w-full h-40 object-cover rounded-lg" />
                  <h2 className="text-lg font-semibold mt-2">{ad.title}</h2>
                  <p className="text-gray-600">{ad.price}</p>
                </motion.div>
              </Link>
            ))}
          </div>
          <Link to="/add-item?type=ad" className="fixed bottom-4 left-4 custom-button">+ افزودن آگهی</Link>
        </div>
      );
    }

    // صفحه جزئیات آگهی
    function AdDetails() {
      const { id } = useParams();
      const [ad, setAd] = useState(null);
      const [error, setError] = useState(null);

      useEffect(() => {
        axios.get(`/api/ads/${id}`)
          .then(res => setAd(res.data))
          .catch(err => {
            console.error('خطا در دریافت آگهی:', err);
            setError('خطا در بارگذاری آگهی');
          });
      }, [id]);

      if (error) return <div className="text-red-500 text-center p-4">{error}</div>;
      if (!ad) return <div>در حال بارگذاری...</div>;

      return (
        <motion.div
          className="container mx-auto p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="card p-6">
            <img src={ad.photo || 'https://via.placeholder.com/300'} alt={ad.title} className="w-full h-64 object-cover rounded-lg" />
            <h1 className="text-2xl font-bold mt-4">{ad.title}</h1>
            <p className="text-gray-600 mt-2">دسته‌بندی: {ad.category}</p>
            <p className="text-gray-600 mt-2">قیمت: {ad.price}</p>
            <p className="text-gray-600 mt-2">آدرس: {ad.address}</p>
            <p className="text-gray-600 mt-2">تلفن: {ad.phone}</p>
            <p className="text-gray-600 mt-2">توضیحات: {ad.description}</p>
            <p className="text-gray-500 text-sm mt-2">ایجاد شده در: {ad.created_at}</p>
          </div>
        </motion.div>
      );
    }

    // لیست گمشده‌ها
    function LostList({ search, userId }) {
      const [items, setItems] = useState([]);
      const [error, setError] = useState(null);

      useEffect(() => {
        axios.get('/api/lost')
          .then(res => setItems(res.data))
          .catch(err => {
            console.error('خطا در دریافت گمشده‌ها:', err);
            setError('خطا در بارگذاری گمشده‌ها');
          });
      }, []);

      const filteredItems = items.filter(item => item.title.toLowerCase().includes(search.toLowerCase()));

      return (
        <div className="container mx-auto p-4">
          {error && <div className="text-red-500 text-center p-4">{error}</div>}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {filteredItems.map(item => (
              <Link to={`/lost/${item.id}`} key={item.id}>
                <motion.div className="card p-4" whileHover={{ scale: 1.05 }}>
                  <img src={item.photo || 'https://via.placeholder.com/150'} alt={item.title} className="w-full h-40 object-cover rounded-lg" />
                  <h2 className="text-lg font-semibold mt-2">{item.title}</h2>
                  <p className="text-gray-600">مژدگانی: {item.reward}</p>
                </motion.div>
              </Link>
            ))}
          </div>
          <Link to="/add-item?type=lost" className="fixed bottom-4 left-4 custom-button">+ افزودن گمشده</Link>
        </div>
      );
    }

    // صفحه جزئیات گمشده
    function LostDetails() {
      const { id } = useParams();
      const [item, setItem] = useState(null);
      const [error, setError] = useState(null);

      useEffect(() => {
        axios.get(`/api/lost/${id}`)
          .then(res => setItem(res.data))
          .catch(err => {
            console.error('خطا در دریافت گمشده:', err);
            setError('خطا در بارگذاری گمشده');
          });
      }, [id]);

      if (error) return <div className="text-red-500 text-center p-4">{error}</div>;
      if (!item) return <div>در حال بارگذاری...</div>;

      return (
        <motion.div
          className="container mx-auto p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="card p-6">
            <img src={item.photo || 'https://via.placeholder.com/300'} alt={item.title} className="w-full h-64 object-cover rounded-lg" />
            <h1 className="text-2xl font-bold mt-4">{item.title}</h1>
            <p className="text-gray-600 mt-2">مژدگانی: {item.reward}</p>
            <p className="text-gray-600 mt-2">آدرس: {item.address}</p>
            <p className="text-gray-600 mt-2">تلفن: {item.phone}</p>
            <p className="text-gray-600 mt-2">توضیحات: {item.description}</p>
            <p className="text-gray-500 text-sm mt-2">ایجاد شده در: {item.created_at}</p>
          </div>
        </motion.div>
      );
    }

    // صفحه پروفایل
    function Profile({ user, setUser }) {
      const [ads, setAds] = useState([]);
      const [lostItems, setLostItems] = useState([]);
      const [editMode, setEditMode] = useState(null);
      const [editData, setEditData] = useState({ name: '', age: '', gender: '' });
      const [error, setError] = useState(null);
      const navigate = useNavigate();

      useEffect(() => {
        if (user) {
          setEditData({ name: user.name, age: user.age, gender: user.gender });
          axios.get(`/api/ads?user_id=${user.user_id}`)
            .then(res => setAds(res.data))
            .catch(err => {
              console.error('خطا در دریافت آگهی‌های کاربر:', err);
              setError('خطا در بارگذاری آگهی‌های کاربر');
            });
          axios.get(`/api/lost?user_id=${user.user_id}`)
            .then(res => setLostItems(res.data))
            .catch(err => {
              console.error('خطا در دریافت گمشده‌های کاربر:', err);
              setError('خطا در بارگذاری گمشده‌های کاربر');
            });
        }
      }, [user]);

      const handleEdit = (field) => {
        setEditMode(field);
      };

      const handleSave = () => {
        if (!editData.name.trim() || !editData.age || !editData.gender) {
          setError('همه فیلدها الزامی هستند');
          return;
        }
        axios.put(`/api/user/${user.user_id}`, editData)
          .then(() => {
            setUser({ ...user, ...editData });
            setEditMode(null);
            setError(null);
          })
          .catch(err => {
            console.error('خطا در به‌روزرسانی کاربر:', err);
            setError('خطا در ذخیره تغییرات');
          });
      };

      const handleDelete = (type, id) => {
        const endpoint = type === 'ad' ? `/api/ads/${id}` : `/api/lost/${id}`;
        axios.delete(endpoint)
          .then(() => {
            if (type === 'ad') {
              setAds(ads.filter(ad => ad.id !== id));
            } else {
              setLostItems(lostItems.filter(item => item.id !== id));
            }
            setError(null);
          })
          .catch(err => {
            console.error(`خطا در حذف ${type}:`, err);
            setError(`خطا در حذف ${type === 'ad' ? 'آگهی' : 'گمشده'}`);
          });
      };

      if (!user) return <div>در حال بارگذاری...</div>;

      return (
        <div className="container mx-auto p-4">
          {error && <div className="text-red-500 text-center p-4">{error}</div>}
          <motion.div className="card p-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
            <h1 className="text-2xl font-bold">پروفایل</h1>
            <div className="mt-4">
              {editMode === 'name' ? (
                <div>
                  <input
                    type="text"
                    value={editData.name}
                    onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                    className="border rounded-lg p-2 w-full"
                  />
                  <button onClick={handleSave} className="custom-button mt-2">ذخیره</button>
                </div>
              ) : (
                <p>نام: {user.name} <button onClick={() => handleEdit('name')} className="text-green-500">✏</button></p>
              )}
              {editMode === 'age' ? (
                <div>
                  <input
                    type="number"
                    value={editData.age}
                    onChange={(e) => setEditData({ ...editData, age: e.target.value })}
                    className="border rounded-lg p-2 w-full"
                  />
                  <button onClick={handleSave} className="custom-button mt-2">ذخیره</button>
                </div>
              ) : (
                <p>سن: {user.age} <button onClick={() => handleEdit('age')} className="text-green-500">✏</button></p>
              )}
              {editMode === 'gender' ? (
                <div>
                  <select
                    value={editData.gender}
                    onChange={(e) => setEditData({ ...editData, gender: e.target.value })}
                    className="border rounded-lg p-2 w-full"
                  >
                    <option value="👦 پسر">پسر</option>
                    <option value="👧 دختر">دختر</option>
                    <option value="🌀 دیگر">دیگر</option>
                  </select>
                  <button onClick={handleSave} className="custom-button mt-2">ذخیره</button>
                </div>
              ) : (
                <p>جنسیت: {user.gender} <button onClick={() => handleEdit('gender')} className="text-green-500">✏</button></p>
              )}
              <p>امتیاز: {user.score}</p>
              <p>کد: {user.unique_code}</p>
            </div>
            <h2 className="text-xl font-bold mt-6">آگهی‌های من</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
              {ads.map(ad => (
                <div key={ad.id} className="card p-4">
                  <img src={ad.photo || 'https://via.placeholder.com/150'} alt={ad.title} className="w-full h-40 object-cover rounded-lg" />
                  <h3 className="text-lg font-semibold mt-2">{ad.title}</h3>
                  <p className="text-gray-600">{ad.price}</p>
                  <div className="flex gap-2 mt-2">
                    <button onClick={() => navigate(`/add-item?type=ad&id=${ad.id}`)} className="custom-button">ویرایش</button>
                    <button onClick={() => handleDelete('ad', ad.id)} className="custom-button bg-red-500 hover:bg-red-600">حذف</button>
                  </div>
                </div>
              ))}
            </div>
            <h2 className="text-xl font-bold mt-6">گمشده‌های من</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
              {lostItems.map(item => (
                <div key={item.id} className="card p-4">
                  <img src={item.photo || 'https://via.placeholder.com/150'} alt={item.title} className="w-full h-40 object-cover rounded-lg" />
                  <h3 className="text-lg font-semibold mt-2">{item.title}</h3>
                  <p className="text-gray-600">مژدگانی: {item.reward}</p>
                  <div className="flex gap-2 mt-2">
                    <button onClick={() => navigate(`/add-item?type=lost&id=${item.id}`)} className="custom-button">ویرایش</button>
                    <button onClick={() => handleDelete('lost', item.id)} className="custom-button bg-red-500 hover:bg-red-600">حذف</button>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      );
    }

    // صفحه جوک‌ها
    function Jokes({ userId }) {
      const [jokes, setJokes] = useState([]);
      const [newJoke, setNewJoke] = useState('');
      const [error, setError] = useState(null);

      useEffect(() => {
        axios.get('/api/jokes')
          .then(res => setJokes(res.data))
          .catch(err => {
            console.error('خطا در دریافت جوک‌ها:', err);
            setError('خطا در بارگذاری جوک‌ها');
          });
      }, []);

      const handleSubmitJoke = () => {
        if (!newJoke.trim()) {
          setError('لطفا متن جوک را وارد کنید');
          return;
        }
        axios.post('/api/jokes', { user_id: userId, text: newJoke })
          .then(() => {
            setNewJoke('');
            setError(null);
            alert('جوک ارسال شد و پس از تایید نمایش داده می‌شود.');
          })
          .catch(err => {
            console.error('خطا در ارسال جوک:', err);
            setError('خطا در ارسال جوک');
          });
      };

      return (
        <div className="container mx-auto p-4">
          {error && <div className="text-red-500 text-center p-4">{error}</div>}
          <motion.div className="card p-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
            <h1 className="text-2xl font-bold">جوک‌ها</h1>
            <div className="mt-4">
              <textarea
                value={newJoke}
                onChange={(e) => setNewJoke(e.target.value)}
                placeholder="جوک خود را بنویسید..."
                className="border rounded-lg p-2 w-full"
              />
              <button onClick={handleSubmitJoke} className="custom-button mt-2">ارسال جوک</button>
            </div>
            <div className="mt-4">
              {jokes.map(joke => (
                <div key={joke.id} className="card p-4 mt-2">
                  <p>{joke.text}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      );
    }

    // پنل مدیریت
    function AdminPanel({ userId }) {
      const [jokes, setJokes] = useState([]);
      const [ads, setAds] = useState([]);
      const [error, setError] = useState(null);

      useEffect(() => {
        if (userId === 7385601641) {
          axios.get('/api/jokes/pending')
            .then(res => setJokes(res.data))
            .catch(err => {
              console.error('خطا در دریافت جوک‌های در انتظار:', err);
              setError('خطا در بارگذاری جوک‌های در انتظار');
            });
          axios.get('/api/ads')
            .then(res => setAds(res.data))
            .catch(err => {
              console.error('خطا در دریافت آگهی‌ها:', err);
              setError('خطا در بارگذاری آگهی‌ها');
            });
        }
      }, [userId]);

      const handleJokeAction = (jokeId, action) => {
        const endpoint = action === 'approve' ? `/api/jokes/${jokeId}/approve` : `/api/jokes/${jokeId}`;
        const method = action === 'approve' ? axios.post : axios.delete;
        method(endpoint)
          .then(() => {
            setJokes(jokes.filter(j => j.id !== jokeId));
            setError(null);
          })
          .catch(err => {
            console.error(`خطا در ${action === 'approve' ? 'تایید' : 'رد'} جوک:`, err);
            setError(`خطا در ${action === 'approve' ? 'تایید' : 'رد'} جوک`);
          });
      };

      const handleAdDelete = (adId) => {
        axios.delete(`/api/ads/${adId}`)
          .then(() => {
            setAds(ads.filter(ad => ad.id !== adId));
            setError(null);
          })
          .catch(err => {
            console.error('خطا در حذف آگهی:', err);
            setError('خطا در حذف آگهی');
          });
      };

      if (userId !== 7385601641) return <div className="text-red-500 text-center p-4">دسترسی غیرمجاز</div>;

      return (
        <div className="container mx-auto p-4">
          {error && <div className="text-red-500 text-center p-4">{error}</div>}
          <motion.div className="card p-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
            <h1 className="text-2xl font-bold">پنل مدیریت</h1>
            <h2 className="text-xl font-bold mt-6">جوک‌های در انتظار</h2>
            {jokes.map(joke => (
              <div key={joke.id} className="card p-4 mt-2">
                <p>{joke.text}</p>
                <div className="flex gap-2 mt-2">
                  <button onClick={() => handleJokeAction(joke.id, 'approve')} className="custom-button">تایید</button>
                  <button onClick={() => handleJokeAction(joke.id, 'reject')} className="custom-button bg-red-500 hover:bg-red-600">رد</button>
                </div>
              </div>
            ))}
            <h2 className="text-xl font-bold mt-6">مدیریت آگهی‌ها</h2>
            {ads.map(ad => (
              <div key={ad.id} className="card p-4 mt-2">
                <p>{ad.title}</p>
                <button onClick={() => handleAdDelete(ad.id)} className="custom-button bg-red-500 hover:bg-red-600">حذف</button>
              </div>
            ))}
          </motion.div>
        </div>
      );
    }

    // فرم افزودن/ویرایش آگهی یا گمشده
    function AddItemForm({ categories, userId }) {
      const navigate = useNavigate();
      const location = useLocation();
      const query = new URLSearchParams(location.search);
      const type = query.get('type') || 'ad';
      const id = query.get('id');
      const [formData, setFormData] = useState({
        category: categories[0], title: '', description: '', price: '', reward: '', address: '', phone: '', photo: ''
      });
      const [error, setError] = useState(null);

      useEffect(() => {
        if (id) {
          const endpoint = type === 'ad' ? `/api/ads/${id}` : `/api/lost/${id}`;
          axios.get(endpoint)
            .then(res => setFormData(res.data))
            .catch(err => {
              console.error(`خطا در دریافت ${type}:`, err);
              setError(`خطا در بارگذاری ${type === 'ad' ? 'آگهی' : 'گمشده'}`);
            });
        }
      }, [id, type]);

      const handleSubmit = () => {
        if (!formData.title.trim()) {
          setError('عنوان الزامی است');
          return;
        }
        const data = { ...formData, user_id: userId };
        if (id) {
          const endpoint = type === 'ad' ? `/api/ads/${id}` : `/api/lost/${id}`;
          axios.put(endpoint, data)
            .then(() => {
              navigate(type === 'ad' ? '/' : '/lost');
              setError(null);
            })
            .catch(err => {
              console.error(`خطا در ویرایش ${type}:`, err);
              setError(`خطا در ویرایش ${type === 'ad' ? 'آگهی' : 'گمشده'}`);
            });
        } else {
          const endpoint = type === 'ad' ? '/api/ads' : '/api/lost';
          axios.post(endpoint, data)
            .then(() => {
              navigate(type === 'ad' ? '/' : '/lost');
              setError(null);
            })
            .catch(err => {
              console.error(`خطا در افزودن ${type}:`, err);
              setError(`خطا در افزودن ${type === 'ad' ? 'آگهی' : 'گمشده'}`);
            });
        }
      };

      return (
        <div className="container mx-auto p-4">
          {error && <div className="text-red-500 text-center p-4">{error}</div>}
          <motion.div className="card p-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
            <h1 className="text-2xl font-bold">{id ? 'ویرایش' : 'افزودن'} {type === 'ad' ? 'آگهی' : 'گمشده'}</h1>
            <div className="mt-4 space-y-4">
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="border rounded-lg p-2 w-full"
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <input
                type="text"
                placeholder="عنوان"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="border rounded-lg p-2 w-full"
              />
              <textarea
                placeholder="توضیحات"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="border rounded-lg p-2 w-full"
              />
              {type === 'ad' ? (
                <input
                  type="text"
                  placeholder="قیمت"
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                  className="border rounded-lg p-2 w-full"
                />
              ) : (
                <input
                  type="text"
                  placeholder="مژدگانی"
                  value={formData.reward}
                  onChange={(e) => setFormData({ ...formData, reward: e.target.value })}
                  className="border rounded-lg p-2 w-full"
                />
              )}
              <input
                type="text"
                placeholder="آدرس"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                className="border rounded-lg p-2 w-full"
              />
              <input
                type="text"
                placeholder="تلفن"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="border rounded-lg p-2 w-full"
              />
              <input
                type="text"
                placeholder="لینک عکس"
                value={formData.photo}
                onChange={(e) => setFormData({ ...formData, photo: e.target.value })}
                className="border rounded-lg p-2 w-full"
              />
              <button onClick={handleSubmit} className="custom-button">ذخیره</button>
            </div>
          </motion.div>
        </div>
      );
    }

    // رندر اپلیکیشن
    ReactDOM.render(<App />, document.getElementById('root'));
  </script>
</body>
</html>
    """)

# ==========================
# وب‌هوک
# ==========================
@app.route("/" + API_TOKEN, methods=["POST"])
def getMessage():
    try:
        json_str = request.stream.read().decode("UTF-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "ok", 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/")
def webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL + "/" + API_TOKEN)
        return "وب‌هوک تنظیم شد!", 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)