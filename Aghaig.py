import telebot
from telebot import types
import sqlite3
import random
import re
from flask import Flask, request
import logging
import time

# تنظیمات
API_TOKEN = "8134200098:AAGGapErG9F0ek0lAEdrI53E5gzPDcObTQM"
ADMIN_ID = 7385601641
WEBHOOK_URL = "https://gogogo-mpge.onrender.com"
PORT = 5000
DB_NAME = "goyim.db"

# راه‌اندازی ربات و سرور Flask
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# تنظیم لاگ
telebot.logger.setLevel(logging.INFO)

# استیکرهای مخصوص
EMOJIS = {
    "profile": "👤", "ads": "📢", "places": "📍", "back": "🔙", "home": "🏠",
    "edit": "✏️", "delete": "🗑️", "add": "➕", "view": "👁️", "success": "✅",
    "error": "❌", "info": "ℹ️", "star": "⭐", "admin": "🔧", "news": "📰",
    "help": "❓", "link": "🔗", "document": "📋", "warning": "⚠️", "search": "🔍"
}

# متغیرهای حالت کاربر
user_states = {}
user_data = {}

# تنظیم پایگاه داده
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # جدول users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER,
        gender TEXT,
        score INTEGER DEFAULT 0,
        numeric_id INTEGER UNIQUE,
        accepted_terms INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0
    )''')
    
    # بررسی و اضافه کردن ستون‌های مورد نیاز
    c.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in c.fetchall()]
    
    if 'accepted_terms' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN accepted_terms INTEGER DEFAULT 0")
    if 'is_blocked' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
    
    # جدول ads
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
        photo TEXT
    )''')
    
    # جدول news
    c.execute('''CREATE TABLE IF NOT EXISTS news (
        news_id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT
    )''')
    
    conn.commit()
    conn.close()

init_db()

# دسته‌بندی آگهی‌ها
AD_CATEGORIES = {
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
    c.execute("INSERT OR REPLACE INTO users (user_id, name, age, gender, score, numeric_id, accepted_terms, is_blocked) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, name, age, gender, 0, numeric_id, 1, 0))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def is_user_blocked(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

def block_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def unblock_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def has_accepted_terms(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT accepted_terms FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

# منوها
def main_menu(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['profile']} پروفایل")
    keyboard.row(f"{EMOJIS['ads']} آگهی‌ها")
    keyboard.row(f"{EMOJIS['star']} گویمی‌های برتر")
    keyboard.row(f"{EMOJIS['link']} لینک‌ها", f"{EMOJIS['help']} راهنما")
    
    # فقط ادمین می‌تواند دکمه ادمین را ببیند
    if user_id == ADMIN_ID:
        keyboard.row(f"{EMOJIS['admin']} ادمین")
    
    return keyboard

def profile_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مشاهده پروفایل")
    keyboard.row("تغییر نام", "تغییر سن", "تغییر جنسیت")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def get_ad_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['add']} اضافه کردن آگهی")
    keyboard.row(f"{EMOJIS['view']} مشاهده آگهی‌ها", f"{EMOJIS['view']} آگهی‌های من")
    keyboard.row(f"{EMOJIS['search']} جستجو")
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

def terms_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['success']} پذیرفتن")
    keyboard.row(f"{EMOJIS['error']} نپذیرفتن")
    return keyboard

def retry_terms_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['info']} درخواست دوباره")
    return keyboard

def admin_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("👥 کاربران فعال")
    keyboard.row(f"{EMOJIS['news']} ارسال خبر")
    keyboard.row("🛡️ مدیر آگهی")
    keyboard.row("🚫 مسدود کردن کاربر", "🔓 رفع مسدودیت")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def photo_management_keyboard(photo_count):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if photo_count < 5:
        keyboard.row(f"{EMOJIS['add']} ارسال عکس دیگر", f"{EMOJIS['success']} تأیید")
    else:
        keyboard.row(f"{EMOJIS['success']} تأیید")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def ad_view_result_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['search']} جستجو دوباره")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

# متن قوانین
def get_terms_text():
    terms_text = f"{EMOJIS['document']} {EMOJIS['star']} قوانین و مقررات ربات صدای گویم {EMOJIS['star']}\n\n"
    terms_text += f"{EMOJIS['info']} {EMOJIS['star']} معرفی ربات:\n"
    terms_text += "ربات صدای گویم یک پلتفرم ارتباطی برای خرید و فروش کالاها و خدمات در جامعه است.\n\n"
    terms_text += f"{EMOJIS['profile']} {EMOJIS['star']} اطلاعات کاربران:\n"
    terms_text += "• اطلاعاتی که از شما گرفته می‌شود: نام، سن، جنسیت\n"
    terms_text += "• این اطلاعات به هیچ وجه فاش نخواهد شد\n"
    terms_text += "• اطلاعات شما فقط برای بهبود تجربه کاربری استفاده می‌شود\n\n"
    terms_text += f"{EMOJIS['ads']} {EMOJIS['star']} خرید و فروش:\n"
    terms_text += "• شما مسئولیت کامل خرید و فروش خود را می‌پذیرید\n"
    terms_text += "• هرگونه تخلف در معاملات بر عهده خود شماست\n"
    terms_text += "• ربات تنها یک پلتفرم ارتباطی است و مسئولیت معاملات را ندارد\n\n"
    terms_text += f"{EMOJIS['error']} {EMOJIS['star']} موارد ممنوع:\n"
    terms_text += "• آگهی‌های نامناسب و مستهجن\n"
    terms_text += "• محتوای توهین‌آمیز و تحقیرآمیز\n"
    terms_text += "• کالاهای غیرقانونی و ممنوعه\n"
    terms_text += "• اطلاعات جعلی و نادرست\n"
    terms_text += "• هرگونه کلاهبرداری\n\n"
    terms_text += f"{EMOJIS['warning']} {EMOJIS['star']} هشدارها:\n"
    terms_text += "• تخلف از قوانین منجر به مسدودیت دائمی می‌شود\n"
    terms_text += "• برای رفع مسدودیت باید هزینه پرداخت کنید\n"
    terms_text += "• رعایت ادب و احترام در تعاملات الزامی است\n\n"
    terms_text += f"{EMOJIS['success']} {EMOJIS['star']} پذیرش قوانین:\n"
    terms_text += "با پذیرفتن این قوانین، شما مسئولیت کامل اقدامات خود را می‌پذیرید.\n"
    terms_text += "هرگونه مشکل در معاملات بر عهده خود شماست.\n\n"
    terms_text += f"{EMOJIS['link']} {EMOJIS['star']} ارتباط با ما:\n"
    terms_text += "پیج اصلی صدای گویم:\n"
    terms_text += "https://www.instagram.com/sedayegoyom?igsh=MXd0MTlkZGdzNzZ6bw==\n\n"
    terms_text += "ایدی ادمین:\n"
    terms_text += "@Sedayegoyom10\n\n"
    terms_text += f"{EMOJIS['star']} {EMOJIS['star']} {EMOJIS['star']} لطفاً قوانین را با دقت مطالعه کنید {EMOJIS['star']} {EMOJIS['star']} {EMOJIS['star']}"
    return terms_text

