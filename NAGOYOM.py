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
    "user": "👤",
    "score": "🏆",
    "add_score": "⬆️",
    "remove_score": "⬇️",
    "message": "💬",
    "comments": "💭",
    "block": "🚫",
    "unblock": "🔓",
    "reply": "↩️",
    "send": "📤"
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
message_blocks = {}  # ذخیره اطلاعات بلاک کردن کاربران برای پیام‌رسانی

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
                 rating_count INTEGER DEFAULT 0,
                 is_top_rated INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS place_ratings (
                 place_id INTEGER,
                 user_id INTEGER,
                 rating INTEGER,
                 PRIMARY KEY (place_id, user_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS place_comments (
                 comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 place_id INTEGER,
                 user_id INTEGER,
                 comment TEXT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS news (
                 news_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                 message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 sender_id INTEGER,
                 receiver_id INTEGER,
                 place_id INTEGER,
                 message_text TEXT,
                 message_type TEXT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_blocks (
                 block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 blocker_id INTEGER,
                 blocked_id INTEGER,
                 place_id INTEGER,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    try:
        c.execute("ALTER TABLE places ADD COLUMN subcategory TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE places ADD COLUMN is_top_rated INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

# دسته‌بندی مکان‌ها
PLACE_CATEGORIES = {
    "🍽️ خوراکی و نوشیدنی": [
        "رستوران‌ها (سنتی، فست فود، بین‌المللی، دریایی، گیاهخواری)",
        "کافه و کافی‌شاپ (کافه‌رستوران، قهوه تخصصی)",
        "بستنی‌فروشی و آبمیوه‌فروشی (بستنی سنتی، بستنی ایتالیایی)",
        "شیرینی‌پزی و نانوایی (نانوایی سنتی، شیرینی‌پزی قنادی)",
        "سفره‌خانه و چایخانه (قهوه خانه سنتی، چایخانه مدرن)",
        "فودکورت و مراکز غذاخوری",
        "کبابی و جگرکی (کباب‌فروشی، جگرکی، دیزی‌سرا)",
        "ساندویچ‌فروشی و پیتزافروشی (پیتزافروشی، ساندویچ‌فروشی محلی)",
        "قنادی و شکلات‌فروشی (شکلات‌فروشی تخصصی، آبنبات‌فروشی)",
        "آجیل‌فروشی و خشکبار (آجیل‌فروشی، خشکبارفروشی)",
        "سوپرمارکت محلی و هایپر",
        "قصابی و مرغ فروشی (قصابی، مرغ‌فروشی، ماهی‌فروشی)",
        "میوه‌فروشی و تره‌بار (میوه‌فروشی، سبزی‌فروشی)",
        "ماهی‌فروشی و غذاهای دریایی",
        "فروشگاه مواد غذایی محلی",
        "عسل‌فروشی و محصولات زنبورداری",
        "محصولات محلی و منطقه‌ای",
        "فروشگاه محصولات ارگانیک",
        "فروشگاه مواد غذایی منجمد",
        "فروشگاه محصولات لبنی و پنیر",
        "نان‌فروشی تخصصی (نان باگت، نان سنگک)",
        "غذاهای محلی و غذاهای قومی"
    ],
    "🛍️ خرید و فروش": [
        "پاساژها و مراکز خرید (مال، مرکز خرید، بازارچه)",
        "سوپرمارکت و هایپرمارکت (زنجیره‌ای، محلی)",
        "فروشگاه زنجیره‌ای",
        "بازار سنتی و بازارچه‌های محلی (بازار روز، بازار هفتگی)",
        "فروشگاه پوشاک و کیف و کفش (لباس مردانه، زنانه، بچگانه)",
        "فروشگاه لوازم خانگی و الکترونیک (لوازم برقی، دیجیتال)",
        "فروشگاه لوازم ورزشی (ورزشی، کوهنوردی، شنا)",
        "کتاب‌فروشی و لوازم التحریر (کتاب‌فروشی عمومی، تخصصی)",
        "مغازه موبایل و لپ‌تاپ (فروش، تعمیر، لوازم جانبی)",
        "گل‌فروشی و گیاهان آپارتمانی (گل‌فروشی، گل‌آرایی)",
        "عینک‌فروشی و اپتیک (عینک‌فروشی، عینک‌سازی)",
        "عطر و ادکلن فروشی (عطر فروشی، محصولات آرایشی)",
        "طلا و جواهر فروشی (طلافروشی، جواهرفروشی)",
        "ساعت‌فروشی (ساعت مچی، دیواری)",
        "لوازم آرایشی و بهداشتی (آرایشی، بهداشتی، مراقبت پوست)",
        "اسباب‌بازی‌فروشی (اسباب‌بازی، بازی فکری)",
        "صنایع‌دستی و سوغاتی‌فروشی (صنایع دستی، سوغات)",
        "دکوراسیون و لوازم منزل (دکوراسیون، لوازم تزئینی)",
        "فرش و گلیم فروشی (فرش‌فروشی، گلیم‌فروشی)",
        "پارچه‌فروشی و خیاطی (پارچه‌فروشی، خیاطی)",
        "چرم‌فروشی و کیف‌سازی (چرم‌فروشی، کیف‌دوزی)",
        "فروشگاه لوازم آشپزخانه (ظروف، لوازم آشپزی)",
        "فروشگاه لوازم باغبانی (لوازم باغبانی، نهال)",
        "فروشگاه حیوانات خانگی (حیوانات، غذای حیوانات)",
        "فروشگاه دوچرخه و اسکوتر (دوچرخه، اسکوتر، لوازم)",
        "فروشگاه ابزارآلات (ابزار صنعتی، دستی)",
        "فروشگاه کامپیوتر و گیم (کامپیوتر، کنسول بازی)",
        "فروشگاه لباس عروس و مراسم",
        "فروشگاه کادو و هدیه",
        "فروشگاه محصولات فرهنگی (سی دی، دی وی دی، آثار هنری)",
        "فروشگاه محصولات دست‌دوم",
        "فروشگاه محصولات سلامت و تندرستی",
        "فروشگاه محصولات روستایی و محلی"
    ],
    "✂️ زیبایی و آرایشی": [
        "آرایشگاه مردانه (آرایشگاه، اصلاح)",
        "آرایشگاه زنانه (آرایش، رنگ مو)",
        "سالن‌های زیبایی و اسپا (اسپا، ماساژ)",
        "مژه و ابرو (اکستنشن مژه، میکروبلیدینگ)",
        "ناخن‌کاری (مانیکور، پدیکور، ناخن مصنوعی)",
        "تتو و میکروپیگمنتیشن (تاتو، میکروپیگمنتیشن)",
        "سالن‌های تاتو و پیرسینگ (پیرسینگ، تاتو حنایی)",
        "مراکز خدمات پوست و مو (پاکسازی پوست، لیزر)",
        "فروشگاه لوازم آرایشی حرفه‌ای",
        "مراکز ماساژ و ریلکسیشن (ماساژ درمانی، ریلکسیشن)",
        "مراکز اپیلاسیون و لیزر",
        "سالن‌های برنزه کردن",
        "مراکز مشاوره زیبایی",
        "آموزشگاه‌های آرایشگری",
        "مراکز خدمات بهداشتی مردانه"
    ],
    "🏥 درمان و سلامت": [
        "بیمارستان و مراکز درمانی (عمومی، تخصصی، خصوصی)",
        "درمانگاه و کلینیک‌های تخصصی (خانواده، زنان، قلب)",
        "داروخانه (شبانه‌روزی، گیاهی)",
        "دندان‌پزشکی و ارتودنسی (عمومی، تخصصی، زیبایی)",
        "آزمایشگاه پزشکی و رادیولوژی (آزمایشگاه، سونوگرافی)",
        "کلینیک زیبایی و لیزر (لیزر، بوتاکس، ژل)",
        "مراکز فیزیوتراپی و کاردرمانی (فیزیوتراپی، کاردرمانی)",
        "دامپزشکی و کلینیک حیوانات (دامپزشکی، حیوانات خانگی)",
        "مراکز توانبخشی (توانبخشی، گفتاردرمانی)",
        "مراکز مشاوره و روانشناسی (مشاوره، روانشناسی)",
        "شنوایی‌سنجی و سمعک (سمعک، شنوایی‌سنجی)",
        "بینایی‌سنجی و عینک‌سازی (بینایی‌سنجی، عینک‌سازی)",
        "پرستاری در منزل (پرستار، پزشک در منزل)",
        "تجهیزات پزشکی (فروش، اجاره)",
        "مراکز اهدای خون",
        "مراکز طب سنتی و گیاهان دارویی",
        "مراکز ماساژ درمانی",
        "مراکز ترک اعتیاد",
        "مراکز خدمات پرستاری",
        "مراکز خدمات پزشکی سیار",
        "مراکز تصویربرداری پزشکی",
        "مراکز خدمات پزشکی ورزشی"
    ],
    "⚽ ورزش و سرگرمی": [
        "باشگاه ورزشی و بدنسازی (بدنسازی، کراسفیت)",
        "استخر و مجموعه ورزشی (استخر، سونا، جکوزی)",
        "سالن فوتسال و بسکتبال (فوتسال، بسکتبال، والیبال)",
        "سینما و تئاتر (سینما، تئاتر، نمایش)",
        "شهربازی و پارک بازی (شهربازی، پارک بازی)",
        "بیلیارد و بولینング (بیلیارد، بولینگ، دارت)",
        "مراکز تفریحی خانوادگی (تفریحی، بازی)",
        "مراکز فرهنگی و هنری (فرهنگی، هنری)",
        "سالن‌های کنسرت و نمایش (کنسرت، نمایش)",
        "گیم‌نت و مراکز بازی (گیم‌نت، بازی کامپیوتری)",
        "باشگاه تیراندازی (تیراندازی، کمان‌اندازی)",
        "باشگاه سینما و خانه فیلم",
        "مراکز آموزشی موسیقی (آموزش موسیقی، نوازندگی)",
        "کتابخانه عمومی (عمومی، تخصصی)",
        "نگارخانه و نمایشگاه هنری (نگارخانه، نمایشگاه)",
        "مراکز بازی اتاق فرار",
        "مراکز پینت بال و لیزرتگ",
        "باشگاه‌های رقص و باله",
        "مراکز یوга و مدیتیشن",
        "باشگاه‌های ورزش‌های رزمی",
        "مراکز اسکیت و رولر",
        "باشگاه‌های بوکس و هنرهای رزمی ترکیبی",
        "مراکز ورزش‌های آبی",
        "باشگاه‌های گلف و تنیس",
        "مراکز ماهیگیری و شکار",
        "باشگاه‌های سوارکاری"
    ],
    "🏨 اقامت و سفر": [
        "هتل و هتل آپارتمان (هتل، هتل آپارتمان)",
        "مسافرخانه و مهمانپذیر (مسافرخانه، مهمانپذیر)",
        "اقامتگاه بوم‌گردی (بوم‌گردی، اقامتگاه محلی)",
        "ویلا و سوئیت اجاره‌ای (ویلا، سوئیت)",
        "کمپینگ و اردوگاه (کمپینگ، اردوگاه)",
        "آژانس مسافرتی و گردشگری (مسافرتی، گردشگری)",
        "ایستگاه قطار و اتوبوس (قطار، اتوبوس)",
        "فرودگاه و پایانه مسافری (فرودگاه، پایانه)",
        "مراکز رزرواسیون (رزرو هتل، بلیط)",
        "خدمات ویزا و پاسپورت (ویزا، پاسپورت)",
        "اجاره خودرو و دوچرخه (اجاره ماشین، دوچرخه)",
        "راهنمایان گردشگری (تورلیدر، راهنما)",
        "مراکز اطلاعات گردشگری",
        "خدمات ترجمه و راهنمای محلی",
        "مراکز کرایه اتومبیل",
        "خدمات انتقال مسافر (حمل و نقل، ترانسفر)",
        "مراکز رزرواسیون آنلاین",
        "خدمات بیمه مسافرتی",
        "مراکز خدمات جهانگردی"
    ],
    "🏛️ خدمات عمومی و اداری": [
        "بانک و خودپرداز (بانک، صرافی)",
        "اداره پست (پست، پیک موتوری)",
        "دفاتر پیشخوان خدمات دولت (پیشخوان، خدمات الکترونیک)",
        "شهرداری و مراکز خدمات شهری (شهرداری، خدمات شهری)",
        "اداره برق، آب، گاز (برق، آب، گاز)",
        "پلیس +۱۰ و مراکز انتظامی (پلیس، انتظامی)",
        "دادگاه و مراجع قضایی (دادگاه، قضایی)",
        "کلانتری و پاسگاه (کلانتری، پاسگاه)",
        "دفاتر اسناد رسمی (اسناد رسمی، دفترخانه)",
        "مراکز صدور گواهینامه (گواهینامه، مدارک)",
        "ادارات دولتی و وزارتخانه‌ها (دولتی، وزارتخانه)",
        "کنسولگری و سفارتخانه‌ها (سفارت، کنسولگری)",
        "مراکز خدمات الکترونیک (خدمات آنلاین، دولت الکترونیک)",
        "مراکز خدمات مشاوره شغلی",
        "دفاتر خدمات مسکن و املاک",
        "مراکز خدمات حقوقی و قضایی",
        "دفاتر خدمات مهاجرتی",
        "مراکز خدمات مالی و حسابداری",
        "دفاتر خدمات بیمه‌ای",
        "مراکز خدمات تعمیرات شهری",
        "دفاتر خدمات پیمانکاری"
    ],
    "🚗 خدمات شهری و حمل‌ونقل": [
        "پمپ بنزین و CNG (بنزین، گاز)",
        "کارواش و خدمات خودرو (کارواش، براق‌سازی)",
        "تعمیرگاه خودرو و موتورسیکلت (تعمیرگاه، مکانیکی)",
        "تاکسی‌سرویس و تاکسی اینترنتی (تاکسی، اسنپ)",
        "پارکینگ عمومی (پارکینگ، جای پارک)",
        "مکانیکی و برق خودرو (مکانیک، برق خودرو)",
        "لاستیک‌فروشی و فروش لوازم یدکی (لاستیک، لوازم یدکی)",
        "خدمات نقاشی و ترمیم خودرو (نقاشی، ترمیم)",
        "مراکز معاینه فنی (معاینه فنی، تست خودرو)",
        "خدمات امداد خودرو (خدمات امدادی، یدک‌کش)",
        "نمایندگی خودرو (نمایندگی، فروش خودرو)",
        "فروشگاه لوازم جانبی خودرو (لوازم جانبی، تزئینات)",
        "خدمات تنظیم موتور و انژکتور",
        "خدمات صافکاری و جلوبندی",
        "خدمات تعویض روغن و فیلتر",
        "خدمات سیستم تهویه و کولر",
        "خدمات تعمیرات تخصصی خودرو",
        "خدمات کارت‌خوان و پرداخت",
        "خدمات پخش محصولات خودرویی",
        "خدمات حمل و نقل معلولین و سالمندان"
    ],
    "📚 آموزش و فرهنگ": [
        "مدرسه و آموزشگاه (دبستان، دبیرستان)",
        "دانشگاه و مراکز آموزش عالی (دانشگاه، موسسه آموزش عالی)",
        "آموزشگاه زبان (زبان انگلیسی، سایر زبان‌ها)",
        "آموزشگاه فنی‌وحرفه‌ای (فنی، حرفه‌ای)",
        "کتابخانه عمومی (عمومی، تخصصی)",
        "فرهنگسرا و خانه فرهنگ (فرهنگسرا، خانه فرهنگ)",
        "موزه و گالری (موزه، گالری هنری)",
        "مراکز آموزشی کامپیوتر (کامپیوتر، برنامه‌نویسی)",
        "مراکز مشاوره تحصیلی (مشاوره، انتخاب رشته)",
        "آموزشگاه‌های هنری (نقاشی، مجسمه‌سازی)",
        "مراکز آموزشی رانندگی (آموزش رانندگی، آیین‌نامه)",
        "مهدکودک و پیش‌دبستانی (مهدکودک، پیش‌دبستانی)",
        "مراکز آموزش علوم مختلف (ریاضی، فیزیک، شیمی)",
        "مراکز آموزش مهارت‌های زندگی",
        "آموزشگاه‌های آشپزی و شیرینی‌پزی",
        "مراکز آموزش خلاقیت کودکان",
        "آموزشگاه‌های کنکور و آزمون",
        "مراکز آموزش از راه دور",
        "آموزشگاه‌های مهارت‌آموزی",
        "مراکز آموزش صنایع دستی",
        "آموزشگاه‌های خیاطی و طراحی لباس",
        "مراکز آموزش عکاسی و فیلمبرداری",
        "آموزشگاه‌های ورزشی تخصصی",
        "مراکز آموزش موسیقی محلی",
        "آموزشگاه‌های زبان اشاره",
        "خدمات آموزش مجازی و آنلاین"
    ],
    "🕌 مذهبی و معنوی": [
        "مسجد و مصلی (مسجد، مصلی)",
        "حسینیه و هیئت (حسینیه، هیئت)",
        "کلیسا و مراکز مسیحی (کلیسا، مراکز مسیحی)",
        "کنیسه و مراکز یهودی (کنیسه، مراکز یهودی)",
        "معابد و پرستشگاه‌ها (معبد، پرستشگاه)",
        "مراکز عرفانی و معنوی (عرفانی، معنوی)",
        "کتابفروشی‌های مذهبی (کتاب مذهبی، نرم افزار مذهبی)",
        "مراکز خیریه و نیکوکاری (خیریه، نیکوکاری)",
        "انتشارات مذهبی (انتشارات، چاپ مذهبی)",
        "مراکز حفظ قرآن و معارف اسلامی",
        "مراکز خدمات حج و زیارت",
        "مراکز مشاوره مذهبی و دینی",
        "مراکز آموزش احکام و معارف",
        "مراکز خدمات اوقاف و امور خیریه",
        "مراکز خدمات مذهبی سیار",
        "مراکز برگزاری مراسم مذهبی"
    ],
    "🌳 طبیعت و تفریح آزاد": [
        "پارک و بوستان (پارک عمومی، بوستان)",
        "باغ وحش و آکواریوم (باغ وحش، آکواریوم)",
        "باغ گیاه‌شناسی (گیاه‌شناسی، گلخانه)",
        "پیست دوچرخه‌سواری (دوچرخه‌سواری، دوچرخه سواری آفرود)",
        "کوهستان و مسیرهای طبیعت‌گردی (کوهنوردی، طبیعت‌گردی)",
        "ساحل و دریاچه (ساحل، دریاچه)",
        "آبشار و چشمه (آبشار، چشمه)",
        "جنگل و منطقه حفاظت شده (جنگل، منطقه حفاظت شده)",
        "کمپینگ و پیکنیک (کمپینگ، پیکنیک)",
        "مراکز اکوتوریسم (اکوتوریسم، گردشگری طبیعت)",
        "پیست اسکی و ورزش‌های زمستانی (اسکی، ورزش زمستانی)",
        "سالن‌های بولدرینگ و صخره‌نوردی (صخره‌نوردی، بولدرینگ)",
        "مراکز ماهیگیری و قایق‌رانی",
        "پارک‌های آبی و استخرهای روباز",
        "مراکز پرنده‌نگری و حیات وحش",
        "مسیرهای پیاده‌روی و کوهپیمایی",
        "مراکز چادرزنی و کاروانینگ",
        "پارک‌های ملی و مناطق گردشگری",
        "مراکز آموزش طبیعت‌گردی",
        "مراکز خدمات تورهای طبیعت"
    ],
    "💼 کسب‌وکار و حرفه‌ای": [
        "دفتر کار و شرکت‌ها (دفter، شرکت)",
        "کارخانه‌ها و واحدهای تولیدی (کارخانه، تولیدی)",
        "کارگاه‌های صنعتی (کارگاه، صنعتی)",
        "دفاتر املاک و مشاورین املاک (املاک، مشاور املاک)",
        "دفاتر بیمه (بیمه، خدمات بیمه‌ای)",
        "شرکت‌های تبلیغاتی و بازاریابی (تبلیغات، بازاریابی)",
        "مراکز طراحی و چاپ (طراحی، چاپ)",
        "شرکت‌های معماری و عمران (معماری، عمران)",
        "دفاتر حقوقی و وکالت (حقوقی، وکالت)",
        "شرکت‌های مشاوره مدیریت (مشاوره، مدیریت)",
        "مراکز خدمات مالی و حسابداری (مالی، حسابداری)",
        "شرکت‌های فناوری اطلاعات (فناوری اطلاعات، نرم‌افزار)",
        "استودیوهای عکاسی و فیلمبرداری (عکاسی، فیلمبرداری)",
        "مراکز خدمات اداری و کپی (خدمات اداری، کپی)",
        "شرکت‌های حمل و نقل و باربری (حمل نقل، باربری)",
        "خدمات نظافتی و نگهداری (نظافتی، نگهداری)",
        "شرکت‌های رسانه‌ای و انتشاراتی",
        "مراکز تحقیقاتی و توسعه",
        "شرکت‌های مشاوره منابع انسانی",
        "مراکز خدمات مشاوره کسب‌وکار",
        "شرکت‌های طراحی سایت و بهینه‌سازی موتور جستجو",
        "مراکز خدمات ترجمه و مترجم",
        "شرکت‌های خدمات امنیتی",
        "مراکز خدمات پشتیبانی فناوری اطلاعات",
        "شرکت‌های خدمات مشاوره مالیاتی",
        "مراکز خدمات برندینگ و هویت سازی",
        "خدمات مشاوره انرژی و بهینه‌سازی"
    ],
    "🧰 خدمات تخصصی و فنی": [
        "تعمیرگاه لوازم خانگی (تعمیر لوازم، سرویس)",
        "تعمیرگاه موبایل و کامپیوتر (تعمیر موبایل، کامپیوتر)",
        "خدمات برق ساختمان (برق‌کاری، سیم‌کشی)",
        "خدمات لوله‌کشی و تاسیسات (لوله‌کشی، تاسیسات)",
        "خدمات نقاشی ساختمان (نقاشی ساختمان، رنگ‌کاری)",
        "خدمات کابینت سازی و نجاری (کابینت‌سازی، نجاری)",
        "خدمات آهنگری و جوشکاری (آهنگری، جوشکاری)",
        "خدمات کلیدسازی و قفل‌سازی (کلیدسازی، قفل‌سازی)",
        "خدمات شیشه‌بری و آینه‌کاری (شیشه‌بری، آینه‌کاری)",
        "خدمات فرش شویی و مبل شویی (فرش‌شویی، مبل‌شویی)",
        "خدمات نظافت منزل و اداره (نظافت، خدمات نظافتی)",
        "خدمات باغبانی و فضای سبز (باغبانی، فضای سبز)",
        "خدمات حشره‌کشی و ضدعفونی (ضدعفونی، سمپاشی)",
        "خدمات امنیتی و نگهبانی (امنیتی، نگهبانی)",
        "خدمات تعمیرات لوازم الکترونیکی",
        "خدمات نصب و راه‌اندازی تجهیزات",
        "خدمات سیم‌کشی شبکه و اینترنت",
        "خدمات تعمیرات صنعتی و ماشین‌آلات",
        "خدمات نصب دوربین و سیستم‌های حفاظتی",
        "خدمات تعمیرات لوازم آشپزخانه",
        "خدمات نصب کفپوش و سقف کاذب",
        "خدمات تعمیرات ابزارآلات دقیق",
        "خدمات نصب آسانسور و پله برقی",
        "خدمات تعمیرات سیستم‌های سرمایشی و گرمایشی",
        "خدمات نصب سیستم‌های اعلام حریق",
        "خدمات تعمیرات ادوات موسیقی",
        "خدمات نصب دیش و سیستم‌های ماهواره‌ای",
        "خدمات تعمیرات لوازم پزشکی",
        "خدمات نصب سیستم‌های هوشمند ساختمان",
        "خدمات بازیافت و محیط زیست",
        "خدمات اجاره تجهیزات و لوازم (مانند اجاره چادر، لباس مراسم، تجهیزات فنی)"
    ]
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

def is_user_blocked_for_messaging(blocker_id, blocked_id, place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM user_blocks WHERE blocker_id = ? AND blocked_id = ? AND place_id = ?", 
              (blocker_id, blocked_id, place_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def block_user_for_messaging(blocker_id, blocked_id, place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO user_blocks (blocker_id, blocked_id, place_id) VALUES (?, ?, ?)",
              (blocker_id, blocked_id, place_id))
    conn.commit()
    conn.close()

def unblock_user_for_messaging(blocker_id, blocked_id, place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM user_blocks WHERE blocker_id = ? AND blocked_id = ? AND place_id = ?",
              (blocker_id, blocked_id, place_id))
    conn.commit()
    conn.close()

def get_place_owner_id(place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM places WHERE place_id = ?", (place_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_place_by_id(place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM places WHERE place_id = ?", (place_id,))
    place = c.fetchone()
    conn.close()
    return place

def add_comment_to_place(place_id, user_id, comment):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO place_comments (place_id, user_id, comment) VALUES (?, ?, ?)",
              (place_id, user_id, comment))
    conn.commit()
    conn.close()

def get_comments_for_place(place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT pc.comment_id, pc.user_id, pc.comment, pc.timestamp, u.name, u.age, u.gender, u.numeric_id
        FROM place_comments pc
        JOIN users u ON pc.user_id = u.user_id
        WHERE pc.place_id = ?
        ORDER BY pc.timestamp DESC
    """, (place_id,))
    comments = c.fetchall()
    conn.close()
    return comments

def delete_comment(comment_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM place_comments WHERE comment_id = ?", (comment_id,))
    conn.commit()
    conn.close()

def send_message_to_user(sender_id, receiver_id, place_id, message_text, message_type="text"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender_id, receiver_id, place_id, message_text, message_type) VALUES (?, ?, ?, ?, ?)",
              (sender_id, receiver_id, place_id, message_text, message_type))
    conn.commit()
    conn.close()

def get_messages_between_users(user1_id, user2_id, place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT m.*, u1.name as sender_name, u2.name as receiver_name
        FROM messages m
        JOIN users u1 ON m.sender_id = u1.user_id
        JOIN users u2 ON m.receiver_id = u2.user_id
        WHERE ((m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?))
        AND m.place_id = ?
        ORDER BY m.timestamp ASC
    """, (user1_id, user2_id, user2_id, user1_id, place_id))
    messages = c.fetchall()
    conn.close()
    return messages

def check_and_update_top_rated_status():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # بررسی مکان‌هایی که باید به برتر تبدیل شوند
    MIN_RATING_COUNT = 100
    MIN_AVG_RATING = 8.0
    
    c.execute("""
        SELECT place_id, rating_sum, rating_count, is_top_rated 
        FROM places 
        WHERE rating_count >= ? AND (rating_sum * 1.0 / rating_count) >= ?
    """, (MIN_RATING_COUNT, MIN_AVG_RATING))
    
    places_to_promote = c.fetchall()
    
    for place in places_to_promote:
        place_id, rating_sum, rating_count, is_top_rated = place
        if not is_top_rated:
            # ارسال پیام تبریک به صاحب مکان
            owner_id = get_place_owner_id(place_id)
            place_info = get_place_by_id(place_id)
            if owner_id and place_info:
                try:
                    bot.send_message(owner_id, 
                                   f"{EMOJIS['success']} تبریک! مکان شما '{place_info[4]}' وارد بخش مکان‌های برتر شد! 🎉")
                except:
                    pass
            c.execute("UPDATE places SET is_top_rated = 1 WHERE place_id = ?", (place_id,))
    
    # بررسی مکان‌هایی که باید از برتر حذف شوند
    c.execute("""
        SELECT place_id, rating_sum, rating_count, is_top_rated 
        FROM places 
        WHERE is_top_rated = 1 AND (rating_count < ? OR (rating_sum * 1.0 / rating_count) < ?)
    """, (MIN_RATING_COUNT, MIN_AVG_RATING))
    
    places_to_demote = c.fetchall()
    
    for place in places_to_demote:
        place_id, rating_sum, rating_count, is_top_rated = place
        if is_top_rated:
            # ارسال پیام به صاحب مکان
            owner_id = get_place_owner_id(place_id)
            place_info = get_place_by_id(place_id)
            if owner_id and place_info:
                try:
                    bot.send_message(owner_id, 
                                   f"{EMOJIS['warning']} متأسفیم! مکان شما '{place_info[4]}' دیگر در بخش مکان‌های برتر نیست.")
                except:
                    pass
            c.execute("UPDATE places SET is_top_rated = 0 WHERE place_id = ?", (place_id,))
    
    conn.commit()
    conn.close()

# منوها
def main_menu(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['profile']} پروفایل")
    keyboard.row(f"{EMOJIS['places']} مکان‌ها", f"{EMOJIS['rating']} مکان‌های برتر")
    keyboard.row(f"{EMOJIS['star']} کاربران برتر")
    keyboard.row(f"{EMOJIS['link']} لینک‌ها", f"{EMOJIS['help']} راهنما")
    
    # فقط ادمین می‌تواند دکمه ادمین را ببیند
    if user_id == ADMIN_ID:
        keyboard.row(f"{EMOJIS['admin']} بخش ادمین")
    
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
    keyboard.row(f"{EMOJIS['score']} امتیاز کاربران")
    keyboard.row(f"{EMOJIS['comments']} مدیریت نظرات")
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

def admin_score_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['add_score']} اضافه کردن امتیاز", f"{EMOJIS['remove_score']} کم کردن امتیاز")
    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
    return keyboard

def edit_place_menu(place_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['edit']} ویرایش عنوان", f"{EMOJIS['edit']} ویرایش توضیحات")
    keyboard.row(f"{EMOJIS['edit']} ویرایش آدرس", f"{EMOJIS['edit']} ویرایش تماس")
    keyboard.row(f"{EMOJIS['edit']} ویرایش عکس")
    keyboard.row(f"{EMOJIS['edit']} ویرایش شیفت صبح", f"{EMOJIS['edit']} ویرایش شیفت عصر")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def search_type_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مغازه های آدرس مورد نظر")
    keyboard.row("جستجوی مغازه مورد نظر")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def place_details_menu(place_id, is_owner=False, is_admin=False):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['rating']} امتیاز", callback_data=f"rate_place_{place_id}"))
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comments']} نظرات", callback_data=f"view_comments_{place_id}"))
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['message']} ارسال پیام", callback_data=f"message_owner_{place_id}"))
    
    if is_admin:
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place_id}"))
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place_id}"))
    elif is_owner:
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place_id}"))
    
    return keyboard

def comments_menu(place_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['add']} افزودن نظر", callback_data=f"add_comment_{place_id}"))
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['back']} بازگشت", callback_data=f"back_to_place_{place_id}"))
    return keyboard

def comment_actions_menu(comment_id, place_id, is_admin=False):
    keyboard = types.InlineKeyboardMarkup()
    if is_admin:
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف نظر", callback_data=f"delete_comment_{comment_id}"))
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['back']} بازگشت", callback_data=f"view_comments_{place_id}"))
    return keyboard

