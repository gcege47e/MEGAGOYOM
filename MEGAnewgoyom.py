import telebot
import sqlite3
from telebot import types
import datetime
import jdatetime
from persian import convert_fa_numbers

# Bot Token and Admin User ID
API_TOKEN = '8134200098:AAGGapErG9F0ek0lAEdrI53E5gzPDcObTQM'
ADMIN_ID = 7385601641

bot = telebot.TeleBot(API_TOKEN)

# Connect to SQLite database
conn = sqlite3.connect('goyom_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    age INTEGER,
    gender TEXT,
    points INTEGER DEFAULT 0
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    description TEXT,
    category_main TEXT,
    category_sub TEXT,
    photo_id TEXT,
    contact TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS shops (
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
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS shop_ratings (
    shop_id INTEGER,
    user_id INTEGER,
    rating INTEGER,
    PRIMARY KEY (shop_id, user_id)
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS admin_content (
    section TEXT PRIMARY KEY,
    content TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS jokes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    joke_text TEXT
)
''')
conn.commit()

# --- Category Structure for Ads ---
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

# --- Helper Functions ---
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

def update_user_points(user_id, points_to_add=1):
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points_to_add, user_id))
    conn.commit()

def notify_all_users(section):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    message_text = f"به بخش '{section}' موضوع جدیدی اضافه شد. برای بررسی بر روی دکمه بخش کلیک کنید."
    for user in users:
        try:
            bot.send_message(user[0], message_text, reply_markup=get_main_keyboard())
        except:
            pass  # Skip if can't send (user blocked bot, etc.)

user_states = {}

# --- General Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        bot.send_message(user_id, "سلام! شما قبلاً ثبت‌نام کرده‌اید و به منوی اصلی منتقل شدید.", reply_markup=get_main_keyboard())
    else:
        user_states[user_id] = 'awaiting_username'
        bot.send_message(user_id, "خوش آمدید به ربات 'مگا گویم'!\nلطفاً یک اسم مستعار برای خود انتخاب کنید:", reply_markup=types.ReplyKeyboardRemove())

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

# --- Registration Handlers ---
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_username')
def get_username(message):
    user_id = message.from_user.id
    username = message.text
    user_states[user_id] = 'awaiting_age'
    user_states[f'reg_username_{user_id}'] = username

    keyboard = types.ReplyKeyboardMarkup(row_width=10, resize_keyboard=True)
    ages = [str(i) for i in range(13, 71)]
    keyboard.add(*ages)
    
    bot.send_message(user_id, f"اسم مستعار شما **{username}** ثبت شد.\n\nلطفاً سن دقیق خود را از بین دکمه‌ها انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_age')
def get_age(message):
    user_id = message.from_user.id
    try:
        age = int(message.text)
        if 13 <= age <= 70:
            user_states[f'reg_age_{user_id}'] = age
            user_states[user_id] = 'awaiting_gender'
            
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
            markup.add("پسر", "دختر")
            
            bot.send_message(user_id, f"سن شما **{convert_fa_numbers(str(age))}** ثبت شد.\n\nلطفاً جنسیت خود را انتخاب کنید:", reply_markup=markup)
        else:
            bot.send_message(user_id, "لطفاً سن خود را از بین 13 تا 70 سال و فقط با استفاده از دکمه‌ها انتخاب کنید.")
    except (ValueError, KeyError):
        bot.send_message(user_id, "لطفاً سن خود را فقط با استفاده از دکمه‌ها انتخاب کنید.")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_gender')
def get_gender(message):
    user_id = message.from_user.id
    gender = message.text
    
    if f'reg_username_{user_id}' not in user_states or f'reg_age_{user_id}' not in user_states:
        bot.send_message(user_id, "خطایی در ثبت‌نام رخ داد. لطفاً از اول شروع کنید: /start", reply_markup=types.ReplyKeyboardRemove())
        if user_id in user_states: del user_states[user_id]
        if f'reg_username_{user_id}' in user_states: del user_states[f'reg_username_{user_id}']
        if f'reg_age_{user_id}' in user_states: del user_states[f'reg_age_{user_id}']
        return

    if gender in ["پسر", "دختر"]:
        username = user_states.pop(f'reg_username_{user_id}')
        age = user_states.pop(f'reg_age_{user_id}')
        cursor.execute("INSERT INTO users (user_id, username, age, gender) VALUES (?, ?, ?, ?)", (user_id, username, age, gender))
        conn.commit()
        del user_states[user_id]
        
        welcome_message = (
            f"🎉 تبریک می‌گم **{username}**!\n"
            f"شما با موفقیت در ربات مگا گویم ثبت‌نام شدید. ✨\n\n"
            "اکنون می‌تونید از تمام امکانات ربات استفاده کنید."
        )
        
        bot.send_message(user_id, welcome_message, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    else:
        bot.send_message(user_id, "لطفاً از دکمه‌های زیر استفاده کنید.")

# --- Main Menu Handlers ---
@bot.message_handler(func=lambda message: message.text in [
    "📢 اخبار گویم", "🌦 روز هفته و تاریخ", "🛍 دیوار گویم (آگهی)","🎉 سرگرمی و مسابقه",
    "😂 طنز و خاطرات", "⚽ ورزش و رویدادها", "🗳 نظرسنجی", "📞 خدمات و شماره‌های مهم",
    "📝 پروفایل من", "🏪 مغازه ها"
])
def handle_main_menu(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        send_welcome(message)
        return

    update_user_points(user_id)

    if message.text == "📢 اخبار گویم":
        show_admin_content(message.chat.id, "اخبار")
    elif message.text == "🌦 روز هفته و تاریخ":
        j_date = jdatetime.datetime.now()
        j_weekday = j_date.strftime('%A')
        j_day = convert_fa_numbers(j_date.strftime('%d'))
        j_month = j_date.strftime('%B')
        j_year = convert_fa_numbers(j_date.strftime('%Y'))
        
        formatted_date = f"امروز {j_day} {j_month} {j_year} - {j_weekday} است. امیدوارم روز خوبی رو داشته باشید. 🪽"
        bot.send_message(user_id, formatted_date, parse_mode='Markdown')
    elif message.text == "🛍 دیوار گویم (آگهی)":
        handle_divar(message)
    elif message.text == "🎉 سرگرمی و مسابقه":
        show_admin_content(message.chat.id, "مسابقات")
    elif message.text == "😂 طنز و خاطرات":
        handle_jokes(message)
    elif message.text == "⚽ ورزش و رویدادها":
        show_admin_content(message.chat.id, "ورزش")
    elif message.text == "🗳 نظرسنجی":
        bot.send_message(user_id, "در حال حاضر نظرسنجی فعالی وجود ندارد.")
    elif message.text == "📞 خدمات و شماره‌های مهم":
        show_admin_content(message.chat.id, "خدمات")
    elif message.text == "📝 پروفایل من":
        show_profile(message)
    elif message.text == "🏪 مغازه ها":
        show_shop_categories(message)

# --- Admin Content Management ---
def show_admin_content(chat_id, section):
    cursor.execute("SELECT content FROM admin_content WHERE section = ?", (section,))
    content = cursor.fetchone()
    if content:
        bot.send_message(chat_id, content[0], parse_mode='Markdown')
    else:
        bot.send_message(chat_id, f"در حال حاضر محتوایی برای بخش '{section}' ثبت نشده است.")

def show_admin_content_with_buttons(chat_id, section):
    cursor.execute("SELECT content FROM admin_content WHERE section = ?", (section,))
    content = cursor.fetchone()

    keyboard = types.InlineKeyboardMarkup()
    edit_btn = types.InlineKeyboardButton("✏️ ویرایش", callback_data=f"edit_admin_content_{section}")
    delete_btn = types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_admin_content_{section}")
    keyboard.add(edit_btn, delete_btn)

    if content:
        bot.send_message(chat_id, content[0], parse_mode='Markdown', reply_markup=keyboard)
    else:
        bot.send_message(chat_id, f"در حال حاضر محتوایی برای بخش '{section}' ثبت نشده است.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["✍️ مدیریت اخبار", "📝 مدیریت ورزش", "📞 مدیریت خدمات", "🎉 مدیریت مسابقات"] and message.from_user.id == ADMIN_ID)
def manage_admin_content_start(message):
    section_map = {
        "✍️ مدیریت اخبار": "اخبار",
        "📝 مدیریت ورزش": "ورزش",
        "📞 مدیریت خدمات": "خدمات",
        "🎉 مدیریت مسابقات": "مسابقات"
    }
    section = section_map.get(message.text)
    
    if section:
        show_admin_content_with_buttons(ADMIN_ID, section)
        bot.send_message(ADMIN_ID, "لطفاً برای تغییر محتوا، متن جدید را وارد کنید، یا از دکمه‌های بالا استفاده کنید.", reply_markup=get_admin_sub_menu_keyboard())
        user_states[ADMIN_ID] = f'awaiting_admin_content_{section}'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) and user_states.get(message.from_user.id).startswith('awaiting_admin_content_') and message.from_user.id == ADMIN_ID)
def save_admin_content(message):
    section = user_states.pop(message.from_user.id).split('_')[3]
    cursor.execute("INSERT OR REPLACE INTO admin_content (section, content) VALUES (?, ?)", (section, message.text))
    conn.commit()
    notify_all_users(section)  # Notify all users about the update
    bot.send_message(ADMIN_ID, f"محتوای بخش **{section}** با موفقیت به‌روزرسانی شد.", parse_mode='Markdown', reply_markup=get_admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_admin_content_') and call.from_user.id == ADMIN_ID)
def edit_admin_content_start(call):
    section = call.data.split('_')[3]
    user_states[ADMIN_ID] = f'awaiting_admin_content_{section}'
    bot.edit_message_text(f"لطفاً متن جدید بخش **{section}** را وارد کنید:", call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=None)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_admin_content_') and call.from_user.id == ADMIN_ID)
def delete_admin_content(call):
    section = call.data.split('_')[3]
    cursor.execute("DELETE FROM admin_content WHERE section = ?", (section,))
    conn.commit()
    try:
        bot.edit_message_text(f"محتوای بخش **{section}** با موفقیت حذف شد.", call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=None)
    except Exception as e:
        print(f"Error editing message: {e}")
    finally:
        bot.send_message(ADMIN_ID, "به پنل مدیریت بازگشتید.", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda message: message.text == "🗳 ایجاد نظرسنجی" and message.from_user.id == ADMIN_ID)
def create_poll_start(message):
    user_states[ADMIN_ID] = 'create_poll_q'
    bot.send_message(ADMIN_ID, "لطفاً متن سوال نظرسنجی را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'create_poll_q' and message.from_user.id == ADMIN_ID)
def create_poll_options(message):
    user_states[ADMIN_ID] = 'create_poll_a'
    user_states[f'poll_data_{ADMIN_ID}'] = {'question': message.text}
    bot.send_message(ADMIN_ID, "لطفاً گزینه‌های نظرسنجی را با کاما (,) از هم جدا کنید:\nمثال: گزینه ۱,گزینه ۲,گزینه ۳", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'create_poll_a' and message.from_user.id == ADMIN_ID)
def create_poll_publish(message):
    question = user_states.pop(f'poll_data_{ADMIN_ID}')['question']
    options = [opt.strip() for opt in message.text.split(',')]
    
    bot.send_poll(
        chat_id='@goyombot', # Replace with your channel ID
        question=question,
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False
    )
    
    del user_states[ADMIN_ID]
    bot.send_message(ADMIN_ID, "نظرسنجی با موفقیت ایجاد شد.", reply_markup=get_admin_keyboard())

# --- Admin Users Management ---
@bot.message_handler(func=lambda message: message.text == "👥 کاربران فعال" and message.from_user.id == ADMIN_ID)
def show_active_users(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("پسرها", "دخترها")
    keyboard.add("⬅️ بازگشت به پنل مدیریت")
    
    bot.send_message(ADMIN_ID, f"تعداد کاربران فعال: {convert_fa_numbers(str(total))}", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["پسرها", "دخترها"] and message.from_user.id == ADMIN_ID)
def list_users_by_gender(message):
    gender = "پسر" if message.text == "پسرها" else "دختر"
    cursor.execute("SELECT username, age, points FROM users WHERE gender = ?", (gender,))
    users = cursor.fetchall()
    
    if not users:
        bot.send_message(ADMIN_ID, f"هیچ کاربری با جنسیت '{gender}' وجود ندارد.")
        return
    
    for username, age, points in users:
        profile_info = (
            f"**نام مستعار:** {username}\n"
            f"**سن:** {convert_fa_numbers(str(age))} سال\n"
            f"**امتیاز:** {convert_fa_numbers(str(points))} ⭐\n\n"
        )
        bot.send_message(ADMIN_ID, profile_info, parse_mode='Markdown')

# --- Jokes Section ---
def handle_jokes(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("📜 لیست طنزها", "➕ افزودن طنز")
    keyboard.add("📄 طنزهای من", "بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "به بخش طنز و خاطرات خوش آمدید.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "📜 لیست طنزها")
def show_all_jokes(message):
    cursor.execute("SELECT id, joke_text FROM jokes")
    jokes = cursor.fetchall()
    
    if not jokes:
        bot.send_message(message.chat.id, "هیچ طنزی هنوز ثبت نشده است.")
        return
        
    for joke in jokes:
        joke_id, joke_text = joke
        bot.send_message(message.chat.id, f"**طنز شماره {convert_fa_numbers(str(joke_id))}**\n\n{joke_text}", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "➕ افزودن طنز")
def handle_add_joke(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_joke'
    bot.send_message(user_id, "لطفاً متن طنز یا خاطره خود را وارد کنید:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_joke')
def process_add_joke(message):
    user_id = message.from_user.id
    joke_text = message.text
    
    cursor.execute("INSERT INTO jokes (user_id, joke_text) VALUES (?, ?)", (user_id, joke_text))
    conn.commit()
    
    del user_states[user_id]
    bot.send_message(user_id, "طنز شما با موفقیت ثبت شد و به لیست اضافه گردید.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📄 طنزهای من")
def show_my_jokes(message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, joke_text FROM jokes WHERE user_id = ?", (user_id,))
    my_jokes = cursor.fetchall()
    
    if not my_jokes:
        bot.send_message(user_id, "شما هنوز طنزی ثبت نکرده‌اید.")
        return
    
    for joke_id, joke_text in my_jokes:
        keyboard = types.InlineKeyboardMarkup()
        edit_btn = types.InlineKeyboardButton("✏️ ویرایش", callback_data=f"edit_joke_{joke_id}")
        delete_btn = types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_joke_{joke_id}")
        keyboard.add(edit_btn, delete_btn)
        bot.send_message(user_id, f"**طنز شما (شماره {convert_fa_numbers(str(joke_id))})**\n\n{joke_text}", reply_markup=keyboard, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_joke_"))
def edit_joke_start(call):
    joke_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    user_states[user_id] = 'awaiting_new_joke'
    user_states[f'edit_joke_id_{user_id}'] = joke_id
    bot.send_message(user_id, "لطفاً متن جدید را برای طنز خود وارد کنید:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_new_joke')
def process_edit_joke(message):
    user_id = message.from_user.id
    joke_id = user_states.pop(f'edit_joke_id_{user_id}')
    new_text = message.text
    
    cursor.execute("UPDATE jokes SET joke_text = ? WHERE id = ? AND user_id = ?", (new_text, joke_id, user_id))
    conn.commit()
    
    del user_states[user_id]
    bot.send_message(user_id, "طنز شما با موفقیت به‌روزرسانی شد.", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_joke_"))
def delete_joke(call):
    joke_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    
    cursor.execute("DELETE FROM jokes WHERE id = ? AND user_id = ?", (joke_id, user_id))
    conn.commit()
    
    bot.send_message(user_id, "طنز شما با موفقیت حذف شد.", reply_markup=get_main_keyboard())

# --- Divar Section ---
def handle_divar(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add("🔎 مشاهده آگهی‌ها", "➕ افزودن آگهی")
    keyboard.add("📄 آگهی‌های من", "بازگشت به منو اصلی")
    bot.send_message(message.chat.id, "به دیوار گویم خوش آمدید.\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "🔎 مشاهده آگهی‌ها")
def show_ad_main_categories(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for main_cat in ad_categories.keys():
        keyboard.add(main_cat)
    keyboard.add("بازگشت به دیوار گویم")
    bot.send_message(message.chat.id, "لطفاً دسته‌بندی اصلی را انتخاب کنید:", reply_markup=keyboard)
    user_states[message.from_user.id] = 'awaiting_ad_main_cat_view'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_ad_main_cat_view' and message.text in ad_categories)
def show_ad_sub_categories_view(message):
    main_cat = message.text
    sub_cats = ad_categories[main_cat]
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for sub_cat in sub_cats:
        keyboard.add(sub_cat)
    keyboard.add("بازگشت به دسته‌های اصلی")
    bot.send_message(message.chat.id, f"دسته‌بندی '{main_cat}' انتخاب شد.\nلطفاً زیر دسته را انتخاب کنید:", reply_markup=keyboard)
    user_states[message.from_user.id] = f'awaiting_ad_sub_cat_view_{main_cat}'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) and user_states.get(message.from_user.id).startswith('awaiting_ad_sub_cat_view_'))
def show_ads_in_sub_cat(message):
    main_cat = user_states.pop(message.from_user.id).split('_')[-1]
    sub_cat = message.text
    cursor.execute("SELECT id, title FROM ads WHERE category_main = ? AND category_sub = ?", (main_cat, sub_cat))
    ads = cursor.fetchall()
    
    if not ads:
        bot.send_message(message.chat.id, f"هیچ آگهی‌ای در زیر دسته '{sub_cat}' وجود ندارد.")
        show_ad_main_categories(message)
        return
    
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for ad_id, title in ads:
        keyboard.add(title)
    keyboard.add("بازگشت به زیر دسته‌ها")
    
    bot.send_message(message.chat.id, f"آگهی‌های '{sub_cat}':", reply_markup=keyboard)
    user_states[message.from_user.id] = f'awaiting_ad_selection_{main_cat}_{sub_cat}'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) and user_states.get(message.from_user.id).startswith('awaiting_ad_selection_'))
def show_selected_ad(message):
    parts = user_states.get(message.from_user.id).split('_')
    main_cat = parts[2]
    sub_cat = parts[3]
    title = message.text
    cursor.execute("SELECT * FROM ads WHERE title = ? AND category_main = ? AND category_sub = ?", (title, main_cat, sub_cat))
    ad = cursor.fetchone()
    
    if ad:
        ad_id, user_id, title, description, category_main, category_sub, photo_id, contact = ad
        caption = (
            f"**عنوان:** {title}\n"
            f"**توضیحات:** {description}\n"
            f"**دسته بندی اصلی:** {category_main}\n"
            f"**زیر دسته:** {category_sub}\n"
            f"**تماس:** {contact}\n"
        )
        keyboard = types.InlineKeyboardMarkup()
        send_msg_btn = types.InlineKeyboardButton("ارسال پیام به آگهی‌دهنده", url=f"tg://user?id={user_id}")
        keyboard.add(send_msg_btn)
        bot.send_photo(message.chat.id, photo_id, caption=caption, parse_mode='Markdown', reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "آگهی مورد نظر پیدا نشد.")

@bot.message_handler(func=lambda message: message.text == "➕ افزودن آگهی")
def add_ad_main_categories(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for main_cat in ad_categories.keys():
        keyboard.add(main_cat)
    keyboard.add("بازگشت به دیوار گویم")
    bot.send_message(message.chat.id, "لطفاً دسته‌بندی اصلی را انتخاب کنید:", reply_markup=keyboard)
    user_states[message.from_user.id] = 'awaiting_ad_main_cat_add'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_ad_main_cat_add' and message.text in ad_categories)
def add_ad_sub_categories(message):
    main_cat = message.text
    sub_cats = ad_categories[main_cat]
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for sub_cat in sub_cats:
        keyboard.add(sub_cat)
    keyboard.add("بازگشت به دسته‌های اصلی")
    bot.send_message(message.chat.id, f"دسته‌بندی '{main_cat}' انتخاب شد.\nلطفاً زیر دسته را انتخاب کنید:", reply_markup=keyboard)
    user_states[message.from_user.id] = f'awaiting_ad_sub_cat_add_{main_cat}'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) and user_states.get(message.from_user.id).startswith('awaiting_ad_sub_cat_add_'))
def get_ad_title_add(message):
    main_cat = user_states.get(message.from_user.id).split('_')[-1]
    sub_cat = message.text
    user_states[message.from_user.id] = 'awaiting_ad_title'
    user_states[f'ad_data_{message.from_user.id}'] = {'category_main': main_cat, 'category_sub': sub_cat}
    bot.send_message(message.from_user.id, "لطفاً عنوان آگهی را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_ad_title')
def get_ad_description(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_ad_description'
    user_states[f'ad_data_{user_id}']['title'] = message.text
    bot.send_message(user_id, "لطفاً توضیحات آگهی را وارد کنید:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_ad_description')
def get_ad_contact(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_ad_contact'
    user_states[f'ad_data_{user_id}']['description'] = message.text
    bot.send_message(user_id, "لطفاً شماره تماس یا آیدی تلگرام خود را وارد کنید:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_ad_contact')
def get_ad_photo(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_ad_photo'
    user_states[f'ad_data_{user_id}']['contact'] = message.text
    bot.send_message(user_id, "لطفاً یک عکس برای آگهی ارسال کنید:")

@bot.message_handler(content_types=['photo'], func=lambda message: user_states.get(message.from_user.id) == 'awaiting_ad_photo')
def process_ad_photo(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    ad_data = user_states.pop(f'ad_data_{user_id}')
    
    cursor.execute("INSERT INTO ads (user_id, title, description, category_main, category_sub, photo_id, contact) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (user_id, ad_data['title'], ad_data['description'], ad_data['category_main'], ad_data['category_sub'], photo_id, ad_data['contact']))
    conn.commit()
    
    del user_states[user_id]
    
    bot.send_message(user_id, "آگهی شما با موفقیت ثبت شد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📄 آگهی‌های من")
def show_my_ads(message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, title, category_main, category_sub FROM ads WHERE user_id = ?", (user_id,))
    my_ads = cursor.fetchall()

    if not my_ads:
        bot.send_message(user_id, "شما هنوز آگهی‌ای ثبت نکرده‌اید.")
        return

    for ad_id, title, main_cat, sub_cat in my_ads:
        keyboard = types.InlineKeyboardMarkup()
        edit_btn = types.InlineKeyboardButton("✏️ ویرایش", callback_data=f"edit_ad_{ad_id}")
        delete_btn = types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_ad_{ad_id}")
        keyboard.add(edit_btn, delete_btn)
        bot.send_message(user_id, f"**آگهی شما (شماره {convert_fa_numbers(str(ad_id))})**\n\n**عنوان:** {title}\n**دسته اصلی:** {main_cat}\n**زیر دسته:** {sub_cat}", reply_markup=keyboard, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_ad_"))
def edit_ad_start(call):
    ad_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    user_states[user_id] = 'awaiting_new_ad_title'
    user_states[f'edit_ad_id_{user_id}'] = ad_id
    bot.send_message(user_id, "لطفاً عنوان جدید آگهی را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_new_ad_title')
def get_new_ad_title(message):
    user_id = message.from_user.id
    ad_id = user_states.pop(f'edit_ad_id_{user_id}')
    user_states[user_id] = 'awaiting_new_ad_description'
    user_states[f'new_ad_data_{user_id}'] = {'title': message.text, 'id': ad_id}
    bot.send_message(user_id, "لطفاً توضیحات جدید آگهی را وارد کنید:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_new_ad_description')
def get_new_ad_description(message):
    user_id = message.from_user.id
    ad_data = user_states.pop(f'new_ad_data_{user_id}')
    ad_id = ad_data['id']
    new_title = ad_data['title']
    new_description = message.text
    
    cursor.execute("UPDATE ads SET title = ?, description = ? WHERE id = ? AND user_id = ?", (new_title, new_description, ad_id, user_id))
    conn.commit()
    del user_states[user_id]
    
    bot.send_message(user_id, "آگهی شما با موفقیت به‌روزرسانی شد.", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_ad_"))
def delete_ad(call):
    ad_id = int(call.data.split('_')[2])
    cursor.execute("DELETE FROM ads WHERE id = ? AND user_id = ?", (ad_id, call.from_user.id))
    conn.commit()
    bot.send_message(call.from_user.id, "آگهی شما با موفقیت حذف شد.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ["بازگشت به دسته‌های اصلی", "بازگشت به زیر دسته‌ها", "بازگشت به دیوار گویم"])
def back_to_previous_divar(message):
    if message.text == "بازگشت به دسته‌های اصلی":
        show_ad_main_categories(message)
    elif message.text == "بازگشت به زیر دسته‌ها":
        # Extract main_cat from state if needed, but for simplicity, redirect to main
        show_ad_main_categories(message)
    elif message.text == "بازگشت به دیوار گویم":
        handle_divar(message)
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]

# --- Profile and Shops Section ---
def show_profile(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        _, username, age, gender, points = user_data
        
        gender_icon = "🧑" if gender == "پسر" else "👩" if gender == "دختر" else "👤"

        profile_info = (
            f"**{gender_icon} پروفایل من**\n\n"
            f"**اسم مستعار:** {username}\n"
            f"**سن:** {convert_fa_numbers(str(age))} سال\n"
            f"**جنسیت:** {gender}\n"
            f"**امتیاز:** {convert_fa_numbers(str(points))} ⭐\n\n"
        )
        
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        keyboard.add("ویرایش پروفایل", "گویمی‌های برتر ⭐", "بازگشت به منو اصلی")

        bot.send_message(user_id, profile_info, parse_mode='Markdown', reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "گویمی‌های برتر ⭐")
def show_top_users_from_keyboard(message):
    cursor.execute("SELECT username, age, gender, points FROM users WHERE points > 1000 ORDER BY points DESC")
    top_users = cursor.fetchall()
    
    if not top_users:
        bot.send_message(message.chat.id, "هنوز کسی به ۱۰۰۰ تا ستاره نرسیده است تو هم میتونی گویمی برتر بشی")
        return
        
    rankings_text = "✨ **گویمی‌های برتر (بالای ۱۰۰۰ امتیاز)** ✨\n\n"
    for i, user in enumerate(top_users, 1):
        username, age, gender, points = user
        rankings_text += f"{convert_fa_numbers(str(i))}. **{username}** - سن: {convert_fa_numbers(str(age))} - جنسیت: {gender} - امتیاز: {convert_fa_numbers(str(points))} ⭐\n"
    
    bot.send_message(message.chat.id, rankings_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "ویرایش پروفایل")
def edit_profile_menu(message):
    bot.send_message(message.chat.id, "چه چیزی را می‌خواهید ویرایش کنید؟", reply_markup=get_profile_edit_keyboard())

@bot.message_handler(func=lambda message: message.text == "تغییر اسم")
def change_username_start(message):
    user_states[message.from_user.id] = 'awaiting_new_username'
    bot.send_message(message.chat.id, "لطفاً اسم مستعار جدید خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_new_username')
def change_username_process(message):
    user_id = message.from_user.id
    new_username = message.text
    cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (new_username, user_id))
    conn.commit()
    del user_states[user_id]
    bot.send_message(user_id, f"نام مستعار شما با موفقیت به **{new_username}** تغییر یافت.", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    
@bot.message_handler(func=lambda message: message.text == "تغییر سن")
def change_age_start(message):
    user_states[message.from_user.id] = 'awaiting_new_age'
    keyboard = types.ReplyKeyboardMarkup(row_width=10, resize_keyboard=True)
    ages = [str(i) for i in range(13, 71)]
    keyboard.add(*ages)
    bot.send_message(message.chat.id, "لطفاً سن جدید خود را انتخاب کنید:", reply_markup=keyboard)
    
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_new_age')
def change_age_process(message):
    user_id = message.from_user.id
    try:
        new_age = int(message.text)
        if 13 <= new_age <= 70:
            cursor.execute("UPDATE users SET age = ? WHERE user_id = ?", (new_age, user_id))
            conn.commit()
            del user_states[user_id]
            bot.send_message(user_id, f"سن شما با موفقیت به **{convert_fa_numbers(str(new_age))}** تغییر یافت.", reply_markup=get_main_keyboard(), parse_mode='Markdown')
        else:
            bot.send_message(user_id, "لطفاً یک عدد بین 13 تا 70 وارد کنید.")
    except ValueError:
        bot.send_message(user_id, "لطفاً سن را به صورت عددی و فقط با استفاده از دکمه‌ها وارد کنید.")
        
@bot.message_handler(func=lambda message: message.text == "تغییر جنسیت")
def change_gender_start(message):
    user_states[message.from_user.id] = 'awaiting_new_gender'
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("پسر", "دختر")
    bot.send_message(message.chat.id, "لطفاً جنسیت جدید خود را انتخاب کنید:", reply_markup=keyboard)
    
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_new_gender')
def change_gender_process(message):
    user_id = message.from_user.id
    new_gender = message.text
    if new_gender in ["پسر", "دختر"]:
        cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (new_gender, user_id))
        conn.commit()
        del user_states[user_id]
        bot.send_message(user_id, f"جنسیت شما با موفقیت به **{new_gender}** تغییر یافت.", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    else:
        bot.send_message(user_id, "لطفاً از دکمه‌های زیر استفاده کنید.")

def show_shop_categories(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    categories = ["رستوران 🍽", "سوپری 🛒", "نانوایی 🥖", "پوشاکی 👕", "موبایل‌فروشی 📱", "میوه‌فروشی 🍎", "قنادی 🍰"]
    items = [types.KeyboardButton(cat) for cat in categories]
    add_shop_btn = types.KeyboardButton("➕ افزودن مکان")
    my_shops_btn = types.KeyboardButton("📄 مکان‌های من")
    keyboard.add(*items)
    keyboard.add(add_shop_btn, my_shops_btn)
    keyboard.add("بازگشت به منو اصلی")
    
    bot.send_message(message.chat.id, "دسته‌بندی‌ها:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["رستوران 🍽", "سوپری 🛒", "نانوایی 🥖", "پوشاکی 👕", "موبایل‌فروشی 📱", "میوه‌فروشی 🍎", "قنادی 🍰"])
def show_shops_by_category(message):
    category = message.text.split(' ')[0]
    
    cursor.execute("SELECT id, title FROM shops WHERE category = ?", (category,))
    shops = cursor.fetchall()
    
    if not shops:
        bot.send_message(message.chat.id, f"در حال حاضر هیچ مکان با دسته بندی {category} ثبت نشده است.")
        return
    
    for shop_id, title in shops:
        cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
        shop = cursor.fetchone()
        if shop:
            shop_id, title, description, address, category, photo_id, contact, _, _, _, _ = shop
            cursor.execute("SELECT rating FROM shop_ratings WHERE shop_id = ?", (shop_id,))
            ratings = cursor.fetchall()
            avg_rating = sum(r[0] for r in ratings) / len(ratings) if ratings else 0

            caption = (
                f"**عنوان:** {title}\n"
                f"**توضیحات:** {description}\n"
                f"**آدرس:** {address}\n"
                f"**دسته بندی:** {category}\n"
                f"**تماس:** {contact}\n\n"
                f"⭐️ **نمره کاربران:** {convert_fa_numbers(f'{avg_rating:.1f}')} از 10"
            )
            
            keyboard = types.InlineKeyboardMarkup()
            send_msg_btn = types.InlineKeyboardButton("ارسال پیام", url=f"tg://user?id={ADMIN_ID}")
            rate_btn = types.InlineKeyboardButton("⭐ امتیاز دادن", callback_data=f"rate_shop_{shop_id}")
            keyboard.add(send_msg_btn, rate_btn)
            
            bot.send_photo(message.chat.id, photo_id, caption=caption, parse_mode='Markdown', reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "➕ افزودن مکان")
def check_add_shop_permission(message):
    if message.from_user.id == ADMIN_ID:
        user_states[message.from_user.id] = 'awaiting_shop_title'
        bot.send_message(message.from_user.id, "لطفاً عنوان مکان (مغازه) را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.from_user.id, f"برای ثبت مکان باید با ادمین هماهنگ کنید: @Sedayegoyom10", reply_markup=get_main_keyboard())
    
@bot.message_handler(func=lambda message: message.text == "🏪 مدیریت مکان‌ها" and message.from_user.id == ADMIN_ID)
def manage_shops_start(message):
    cursor.execute("SELECT id, title FROM shops WHERE admin_id = ?", (ADMIN_ID,))
    shops = cursor.fetchall()

    if not shops:
        bot.send_message(ADMIN_ID, "شما هنوز مکانی ثبت نکرده‌اید.", reply_markup=get_admin_sub_menu_keyboard())
        return

    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    shop_buttons = [types.KeyboardButton(title) for _, title in shops]
    keyboard.add(*shop_buttons)
    keyboard.add("⬅️ بازگشت به پنل مدیریت")
    
    bot.send_message(ADMIN_ID, "مکان‌های ثبت‌شده توسط شما:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text in [title for _, title in cursor.execute("SELECT id, title FROM shops WHERE admin_id = ?", (ADMIN_ID,)).fetchall()])
def show_admin_shop_details(message):
    title = message.text
    cursor.execute("SELECT * FROM shops WHERE title = ? AND admin_id = ?", (title, ADMIN_ID,))
    shop = cursor.fetchone()
    
    if shop:
        shop_id, _, description, address, category, photo_id, contact, _, _, _, _ = shop
        caption = (
            f"**عنوان:** {title}\n"
            f"**توضیحات:** {description}\n"
            f"**آدرس:** {address}\n"
            f"**دسته بندی:** {category}\n"
            f"**تماس:** {contact}\n"
        )
        
        keyboard = types.InlineKeyboardMarkup()
        edit_btn = types.InlineKeyboardButton("✏️ ویرایش", callback_data=f"edit_shop_{shop_id}")
        delete_btn = types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_shop_{shop_id}")
        keyboard.add(edit_btn, delete_btn)
        
        bot.send_photo(ADMIN_ID, photo_id, caption=caption, parse_mode='Markdown', reply_markup=keyboard)
    else:
        bot.send_message(ADMIN_ID, "مکان مورد نظر پیدا نشد.")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_shop_title' and message.from_user.id == ADMIN_ID)
def get_shop_title(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_shop_description'
    user_states[f'shop_data_{user_id}'] = {'title': message.text}
    bot.send_message(user_id, "لطفاً توضیحات مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_shop_description' and message.from_user.id == ADMIN_ID)
def get_shop_description(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_shop_address'
    user_states[f'shop_data_{user_id}']['description'] = message.text
    bot.send_message(user_id, "لطفاً آدرس مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_shop_address' and message.from_user.id == ADMIN_ID)
def get_shop_address(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_shop_category'
    user_states[f'shop_data_{user_id}']['address'] = message.text
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("رستوران", "سوپری", "نانوایی", "پوشاکی", "موبایل‌فروشی", "میوه‌فروشی", "قنادی")
    bot.send_message(user_id, "لطفاً دسته بندی مکان را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_shop_category' and message.from_user.id == ADMIN_ID)
def get_shop_category(message):
    user_id = message.from_user.id
    category = message.text
    valid_categories = ["رستوران", "سوپری", "نانوایی", "پوشاکی", "موبایل‌فروشی", "میوه‌فروشی", "قنادی"]
    if category in valid_categories:
        user_states[user_id] = 'awaiting_shop_contact'
        user_states[f'shop_data_{user_id}']['category'] = category
        bot.send_message(user_id, "لطفاً شماره تماس مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())
    else:
        bot.send_message(user_id, "لطفاً از دکمه‌های زیر استفاده کنید.")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_shop_contact' and message.from_user.id == ADMIN_ID)
def get_shop_contact(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_seller_username'
    user_states[f'shop_data_{user_id}']['contact'] = message.text
    bot.send_message(user_id, "لطفاً اسم مستعار فروشنده را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_seller_username' and message.from_user.id == ADMIN_ID)
def get_seller_username(message):
    user_id = message.from_user.id
    user_states[user_id] = 'awaiting_seller_age'
    user_states[f'shop_data_{user_id}']['seller_username'] = message.text
    bot.send_message(user_id, "لطفاً سن فروشنده را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())
    
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_seller_age' and message.from_user.id == ADMIN_ID)
def get_seller_age(message):
    user_id = message.from_user.id
    try:
        age = int(message.text)
        user_states[user_id] = 'awaiting_seller_gender'
        user_states[f'shop_data_{user_id}']['seller_age'] = age
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
        markup.add("پسر", "دختر")
        bot.send_message(user_id, "لطفاً جنسیت فروشنده را وارد کنید:", reply_markup=markup)
    except ValueError:
        bot.send_message(user_id, "لطفاً سن را به صورت عددی وارد کنید.")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_seller_gender' and message.from_user.id == ADMIN_ID)
def get_seller_gender(message):
    user_id = message.from_user.id
    gender = message.text
    if gender in ["پسر", "دختر"]:
        user_states[user_id] = 'awaiting_shop_photo'
        user_states[f'shop_data_{user_id}']['seller_gender'] = gender
        bot.send_message(user_id, "لطفاً یک عکس برای مکان ارسال کنید:", reply_markup=get_admin_sub_menu_keyboard())
    else:
        bot.send_message(user_id, "لطفاً از دکمه‌ها استفاده کنید.")

@bot.message_handler(content_types=['photo'], func=lambda message: user_states.get(message.from_user.id) == 'awaiting_shop_photo' and message.from_user.id == ADMIN_ID)
def get_shop_photo(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    shop_data = user_states.pop(f'shop_data_{user_id}')
    
    cursor.execute("INSERT INTO shops (title, description, address, category, photo_id, contact, admin_id, seller_username, seller_age, seller_gender) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (shop_data['title'], shop_data['description'], shop_data['address'], shop_data['category'], photo_id, shop_data['contact'], user_id, shop_data['seller_username'], shop_data['seller_age'], shop_data['seller_gender']))
    conn.commit()
    
    del user_states[user_id]
    
    bot.send_message(user_id, "مکان جدید با موفقیت ثبت شد. 🥳", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda message: message.text == "📄 مکان‌های من")
def show_my_shops(message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, title FROM shops WHERE admin_id = ?", (user_id,))
    my_shops = cursor.fetchall()
    
    if not my_shops:
        bot.send_message(user_id, "شما هنوز مکانی ثبت نکرده‌اید.")
        return
    
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    shop_buttons = [types.KeyboardButton(title) for _, title in my_shops]
    keyboard.add(*shop_buttons)
    keyboard.add("بازگشت به منو اصلی")
    
    bot.send_message(user_id, "مکان‌های ثبت‌شده برای شما:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.from_user.id != ADMIN_ID and message.text in [title for _, title in cursor.execute("SELECT id, title FROM shops WHERE admin_id = ?", (message.from_user.id,)).fetchall()])
def show_user_shop_details(message):
    title = message.text
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM shops WHERE title = ? AND admin_id = ?", (title, user_id,))
    shop = cursor.fetchone()
    
    if shop:
        shop_id, _, description, address, category, photo_id, contact, _, _, _, _ = shop
        caption = (
            f"**عنوان:** {title}\n"
            f"**توضیحات:** {description}\n"
            f"**آدرس:** {address}\n"
            f"**دسته بندی:** {category}\n"
            f"**تماس:** {contact}\n"
        )
        
        bot.send_photo(user_id, photo_id, caption=caption, parse_mode='Markdown')
    else:
        bot.send_message(user_id, "مکان مورد نظر پیدا نشد.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_shop_") and call.from_user.id == ADMIN_ID)
def edit_shop_start(call):
    shop_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    user_states[user_id] = 'awaiting_new_shop_title'
    user_states[f'edit_shop_id_{user_id}'] = shop_id
    bot.send_message(user_id, "لطفاً عنوان جدید مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_new_shop_title' and message.from_user.id == ADMIN_ID)
def get_new_shop_title(message):
    user_id = message.from_user.id
    shop_id = user_states.pop(f'edit_shop_id_{user_id}')
    user_states[user_id] = 'awaiting_new_shop_description'
    user_states[f'new_shop_data_{user_id}'] = {'title': message.text, 'id': shop_id}
    bot.send_message(user_id, "لطفاً توضیحات جدید مکان را وارد کنید:", reply_markup=get_admin_sub_menu_keyboard())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_new_shop_description' and message.from_user.id == ADMIN_ID)
def get_new_shop_description(message):
    user_id = message.from_user.id
    shop_data = user_states.pop(f'new_shop_data_{user_id}')
    shop_id = shop_data['id']
    new_title = shop_data['title']
    new_description = message.text
    
    cursor.execute("UPDATE shops SET title = ?, description = ? WHERE id = ? AND admin_id = ?", (new_title, new_description, shop_id, user_id))
    conn.commit()
    del user_states[user_id]
    
    bot.send_message(user_id, "مکان شما با موفقیت به‌روزرسانی شد.", reply_markup=get_admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_shop_") and call.from_user.id == ADMIN_ID)
def delete_shop(call):
    shop_id = int(call.data.split('_')[2])
    cursor.execute("DELETE FROM shops WHERE id = ? AND admin_id = ?", (shop_id, call.from_user.id))
    conn.commit()
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.from_user.id, "مکان شما با موفقیت حذف شد.", reply_markup=get_admin_keyboard())
    except Exception as e:
        print(f"Error deleting message: {e}")
        bot.send_message(call.from_user.id, "مکان شما با موفقیت حذف شد.", reply_markup=get_admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_shop_"))
def handle_rate_shop(call):
    shop_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    
    user_states[user_id] = 'awaiting_rating'
    user_states[f'rating_data_{user_id}'] = {'shop_id': shop_id}
    
    keyboard = types.ReplyKeyboardMarkup(row_width=5, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*[str(i) for i in range(11)])
    
    bot.send_message(user_id, "لطفاً از 0 تا 10 به این مکان امتیاز دهید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_rating')
def process_rating(message):
    user_id = message.from_user.id
    try:
        rating = int(message.text)
        if 0 <= rating <= 10:
            shop_data = user_states.get(f'rating_data_{user_id}')
            if not shop_data:
                bot.send_message(user_id, "خطایی رخ داد. لطفاً دوباره تلاش کنید.", reply_markup=get_main_keyboard())
                return
            
            shop_id = shop_data['shop_id']
            
            cursor.execute("INSERT OR REPLACE INTO shop_ratings (shop_id, user_id, rating) VALUES (?, ?, ?)", (shop_id, user_id, rating))
            conn.commit()
            
            del user_states[user_id]
            del user_states[f'rating_data_{user_id}']

            bot.send_message(user_id, "امتیاز شما ثبت شد! از همکاری شما سپاسگزاریم. ❤️", reply_markup=get_main_keyboard())
            
            cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
            shop = cursor.fetchone()
            if shop:
                shop_id, title, description, address, category, photo_id, contact, _, _, _, _ = shop
                cursor.execute("SELECT rating FROM shop_ratings WHERE shop_id = ?", (shop_id,))
                ratings = cursor.fetchall()
                avg_rating = sum(r[0] for r in ratings) / len(ratings) if ratings else 0

                caption = (
                    f"**عنوان:** {title}\n"
                    f"**توضیحات:** {description}\n"
                    f"**آدرس:** {address}\n"
                    f"**دسته بندی:** {category}\n"
                    f"**تماس:** {contact}\n\n"
                    f"⭐️ **نمره کاربران:** {convert_fa_numbers(f'{avg_rating:.1f}')} از 10"
                )
                
                keyboard = types.InlineKeyboardMarkup()
                send_msg_btn = types.InlineKeyboardButton("ارسال پیام", url=f"tg://user?id={ADMIN_ID}")
                rate_btn = types.InlineKeyboardButton("⭐ امتیاز دادن", callback_data=f"rate_shop_{shop_id}")
                keyboard.add(send_msg_btn, rate_btn)
                
                bot.send_photo(user_id, photo_id, caption=caption, parse_mode='Markdown', reply_markup=keyboard)
        else:
            bot.send_message(user_id, "لطفاً یک عدد بین 0 تا 10 وارد کنید.")
    except (ValueError, KeyError):
        bot.send_message(user_id, "خطایی رخ داد. لطفاً یک عدد وارد کنید یا مجدداً تلاش کنید.", reply_markup=get_main_keyboard())
        if user_id in user_states: del user_states[user_id]
        if f'rating_data_{user_id}' in user_states: del user_states[f'rating_data_{user_id}']

@bot.message_handler(func=lambda message: message.text == "بازگشت به منو اصلی")
def go_back_to_main_menu(message):
    bot.send_message(message.chat.id, "به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        if user_id not in user_states:
            bot.send_message(user_id, "منظور شما را متوجه نشدم. لطفاً از دکمه‌ها استفاده کنید.", reply_markup=get_main_keyboard())
    else:
        send_welcome(message)

bot.infinity_polling()