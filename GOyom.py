import telebot
import sqlite3
import os
import json
from flask import Flask, request
from telebot import types
import datetime
import jdatetime
from persian import convert_fa_numbers

# Flask app setup
app = Flask(__name__)

# Bot Token and Admin User ID from environment variables
API_TOKEN = os.getenv('API_TOKEN', '8134200098:AAGGapErG9F0ek0lAEdrI53E5gzPDcObTQM')
ADMIN_ID = int(os.getenv('ADMIN_ID', '7385601641'))
WEBHOOK_URL = os.getenv('WEBHOOK_URL') + f'/{API_TOKEN}'

bot = telebot.TeleBot(API_TOKEN)

# Connect to SQLite database (ensure persistence on Render)
DB_PATH = os.getenv('DB_PATH', 'goyom_bot.db')
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    age INTEGER,
    gender TEXT,
    points INTEGER DEFAULT 0,
    user_code TEXT UNIQUE
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
    seller_gender TEXT,
    owner_user_id INTEGER
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
        types.KeyboardButton("🗳 ایجاد نظرسنجی"),
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

def update_user_points(user_id, points_to_add=5):
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points_to_add, user_id))
    conn.commit()

def notify_all_users(section):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    message_text = f"به بخش '{section}' موضوع جدیدی اضافه شد. برای بررسی بر روی دکمه بخش کلیک کنید."
    for user in users:
        try:
            bot.send_message(user[0], message_text, reply_markup=get_main_keyboard())
        except Exception as e:
            print(f"Failed to notify user {user[0]}: {e}")

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

def get_age_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=10, resize_keyboard=True)
    ages = [str(i) for i in range(13, 71)]
    keyboard.add(*ages)
    return keyboard