# تابع برای نمایش عکس‌های آگهی
def display_ad_photos(user_id, photos, ad_info, is_admin=False, numeric_id=None):
    if photos:
        photo_list = photos.split("|")
        media = [types.InputMediaPhoto(photo_id) for photo_id in photo_list if photo_id]
        if media:
            try:
                bot.send_media_group(user_id, media)
            except:
                pass
    msg = f"{EMOJIS['ads']} آگهی:\n"
    msg += f"عنوان: {ad_info[4]}\n"
    msg += f"دسته: {ad_info[2]}\n"
    msg += f"زیردسته: {ad_info[3]}\n"
    msg += f"توضیحات: {ad_info[5]}\n"
    msg += f"قیمت: {ad_info[6]} تومان\n"
    msg += f"آدرس: {ad_info[7] or 'مشخص نشده'}\n"
    msg += f"تماس: {ad_info[8] or 'مشخص نشده'}"
    if is_admin and numeric_id:
        msg += f"\nشناسه عددی مالک: {numeric_id}"
    bot.send_message(user_id, msg)

# دستور شروع
@app.route('/', methods=['GET'])
def index():
    return "ربات صدای گویم در حال اجراست!"

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403

@bot.message_handler(commands=['start', 'admin'])
def start(message):
    user_id = message.from_user.id
    
    # بررسی مسدودیت کاربر
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.\n\nبرای رفع مسدودیت باید هزینه‌ای اندک بپردازید‼️\nبرای هماهنگی به ایدی ادمین پیام دهید:\n@Sedayegoyom10")
        return
    
    # بررسی اینکه کاربر قوانین را پذیرفته یا نه
    if not has_accepted_terms(user_id):
        terms_text = get_terms_text()
        bot.send_message(user_id, terms_text, reply_markup=terms_menu())
        user_states[user_id] = "awaiting_terms_acceptance"
        return
    
    # اگر کاربر اطلاعات پروفایل را کامل نکرده باشد
    user = get_user(user_id)
    if not user or not user[1]:  # اگر نام کاربر وجود ندارد
        bot.send_message(user_id, "لطفاً نام خود را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "awaiting_name"
        user_data[user_id] = {}
        return
    
    # نمایش منوی اصلی
    if message.text == '/admin' and user_id == ADMIN_ID:
        bot.send_message(user_id, f"{EMOJIS['admin']} به پنل ادمین خوش آمدید!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    else:
        bot.send_message(user_id, f"{EMOJIS['success']} به ربات صدای گویم خوش آمدید!", reply_markup=main_menu(user_id))
        user_states[user_id] = "main_menu"

# مدیریت پیام‌ها
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    text = message.text
    
    # بررسی مسدودیت کاربر
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.\n\nبرای رفع مسدودیت باید هزینه‌ای اندک بپردازید‼️\nبرای هماهنگی به ایدی ادمین پیام دهید:\n@Sedayegoyom10")
        return
    
    state = user_states.get(user_id, "main_menu")
    
    # مدیریت دکمه برگشت
    if text == f"{EMOJIS['back']} برگشت":
        handle_back_button(user_id, state)
        return
    elif text == f"{EMOJIS['home']} صفحه اصلی":
        bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu(user_id))
        user_states[user_id] = "main_menu"
        return
    
    # مدیریت حالت‌های مختلف
    if state == "awaiting_terms_acceptance":
        handle_awaiting_terms_acceptance(user_id, text)
    elif state == "awaiting_terms_rejection":
        handle_awaiting_terms_rejection(user_id, text)
    elif state == "awaiting_name":
        handle_awaiting_name(user_id, text)
    elif state == "awaiting_age":
        handle_awaiting_age(user_id, text)
    elif state == "awaiting_gender":
        handle_awaiting_gender(user_id, text)
    elif state == "main_menu":
        handle_main_menu(user_id, text)
    elif state == "profile_menu":
        handle_profile_menu(user_id, text)
    elif state == "profile_edit_name":
        handle_profile_edit_name(user_id, text)
    elif state == "profile_edit_age":
        handle_profile_edit_age(user_id, text)
    elif state == "profile_edit_gender":
        handle_profile_edit_gender(user_id, text)
    elif state == "ad_menu":
        handle_ad_menu(user_id, text)
    elif state == "ad_add_category":
        handle_ad_add_category(user_id, text)
    elif state == "ad_add_subcategory":
        handle_ad_add_subcategory(user_id, text)
    elif state == "ad_add_title":
        handle_ad_add_title(user_id, text)
    elif state == "ad_add_description":
        handle_ad_add_description(user_id, text)
    elif state == "ad_add_price":
        handle_ad_add_price(user_id, text)
    elif state == "ad_add_address":
        handle_ad_add_address(user_id, text)
    elif state == "ad_add_phone":
        handle_ad_add_phone(user_id, text)
    elif state == "ad_add_photo_collect":
        handle_ad_add_photo_collect(user_id, text)
    elif state == "ad_view_category":
        handle_ad_view_category(user_id, text)
    elif state == "ad_view_subcategory":
        handle_ad_view_subcategory(user_id, text)
    elif state == "ad_search_title":
        handle_ad_search_title(user_id, text)
    elif state == "ad_search_min_price":
        handle_ad_search_min_price(user_id, text)
    elif state == "ad_search_max_price":
        handle_ad_search_max_price(user_id, text)
    elif state == "ad_view_result":
        handle_ad_view_result(user_id, text)
    elif state == "ad_my_ads":
        handle_ad_my_ads(user_id, text)
    elif state == "edit_ad_menu":
        handle_edit_ad_menu(user_id, text)
    elif state == "edit_ad_title":
        handle_edit_ad_title(user_id, text)
    elif state == "edit_ad_description":
        handle_edit_ad_description(user_id, text)
    elif state == "edit_ad_price":
        handle_edit_ad_price(user_id, text)
    elif state == "edit_ad_address":
        handle_edit_ad_address(user_id, text)
    elif state == "edit_ad_phone":
        handle_edit_ad_phone(user_id, text)
    elif state == "edit_ad_photo_collect":
        handle_edit_ad_photo_collect(user_id, text)
    elif state == "admin_menu":
        handle_admin_menu(user_id, text)
    elif state == "admin_view_gender":
        handle_admin_view_gender(user_id, text)
    elif state == "admin_users":
        handle_admin_users(user_id, text)
    elif state == "admin_block_user":
        handle_admin_block_user(user_id, text)
    elif state == "admin_confirm_block":
        handle_admin_confirm_block(user_id, text)
    elif state == "admin_unblock_user":
        handle_admin_unblock_user(user_id, text)
    elif state == "admin_confirm_unblock":
        handle_admin_confirm_unblock(user_id, text)
    elif state == "admin_news_content":
        handle_admin_news_content(user_id, text)
    elif state == "admin_news_confirm":
        handle_admin_news_confirm(user_id, text)
    elif state == "admin_news_sent":
        handle_admin_news_sent(user_id, text)
    elif state == "admin_delete_ad_title":
        handle_admin_delete_ad_title(user_id, text)
    elif state == "admin_delete_ad_category":
        handle_admin_delete_ad_category(user_id, text)
    elif state == "admin_delete_ad_subcategory":
        handle_admin_delete_ad_subcategory(user_id, text)
    elif state == "admin_delete_ad_user_id":
        handle_admin_delete_ad_user_id(user_id, text)
    elif state == "admin_delete_ad_confirm":
        handle_admin_delete_ad_confirm(user_id, text)

# تابع مدیریت دکمه برگشت
def handle_back_button(user_id, state):
    if state in ["profile_menu", "profile_view", "profile_edit_name", "profile_edit_age", "profile_edit_gender"]:
        bot.send_message(user_id, "بخش پروفایل:", reply_markup=profile_menu())
        user_states[user_id] = "profile_menu"
    elif state in ["ad_menu", "ad_add_category", "ad_add_subcategory", "ad_add_title", "ad_add_description", 
                  "ad_add_price", "ad_add_address", "ad_add_phone", "ad_add_photo_collect", "ad_view_category", 
                  "ad_view_subcategory", "ad_my_ads", "ad_view_result", "ad_search_title", "ad_search_min_price", 
                  "ad_search_max_price"]:
        bot.send_message(user_id, "بخش آگهی‌ها:", reply_markup=get_ad_menu())
        user_states[user_id] = "ad_menu"
    elif state in ["edit_ad_menu", "edit_ad_title", "edit_ad_description", "edit_ad_price", "edit_ad_address", 
                  "edit_ad_phone", "edit_ad_photo_collect"]:
        bot.send_message(user_id, "آگهی‌های شما:", reply_markup=get_ad_menu())
        user_states[user_id] = "ad_menu"
    elif state in ["admin_menu", "admin_view_gender", "admin_users", "admin_news_content", "admin_news_confirm", 
                  "admin_news_sent", "admin_delete_ad_title", "admin_delete_ad_category", "admin_delete_ad_subcategory", 
                  "admin_delete_ad_user_id", "admin_delete_ad_confirm", "admin_block_user", "admin_confirm_block", 
                  "admin_unblock_user", "admin_confirm_unblock"]:
        bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    else:
        bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu(user_id))
        user_states[user_id] = "main_menu"

