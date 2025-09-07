import telebot
from telebot import types
import sqlite3
import random
import re
import threading
import time
import os
from flask import Flask, request

# تنظیمات
API_TOKEN = "7996840669:AAEB2byd8vaa6xj94o42YkDB_loDPuawjZA"
ADMIN_ID = 7385601641
DB_NAME = "goyim.db"
WEBHOOK_URL = "https://goyomnama.onrender.com"
PORT = 5000

# تنظیم ربات
bot = telebot.TeleBot(API_TOKEN, threaded=True)

# ایجاد برنامه Flask
app = Flask(__name__)

# استیکرهای مخصوص
EMOJIS = {
    "profile": "👤",
    "places": "📍",
    "back": "🔙",
    "home": "🏠",
    "edit": "✏️",
    "delete": "🗑️",
    "add": "➕",
    "view": "👁️",
    "success": "✅",
    "error": "❌",
    "info": "ℹ️",
    "star": "⭐",
    "admin": "🔧",
    "news": "📰",
    "help": "❓",
    "link": "🔗",
    "document": "📋",
    "warning": "⚠️",
    "rating": "🌟",
    "group": "👥",
    "user": "👤",
    "send": "📤"
}

# پیام خوش‌آمدگویی و قوانین
WELCOME_MESSAGE = f"""
{EMOJIS['home']}به ربات گویم‌نما خوش آمدید! {EMOJIS['success']}

برای استفاده از این ربات، لطفاً قوانین زیر را مطالعه و تأیید کنید:

{EMOJIS['info']} قوانین استفاده از ربات:

1. در صورتی که صاحب یک مکان هستید، مسئولیت هرگونه مشکل یا اتفاق مرتبط با مکان ثبت‌شده بر عهده شماست.
2. از ارسال محتوای غیراخلاقی، توهین‌آمیز یا نقض‌کننده قوانین ربات جداً خودداری کنید.
3. اطلاعات مکان‌ها را با دقت و صحت وارد کنید.
4. هرگونه سوءاستفاده از اطلاعات مکان‌ها ممنوع بوده و منجر به مسدود شدن حساب کاربری شما خواهد شد.
5. در صورت نقض قوانین، حساب شما مسدود شده و برای رفع مسدودیت نیاز به پرداخت هزینه‌ای اندک خواهد بود.

{EMOJIS['warning']} توجه: هرگونه استفاده غیرمجاز از اطلاعات مکان‌ها پیگرد قانونی دارد.

لطفاً با دقت قوانین را مطالعه کرده و گزینه مناسب را انتخاب کنید:
"""

# متغیرهای حالت کاربر
user_states = {}
user_data = {}
blocked_users = set()