def message_actions_menu(sender_id, receiver_id, place_id, message_id=None):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['reply']} پاسخ", callback_data=f"reply_message_{sender_id}_{receiver_id}_{place_id}"))
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['block']} بلاک", callback_data=f"block_user_{sender_id}_{receiver_id}_{place_id}"))
    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['unblock']} رفع بلاک", callback_data=f"unblock_user_{sender_id}_{receiver_id}_{place_id}"))
    return keyboard

def confirm_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("بله", "خیر")
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
        bot.send_message(user_id, f"{EMOJIS['success']} خوش برگشتی! 😍", reply_markup=main_menu(user_id))
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

    # بررسی وضعیت‌های مربوط به سیستم پیام‌رسانی و نظرات
    if state.startswith("comment_for_place_"):
        place_id = int(state.split("_")[3])
        if text.strip():
            add_comment_to_place(place_id, user_id, text)
            
            # اطلاع به صاحب مکان
            owner_id = get_place_owner_id(place_id)
            place_info = get_place_by_id(place_id)
            user_info = get_user(user_id)
            
            if owner_id and place_info and user_info:
                try:
                    comment_msg = f"{EMOJIS['comments']} کاربر جدید برای مکان شما نظر داد:\n"
                    comment_msg += f"مکان: {place_info[4]}\n"
                    comment_msg += f"کاربر: {user_info[1]} ({user_info[2]} سال، {user_info[3]})\n"
                    comment_msg += f"شناسه کاربری: {user_info[5]}\n"
                    comment_msg += f"نظر: {text}"
                    bot.send_message(owner_id, comment_msg)
                except:
                    pass
            
            bot.send_message(user_id, f"{EMOJIS['success']} نظر شما با موفقیت ثبت شد!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} نظر نمی‌تواند خالی باشد!")
    
    elif state.startswith("message_for_place_"):
        parts = state.split("_")
        place_id = int(parts[3])
        receiver_id = int(parts[4])
        
        if text.strip():
            send_message_to_user(user_id, receiver_id, place_id, text, "text")
            
            # اطلاع به گیرنده
            place_info = get_place_by_id(place_id)
            user_info = get_user(user_id)
            
            if place_info and user_info:
                try:
                    msg = f"{EMOJIS['message']} پیام جدید برای مکان شما:\n"
                    msg += f"مکان: {place_info[4]}\n"
                    msg += f"فرستنده: {user_info[1]} ({user_info[2]} سال، {user_info[3]})\n"
                    msg += f"شناسه کاربری: {user_info[5]}\n"
                    msg += f"پیام: {text}"
                    
                    keyboard = message_actions_menu(user_id, receiver_id, place_id)
                    bot.send_message(receiver_id, msg, reply_markup=keyboard)
                except:
                    pass
            
            bot.send_message(user_id, f"{EMOJIS['success']} پیام شما با موفقیت ارسال شد!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} پیام نمی‌تواند خالی باشد!")
    
    elif state.startswith("reply_message_"):
        parts = state.split("_")
        receiver_id = int(parts[3])
        place_id = int(parts[4])
        
        if text.strip():
            send_message_to_user(user_id, receiver_id, place_id, text, "text")
            
            # اطلاع به گیرنده
            place_info = get_place_by_id(place_id)
            user_info = get_user(user_id)
            
            if place_info and user_info:
                try:
                    msg = f"{EMOJIS['message']} پاسخ جدید به پیام شما:\n"
                    msg += f"مکان: {place_info[4]}\n"
                    msg += f"فرستنده: {user_info[1]} ({user_info[2]} سال، {user_info[3]})\n"
                    msg += f"شناسه کاربری: {user_info[5]}\n"
                    msg += f"پیام: {text}"
                    
                    keyboard = message_actions_menu(user_id, receiver_id, place_id)
                    bot.send_message(receiver_id, msg, reply_markup=keyboard)
                except:
                    pass
            
            bot.send_message(user_id, f"{EMOJIS['success']} پاسخ شما با موفقیت ارسال شد!", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} پیام نمی‌تواند خالی باشد!")
    
    elif state == "admin_delete_comment_title":
        if text.strip():
            user_data[user_id] = {'delete_comment_title': text}
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی صاحب مکان را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_delete_comment_owner_id"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان مکان نمی‌تواند خالی باشد!", reply_markup=admin_sub_menu())
    
    elif state == "admin_delete_comment_owner_id":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                user_data[user_id]['delete_comment_owner_id'] = numeric_id
                user_data[user_id]['delete_comment_owner_user_id'] = target_user[0]
                bot.send_message(user_id, f"{EMOJIS['info']} اولین کلمه نظر را وارد کنید:", reply_markup=admin_sub_menu())
                user_states[user_id] = "admin_delete_comment_text"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه عددی یافت نشد!", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=admin_sub_menu())
    
    elif state == "admin_delete_comment_text":
        if text.strip():
            user_data[user_id]['delete_comment_text'] = text
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر نظر دهنده را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_delete_comment_user_id"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} متن نظر نمی‌تواند خالی باشد!", reply_markup=admin_sub_menu())
    
    elif state == "admin_delete_comment_user_id":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                user_data[user_id]['delete_comment_user_id'] = numeric_id
                user_data[user_id]['delete_comment_user_user_id'] = target_user[0]
                
                # جستجوی نظر
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("""
                    SELECT pc.comment_id, p.title, u1.name as owner_name, u2.name as commenter_name, pc.comment
                    FROM place_comments pc
                    JOIN places p ON pc.place_id = p.place_id
                    JOIN users u1 ON p.user_id = u1.user_id
                    JOIN users u2 ON pc.user_id = u2.user_id
                    WHERE p.title = ? AND p.user_id = ? AND pc.comment LIKE ? AND pc.user_id = ?
                """, (
                    user_data[user_id]['delete_comment_title'],
                    user_data[user_id]['delete_comment_owner_user_id'],
                    f"{user_data[user_id]['delete_comment_text']}%",
                    user_data[user_id]['delete_comment_user_user_id']
                ))
                comment = c.fetchone()
                conn.close()
                
                if comment:
                    user_data[user_id]['delete_comment_id'] = comment[0]
                    
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.row("بله", "خیر")
                    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                    
                    msg = f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این نظر را حذف کنید؟\n\n"
                    msg += f"مکان: {comment[1]}\n"
                    msg += f"صاحب مکان: {comment[2]}\n"
                    msg += f"نظر دهنده: {comment[3]}\n"
                    msg += f"نظر: {comment[4]}"
                    
                    bot.send_message(user_id, msg, reply_markup=keyboard)
                    user_states[user_id] = "admin_delete_comment_confirm"
                else:
                    bot.send_message(user_id, f"{EMOJIS['error']} نظری با این مشخصات یافت نشد!", reply_markup=admin_menu())
                    user_states[user_id] = "admin_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه عددی یافت نشد!", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=admin_sub_menu())
    
    elif state == "admin_delete_comment_confirm":
        if text == "بله":
            comment_id = user_data[user_id]['delete_comment_id']
            delete_comment(comment_id)
            
            # اطلاع به کاربر نظر دهنده
            try:
                target_user_id = user_data[user_id]['delete_comment_user_user_id']
                place_title = user_data[user_id]['delete_comment_title']
                bot.send_message(target_user_id, 
                               f"{EMOJIS['warning']} نظر شما در مکان '{place_title}' توسط ادمین به دلیل نقض قوانین حذف شد.")
            except:
                pass
            
            bot.send_message(user_id, f"{EMOJIS['success']} نظر با موفقیت حذف شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} حذف نظر لغو شد.", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    
    # ادامه کد قبلی برای سایر وضعیت‌ها
    elif text == f"{EMOJIS['home']} صفحه اصلی":
        bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu(user_id))
        user_states[user_id] = "main_menu"
        return
    
    # ادامه کد قبلی برای سایر وضعیت‌ها
    # (کدهای قبلی برای مدیریت منوها و سایر وضعیت‌ها)
    
    # بررسی وضعیت مکان‌های برتر
    check_and_update_top_rated_status()