# توابع مدیریت حالت‌های مختلف
def handle_awaiting_terms_acceptance(user_id, text):
    if text == f"{EMOJIS['success']} پذیرفتن":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET accepted_terms = 1 WHERE user_id = ?", (user_id,))
        if c.rowcount == 0:
            c.execute("INSERT INTO users (user_id, accepted_terms) VALUES (?, ?)", (user_id, 1))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} قوانین پذیرفته شد!\nلطفاً نام خود را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "awaiting_name"
        user_data[user_id] = {}
    elif text == f"{EMOJIS['error']} نپذیرفتن":
        bot.send_message(user_id, f"{EMOJIS['error']} برای استفاده از ربات باید قوانین را بپذیرید!\nدر صورت عدم پذیرش شما قادر به استفاده از این ربات نخواهید بود.", reply_markup=retry_terms_menu())
        user_states[user_id] = "awaiting_terms_rejection"
    else:
        terms_text = get_terms_text()
        bot.send_message(user_id, terms_text, reply_markup=terms_menu())

def handle_awaiting_terms_rejection(user_id, text):
    if text == f"{EMOJIS['info']} درخواست دوباره":
        terms_text = get_terms_text()
        bot.send_message(user_id, terms_text, reply_markup=terms_menu())
        user_states[user_id] = "awaiting_terms_acceptance"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} برای استفاده از ربات باید قوانین را بپذیرید!", reply_markup=retry_terms_menu())

def handle_awaiting_name(user_id, text):
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

def handle_awaiting_age(user_id, text):
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

def handle_awaiting_gender(user_id, text):
    if text in ["👦 پسر", "👧 دختر", "🌀 دیگر"]:
        gender = text.split()[1] if " " in text else text
        user_data[user_id]['gender'] = gender
        save_user(user_id, user_data[user_id]['name'], user_data[user_id]['age'], gender)
        user = get_user(user_id)
        profile_msg = f"{EMOJIS['profile']} پروفایل شما:\n"
        profile_msg += f"نام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}"
        bot.send_message(user_id, profile_msg, reply_markup=main_menu(user_id))
        user_states[user_id] = "main_menu"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} یکی از گزینه‌ها را انتخاب کنید!")

