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
API_TOKEN = "8158514610:AAG6QYu1tlOuh6BkbjhojAkjRl3cCAP31Ao"
ADMIN_ID = 7385601641
DB_NAME = "goyim.db"
WEBHOOK_URL = "https://goyomnama.onrender.com"
PORT = 5000

# تنظیم ربات
bot = telebot.TeleBot(API_TOKEN, threaded=True)
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
    "user": "👤"
}

# پیام خوش‌آمدگویی و قوانین
WELCOME_MESSAGE = f"""
{EMOJIS['home']} به ربات گویم‌نما خوش آمدید! {EMOJIS['success']}

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

def place_view_result_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مشاهده دوباره")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    keyboard.row(f"{EMOJIS['home']} صفحه اصلی")
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

def admin_sub_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
    return keyboard

def admin_news_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['group']} ارسال خبر گروهی")
    keyboard.row(f"{EMOJIS['user']} ارسال خبر به کاربر")
    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
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
@app.route('/' + API_TOKEN, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + '/' + API_TOKEN)
    return "Webhook set!", 200

@app.route('/health')
def health_check():
    return "OK", 200

@bot.message_handler(commands=['start', 'admin'])
def start(message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما به دلیل نقض قوانین از طرف ادمین مسدود شده اید❌برای رفع مسدودیت باید هزینه ای اندک بپردازید ‼️ برای هماهنگی به ایدی ادمین پیام دهید: @Sedayegoyom10")
        return
    if message.text == '/admin' and user_id == ADMIN_ID:
        bot.send_message(user_id, f"{EMOJIS['admin']} به پنل ادمین خوش آمدید!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
        return
    user = get_user(user_id)
    if user:
        bot.send_message(user_id, f"{EMOJIS['success']} خوش برگشتی! 😍", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['success']} پذیرفتن", callback_data="accept_terms"))
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['error']} نپذیرفتن", callback_data="decline_terms"))
        bot.send_message(user_id, WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=keyboard)
        user_states[user_id] = "awaiting_terms"

# مدیریت پیام‌ها - بهبود برای کارکرد بدون نیاز به /start
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما به دلیل نقض قوانین از طرف ادمین مسدود شده اید❌برای رفع مسدودیت باید هزینه ای اندک بپردازید ‼️ برای هماهنگی به ایدی ادمین پیام دهید: @Sedayegoyom10")
        return
    
    # اگر کاربر قبلاً ثبت‌نام نکرده، مستقیماً به فرآیند ثبت‌نام هدایت شود
    if user_id not in user_states and not get_user(user_id):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['success']} پذیرفتن", callback_data="accept_terms"))
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['error']} نپذیرفتن", callback_data="decline_terms"))
        bot.send_message(user_id, WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=keyboard)
        user_states[user_id] = "awaiting_terms"
        return
    
    state = user_states.get(user_id, "main_menu")
    text = message.text if message.text else ""

    if text == f"{EMOJIS['home']} صفحه اصلی":
        bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu())
        user_states[user_id] = "main_menu"
        return
    if text == f"{EMOJIS['back']} برگشت":
        if state in ["profile_menu", "profile_view", "profile_edit_name", "profile_edit_age", "profile_edit_gender"]:
            bot.send_message(user_id, "بخش پروفایل:", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
            return
        elif state == "place_view_category":
            bot.send_message(user_id, f"{EMOJIS['places']} به بخش مکان‌ها خوش آمدید!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        elif state == "place_view_subcategory":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for cat in PLACE_CATEGORIES:
                keyboard.row(f"📌 {cat}")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['places']} یک دسته انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_view_category"
            return
        elif state in ["place_menu", "place_add_category", "place_add_subcategory", "place_add_title", "place_add_description", 
                       "place_add_address", "place_add_phone", "place_add_photo", "place_add_morning_shift", 
                       "place_add_afternoon_shift", "place_add_numeric_id", "place_view_result", "place_my_places", 
                       "place_top_rated", "place_rate", "place_rate_confirm", "place_search_title", "place_search_address", "place_search_result"]:
            bot.send_message(user_id, "بخش مکان‌ها:", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        elif state in ["edit_place_menu", "edit_place_title", "edit_place_description", "edit_place_address", 
                       "edit_place_phone", "edit_place_photo", "edit_place_morning_shift", "edit_place_afternoon_shift"]:
            bot.send_message(user_id, "ویرایش مکان:", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
            return
        elif state in ["admin_menu", "admin_view_gender", "admin_users", "admin_news_content", "admin_news_confirm", 
                       "admin_news_sent", "admin_delete_place_title", "admin_delete_place_category", 
                       "admin_delete_place_subcategory", "admin_delete_place_user_id", "admin_delete_place_confirm", 
                       "admin_block_user", "admin_confirm_block", "admin_unblock_user", "admin_confirm_unblock",
                       "admin_news_menu", "admin_news_user_content", "admin_news_user_numeric_id", "admin_news_user_confirm"]:
            if state.startswith("admin_news"):
                bot.send_message(user_id, f"{EMOJIS['news']} بخش ارسال خبر:", reply_markup=admin_news_menu())
                user_states[user_id] = "admin_news_menu"
            elif state == "admin_view_gender":
                bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
            return
        else:
            bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
            return
    if text == "برگشت به ادمین":
        bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
        return
    if state == "awaiting_name":
        if text.strip():
            user_data[user_id] = {'name': text}
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for i in range(13, 71, 10):
                row = [str(x) for x in range(i, min(i+10, 71))]
                keyboard.row(*row)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, "سن خود را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "awaiting_age"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} نام نمی‌تواند خالی باشد!")
    elif state == "awaiting_age":
        try:
            age = int(text)
            if 13 <= age <= 70:
                user_data[user_id]['age'] = age
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("👦 پسر", "👧 دختر", "🌀 دیگر")
                keyboard.row(f"{EMOJIS['back']} برگشت")
                bot.send_message(user_id, "جنسیت خود را انتخاب کنید:", reply_markup=keyboard)
                user_states[user_id] = "awaiting_gender"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} سن بین 13 تا 70 باشد!")
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "awaiting_gender":
        if text in ["👦 پسر", "👧 دختر", "🌀 دیگر"]:
            gender = text.split()[1] if " " in text else text
            user_data[user_id]['gender'] = gender
            save_user(user_id, user_data[user_id]['name'], user_data[user_id]['age'], gender)
            user = get_user(user_id)
            profile_msg = f"{EMOJIS['profile']} پروفایل شما:\n"
            profile_msg += f"نام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}"
            bot.send_message(user_id, profile_msg, reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} یکی از گزینه‌ها را انتخاب کنید!")
    elif state == "main_menu":
        if text == f"{EMOJIS['profile']} پروفایل":
            user = get_user(user_id)
            if user:
                keyboard = profile_menu()
                profile_msg = f"{EMOJIS['profile']} پروفایل شما:\n"
                profile_msg += f"نام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}"
                bot.send_message(user_id, profile_msg, reply_markup=keyboard)
                user_states[user_id] = "profile_menu"
        elif text == f"{EMOJIS['places']} مکان‌ها":
            bot.send_message(user_id, f"{EMOJIS['places']} به بخش مکان‌ها خوش آمدید!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        elif text == f"{EMOJIS['rating']} مکان‌های برتر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            MIN_RATING_COUNT = 200
            MIN_AVG_RATING = 8.0
            c.execute("""
                SELECT places.*, users.numeric_id
                FROM places
                JOIN users ON places.user_id = users.user_id
                WHERE places.rating_count >= ? AND (places.rating_sum * 1.0 / places.rating_count) > ?
                ORDER BY (places.rating_sum * 1.0 / places.rating_count) DESC
            """, (MIN_RATING_COUNT, MIN_AVG_RATING))
            places = c.fetchall()
            conn.close()
            if places:
                for place in places:
                    if place[8]:
                        try:
                            bot.send_photo(user_id, place[8])
                        except:
                            pass
                    avg_rating = (place[11] / place[12]) if place[12] > 0 else 0
                    msg = f"{EMOJIS['places']} مکان برتر:\n"
                    msg += f"عنوان: {place[4]}\nدسته: {place[2]}\nزیردسته: {place[3] or 'مشخص نشده'}\n"
                    msg += f"توضیحات: {place[5]}\n"
                    msg += f"آدرس: {place[6]}\n"
                    msg += f"تماس: {place[7] or 'مشخص نشده'}\n"
                    msg += f"شیفت صبح: {place[9] or 'مشخص نشده'}\n"
                    msg += f"شیفت عصر: {place[10] or 'مشخص نشده'}\n"
                    msg += f"امتیاز میانگین: {avg_rating:.1f} ({place[12]} رای)"
                    # نمایش شناسه عددی مالک فقط برای ادمین
                    if user_id == ADMIN_ID:
                        msg += f"\nشناسه عددی مالک: {place[13]}"
                    keyboard = types.InlineKeyboardMarkup()
                    if user_id == ADMIN_ID:
                        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place[0]}"))
                        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['rating']} امتیاز", callback_data=f"rate_place_{place[0]}"))
                    bot.send_message(user_id, msg, reply_markup=keyboard)
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} هنوز هیچ مکانی نتونسته مرتبه برتر را در مکان‌ها کسب کند!")
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=main_menu())
            user_states[user_id] = "place_top_rated"
        elif text == f"{EMOJIS['star']} کاربران برتر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT name, score FROM users WHERE score >= 1000 ORDER BY score DESC")
            users = c.fetchall()
            conn.close()
            if users:
                msg = f"{EMOJIS['star']} کاربران برتر:\n"
                msg += "\n".join([f"{u[0]}: {u[1]} امتیاز" for u in users])
            else:
                msg = f"{EMOJIS['error']} هنوز کسی به ۱۰۰۰ امتیاز نرسیده است!"
            bot.send_message(user_id, msg, reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        elif text == f"{EMOJIS['link']} لینک‌ها":
            link_text = f"{EMOJIS['link']} لینک‌های مفید:\n\n"
            link_text += f"{EMOJIS['link']} لینک پیج اصلی گویم‌نما:\n"
            link_text += "https://www.instagram.com/sedayegoyom?igsh=MXd0MTlkZGdzNzZ6bw==\n\n"
            link_text += f"{EMOJIS['admin']} ایدی ادمین گویم‌نما:\n"
            link_text += "@Sedayegoyom10"
            bot.send_message(user_id, link_text, reply_markup=main_menu())
            user_states[user_id] = "main_menu"
        elif text == f"{EMOJIS['help']} راهنما":
            help_text = f"{EMOJIS['help']} راهنمای استفاده از ربات گویم‌نما:\n\n"
            help_text += f"{EMOJIS['profile']} بخش پروفایل:\n"
            help_text += "• مشاهده اطلاعات شخصی خود\n"
            help_text += "• ویرایش نام، سن و جنسیت\n\n"
            help_text += f"{EMOJIS['places']} بخش مکان‌ها:\n"
            help_text += "• مشاهده مکان‌ها بر اساس دسته‌بندی\n"
            help_text += "• مدیریت مکان‌های خود (ویرایش/حذف برای ادمین)\n"
            help_text += "• برای اضافه کردن مکان با ادمین تماس بگیرید\n"
            help_text += "• هر مکان ۱۵ امتیاز برای کاربر مرتبط\n\n"
            help_text += f"{EMOJIS['rating']} مکان‌های برتر:\n"
            help_text += "• مشاهده مکان‌هایی با حداقل ۲۰۰ رای و میانگین امتیاز بالای ۸\n"
            help_text += "• هر کاربر فقط یک‌بار می‌تواند به هر مکان رای دهد\n\n"
            help_text += f"{EMOJIS['star']} کاربران برتر:\n"
            help_text += "• مشاهده کاربران با بیشترین امتیاز\n"
            help_text += "• حداقل ۱۰۰۰ امتیاز برای نمایش\n\n"
            help_text += f"{EMOJIS['link']} بخش لینک‌ها:\n"
            help_text += "• دسترسی به پیج اصلی\n"
            help_text += "• ارتباط با ادمین\n\n"
            help_text += f"{EMOJIS['info']} قوانین مهم:\n"
            help_text += "• محتوای مستهجن یا توهین‌آمیز مجاز نیست\n"
            help_text += "• اطلاعات واقعی و دقیق وارد کنید\n"
            help_text += "• رعایت ادب و احترام در تعاملات\n"
            help_text += "• تخلف از قوانین منجر به مسدودیت می‌شود\n\n"
            help_text += f"{EMOJIS['success']} موفق باشید!"
            bot.send_message(user_id, help_text, reply_markup=main_menu())
            user_states[user_id] = "main_menu"
    elif state == "profile_menu":
        if text == "مشاهده پروفایل":
            user = get_user(user_id)
            if user:
                profile_msg = f"{EMOJIS['profile']} پروفایل شما:\n"
                profile_msg += f"نام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}"
                bot.send_message(user_id, profile_msg, reply_markup=profile_menu())
                user_states[user_id] = "profile_menu"
        elif text == "تغییر نام":
            bot.send_message(user_id, f"{EMOJIS['edit']} نام جدید خود را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "profile_edit_name"
        elif text == "تغییر سن":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for i in range(13, 71, 10):
                row = [str(x) for x in range(i, min(i+10, 71))]
                keyboard.row(*row)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['edit']} سن جدید را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "profile_edit_age"
        elif text == "تغییر جنسیت":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("👦 پسر", "👧 دختر", "🌀 دیگر")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['edit']} جنسیت جدید را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "profile_edit_gender"
    elif state == "profile_edit_name":
        if text.strip():
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET name = ? WHERE user_id = ?", (text, user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} نام به‌روزرسانی شد!", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} نام نمی‌تواند خالی باشد!")
    elif state == "profile_edit_age":
        try:
            age = int(text)
            if 13 <= age <= 70:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("UPDATE users SET age = ? WHERE user_id = ?", (age, user_id))
                conn.commit()
                conn.close()
                bot.send_message(user_id, f"{EMOJIS['success']} سن به‌روزرسانی شد!", reply_markup=profile_menu())
                user_states[user_id] = "profile_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} سن بین 13 تا 70 باشد!")
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "profile_edit_gender":
        if text in ["👦 پسر", "👧 دختر", "🌀 دیگر"]:
            gender = text.split()[1] if " " in text else text
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} جنسیت به‌روزرسانی شد!", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} یکی از گزینه‌ها را انتخاب کنید!")
    elif state == "place_menu":
        if text == f"{EMOJIS['add']} اضافه کردن مکان":
            if user_id == ADMIN_ID:
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for cat in PLACE_CATEGORIES:
                    keyboard.row(f"📌 {cat}")
                keyboard.row(f"{EMOJIS['back']} برگشت")
                bot.send_message(user_id, f"{EMOJIS['places']} یک دسته انتخاب کنید:", reply_markup=keyboard)
                user_states[user_id] = "place_add_category"
            else:
                bot.send_message(user_id, f"{EMOJIS['info']} برای اضافه کردن مکان و هماهنگی به ادمین گویم‌نما پیام دهید: @Sedayegoyom10", reply_markup=get_place_menu())
                user_states[user_id] = "place_menu"
        elif text == f"{EMOJIS['view']} مشاهده مکان‌ها":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for cat in PLACE_CATEGORIES:
                keyboard.row(f"📌 {cat}")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['places']} یک دسته انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_view_category"
        elif text == f"{EMOJIS['view']} مکان‌های من":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT places.*, users.numeric_id FROM places JOIN users ON places.user_id = users.user_id WHERE places.user_id = ? ORDER BY (places.rating_sum * 1.0 / NULLIF(places.rating_count, 0)) DESC, places.place_id DESC", (user_id,))
            places = c.fetchall()
            conn.close()
            if places:
                for place in places:
                    if place[8]:
                        try:
                            bot.send_photo(user_id, place[8])
                        except:
                            pass
                    avg_rating = (place[11] / place[12]) if place[12] > 0 else 0
                    msg = f"{EMOJIS['places']} مکان شما:\n"
                    msg += f"عنوان: {place[4]}\nدسته: {place[2]}\nزیردسته: {place[3] or 'مشخص نشده'}\n"
                    msg += f"توضیحات: {place[5]}\n"
                    msg += f"آدرس: {place[6]}\n"
                    msg += f"تماس: {place[7] or 'مشخص نشده'}\n"
                    msg += f"شیفت صبح: {place[9] or 'مشخص نشده'}\n"
                    msg += f"شیفت عصر: {place[10] or 'مشخص نشده'}\n"
                    msg += f"امتیاز: {avg_rating:.1f} ({place[12]} رای)"
                    # نمایش شناسه عددی مالک فقط برای ادمین
                    if user_id == ADMIN_ID:
                        msg += f"\nشناسه عددی مالک: {place[13]}"
                    keyboard = types.InlineKeyboardMarkup()
                    if user_id == ADMIN_ID:
                        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place[0]}"))
                        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['rating']} امتیاز", callback_data=f"rate_place_{place[0]}"))
                    bot.send_message(user_id, msg, reply_markup=keyboard)
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} شما مکانی ندارید!")
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=get_place_menu())
            user_states[user_id] = "place_my_places"
        elif text == f"{EMOJIS['view']} جستجو":
            bot.send_message(user_id, f"{EMOJIS['places']} عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_search_title"
    elif state == "place_add_category":
        if user_id != ADMIN_ID:
            bot.send_message(user_id, f"{EMOJIS['error']} فقط ادمین می‌تواند مکان اضافه کند!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        if text.startswith("📌"):
            category = text[2:]
            if category in PLACE_CATEGORIES:
                user_data[user_id] = {'category': category}
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for sub in PLACE_CATEGORIES[category]:
                    keyboard.row(f"🔹 {sub}")
                keyboard.row(f"{EMOJIS['back']} برگشت")
                bot.send_message(user_id, f"{EMOJIS['places']} یک زیرشاخه انتخاب کنید:", reply_markup=keyboard)
                user_states[user_id] = "place_add_subcategory"
    elif state == "place_add_subcategory":
        if text.startswith("🔹"):
            subcategory = text[2:]
            category = user_data[user_id].get('category', '')
            if subcategory in PLACE_CATEGORIES.get(category, []):
                user_data[user_id]['subcategory'] = subcategory
                bot.send_message(user_id, f"{EMOJIS['places']} عنوان مکان را وارد کنید:", reply_markup=back_button_only())
                user_states[user_id] = "place_add_title"
    elif state == "place_add_title":
        if text.strip():
            user_data[user_id]['title'] = text
            bot.send_message(user_id, f"{EMOJIS['places']} توضیحات مکان را وارد کنید (حداقل 10 کلمه):", reply_markup=back_button_only())
            user_states[user_id] = "place_add_description"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان نمی‌تواند خالی باشد!")
    elif state == "place_add_description":
        words = text.strip().split()
        if len(words) >= 10:
            user_data[user_id]['description'] = text
            bot.send_message(user_id, f"{EMOJIS['places']} آدرس را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_address"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} توضیحات باید حداقل 10 کلمه باشد! ({len(words)} کلمه وارد کرده‌اید)")
    elif state == "place_add_address":
        if text.strip():
            user_data[user_id]['address'] = text
            bot.send_message(user_id, f"{EMOJIS['places']} شماره تماس را وارد کنید (شماره باید با 09 شروع شود و 11 رقم باشد یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
            user_states[user_id] = "place_add_phone"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} آدرس نمی‌تواند خالی باشد!")
    elif state == "place_add_phone":
        if text == "رد کردن":
            user_data[user_id]['phone'] = None
            bot.send_message(user_id, f"{EMOJIS['places']} یک عکس برای مکان ارسال کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_photo"
        elif re.match(r'^09\d{9}$', text):
            user_data[user_id]['phone'] = text
            bot.send_message(user_id, f"{EMOJIS['places']} یک عکس برای مکان ارسال کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_photo"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شماره موبایل باید با 09 شروع شود و 11 رقم باشد یا 'رد کردن' را انتخاب کنید!")
    elif state == "place_add_photo":
        bot.send_message(user_id, f"{EMOJIS['places']} شیفت صبح را وارد کنید (مثال: 8:00-12:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
        user_states[user_id] = "place_add_morning_shift"
    elif state == "place_add_morning_shift":
        user_data[user_id]['morning_shift'] = None if text == "رد کردن" else text
        bot.send_message(user_id, f"{EMOJIS['places']} شیفت عصر را وارد کنید (مثال: 14:00-20:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
        user_states[user_id] = "place_add_afternoon_shift"
    elif state == "place_add_afternoon_shift":
        user_data[user_id]['afternoon_shift'] = None if text == "رد کردن" else text
        bot.send_message(user_id, f"{EMOJIS['places']} شناسه عددی کاربر را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "place_add_numeric_id"
    elif state == "place_add_numeric_id":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                user_data[user_id]['numeric_id'] = numeric_id
                target_user_id = target_user[0]
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO places (user_id, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (target_user_id, user_data[user_id]['category'], user_data[user_id]['subcategory'], user_data[user_id]['title'],
                           user_data[user_id]['description'], user_data[user_id]['address'], user_data[user_id].get('phone'),
                           user_data[user_id].get('photo'), user_data[user_id]['morning_shift'], user_data[user_id]['afternoon_shift']))
                c.execute("UPDATE users SET score = score + 15 WHERE user_id = ?", (target_user_id,))
                place_id = c.lastrowid
                conn.commit()
                conn.close()
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT user_id FROM users")
                users = c.fetchall()
                conn.close()
                success_count = 0
                for user in users:
                    try:
                        bot.send_message(user[0], f"{EMOJIS['places']} مکان جدید در دسته {user_data[user_id]['category']}، زیردسته {user_data[user_id]['subcategory']}:\nعنوان: {user_data[user_id]['title']}")
                        success_count += 1
                    except:
                        pass
                bot.send_message(user_id, f"{EMOJIS['success']} مکان با موفقیت ثبت شد! ۱۵ امتیاز به کاربر با شناسه {numeric_id} اضافه شد.\nارسال به {success_count} کاربر.", reply_markup=get_place_menu())
                user_states[user_id] = "place_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه عددی یافت نشد!", reply_markup=get_place_menu())
                user_states[user_id] = "place_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=back_button_only())
    elif state == "place_view_category":
        if text.startswith("📌"):
            category = text[2:]
            if category in PLACE_CATEGORIES:
                user_data[user_id] = {'category': category}
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for sub in PLACE_CATEGORIES[category]:
                    keyboard.row(f"🔹 {sub}")
                keyboard.row(f"{EMOJIS['back']} برگشت")
                bot.send_message(user_id, f"{EMOJIS['places']} یک زیرشاخه انتخاب کنید:", reply_markup=keyboard)
                user_states[user_id] = "place_view_subcategory"
    elif state == "place_view_subcategory":
        if text.startswith("🔹"):
            subcategory = text[2:]
            category = user_data[user_id].get('category', '')
            if subcategory in PLACE_CATEGORIES.get(category, []):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT places.*, users.numeric_id FROM places JOIN users ON places.user_id = users.user_id WHERE category = ? AND subcategory = ? ORDER BY (places.rating_sum * 1.0 / NULLIF(places.rating_count, 0)) DESC, places.place_id DESC", (category, subcategory))
                places = c.fetchall()
                conn.close()
                if places:
                    for place in places:
                        if place[8]:
                            try:
                                bot.send_photo(user_id, place[8])
                            except:
                                pass
                        avg_rating = (place[11] / place[12]) if place[12] > 0 else 0
                        msg = f"{EMOJIS['places']} مکان:\n"
                        msg += f"عنوان: {place[4]}\n"
                        msg += f"توضیحات: {place[5]}\n"
                        msg += f"آدرس: {place[6]}\n"
                        msg += f"تماس: {place[7] or 'مشخص نشده'}\n"
                        msg += f"شیفت صبح: {place[9] or 'مشخص نشده'}\n"
                        msg += f"شیفت عصر: {place[10] or 'مشخص نشده'}\n"
                        msg += f"امتیاز: {avg_rating:.1f} ({place[12]} رای)"
                        # نمایش شناسه عددی مالک فقط برای ادمین
                        if user_id == ADMIN_ID:
                            msg += f"\nشناسه عددی مالک: {place[13]}"
                        keyboard = types.InlineKeyboardMarkup()
                        if user_id == ADMIN_ID:
                            keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place[0]}"))
                            keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place[0]}"))
                        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['rating']} امتیاز", callback_data=f"rate_place_{place[0]}"))
                        bot.send_message(user_id, msg, reply_markup=keyboard)
                else:
                    bot.send_message(user_id, f"{EMOJIS['error']} مکانی در این دسته وجود ندارد!", reply_markup=back_button_only())
                bot.send_message(user_id, "انتخاب کنید:", reply_markup=place_view_result_menu())
                user_states[user_id] = "place_view_result"
    elif state == "place_view_result":
        if text == "مشاهده دوباره":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for cat in PLACE_CATEGORIES:
                keyboard.row(f"📌 {cat}")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['places']} یک دسته انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_view_category"
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, "بخش مکان‌ها:", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
    elif state == "place_search_title":
        if text.strip():
            user_data[user_id] = {'search_title': text}
            bot.send_message(user_id, f"{EMOJIS['places']} آدرس مورد نظر را وارد کنید (یا 'رد کردن' برای جستجو فقط بر اساس عنوان):", reply_markup=skip_button())
            user_states[user_id] = "place_search_address"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان نمی‌تواند خالی باشد!")
    elif state == "place_search_address":
        search_title = user_data[user_id].get('search_title', '')
        search_address = None if text == "رد کردن" else text
        query = "SELECT places.*, users.numeric_id FROM places JOIN users ON places.user_id = users.user_id WHERE title LIKE ?"
        params = [f"%{search_title}%"]
        if search_address:
            query += " AND address LIKE ?"
            params.append(f"%{search_address}%")
        query += " ORDER BY (places.rating_sum * 1.0 / NULLIF(places.rating_count, 0)) DESC, places.place_id DESC"
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(query, params)
        places = c.fetchall()
        conn.close()
        if places:
            for place in places:
                if place[8]:
                    try:
                        bot.send_photo(user_id, place[8])
                    except:
                        pass
                avg_rating = (place[11] / place[12]) if place[12] > 0 else 0
                msg = f"{EMOJIS['places']} مکان یافت شده:\n"
                msg += f"عنوان: {place[4]}\nدسته: {place[2]}\nزیردسته: {place[3] or 'مشخص نشده'}\n"
                msg += f"توضیحات: {place[5]}\n"
                msg += f"آدرس: {place[6]}\n"
                msg += f"تماس: {place[7] or 'مشخص نشده'}\n"
                msg += f"شیفت صبح: {place[9] or 'مشخص نشده'}\n"
                msg += f"شیفت عصر: {place[10] or 'مشخص نشده'}\n"
                msg += f"امتیاز: {avg_rating:.1f} ({place[12]} رای)"
                # نمایش شناسه عددی مالک فقط برای ادمین
                if user_id == ADMIN_ID:
                    msg += f"\nشناسه عددی مالک: {place[13]}"
                keyboard = types.InlineKeyboardMarkup()
                if user_id == ADMIN_ID:
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['rating']} امتیاز", callback_data=f"rate_place_{place[0]}"))
                bot.send_message(user_id, msg, reply_markup=keyboard)
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} مکانی با این مشخصات یافت نشد!")
        bot.send_message(user_id, "انتخاب کنید:", reply_markup=search_result_menu())
        user_states[user_id] = "place_search_result"
    elif state == "place_search_result":
        if text == "جستجو دوباره":
            bot.send_message(user_id, f"{EMOJIS['places']} عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_search_title"
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, "بخش مکان‌ها:", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu())
            user_states[user_id] = "main_menu"
    elif state == "edit_place_menu":
        if text == f"{EMOJIS['edit']} ویرایش عنوان":
            bot.send_message(user_id, f"{EMOJIS['edit']} عنوان جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_title"
        elif text == f"{EMOJIS['edit']} ویرایش توضیحات":
            bot.send_message(user_id, f"{EMOJIS['edit']} توضیحات جدید را وارد کنید (حداقل 10 کلمه):", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_description"
        elif text == f"{EMOJIS['edit']} ویرایش آدرس":
            bot.send_message(user_id, f"{EMOJIS['edit']} آدرس جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_address"
        elif text == f"{EMOJIS['edit']} ویرایش تماس":
            bot.send_message(user_id, f"{EMOJIS['edit']} شماره تماس جدید را وارد کنید (شماره باید با 09 شروع شود و 11 رقم باشد یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
            user_states[user_id] = "edit_place_phone"
        elif text == f"{EMOJIS['edit']} ویرایش عکس":
            bot.send_message(user_id, f"{EMOJIS['edit']} عکس جدید را ارسال کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_photo"
        elif text == f"{EMOJIS['edit']} ویرایش شیفت صبح":
            bot.send_message(user_id, f"{EMOJIS['edit']} شیفت صبح جدید را وارد کنید (مثال: 8:00-12:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
            user_states[user_id] = "edit_place_morning_shift"
        elif text == f"{EMOJIS['edit']} ویرایش شیفت عصر":
            bot.send_message(user_id, f"{EMOJIS['edit']} شیفت عصر جدید را وارد کنید (مثال: 14:00-20:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
            user_states[user_id] = "edit_place_afternoon_shift"
    elif state == "edit_place_title":
        if text.strip():
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET title = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} عنوان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان نمی‌تواند خالی باشد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
    elif state == "edit_place_description":
        words = text.strip().split()
        if len(words) >= 10:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET description = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} توضیحات به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} توضیحات باید حداقل 10 کلمه باشد! ({len(words)} کلمه وارد کرده‌اید)", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
    elif state == "edit_place_address":
        if text.strip():
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET address = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} آدرس به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} آدرس نمی‌تواند خالی باشد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
    elif state == "edit_place_phone":
        if text == "رد کردن":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET phone = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", (None, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} شماره تماس به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        elif re.match(r'^09\d{9}$', text):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET phone = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} شماره تماس به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شماره موبایل باید با 09 شروع شود و 11 رقم باشد یا 'رد کردن' را انتخاب کنید!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
    elif state == "edit_place_morning_shift":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET morning_shift = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                  (None if text == "رد کردن" else text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} شیفت صبح به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    elif state == "edit_place_afternoon_shift":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET afternoon_shift = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                  (None if text == "رد کردن" else text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} شیفت عصر به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    elif state == "admin_menu":
        if text == "👥 کاربران فعال":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            total_users = c.fetchone()[0]
            conn.close()
            msg = f"{EMOJIS['info']} تعداد کل пользоваان فعال: {total_users}"
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("👦 نمایش کاربران پسر", "👧 نمایش کاربران دختر")
            keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
            bot.send_message(user_id, msg, reply_markup=keyboard)
            user_states[user_id] = "admin_view_gender"
        elif text == f"{EMOJIS['news']} ارسال خبر":
            bot.send_message(user_id, f"{EMOJIS['news']} بخش ارسال خبر:", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
        elif text == "🛡️ مدیر مکان‌ها":
            bot.send_message(user_id, f"{EMOJIS['info']} عنوان مکان را برای حذف وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_delete_place_title"
        elif text == "🚫 مسدود کردن کاربر":
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر را برای مسدود کردن وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_block_user"
        elif text == "🔓 رفع مسدودیت":
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر را برای رفع مسدودیت وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_unblock_user"
    elif state == "admin_news_menu":
        if text == f"{EMOJIS['group']} ارسال خبر گروهی":
            bot.send_message(user_id, f"{EMOJIS['news']} متن خبر گروهی را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_news_content"
        elif text == f"{EMOJIS['user']} ارسال خبر به کاربر":
            bot.send_message(user_id, f"{EMOJIS['news']} متن خبر را برای کاربر وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_news_user_content"
    elif state == "admin_news_user_content":
        if text.strip():
            user_data[user_id] = {'news_user_content': text}
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر مورد نظر را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_news_user_numeric_id"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} متن خبر نمی‌تواند خالی باشد!", reply_markup=admin_sub_menu())
    elif state == "admin_news_user_numeric_id":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                user_data[user_id]['target_user_numeric_id'] = numeric_id
                user_data[user_id]['target_user_id'] = target_user[0]
                user_data[user_id]['target_user_name'] = target_user[1]
                user_data[user_id]['target_user_age'] = target_user[2]
                user_data[user_id]['target_user_gender'] = target_user[3]
                
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("بله", "خیر")
                keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                
                msg = f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این خبر را برای کاربر زیر ارسال کنید؟\n\n"
                msg += f"👤 نام: {target_user[1]}\n"
                msg += f"🎂 سن: {target_user[2]}\n"
                msg += f"👫 جنسیت: {target_user[3]}\n\n"
                msg += f"📝 خبر:\n{user_data[user_id]['news_user_content']}"
                
                bot.send_message(user_id, msg, reply_markup=keyboard)
                user_states[user_id] = "admin_news_user_confirm"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه عددی یافت نشد!", reply_markup=admin_news_menu())
                user_states[user_id] = "admin_news_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=admin_sub_menu())
    elif state == "admin_news_user_confirm":
        if text == "بله":
            news_content = user_data[user_id]['news_user_content']
            target_user_id = user_data[user_id]['target_user_id']
            
            try:
                bot.send_message(target_user_id, f"{EMOJIS['news']} خبر ویژه برای شما:\n\n{news_content}")
                bot.send_message(user_id, f"{EMOJIS['success']} خبر با موفقیت برای کاربر ارسال شد!", reply_markup=admin_menu())
            except Exception as e:
                bot.send_message(user_id, f"{EMOJIS['error']} خطا در ارسال خبر: {str(e)}", reply_markup=admin_menu())
            
            user_states[user_id] = "admin_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} ارسال خبر لغو شد.", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
    elif state == "admin_view_gender":
        if text == "👦 نمایش کاربران پسر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_id, name, age, score, numeric_id FROM users WHERE gender = 'پسر'")
            users = c.fetchall()
            conn.close()
            if users:
                msg = f"{EMOJIS['info']} کاربران پسر:\n\n"
                msg += "\n".join([f"نام: {u[1]}\nسن: {u[2]}\nامتیاز: {u[3]}\nشناسه عددی: {u[4]}\nآیدی تلگرام: {u[0]}\n-------------------" for u in users])
            else:
                msg = f"{EMOJIS['error']} کاربر پسری یافت نشد!"
            bot.send_message(user_id, msg, reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif text == "👧 نمایش کاربران دختر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_id, name, age, score, numeric_id FROM users WHERE gender = 'دختر'")
            users = c.fetchall()
            conn.close()
            if users:
                msg = f"{EMOJIS['info']} کاربران دختر:\n\n"
                msg += "\n".join([f"نام: {u[1]}\nسن: {u[2]}\nامتیاز: {u[3]}\nشناسه عددی: {u[4]}\nآیدی تلگرام: {u[0]}\n-------------------" for u in users])
            else:
                msg = f"{EMOJIS['error']} کاربر دختری یافت نشد!"
            bot.send_message(user_id, msg, reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    elif state == "admin_block_user":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                telegram_id = target_user[0]
                username = target_user[1]
                user_data[user_id] = {'target_telegram_id': telegram_id, 'target_numeric_id': numeric_id}
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("بله", "خیر")
                keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید کاربر {username} را مسدود کنید؟", reply_markup=keyboard)
                user_states[user_id] = "admin_confirm_block"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه یافت نشد!", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=admin_sub_menu())
    elif state == "admin_confirm_block":
        if text == "بله":
            target_telegram_id = user_data[user_id]['target_telegram_id']
            block_user(target_telegram_id)
            bot.send_message(user_id, f"{EMOJIS['success']} کاربر مسدود شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
            try:
                bot.send_message(target_telegram_id, f"{EMOJIS['error']} شما به دلیل نقض قوانین از طرف ادمین مسدود شده اید❌برای رفع مسدودیت باید هزینه ای اندک بپردازید ‼️ برای هماهنگی به ایدی ادمین پیام دهید: @Sedayegoyom10")
            except:
                pass
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    elif state == "admin_unblock_user":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                telegram_id = target_user[0]
                user_data[user_id] = {'target_telegram_id': telegram_id, 'target_numeric_id': numeric_id}
                if is_user_blocked(telegram_id):
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.row("بله", "خیر")
                    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                    bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید کاربر را از مسدودیت خارج کنید؟", reply_markup=keyboard)
                    user_states[user_id] = "admin_confirm_unblock"
                else:
                    bot.send_message(user_id, f"{EMOJIS['error']} این کاربر مسدود نیست❌", reply_markup=admin_menu())
                    user_states[user_id] = "admin_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه یافت نشد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=admin_sub_menu())
    elif state == "admin_confirm_unblock":
        if text == "بله":
            target_telegram_id = user_data[user_id]['target_telegram_id']
            unblock_user(target_telegram_id)
            bot.send_message(user_id, f"{EMOJIS['success']} کاربر از مسدودیت خارج شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
            try:
                bot.send_message(target_telegram_id, f"{EMOJIS['success']} شما رفع مسدود شدید و دیگر میتوانید از قابلیت‌های ربات استفاده کنید🔥")
            except:
                pass
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    elif state == "admin_news_content":
        if text.strip():
            user_data[user_id] = {'news_content': text}
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("بله", "خیر")
            keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
            bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این خبر را ارسال کنید؟\n\n{text}", reply_markup=keyboard)
            user_states[user_id] = "admin_news_confirm"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} متن خبر نمی‌تواند خالی باشد!", reply_markup=admin_sub_menu())
    elif state == "admin_news_confirm":
        if text == "بله":
            news_content = user_data[user_id]['news_content']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO news (content) VALUES (?)", (news_content,))
            c.execute("SELECT user_id FROM users")
            users = c.fetchall()
            conn.commit()
            conn.close()
            success_count = 0
            for user in users:
                try:
                    bot.send_message(user[0], f"{EMOJIS['news']} خبر جدید:\n{news_content}")
                    success_count += 1
                except:
                    pass
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row(f"{EMOJIS['delete']} حذف خبر", f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
            msg = f"{EMOJIS['success']} خبر با موفقیت به {success_count} کاربر ارسال شد!"
            bot.send_message(user_id, msg, reply_markup=keyboard)
            user_states[user_id] = "admin_news_sent"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} ارسال خبر لغو شد.", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    elif state == "admin_news_sent":
        if text == f"{EMOJIS['delete']} حذف خبر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM news WHERE news_id = (SELECT MAX(news_id) FROM news)")
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} خبر حذف شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    elif state == "admin_delete_place_title":
        if text.strip():
            user_data[user_id] = {'delete_place_title': text}
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for cat in PLACE_CATEGORIES:
                keyboard.row(f"📌 {cat}")
            keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
            bot.send_message(user_id, f"{EMOJIS['places']} دسته مکان را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "admin_delete_place_category"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان مکان نمی‌تواند خالی باشد!", reply_markup=admin_sub_menu())
    elif state == "admin_delete_place_category":
        if text.startswith("📌"):
            category = text[2:]
            if category in PLACE_CATEGORIES:
                user_data[user_id]['delete_place_category'] = category
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for sub in PLACE_CATEGORIES[category]:
                    keyboard.row(f"🔹 {sub}")
                keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                bot.send_message(user_id, f"{EMOJIS['places']} زیردسته مکان را انتخاب کنید:", reply_markup=keyboard)
                user_states[user_id] = "admin_delete_place_subcategory"
    elif state == "admin_delete_place_subcategory":
        if text.startswith("🔹"):
            subcategory = text[2:]
            category = user_data[user_id].get('delete_place_category', '')
            if subcategory in PLACE_CATEGORIES.get(category, []):
                user_data[user_id]['delete_place_subcategory'] = subcategory
                bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر مالک مکان را وارد کنید:", reply_markup=admin_sub_menu())
                user_states[user_id] = "admin_delete_place_user_id"
    elif state == "admin_delete_place_user_id":
        try:
            numeric_id = int(text)
            user_data[user_id]['delete_place_numeric_id'] = numeric_id
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE numeric_id = ?", (numeric_id,))
            user_result = c.fetchone()
            if user_result:
                user_db_id = user_result[0]
                title = user_data[user_id]['delete_place_title']
                category = user_data[user_id]['delete_place_category']
                subcategory = user_data[user_id]['delete_place_subcategory']
                c.execute("SELECT place_id FROM places WHERE user_id = ? AND title = ? AND category = ? AND subcategory = ?",
                          (user_db_id, title, category, subcategory))
                place_result = c.fetchone()
                if place_result:
                    user_data[user_id]['delete_place_id'] = place_result[0]
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.row("بله", "خیر")
                    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                    bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این مکان را حذف کنید؟\nعنوان: {title}", reply_markup=keyboard)
                    user_states[user_id] = "admin_delete_place_confirm"
                else:
                    bot.send_message(user_id, f"{EMOJIS['error']} مکانی با این مشخصات یافت نشد!", reply_markup=admin_menu())
                    user_states[user_id] = "admin_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه عددی یافت نشد!", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=admin_sub_menu())
    elif state == "admin_delete_place_confirm":
        if text == "بله":
            place_id = user_data[user_id]['delete_place_id']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM places WHERE place_id = ?", (place_id,))
            c.execute("DELETE FROM place_ratings WHERE place_id = ?", (place_id,))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} مکان با موفقیت حذف شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} حذف مکان لغو شد.", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    elif state == "place_rate":
        try:
            rating = int(text)
            if 0 <= rating <= 10:
                user_data[user_id]['rating'] = rating
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("بله", "خیر")
                keyboard.row(f"{EMOJIS['back']} برگشت")
                bot.send_message(user_id, f"{EMOJIS['rating']} آیا امتیاز {rating} برای این مکان صحیح است؟", reply_markup=keyboard)
                user_states[user_id] = "place_rate_confirm"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} امتیاز باید بین 0 تا 10 باشد!", reply_markup=back_button_only())
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً عدد معتبر وارد کنید!", reply_markup=back_button_only())
    elif state == "place_rate_confirm":
        if text == "بله":
            place_id = user_data[user_id]['place_id']
            rating = user_data[user_id]['rating']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            # ثبت امتیاز
            c.execute("INSERT OR REPLACE INTO place_ratings (place_id, user_id, rating) VALUES (?, ?, ?)", (place_id, user_id, rating))
            c.execute("SELECT rating_sum, rating_count, user_id FROM places WHERE place_id = ?", (place_id,))
            current = c.fetchone()
            rating_sum = current[0] + rating if current else rating
            rating_count = current[1] + 1 if current else 1
            owner_id = current[2]
            c.execute("UPDATE places SET rating_sum = ?, rating_count = ? WHERE place_id = ?", (rating_sum, rating_count, place_id))
            # دریافت اطلاعات کاربر
            c.execute("SELECT name, age, gender FROM users WHERE user_id = ?", (user_id,))
            user_info = c.fetchone()
            conn.commit()
            conn.close()
            avg_rating = rating_sum / rating_count
            # ارسال پیام به کاربر
            bot.send_message(user_id, f"{EMOJIS['success']} امتیاز شما ({rating}) ثبت شد! میانگین امتیاز: {avg_rating:.1f}", reply_markup=get_place_menu())
            # ارسال پیام به صاحب مکان
            if owner_id:
                try:
                    bot.send_message(owner_id, f"{EMOJIS['rating']} کاربر جدید به مکان شما امتیاز داد:\n"
                                              f"نام: {user_info[0]}\nسن: {user_info[1]}\nجنسیت: {user_info[2]}\nامتیاز: {rating}")
                except:
                    pass
            user_states[user_id] = "place_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} امتیازدهی لغو شد. لطفاً امتیاز جدیدی وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_rate"

# مدیریت عکس‌ها
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما به دلیل نقض قوانین از طرف ادمین مسدود شده اید❌برای رفع مسدودیت باید هزینه ای اندک بپردازید ‼️ برای هماهنگی به ایدی ادمین پیام دهید: @Sedayegoyom10")
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
        c.execute("UPDATE places SET photo = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", (photo_id, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} عکس مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"

# مدیریت دکمه‌های اینلاین
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما به دلیل نقض قوانین از طرف ادمین مسدود شده اید❌برای رفع مسدودیت باید هزینه ای اندک بپردازید ‼️ برای هماهنگی به ایدی ادمین پیام دهید: @Sedayegoyom10")
        return
    data = call.data
    if data == "accept_terms":
        user = get_user(user_id)
        if user:
            bot.send_message(user_id, f"{EMOJIS['success']} خوش برگشتی! 😍", reply_markup=main_menu())
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
    elif data.startswith("delete_place"):
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
    elif data.startswith("edit_place"):
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
    elif data.startswith("rate_place"):
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

# اجرای ربات در حالت وب هوک
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)