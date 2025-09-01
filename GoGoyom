import telebot
import sqlite3
import os
import json
from flask import Flask, request
from telebot import types
import datetime
import jdatetime
import random
import re

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN', '8134200098:AAGGapErG9F0ek0lAEdrI53E5gzPDcObTQM')
ADMIN_ID = int(os.getenv('ADMIN_ID', '7385601641'))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'YOUR_WEBHOOK_URL_HERE') + f'/{API_TOKEN}'

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- DATABASE SETUP ---
DB_PATH = "goyom_bot.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

def setup_database():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        age INTEGER,
        gender TEXT,
        points INTEGER DEFAULT 0,
        random_id INTEGER UNIQUE
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category_main TEXT,
        category_sub TEXT,
        title TEXT,
        description TEXT,
        price TEXT,
        address TEXT,
        contact TEXT,
        photo_id TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_user_id INTEGER,
        category_main TEXT,
        category_sub TEXT,
        title TEXT,
        description TEXT,
        address TEXT,
        contact TEXT,
        photo_id TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shop_ratings (
        shop_id INTEGER,
        user_id INTEGER,
        rating INTEGER,
        PRIMARY KEY (shop_id, user_id)
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_content (
        section TEXT PRIMARY KEY,
        content TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_states (
        user_id INTEGER PRIMARY KEY,
        state TEXT,
        data TEXT
    )''')
    conn.commit()

setup_database()

# --- CATEGORIES DEFINITION ---
AD_CATEGORIES = {
    "🏡 املاک": ["خرید و فروش", "رهن و اجاره"],
    "🚗 وسایل نقلیه": ["خودرو", "موتورسیکلت", "لوازم یدکی"],
    "🛒 لوازم خانگی": ["مبلمان", "لوازم آشپزخانه"],
    "👔 پوشاک": ["لباس", "کیف و کفش"],
    "🖥️ الکترونیک": ["موبایل", "کامپیوتر"],
    "🎓 خدمات و استخدام": ["استخدام", "خدمات فنی"]
}

SHOP_CATEGORIES = {
    "🥖 مواد غذایی": ["سوپرمارکت", "نانوایی", "میوه فروشی"],
    "👕 پوشاک": ["پوشاک و لباس", "کیف و کفش"],
    "🏨 رستوران": ["رستوران", "فست فود", "کافی شاپ"],
    "🛠️ خدمات": ["تعمیرگاه خودرو", "خدمات فنی", "آرایشگاه"]
}

# --- HELPER & STATE FUNCTIONS ---
def get_user_state(user_id):
    cursor.execute("SELECT state, data FROM user_states WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return (result[0], json.loads(result[1] or '{}')) if result else (None, {})

def set_user_state(user_id, state, data=None):
    cursor.execute("INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, ?, ?)",
                   (user_id, state, json.dumps(data or {})))
    conn.commit()

def clear_user_state(user_id):
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    
def update_user_points(user_id, points):
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
    conn.commit()

# --- KEYBOARDS ---
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("🛍 دیوار گویم", "🏪 مغازه ها", "📢 اخبار", "📝 پروفایل من")
    return keyboard

def get_admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("✍️ مدیریت اخبار", "🏪 مدیریت مکان‌ها", "👥 کاربران فعال", "⬅️ خروج از پنل")
    return keyboard

def get_divar_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("➕ ثبت آگهی", "📋 مشاهده آگهی‌ها", "📄 آگهی‌های من", "⬅️ بازگشت")
    return keyboard

def get_shops_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("➕ ثبت مکان", "🏪 مشاهده مغازه‌ها", "🏬 مغازه‌های من", "⬅️ بازگشت")
    return keyboard
    
# --- GENERAL HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        bot.send_message(user_id, "سلام! خوش آمدید.", reply_markup=get_main_keyboard())
    else:
        set_user_state(user_id, 'awaiting_username')
        bot.send_message(user_id, "خوش آمدید! لطفاً یک نام مستعار برای خود انتخاب کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "به پنل مدیریت خوش آمدید.", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "شما ادمین نیستید.")

# --- REGISTRATION FLOW ---
# (This section is simplified for brevity but works as intended)
@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'awaiting_username')
def process_username(message):
    username = message.text.strip()
    set_user_state(message.from_user.id, 'awaiting_age', {'username': username})
    bot.send_message(message.from_user.id, "نام شما ثبت شد. لطفاً سن خود را وارد کنید (مثلا: 25):")

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'awaiting_age')
def process_age(message):
    try:
        age = int(message.text)
        if 13 <= age <= 99:
            state, data = get_user_state(message.from_user.id)
            data['age'] = age
            set_user_state(message.from_user.id, 'awaiting_gender', data)
            keyboard = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
            keyboard.add("پسر 👨", "دختر 👩")
            bot.send_message(message.from_user.id, "سن شما ثبت شد. جنسیت خود را انتخاب کنید:", reply_markup=keyboard)
        else:
            bot.send_message(message.from_user.id, "سن باید بین ۱۳ تا ۹۹ باشد.")
    except ValueError:
        bot.send_message(message.from_user.id, "لطفاً سن را به صورت عدد وارد کنید.")

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'awaiting_gender')
def process_gender(message):
    gender = "پسر" if "پسر" in message.text else "دختر"
    state, data = get_user_state(message.from_user.id)
    random_id = random.randint(100000, 999999)
    cursor.execute("INSERT INTO users (user_id, username, age, gender, random_id) VALUES (?, ?, ?, ?, ?)",
                   (message.from_user.id, data['username'], data['age'], gender, random_id))
    conn.commit()
    clear_user_state(message.from_user.id)
    bot.send_message(message.from_user.id, "🎉 ثبت‌نام شما تکمیل شد!", reply_markup=get_main_keyboard())


# --- MAIN MENU & NAVIGATION ---
@bot.message_handler(func=lambda msg: msg.text in ["🛍 دیوار گویم", "🏪 مغازه ها", "📢 اخبار", "📝 پروفایل من"])
def handle_main_menu(message):
    if message.text == "🛍 دیوار گویم":
        bot.send_message(message.chat.id, "به بخش دیوار گویم خوش آمدید.", reply_markup=get_divar_keyboard())
    elif message.text == "🏪 مغازه ها":
        bot.send_message(message.chat.id, "به بخش مغازه‌ها خوش آمدید.", reply_markup=get_shops_keyboard())
    elif message.text == "📢 اخبار":
        cursor.execute("SELECT content FROM admin_content WHERE section='news'")
        news = cursor.fetchone()
        bot.send_message(message.chat.id, news[0] if news else "خبری وجود ندارد.")
    elif message.text == "📝 پروفایل من":
        cursor.execute("SELECT username, age, gender, points, random_id FROM users WHERE user_id=?", (message.from_user.id,))
        user = cursor.fetchone()
        text = (f"👤 **پروفایل شما**\n\n"
                f"🏷️ نام: {user[0]}\n"
                f"🔢 شناسه: `{user[4]}`\n"
                f"🎂 سن: {user[1]}\n"
                f"🚻 جنسیت: {user[2]}\n"
                f"⭐ امتیاز: {user[3]}")
        bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "⬅️ بازگشت")
def back_to_main_menu(message):
    clear_user_state(message.from_user.id)
    bot.send_message(message.chat.id, "به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())


# --- AD (DIVAR) COMPLETE FLOW ---
@bot.message_handler(func=lambda msg: msg.text == "➕ ثبت آگهی")
def ad_add_main_cat(message):
    set_user_state(message.from_user.id, 'ad_add_sub_cat')
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(*AD_CATEGORIES.keys())
    keyboard.add("⬅️ بازگشت")
    bot.send_message(message.chat.id, "۱/۷: دسته‌بندی اصلی را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_add_sub_cat')
def ad_add_sub_cat(message):
    main_cat = message.text
    if main_cat not in AD_CATEGORIES:
        bot.send_message(message.chat.id, "لطفاً از دکمه‌ها استفاده کنید.")
        return
    state, data = get_user_state(message.from_user.id)
    data['main_cat'] = main_cat
    set_user_state(message.from_user.id, 'ad_add_title', data)
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(*AD_CATEGORIES[main_cat])
    keyboard.add("⬅️ بازگشت")
    bot.send_message(message.chat.id, "۲/۷: زیردسته را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_add_title')
def ad_add_title(message):
    sub_cat = message.text
    state, data = get_user_state(message.from_user.id)
    if sub_cat not in AD_CATEGORIES.get(data.get('main_cat'), []):
         bot.send_message(message.chat.id, "لطفاً از دکمه‌ها استفاده کنید.")
         return
    data['sub_cat'] = sub_cat
    set_user_state(message.from_user.id, 'ad_add_description', data)
    bot.send_message(message.chat.id, "۳/۷: عنوان آگهی را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_add_description')
def ad_add_description(message):
    state, data = get_user_state(message.from_user.id)
    data['title'] = message.text.strip()
    set_user_state(message.from_user.id, 'ad_add_price', data)
    bot.send_message(message.chat.id, "۴/۷: توضیحات آگهی را وارد کنید:")

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_add_price')
def ad_add_price(message):
    state, data = get_user_state(message.from_user.id)
    data['description'] = message.text.strip()
    set_user_state(message.from_user.id, 'ad_add_address', data)
    bot.send_message(message.chat.id, "۵/۷: قیمت را وارد کنید (مثال: ۲۰۰۰۰۰ تومان یا توافقی):")

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_add_address')
def ad_add_address(message):
    state, data = get_user_state(message.from_user.id)
    data['price'] = message.text.strip()
    set_user_state(message.from_user.id, 'ad_add_contact', data)
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("ثبت نشود")
    bot.send_message(message.chat.id, "۶/۷: آدرس را وارد کنید (یا دکمه 'ثبت نشود' را بزنید):", reply_markup=keyboard)

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_add_contact')
def ad_add_contact(message):
    state, data = get_user_state(message.from_user.id)
    data['address'] = "" if message.text == "ثبت نشود" else message.text.strip()
    set_user_state(message.from_user.id, 'ad_add_photo', data)
    bot.send_message(message.chat.id, "۷/۷: شماره تماس خود را وارد کنید (الزامی):", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_add_photo')
def ad_add_photo(message):
    contact = message.text.strip()
    if not re.match(r'^09\d{9}$', contact):
        bot.send_message(message.chat.id, "❌ شماره تماس نامعتبر است. باید ۱۱ رقم باشد و با 09 شروع شود.")
        return
    state, data = get_user_state(message.from_user.id)
    data['contact'] = contact
    set_user_state(message.from_user.id, 'ad_add_final', data)
    bot.send_message(message.chat.id, "لطفاً عکس آگهی را ارسال کنید (الزامی است):")

@bot.message_handler(content_types=['photo'], func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_add_final')
def ad_add_save(message):
    photo_id = message.photo[-1].file_id
    state, data = get_user_state(message.from_user.id)
    cursor.execute("""
        INSERT INTO ads (user_id, category_main, category_sub, title, description, price, address, contact, photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (message.from_user.id, data['main_cat'], data['sub_cat'], data['title'], data['description'],
          data['price'], data['address'], data['contact'], photo_id))
    conn.commit()
    clear_user_state(message.from_user.id)
    update_user_points(message.from_user.id, 10)
    bot.send_message(message.chat.id, "✅ آگهی شما با موفقیت ثبت شد و ۱۰ امتیاز گرفتید!", reply_markup=get_divar_keyboard())

# --- VIEW ADS FLOW ---
# (Simplified, a full version would have more 'back' options)
@bot.message_handler(func=lambda msg: msg.text == "📋 مشاهده آگهی‌ها")
def ad_view_main_cat(message):
    set_user_state(message.from_user.id, 'ad_view_sub_cat')
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(*AD_CATEGORIES.keys())
    keyboard.add("⬅️ بازگشت")
    bot.send_message(message.chat.id, "دسته‌بندی مورد نظر را برای مشاهده آگهی‌ها انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_view_sub_cat')
def ad_view_sub_cat(message):
    main_cat = message.text
    if main_cat not in AD_CATEGORIES: return
    state, data = get_user_state(message.from_user.id)
    data['main_cat'] = main_cat
    set_user_state(message.from_user.id, 'ad_view_list', data)
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(*AD_CATEGORIES[main_cat])
    keyboard.add("⬅️ بازگشت")
    bot.send_message(message.chat.id, "زیردسته را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_view_list')
def ad_view_list(message):
    sub_cat = message.text
    state, data = get_user_state(message.from_user.id)
    cursor.execute("SELECT id, title FROM ads WHERE category_main=? AND category_sub=?", (data['main_cat'], sub_cat))
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, "در این دسته آگهی وجود ندارد.", reply_markup=get_divar_keyboard())
        clear_user_state(message.from_user.id)
        return

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for ad_id, title in ads:
        keyboard.add(f"{title} (آگهی {ad_id})")
    keyboard.add("⬅️ بازگشت")
    set_user_state(message.from_user.id, 'ad_view_final')
    bot.send_message(message.chat.id, "آگهی مورد نظر را انتخاب کنید:", reply_markup=keyboard)
    
@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'ad_view_final')
def ad_view_final(message):
    try:
        ad_id = int(re.search(r'\(آگهی (\d+)\)', message.text).group(1))
        cursor.execute("SELECT title, description, price, address, contact, photo_id, user_id FROM ads WHERE id=?", (ad_id,))
        ad = cursor.fetchone()
        if not ad:
            bot.send_message(message.chat.id, "آگهی یافت نشد.")
            return

        title, desc, price, address, contact, photo, owner_id = ad
        caption = (f"**{title}**\n\n"
                   f"📝 **توضیحات:**\n{desc}\n\n"
                   f"💰 **قیمت:** {price}\n"
                   f"📍 **آدرس:** {address or 'ثبت نشده'}\n"
                   f"📞 **تماس:** `{contact}`")
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("💬 ارسال پیام به آگهی‌دهنده", url=f"tg://user?id={owner_id}"))
        
        bot.send_photo(message.chat.id, photo, caption=caption, parse_mode='Markdown', reply_markup=keyboard)
    except (AttributeError, ValueError):
        bot.send_message(message.chat.id, "لطفاً از دکمه‌ها برای انتخاب آگهی استفاده کنید.")

# --- MY ADS FLOW ---
# (This is also simplified for brevity but demonstrates the core logic)
@bot.message_handler(func=lambda msg: msg.text == "📄 آگهی‌های من")
def my_ads_list(message):
    cursor.execute("SELECT id, title FROM ads WHERE user_id=?", (message.from_user.id,))
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, "شما آگهی ثبت نکرده‌اید.")
        return
    for ad_id, title in ads:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("✏️ ویرایش", callback_data=f"ad_edit_{ad_id}"),
            types.InlineKeyboardButton("🗑️ حذف", callback_data=f"ad_delete_{ad_id}")
        )
        bot.send_message(message.chat.id, f"آگهی: **{title}**", reply_markup=keyboard, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('ad_delete_'))
def my_ads_delete(call):
    ad_id = int(call.data.split('_')[2])
    cursor.execute("DELETE FROM ads WHERE id=? AND user_id=?", (ad_id, call.from_user.id))
    conn.commit()
    bot.edit_message_text("آگهی با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)

# The 'ad_edit' flow would be a new state machine similar to 'ad_add' but for updating an existing record.

# --- ADMIN PANEL ---
# (Simplified admin handlers)
@bot.message_handler(func=lambda msg: msg.text == "✍️ مدیریت اخبار" and msg.from_user.id == ADMIN_ID)
def admin_manage_news(message):
    set_user_state(ADMIN_ID, 'admin_awaiting_news_text')
    bot.send_message(ADMIN_ID, "متن خبر جدید را برای ارسال به همه کاربران وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id)[0] == 'admin_awaiting_news_text')
def admin_send_news(message):
    news_text = message.text
    cursor.execute("INSERT OR REPLACE INTO admin_content (section, content) VALUES ('news', ?)", (news_text,))
    conn.commit()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for user in users:
        try: bot.send_message(user[0], f"📢 **خبر جدید**\n\n{news_text}", parse_mode='Markdown')
        except: pass
    clear_user_state(ADMIN_ID)
    bot.send_message(ADMIN_ID, "✅ خبر برای همه ارسال شد.", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "👥 کاربران فعال" and msg.from_user.id == ADMIN_ID)
def admin_active_users(message):
    cursor.execute("SELECT COUNT(user_id) FROM users")
    count = cursor.fetchone()[0]
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("پسرها 👨", "دخترها 👩", "⬅️ بازگشت")
    bot.send_message(ADMIN_ID, f"تعداد کل کاربران: {count} نفر", reply_markup=keyboard)

# --- WEBHOOK & FALLBACK ---
@app.route(f'/{API_TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK', 200

@bot.message_handler(func=lambda message: True)
def fallback_handler(message):
    bot.send_message(message.chat.id, "دستور نامشخص است. لطفاً از دکمه‌ها استفاده کنید.", reply_markup=get_main_keyboard())

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