def handle_main_menu(user_id, text):
    if text == f"{EMOJIS['profile']} پروفایل":
        user = get_user(user_id)
        if user:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("مشاهده پروفایل")
            keyboard.row("تغییر نام", "تغییر سن", "تغییر جنسیت")
            keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
            profile_msg = f"{EMOJIS['profile']} پروفایل شما:\n"
            profile_msg += f"نام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}"
            bot.send_message(user_id, profile_msg, reply_markup=keyboard)
            user_states[user_id] = "profile_menu"
    elif text == f"{EMOJIS['ads']} آگهی‌ها":
        bot.send_message(user_id, f"{EMOJIS['ads']} به بخش آگهی‌ها خوش آمدید!", reply_markup=get_ad_menu())
        user_states[user_id] = "ad_menu"
    elif text == f"{EMOJIS['star']} گویمی‌های برتر":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT name, score FROM users WHERE score >= 1000 ORDER BY score DESC")
        users = c.fetchall()
        conn.close()
        if users:
            msg = f"{EMOJIS['star']} گویمی‌های برتر:\n"
            msg += "\n".join([f"{u[0]}: {u[1]} امتیاز" for u in users])
        else:
            msg = f"{EMOJIS['error']} هنوز کسی به ۱۰۰۰ امتیاز نرسیده است!"
        bot.send_message(user_id, msg, reply_markup=back_home_buttons())
    elif text == f"{EMOJIS['link']} لینک‌ها":
        link_text = f"{EMOJIS['link']} لینک‌های مفید:\n\n"
        link_text += f"{EMOJIS['link']} لینک پیج اصلی صدای گویم:\n"
        link_text += "https://www.instagram.com/sedayegoyom?igsh=MXd0MTlkZGdzNzZ6bw==\n\n"
        link_text += f"{EMOJIS['admin']} ایدی ادمین صدای گویم:\n"
        link_text += "@Sedayegoyom10"
        bot.send_message(user_id, link_text, reply_markup=main_menu(user_id))
    elif text == f"{EMOJIS['help']} راهنما":
        help_text = f"{EMOJIS['help']} راهنمای استفاده از ربات:\n\n"
        help_text += f"{EMOJIS['profile']} بخش پروفایل:\n"
        help_text += "• مشاهده اطلاعات شخصی خود\n"
        help_text += "• ویرایش نام، سن و جنسیت\n\n"
        help_text += f"{EMOJIS['ads']} بخش آگهی‌ها:\n"
        help_text += "• اضافه کردن آگهی جدید با حداکثر ۵ عکس\n"
        help_text += "• مشاهده آگهی‌ها بر اساس دسته‌بندی\n"
        help_text += "• جستجوی آگهی‌ها بر اساس عنوان و قیمت\n"
        help_text += "• مدیریت آگهی‌های خود (ویرایش/حذف)\n"
        help_text += "• هر آگهی ۱۵ امتیاز برای شما\n\n"
        help_text += f"{EMOJIS['star']} گویمی‌های برتر:\n"
        help_text += "• مشاهده کاربران با بیشترین امتیاز\n"
        help_text += "• حداقل ۱۰۰۰ امتیاز برای نمایش\n\n"
        help_text += f"{EMOJIS['link']} بخش لینک‌ها:\n"
        help_text += "• دسترسی به پیج اصلی\n"
        help_text += "• ارتباط با ادمین\n\n"
        help_text += f"{EMOJIS['info']} قوانین مهم:\n"
        help_text += "• آگهی‌های نامناسب مسدود می‌شوند\n"
        help_text += "• محتوای مستهجن یا توهین‌آمیز مجاز نیست\n"
        help_text += "• اطلاعات واقعی و دقیق وارد کنید\n"
        help_text += "• رعایت ادب و احترام در تعاملات\n"
        help_text += "• تخلف از قوانین منجر به مسدودیت می‌شود\n\n"
        help_text += f"{EMOJIS['success']} موفق باشید!"
        bot.send_message(user_id, help_text, reply_markup=main_menu(user_id))
    elif text == f"{EMOJIS['admin']} ادمین" and user_id == ADMIN_ID:
        bot.send_message(user_id, f"{EMOJIS['admin']} به پنل ادمین خوش آمدید!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"

def handle_profile_menu(user_id, text):
    if text == "مشاهده پروفایل":
        user = get_user(user_id)
        if user:
            profile_msg = f"{EMOJIS['profile']} پروفایل شما:\n"
            profile_msg += f"نام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nامتیاز: {user[4]}\nشناسه: {user[5]}"
            bot.send_message(user_id, profile_msg, reply_markup=profile_menu())
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

def handle_profile_edit_name(user_id, text):
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

def handle_profile_edit_age(user_id, text):
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

def handle_profile_edit_gender(user_id, text):
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

def handle_ad_menu(user_id, text):
    if text == f"{EMOJIS['add']} اضافه کردن آگهی":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for cat in AD_CATEGORIES:
            keyboard.row(f"📌 {cat}")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        bot.send_message(user_id, f"{EMOJIS['ads']} یک دسته انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "ad_add_category"
    elif text == f"{EMOJIS['view']} مشاهده آگهی‌ها":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for cat in AD_CATEGORIES:
            keyboard.row(f"📌 {cat}")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        bot.send_message(user_id, f"{EMOJIS['ads']} یک دسته انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "ad_view_category"
    elif text == f"{EMOJIS['view']} آگهی‌های من":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM ads WHERE user_id = ?", (user_id,))
        ads = c.fetchall()
        conn.close()
        if ads:
            for ad in ads:
                display_ad_photos(user_id, ad[9], ad)
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_ad_{ad[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_ad_{ad[0]}"))
                bot.send_message(user_id, "انتخاب کنید:", reply_markup=keyboard)
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شما آگهی‌ای ندارید!")
        bot.send_message(user_id, "انتخاب کنید:", reply_markup=back_home_buttons())
        user_states[user_id] = "ad_my_ads"
    elif text == f"{EMOJIS['search']} جستجو":
        bot.send_message(user_id, f"{EMOJIS['search']} نام کالا یا عنوان آگهی را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "ad_search_title"

def handle_ad_add_category(user_id, text):
    if text.startswith("📌"):
        category = text[2:]
        if category in AD_CATEGORIES:
            user_data[user_id] = {'category': category}
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for sub in AD_CATEGORIES[category]:
                keyboard.row(f"🔹 {sub}")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['ads']} یک زیرشاخه انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "ad_add_subcategory"

def handle_ad_add_subcategory(user_id, text):
    if text.startswith("🔹"):
        subcategory = text[2:]
        category = user_data[user_id].get('category', '')
        if subcategory in AD_CATEGORIES.get(category, []):
            user_data[user_id]['subcategory'] = subcategory
            bot.send_message(user_id, f"{EMOJIS['ads']} عنوان آگهی را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "ad_add_title"

def handle_ad_add_title(user_id, text):
    if text.strip():
        user_data[user_id]['title'] = text
        bot.send_message(user_id, f"{EMOJIS['ads']} توضیحات آگهی را وارد کنید (حداقل 10 کلمه):", reply_markup=back_button_only())
        user_states[user_id] = "ad_add_description"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} عنوان نمی‌تواند خالی باشد!")

def handle_ad_add_description(user_id, text):
    words = text.strip().split()
    if len(words) >= 10:
        user_data[user_id]['description'] = text
        bot.send_message(user_id, f"{EMOJIS['ads']} قیمت را به تومان وارد کنید (فقط عدد):", reply_markup=back_button_only())
        user_states[user_id] = "ad_add_price"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} توضیحات باید حداقل 10 کلمه باشد! ({len(words)} کلمه وارد کرده‌اید)")

def handle_ad_add_price(user_id, text):
    try:
        price = int(text.replace(",", ""))
        if price > 0:
            user_data[user_id]['price'] = f"{price:,}"
            bot.send_message(user_id, f"{EMOJIS['ads']} آدرس را وارد کنید (یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
            user_states[user_id] = "ad_add_address"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} قیمت باید بیشتر از صفر باشد!")
    except ValueError:
        bot.send_message(user_id, f"{EMOJIS['error']} لطفاً فقط عدد وارد کنید!")

def handle_ad_add_address(user_id, text):
    if text == "رد کردن":
        user_data[user_id]['address'] = None
        bot.send_message(user_id, f"{EMOJIS['ads']} شماره تماس را وارد کنید (شماره باید با 09 شروع شود و 11 رقم باشد):", reply_markup=back_button_only())
        user_states[user_id] = "ad_add_phone"
    else:
        user_data[user_id]['address'] = text
        bot.send_message(user_id, f"{EMOJIS['ads']} شماره تماس را وارد کنید (شماره باید با 09 شروع شود و 11 رقم باشد):", reply_markup=back_button_only())
        user_states[user_id] = "ad_add_phone"

def handle_ad_add_phone(user_id, text):
    if text.strip():
        if re.match(r'^09\d{9}$', text):
            user_data[user_id]['phone'] = text
            user_data[user_id]['photos'] = []  # لیست برای ذخیره موقت عکس‌ها
            bot.send_message(user_id, f"{EMOJIS['ads']} یک عکس برای آگهی ارسال کنید (حداکثر ۵ عکس):", reply_markup=photo_management_keyboard(0))
            user_states[user_id] = "ad_add_photo_collect"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شماره موبایل باید با 09 شروع شود و 11 رقم باشد!")
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} شماره تماس نمی‌تواند خالی باشد!")

def handle_ad_add_photo_collect(user_id, text):
    if text == f"{EMOJIS['success']} تأیید":
        if user_data[user_id]['photos']:
            photos = "|".join(user_data[user_id]['photos'])
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO ads (user_id, category, subcategory, title, description, price, address, phone, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (user_id, user_data[user_id]['category'], user_data[user_id]['subcategory'], user_data[user_id]['title'], user_data[user_id]['description'], user_data[user_id]['price'], user_data[user_id]['address'], user_data[user_id]['phone'], photos))
            c.execute("UPDATE users SET score = score + 15 WHERE user_id = ?", (user_id,))
            c.execute("SELECT user_id FROM users")
            users = c.fetchall()
            conn.commit()
            conn.close()
            
            notification = f"{EMOJIS['ads']} آگهی جدید در دسته {user_data[user_id]['category']}، زیردسته {user_data[user_id]['subcategory']} ثبت شد:\nعنوان: {user_data[user_id]['title']}\nبرای بررسی به بخش آگهی‌ها مراجعه کنید."
            for user in users:
                if user[0] != user_id:
                    try:
                        bot.send_message(user[0], notification)
                    except:
                        pass
            
            bot.send_message(user_id, f"{EMOJIS['success']} آگهی با موفقیت ثبت شد! ۱۵ امتیاز به شما اضافه شد.", reply_markup=get_ad_menu())
            user_states[user_id] = "ad_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} حداقل یک عکس باید ارسال کنید!", reply_markup=photo_management_keyboard(len(user_data[user_id]['photos'])))
    elif text == f"{EMOJIS['add']} ارسال عکس دیگر":
        bot.send_message(user_id, f"{EMOJIS['ads']} عکس بعدی را ارسال کنید (تا {5 - len(user_data[user_id]['photos'])} عکس دیگر):", reply_markup=photo_management_keyboard(len(user_data[user_id]['photos'])))

def handle_ad_view_category(user_id, text):
    if text.startswith("📌"):
        category = text[2:]
        if category in AD_CATEGORIES:
            user_data[user_id] = {'category': category}
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for sub in AD_CATEGORIES[category]:
                keyboard.row(f"🔹 {sub}")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['ads']} یک زیرشاخه انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "ad_view_subcategory"

def handle_ad_view_subcategory(user_id, text):
    if text.startswith("🔹"):
        subcategory = text[2:]
        category = user_data[user_id].get('category', '')
        if subcategory in AD_CATEGORIES.get(category, []):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT ads.*, users.numeric_id FROM ads JOIN users ON ads.user_id = users.user_id WHERE category = ? AND subcategory = ?", (category, subcategory))
            ads = c.fetchall()
            conn.close()
            if ads:
                for ad in ads:
                    display_ad_photos(user_id, ad[9], ad, is_admin=(user_id == ADMIN_ID), numeric_id=ad[10])
                bot.send_message(user_id, "انتخاب کنید:", reply_markup=ad_view_result_keyboard())
                user_states[user_id] = "ad_view_result"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} آگهی‌ای در این دسته وجود ندارد!", reply_markup=ad_view_result_keyboard())
                user_states[user_id] = "ad_view_result"