# تنظیم پایگاه داده
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY,
                 name TEXT,
                 age INTEGER,
                 gender TEXT,
                 score INTEGER DEFAULT 0,
                 numeric_id INTEGER UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS places (
                 place_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 category TEXT,
                 subcategory TEXT,
                 title TEXT,
                 description TEXT,
                 address TEXT,
                 phone TEXT,
                 photo TEXT,
                 morning_shift TEXT,
                 afternoon_shift TEXT,
                 rating_sum INTEGER DEFAULT 0,
                 rating_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS place_ratings (
                 place_id INTEGER,
                 user_id INTEGER,
                 rating INTEGER,
                 PRIMARY KEY (place_id, user_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS news (
                 news_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 content TEXT)''')
    try:
        c.execute("ALTER TABLE places ADD COLUMN subcategory TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

# دسته‌بندی مکان‌ها
PLACE_CATEGORIES = {
    "خوراکی و نوشیدنی": ["رستوران‌ها", "کافه و کافی‌شاپ", "بستنی‌فروشی و آبمیوه‌فروشی", "شیرینی‌پزی و نانوایی", "سفره‌خانه و چایخانه", "فودکورت"],
    "خرید و فروش": ["پاساژها و مراکز خرید", "سوپرمارکت و هایپرمارکت", "فروشگاه زنجیره‌ای", "بازار سنتی", "فروشگاه پوشاک و کیف و کفش", "فروشگاه لوازم خانگی و الکترونیک", "فروشگاه لوازم ورزشی", "کتاب‌فروشی", "مغازه موبایل و لپ‌تاپ", "گل‌فروشی"],
    "درمان و سلامت": ["بیمارستان", "درمانگاه و کلینیک", "داروخانه", "دندان‌پزشکی", "آزمایشگاه پزشکی", "کلینیک زیبایی", "مراکز فیزیوتراپی", "دامپزشکی"],
    "ورزش و سرگرمی": ["باشگاه ورزشی", "استخر و مجموعه ورزشی", "سالن فوتسال و بسکتبال", "سینما و تئاتر", "شهربازی", "بیلیارد و بولینگ", "مراکز تفریحی خانوادگی", "مراکز فرهنگی و هنری"],
    "اقامت و سفر": ["هتل", "مسافرخانه و مهمانپذیر", "اقامتگاه بوم‌گردی", "ویلا و سوئیت اجاره‌ای", "کمپینگ", "آژانس مسافرتی", "ایستگاه قطار و اتوبوس", "فرودگاه"],
    "خدمات عمومی و اداری": ["بانک و خودپرداز", "اداره پست", "دفاتر پیشخوان خدمات", "شهرداری", "اداره برق، آب، گاز", "پلیس +۱۰", "دادگاه", "کلانتری و پاسگاه"],
    "خدمات شهری و حمل‌ونقل": ["پمپ بنزین و CNG", "کارواش", "تعمیرگاه خودرو و موتورسیکلت", "تاکسی‌سرویس و تاکسی اینترنتی", "پارکینگ", "مکانیکی و برق خودرو", "لاستیک‌فروشی"],
    "آموزش و فرهنگ": ["مدرسه", "دانشگاه", "آموزشگاه زبان", "آموزشگاه فنی‌وحرفه‌ای", "کتابخانه", "فرهنگسرا", "موزه و گالری"],
    "مذهبی و معنوی": ["مسجد", "حسینیه و هیئت", "کلیسا", "کنیسه", "معابد"],
    "طبیعت و تفریح آزاد": ["پارک و بوستان", "باغ وحش", "باغ گیاه‌شناسی", "پیست دوچرخه‌سواری", "کوهستان و مسیرهای طبیعت‌گردی", "ساحل و دریاچه"],
    "کسب‌وکار و حرفه‌ای": ["دفتر کار و شرکت‌ها", "کارخانه‌ها", "کارگاه‌ها", "دفاتر املاک", "دفاتر بیمه"]
}

# متغیرهای کمکی
def generate_numeric_id():
    while True:
        num_id = random.randint(100000, 999999)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT numeric_id FROM users WHERE numeric_id = ?", (num_id,))
        if not c.fetchone():
            conn.close()
            return num_id
        conn.close()

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

def get_user_by_numeric_id(numeric_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE numeric_id = ?", (numeric_id,))
    user = c.fetchone()
    conn.close()
    return user

def is_user_blocked(user_id):
    return user_id in blocked_users

def block_user(user_id):
    blocked_users.add(user_id)

def unblock_user(user_id):
    blocked_users.discard(user_id)

# منوها
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['profile']} پروفایل")
    keyboard.row(f"{EMOJIS['places']} مکان‌ها", f"{EMOJIS['rating']} مکان‌های برتر")
    keyboard.row(f"{EMOJIS['star']} کاربران برتر")
    keyboard.row(f"{EMOJIS['link']} لینک‌ها", f"{EMOJIS['help']} راهنما")
    return keyboard

def profile_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مشاهده پروفایل")
    keyboard.row("تغییر نام", "تغییر سن", "تغییر جنسیت")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def get_place_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['add']} اضافه کردن مکان")
    keyboard.row(f"{EMOJIS['view']} مشاهده مکان‌ها", f"{EMOJIS['view']} مکان‌های من")
    keyboard.row(f"{EMOJIS['view']} جستجو")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def back_home_buttons():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def back_button_only():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def skip_button():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("رد کردن")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def search_result_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("جستجو دوباره")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    keyboard.row(f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def admin_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("👥 کاربران فعال")
    keyboard.row(f"{EMOJIS['news']} ارسال خبر")
    keyboard.row("🛡️ مدیر مکان‌ها")
    keyboard.row("🚫 مسدود کردن کاربر", "🔓 رفع مسدودیت")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def admin_news_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['group']} ارسال خبر گروهی")
    keyboard.row(f"{EMOJIS['user']} ارسال خبر به کاربر")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def edit_place_menu(place_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['edit']} ویرایش عنوان", f"{EMOJIS['edit']} ویرایش توضیحات")
    keyboard.row(f"{EMOJIS['edit']} ویرایش آدرس", f"{EMOJIS['edit']} ویرایش تماس")
    keyboard.row(f"{EMOJIS['edit']} ویرایش عکس")
    keyboard.row(f"{EMOJIS['edit']} ویرایش شیفت صبح", f"{EMOJIS['edit']} ویرایش شیفت عصر")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

# دستور شروع
@bot.message_handler(commands=['start', 'admin'])
def start(message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.")
        return
    
    if message.text == '/admin' and user_id == ADMIN_ID:
        bot.send_message(user_id, f"{EMOJIS['admin']} به پنل ادمین خوش آمدید!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
        return
    
    user = get_user(user_id)
    if user:
        bot.send_message(user_id, f"{EMOJIS['success']} خوش برگشتی! {EMOJIS['home']}", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['success']} پذیرفتن", callback_data="accept_terms"))
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['error']} نپذیرفتن", callback_data="decline_terms"))
        bot.send_message(user_id, WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=keyboard)
        user_states[user_id] = "awaiting_terms"

# مدیریت پیام‌ها
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.")
        return
    
    state = user_states.get(user_id, "awaiting_terms")
    text = message.text if message.text else ""
    
    # حالت‌های مختلف
    if state == "awaiting_name":
        if len(text) < 2:
            bot.send_message(user_id, f"{EMOJIS['error']} نام باید حداقل ۲ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        user_data[user_id]['name'] = text
        bot.send_message(user_id, f"{EMOJIS['profile']} سن خود را وارد کنید:")
        user_states[user_id] = "awaiting_age"
    
    elif state == "awaiting_age":
        if not text.isdigit() or int(text) < 1 or int(text) > 150:
            bot.send_message(user_id, f"{EMOJIS['error']} سن نامعتبر است. لطفاً یک عدد بین ۱ تا ۱۵۰ وارد کنید:")
            return
        
        user_data[user_id]['age'] = int(text)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("مرد", "زن")
        keyboard.row("سایر")
        bot.send_message(user_id, f"{EMOJIS['profile']} جنسیت خود را انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "awaiting_gender"
    
    elif state == "awaiting_gender":
        if text not in ["مرد", "زن", "سایر"]:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=back_button_only())
            return
        
        user_data[user_id]['gender'] = text
        save_user(user_id, user_data[user_id]['name'], user_data[user_id]['age'], user_data[user_id]['gender'])
        bot.send_message(user_id, f"{EMOJIS['success']} ثبت نام شما با موفقیت انجام شد!", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
    
    elif state == "main_menu":
        if text == f"{EMOJIS['profile']} پروفایل":
            user = get_user(user_id)
            if user:
                profile_text = f"""
{EMOJIS['profile']} پروفایل کاربری:
نام: {user[1]}
سن: {user[2]}
جنسیت: {user[3]}
امتیاز: {user[4]}
کد عددی: {user[5]}
"""
                bot.send_message(user_id, profile_text, reply_markup=profile_menu())
                user_states[user_id] = "profile_menu"
        
        elif text == f"{EMOJIS['places']} مکان‌ها":
            bot.send_message(user_id, f"{EMOJIS['places']} مدیریت مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        
        elif text == f"{EMOJIS['rating']} مکان‌های برتر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("""
                SELECT place_id, title, rating_count, 
                       CASE WHEN rating_count > 0 THEN rating_sum * 1.0 / rating_count ELSE 0 END as avg_rating
                FROM places 
                WHERE rating_count > 0 
                ORDER BY avg_rating DESC 
                LIMIT 10
            """)
            top_places = c.fetchall()
            conn.close()
            
            if top_places:
                response = f"{EMOJIS['rating']} برترین مکان‌ها بر اساس امتیاز:\n\n"
                for i, place in enumerate(top_places, 1):
                    avg_rating = place[3]
                    response += f"{i}. {place[1]} - ⭐ {avg_rating:.1f} ({place[2]} امتیاز)\n"
                bot.send_message(user_id, response, reply_markup=main_menu())
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} هنوز هیچ مکان امتیازدهی نشده است.", reply_markup=main_menu())
        
        elif text == f"{EMOJIS['star']} کاربران برتر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_id, name, score FROM users ORDER BY score DESC LIMIT 10")
            top_users = c.fetchall()
            conn.close()
            
            if top_users:
                response = f"{EMOJIS['star']} برترین کاربران بر اساس امتیاز:\n\n"
                for i, user in enumerate(top_users, 1):
                    response += f"{i}. {user[1]} - ⭐ {user[2]} امتیاز\n"
                bot.send_message(user_id, response, reply_markup=main_menu())
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} هنوز هیچ کاربری امتیازی ندارد.", reply_markup=main_menu())
        
        elif text == f"{EMOJIS['link']} لینک‌ها":
            bot.send_message(user_id, f"{EMOJIS['link']} لینک‌های مفید:\n\n- کانال ما: @goyim_channel\n- پشتیبانی: @goyim_support", reply_markup=main_menu())
        
        elif text == f"{EMOJIS['help']} راهنما":
            help_text = f"""
{EMOJIS['help']} راهنمای استفاده از ربات:

- {EMOJIS['profile']} پروفایل: مشاهده و ویرایش اطلاعات کاربری
- {EMOJIS['places']} مکان‌ها: اضافه کردن و مدیریت مکان‌ها
- {EMOJIS['rating']} مکان‌های برتر: مشاهده برترین مکان‌ها
- {EMOJIS['star']} کاربران برتر: مشاهده برترین کاربران
- {EMOJIS['link']} لینک‌ها: لینک‌های مفید
- {EMOJIS['help']} راهنما: همین صفحه

برای شروع از منوی اصلی گزینه مورد نظر را انتخاب کنید.
"""
            bot.send_message(user_id, help_text, reply_markup=main_menu())
    
    elif state == "profile_menu":
        if text == "مشاهده پروفایل":
            user = get_user(user_id)
            if user:
                profile_text = f"""
{EMOJIS['profile']} پروفایل کاربری:
نام: {user[1]}
سن: {user[2]}
جنسیت: {user[3]}
امتیاز: {user[4]}
کد عددی: {user[5]}
"""
                bot.send_message(user_id, profile_text, reply_markup=profile_menu())
        
        elif text == "تغییر نام":
            bot.send_message(user_id, f"{EMOJIS['edit']} نام جدید خود را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_name"
        
        elif text == "تغییر سن":
            bot.send_message(user_id, f"{EMOJIS['edit']} سن جدید خود را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_age"
        
        elif text == "تغییر جنسیت":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("مرد", "زن")
            keyboard.row("سایر")
            bot.send_message(user_id, f"{EMOJIS['edit']} جنسیت جدید خود را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "edit_gender"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
    
    elif state == "edit_name":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['profile']} پروفایل", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
            return
        
        if len(text) < 2:
            bot.send_message(user_id, f"{EMOJIS['error']} نام باید حداقل ۲ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET name = ? WHERE user_id = ?", (text, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} نام شما با موفقیت تغییر یافت!", reply_markup=profile_menu())
        user_states[user_id] = "profile_menu"
    
    elif state == "edit_age":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['profile']} پروفایل", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
            return
        
        if not text.isdigit() or int(text) < 1 or int(text) > 150:
            bot.send_message(user_id, f"{EMOJIS['error']} سن نامعتبر است. لطفاً یک عدد بین ۱ تا ۱۵۰ وارد کنید:")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET age = ? WHERE user_id = ?", (int(text), user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} سن شما با موفقیت تغییر یافت!", reply_markup=profile_menu())
        user_states[user_id] = "profile_menu"
    
    elif state == "edit_gender":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['profile']} پروفایل", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
            return
        
        if text not in ["مرد", "زن", "سایر"]:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً یکی از گزینه‌های معتبر را انتخاب کنید:")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET gender = ? WHERE user_id = ?", (text, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} جنسیت شما با موفقیت تغییر یافت!", reply_markup=profile_menu())
        user_states[user_id] = "profile_menu"
    
    elif state == "place_menu":
        if text == f"{EMOJIS['add']} اضافه کردن مکان":
            if user_id != ADMIN_ID:
                bot.send_message(user_id, f"{EMOJIS['error']} فقط ادمین می‌تواند مکان اضافه کند!", reply_markup=get_place_menu())
                return
            
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for category in PLACE_CATEGORIES.keys():
                keyboard.row(category)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            
            bot.send_message(user_id, f"{EMOJIS['add']} دسته‌بندی مکان را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_add_category"
            user_data[user_id] = {}
        
        elif text == f"{EMOJIS['view']} مشاهده مکان‌ها":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM places ORDER BY place_id DESC LIMIT 10")
            places = c.fetchall()
            conn.close()
            
            if places:
                response = f"{EMOJIS['places']} آخرین مکان‌های اضافه شده:\n\n"
                for place in places:
                    avg_rating = place[11] / place[12] if place[12] > 0 else 0
                    response += f"📍 {place[4]}\n📝 {place[5]}\n⭐ امتیاز: {avg_rating:.1f}\n\n"
                bot.send_message(user_id, response, reply_markup=get_place_menu())
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} هنوز هیچ مکانی اضافه نشده است.", reply_markup=get_place_menu())
        
        elif text == f"{EMOJIS['view']} مکان‌های من":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM places WHERE user_id = ? ORDER BY place_id DESC", (user_id,))
            places = c.fetchall()
            conn.close()
            
            if places:
                response = f"{EMOJIS['places']} مکان‌های شما:\n\n"
                for place in places:
                    avg_rating = place[11] / place[12] if place[12] > 0 else 0
                    response += f"📍 {place[4]}\n📝 {place[5]}\n⭐ امتیاز: {avg_rating:.1f}\n\n"
                
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['view']} مشاهده جزئیات", callback_data="view_my_places"))
                
                bot.send_message(user_id, response, reply_markup=keyboard)
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} شما هنوز هیچ مکانی اضافه نکرده‌اید.", reply_markup=get_place_menu())
        
        elif text == f"{EMOJIS['view']} جستجو":
            bot.send_message(user_id, f"{EMOJIS['view']} عبارت جستجو را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_search"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
    
    elif state == "place_add_category":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['places']} مدیریت مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        
        if text not in PLACE_CATEGORIES:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً یک دسته‌بندی معتبر انتخاب کنید:")
            return
        
        user_data[user_id]['category'] = text
        
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for subcategory in PLACE_CATEGORIES[text]:
            keyboard.row(subcategory)
        keyboard.row(f"{EMOJIS['back']} برگشت")
        
        bot.send_message(user_id, f"{EMOJIS['add']} زیردسته را انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "place_add_subcategory"
    
    elif state == "place_add_subcategory":
        if text == f"{EMOJIS['back']} برگشت":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for category in PLACE_CATEGORIES.keys():
                keyboard.row(category)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            
            bot.send_message(user_id, f"{EMOJIS['add']} دسته‌بندی مکان را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_add_category"
            return
        
        if text not in PLACE_CATEGORIES[user_data[user_id]['category']]:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً یک زیردسته معتبر انتخاب کنید:")
            return
        
        user_data[user_id]['subcategory'] = text
        bot.send_message(user_id, f"{EMOJIS['add']} عنوان مکان را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "place_add_title"
    
    elif state == "place_add_title":
        if text == f"{EMOJIS['back']} برگشت":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for subcategory in PLACE_CATEGORIES[user_data[user_id]['category']]:
                keyboard.row(subcategory)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            
            bot.send_message(user_id, f"{EMOJIS['add']} زیردسته را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_add_subcategory"
            return
        
        if len(text) < 3:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان باید حداقل ۳ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        user_data[user_id]['title'] = text
        bot.send_message(user_id, f"{EMOJIS['add']} توضیحات مکان را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "place_add_description"
    
    elif state == "place_add_description":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} عنوان مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_title"
            return
        
        if len(text) < 10:
            bot.send_message(user_id, f"{EMOJIS['error']} توضیحات باید حداقل ۱۰ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        user_data[user_id]['description'] = text
        bot.send_message(user_id, f"{EMOJIS['add']} آدرس مکان را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "place_add_address"
    
    elif state == "place_add_address":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} توضیحات مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_description"
            return
        
        if len(text) < 5:
            bot.send_message(user_id, f"{EMOJIS['error']} آدرس باید حداقل ۵ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        user_data[user_id]['address'] = text
        bot.send_message(user_id, f"{EMOJIS['add']} شماره تماس مکان را وارد کنید (یا 'رد کردن'):", reply_markup=skip_button())
        user_states[user_id] = "place_add_phone"
    
    elif state == "place_add_phone":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} آدرس مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_address"
            return
        
        if text == "رد کردن":
            user_data[user_id]['phone'] = None
        else:
            if not re.match(r'^[\d\s\-+\(\)]{5,}$', text):
                bot.send_message(user_id, f"{EMOJIS['error']} شماره تماس نامعتبر است. لطفاً دوباره وارد کنید یا 'رد کردن' بزنید:")
                return
            user_data[user_id]['phone'] = text
        
        bot.send_message(user_id, f"{EMOJIS['add']} عکس مکان را ارسال کنید:", reply_markup=back_button_only())
        user_states[user_id] = "place_add_photo"
    
    elif state == "place_add_photo":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} شماره تماس مکان را وارد کنید (یا 'رد کردن'):", reply_markup=skip_button())
            user_states[user_id] = "place_add_phone"
            return
        
        bot.send_message(user_id, f"{EMOJIS['error']} لطفاً یک عکس ارسال کنید:", reply_markup=back_button_only())
    
    elif state == "place_add_morning_shift":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} عکس مکان را ارسال کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_photo"
            return
        
        if text == "رد کردن":
            user_data[user_id]['morning_shift'] = None
        else:
            user_data[user_id]['morning_shift'] = text
        
        bot.send_message(user_id, f"{EMOJIS['add']} شیفت عصر را وارد کنید (مثال: 16:00-20:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
        user_states[user_id] = "place_add_afternoon_shift"
    
    elif state == "place_add_afternoon_shift":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} شیفت صبح را وارد کنید (مثال: 8:00-12:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
            user_states[user_id] = "place_add_morning_shift"
            return
        
        if text == "رد کردن":
            user_data[user_id]['afternoon_shift'] = None
        else:
            user_data[user_id]['afternoon_shift'] = text
        
        # ذخیره مکان در دیتابیس
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            INSERT INTO places (user_id, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            user_data[user_id]['category'],
            user_data[user_id]['subcategory'],
            user_data[user_id]['title'],
            user_data[user_id]['description'],
            user_data[user_id]['address'],
            user_data[user_id]['phone'],
            user_data[user_id]['photo'],
            user_data[user_id]['morning_shift'],
            user_data[user_id]['afternoon_shift']
        ))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} مکان با موفقیت اضافه شد!", reply_markup=get_place_menu())
        user_states[user_id] = "place_menu"
    
    elif state == "place_search":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['places']} مدیریت مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        
        if len(text) < 2:
            bot.send_message(user_id, f"{EMOJIS['error']} عبارت جستجو باید حداقل ۲ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT * FROM places 
            WHERE title LIKE ? OR description LIKE ? OR address LIKE ?
            ORDER BY place_id DESC LIMIT 10
        """, (f'%{text}%', f'%{text}%', f'%{text}%'))
        places = c.fetchall()
        conn.close()
        
        if places:
            response = f"{EMOJIS['view']} نتایج جستجو برای '{text}':\n\n"
            for place in places:
                avg_rating = place[11] / place[12] if place[12] > 0 else 0
                response += f"📍 {place[4]}\n📝 {place[5]}\n🏠 {place[6]}\n⭐ امتیاز: {avg_rating:.1f}\n\n"
            
            bot.send_message(user_id, response, reply_markup=search_result_menu())
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} هیچ نتیجه‌ای برای '{text}' یافت نشد.", reply_markup=search_result_menu())
        
        user_states[user_id] = "search_results"
    
    elif state == "search_results":
        if text == "جستجو دوباره":
            bot.send_message(user_id, f"{EMOJIS['view']} عبارت جستجو را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_search"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['places']} مدیریت مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
    
    elif state == "edit_place_menu":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['places']} مدیریت مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        
        place_id = user_data[user_id]['edit_place_id']
        
        if text == f"{EMOJIS['edit']} ویرایش عنوان":
            bot.send_message(user_id, f"{EMOJIS['edit']} عنوان جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_title"
        
        elif text == f"{EMOJIS['edit']} ویرایش توضیحات":
            bot.send_message(user_id, f"{EMOJIS['edit']} توضیحات جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_description"
        
        elif text == f"{EMOJIS['edit']} ویرایش آدرس":
            bot.send_message(user_id, f"{EMOJIS['edit']} آدرس جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_address"
        
        elif text == f"{EMOJIS['edit']} ویرایش تماس":
            bot.send_message(user_id, f"{EMOJIS['edit']} شماره تماس جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_phone"
        
        elif text == f"{EMOJIS['edit']} ویرایش عکس":
            bot.send_message(user_id, f"{EMOJIS['edit']} عکس جدید را ارسال کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_photo"
        
        elif text == f"{EMOJIS['edit']} ویرایش شیفت صبح":
            bot.send_message(user_id, f"{EMOJIS['edit']} شیفت صبح جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_morning_shift"
        
        elif text == f"{EMOJIS['edit']} ویرایش شیفت عصر":
            bot.send_message(user_id, f"{EMOJIS['edit']} شیفت عصر جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_afternoon_shift"
    
    elif state == "edit_place_title":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['edit']} کدام بخش را می‌خواهید ویرایش کنید؟", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
            return
        
        if len(text) < 3:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان باید حداقل ۳ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET title = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} عنوان مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_description":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['edit']} کدام بخش را می‌خواهید ویرایش کنید؟", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
            return
        
        if len(text) < 10:
            bot.send_message(user_id, f"{EMOJIS['error']} توضیحات باید حداقل ۱۰ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET description = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} توضیحات مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_address":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['edit']} کدام بخش را می‌خواهید ویرایش کنید؟", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
            return
        
        if len(text) < 5:
            bot.send_message(user_id, f"{EMOJIS['error']} آدرس باید حداقل ۵ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET address = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} آدرس مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_phone":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['edit']} کدام بخش را می‌خواهید ویرایش کنید؟", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
            return
        
        if not re.match(r'^[\d\s\-+\(\)]{5,}$', text):
            bot.send_message(user_id, f"{EMOJIS['error']} شماره تماس نامعتبر است. لطفاً دوباره وارد کنید:")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET phone = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} شماره تماس مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_morning_shift":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['edit']} کدام بخش را می‌خواهید ویرایش کنید؟", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET morning_shift = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} شیفت صبح مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_afternoon_shift":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['edit']} کدام بخش را می‌خواهید ویرایش کنید؟", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET afternoon_shift = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} شیفت عصر مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    
    elif state == "place_rate":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['places']} مدیریت مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        
        if not text.isdigit() or int(text) < 0 or int(text) > 10:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً یک عدد بین ۰ تا ۱۰ وارد کنید:")
            return
        
        rating = int(text)
        place_id = user_data[user_id]['place_id']
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # بررسی آیا کاربر قبلاً به این مکان امتیاز داده است
        c.execute("SELECT rating FROM place_ratings WHERE place_id = ? AND user_id = ?", (place_id, user_id))
        existing_rating = c.fetchone()
        
        if existing_rating:
            # به‌روزرسانی امتیاز قبلی
            old_rating = existing_rating[0]
            c.execute("UPDATE place_ratings SET rating = ? WHERE place_id = ? AND user_id = ?", (rating, place_id, user_id))
            c.execute("UPDATE places SET rating_sum = rating_sum - ? + ? WHERE place_id = ?", (old_rating, rating, place_id))
        else:
            # اضافه کردن امتیاز جدید
            c.execute("INSERT INTO place_ratings (place_id, user_id, rating) VALUES (?, ?, ?)", (place_id, user_id, rating))
            c.execute("UPDATE places SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE place_id = ?", (rating, place_id))
        
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} امتیاز شما با موفقیت ثبت شد!", reply_markup=get_place_menu())
        user_states[user_id] = "place_menu"
    
    elif state == "admin_menu":
        if text == "👥 کاربران فعال":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            user_count = c.fetchone()[0]
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['group']} تعداد کاربران فعال: {user_count}", reply_markup=admin_menu())
        
        elif text == f"{EMOJIS['news']} ارسال خبر":
            bot.send_message(user_id, f"{EMOJIS['news']} مدیریت اخبار", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
        
        elif text == "🛡️ مدیر مکان‌ها":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM places")
            place_count = c.fetchone()[0]
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['places']} مدیریت مکان‌ها\nتعداد کل مکان‌ها: {place_count}", reply_markup=admin_menu())
        
        elif text == "🚫 مسدود کردن کاربر":
            bot.send_message(user_id, f"{EMOJIS['error']} کد عددی کاربری که می‌خواهید مسدود کنید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "admin_block_user"
        
        elif text == "🔓 رفع مسدودیت":
            bot.send_message(user_id, f"{EMOJIS['success']} کد عددی کاربری که می‌خواهید رفع مسدودیت کنید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "admin_unblock_user"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
    
    elif state == "admin_news_menu":
        if text == f"{EMOJIS['group']} ارسال خبر گروهی":
            bot.send_message(user_id, f"{EMOJIS['group']} متن خبر گروهی را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "admin_send_news_group"
        
        elif text == f"{EMOJIS['user']} ارسال خبر به کاربر":
            bot.send_message(user_id, f"{EMOJIS['user']} ابتدا کد عددی کاربر را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "admin_send_news_user_id"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
    
    elif state == "admin_send_news_group":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['news']} مدیریت اخبار", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
            return
        
        if len(text) < 5:
            bot.send_message(user_id, f"{EMOJIS['error']} خبر باید حداقل ۵ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        # ذخیره خبر در دیتابیس
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO news (content) VALUES (?)", (text,))
        conn.commit()
        conn.close()
        
        # ارسال خبر به همه کاربران
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = c.fetchall()
        conn.close()
        
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                bot.send_message(user[0], f"{EMOJIS['news']} خبر جدید:\n\n{text}")
                success_count += 1
            except:
                fail_count += 1
        
        bot.send_message(user_id, f"{EMOJIS['success']} خبر به {success_count} کاربر ارسال شد. {fail_count} ارسال ناموفق.", reply_markup=admin_news_menu())
        user_states[user_id] = "admin_news_menu"
    
    elif state == "admin_send_news_user_id":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['news']} مدیریت اخبار", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
            return
        
        if not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} کد عددی نامعتبر است. لطفاً دوباره وارد کنید:")
            return
        
        numeric_id = int(text)
        target_user = get_user_by_numeric_id(numeric_id)
        
        if not target_user:
            bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این کد عددی یافت نشد.", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
            return
        
        user_data[user_id]['news_target'] = target_user[0]  # user_id
        bot.send_message(user_id, f"{EMOJIS['user']} متن خبر برای کاربر {target_user[1]} را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "admin_send_news_user_text"
    
    elif state == "admin_send_news_user_text":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['user']} ابتدا کد عددی کاربر را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "admin_send_news_user_id"
            return
        
        if len(text) < 5:
            bot.send_message(user_id, f"{EMOJIS['error']} خبر باید حداقل ۵ حرف باشد. لطفاً دوباره وارد کنید:")
            return
        
        target_user_id = user_data[user_id]['news_target']
        
        try:
            bot.send_message(target_user_id, f"{EMOJIS['news']} خبر ویژه برای شما:\n\n{text}")
            bot.send_message(user_id, f"{EMOJIS['success']} خبر با موفقیت ارسال شد!", reply_markup=admin_news_menu())
        except:
            bot.send_message(user_id, f"{EMOJIS['error']} ارسال خبر ناموفق بود. ممکن است کاربر ربات را بلاک کرده باشد.", reply_markup=admin_news_menu())
        
        user_states[user_id] = "admin_news_menu"
    
    elif state == "admin_block_user":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
            return
        
        if not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} کد عددی نامعتبر است. لطفاً دوباره وارد کنید:")
            return
        
        numeric_id = int(text)
        target_user = get_user_by_numeric_id(numeric_id)
        
        if not target_user:
            bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این کد عددی یافت نشد.", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
            return
        
        block_user(target_user[0])
        bot.send_message(user_id, f"{EMOJIS['success']} کاربر {target_user[1]} با موفقیت مسدود شد!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    
    elif state == "admin_unblock_user":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
            return
        
        if not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} کد عددی نامعتبر است. لطفاً دوباره وارد کنید:")
            return
        
        numeric_id = int(text)
        target_user = get_user_by_numeric_id(numeric_id)
        
        if not target_user:
            bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این کد عددی یافت نشد.", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
            return
        
        unblock_user(target_user[0])
        bot.send_message(user_id, f"{EMOJIS['success']} کاربر {target_user[1]} با موفقیت رفع مسدودیت شد!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} دستور نامعتبر است. لطفاً از منو استفاده کنید.", reply_markup=main_menu())
        user_states[user_id] = "main_menu"

# مدیریت عکس‌ها
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.")
        return
    
    state = user_states.get(user_id, "")
    
    if state == "place_add_photo":
        if user_id != ADMIN_ID:
            bot.send_message(user_id, f"{EMOJIS['error']} فقط ادمین می‌تواند مکان اضافه کند!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        
        user_data[user_id]['photo'] = message.photo[-1].file_id
        bot.send_message(user_id, f"{EMOJIS['places']} شیفت صبح را وارد کنید (مثال: 8:00-12:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
        user_states[user_id] = "place_add_morning_shift"
    
    elif state == "edit_place_photo":
        photo_id = message.photo[-1].file_id
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET photo = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (photo_id, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} عکس مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"

# مدیریت دکمه‌های اینلاین
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.")
        return
    
    data = call.data
    
    if data == "accept_terms":
        user = get_user(user_id)
        if user:
            bot.send_message(user_id, f"{EMOJIS['success']} خوش برگشتی!", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['profile']} سلام! نام خود را وارد کنید:")
            user_states[user_id] = "awaiting_name"
            user_data[user_id] = {}
    
    elif data == "decline_terms":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['info']} درخواست دوباره", callback_data="retry_terms"))
        bot.send_message(user_id, f"{EMOJIS['error']} برای استفاده از ربات، باید قوانین را بپذیرید. در صورت عدم پذیرش، قادر به استفاده از ربات نخواهید بود.", reply_markup=keyboard)
    
    elif data == "retry_terms":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['success']} پذیرفتن", callback_data="accept_terms"))
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['error']} نپذیرفتن", callback_data="decline_terms"))
        bot.send_message(user_id, WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=keyboard)
        user_states[user_id] = "awaiting_terms"
    
    elif data.startswith("delete_place_"):
        place_id = int(data.split("_")[2])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id FROM places WHERE place_id = ?", (place_id,))
        place = c.fetchone()
        
        if place and (place[0] == user_id or user_id == ADMIN_ID):
            c.execute("DELETE FROM places WHERE place_id = ?", (place_id,))
            c.execute("DELETE FROM place_ratings WHERE place_id = ?", (place_id,))
            conn.commit()
            bot.send_message(user_id, f"{EMOJIS['success']} مکان حذف شد!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شما مجاز به حذف این مکان نیستید!", reply_markup=get_place_menu())
        
        conn.close()
    
    elif data.startswith("edit_place_"):
        place_id = int(data.split("_")[2])
        user_data[user_id] = {'edit_place_id': place_id}
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM places WHERE place_id = ? AND (user_id = ? OR ? = ?)", (place_id, user_id, user_id, ADMIN_ID))
        place = c.fetchone()
        conn.close()
        
        if place:
            keyboard = edit_place_menu(place_id)
            msg = f"{EMOJIS['edit']} کدام بخش را می‌خواهید ویرایش کنید؟"
            bot.send_message(user_id, msg, reply_markup=keyboard)
            user_states[user_id] = "edit_place_menu"
    
    elif data.startswith("rate_place_"):
        place_id = int(data.split("_")[2])
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT rating FROM place_ratings WHERE place_id = ? AND user_id = ?", (place_id, user_id))
        existing_rating = c.fetchone()
        conn.close()
        
        if existing_rating:
            bot.send_message(user_id, f"{EMOJIS['error']} شما قبلاً به این مکان امتیاز {existing_rating[0]} داده‌اید!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        else:
            user_data[user_id] = {'place_id': place_id}
            bot.send_message(user_id, f"{EMOJIS['rating']} امتیازی بین 0 تا 10 برای این مکان وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_rate"

# راه‌اندازی Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Invalid content type', 400

@app.route('/webhook', methods=['GET', 'HEAD', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def handle_other_methods():
    return 'Method Not Allowed', 405

# تنظیم Webhook هنگام راه‌اندازی
def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{WEBHOOK_URL}/webhook", certificate=open('webhook_cert.pem', 'r') if os.path.exists('webhook_cert.pem') else None)
        print("Webhook set successfully")
    except Exception as e:
        print(f"Error setting webhook: {e}")

# صفحه اصلی برای تست
@app.route('/')
def index():
    return "ربات گویم‌نما در حال اجراست!"

# اجرای برنامه
if __name__ == "__main__":
    # فقط در محیط توسعه از Polling استفاده کن
    if os.environ.get('ENV') == 'development':
        print("Running in development mode (Polling)")
        while True:
            try:
                bot.infinity_polling(timeout=5, long_polling_timeout=5)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)
    else:
        print("Running in production mode (Webhook)")
        set_webhook()
        app.run(host='0.0.0.0', port=PORT, ssl_context='adhoc')