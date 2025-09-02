import telebot
from telebot import types
import sqlite3
import random
from flask import Flask
import threading
import time
import os

# تنظیمات
API_TOKEN = "8134200098:AAGGapErG9F0ek0lAEdrI53E5gzPDcObTQM"
ADMIN_ID = 7385601641
WEBHOOK_URL = "https://gogogo-mpge.onrender.com"
PORT = int(os.environ.get('PORT', 5000))  # استفاده از متغیر محیطی یا پیش‌فرض 5000
DB_NAME = "goyim.db"

# راه‌اندازی ربات و اپلیکیشن Flask
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# تنظیم پایگاه داده
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY,
                 name TEXT,
                 age INTEGER,
                 gender TEXT,
                 score INTEGER,
                 numeric_id INTEGER UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ads (
                 ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 category TEXT,
                 subcategory TEXT,
                 title TEXT,
                 description TEXT,
                 price TEXT,
                 address TEXT,
                 phone TEXT,
                 photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS shops (
                 shop_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 title TEXT,
                 description TEXT,
                 address TEXT,
                 phone TEXT,
                 photo TEXT,
                 score_sum INTEGER,
                 score_count INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS jokes (
                 joke_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS news (
                 news_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 content TEXT)''')
    conn.commit()
    conn.close()

init_db()

# دسته‌ها و زیرشاخه‌ها
CATEGORIES = {
    "املاک و مستغلات": ["خرید و فروش", "اجاره", "رهن"],
    "وسایل نقلیه": ["خودرو", "موتورسیکلت", "دوچرخه"],
    "لوازم شخصی و خانگی": ["مبلمان", "لوازم آشپزخانه", "دکوراسیون"],
    "پوشاک و مد": ["مردانه", "زنانه", "بچگانه"],
    "اسباب‌بازی و کودک": ["اسباب‌بازی", "لباس کودک", "لوازم کودک"],
    "الکترونیک و موبایل": ["موبایل", "لپ‌تاپ", "لوازم جانبی"],
    "ورزش و سرگرمی": ["لوازم ورزشی", "بازی‌های رومیزی", "تجهیزات کمپینگ"],
    "ابزار و تجهیزات": ["ابزار برقی", "ابزار دستی", "تجهیزات صنعتی"],
    "حیوانات خانگی و لوازم مربوطه": ["حیوانات", "لوازم حیوانات"],
    "خدمات آموزشی و کلاس‌ها": ["تدریس خصوصی", "کلاس‌های آنلاین", "کارگاه‌ها"],
    "خدمات و استخدام": ["خدمات فنی", "استخدام", "خدمات حرفه‌ای"],
    "گردشگری و سفر": ["تورهای مسافرتی", "اقامتگاه", "بلیط"],
    "هدایا و هنر و صنایع دستی": ["هدایا", "صنایع دستی", "آثار هنری"],
    "رستوران و غذا": ["رستوران", "کافی‌شاپ", "فست‌فود"],
    "کسب‌وکار و تبلیغات": ["تبلیغات", "خدمات تجاری", "سرمایه‌گذاری"]
}

SHOP_CATEGORIES = [
    "مواد غذایی و سوپرمارکت‌ها", "اسباب‌بازی و کودک", "پوشاک و لباس",
    "کفش و کیف", "الکترونیک و موبایل", "لوازم خانگی و آشپزخانه",
    "آرایشی و بهداشتی", "کتاب و نوشت‌افزار", "ابزار و یراق آلات",
    "گل و گیاه", "باشگاه و لوازم ورزشی", "موتور و دوچرخه و لوازم جانبی",
    "لوازم خودرو و تعمیرگاه‌ها", "رستوران و کافی‌شاپ", "گیم و سرگرمی"
]

# متغیرهای حالت کاربر
user_states = {}
user_data = {}

# توابع کمکی
def generate_numeric_id():
    while True:
        num_id = random.randint(100000, 999999)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT numeric_id FROM users WHERE numeric_id = ?", (num_id,))
        if not c.fetchone():
            conn.close()
            return num_id

def save_user(user_id, name, age, gender):
    numeric_id = generate_numeric_id()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, name, age, gender, score, numeric_id) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, name, age, gender, 0, numeric_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

# منوی اصلی
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("👤 پروفایل", "📢 دیوار گویم")
    keyboard.row("😂 جوک‌ها", "🏪 مغازه‌ها")
    keyboard.row("⭐ گویمی‌های برتر")
    return keyboard

# دکمه بازگشت
def back_button():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🔙 بازگشت به منوی اصلی")
    return keyboard

# دستور شروع
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if user:
        bot.send_message(user_id, "خوش برگشتی! به منوی اصلی برو:", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
    else:
        bot.send_message(user_id, "سلام! به ربات مگا گویم خوش آمدید 😊\nلطفاً نام خود را وارد کنید:")
        user_states[user_id] = "awaiting_name"
        user_data[user_id] = {}

# پنل ادمین
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "شما دسترسی به پنل ادمین ندارید!")
        return
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📰 اضافه کردن خبر", "👥 کاربران فعال")
    keyboard.row("🔙 بازگشت به منوی اصلی")
    bot.send_message(user_id, "به پنل ادمین خوش آمدید!", reply_markup=keyboard)
    user_states[user_id] = "admin_menu"

# مدیریت پیام‌ها
@bot.message_handler(content_types=['text', 'photo'])
def handle_message(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, "main_menu")
    text = message.text if message.text else ""

    if text == "🔙 بازگشت به منوی اصلی":
        bot.send_message(user_id, "به منوی اصلی برگشتید:", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
        return

    if state == "awaiting_name":
        user_data[user_id]['name'] = text
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(13, 71, 10):
            row = [str(x) for x in range(i, min(i+10, 71))]
            keyboard.row(*row)
        bot.send_message(user_id, "سن خود را انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "awaiting_age"
    elif state == "awaiting_age":
        try:
            age = int(text)
            if 13 <= age <= 70:
                user_data[user_id]['age'] = age
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("👦 پسر", "👧 دختر", "🌀 دیگر")
                bot.send_message(user_id, "جنسیت خود را انتخاب کنید:", reply_markup=keyboard)
                user_states[user_id] = "awaiting_gender"
            else:
                bot.send_message(user_id, "لطفاً عدد بین ۱۳ تا ۷۰ وارد کنید!")
        except ValueError:
            bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید!")
    elif state == "awaiting_gender":
        if text in ["👦 پسر", "👧 دختر", "🌀 دیگر"]:
            gender = text.split()[1] if " " in text else text
            user_data[user_id]['gender'] = gender
            save_user(user_id, user_data[user_id]['name'], user_data[user_id]['age'], gender)
            user = get_user(user_id)
            bot.send_message(user_id, f"پروفایل شما:\nنام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        else:
            bot.send_message(user_id, "لطفاً یکی از گزینه‌ها را انتخاب کنید!")
    elif state == "main_menu":
        if text == "👤 پروفایل":
            user = get_user(user_id)
            if user:
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("تغییر پروفایل")
                keyboard.row("🔙 بازگشت به منوی اصلی")
                bot.send_message(user_id, f"پروفایل شما:\nنام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}", reply_markup=keyboard)
                user_states[user_id] = "profile"
        elif text == "📢 دیوار گویم":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("اضافه کردن آگهی", "مشاهده آگهی‌ها", "آگهی‌های من")
            keyboard.row("🔙 بازگشت به منوی اصلی")
            bot.send_message(user_id, "📢 به دیوار گویم خوش آمدید!", reply_markup=keyboard)
            user_states[user_id] = "ad_wall"
        elif text == "😂 جوک‌ها":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("اضافه کردن جوک", "مشاهده جوک‌های من", "مشاهده جوک‌های دیگران")
            keyboard.row("🔙 بازگشت به منوی اصلی")
            bot.send_message(user_id, "😂 به بخش جوک‌ها خوش آمدید!", reply_markup=keyboard)
            user_states[user_id] = "jokes"
        elif text == "🏪 مغازه‌ها":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("مشاهده مغازه‌ها", "مغازه‌های من")
            if user_id == ADMIN_ID:
                keyboard.row("اضافه کردن مغازه")
            keyboard.row("🔙 بازگشت به منوی اصلی")
            bot.send_message(user_id, "🏪 به بخش مغازه‌ها خوش آمدید!", reply_markup=keyboard)
            user_states[user_id] = "shops"
        elif text == "⭐ گویمی‌های برتر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT name, score FROM users WHERE score >= 1000 ORDER BY score DESC")
            users = c.fetchall()
            conn.close()
            if users:
                msg = "⭐ گویمی‌های برتر:\n" + "\n".join([f"{u[0]}: {u[1]} امتیاز" for u in users])
            else:
                msg = "هنوز گویمی برتر نداریم!"
            bot.send_message(user_id, msg, reply_markup=back_button())
    elif state == "profile" and text == "تغییر پروفایل":
        bot.send_message(user_id, "نام جدید خود را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "edit_name"
    elif state == "edit_name":
        user_data[user_id] = {'name': text}
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(13, 71, 10):
            row = [str(x) for x in range(i, min(i+10, 71))]
            keyboard.row(*row)
        bot.send_message(user_id, "سن جدید را انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "edit_age"
    elif state == "edit_age":
        try:
            age = int(text)
            if 13 <= age <= 70:
                user_data[user_id]['age'] = age
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("👦 پسر", "👧 دختر", "🌀 دیگر")
                bot.send_message(user_id, "جنسیت جدید را انتخاب کنید:", reply_markup=keyboard)
                user_states[user_id] = "edit_gender"
            else:
                bot.send_message(user_id, "لطفاً عدد بین ۱۳ تا ۷۰ وارد کنید!")
        except ValueError:
            bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید!")
    elif state == "edit_gender":
        if text in ["👦 پسر", "👧 دختر", "🌀 دیگر"]:
            gender = text.split()[1] if " " in text else text
            user_data[user_id]['gender'] = gender
            save_user(user_id, user_data[user_id]['name'], user_data[user_id]['age'], gender)
            user = get_user(user_id)
            bot.send_message(user_id, f"پروفایل به‌روزرسانی شد:\nنام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        else:
            bot.send_message(user_id, "لطفاً یکی از گزینه‌ها را انتخاب کنید!")
    elif state == "ad_wall":
        if text == "اضافه کردن آگهی":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for cat in CATEGORIES:
                keyboard.row(cat)
            keyboard.row("🔙 بازگشت به منوی اصلی")
            bot.send_message(user_id, "یک دسته انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "ad_category"
        elif text == "مشاهده آگهی‌ها":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for cat in CATEGORIES:
                keyboard.row(cat)
            keyboard.row("🔙 بازگشت به منوی اصلی")
            bot.send_message(user_id, "یک دسته انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "view_ad_category"
        elif text == "آگهی‌های من":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM ads WHERE user_id = ?", (user_id,))
            ads = c.fetchall()
            conn.close()
            if ads:
                for ad in ads:
                    msg = f"عنوان: {ad[4]}\nدسته: {ad[2]}\nتوضیحات: {ad[5]}\nقیمت: {ad[6] or 'مشخص نشده'}\nآدرس: {ad[7] or 'مشخص نشده'}\nتلفن: {ad[8]}"
                    bot.send_message(user_id, msg)
                    if ad[9]:
                        bot.send_photo(user_id, ad[9])
            else:
                bot.send_message(user_id, "شما آگهی‌ای ندارید!")
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=back_button())
    elif state == "ad_category" and text in CATEGORIES:
        user_data[user_id] = {'category': text}
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for sub in CATEGORIES[text]:
            keyboard.row(sub)
        keyboard.row("🔙 بازگشت به منوی اصلی")
        bot.send_message(user_id, "یک زیرشاخه انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "ad_subcategory"
    elif state == "ad_subcategory" and text in CATEGORIES[user_data[user_id]['category']]:
        user_data[user_id]['subcategory'] = text
        bot.send_message(user_id, "عنوان آگهی را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "ad_title"
    elif state == "ad_title":
        user_data[user_id]['title'] = text
        bot.send_message(user_id, "توضیحات آگهی را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "ad_description"
    elif state == "ad_description":
        user_data[user_id]['description'] = text
        bot.send_message(user_id, "قیمت (اختیاری، در صورت عدم نیاز خالی بگذارید):", reply_markup=back_button())
        user_states[user_id] = "ad_price"
    elif state == "ad_price":
        user_data[user_id]['price'] = text if text else None
        bot.send_message(user_id, "آدرس (اختیاری، در صورت عدم نیاز خالی بگذارید):", reply_markup=back_button())
        user_states[user_id] = "ad_address"
    elif state == "ad_address":
        user_data[user_id]['address'] = text if text else None
        bot.send_message(user_id, "شماره تلفن را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "ad_phone"
    elif state == "ad_phone":
        user_data[user_id]['phone'] = text
        bot.send_message(user_id, "یک عکس برای آگهی ارسال کنید:", reply_markup=back_button())
        user_states[user_id] = "ad_photo"
    elif state == "ad_photo" and message.photo:
        user_data[user_id]['photo'] = message.photo[-1].file_id
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO ads (user_id, category, subcategory, title, description, price, address, phone, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (user_id, user_data[user_id]['category'], user_data[user_id]['subcategory'], user_data[user_id]['title'],
                   user_data[user_id]['description'], user_data[user_id]['price'], user_data[user_id]['address'],
                   user_data[user_id]['phone'], user_data[user_id]['photo']))
        c.execute("UPDATE users SET score = score + 5 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "آگهی با موفقیت ثبت شد!", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
    elif state == "view_ad_category" and text in CATEGORIES:
        user_data[user_id] = {'category': text}
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for sub in CATEGORIES[text]:
            keyboard.row(sub)
        keyboard.row("🔙 بازگشت به منوی اصلی")
        bot.send_message(user_id, "یک زیرشاخه انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "view_ad_subcategory"
    elif state == "view_ad_subcategory" and text in CATEGORIES[user_data[user_id]['category']]:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM ads WHERE category = ? AND subcategory = ?", (user_data[user_id]['category'], text))
        ads = c.fetchall()
        conn.close()
        if ads:
            for ad in ads:
                msg = f"عنوان: {ad[4]}\nتوضیحات: {ad[5]}\nقیمت: {ad[6] or 'مشخص نشده'}\nآدرس: {ad[7] or 'مشخص نشده'}\nتلفن: {ad[8]}"
                bot.send_message(user_id, msg)
                if ad[9]:
                    bot.send_photo(user_id, ad[9])
        else:
            bot.send_message(user_id, "آگهی‌ای در این دسته وجود ندارد!")
        bot.send_message(user_id, "انتخاب کنید:", reply_markup=back_button())
    elif state == "jokes":
        if text == "اضافه کردن جوک":
            bot.send_message(user_id, "جوک خود را وارد کنید:", reply_markup=back_button())
            user_states[user_id] = "add_joke"
        elif text == "مشاهده جوک‌های من":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT joke_id, content FROM jokes WHERE user_id = ?", (user_id,))
            jokes = c.fetchall()
            conn.close()
            if jokes:
                keyboard = types.InlineKeyboardMarkup()
                for joke in jokes:
                    keyboard.add(types.InlineKeyboardButton(f"جوک {joke[0]}", callback_data=f"view_joke_{joke[0]}"))
                bot.send_message(user_id, "جوک‌های شما:", reply_markup=keyboard)
            else:
                bot.send_message(user_id, "شما جوکی ندارید!")
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=back_button())
        elif text == "مشاهده جوک‌های دیگران":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT joke_id, content FROM jokes WHERE user_id != ?", (user_id,))
            jokes = c.fetchall()
            conn.close()
            if jokes:
                keyboard = types.InlineKeyboardMarkup()
                for joke in jokes:
                    keyboard.add(types.InlineKeyboardButton(f"جوک {joke[0]}", callback_data=f"view_joke_{joke[0]}"))
                bot.send_message(user_id, "جوک‌های دیگران:", reply_markup=keyboard)
            else:
                bot.send_message(user_id, "جوک دیگری وجود ندارد!")
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=back_button())
    elif state == "add_joke":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO jokes (user_id, content) VALUES (?, ?)", (user_id, text))
        c.execute("UPDATE users SET score = score + 5 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "جوک با موفقیت ثبت شد!", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
    elif state == "shops":
        if text == "مشاهده مغازه‌ها":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for cat in SHOP_CATEGORIES:
                keyboard.row(cat)
            keyboard.row("🔙 بازگشت به منوی اصلی")
            bot.send_message(user_id, "یک دسته انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "view_shop_category"
        elif text == "مغازه‌های من":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM shops WHERE user_id = ?", (user_id,))
            shops = c.fetchall()
            conn.close()
            if shops:
                for shop in shops:
                    avg_score = shop[7] / shop[8] if shop[8] > 0 else 0
                    msg = f"عنوان: {shop[2]}\nتوضیحات: {shop[3]}\nآدرس: {shop[4]}\nتلفن: {shop[5]}\nامتیاز: {avg_score:.1f}"
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton("⭐ امتیاز بده", callback_data=f"rate_shop_{shop[0]}"))
                    bot.send_message(user_id, msg, reply_markup=keyboard)
                    if shop[6]:
                        bot.send_photo(user_id, shop[6])
            else:
                bot.send_message(user_id, "شما مغازه‌ای ندارید!")
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=back_button())
        elif text == "اضافه کردن مغازه" and user_id == ADMIN_ID:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for cat in SHOP_CATEGORIES:
                keyboard.row(cat)
            keyboard.row("🔙 بازگشت به منوی اصلی")
            bot.send_message(user_id, "دسته مغازه را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "shop_category"
        elif text == "اضافه کردن مغازه":
            bot.send_message(user_id, "کاربر عزیز، برای اضافه کردن مکان و هماهنگی به این ایدی پیام دهید: @Sedayegoyom10", reply_markup=back_button())
    elif state == "shop_category" and text in SHOP_CATEGORIES:
        user_data[user_id] = {'category': text}
        bot.send_message(user_id, "عنوان مغازه را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "shop_title"
    elif state == "shop_title":
        user_data[user_id]['title'] = text
        bot.send_message(user_id, "توضیحات مغازه را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "shop_description"
    elif state == "shop_description":
        user_data[user_id]['description'] = text
        bot.send_message(user_id, "آدرس مغازه را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "shop_address"
    elif state == "shop_address":
        user_data[user_id]['address'] = text
        bot.send_message(user_id, "شماره تلفن مغازه را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "shop_phone"
    elif state == "shop_phone":
        user_data[user_id]['phone'] = text
        bot.send_message(user_id, "یک عکس برای مغازه ارسال کنید:", reply_markup=back_button())
        user_states[user_id] = "shop_photo"
    elif state == "shop_photo" and message.photo:
        user_data[user_id]['photo'] = message.photo[-1].file_id
        bot.send_message(user_id, "شناسه عددی صاحب مغازه را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "shop_owner_id"
    elif state == "shop_owner_id":
        try:
            owner_id = int(text)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE numeric_id = ?", (owner_id,))
            result = c.fetchone()
            if result:
                c.execute("INSERT INTO shops (user_id, title, description, address, phone, photo, score_sum, score_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (result[0], user_data[user_id]['title'], user_data[user_id]['description'], user_data[user_id]['address'],
                           user_data[user_id]['phone'], user_data[user_id]['photo'], 0, 0))
                conn.commit()
                bot.send_message(user_id, "مغازه با موفقیت ثبت شد!", reply_markup=main_menu())
                user_states[user_id] = "main_menu"
            else:
                bot.send_message(user_id, "شناسه عددی نامعتبر است!", reply_markup=back_button())
            conn.close()
        except ValueError:
            bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید!", reply_markup=back_button())
    elif state == "view_shop_category" and text in SHOP_CATEGORIES:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM shops WHERE title LIKE ?", (f"%{text}%",))
        shops = c.fetchall()
        conn.close()
        if shops:
            for shop in shops:
                avg_score = shop[7] / shop[8] if shop[8] > 0 else 0
                msg = f"عنوان: {shop[2]}\nتوضیحات: {shop[3]}\nآدرس: {shop[4]}\nتلفن: {shop[5]}\nامتیاز: {avg_score:.1f}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("⭐ امتیاز بده", callback_data=f"rate_shop_{shop[0]}"))
                bot.send_message(user_id, msg, reply_markup=keyboard)
                if shop[6]:
                    bot.send_photo(user_id, shop[6])
        else:
            bot.send_message(user_id, "مغازه‌ای در این دسته وجود ندارد!")
        bot.send_message(user_id, "انتخاب کنید:", reply_markup=back_button())
    elif state == "admin_menu":
        if text == "📰 اضافه کردن خبر":
            bot.send_message(user_id, "متن خبر را وارد کنید:", reply_markup=back_button())
            user_states[user_id] = "add_news"
        elif text == "👥 کاربران فعال":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT COUNT(*), SUM(CASE WHEN gender = 'پسر' THEN 1 ELSE 0 END), SUM(CASE WHEN gender = 'دختر' THEN 1 ELSE 0 END) FROM users")
            result = c.fetchone()
            msg = f"تعداد کاربران: {result[0]}\nپسران: {result[1]}\nدختران: {result[2]}"
            bot.send_message(user_id, msg, reply_markup=back_button())
    elif state == "add_news":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO news (content) VALUES (?)", (text,))
        c.execute("SELECT user_id FROM users")
        users = c.fetchall()
        conn.commit()
        conn.close()
        for user in users:
            bot.send_message(user[0], f"📰 خبر جدید:\n{text}")
        bot.send_message(user_id, "خبر با موفقیت ارسال شد!", reply_markup=back_button())
        user_states[user_id] = "admin_menu"

# مدیریت دکمه‌های اینلاین
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if call.data.startswith("view_joke_"):
        joke_id = int(call.data.split("_")[2])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT content, user_id FROM jokes WHERE joke_id = ?", (joke_id,))
        joke = c.fetchone()
        conn.close()
        keyboard = types.InlineKeyboardMarkup()
        if joke[1] == user_id:
            keyboard.add(types.InlineKeyboardButton("تغییر", callback_data=f"edit_joke_{joke_id}"))
            keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_joke_{joke_id}"))
        bot.send_message(user_id, joke[0], reply_markup=keyboard)
    elif call.data.startswith("edit_joke_"):
        joke_id = int(call.data.split("_")[2])
        user_data[user_id] = {'joke_id': joke_id}
        bot.send_message(user_id, "جوک جدید را وارد کنید:", reply_markup=back_button())
        user_states[user_id] = "edit_joke"
    elif call.data.startswith("delete_joke_"):
        joke_id = int(call.data.split("_")[2])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM jokes WHERE joke_id = ? AND user_id = ?", (joke_id, user_id))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "جوک حذف شد!", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
    elif call.data.startswith("rate_shop_"):
        shop_id = int(call.data.split("_")[2])
        user_data[user_id] = {'shop_id': shop_id}
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(0, 11):
            keyboard.row(str(i))
        keyboard.row("🔙 بازگشت به منوی اصلی")
        bot.send_message(user_id, "امتیاز (۰ تا ۱۰) را انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "rate_shop"

@bot.message_handler(content_types=['text'])
def handle_rating(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if state == "rate_shop":
        try:
            score = int(message.text)
            if 0 <= score <= 10:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("UPDATE shops SET score_sum = score_sum + ?, score_count = score_count + 1 WHERE shop_id = ?",
                          (score, user_data[user_id]['shop_id']))
                conn.commit()
                conn.close()
                bot.send_message(user_id, "امتیاز ثبت شد!", reply_markup=main_menu())
                user_states[user_id] = "main_menu"
            else:
                bot.send_message(user_id, "لطفاً عدد بین ۰ تا ۱۰ وارد کنید!")
        except ValueError:
            bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید!")
    elif state == "edit_joke":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE jokes SET content = ? WHERE joke_id = ? AND user_id = ?",
                  (message.text, user_data[user_id]['joke_id'], user_id))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "جوک به‌روزرسانی شد!", reply_markup=main_menu())
        user_states[user_id] = "main_menu"

# تنظیم وب‌هوک
@app.route('/')
def webhook():
    bot.remove_webhook()
    time.sleep(0.1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
    return "Webhook set", 200

@app.route(f'/{API_TOKEN}', methods=['POST'])
def get_message():
    from flask import request
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "!", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()