def handle_ad_search_title(user_id, text):
    if text.strip():
        user_data[user_id] = {'search_title': text}
        bot.send_message(user_id, f"{EMOJIS['search']} حداقل قیمت را به تومان وارد کنید (یا 'رد کردن' برای جستجو بدون قیمت):", reply_markup=skip_button())
        user_states[user_id] = "ad_search_min_price"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} عنوان جستجو نمی‌تواند خالی باشد!")

def handle_ad_search_min_price(user_id, text):
    if text == "رد کردن":
        search_title = user_data[user_id]['search_title']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT ads.*, users.numeric_id FROM ads JOIN users ON ads.user_id = users.user_id WHERE ads.title LIKE ?", (f"%{search_title}%",))
        ads = c.fetchall()
        conn.close()
        if ads:
            for ad in ads:
                display_ad_photos(user_id, ad[9], ad, is_admin=(user_id == ADMIN_ID), numeric_id=ad[10])
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=ad_view_result_keyboard())
            user_states[user_id] = "ad_view_result"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} هیچ آگهی‌ای با این عنوان یافت نشد!", reply_markup=ad_view_result_keyboard())
            user_states[user_id] = "ad_view_result"
    else:
        try:
            min_price = int(text.replace(",", ""))
            if min_price >= 0:
                user_data[user_id]['min_price'] = min_price
                bot.send_message(user_id, f"{EMOJIS['search']} حداکثر قیمت را به تومان وارد کنید:", reply_markup=back_button_only())
                user_states[user_id] = "ad_search_max_price"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} قیمت نمی‌تواند منفی باشد!")
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً فقط عدد وارد کنید!")