# مدیریت callback queries
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
            bot.send_message(user_id, f"{EMOJIS['success']} خوش برگشتی! 😍", reply_markup=main_menu(user_id))
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
    
    elif data.startswith("view_comments_"):
        place_id = int(data.split("_")[2])
        comments = get_comments_for_place(place_id)
        
        if comments:
            msg = f"{EMOJIS['comments']} نظرات برای این مکان:\n\n"
            for comment in comments:
                comment_id, comment_user_id, comment_text, timestamp, user_name, user_age, user_gender, user_numeric_id = comment
                msg += f"{user_name} ({user_age} سال، {user_gender}) - شناسه: {user_numeric_id}\n"
                msg += f"نظر: {comment_text}\n"
                msg += f"زمان: {timestamp}\n"
                msg += "-------------------\n\n"
            
            keyboard = comments_menu(place_id)
            bot.send_message(user_id, msg, reply_markup=keyboard)
        else:
            bot.send_message(user_id, f"{EMOJIS['info']} هنوز نظری برای این مکان ثبت نشده است.")
    
    elif data.startswith("add_comment_"):
        place_id = int(data.split("_")[2])
        bot.send_message(user_id, f"{EMOJIS['comments']} نظر خود را برای این مکان وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = f"comment_for_place_{place_id}"
    
    elif data.startswith("message_owner_"):
        place_id = int(data.split("_")[2])
        owner_id = get_place_owner_id(place_id)
        
        if not owner_id:
            bot.send_message(user_id, f"{EMOJIS['error']} اطلاعات صاحب مکان یافت نشد!")
            return
        
        # بررسی آیا کاربر بلاک شده است
        if is_user_blocked_for_messaging(owner_id, user_id, place_id):
            bot.send_message(user_id, f"{EMOJIS['error']} شما توسط صاحب این مکان بلاک شده‌اید و نمی‌توانید پیام ارسال کنید.")
            return
        
        bot.send_message(user_id, f"{EMOJIS['message']} پیام خود را برای صاحب این مکان وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = f"message_for_place_{place_id}_{owner_id}"
    
    elif data.startswith("reply_message_"):
        parts = data.split("_")
        receiver_id = int(parts[2])
        place_id = int(parts[3])
        
        bot.send_message(user_id, f"{EMOJIS['reply']} پاسخ خود را وارد کنید:", reply_markup=back_button_only())
        user_states[user_id] = f"reply_message_{receiver_id}_{place_id}"
    
    elif data.startswith("block_user_"):
        parts = data.split("_")
        blocked_id = int(parts[2])
        place_id = int(parts[3])
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("بله", callback_data=f"confirm_block_{blocked_id}_{place_id}"))
        keyboard.add(types.InlineKeyboardButton("خیر", callback_data=f"cancel_block_{blocked_id}_{place_id}"))
        
        bot.send_message(user_id, f"{EMOJIS['warning']} آیا مطمئن هستید که می‌خواهید این کاربر را بلاک کنید؟", reply_markup=keyboard)
    
    elif data.startswith("confirm_block_"):
        parts = data.split("_")
        blocked_id = int(parts[2])
        place_id = int(parts[3])
        
        block_user_for_messaging(user_id, blocked_id, place_id)
        
        # اطلاع به کاربر بلاک شده
        try:
            place_info = get_place_by_id(place_id)
            if place_info:
                bot.send_message(blocked_id, 
                               f"{EMOJIS['error']} شما توسط صاحب مکان '{place_info[4]}' بلاک شده‌اید و نمی‌توانید پیام ارسال کنید.")
        except:
            pass
        
        bot.send_message(user_id, f"{EMOJIS['success']} کاربر با موفقیت بلاک شد.")
    
    elif data.startswith("unblock_user_"):
        parts = data.split("_")
        unblocked_id = int(parts[2])
        place_id = int(parts[3])
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("بله", callback_data=f"confirm_unblock_{unblocked_id}_{place_id}"))
        keyboard.add(types.InlineKeyboardButton("خیر", callback_data=f"cancel_unblock_{unblocked_id}_{place_id}"))
        
        bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این کاربر را از بلاک خارج کنید؟", reply_markup=keyboard)
    
    elif data.startswith("confirm_unblock_"):
        parts = data.split("_")
        unblocked_id = int(parts[2])
        place_id = int(parts[3])
        
        unblock_user_for_messaging(user_id, unblocked_id, place_id)
        
        # اطلاع به کاربر رفع بلاک شده
        try:
            place_info = get_place_by_id(place_id)
            if place_info:
                bot.send_message(unblocked_id, 
                               f"{EMOJIS['success']} شما توسط صاحب مکان '{place_info[4]}' رفع بلاک شده‌اید و می‌توانید دوباره پیام ارسال کنید.")
        except:
            pass
        
        bot.send_message(user_id, f"{EMOJIS['success']} کاربر با موفقیت از بلاک خارج شد.")
    
    elif data.startswith("delete_comment_"):
        comment_id = int(data.split("_")[2])
        
        # فقط ادمین می‌تواند نظرات را حذف کند
        if user_id != ADMIN_ID:
            bot.send_message(user_id, f"{EMOJIS['error']} شما مجاز به حذف نظرات نیستید!")
            return
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("بله", callback_data=f"confirm_delete_comment_{comment_id}"))
        keyboard.add(types.InlineKeyboardButton("خیر", callback_data=f"cancel_delete_comment_{comment_id}"))
        
        bot.send_message(user_id, f"{EMOJIS['warning']} آیا مطمئن هستید که می‌خواهید این نظر را حذف کنید؟", reply_markup=keyboard)
    
    elif data.startswith("confirm_delete_comment_"):
        comment_id = int(data.split("_")[3])
        
        # دریافت اطلاعات نظر قبل از حذف
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT pc.user_id, p.title 
            FROM place_comments pc
            JOIN places p ON pc.place_id = p.place_id
            WHERE pc.comment_id = ?
        """, (comment_id,))
        comment_info = c.fetchone()
        
        delete_comment(comment_id)
        conn.close()
        
        if comment_info:
            comment_user_id, place_title = comment_info
            # اطلاع به کاربر نظر دهنده
            try:
                bot.send_message(comment_user_id, 
                               f"{EMOJIS['warning']} نظر شما در مکان '{place_title}' توسط ادمین به دلیل نقض قوانین حذف شد.")
            except:
                pass
        
        bot.send_message(user_id, f"{EMOJIS['success']} نظر با موفقیت حذف شد!")
    
    # ادامه callback های قبلی
    elif data.startswith("delete_place"):
        place_id = int(data.split("_")[2])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id FROM places WHERE place_id = ?", (place_id,))
        place = c.fetchone()
        if place and (place[0] == user_id or user_id == ADMIN_ID):
            c.execute("DELETE FROM places WHERE place_id = ?", (place_id,))
            c.execute("DELETE FROM place_ratings WHERE place_id = ?", (place_id,))
            c.execute("DELETE FROM place_comments WHERE place_id = ?", (place_id,))
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
    
    elif data.startswith("back_to_place_"):
        place_id = int(data.split("_")[3])
        # نمایش اطلاعات مکان مجدداً
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT places.*, users.numeric_id FROM places JOIN users ON places.user_id = users.user_id WHERE place_id = ?", (place_id,))
        place = c.fetchone()
        conn.close()
        
        if place:
            if place[8]:
                try:
                    bot.send_photo(user_id, place[8])
                except:
                    pass
            
            avg_rating = (place[11] / place[12]) if place[12] > 0 else 0
            msg = f"{EMOJIS['places']} مکان:\n"
            msg += f"عنوان: {place[4]}\nدسته: {place[2]}\nزیردسته: {place[3] or 'مشخص نشده'}\n"
            msg += f"توضیحات: {place[5]}\n"
            msg += f"آدرس: {place[6]}\n"
            msg += f"تماس: {place[7] or 'مشخص نشده'}\n"
            msg += f"شیفت صبح: {place[9] or 'مشخص نشده'}\n"
            msg += f"شیفت عصر: {place[10] or 'مشخص نشده'}\n"
            msg += f"امتیاز: {avg_rating:.1f} ({place[12]} رای)"
            
            is_owner = (place[1] == user_id)
            is_admin = (user_id == ADMIN_ID)
            keyboard = place_details_menu(place_id, is_owner, is_admin)
            bot.send_message(user_id, msg, reply_markup=keyboard)

# مدیریت سایر انواع محتوا (عکس، وویس، استیکر)
@bot.message_handler(content_types=['photo', 'voice', 'sticker'])
def handle_other_content(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, "")
    
    if state.startswith("message_for_place_"):
        parts = state.split("_")
        place_id = int(parts[3])
        receiver_id = int(parts[4])
        
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            send_message_to_user(user_id, receiver_id, place_id, file_id, "photo")
            message_text = "یک عکس"
        elif message.content_type == 'voice':
            file_id = message.voice.file_id
            send_message_to_user(user_id, receiver_id, place_id, file_id, "voice")
            message_text = "یک پیام صوتی"
        elif message.content_type == 'sticker':
            file_id = message.sticker.file_id
            send_message_to_user(user_id, receiver_id, place_id, file_id, "sticker")
            message_text = "یک استیکر"
        
        # اطلاع به گیرنده
        place_info = get_place_by_id(place_id)
        user_info = get_user(user_id)
        
        if place_info and user_info:
            try:
                msg = f"{EMOJIS['message']} پیام جدید برای مکان شما:\n"
                msg += f"مکان: {place_info[4]}\n"
                msg += f"فرستنده: {user_info[1]} ({user_info[2]} سال، {user_info[3]})\n"
                msg += f"شناسه کاربری: {user_info[5]}\n"
                msg += f"پیام: {message_text}"
                
                keyboard = message_actions_menu(user_id, receiver_id, place_id)
                bot.send_message(receiver_id, msg, reply_markup=keyboard)
                
                # ارسال محتوای واقعی
                if message.content_type == 'photo':
                    bot.send_photo(receiver_id, file_id, reply_markup=keyboard)
                elif message.content_type == 'voice':
                    bot.send_voice(receiver_id, file_id, reply_markup=keyboard)
                elif message.content_type == 'sticker':
                    bot.send_sticker(receiver_id, file_id, reply_markup=keyboard)
                    
            except:
                pass
        
        bot.send_message(user_id, f"{EMOJIS['success']} پیام شما با موفقیت ارسال شد!", reply_markup=get_place_menu())
        user_states[user_id] = "place_menu"

# اجرای ربات در حالت وب هوک
if __name__ == "__main__":
    # راه‌اندازی یک تایمر برای بررسی وضعیت مکان‌های برتر
    def check_top_rated_timer():
        while True:
            check_and_update_top_rated_status()
            time.sleep(3600)  # هر ساعت یکبار بررسی کند
    
    timer_thread = threading.Thread(target=check_top_rated_timer)
    timer_thread.daemon = True
    timer_thread.start()
    
    app.run(host="0.0.0.0", port=PORT)