# General Handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        bot.send_message(user_id, "سلام! شما قبلاً ثبت‌نام کرده‌اید.", reply_markup=get_main_keyboard())
    else:
        set_user_state(user_id, 'awaiting_username')
        bot.send_message(user_id, "خوش آمدید به ربات 'مگا گویم'!\n\n"
                                  "لطفاً اسم مستعار خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

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
    user_code = str(random.randint(10000, 99999))
    while True:
        cursor.execute("SELECT 1 FROM users WHERE user_code = ?", (user_code,))
        if cursor.fetchone() is None:
            break
        user_code = str(random.randint(10000, 99999))
    set_user_state(user_id, 'awaiting_age', {'reg_username': username, 'user_code': user_code})
    bot.send_message(user_id, "لطفاً سن خود را انتخاب کنید:", reply_markup=get_age_keyboard())

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
        user_code = data['user_code']
        cursor.execute("INSERT INTO users (user_id, username, age, gender, user_code) VALUES (?, ?, ?, ?, ?)",
                       (user_id, username, age, gender, user_code))
        conn.commit()
        cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        conn.commit()
        bot.send_message(user_id, f"ثبت‌نام با موفقیت انجام شد!\nکد شما: `{user_code}`", reply_markup=get_main_keyboard(), parse_mode='Markdown')
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

    if message.text == "📢 اخبار گویم":
        show_admin_content(user_id, "اخبار")
    elif message.text == "🌦 روز هفته و تاریخ":
        today = jdatetime.date.today()
        bot.send_message(user_id, f"امروز: {today.strftime('%A %d %B %Y')}", reply_markup=get_main_keyboard())
    elif message.text == "🛍 دیوار گویم (آگهی)":
        handle_divar(message)
    elif message.text == "🎉 سرگرمی و مسابقه":
        bot.send_message(user_id, "این بخش در حال توسعه است.", reply_markup=get_main_keyboard())
    elif message.text == "😂 طنز و خاطرات":
        handle_jokes(message)
    elif message.text == "⚽ ورزش و رویدادها":
        show_admin_content(user_id, "ورزش")
    elif message.text == "🗳 نظرسنجی":
        bot.send_message(user_id, "این بخش در حال توسعه است.", reply_markup=get_main_keyboard())
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

@bot.message_handler(func=lambda message: message.text in ["✍️ مدیریت اخبار", "📝 مدیریت ورزش", "📞 مدیریت خدمات", "🎉 مدیریت مسابقات"] and message.from_user.id == ADMIN_ID)
def manage_admin_content_start(message):
    section_map = {
        "✍️ مدیریت اخبار": "اخبار",
        "📝 مدیریت ورزش": "ورزش",
        "📞 مدیریت خدمات": "خدمات",
        "🎉 مدیریت مسابقات": "مسابقات"
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

@bot.message_handler(func=lambda message: message.text == "🗳 ایجاد نظرسنجی" and message.from_user.id == ADMIN_ID)
def create_poll_start(message):
    set_user_state(ADMIN_ID, 'create_poll_q')
    bot.send_message(ADMIN_ID, "لطفاً متن سوال نظرسنجی را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'create_poll_q' and message.from_user.id == ADMIN_ID)
def create_poll_options(message):
    set_user_state(ADMIN_ID, 'create_poll_a', {'question': message.text})
    bot.send_message(ADMIN_ID, "گزینه‌های نظرسنجی را با کاما جدا کنید (مثال: گزینه ۱,گزینه ۲):", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'create_poll_a' and message.from_user.id == ADMIN_ID)
def create_poll_publish(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    question = data['question']
    options = [opt.strip() for opt in message.text.split(',')]
    if len(options) < 2 or len(options) > 10:
        bot.send_message(user_id, "تعداد گزینه‌ها باید بین 2 تا 10 باشد.")
        return
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for user in users:
        try:
            bot.send_poll(user[0], question, options, is_anonymous=False)
            update_user_points(user[0], 5)
        except Exception as e:
            print(f"Failed to send poll to {user[0]}: {e}")
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "نظرسنجی ارسال شد و کاربران 5 امتیاز گرفتند.", reply_markup=get_admin_keyboard())

# Admin Users Management
@bot.message_handler(func=lambda message: message.text == "👥 کاربران فعال" and message.from_user.id == ADMIN_ID)
def show_active_users(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("پسرها", "دخترها")
    keyboard.add("⬅️ بازگشت به پنل مدیریت")
    bot.send_message(message.from_user.id, f"تعداد کاربران: {total}", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["پسرها", "دخترها"] and message.from_user.id == ADMIN_ID)
def list_users_by_gender(message):
    gender = "پسر" if message.text == "پسرها" else "دختر"
    cursor.execute("SELECT username, age, points FROM users WHERE gender = ?", (gender,))
    users = cursor.fetchall()
    if users:
        response = f"کاربران {gender}:\n"
        for user in users:
            response += f"نام: {user[0]}، سن: {user[1]}، امتیاز: {user[2]}\n"
    else:
        response = f"کاربری با جنسیت {gender} یافت نشد."
    bot.send_message(message.from_user.id, response, reply_markup=get_admin_keyboard())

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_joke_"))
def show_joke_detail(call):
    joke_id = int(call.data.split('_')[2])
    cursor.execute("SELECT joke_text FROM jokes WHERE id = ?", (joke_id,))
    joke = cursor.fetchone()
    if joke:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("ویرایش", callback_data=f"edit_joke_{joke_id}"))
        keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_joke_{joke_id}"))
        bot.edit_message_text(joke[0], call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    else:
        bot.answer_callback_query(call.id, "طنز یافت نشد.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_joke_"))
def edit_joke_start(call):
    joke_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    cursor.execute("SELECT user_id FROM jokes WHERE id = ?", (joke_id,))
    owner = cursor.fetchone()
    if not owner or owner[0] != user_id:
        bot.answer_callback_query(call.id, "شما مالک این طنز نیستید.")
        return
    set_user_state(user_id, 'awaiting_new_joke', {'edit_joke_id': joke_id})
    bot.send_message(user_id, "لطفاً متن جدید طنز را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_new_joke')
def edit_joke_finish(message):
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
    bot.send_message(user_id, "طنز با موفقیت ویرایش شد.", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_joke_"))
def delete_joke(call):
    joke_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    cursor.execute("SELECT user_id FROM jokes WHERE id = ?", (joke_id,))
    owner = cursor.fetchone()
    if not owner or owner[0] != user_id:
        bot.answer_callback_query(call.id, "شما مالک این طنز نیستید.")
        return
    cursor.execute("DELETE FROM jokes WHERE id = ? AND user_id = ?", (joke_id, user_id))
    conn.commit()
    bot.edit_message_text("طنز حذف شد.", call.message.chat.id, call.message.message_id)
    bot.send_message(user_id, "طنز شما حذف شد.", reply_markup=get_main_keyboard())

# Divar Section
def handle_divar(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("🔎 مشاهده آگهی‌ها", "➕ افزودن آگهی")
    keyboard.add("📄 آگهی‌های من", "بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "به دیوار گویم خوش آمدید.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "➕ افزودن آگهی")
def start_add_ad(message):
    user_id = message.from_user.id
    set_user_state(user_id, 'awaiting_ad_title')
    bot.send_message(user_id, "عنوان آگهی را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_title')
def get_ad_title(message):
    user_id = message.from_user.id
    set_user_state(user_id, 'awaiting_ad_description', {'title': message.text})
    bot.send_message(user_id, "توضیحات آگهی را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_description')
def get_ad_description(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    data['description'] = message.text
    set_user_state(user_id, 'awaiting_ad_category_main', data)
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(*list(ad_categories.keys()))
    bot.send_message(user_id, "دسته اصلی را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_category_main')
def get_ad_category_main(message):
    user_id = message.from_user.id
    main_cat = message.text
    if main_cat not in ad_categories:
        bot.send_message(user_id, "لطفاً از دکمه‌ها استفاده کنید.")
        return
    state, data = get_user_state(user_id)
    data['category_main'] = main_cat
    set_user_state(user_id, 'awaiting_ad_category_sub', data)
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(*ad_categories[main_cat])
    bot.send_message(user_id, "دسته فرعی را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_category_sub')
def get_ad_category_sub(message):
    user_id = message.from_user.id
    sub_cat = message.text
    state, data = get_user_state(user_id)
    main_cat = data['category_main']
    if sub_cat not in ad_categories.get(main_cat, []):
        bot.send_message(user_id, "لطفاً از دکمه‌ها استفاده کنید.")
        return
    data['category_sub'] = sub_cat
    set_user_state(user_id, 'awaiting_ad_contact', data)
    bot.send_message(user_id, "شماره تماس خود را وارد کنید (11 رقم):", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_contact')
def get_ad_contact(message):
    user_id = message.from_user.id
    contact = message.text.replace(' ', '')
    if len(contact) != 11 or not contact.isdigit():
        bot.send_message(user_id, "شماره تماس باید 11 رقم باشد. دوباره وارد کنید:")
        return
    state, data = get_user_state(user_id)
    data['contact'] = contact
    set_user_state(user_id, 'awaiting_ad_photo', data)
    bot.send_message(user_id, "عکس آگهی را ارسال کنید (اجباری):")

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_photo')
def get_ad_photo(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    state, data = get_user_state(user_id)
    data['photo_id'] = photo_id
    cursor.execute('''INSERT INTO ads (user_id, title, description, category_main, category_sub, photo_id, contact)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (user_id, data['title'], data['description'], data['category_main'], data['category_sub'], photo_id, data['contact']))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    update_user_points(user_id, 5)
    bot.send_message(user_id, "آگهی شما با موفقیت ثبت شد و 5 امتیاز گرفتید!", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_ad_photo')
def warn_ad_photo(message):
    bot.send_message(message.from_user.id, "لطفاً یک عکس ارسال کنید (اجباری):")

@bot.message_handler(func=lambda message: message.text == "🔎 مشاهده آگهی‌ها")
def show_all_ads(message):
    cursor.execute("SELECT id, title FROM ads")
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, "آگهی‌ای یافت نشد.", reply_markup=get_main_keyboard())
        return
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for ad_id, title in ads:
        keyboard.add(f"📌 {title}")
    keyboard.add("بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "آگهی‌ها:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text.startswith("📌 ") and message.text[2:] in [title for _, title in cursor.execute("SELECT id, title FROM ads").fetchall()])
def show_ad_detail(message):
    title = message.text[2:]
    cursor.execute("SELECT * FROM ads WHERE title = ?", (title,))
    ad = cursor.fetchone()
    if not ad:
        bot.send_message(message.chat.id, "آگهی یافت نشد.")
        return
    ad_id, _, title, description, category_main, category_sub, photo_id, contact = ad
    response = f"عنوان: {title}\nتوضیحات: {description}\nدسته: {category_main} → {category_sub}\nتماس: {contact}"
    keyboard = types.InlineKeyboardMarkup()
    user_id = message.from_user.id
    if user_id == ad[1]:  # owner
        keyboard.add(types.InlineKeyboardButton("ویرایش", callback_data=f"edit_ad_{ad_id}"))
        keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_ad_{ad_id}"))
    if photo_id:
        bot.send_photo(message.chat.id, photo_id, caption=response, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_ad_"))
def edit_ad_start(call):
    ad_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    cursor.execute("SELECT user_id FROM ads WHERE id = ?", (ad_id,))
    owner = cursor.fetchone()
    if not owner or owner[0] != user_id:
        bot.answer_callback_query(call.id, "شما مالک این آگهی نیستید.")
        return
    set_user_state(user_id, 'edit_ad', {'ad_id': ad_id})
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("تغییر عنوان", "تغییر توضیحات", "تغییر دسته", "تغییر شماره", "تغییر عکس")
    bot.send_message(user_id, "کدام بخش را می‌خواهید ویرایش کنید؟", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'edit_ad')
def handle_edit_ad_choice(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    ad_id = data['ad_id']
    choice = message.text
    if choice == "تغییر عنوان":
        set_user_state(user_id, 'edit_ad_title', data)
        bot.send_message(user_id, "عنوان جدید را وارد کنید:")
    elif choice == "تغییر توضیحات":
        set_user_state(user_id, 'edit_ad_description', data)
        bot.send_message(user_id, "توضیحات جدید را وارد کنید:")
    elif choice == "تغییر دسته":
        set_user_state(user_id, 'edit_ad_category_main', data)
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        keyboard.add(*list(ad_categories.keys()))
        bot.send_message(user_id, "دسته اصلی جدید را انتخاب کنید:", reply_markup=keyboard)
    elif choice == "تغییر شماره":
        set_user_state(user_id, 'edit_ad_contact', data)
        bot.send_message(user_id, "شماره جدید (11 رقم):")
    elif choice == "تغییر عکس":
        set_user_state(user_id, 'edit_ad_photo', data)
        bot.send_message(user_id, "عکس جدید را ارسال کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'edit_ad_title')
def edit_ad_title(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    cursor.execute("UPDATE ads SET title = ? WHERE id = ?", (message.text, data['ad_id']))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "عنوان آگهی ویرایش شد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'edit_ad_description')
def edit_ad_description(message):
    user_id = message.from_user.id
    state, data = get_user_state(user_id)
    cursor.execute("UPDATE ads SET description = ? WHERE id = ?", (message.text, data['ad_id']))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "توضیحات آگهی ویرایش شد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'edit_ad_contact')
def edit_ad_contact(message):
    user_id = message.from_user.id
    contact = message.text.replace(' ', '')
    if len(contact) != 11 or not contact.isdigit():
        bot.send_message(user_id, "شماره باید 11 رقم باشد. دوباره وارد کنید:")
        return
    state, data = get_user_state(user_id)
    cursor.execute("UPDATE ads SET contact = ? WHERE id = ?", (contact, data['ad_id']))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "شماره تماس آگهی ویرایش شد.", reply_markup=get_main_keyboard())

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id)[0] == 'edit_ad_photo')
def edit_ad_photo(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    state, data = get_user_state(user_id)
    cursor.execute("UPDATE ads SET photo_id = ? WHERE id = ?", (photo_id, data['ad_id']))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "عکس آگهی ویرایش شد.", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_ad_"))
def delete_ad(call):
    ad_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    cursor.execute("SELECT user_id FROM ads WHERE id = ?", (ad_id,))
    owner = cursor.fetchone()
    if not owner or owner[0] != user_id:
        bot.answer_callback_query(call.id, "شما مالک این آگهی نیستید.")
        return
    cursor.execute("DELETE FROM ads WHERE id = ? AND user_id = ?", (ad_id, user_id))
    conn.commit()
    bot.edit_message_text("آگهی حذف شد.", call.message.chat.id, call.message.message_id)
    bot.send_message(user_id, "آگهی شما حذف شد.", reply_markup=get_main_keyboard())

# Profile and Shops Section
def show_profile(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        _, username, age, gender, points, user_code = user_data
        response = f"پروفایل:\nنام: {username}\nسن: {convert_fa_numbers(str(age))}\nجنسیت: {gender}\nامتیاز: {points}\nکد کاربری: `{user_code}`"
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        keyboard.add("ویرایش پروفایل", "گویمی‌های برتر ⭐")
        keyboard.add("بازگشت به منو اصلی")
        bot.send_message(user_id, response, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "ویرایش پروفایل")
def edit_profile(message):
    bot.send_message(message.chat.id, "لطفاً از دکمه‌ها استفاده کنید:", reply_markup=get_profile_edit_keyboard())

@bot.message_handler(func=lambda message: message.text == "تغییر اسم")
def change_username(message):
    user_id = message.from_user.id
    set_user_state(user_id, 'changing_username')
    bot.send_message(user_id, "نام جدید خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'changing_username')
def save_username(message):
    user_id = message.from_user.id
    new_name = message.text.strip()
    if not new_name:
        bot.send_message(user_id, "نام نمی‌تواند خالی باشد.")
        return
    cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (new_name, user_id))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "نام شما تغییر کرد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "تغییر سن")
def change_age(message):
    user_id = message.from_user.id
    set_user_state(user_id, 'changing_age')
    bot.send_message(user_id, "سن جدید را انتخاب کنید:", reply_markup=get_age_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'changing_age')
def save_age(message):
    user_id = message.from_user.id
    try:
        age = int(message.text)
        if 13 <= age <= 70:
            cursor.execute("UPDATE users SET age = ? WHERE user_id = ?", (age, user_id))
            conn.commit()
            cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
            conn.commit()
            bot.send_message(user_id, "سن شما تغییر کرد.", reply_markup=get_main_keyboard())
        else:
            bot.send_message(user_id, "سن باید بین 13 تا 70 باشد.")
    except ValueError:
        bot.send_message(user_id, "لطفاً عدد وارد کنید.")

@bot.message_handler(func=lambda message: message.text == "تغییر جنسیت")
def change_gender(message):
    user_id = message.from_user.id
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("پسر", "دختر")
    set_user_state(user_id, 'changing_gender')
    bot.send_message(user_id, "جنسیت جدید را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'changing_gender')
def save_gender(message):
    user_id = message.from_user.id
    gender = message.text
    if gender in ["پسر", "دختر"]:
        cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
        conn.commit()
        cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        conn.commit()
        bot.send_message(user_id, "جنسیت شما تغییر کرد.", reply_markup=get_main_keyboard())
    else:
        bot.send_message(user_id, "لطفاً 'پسر' یا 'دختر' را انتخاب کنید.")

# Shop Section
def show_shop_categories(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    categories = ["غذا", "لوازم", "خدمات", "ورزشی", "آموزشی"]
    keyboard.add(*categories)
    keyboard.add("بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "دسته مغازه را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["غذا", "لوازم", "خدمات", "ورزشی", "آموزشی"])
def show_shops_in_category(message):
    category = message.text
    cursor.execute("SELECT id, title FROM shops WHERE category = ?", (category,))
    shops = cursor.fetchall()
    if not shops:
        bot.send_message(message.chat.id, "مغازه‌ای یافت نشد.", reply_markup=get_main_keyboard())
        return
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for shop_id, title in shops:
        keyboard.add(f"🏪 {title}")
    keyboard.add("بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "مغازه‌ها:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text.startswith("🏪 ") and message.text[2:] in [title for _, title in cursor.execute("SELECT id, title FROM shops").fetchall()])
def show_shop_detail(message):
    title = message.text[2:]
    cursor.execute("SELECT * FROM shops WHERE title = ?", (title,))
    shop = cursor.fetchone()
    if not shop:
        bot.send_message(message.chat.id, "مغازه یافت نشد.")
        return
    shop_id, title, description, address, category, photo_id, contact, admin_id, seller_username, seller_age, seller_gender, owner_user_id = shop
    contact_text = contact if contact else "بدون شماره"
    response = f"عنوان: {title}\nتوضیحات: {description}\nآدرس: {address}\nدسته: {category}\nتماس: {contact_text}\nفروشنده: {seller_username}، سن: {seller_age}، جنسیت: {seller_gender}"
    keyboard = types.InlineKeyboardMarkup()
    user_id = message.from_user.id
    if user_id == owner_user_id or user_id == ADMIN_ID:
        keyboard.add(types.InlineKeyboardButton("ویرایش", callback_data=f"edit_shop_{shop_id}"))
        keyboard.add(types.InlineKeyboardButton("حذف", callback_data=f"delete_shop_{shop_id}"))
    if photo_id:
        bot.send_photo(message.chat.id, photo_id, caption=response, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, response, reply_markup=keyboard)

# Admin Shop Management
@bot.message_handler(func=lambda message: message.text == "🏪 مدیریت مکان‌ها" and message.from_user.id == ADMIN_ID)
def manage_shops(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("➕ افزودن مغازه", "🗂 لیست مغازه‌ها")
    keyboard.add("⬅️ بازگشت به پنل مدیریت")
    bot.send_message(message.from_user.id, "مدیریت مغازه‌ها:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "➕ افزودن مغازه" and message.from_user.id == ADMIN_ID)
def start_add_shop(message):
    set_user_state(ADMIN_ID, 'awaiting_shop_title')
    bot.send_message(ADMIN_ID, "عنوان مغازه را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_title' and message.from_user.id == ADMIN_ID)
def get_shop_title(message):
    set_user_state(ADMIN_ID, 'awaiting_shop_description', {'title': message.text})
    bot.send_message(ADMIN_ID, "توضیحات مغازه را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_description' and message.from_user.id == ADMIN_ID)
def get_shop_description(message):
    state, data = get_user_state(ADMIN_ID)
    data['description'] = message.text
    set_user_state(ADMIN_ID, 'awaiting_shop_address', data)
    bot.send_message(ADMIN_ID, "آدرس مغازه را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_address' and message.from_user.id == ADMIN_ID)
def get_shop_address(message):
    state, data = get_user_state(ADMIN_ID)
    data['address'] = message.text
    set_user_state(ADMIN_ID, 'awaiting_shop_category', data)
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("غذا", "لوازم", "خدمات", "ورزشی", "آموزشی")
    bot.send_message(ADMIN_ID, "دسته مغازه را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_category' and message.from_user.id == ADMIN_ID)
def get_shop_category(message):
    cat = message.text
    if cat not in ["غذا", "لوازم", "خدمات", "ورزشی", "آموزشی"]:
        bot.send_message(ADMIN_ID, "لطفاً از دکمه‌ها استفاده کنید.")
        return
    state, data = get_user_state(ADMIN_ID)
    data['category'] = cat
    set_user_state(ADMIN_ID, 'awaiting_shop_contact', data)
    bot.send_message(ADMIN_ID, "شماره تماس (11 رقم) یا 'بدون شماره':", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_contact' and message.from_user.id == ADMIN_ID)
def get_shop_contact(message):
    contact = message.text.strip()
    if contact != "بدون شماره":
        contact = contact.replace(' ', '')
        if len(contact) != 11 or not contact.isdigit():
            bot.send_message(ADMIN_ID, "شماره باید 11 رقم باشد یا 'بدون شماره'.")
            return
    state, data = get_user_state(ADMIN_ID)
    data['contact'] = contact
    set_user_state(ADMIN_ID, 'awaiting_shop_photo', data)
    bot.send_message(ADMIN_ID, "عکس مغازه را ارسال کنید (اجباری):")

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_photo' and message.from_user.id == ADMIN_ID)
def get_shop_photo(message):
    photo_id = message.photo[-1].file_id
    state, data = get_user_state(ADMIN_ID)
    data['photo_id'] = photo_id
    set_user_state(ADMIN_ID, 'awaiting_shop_seller_username', data)
    bot.send_message(ADMIN_ID, "اسم فروشنده را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_seller_username' and message.from_user.id == ADMIN_ID)
def get_shop_seller_username(message):
    state, data = get_user_state(ADMIN_ID)
    data['seller_username'] = message.text
    set_user_state(ADMIN_ID, 'awaiting_shop_seller_age', data)
    bot.send_message(ADMIN_ID, "سن فروشنده را وارد کنید:")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_seller_age' and message.from_user.id == ADMIN_ID)
def get_shop_seller_age(message):
    try:
        age = int(message.text)
        state, data = get_user_state(ADMIN_ID)
        data['seller_age'] = age
        set_user_state(ADMIN_ID, 'awaiting_shop_seller_gender', data)
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        keyboard.add("پسر", "دختر")
        bot.send_message(ADMIN_ID, "جنسیت فروشنده را انتخاب کنید:", reply_markup=keyboard)
    except ValueError:
        bot.send_message(ADMIN_ID, "لطفاً عدد وارد کنید.")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_seller_gender' and message.from_user.id == ADMIN_ID)
def get_shop_seller_gender(message):
    gender = message.text
    if gender not in ["پسر", "دختر"]:
        bot.send_message(ADMIN_ID, "لطفاً 'پسر' یا 'دختر' را انتخاب کنید.")
        return
    state, data = get_user_state(ADMIN_ID)
    data['seller_gender'] = gender
    set_user_state(ADMIN_ID, 'awaiting_shop_owner_code', data)
    bot.send_message(ADMIN_ID, "کد کاربری مالک مغازه را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id)[0] == 'awaiting_shop_owner_code' and message.from_user.id == ADMIN_ID)
def assign_shop_to_user(message):
    code = message.text.strip()
    cursor.execute("SELECT user_id FROM users WHERE user_code = ?", (code,))
    user = cursor.fetchone()
    if not user:
        bot.send_message(ADMIN_ID, "کد کاربری نامعتبر است. دوباره وارد کنید:")
        return
    owner_user_id = user[0]
    state, data = get_user_state(ADMIN_ID)
    cursor.execute('''INSERT INTO shops (title, description, address, category, photo_id, contact, admin_id,
                      seller_username, seller_age, seller_gender, owner_user_id)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (data['title'], data['description'], data['address'], data['category'], data['photo_id'],
                    data['contact'], ADMIN_ID, data['seller_username'], data['seller_age'], data['seller_gender'], owner_user_id))
    conn.commit()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (ADMIN_ID,))
    conn.commit()
    bot.send_message(ADMIN_ID, f"مغازه برای کاربر {code} ثبت شد.", reply_markup=get_admin_keyboard())
    bot.send_message(owner_user_id, "مغازه‌ای برای شما ثبت شد!", reply_markup=get_main_keyboard())

# Back to main menu
@bot.message_handler(func=lambda message: message.text == "بازگشت به منو اصلی")
def go_back_to_main_menu(message):
    user_id = message.from_user.id
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(message.chat.id, "به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())

# Handle all other messages
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
    import random
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))