def handle_ad_search_max_price(user_id, text):
    try:
        max_price = int(text.replace(",", ""))
        min_price = user_data[user_id]['min_price']
        if max_price >= min_price:
            search_title = user_data[user_id]['search_title']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT ads.*, users.numeric_id FROM ads JOIN users ON ads.user_id = users.user_id WHERE ads.title LIKE ? AND CAST(REPLACE(ads.price, ',', '') AS INTEGER) BETWEEN ? AND ?", (f"%{search_title}%", min_price, max_price))
            ads = c.fetchall()
            conn.close()
            if ads:
                for ad in ads:
                    display_ad_photos(user_id, ad[9], ad, is_admin=(user_id == ADMIN_ID), numeric_id=ad[10])
                bot.send_message(user_id, "انتخاب کنید:", reply_markup=ad_view_result_keyboard())
                user_states[user_id] = "ad_view_result"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} هیچ آگهی‌ای با این عنوان و رنج قیمت یافت نشد!", reply_markup=ad_view_result_keyboard())
                user_states[user_id] = "ad_view_result"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} حداکثر قیمت باید بیشتر یا مساوی حداقل قیمت باشد!")
    except ValueError:
        bot.send_message(user_id, f"{EMOJIS['error']} لطفاً فقط عدد وارد کنید!")

def handle_ad_view_result(user_id, text):
    if text == f"{EMOJIS['search']} جستجو دوباره":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for cat in AD_CATEGORIES:
            keyboard.row(f"📌 {cat}")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        bot.send_message(user_id, f"{EMOJIS['ads']} یک دسته انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "ad_view_category"

def handle_edit_ad_menu(user_id, text):
    if text == f"{EMOJIS['edit']} ویرایش عنوان":
        bot.send_message(user_id, f"{EMOJIS['edit']} عنوان جدید را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "edit_ad_title"
    elif text == f"{EMOJIS['edit']} ویرایش توضیحات":
        bot.send_message(user_id, f"{EMOJIS['edit']} توضیحات جدید را وارد کنید (حداقل 10 کلمه):", reply_markup=back_button_only())
        user_states[user_id] = "edit_ad_description"
    elif text == f"{EMOJIS['edit']} ویرایش قیمت":
        bot.send_message(user_id, f"{EMOJIS['edit']} قیمت جدید را به تومان وارد کنید (فقط عدد):", reply_markup=back_button_only())
        user_states[user_id] = "edit_ad_price"
    elif text == f"{EMOJIS['edit']} ویرایش آدرس":
        bot.send_message(user_id, f"{EMOJIS['edit']} آدرس جدید را وارد کنید (یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
        user_states[user_id] = "edit_ad_address"
    elif text == f"{EMOJIS['edit']} ویرایش تماس":
        bot.send_message(user_id, f"{EMOJIS['edit']} شماره تماس جدید را وارد کنید (شماره باید با 09 شروع شود و 11 رقم باشد):", reply_markup=back_button_only())
        user_states[user_id] = "edit_ad_phone"
    elif text == f"{EMOJIS['edit']} ویرایش عکس":
        user_data[user_id]['photos'] = []
        bot.send_message(user_id, f"{EMOJIS['edit']} یک عکس برای آگهی ارسال کنید (حداکثر ۵ عکس):", reply_markup=photo_management_keyboard(0))
        user_states[user_id] = "edit_ad_photo_collect"

def handle_edit_ad_title(user_id, text):
    if text.strip():
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE ads SET title = ? WHERE ad_id = ? AND user_id = ?", (text, user_data[user_id]['edit_ad_id'], user_id))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} عنوان به‌روزرسانی شد!", reply_markup=get_ad_menu())
        user_states[user_id] = "ad_menu"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} عنوان نمی‌تواند خالی باشد!")

def handle_edit_ad_description(user_id, text):
    words = text.strip().split()
    if len(words) >= 10:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE ads SET description = ? WHERE ad_id = ? AND user_id = ?", (text, user_data[user_id]['edit_ad_id'], user_id))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} توضیحات به‌روزرسانی شد!", reply_markup=get_ad_menu())
        user_states[user_id] = "ad_menu"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} توضیحات باید حداقل 10 کلمه باشد! ({len(words)} کلمه وارد کرده‌اید)")

def handle_edit_ad_price(user_id, text):
    try:
        price = int(text.replace(",", ""))
        if price > 0:
            formatted_price = f"{price:,}"
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE ads SET price = ? WHERE ad_id = ? AND user_id = ?", (formatted_price, user_data[user_id]['edit_ad_id'], user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} قیمت به‌روزرسانی شد!", reply_markup=get_ad_menu())
            user_states[user_id] = "ad_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} قیمت باید بیشتر از صفر باشد!")
    except ValueError:
        bot.send_message(user_id, f"{EMOJIS['error']} لطفاً فقط عدد وارد کنید!")

def handle_edit_ad_address(user_id, text):
    value = None if text == "رد کردن" else text
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE ads SET address = ? WHERE ad_id = ? AND user_id = ?", (value, user_data[user_id]['edit_ad_id'], user_id))
    conn.commit()
    conn.close()
    bot.send_message(user_id, f"{EMOJIS['success']} آدرس به‌روزرسانی شد!", reply_markup=get_ad_menu())
    user_states[user_id] = "ad_menu"

def handle_edit_ad_phone(user_id, text):
    if text.strip():
        if re.match(r'^09\d{9}$', text):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE ads SET phone = ? WHERE ad_id = ? AND user_id = ?", (text, user_data[user_id]['edit_ad_id'], user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} شماره تماس به‌روزرسانی شد!", reply_markup=get_ad_menu())
            user_states[user_id] = "ad_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شماره موبایل باید با 09 شروع شود و 11 رقم باشد!")
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} شماره تماس نمی‌تواند خالی باشد!")

