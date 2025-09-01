import telebot
import sqlite3
import os
import json
from flask import Flask, request
from telebot import types
import datetime
import jdatetime
from persian import convert_fa_numbers
import random

# Flask app setup
app = Flask(__name__)
# Bot Token and Admin User ID from environment variables
API_TOKEN = os.getenv('API_TOKEN', '8134200098:AAGGapErG9F0ek0lAEdrI53E5gzPDcObTQM')
ADMIN_ID = int(os.getenv('ADMIN_ID', '7385601641'))
WEBHOOK_URL = os.getenv('WEBHOOK_URL') + f'/{API_TOKEN}'
bot = telebot.TeleBot(API_TOKEN)

# Ensure data directory exists
os.makedirs("data", exist_ok=True)
DB_PATH = "data/goyom_bot.db"

# Connect to SQLite database
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    age INTEGER,
    gender TEXT,
    points INTEGER DEFAULT 0,
    random_id INTEGER UNIQUE,
    last_active DATE
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS ads(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    description TEXT,
    category_main TEXT,
    category_sub TEXT,
    photo_id TEXT,
    contact TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS shops(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    address TEXT,
    category TEXT,
    photo_id TEXT,
    contact TEXT,
    admin_id INTEGER,
    seller_username TEXT,
    seller_age INTEGER,
    seller_gender TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS shop_ratings(
    shop_id INTEGER,
    user_id INTEGER,
    rating INTEGER,
    PRIMARY KEY (shop_id, user_id)
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS admin_content(
    section TEXT PRIMARY KEY,
    content TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS jokes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    joke_text TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS user_states(
    user_id INTEGER PRIMARY KEY,
    state TEXT,
    data TEXT
)''')
conn.commit()

# Category Structure for Ads
ad_categories = {
    "🏡 املاک": ["🏢 خرید و فروش آپارتمان", "🏠 خرید و فروش خانه و ویلا", "🛖 زمین و کلنگی", "📦 اجاره مسکونی"],
    "🚗 وسایل نقلیه": ["🚘 خرید و فروش خودرو", "🛵 موتور سیکلت", "🚌 خودروهای سنگین"],
    "📱 کالای دیجیتال": ["📱 موبایل", "💻 لپ‌تاپ و کامپیوتر", "🎧 لوازم جانبی"],
    "👔 خدمات و کسب‌وکار": ["🛠 خدمات فنی", "🎨 آموزش", "🍴 خدمات غذایی"],
    "👕 وسایل شخصی": ["👗 پوشاک", "⌚ ساعت و اکسسوری", "🍼 لوازم کودک"],
    "🛋 خانه و آشپزخانه": ["🛏 وسایل خانه", "🍳 وسایل آشپزخانه", "🪑 مبلمان"],
    "🐾 حیوانات": ["🐶 سگ", "🐱 گربه", "🐠 حیوانات دیگر"],
    "🎉 سرگرمی و اجتماعی": ["🎮 بازی و کنسول", "🎤 بلیط و رویداد", "📚 کتاب و مجله"],
    "👷 استخدام و کاریابی": ["🧑‍💼 اداری", "👨‍🍳 خدماتی", "👨‍🔧 فنی و مهندسی"]
}

# Helper Functions
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    items = [
        types.KeyboardButton("📢 اخبار گویم"),
        types.KeyboardButton("🌦 روز هفته و تاریخ"),
        types.KeyboardButton("🛍 دیوار گویم (آگهی)"),
        types.KeyboardButton("🎉 سرگرمی و مسابقه"),
        types.KeyboardButton("😂 طنز و خاطرات"),
        types.KeyboardButton("⚽ ورزش و رویدادها"),
        types.KeyboardButton("🗳 نظرسنجی"),
        types.KeyboardButton("📞 خدمات و شماره‌های مهم"),
        types.KeyboardButton("📝 پروفایل من"),
        types.KeyboardButton("🏪 مغازه ها")
    ]
    keyboard.add(*items)
    return keyboard

def get_admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    items = [
        types.KeyboardButton("✍️ مدیریت اخبار"),
        types.KeyboardButton("📝 مدیریت ورزش"),
        types.KeyboardButton("📞 مدیریت خدمات"),
        types.KeyboardButton("🎉 مدیریت مسابقات"),
        types.KeyboardButton("🗳 مدیریت نظرسنجی"),
        types.KeyboardButton("🏪 مدیریت مکان‌ها"),
        types.KeyboardButton("👥 کاربران فعال"),
        types.KeyboardButton("⬅️ خروج از پنل ادمین")
    ]
    keyboard.add(*items)
    return keyboard

def get_admin_sub_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.add("⬅️ بازگشت به پنل مدیریت")
    return keyboard

def get_profile_edit_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("تغییر اسم", "تغییر سن", "تغییر جنسیت")
    keyboard.add("بازگشت به منو اصلی")
    return keyboard

def get_user_data(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def update_user_points(user_id, points_to_add=1):
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points_to_add, user_id))
    conn.commit()

def give_daily_bonus(user_id):
    today = datetime.date.today()
    cursor.execute("SELECT last_active FROM users WHERE user_id = ?", (user_id,))
    last_active = cursor.fetchone()
    if not last_active or not last_active[0] or last_active[0] != str(today):
        update_user_points(user_id, 5)
        cursor.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (str(today), user_id))
        conn.commit()

def notify_all_users(section):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    message_text = f"به بخش '{section}' موضوع جدیدی اضافه شد. برای بررسی بر روی دکمه بخش کلیک کنید."
    for user in users:
        try:
            bot.send_message(user[0], message_text, reply_markup=get_main_keyboard())
        except:
            pass

def set_user_state(user_id, state, data=None):
    cursor.execute("INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, ?, ?)",
                   (user_id, state, json.dumps(data) if data else None))
    conn.commit()

def get_user_state(user_id):
    cursor.execute("SELECT state, data FROM user_states WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        state, data = result
        return state, json.loads(data) if data else None
    return None, None

# General Handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        bot.send_message(user_id, "سلام! شما قبلاً ثبت‌نام کرده‌اید.", reply_markup=get_main_keyboard())
        give_daily_bonus(user_id)
    else:
        set_user_state(user_id, 'awaiting_username')
        bot.send_message(user_id, "خوش آمدید به ربات 'مگا گویم'!\nلطفاً اسم مستعار خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['admin'])
def send_admin_panel(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        bot.send_message(user_id, "به پنل مدیریت خوش آمدید.", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(user_id, "شما دسترسی به این بخش ندارید.")

@bot.message_handler(func=lambda message: message.text == "⬅️ خروج از پنل ادمین" and message.from_user.id == ADMIN_ID)
def return_to_main_menu(message):
    bot.send_message(message.from_user.id, "به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "⬅️ بازگشت به پنل مدیریت" and message.from_user.id == ADMIN_ID)
def return_to_admin_panel(message):
    bot.send_message(message.from_user.id, "به پنل مدیریت بازگشتید.", reply_markup=get_admin_keyboard())

# Registration Handlers
@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_username')
def get_username(message):
    user_id = message.from_user.id
    username = message.text.strip()
    if not username:
        bot.send_message(user_id, "لطفاً نام معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_age', {'reg_username': username})
    bot.send_message(user_id, "لطفاً سن خود را وارد کنید (13-70):", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_age')
def get_age(message):
    user_id = message.from_user.id
    try:
        age = int(message.text)
        if 13 <= age <= 70:
            state, data = get_user_state(user_id)
            data['reg_age'] = age
            set_user_state(user_id, 'awaiting_gender', data)
            keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
            keyboard.add("پسر", "دختر")
            bot.send_message(user_id, "لطفاً جنسیت خود را انتخاب کنید:", reply_markup=keyboard)
        else:
            bot.send_message(user_id, "سن باید بین 13 تا 70 باشد:")
    except ValueError:
        bot.send_message(user_id, "لطفاً عدد وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_gender')
def get_gender(message):
    user_id = message.from_user.id
    gender = message.text
    if gender in ["پسر", "دختر"]:
        state, data = get_user_state(user_id)
        username = data['reg_username']
        age = data['reg_age']
        rand_id = random.randint(100000, 999999)
        cursor.execute("INSERT INTO users (user_id, username, age, gender, random_id, last_active) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, username, age, gender, rand_id, str(datetime.date.today())))
        conn.commit()
        cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        conn.commit()
        bot.send_message(user_id, "ثبت‌نام با موفقیت انجام شد!", reply_markup=get_main_keyboard())
        update_user_points(user_id, 5)
    else:
        bot.send_message(user_id, "لطفاً 'پسر' یا 'دختر' را انتخاب کنید:", reply_markup=types.ReplyKeyboardMarkup(row_width=2).add("پسر", "دختر"))

# Main Menu Handlers
@bot.message_handler(func=lambda message: message.text in [
    "📢 اخبار گویم", "🌦 روز هفته و تاریخ", "🛍 دیوار گویم (آگهی)", "🎉 سرگرمی و مسابقه",
    "😂 طنز و خاطرات", "⚽ ورزش و رویدادها", "🗳 نظرسنجی", "📞 خدمات و شماره‌های مهم",
    "📝 پروفایل من", "🏪 مغازه ها"
])
def handle_main_menu(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        send_welcome(message)
        return
    give_daily_bonus(user_id)
    if message.text == "📢 اخبار گویم":
        show_admin_content(user_id, "اخبار")
    elif message.text == "🌦 روز هفته و تاریخ":
        today = jdatetime.date.today()
        bot.send_message(user_id, f"امروز: {today.strftime('%A %d %B %Y')}", reply_markup=get_main_keyboard())
    elif message.text == "🛍 دیوار گویم (آگهی)":
        handle_divar(message)
    elif message.text == "🎉 سرگرمی و مسابقه":
        show_admin_content(user_id, "مسابقات")
    elif message.text == "😂 طنز و خاطرات":
        handle_jokes(message)
    elif message.text == "⚽ ورزش و رویدادها":
        show_admin_content(user_id, "ورزش")
    elif message.text == "🗳 نظرسنجی":
        show_admin_content(user_id, "نظرسنجی")
    elif message.text == "📞 خدمات و شماره‌های مهم":
        show_admin_content(user_id, "خدمات")
    elif message.text == "📝 پروفایل من":
        show_profile(message)
    elif message.text == "🏪 مغازه ها":
        show_shop_categories(message)

# Admin Content Management
def show_admin_content(chat_id, section):
    cursor.execute("SELECT content FROM admin_content WHERE section = ?", (section,))
    content = cursor.fetchone()
    if content:
        bot.send_message(chat_id, content[0], parse_mode='Markdown')
    else:
        bot.send_message(chat_id, f"محتوایی برای '{section}' وجود ندارد.")

def show_admin_content_with_buttons(chat_id, section):
    cursor.execute("SELECT content FROM admin_content WHERE section = ?", (section,))
    content = cursor.fetchone()
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("ویرایش", callback_data=f"edit_admin_content_{section}"))
    keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_admin_content_{section}"))
    if content:
        bot.send_message(chat_id, content[0], reply_markup=keyboard, parse_mode='Markdown')
    else:
        bot.send_message(chat_id, f"محتوایی برای '{section}' وجود ندارد.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["✍️ مدیریت اخبار", "📝 مدیریت ورزش", "📞 مدیریت خدمات", "🎉 مدیریت مسابقات", "🗳 مدیریت نظرسنجی"] and message.from_user.id == ADMIN_ID)
def manage_admin_content_start(message):
    section_map = {
        "✍️ مدیریت اخبار": "اخبار",
        "📝 مدیریت ورزش": "ورزش",
        "📞 مدیریت خدمات": "خدمات",
        "🎉 مدیریت مسابقات": "مسابقات",
        "🗳 مدیریت نظرسنجی": "نظرسنجی"
    }
    section = section_map.get(message.text)
    show_admin_content_with_buttons(message.from_user.id, section)
    set_user_state(message.from_user.id, f'awaiting_admin_content_{section}')
    bot.send_message(message.from_user.id, f"لطفاً متن جدید بخش {section} را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] and get_user_state(message.from_user.id)[0].startswith('awaiting_admin_content_') and message.from_user.id == ADMIN_ID)
def save_admin_content(message):
    user_id = message.from_user.id
    state, _ = get_user_state(user_id)
    section = state.split('_')[3]
    cursor.execute("INSERT OR REPLACE INTO admin_content (section, content) VALUES (?, ?)", (section, message.text))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    notify_all_users(section)
    bot.send_message(ADMIN_ID, f"محتوای بخش {section} به‌روزرسانی شد.", reply_markup=get_admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_admin_content_') and call.from_user.id == ADMIN_ID)
def edit_admin_content_start(call):
    section = call.data.split('_')[3]
    set_user_state(ADMIN_ID, f'awaiting_admin_content_{section}')
    bot.edit_message_text(f"لطفاً متن جدید بخش {section} را وارد کنید:", call.message.chat.id, call.message.message_id, reply_markup=get_admin_sub_menu_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_admin_content_') and call.from_user.id == ADMIN_ID)
def delete_admin_content(call):
    section = call.data.split('_')[3]
    cursor.execute("DELETE FROM admin_content WHERE section = ?", (section,))
    conn.commit()
    try:
        bot.edit_message_text(f"محتوای بخش {section} حذف شد.", call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Error: {e}")
    bot.send_message(ADMIN_ID, "به پنل مدیریت بازگشتید.", reply_markup=get_admin_keyboard())

# Jokes Section
def handle_jokes(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("📜 لیست طنزها", "➕ افزودن طنز")
    keyboard.add("📄 طنزهای من", "بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "به بخش طنز و خاطرات خوش آمدید.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "📜 لیست طنزها")
def show_all_jokes(message):
    cursor.execute("SELECT id, joke_text FROM jokes")
    jokes = cursor.fetchall()
    if jokes:
        for joke in jokes:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("نمایش کامل", callback_data=f"show_joke_{joke[0]}"))
            bot.send_message(message.chat.id, joke[1][:100] + "...", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "هیچ طنزی یافت نشد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "➕ افزودن طنز")
def handle_add_joke(message):
    user_id = message.from_user.id
    set_user_state(user_id, 'awaiting_joke')
    bot.send_message(user_id, "لطفاً متن طنز یا خاطره خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_joke')
def process_add_joke(message):
    user_id = message.from_user.id
    joke_text = message.text.strip()
    if not joke_text:
        bot.send_message(user_id, "لطفاً متن معتبر وارد کنید:")
        return
    cursor.execute("INSERT INTO jokes (user_id, joke_text) VALUES (?, ?)", (user_id, joke_text))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    update_user_points(user_id, 5)
    bot.send_message(user_id, "طنز شما ثبت شد و 5 امتیاز گرفتید!", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📄 طنزهای من")
def show_my_jokes(message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, joke_text FROM jokes WHERE user_id = ?", (user_id,))
    my_jokes = cursor.fetchall()
    if my_jokes:
        for joke in my_jokes:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("ویرایش", callback_data=f"edit_joke_{joke[0]}"))
            keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_joke_{joke[0]}"))
            bot.send_message(user_id, joke[1], reply_markup=keyboard)
    else:
        bot.send_message(user_id, "شما طنزی ثبت نکرده‌اید.", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_joke_"))
def edit_joke_start(call):
    joke_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    set_user_state(user_id, 'awaiting_new_joke', {'edit_joke_id': joke_id})
    bot.send_message(user_id, "لطفاً متن جدید طنز را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_joke')
def process_edit_joke(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    joke_id = data['edit_joke_id']
    new_text = message.text.strip()
    if not new_text:
        bot.send_message(user_id, "لطفاً متن معتبر وارد کنید:")
        return
    cursor.execute("UPDATE jokes SET joke_text = ? WHERE id = ? AND user_id = ?", (new_text, joke_id, user_id))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "طنز شما ویرایش شد.", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_joke_"))
def delete_joke(call):
    joke_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    cursor.execute("DELETE FROM jokes WHERE id = ? AND user_id = ?", (joke_id, user_id))
    conn.commit()
    bot.send_message(user_id, "طنز شما حذف شد.", reply_markup=get_main_keyboard())

# Divar Section
def handle_divar(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("🔎 مشاهده آگهی‌ها", "➕ افزودن آگهی")
    keyboard.add("📄 آگهی‌های من", "بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "به دیوار گویم خوش آمدید.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "🔎 مشاهده آگهی‌ها")
def show_ad_main_categories(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for main_cat in ad_categories.keys():
        keyboard.add(main_cat)
    keyboard.add("بازگشت به منو اصلی")
    set_user_state(message.from_user.id, 'awaiting_ad_main_cat_view')
    bot.send_message(message.chat.id, "دسته‌بندی اصلی را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_main_cat_view' and message.text in ad_categories)
def show_ad_sub_categories_view(message):
    main_cat = message.text
    sub_cats = ad_categories[main_cat]
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for sub_cat in sub_cats:
        keyboard.add(sub_cat)
    keyboard.add("بازگشت به منو اصلی")
    set_user_state(message.from_user.id, f'awaiting_ad_sub_cat_view_{main_cat}')
    bot.send_message(message.chat.id, f"دسته‌بندی '{main_cat}' انتخاب شد.\nزیر دسته را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] and get_user_state(message.from_user.id)[0].startswith('awaiting_ad_sub_cat_view_'))
def show_ads_in_sub_cat(message):
    user_id = message.from_user.id
    state, _ = get_user_state(user_id)
    main_cat = state.split('_')[-1]
    sub_cat = message.text
    if sub_cat == "بازگشت به منو اصلی":
        handle_divar(message)
        return
    cursor.execute("SELECT id, title FROM ads WHERE category_main = ? AND category_sub = ?", (main_cat, sub_cat))
    ads = cursor.fetchall()
    if ads:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        for ad in ads:
            keyboard.add(ad[1])  # دکمه با عنوان آگهی
        keyboard.add("بازگشت به منو اصلی")
        set_user_state(user_id, f'awaiting_ad_selection_{main_cat}_{sub_cat}')
        bot.send_message(user_id, "آگهی را انتخاب کنید:", reply_markup=keyboard)
    else:
        bot.send_message(user_id, "هیچ آگهی‌ای یافت نشد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] and get_user_state(message.from_user.id)[0].startswith('awaiting_ad_selection_'))
def show_selected_ad(message):
    user_id = message.from_user.id
    state, _ = get_user_state(user_id)
    parts = state.split('_')
    main_cat = parts[3]
    sub_cat = parts[4]
    title = message.text
    if title == "بازگشت به منو اصلی":
        handle_divar(message)
        return
    cursor.execute("SELECT * FROM ads WHERE title = ? AND category_main = ? AND category_sub = ?", (title, main_cat, sub_cat))
    ad = cursor.fetchone()
    if ad:
        ad_id, user_id_owner, title, description, category_main, category_sub, photo_id, contact = ad
        response = f"عنوان: {title}\nتوضیحات: {description}\nتماس: {contact}"
        if photo_id:
            bot.send_photo(message.chat.id, photo_id, caption=response)
        else:
            bot.send_message(message.chat.id, response)
        keyboard = types.InlineKeyboardMarkup()
        if user_id == user_id_owner:
            keyboard.add(types.InlineKeyboardButton("ویرایش", callback_data=f"edit_ad_{ad_id}"))
            keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_ad_{ad_id}"))
        bot.send_message(message.chat.id, "گزینه‌ها:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "آگهی یافت نشد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "➕ افزودن آگهی")
def add_ad_main_categories(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for main_cat in ad_categories.keys():
        keyboard.add(main_cat)
    keyboard.add("بازگشت به منو اصلی")
    set_user_state(message.from_user.id, 'awaiting_ad_main_cat_add')
    bot.send_message(message.chat.id, "دسته‌بندی اصلی را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_main_cat_add' and message.text in ad_categories)
def add_ad_sub_categories(message):
    main_cat = message.text
    sub_cats = ad_categories[main_cat]
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for sub_cat in sub_cats:
        keyboard.add(sub_cat)
    keyboard.add("بازگشت به منو اصلی")
    set_user_state(message.from_user.id, f'awaiting_ad_sub_cat_add_{main_cat}')
    bot.send_message(message.chat.id, f"دسته‌بندی '{main_cat}' انتخاب شد.\nزیر دسته را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] and get_user_state(message.from_user.id)[0].startswith('awaiting_ad_sub_cat_add_'))
def get_ad_title_add(message):
    user_id = message.from_user.id
    state, _ = get_user_state(user_id)
    main_cat = state.split('_')[-1]
    sub_cat = message.text
    if sub_cat == "بازگشت به منو اصلی":
        handle_divar(message)
        return
    set_user_state(user_id, 'awaiting_ad_title', {'category_main': main_cat, 'category_sub': sub_cat})
    bot.send_message(user_id, "عنوان آگهی را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_title')
def get_ad_description(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    data['title'] = message.text.strip()
    if not data['title']:
        bot.send_message(user_id, "عنوان معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_ad_description', data)
    bot.send_message(user_id, "توضیحات آگهی را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_description')
def get_ad_contact(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    data['description'] = message.text.strip()
    if not data['description']:
        bot.send_message(user_id, "توضیحات معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_ad_contact', data)
    bot.send_message(user_id, "شماره تماس یا آیدی تلگرام را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_contact')
def get_ad_photo(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    contact = message.text.strip()
    if not contact:
        bot.send_message(user_id, "اطلاعات تماس معتبر وارد کنید:")
        return
    if contact.startswith("09") and len(contact) == 11 and contact.isdigit():
        data['contact'] = contact
    else:
        bot.send_message(user_id, "شماره تماس باید ۱۱ رقم و با 09 شروع شود.")
        return
    set_user_state(user_id, 'awaiting_ad_photo', data)
    bot.send_message(user_id, "عکس آگهی را ارسال کنید (الزامی):")

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_photo')
def process_ad_photo(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    photo_id = message.photo[-1].file_id
    data['photo_id'] = photo_id
    cursor.execute("INSERT INTO ads (user_id, title, description, category_main, category_sub, photo_id, contact) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (user_id, data['title'], data['description'], data['category_main'], data['category_sub'], photo_id, data['contact']))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    update_user_points(user_id, 10)
    bot.send_message(user_id, "آگهی ثبت شد و 10 امتیاز گرفتید!", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_photo' and message.content_types != ['photo'])
def warn_photo_required(message):
    bot.send_message(message.chat.id, "عکس الزامی است. لطفاً یک عکس ارسال کنید.")

@bot.message_handler(func=lambda message: message.text == "📄 آگهی‌های من")
def show_my_ads(message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, title, category_main, category_sub FROM ads WHERE user_id = ?", (user_id,))
    my_ads = cursor.fetchall()
    if my_ads:
        for ad in my_ads:
            ad_id, title, main_cat, sub_cat = ad
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("ویرایش", callback_data=f"edit_ad_{ad_id}"))
            keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_ad_{ad_id}"))
            bot.send_message(user_id, f"عنوان: {title}\nدسته: {main_cat} - {sub_cat}", reply_markup=keyboard)
    else:
        bot.send_message(user_id, "شما آگهی ثبت نکرده‌اید.", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_ad_"))
def edit_ad_start(call):
    ad_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    set_user_state(user_id, 'awaiting_new_ad_title', {'edit_ad_id': ad_id})
    bot.send_message(user_id, "عنوان جدید آگهی را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_ad_title')
def get_new_ad_title(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    ad_id = data['edit_ad_id']
    new_title = message.text.strip()
    if not new_title:
        bot.send_message(user_id, "عنوان معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_new_ad_description', {'title': new_title, 'id': ad_id})
    bot.send_message(user_id, "توضیحات جدید آگهی را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_ad_description')
def get_new_ad_description(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    ad_id = data['id']
    new_title = data['title']
    new_description = message.text.strip()
    if not new_description:
        bot.send_message(user_id, "توضیحات معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_new_ad_contact', {'title': new_title, 'description': new_description, 'id': ad_id})
    bot.send_message(user_id, "شماره تماس جدید را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_ad_contact')
def get_new_ad_contact(message):
    user_id = message.from_user.id
    contact = message.text.strip()
    if not contact or not (contact.startswith("09") and len(contact) == 11 and contact.isdigit()):
        bot.send_message(user_id, "شماره تماس باید ۱۱ رقم و با 09 شروع شود.")
        return
    state, data = get_user_state(user_id)
    ad_id = data['id']
    new_title = data['title']
    new_description = data['description']
    set_user_state(user_id, 'awaiting_new_ad_photo', {'title': new_title, 'description': new_description, 'contact': contact, 'id': ad_id})
    bot.send_message(user_id, "عکس جدید آگهی را ارسال کنید (الزامی):")

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_ad_photo')
def process_edited_ad_photo(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    state, data = get_user_state(user_id)
    ad_id = data['id']
    cursor.execute("UPDATE ads SET title = ?, description = ?, contact = ?, photo_id = ? WHERE id = ? AND user_id = ?",
                   (data['title'], data['description'], data['contact'], photo_id, ad_id, user_id))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "آگهی ویرایش شد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_ad_photo' and message.content_types != ['photo'])
def warn_edit_photo_required(message):
    bot.send_message(message.chat.id, "عکس الزامی است. لطفاً یک عکس ارسال کنید.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_ad_"))
def delete_ad(call):
    ad_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    cursor.execute("DELETE FROM ads WHERE id = ? AND user_id = ?", (ad_id, user_id))
    conn.commit()
    bot.send_message(user_id, "آگهی حذف شد.", reply_markup=get_main_keyboard())

# Profile and Shops Section
def show_profile(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        _, username, age, gender, points, rand_id, _ = user_data
        response = f"پروفایل:\nنام: {username}\nشناسه: {rand_id}\nسن: {convert_fa_numbers(str(age))}\nجنسیت: {gender}\nامتیاز: {points}"
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        keyboard.add("ویرایش پروفایل", "گویمی‌های برتر ⭐")
        keyboard.add("بازگشت به منو اصلی")
        bot.send_message(user_id, response, reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "گویمی‌های برتر ⭐")
def show_top_users_from_keyboard(message):
    cursor.execute("SELECT username, age, gender, points FROM users WHERE points > 1000 ORDER BY points DESC")
    top_users = cursor.fetchall()
    if top_users:
        response = "گویمی‌های برتر:\n"
        for user in top_users:
            response += f"نام: {user[0]}، سن: {user[1]}، جنسیت: {user[2]}، امتیاز: {user[3]}\n"
    else:
        response = "کاربری با امتیاز بالای 1000 یافت نشد."
    bot.send_message(message.chat.id, response, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "ویرایش پروفایل")
def edit_profile_menu(message):
    bot.send_message(message.chat.id, "چه چیزی را ویرایش کنید؟", reply_markup=get_profile_edit_keyboard())

@bot.message_handler(func=lambda message: message.text == "تغییر اسم")
def change_username_start(message):
    set_user_state(message.from_user.id, 'awaiting_new_username')
    bot.send_message(message.chat.id, "اسم مستعار جدید را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_username')
def change_username_process(message):
    user_id = message.from_user.id
    new_username = message.text.strip()
    if not new_username:
        bot.send_message(user_id, "نام معتبر وارد کنید:")
        return
    cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (new_username, user_id))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, f"نام شما به {new_username} تغییر یافت.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "تغییر سن")
def change_age_start(message):
    set_user_state(message.from_user.id, 'awaiting_new_age')
    keyboard = types.ReplyKeyboardMarkup(row_width=10, resize_keyboard=True)
    ages = [str(i) for i in range(13, 71)]
    keyboard.add(*ages)
    bot.send_message(message.chat.id, "سن جدید را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_age')
def change_age_process(message):
    user_id = message.from_user.id
    try:
        new_age = int(message.text)
        if 13 <= new_age <= 70:
            cursor.execute("UPDATE users SET age = ? WHERE user_id = ?", (new_age, user_id))
            conn.commit()
            cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
            conn.commit()
            bot.send_message(user_id, f"سن شما به {convert_fa_numbers(str(new_age))} تغییر یافت.", reply_markup=get_main_keyboard())
        else:
            bot.send_message(user_id, "سن باید بین 13 تا 70 باشد:")
    except ValueError:
        bot.send_message(user_id, "لطفاً عدد وارد کنید:")

@bot.message_handler(func=lambda message: message.text == "تغییر جنسیت")
def change_gender_start(message):
    set_user_state(message.from_user.id, 'awaiting_new_gender')
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("پسر", "دختر")
    bot.send_message(message.chat.id, "جنسیت جدید را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_gender')
def change_gender_process(message):
    user_id = message.from_user.id
    new_gender = message.text
    if new_gender in ["پسر", "دختر"]:
        cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (new_gender, user_id))
        conn.commit()
        cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        conn.commit()
        bot.send_message(user_id, f"جنسیت شما به {new_gender} تغییر یافت.", reply_markup=get_main_keyboard())
    else:
        bot.send_message(user_id, "لطفاً 'پسر' یا 'دختر' را انتخاب کنید:", reply_markup=types.ReplyKeyboardMarkup(row_width=2).add("پسر", "دختر"))

def show_shop_categories(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    categories = ["رستوران 🍽", "سوپری 🛒", "نانوایی 🥖", "پوشاکی 👕", "موبایل‌فروشی 📱", "میوه‌فروشی 🍎", "قنادی 🍰"]
    items = [types.KeyboardButton(cat) for cat in categories]
    add_shop_btn = types.KeyboardButton("➕ افزودن مکان")
    my_shops_btn = types.KeyboardButton("📄 مکان‌های من")
    keyboard.add(*items)
    keyboard.add(add_shop_btn, my_shops_btn)
    keyboard.add("بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "دسته‌بندی یا گزینه را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["رستوران 🍽", "سوپری 🛒", "نانوایی 🥖", "پوشاکی 👕", "موبایل‌فروشی 📱", "میوه‌فروشی 🍎", "قنادی 🍰"])
def show_shops_by_category(message):
    category = message.text.split(' ')[0]
    cursor.execute("SELECT id, title FROM shops WHERE category = ?", (category,))
    shops = cursor.fetchall()
    if shops:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        for shop in shops:
            keyboard.add(shop[1])
        keyboard.add("بازگشت به منو اصلی")
        set_user_state(message.from_user.id, f'awaiting_shop_selection_{category}')
        bot.send_message(message.chat.id, f"مکان‌های دسته {category}:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, f"مغازه‌ای در دسته {category} یافت نشد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "➕ افزودن مکان")
def check_add_shop_permission(message):
    if message.from_user.id == ADMIN_ID:
        set_user_state(message.from_user.id, 'awaiting_shop_title')
        bot.send_message(message.from_user.id, "عنوان مکان (مغازه) را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.from_user.id, "برای ثبت مکان با ادمین هماهنگ کنید: @Sedayegoyom10", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text in [title for _, title in cursor.execute("SELECT id, title FROM shops WHERE admin_id = ?", (ADMIN_ID,)).fetchall()])
def show_admin_shop_details(message):
    title = message.text
    cursor.execute("SELECT * FROM shops WHERE title = ? AND admin_id = ?", (title, ADMIN_ID))
    shop = cursor.fetchone()
    if shop:
        shop_id, title, description, address, category, photo_id, contact, admin_id, seller_username, seller_age, seller_gender = shop
        response = f"عنوان: {title}\nتوضیحات: {description}\nآدرس: {address}\nدسته: {category}\nتماس: {contact}\nفروشنده: {seller_username}، سن: {seller_age}، جنسیت: {seller_gender}"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("ویرایش", callback_data=f"edit_shop_{shop_id}"))
        keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_shop_{shop_id}"))
        if photo_id:
            bot.send_photo(message.chat.id, photo_id, caption=response, reply_markup=keyboard)
        else:
            bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_title' and message.from_user.id == ADMIN_ID)
def get_shop_title(message):
    user_id = message.from_user.id
    title = message.text.strip()
    if not title:
        bot.send_message(user_id, "عنوان معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_shop_description', {'title': title})
    bot.send_message(user_id, "توضیحات مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_description' and message.from_user.id == ADMIN_ID)
def get_shop_description(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    data['description'] = message.text.strip()
    if not data['description']:
        bot.send_message(user_id, "توضیحات معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_shop_address', data)
    bot.send_message(user_id, "آدرس مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_address' and message.from_user.id == ADMIN_ID)
def get_shop_address(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    data['address'] = message.text.strip()
    if not data['address']:
        bot.send_message(user_id, "آدرس معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_shop_category', data)
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("رستوران", "سوپری", "نانوایی", "پوشاکی", "موبایل‌فروشی", "میوه‌فروشی", "قنادی")
    bot.send_message(user_id, "دسته‌بندی مکان را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_category' and message.from_user.id == ADMIN_ID)
def get_shop_category(message):
    user_id = message.from_user.id
    category = message.text
    valid_categories = ["رستوران", "سوپری", "نانوایی", "پوشاکی", "موبایل‌فروشی", "میوه‌فروشی", "قنادی"]
    if category in valid_categories:
        state, data = get_user_state(user_id)
        data['category'] = category
        set_user_state(user_id, 'awaiting_shop_contact', data)
        bot.send_message(user_id, "شماره تماس مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())
    else:
        bot.send_message(user_id, "از دکمه‌ها استفاده کنید:", reply_markup=types.ReplyKeyboardMarkup(row_width=2).add(*valid_categories))

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_contact' and message.from_user.id == ADMIN_ID)
def get_shop_contact(message):
    user_id = message.from_user.id
    contact = message.text.strip()
    if not contact:
        bot.send_message(user_id, "اطلاعات تماس معتبر وارد کنید:")
        return
    if not (contact.startswith("09") and len(contact) == 11 and contact.isdigit()):
        bot.send_message(user_id, "شماره تماس باید ۱۱ رقم و با 09 شروع شود.")
        return
    state, data = get_user_state(user_id)
    data['contact'] = contact
    set_user_state(user_id, 'awaiting_user_id', data)
    bot.send_message(user_id, "شناسه رندوم کاربر (در پروفایل) را وارد کنید تا مغازه به او اختصاص داده شود:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_user_id' and message.from_user.id == ADMIN_ID)
def get_shop_owner_id(message):
    user_id = message.from_user.id
    try:
        rand_id = int(message.text.strip())
        cursor.execute("SELECT user_id FROM users WHERE random_id = ?", (rand_id,))
        owner = cursor.fetchone()
        if not owner:
            bot.send_message(user_id, "کاربری با این شناسه یافت نشد.")
            return
        data = get_user_state(user_id)[1]
        data['admin_id'] = owner[0]
        set_user_state(user_id, 'awaiting_seller_username', data)
        bot.send_message(user_id, "اسم مستعار فروشنده را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())
    except:
        bot.send_message(user_id, "شناسه نامعتبر است.")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_seller_username' and message.from_user.id == ADMIN_ID)
def get_seller_username(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    data['seller_username'] = message.text.strip()
    if not data['seller_username']:
        bot.send_message(user_id, "نام معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_seller_age', data)
    bot.send_message(user_id, "سن فروشنده را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_seller_age' and message.from_user.id == ADMIN_ID)
def get_seller_age(message):
    user_id = message.from_user.id
    try:
        age = int(message.text)
        if 13 <= age <= 70:
            state, data = get_user_state(user_id)
            data['seller_age'] = age
            set_user_state(user_id, 'awaiting_seller_gender', data)
            keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
            keyboard.add("پسر", "دختر")
            bot.send_message(user_id, "جنسیت فروشنده را وارد کنید:", reply_markup=keyboard)
        else:
            bot.send_message(user_id, "سن باید بین 13 تا 70 باشد:")
    except ValueError:
        bot.send_message(user_id, "عدد وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_seller_gender' and message.from_user.id == ADMIN_ID)
def get_seller_gender(message):
    user_id = message.from_user.id
    gender = message.text
    if gender in ["پسر", "دختر"]:
        state, data = get_user_state(user_id)
        data['seller_gender'] = gender
        set_user_state(user_id, 'awaiting_shop_photo', data)
        bot.send_message(user_id, "عکس مکان را ارسال کنید (الزامی):", reply_markup=get_admin_sub_menu_keyboard())
    else:
        bot.send_message(user_id, "از دکمه‌ها استفاده کنید:", reply_markup=types.ReplyKeyboardMarkup(row_width=2).add("پسر", "دختر"))

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_photo' and message.from_user.id == ADMIN_ID)
def get_shop_photo(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    photo_id = message.photo[-1].file_id
    cursor.execute("""INSERT INTO shops (title, description, address, category, photo_id, contact, admin_id, 
                      seller_username, seller_age, seller_gender) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (data['title'], data['description'], data['address'], data['category'], photo_id,
                    data['contact'], data['admin_id'], data['seller_username'], data['seller_age'], data['seller_gender']))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "مکان ثبت شد.", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_photo' and message.content_types != ['photo'] and message.from_user.id == ADMIN_ID)
def warn_shop_photo_required(message):
    bot.send_message(message.chat.id, "عکس الزامی است. لطفاً یک عکس ارسال کنید.")

@bot.message_handler(func=lambda message: message.text == "📄 مکان‌های من")
def show_my_shops(message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, title FROM shops WHERE admin_id = ?", (user_id,))
    my_shops = cursor.fetchall()
    if my_shops:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        for shop in my_shops:
            keyboard.add(shop[1])
        keyboard.add("بازگشت به منو اصلی")
        bot.send_message(user_id, "مکان‌های شما:", reply_markup=keyboard)
    else:
        bot.send_message(user_id, "شما مکانی ثبت نکرده‌اید.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text in [title for _, title in cursor.execute("SELECT id, title FROM shops").fetchall()])
def show_user_shop_details(message):
    title = message.text
    cursor.execute("SELECT * FROM shops WHERE title = ?", (title,))
    shop = cursor.fetchone()
    if shop:
        shop_id, title, description, address, category, photo_id, contact, admin_id, seller_username, seller_age, seller_gender = shop
        response = f"عنوان: {title}\nتوضیحات: {description}\nآدرس: {address}\nدسته: {category}\nتماس: {contact}\nفروشنده: {seller_username}، سن: {seller_age}، جنسیت: {seller_gender}"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("امتیاز دادن", callback_data=f"rate_shop_{shop_id}"))
        if photo_id:
            bot.send_photo(message.chat.id, photo_id, caption=response, reply_markup=keyboard)
        else:
            bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_shop_") and call.from_user.id == ADMIN_ID)
def edit_shop_start(call):
    shop_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    set_user_state(user_id, 'awaiting_new_shop_title', {'edit_shop_id': shop_id})
    bot.send_message(user_id, "عنوان جدید مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_shop_title' and message.from_user.id == ADMIN_ID)
def get_new_shop_title(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    shop_id = data['edit_shop_id']
    new_title = message.text.strip()
    if not new_title:
        bot.send_message(user_id, "عنوان معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_new_shop_description', {'title': new_title, 'id': shop_id})
    bot.send_message(user_id, "توضیحات جدید مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_shop_description' and message.from_user.id == ADMIN_ID)
def get_new_shop_description(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    shop_id = data['id']
    new_title = data['title']
    new_description = message.text.strip()
    if not new_description:
        bot.send_message(user_id, "توضیحات معتبر وارد کنید:")
        return
    set_user_state(user_id, 'awaiting_new_shop_address', {'title': new_title, 'description': new_description, 'id': shop_id})
    bot.send_message(user_id, "آدرس جدید مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_shop_address' and message.from_user.id == ADMIN_ID)
def get_new_shop_address(message):
    user_id = message.from_user.id
    new_address = message.text.strip()
    if not new_address:
        bot.send_message(user_id, "آدرس معتبر وارد کنید:")
        return
    state, data = get_user_state(user_id)
    shop_id = data['id']
    new_title = data['title']
    new_description = data['description']
    set_user_state(user_id, 'awaiting_new_shop_contact', {'title': new_title, 'description': new_description, 'address': new_address, 'id': shop_id})
    bot.send_message(user_id, "شماره تماس جدید را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_shop_contact' and message.from_user.id == ADMIN_ID)
def get_new_shop_contact(message):
    user_id = message.from_user.id
    contact = message.text.strip()
    if not contact or not (contact.startswith("09") and len(contact) == 11 and contact.isdigit()):
        bot.send_message(user_id, "شماره تماس باید ۱۱ رقم و با 09 شروع شود.")
        return
    state, data = get_user_state(user_id)
    shop_id = data['id']
    new_title = data['title']
    new_description = data['description']
    new_address = data['address']
    set_user_state(user_id, 'awaiting_new_shop_photo', {'title': new_title, 'description': new_description, 'address': new_address, 'contact': contact, 'id': shop_id})
    bot.send_message(user_id, "عکس جدید مکان را ارسال کنید (الزامی):", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_shop_photo' and message.from_user.id == ADMIN_ID)
def process_edited_shop_photo(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    state, data = get_user_state(user_id)
    shop_id = data['id']
    cursor.execute("""UPDATE shops SET title = ?, description = ?, address = ?, contact = ?, photo_id = ? WHERE id = ? AND admin_id = ?""",
                   (data['title'], data['description'], data['address'], data['contact'], photo_id, shop_id, user_id))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "مکان ویرایش شد.", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_shop_photo' and message.content_types != ['photo'] and message.from_user.id == ADMIN_ID)
def warn_edit_shop_photo_required(message):
    bot.send_message(message.chat.id, "عکس الزامی است. لطفاً یک عکس ارسال کنید.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_shop_") and call.from_user.id == ADMIN_ID)
def delete_shop(call):
    shop_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    cursor.execute("DELETE FROM shops WHERE id = ? AND admin_id = ?", (shop_id, user_id))
    conn.commit()
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Error: {e}")
    bot.send_message(user_id, "مکان حذف شد.", reply_markup=get_admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_shop_"))
def handle_rate_shop(call):
    shop_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    set_user_state(user_id, 'awaiting_rating', {'shop_id': shop_id})
    bot.send_message(user_id, "امتیاز خود را از 0 تا 10 وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_rating')
def process_rating(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    shop_id = data['shop_id']
    try:
        rating = int(message.text)
        if 0 <= rating <= 10:
            cursor.execute("INSERT OR REPLACE INTO shop_ratings (shop_id, user_id, rating) VALUES (?, ?, ?)", (shop_id, user_id, rating))
            conn.commit()
            cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
            conn.commit()
            bot.send_message(user_id, f"امتیاز {rating} ثبت شد.", reply_markup=get_main_keyboard())
        else:
            bot.send_message(user_id, "عدد بین 0 تا 10 وارد کنید:")
    except ValueError:
        bot.send_message(user_id, "لطفاً عدد وارد کنید:")

@bot.message_handler(func=lambda message: message.text == "بازگشت به منو اصلی")
def go_back_to_main_menu(message):
    user_id = message.from_user.id
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(message.chat.id, "به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        state, _ = get_user_state(user_id)
        if not state:
            bot.send_message(user_id, "لطفاً از دکمه‌ها استفاده کنید.", reply_markup=get_main_keyboard())
        else:
            bot.send_message(user_id, "لطفاً مراحل قبلی را تکمیل کنید یا به منوی اصلی بازگردید.")
    else:
        send_welcome(message)

# Webhook setup
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)
@app.route(f'/{API_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Invalid Content-Type', 403

@app.route('/')
def index():
    return 'Goyom Bot is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))