def handle_edit_ad_photo_collect(user_id, text):
    if text == f"{EMOJIS['success']} تأیید":
        if user_data[user_id]['photos']:
            photos = "|".join(user_data[user_id]['photos'])
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE ads SET photo = ? WHERE ad_id = ? AND user_id = ?", (photos, user_data[user_id]['edit_ad_id'], user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} عکس‌های آگهی به‌روزرسانی شدند!", reply_markup=get_ad_menu())
            user_states[user_id] = "ad_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} حداقل یک عکس باید ارسال کنید!", reply_markup=photo_management_keyboard(len(user_data[user_id]['photos'])))
    elif text == f"{EMOJIS['add']} ارسال عکس دیگر":
        bot.send_message(user_id, f"{EMOJIS['ads']} عکس بعدی را ارسال کنید (تا {5 - len(user_data[user_id]['photos'])} عکس دیگر):", reply_markup=photo_management_keyboard(len(user_data[user_id]['photos'])))

def handle_admin_menu(user_id, text):
    if text == "👥 کاربران فعال":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        conn.close()
        msg = f"{EMOJIS['info']} تعداد کل کاربران فعال: {total_users}"
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("👦 نمایش کاربران پسر", "👧 نمایش کاربران دختر")
        keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
        bot.send_message(user_id, msg, reply_markup=keyboard)
        user_states[user_id] = "admin_view_gender"
    elif text == f"{EMOJIS['news']} ارسال خبر":
        bot.send_message(user_id, f"{EMOJIS['news']} متن خبر را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "admin_news_content"
    elif text == "🛡️ مدیر آگهی":
        bot.send_message(user_id, f"{EMOJIS['info']} عنوان آگهی را برای حذف وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "admin_delete_ad_title"
    elif text == "🚫 مسدود کردن کاربر":
        bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر را برای مسدود کردن وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "admin_block_user"
    elif text == "🔓 رفع مسدودیت":
        bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر را برای رفع مسدودیت وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = "admin_unblock_user"

def handle_admin_view_gender(user_id, text):
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
        bot.send_message(user_id, msg, reply_markup=back_home_buttons())
        user_states[user_id] = "admin_users"
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
        bot.send_message(user_id, msg, reply_markup=back_home_buttons())
        user_states[user_id] = "admin_users"

def handle_admin_block_user(user_id, text):
    try:
        target_numeric_id = int(text)
        user_data[user_id] = {'target_numeric_id': target_numeric_id}
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id, name FROM users WHERE numeric_id = ?", (target_numeric_id,))
        user = c.fetchone()
        conn.close()
        
        if user:
            user_data[user_id]['target_user_id'] = user[0]
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("بله", "خیر")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید کاربر {user[1]} را مسدود کنید؟", reply_markup=keyboard)
            user_states[user_id] = "admin_confirm_block"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه یافت نشد!", reply_markup=back_home_buttons())
            user_states[user_id] = "admin_menu"
    except ValueError:
        bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=back_button_only())

def handle_admin_confirm_block(user_id, text):
    if text == "بله":
        target_user_id = user_data[user_id]['target_user_id']
        block_user(target_user_id)
        bot.send_message(user_id, f"{EMOJIS['success']} کاربر مسدود شد!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
        
        # ارسال پیام به کاربر مسدود شده
        try:
            bot.send_message(target_user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.\n\nبرای رفع مسدودیت باید هزینه‌ای اندک بپردازید‼️\nبرای هماهنگی به ایدی ادمین پیام دهید:\n@Sedayegoyom10")
        except:
            pass
            
    elif text == "خیر":
        bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    elif text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"

def handle_admin_unblock_user(user_id, text):
    try:
        target_numeric_id = int(text)
        user_data[user_id] = {'target_numeric_id': target_numeric_id}
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id, name FROM users WHERE numeric_id = ?", (target_numeric_id,))
        user = c.fetchone()
        conn.close()
        
        if user:
            user_data[user_id]['target_user_id'] = user[0]
            
            if is_user_blocked(user[0]):
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("بله", "خیر")
                keyboard.row(f"{EMOJIS['back']} برگشت")
                bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید کاربر {user[1]} را از مسدودیت خارج کنید؟", reply_markup=keyboard)
                user_states[user_id] = "admin_confirm_unblock"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} این کاربر مسدود نیست!", reply_markup=back_home_buttons())
                user_states[user_id] = "admin_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه یافت نشد!", reply_markup=back_home_buttons())
            user_states[user_id] = "admin_menu"
    except ValueError:
        bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=back_button_only())

def handle_admin_confirm_unblock(user_id, text):
    if text == "بله":
        target_user_id = user_data[user_id]['target_user_id']
        unblock_user(target_user_id)
        bot.send_message(user_id, f"{EMOJIS['success']} کاربر از مسدودیت خارج شد!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
        
        # ارسال پیام به کاربر رفع مسدود شده
        try:
            bot.send_message(target_user_id, f"{EMOJIS['success']} شما رفع مسدود شدید و دیگر میتوانید از قابلیت‌های ربات استفاده کنید🔥")
        except:
            pass
            
    elif text == "خیر":
        bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    elif text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"

def handle_admin_news_content(user_id, text):
    if text.strip():
        user_data[user_id] = {'news_content': text}
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("بله", "خیر")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این خبر را ارسال کنید؟\n\n{text}", reply_markup=keyboard)
        user_states[user_id] = "admin_news_confirm"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} متن خبر نمی‌تواند خالی باشد!")

def handle_admin_news_confirm(user_id, text):
    if text == "بله":
        news_content = user_data[user_id]['news_content']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO news (content) VALUES (?)", (news_content,))
        c.execute("SELECT user_id FROM users WHERE is_blocked = 0")
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
        keyboard.row(f"{EMOJIS['delete']} حذف خبر", f"{EMOJIS['back']} برگشت")
        msg = f"{EMOJIS['success']} خبر با موفقیت به {success_count} کاربر ارسال شد!"
        bot.send_message(user_id, msg, reply_markup=keyboard)
        user_states[user_id] = "admin_news_sent"
    elif text == "خیر":
        bot.send_message(user_id, f"{EMOJIS['info']} ارسال خبر لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    elif text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"

def handle_admin_news_sent(user_id, text):
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

def handle_admin_delete_ad_title(user_id, text):
    if text.strip():
        user_data[user_id] = {'delete_ad_title': text}
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for cat in AD_CATEGORIES:
            keyboard.row(f"📌 {cat}")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        bot.send_message(user_id, f"{EMOJIS['ads']} دسته آگهی را انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "admin_delete_ad_category"
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} عنوان آگهی نمی‌تواند خالی باشد!")

def handle_admin_delete_ad_category(user_id, text):
    if text.startswith("📌"):
        category = text[2:]
        if category in AD_CATEGORIES:
            user_data[user_id]['delete_ad_category'] = category
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for sub in AD_CATEGORIES[category]:
                keyboard.row(f"🔹 {sub}")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['ads']} زیردسته آگهی را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "admin_delete_ad_subcategory"

def handle_admin_delete_ad_subcategory(user_id, text):
    if text.startswith("🔹"):
        subcategory = text[2:]
        category = user_data[user_id].get('delete_ad_category', '')
        if subcategory in AD_CATEGORIES.get(category, []):
            user_data[user_id]['delete_ad_subcategory'] = subcategory
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر مالک آگهی را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "admin_delete_ad_user_id"

def handle_admin_delete_ad_user_id(user_id, text):
    try:
        numeric_id = int(text)
        user_data[user_id]['delete_ad_numeric_id'] = numeric_id
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE numeric_id = ?", (numeric_id,))
        user_result = c.fetchone()
        
        if user_result:
            user_db_id = user_result[0]
            title = user_data[user_id]['delete_ad_title']
            category = user_data[user_id]['delete_ad_category']
            subcategory = user_data[user_id]['delete_ad_subcategory']
            
            c.execute("SELECT ad_id FROM ads WHERE user_id = ? AND title = ? AND category = ? AND subcategory = ?", (user_db_id, title, category, subcategory))
            ad_result = c.fetchone()
            
            if ad_result:
                user_data[user_id]['delete_ad_id'] = ad_result[0]
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("بله", "خیر")
                keyboard.row(f"{EMOJIS['back']} برگشت")
                bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این آگهی را حذف کنید؟\nعنوان: {title}", reply_markup=keyboard)
                user_states[user_id] = "admin_delete_ad_confirm"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} آگهی با این مشخصات یافت نشد!", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه عددی یافت نشد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        conn.close()
    except ValueError:
        bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=back_button_only())

def handle_admin_delete_ad_confirm(user_id, text):
    if text == "بله":
        ad_id = user_data[user_id]['delete_ad_id']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM ads WHERE ad_id = ?", (ad_id,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} آگهی با موفقیت حذف شد!", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    elif text == "خیر":
        bot.send_message(user_id, f"{EMOJIS['info']} حذف آگهی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"
    elif text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
        user_states[user_id] = "admin_menu"

def handle_ad_my_ads(user_id, text):
    # فقط برای مدیریت پیام‌های متنی در این حالت
    pass

def handle_admin_users(user_id, text):
    # فقط برای مدیریت پیام‌های متنی در این حالت
    pass

# مدیریت عکس‌ها
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    # بررسی مسدودیت کاربر
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.\n\nبرای رفع مسدودیت باید هزینه‌ای اندک بپردازید‼️\nبرای هماهنگی به ایدی ادمین پیام دهید:\n@Sedayegoyom10")
        return
    
    state = user_states.get(user_id, "")
    
    if state == "ad_add_photo_collect":
        if len(user_data[user_id]['photos']) < 5:
            user_data[user_id]['photos'].append(message.photo[-1].file_id)
            bot.send_message(user_id, f"{EMOJIS['success']} عکس دریافت شد ({len(user_data[user_id]['photos'])}/۵).", reply_markup=photo_management_keyboard(len(user_data[user_id]['photos'])))
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شما به حداکثر تعداد عکس (۵) رسیده‌اید!", reply_markup=photo_management_keyboard(5))
    elif state == "edit_ad_photo_collect":
        if len(user_data[user_id]['photos']) < 5:
            user_data[user_id]['photos'].append(message.photo[-1].file_id)
            bot.send_message(user_id, f"{EMOJIS['success']} عکس دریافت شد ({len(user_data[user_id]['photos'])}/۵).", reply_markup=photo_management_keyboard(len(user_data[user_id]['photos'])))
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شما به حداکثر تعداد عکس (۵) رسیده‌اید!", reply_markup=photo_management_keyboard(5))

# مدیریت دکمه‌های اینلاین
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    # بررسی مسدودیت کاربر
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما مسدود شده‌اید! به دلیل تخلف از قوانین ربات.\n\nبرای رفع مسدودیت باید هزینه‌ای اندک بپردازید‼️\nبرای هماهنگی به ایدی ادمین پیام دهید:\n@Sedayegoyom10")
        return
    
    data = call.data
    
    if data.startswith("delete_ad_"):
        ad_id = int(data.split("_")[2])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id FROM ads WHERE ad_id = ?", (ad_id,))
        ad = c.fetchone()
        if ad and ad[0] == user_id:
            c.execute("DELETE FROM ads WHERE ad_id = ?", (ad_id,))
            conn.commit()
            bot.send_message(user_id, f"{EMOJIS['success']} آگهی حذف شد!", reply_markup=get_ad_menu())
            user_states[user_id] = "ad_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شما مجاز به حذف این آگهی نیستید!")
        conn.close()
    elif data.startswith("edit_ad_"):
        ad_id = int(data.split("_")[2])
        user_data[user_id] = {'edit_ad_id': ad_id}
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM ads WHERE ad_id = ? AND user_id = ?", (ad_id, user_id))
        ad = c.fetchone()
        conn.close()
        if ad:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row(f"{EMOJIS['edit']} ویرایش عنوان", f"{EMOJIS['edit']} ویرایش توضیحات")
            keyboard.row(f"{EMOJIS['edit']} ویرایش قیمت", f"{EMOJIS['edit']} ویرایش آدرس")
            keyboard.row(f"{EMOJIS['edit']} ویرایش تماس")
            keyboard.row(f"{EMOJIS['edit']} ویرایش عکس")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            msg = f"{EMOJIS['edit']} کدام بخش را می‌خواهید ویرایش کنید؟"
            bot.send_message(user_id, msg, reply_markup=keyboard)
            user_states[user_id] = "edit_ad_menu"

# تنظیم Webhook
def set_webhook():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=WEBHOOK_URL)

# اجرای سرور
if __name__ == '__main__':
    set_webhook()
    app.run(host='0.0.0.0', port=PORT)