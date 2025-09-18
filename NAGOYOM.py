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
    "report": "📝",
    "message": "💬",
    "comment": "💭",
    "feedback": "📊",
    "buy": "💰",
    "top_place": "🏅",
    "vote": "🗳️",
    "block": "🚫",
    "unblock": "🔓",
    "reply": "↩️",
    "next": "➡️",
    "previous": "⬅️",
    "confirm": "✔️",
    "cancel": "❌"
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
user_comments = {}
user_messages = {}

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
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
                 comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 place_id INTEGER,
                 user_id INTEGER,
                 comment_text TEXT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
                 report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 report_text TEXT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS top_place_requests (
                 request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 place_title TEXT,
                 status TEXT DEFAULT 'pending',
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    try:
        c.execute("ALTER TABLE places ADD COLUMN subcategory TEXT")
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
        "تتو و микропиگمنتیشن (تاتو، میکروپیگمنتیشن)",
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
        "بیلیارد و بولینگ (بیلیارد، بولینگ، دارت)",
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
        "مراکز یوگا و مدیتیشن",
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
        "دفتر کار و شرکت‌ها (دفتر، شرکت)",
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
        num_id = random.randint(100000000, 999999999)  # 9 رقمی
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
def main_menu(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['profile']} پروفایل")
    keyboard.row(f"{EMOJIS['places']} مکان‌ها", f"{EMOJIS['rating']} مکان‌های برتر")
    keyboard.row(f"{EMOJIS['star']} کاربران برتر")
    keyboard.row(f"{EMOJIS['link']} لینک‌ها", f"{EMOJIS['help']} راهنما")
    keyboard.row(f"{EMOJIS['report']} گزارش", f"{EMOJIS['buy']} خرید مکان برتر")
    
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

def confirm_cancel_buttons():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['confirm']} تایید", f"{EMOJIS['cancel']} انصراف")
    return keyboard

def admin_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مدیریت اخبار", "مدیریت کاربران")
    keyboard.row("مدیریت مکان‌ها", "مدیریت نظرات")
    keyboard.row("قرارگیری مکان برتر", "مدیریت گزارش‌ها")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def admin_manage_news_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("افزودن خبر", "حذف خبر")
    keyboard.row("مشاهده اخبار")
    keyboard.row(f"{EMOJIS['back']} برگشت به ادمین", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def admin_manage_users_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مشاهده کاربران", "حذف کاربر")
    keyboard.row("جستجوی کاربر")
    keyboard.row(f"{EMOJIS['back']} برگشت به ادمین", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def admin_manage_places_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مشاهده مکان‌ها", "حذف مکان")
    keyboard.row("جستجوی مکان")
    keyboard.row(f"{EMOJIS['back']} برگشت به ادمین", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def admin_manage_comments_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مدیریت نظرات")
    keyboard.row(f"{EMOJIS['back']} برگشت به ادمین", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def admin_manage_reports_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مشاهده گزارش‌ها", "حذف گزارش")
    keyboard.row(f"{EMOJIS['back']} برگشت به ادمین", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def top_place_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['add_score']} اضافه کردن رای")
    keyboard.row(f"{EMOJIS['remove_score']} کم کردن رای")
    keyboard.row(f"{EMOJIS['back']} برگشت به ادمین", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

# دسته‌بندی‌های مکان‌ها
def get_categories_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in PLACE_CATEGORIES.keys():
        keyboard.row(category)
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

# زیردسته‌بندی‌ها
def get_subcategories_keyboard(category):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for subcategory in PLACE_CATEGORIES[category]:
        keyboard.row(subcategory)
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

# مدیریت حالت‌های کاربر
def set_user_state(user_id, state):
    user_states[user_id] = state

def get_user_state(user_id):
    return user_states.get(user_id, "HOME")

# مدیریت داده‌های کاربر
def set_user_data(user_id, key, value):
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id][key] = value

def get_user_data(user_id, key, default=None):
    if user_id in user_data and key in user_data[user_id]:
        return user_data[user_id][key]
    return default

# مدیریت نظرات
def add_comment(place_id, user_id, comment_text):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO comments (place_id, user_id, comment_text) VALUES (?, ?, ?)",
              (place_id, user_id, comment_text))
    conn.commit()
    conn.close()

def get_comments(place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT c.*, u.name, u.age, u.gender, u.numeric_id FROM comments c JOIN users u ON c.user_id = u.user_id WHERE c.place_id = ? ORDER BY c.timestamp DESC", (place_id,))
    comments = c.fetchall()
    conn.close()
    return comments

def delete_comment(comment_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM comments WHERE comment_id = ?", (comment_id,))
    conn.commit()
    conn.close()

# مدیریت گزارش‌ها
def add_report(user_id, report_text):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO reports (user_id, report_text) VALUES (?, ?)",
              (user_id, report_text))
    conn.commit()
    conn.close()

def get_reports():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT r.*, u.name, u.age, u.gender, u.numeric_id FROM reports r JOIN users u ON r.user_id = u.user_id ORDER BY r.timestamp DESC")
    reports = c.fetchall()
    conn.close()
    return reports

def delete_report(report_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
    conn.commit()
    conn.close()

# مدیریت درخواست‌های مکان برتر
def add_top_place_request(user_id, place_title):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO top_place_requests (user_id, place_title) VALUES (?, ?)",
              (user_id, place_title))
    conn.commit()
    conn.close()

def get_top_place_requests():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT r.*, u.name, u.age, u.gender, u.numeric_id FROM top_place_requests r JOIN users u ON r.user_id = u.user_id ORDER BY r.timestamp DESC")
    requests = c.fetchall()
    conn.close()
    return requests

def delete_top_place_request(request_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM top_place_requests WHERE request_id = ?", (request_id,))
    conn.commit()
    conn.close()

# مدیریت مکان‌ها
def add_place(user_id, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO places (user_id, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift))
    conn.commit()
    place_id = c.lastrowid
    conn.close()
    return place_id

def get_places():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM places ORDER BY place_id DESC")
    places = c.fetchall()
    conn.close()
    return places

def get_user_places(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM places WHERE user_id = ? ORDER BY place_id DESC", (user_id,))
    places = c.fetchall()
    conn.close()
    return places

def get_place(place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT p.*, u.name, u.age, u.gender, u.numeric_id FROM places p JOIN users u ON p.user_id = u.user_id WHERE p.place_id = ?", (place_id,))
    place = c.fetchone()
    conn.close()
    return place

def delete_place(place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM places WHERE place_id = ?", (place_id,))
    conn.commit()
    conn.close()

def search_places(query):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # جستجو در آدرس با تطبیق کلمه به کلمه
    words = query.split()
    search_pattern = '%' + '%'.join(words) + '%'
    
    c.execute("SELECT * FROM places WHERE address LIKE ? OR title LIKE ? OR description LIKE ?", 
              (search_pattern, search_pattern, search_pattern))
    places = c.fetchall()
    conn.close()
    return places

# مدیریت امتیازها
def add_rating(place_id, user_id, rating):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # بررسی آیا کاربر قبلاً به این مکان امتیاز داده است
    c.execute("SELECT * FROM place_ratings WHERE place_id = ? AND user_id = ?", (place_id, user_id))
    existing_rating = c.fetchone()
    
    if existing_rating:
        # به‌روزرسانی امتیاز قبلی
        c.execute("UPDATE place_ratings SET rating = ? WHERE place_id = ? AND user_id = ?", 
                 (rating, place_id, user_id))
        # به‌روزرسانی مجموع امتیازها
        c.execute("UPDATE places SET rating_sum = rating_sum - ? + ? WHERE place_id = ?", 
                 (existing_rating[2], rating, place_id))
    else:
        # افزودن امتیاز جدید
        c.execute("INSERT INTO place_ratings (place_id, user_id, rating) VALUES (?, ?, ?)", 
                 (place_id, user_id, rating))
        # به‌روزرسانی مجموع امتیازها و تعداد امتیازها
        c.execute("UPDATE places SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE place_id = ?", 
                 (rating, place_id))
    
    conn.commit()
    conn.close()

def get_place_rating(place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT rating_sum, rating_count FROM places WHERE place_id = ?", (place_id,))
    result = c.fetchone()
    conn.close()
    
    if result and result[1] > 0:
        return round(result[0] / result[1], 1)
    return 0

# مدیریت اخبار
def add_news(content):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO news (content) VALUES (?)", (content,))
    conn.commit()
    conn.close()

def get_news():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM news ORDER BY news_id DESC")
    news = c.fetchall()
    conn.close()
    return news

def delete_news(news_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM news WHERE news_id = ?", (news_id,))
    conn.commit()
    conn.close()

# مدیریت پیام‌ها
def send_message_to_user(sender_id, receiver_numeric_id, message_text):
    receiver = get_user_by_numeric_id(receiver_numeric_id)
    if receiver:
        try:
            bot.send_message(receiver[0], f"📩 پیام جدید از کاربر:\n\n{message_text}")
            return True
        except:
            return False
    return False

# راهنمای تعاملی
def get_help_keyboard(page=1):
    keyboard = types.InlineKeyboardMarkup()
    
    if page == 1:
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['next']} صفحه بعدی", callback_data="help_next_2"))
    elif page == 2:
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['previous']} صفحه قبلی", callback_data="help_prev_1"))
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['next']} صفحه بعدی", callback_data="help_next_3"))
    elif page == 3:
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['previous']} صفحه قبلی", callback_data="help_prev_2"))
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['next']} صفحه بعدی", callback_data="help_next_4"))
    elif page == 4:
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['previous']} صفحه قبلی", callback_data="help_prev_3"))
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['next']} صفحه بعدی", callback_data="help_next_5"))
    else:  # page == 5
        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['previous']} صفحه قبلی", callback_data="help_prev_4"))
    
    return keyboard

def get_help_message(page=1):
    if page == 1:
        return f"""
{EMOJIS['help']} راهنمای ربات گویم‌نما - صفحه ۱/۵

{EMOJIS['profile']} بخش پروفایل:
- مشاهده اطلاعات حساب کاربری
- تغییر نام، سن و جنسیت
- مشاهده شناسه عددی یکتا

{EMOJIS['places']} بخش مکان‌ها:
- افزودن مکان جدید با جزئیات کامل
- مشاهده و مدیریت مکان‌های اضافه شده
- جستجوی مکان‌ها بر اساس آدرس یا عنوان
        """
    elif page == 2:
        return f"""
{EMOJIS['help']} راهنمای ربات گویم‌نما - صفحه ۲/۵

{EMOJIS['rating']} بخش مکان‌های برتر:
- مشاهده مکان‌های دارای بالاترین امتیاز
- امتیازدهی به مکان‌های مختلف
- مشاهده نظرات سایر کاربران

{EMOJIS['star']} بخش کاربران برتر:
- مشاهده کاربران فعال و پرامتیاز
- رقابت برای کسب امتیاز بیشتر
        """
    elif page == 3:
        return f"""
{EMOJIS['help']} راهنمای ربات گویم‌نما - صفحه ۳/۵

{EMOJIS['link']} بخش لینک‌ها:
- دسترسی سریع به بخش‌های مختلف
- لینک‌های مفید و راهنما

{EMOJIS['report']} بخش گزارش:
- ارسال گزارش و پیشنهاد به ادمین
- گزارش مشکلات و باگ‌ها
- ارتباط مستقیم با پشتیبانی
        """
    elif page == 4:
        return f"""
{EMOJIS['help']} راهنمای ربات گویم‌نما - صفحه ۴/۵

{EMOJIS['buy']} بخش خرید مکان برتر:
- درخواست قرارگیری مکان در بخش برترها
- افزایش visibility مکان شما
- جذب مشتریان بیشتر

{EMOJIS['admin']} بخش ادمین (فقط برای مدیران):
- مدیریت کاربران و مکان‌ها
- مدیریت اخبار و گزارشات
- تنظیمات سیستم
        """
    else:  # page == 5
        return f"""
{EMOJIS['help']} راهنمای ربات گویم‌نما - صفحه ۵/۵

{EMOJIS['info']} نکات مهم:
- اطلاعات مکان‌ها را با دقت وارد کنید
- از ارسال محتوای نامناسب خودداری کنید
- در صورت بروز مشکل از بخش گزارش استفاده کنید

{EMOJIS['warning']} قوانین:
- هر کاربر مسئول اطلاعات مکان‌های خود است
- نقض قوانین منجر به مسدود شدن حساب می‌شود
- حفظ حریم خصوصی کاربران الزامی است

برای اطلاعات بیشتر می‌توانید از بخش گزارش با ما در ارتباط باشید.
        """

# هندلرهای ربات
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Invalid content type', 403

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    set_user_state(user_id, "HOME")
    
    # بررسی آیا کاربر قبلاً ثبت‌نام کرده است
    user = get_user(user_id)
    if user:
        bot.send_message(user_id, f"{EMOJIS['home']} به ربات گویم‌نما خوش آمدید!", reply_markup=main_menu(user_id))
    else:
        # درخواست اطلاعات کاربر
        bot.send_message(user_id, WELCOME_MESSAGE, reply_markup=confirm_cancel_buttons())
        set_user_state(user_id, "CONFIRM_RULES")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "CONFIRM_RULES")
def handle_confirm_rules(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['confirm']} تایید":
        bot.send_message(user_id, "لطفاً نام خود را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "GET_NAME")
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        bot.send_message(user_id, "برای استفاده از ربات باید قوانین را بپذیرید. لطفاً دوباره /start را بزنید.")
        set_user_state(user_id, "HOME")
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های بالا را انتخاب کنید.", reply_markup=confirm_cancel_buttons())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "GET_NAME")
def handle_get_name(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, WELCOME_MESSAGE, reply_markup=confirm_cancel_buttons())
        set_user_state(user_id, "CONFIRM_RULES")
    else:
        set_user_data(user_id, "name", message.text)
        bot.send_message(user_id, "لطفاً سن خود را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "GET_AGE")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "GET_AGE")
def handle_get_age(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً نام خود را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "GET_NAME")
    elif message.text.isdigit() and 1 <= int(message.text) <= 120:
        set_user_data(user_id, "age", int(message.text))
        
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("مرد", "زن")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        
        bot.send_message(user_id, "لطفاً جنسیت خود را انتخاب کنید:", reply_markup=keyboard)
        set_user_state(user_id, "GET_GENDER")
    else:
        bot.send_message(user_id, "لطفاً یک سن معتبر بین 1 تا 120 وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "GET_GENDER")
def handle_get_gender(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً سن خود را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "GET_AGE")
    elif message.text in ["مرد", "زن"]:
        name = get_user_data(user_id, "name")
        age = get_user_data(user_id, "age")
        gender = message.text
        
        # ذخیره کاربر در پایگاه داده
        save_user(user_id, name, age, gender)
        
        # پاک کردن داده‌های موقت
        if user_id in user_data:
            del user_data[user_id]
        
        bot.send_message(user_id, f"{EMOJIS['success']} ثبت‌نام شما با موفقیت انجام شد!", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("مرد", "زن")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های بالا را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['profile']} پروفایل" and get_user_state(message.from_user.id) == "HOME")
def handle_profile(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user:
        profile_text = f"""
{EMOJIS['profile']} اطلاعات پروفایل:

{EMOJIS['user']} نام: {user[1]}
{EMOJIS['info']} سن: {user[2]}
{EMOJIS['group']} جنسیت: {user[3]}
{EMOJIS['score']} امتیاز: {user[4]}
{EMOJIS['document']} شناسه عددی: {user[5]}
        """
        bot.send_message(user_id, profile_text, reply_markup=profile_menu())
        set_user_state(user_id, "PROFILE")
    else:
        bot.send_message(user_id, "خطا در دریافت اطلاعات پروفایل. لطفاً دوباره /start را بزنید.")

@bot.message_handler(func=lambda message: message.text == "مشاهده پروفایل" and get_user_state(message.from_user.id) == "PROFILE")
def handle_view_profile(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user:
        profile_text = f"""
{EMOJIS['profile']} اطلاعات پروفایل:

{EMOJIS['user']} نام: {user[1]}
{EMOJIS['info']} سن: {user[2]}
{EMOJIS['group']} جنسیت: {user[3]}
{EMOJIS['score']} امتیاز: {user[4]}
{EMOJIS['document']} شناسه عددی: {user[5]}
        """
        bot.send_message(user_id, profile_text, reply_markup=profile_menu())
    else:
        bot.send_message(user_id, "خطا در دریافت اطلاعات پروفایل.")

@bot.message_handler(func=lambda message: message.text == "تغییر نام" and get_user_state(message.from_user.id) == "PROFILE")
def handle_change_name(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً نام جدید خود را وارد کنید:", reply_markup=back_button_only())
    set_user_state(user_id, "CHANGE_NAME")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "CHANGE_NAME")
def handle_change_name_input(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['profile']} بخش پروفایل", reply_markup=profile_menu())
        set_user_state(user_id, "PROFILE")
    else:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET name = ? WHERE user_id = ?", (message.text, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} نام شما با موفقیت تغییر یافت!", reply_markup=profile_menu())
        set_user_state(user_id, "PROFILE")

@bot.message_handler(func=lambda message: message.text == "تغییر سن" and get_user_state(message.from_user.id) == "PROFILE")
def handle_change_age(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً سن جدید خود را وارد کنید:", reply_markup=back_button_only())
    set_user_state(user_id, "CHANGE_AGE")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "CHANGE_AGE")
def handle_change_age_input(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['profile']} بخش پروفایل", reply_markup=profile_menu())
        set_user_state(user_id, "PROFILE")
    elif message.text.isdigit() and 1 <= int(message.text) <= 120:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET age = ? WHERE user_id = ?", (int(message.text), user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} سن شما با موفقیت تغییر یافت!", reply_markup=profile_menu())
        set_user_state(user_id, "PROFILE")
    else:
        bot.send_message(user_id, "لطفاً یک سن معتبر بین 1 تا 120 وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: message.text == "تغییر جنسیت" and get_user_state(message.from_user.id) == "PROFILE")
def handle_change_gender(message):
    user_id = message.from_user.id
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مرد", "زن")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    
    bot.send_message(user_id, "لطفاً جنسیت جدید خود را انتخاب کنید:", reply_markup=keyboard)
    set_user_state(user_id, "CHANGE_GENDER")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "CHANGE_GENDER")
def handle_change_gender_input(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['profile']} بخش پروفایل", reply_markup=profile_menu())
        set_user_state(user_id, "PROFILE")
    elif message.text in ["مرد", "زن"]:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET gender = ? WHERE user_id = ?", (message.text, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} جنسیت شما با موفقیت تغییر یافت!", reply_markup=profile_menu())
        set_user_state(user_id, "PROFILE")
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("مرد", "زن")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های بالا را انتخاب کنید:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['places']} مکان‌ها" and get_user_state(message.from_user.id) == "HOME")
def handle_places(message):
    user_id = message.from_user.id
    bot.send_message(user_id, f"{EMOJIS['places']} بخش مکان‌ها", reply_markup=get_place_menu())
    set_user_state(user_id, "PLACES")

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['add']} اضافه کردن مکان" and get_user_state(message.from_user.id) == "PLACES")
def handle_add_place(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً دسته‌بندی مکان را انتخاب کنید:", reply_markup=get_categories_keyboard())
    set_user_state(user_id, "ADD_PLACE_CATEGORY")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_CATEGORY")
def handle_add_place_category(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['places']} بخش مکان‌ها", reply_markup=get_place_menu())
        set_user_state(user_id, "PLACES")
    elif message.text == f"{EMOJIS['home']} صفحه اصلی":
        bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")
    elif message.text in PLACE_CATEGORIES:
        set_user_data(user_id, "category", message.text)
        bot.send_message(user_id, "لطفاً زیردسته‌بندی مکان را انتخاب کنید:", reply_markup=get_subcategories_keyboard(message.text))
        set_user_state(user_id, "ADD_PLACE_SUBCATEGORY")
    else:
        bot.send_message(user_id, "لطفاً یکی از دسته‌بندی‌های موجود را انتخاب کنید:", reply_markup=get_categories_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_SUBCATEGORY")
def handle_add_place_subcategory(message):
    user_id = message.from_user.id
    category = get_user_data(user_id, "category")
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً دسته‌بندی مکان را انتخاب کنید:", reply_markup=get_categories_keyboard())
        set_user_state(user_id, "ADD_PLACE_CATEGORY")
    elif message.text == f"{EMOJIS['home']} صفحه اصلی":
        bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")
    elif category and message.text in PLACE_CATEGORIES[category]:
        set_user_data(user_id, "subcategory", message.text)
        bot.send_message(user_id, "لطفاً عنوان مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADD_PLACE_TITLE")
    else:
        bot.send_message(user_id, "لطفاً یکی از زیردسته‌بندی‌های موجود را انتخاب کنید:", reply_markup=get_subcategories_keyboard(category))

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_TITLE")
def handle_add_place_title(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        category = get_user_data(user_id, "category")
        bot.send_message(user_id, "لطفاً زیردسته‌بندی مکان را انتخاب کنید:", reply_markup=get_subcategories_keyboard(category))
        set_user_state(user_id, "ADD_PLACE_SUBCATEGORY")
    else:
        set_user_data(user_id, "title", message.text)
        bot.send_message(user_id, "لطفاً توضیحات مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADD_PLACE_DESCRIPTION")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_DESCRIPTION")
def handle_add_place_description(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً عنوان مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADD_PLACE_TITLE")
    else:
        set_user_data(user_id, "description", message.text)
        bot.send_message(user_id, "لطفاً آدرس مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADD_PLACE_ADDRESS")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_ADDRESS")
def handle_add_place_address(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً توضیحات مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADD_PLACE_DESCRIPTION")
    else:
        set_user_data(user_id, "address", message.text)
        bot.send_message(user_id, "لطفاً شماره تلفن مکان را وارد کنید:", reply_markup=skip_button())
        set_user_state(user_id, "ADD_PLACE_PHONE")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_PHONE")
def handle_add_place_phone(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً آدرس مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADD_PLACE_ADDRESS")
    elif message.text == "رد کردن":
        set_user_data(user_id, "phone", "ندارد")
        bot.send_message(user_id, "لطفاً ساعت کاری صبح مکان را وارد کنید (مثلاً 8:00-12:00):", reply_markup=skip_button())
        set_user_state(user_id, "ADD_PLACE_MORNING_SHIFT")
    else:
        set_user_data(user_id, "phone", message.text)
        bot.send_message(user_id, "لطفاً ساعت کاری صبح مکان را وارد کنید (مثلاً 8:00-12:00):", reply_markup=skip_button())
        set_user_state(user_id, "ADD_PLACE_MORNING_SHIFT")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_MORNING_SHIFT")
def handle_add_place_morning_shift(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً شماره تلفن مکان را وارد کنید:", reply_markup=skip_button())
        set_user_state(user_id, "ADD_PLACE_PHONE")
    elif message.text == "رد کردن":
        set_user_data(user_id, "morning_shift", "تعریف نشده")
        bot.send_message(user_id, "لطفاً ساعت کاری عصر مکان را وارد کنید (مثلاً 16:00-20:00):", reply_markup=skip_button())
        set_user_state(user_id, "ADD_PLACE_AFTERNOON_SHIFT")
    else:
        set_user_data(user_id, "morning_shift", message.text)
        bot.send_message(user_id, "لطفاً ساعت کاری عصر مکان را وارد کنید (مثلاً 16:00-20:00):", reply_markup=skip_button())
        set_user_state(user_id, "ADD_PLACE_AFTERNOON_SHIFT")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_AFTERNOON_SHIFT")
def handle_add_place_afternoon_shift(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً ساعت کاری صبح مکان را وارد کنید (مثلاً 8:00-12:00):", reply_markup=skip_button())
        set_user_state(user_id, "ADD_PLACE_MORNING_SHIFT")
    elif message.text == "رد کردن":
        set_user_data(user_id, "afternoon_shift", "تعریف نشده")
        bot.send_message(user_id, "لطفاً عکس مکان را ارسال کنید (حداکثر 8 عکس):", reply_markup=back_button_only())
        set_user_state(user_id, "ADD_PLACE_PHOTO")
    else:
        set_user_data(user_id, "afternoon_shift", message.text)
        bot.send_message(user_id, "لطفاً عکس مکان را ارسال کنید (حداکثر 8 عکس):", reply_markup=back_button_only())
        set_user_state(user_id, "ADD_PLACE_PHOTO")

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_PHOTO")
def handle_add_place_photo(message):
    user_id = message.from_user.id
    
    # ذخیره عکس‌ها
    if 'photos' not in user_data.get(user_id, {}):
        set_user_data(user_id, 'photos', [])
    
    user_data[user_id]['photos'].append(message.photo[-1].file_id)
    
    if len(user_data[user_id]['photos']) >= 8:
        bot.send_message(user_id, "حداکثر تعداد عکس‌ها رسید. برای ادامه دکمه تایید را بزنید.", reply_markup=confirm_cancel_buttons())
        set_user_state(user_id, "ADD_PLACE_CONFIRM")
    else:
        remaining = 8 - len(user_data[user_id]['photos'])
        bot.send_message(user_id, f"عکس دریافت شد. می‌توانید تا {remaining} عکس دیگر ارسال کنید یا برای ادامه دکمه تایید را بزنید.", reply_markup=confirm_cancel_buttons())
        set_user_state(user_id, "ADD_PLACE_CONFIRM")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADD_PLACE_CONFIRM")
def handle_add_place_confirm(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تایید":
        # جمع‌آوری تمام اطلاعات
        category = get_user_data(user_id, "category")
        subcategory = get_user_data(user_id, "subcategory")
        title = get_user_data(user_id, "title")
        description = get_user_data(user_id, "description")
        address = get_user_data(user_id, "address")
        phone = get_user_data(user_id, "phone")
        morning_shift = get_user_data(user_id, "morning_shift")
        afternoon_shift = get_user_data(user_id, "afternoon_shift")
        photos = user_data[user_id].get('photos', [])
        
        # ذخیره مکان در پایگاه داده
        photo_ids = ",".join(photos) if photos else "ندارد"
        place_id = add_place(user_id, category, subcategory, title, description, address, phone, photo_ids, morning_shift, afternoon_shift)
        
        # پاک کردن داده‌های موقت
        keys_to_remove = ['category', 'subcategory', 'title', 'description', 'address', 'phone', 'morning_shift', 'afternoon_shift', 'photos']
        for key in keys_to_remove:
            if key in user_data.get(user_id, {}):
                del user_data[user_id][key]
        
        bot.send_message(user_id, f"{EMOJIS['success']} مکان شما با موفقیت اضافه شد!", reply_markup=get_place_menu())
        set_user_state(user_id, "PLACES")
        
        # ارسال عکس‌ها به صورت گروهی
        if photos:
            media = [types.InputMediaPhoto(photo_id) for photo_id in photos]
            bot.send_media_group(user_id, media)
            
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        # پاک کردن داده‌های موقت
        keys_to_remove = ['category', 'subcategory', 'title', 'description', 'address', 'phone', 'morning_shift', 'afternoon_shift', 'photos']
        for key in keys_to_remove:
            if key in user_data.get(user_id, {}):
                del user_data[user_id][key]
        
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=get_place_menu())
        set_user_state(user_id, "PLACES")
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های بالا را انتخاب کنید:", reply_markup=confirm_cancel_buttons())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['view']} مشاهده مکان‌ها" and get_user_state(message.from_user.id) == "PLACES")
def handle_view_places(message):
    user_id = message.from_user.id
    places = get_places()
    
    if places:
        for place in places:
            place_text = f"""
{EMOJIS['places']} مکان #{place[0]}

{EMOJIS['info']} دسته‌بندی: {place[2]}
{EMOJIS['info']} زیردسته: {place[3]}
{EMOJIS['document']} عنوان: {place[4]}
{EMOJIS['edit']} توضیحات: {place[5]}
{EMOJIS['location']} آدرس: {place[6]}
{EMOJIS['phone']} تلفن: {place[7]}
{EMOJIS['time']} ساعت کاری صبح: {place[9]}
{EMOJIS['time']} ساعت کاری عصر: {place[10]}
{EMOJIS['star']} امتیاز: {get_place_rating(place[0])}
            """
            
            # ارسال عکس‌ها به صورت گروهی اگر وجود دارند
            if place[8] and place[8] != "ندارد":
                photo_ids = place[8].split(',')
                media = [types.InputMediaPhoto(photo_id) for photo_id in photo_ids]
                bot.send_media_group(user_id, media)
            
            bot.send_message(user_id, place_text, reply_markup=place_view_result_menu())
    else:
        bot.send_message(user_id, "هنوز هیچ مکانی اضافه نشده است.", reply_markup=get_place_menu())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['view']} مکان‌های من" and get_user_state(message.from_user.id) == "PLACES")
def handle_view_my_places(message):
    user_id = message.from_user.id
    places = get_user_places(user_id)
    
    if places:
        for place in places:
            place_text = f"""
{EMOJIS['places']} مکان #{place[0]}

{EMOJIS['info']} دسته‌بندی: {place[2]}
{EMOJIS['info']} زیردسته: {place[3]}
{EMOJIS['document']} عنوان: {place[4]}
{EMOJIS['edit']} توضیحات: {place[5]}
{EMOJIS['location']} آدرس: {place[6]}
{EMOJIS['phone']} تلفن: {place[7]}
{EMOJIS['time']} ساعت کاری صبح: {place[9]}
{EMOJIS['time']} ساعت کاری عصر: {place[10]}
{EMOJIS['star']} امتیاز: {get_place_rating(place[0])}
            """
            
            # ارسال عکس‌ها به صورت گروهی اگر وجود دارند
            if place[8] and place[8] != "ندارد":
                photo_ids = place[8].split(',')
                media = [types.InputMediaPhoto(photo_id) for photo_id in photo_ids]
                bot.send_media_group(user_id, media)
            
            bot.send_message(user_id, place_text, reply_markup=place_view_result_menu())
    else:
        bot.send_message(user_id, "شما هنوز هیچ مکانی اضافه نکرده‌اید.", reply_markup=get_place_menu())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['view']} جستجو" and get_user_state(message.from_user.id) == "PLACES")
def handle_search_places(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً عبارت جستجو را وارد کنید (عنوان، آدرس یا توضیحات):", reply_markup=back_button_only())
    set_user_state(user_id, "SEARCH_PLACES")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "SEARCH_PLACES")
def handle_search_places_input(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['places']} بخش مکان‌ها", reply_markup=get_place_menu())
        set_user_state(user_id, "PLACES")
    else:
        places = search_places(message.text)
        
        if places:
            bot.send_message(user_id, f"{len(places)} نتیجه یافت شد:")
            
            for place in places:
                place_text = f"""
{EMOJIS['places']} مکان #{place[0]}

{EMOJIS['info']} دسته‌بندی: {place[2]}
{EMOJIS['info']} زیردسته: {place[3]}
{EMOJIS['document']} عنوان: {place[4]}
{EMOJIS['edit']} توضیحات: {place[5]}
{EMOJIS['location']} آدرس: {place[6]}
{EMOJIS['phone']} تلفن: {place[7]}
{EMOJIS['time']} ساعت کاری صبح: {place[9]}
{EMOJIS['time']} ساعت کاری عصر: {place[10]}
{EMOJIS['star']} امتیاز: {get_place_rating(place[0])}
                """
                
                # ارسال عکس‌ها به صورت گروهی اگر وجود دارند
                if place[8] and place[8] != "ندارد":
                    photo_ids = place[8].split(',')
                    media = [types.InputMediaPhoto(photo_id) for photo_id in photo_ids]
                    bot.send_media_group(user_id, media)
                
                bot.send_message(user_id, place_text, reply_markup=place_view_result_menu())
        else:
            bot.send_message(user_id, "هیچ نتیجه‌ای یافت نشد.", reply_markup=get_place_menu())
            set_user_state(user_id, "PLACES")

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['report']} گزارش" and get_user_state(message.from_user.id) == "HOME")
def handle_report(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً گزارش خود را وارد کنید:", reply_markup=back_button_only())
    set_user_state(user_id, "SEND_REPORT")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "SEND_REPORT")
def handle_send_report(message):
    user_id = message.from_user.id
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")
    else:
        # ذخیره گزارش
        add_report(user_id, message.text)
        
        # ارسال گزارش به ادمین
        user = get_user(user_id)
        if user:
            report_text = f"""
{EMOJIS['report']} گزارش جدید از کاربر:

{EMOJIS['user']} نام: {user[1]}
{EMOJIS['info']} سن: {user[2]}
{EMOJIS['group']} جنسیت: {user[3]}
{EMOJIS['document']} شناسه عددی: {user[5]}

{EMOJIS['edit']} متن گزارش:
{message.text}
            """
            
            try:
                bot.send_message(ADMIN_ID, report_text)
            except:
                pass
        
        bot.send_message(user_id, f"{EMOJIS['success']} گزارش شما با موفقیت ارسال شد و پیگیری خواهد شد!", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['buy']} خرید مکان برتر" and get_user_state(message.from_user.id) == "HOME")
def handle_buy_top_place(message):
    user_id = message.from_user.id
    
    # دریافت مکان‌های کاربر
    user_places = get_user_places(user_id)
    
    if not user_places:
        bot.send_message(user_id, "شما هیچ مکانی برای قرارگیری در بخش برترها ندارید.", reply_markup=main_menu(user_id))
        return
    
    # ایجاد کیبورد با مکان‌های کاربر
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for place in user_places:
        keyboard.row(place[4])  # عنوان مکان
    
    keyboard.row(f"{EMOJIS['back']} برگشت")
    
    bot.send_message(user_id, "لطفاً مکان مورد نظر برای قرارگیری در بخش برترها را انتخاب کنید:", reply_markup=keyboard)
    set_user_state(user_id, "SELECT_TOP_PLACE")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "SELECT_TOP_PLACE")
def handle_select_top_place(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")
    else:
        # بررسی آیا مکان متعلق به کاربر است
        user_places = get_user_places(user_id)
        place_titles = [place[4] for place in user_places]
        
        if message.text in place_titles:
            # ذخیره درخواست
            add_top_place_request(user_id, message.text)
            
            # ارسال درخواست به ادمین
            user = get_user(user_id)
            if user:
                request_text = f"""
{EMOJIS['buy']} درخواست جدید برای مکان برتر:

{EMOJIS['user']} نام: {user[1]}
{EMOJIS['info']} سن: {user[2]}
{EMOJIS['group']} جنسیت: {user[3]}
{EMOJIS['document']} شناسه عددی: {user[5]}

{EMOJIS['places']} مکان درخواستی: {message.text}
                """
                
                try:
                    bot.send_message(ADMIN_ID, request_text)
                except:
                    pass
            
            bot.send_message(user_id, f"{EMOJIS['success']} درخواست شما با موفقیت ارسال شد!", reply_markup=main_menu(user_id))
            set_user_state(user_id, "HOME")
        else:
            bot.send_message(user_id, "لطفاً یکی از مکان‌های خود را انتخاب کنید:", reply_markup=back_home_buttons())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['admin']} بخش ادمین" and get_user_state(message.from_user.id) == "HOME" and message.from_user.id == ADMIN_ID)
def handle_admin(message):
    user_id = message.from_user.id
    bot.send_message(user_id, f"{EMOJIS['admin']} بخش مدیریت ادمین", reply_markup=admin_menu())
    set_user_state(user_id, "ADMIN")

@bot.message_handler(func=lambda message: message.text == "قرارگیری مکان برتر" and get_user_state(message.from_user.id) == "ADMIN")
def handle_admin_top_place(message):
    user_id = message.from_user.id
    bot.send_message(user_id, f"{EMOJIS['star']} مدیریت مکان‌های برتر", reply_markup=top_place_menu())
    set_user_state(user_id, "ADMIN_TOP_PLACE")

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['add_score']} اضافه کردن رای" and get_user_state(message.from_user.id) == "ADMIN_TOP_PLACE")
def handle_admin_add_vote(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
    set_user_state(user_id, "ADMIN_ADD_VOTE_TITLE")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_ADD_VOTE_TITLE")
def handle_admin_add_vote_title(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['star']} مدیریت مکان‌های برتر", reply_markup=top_place_menu())
        set_user_state(user_id, "ADMIN_TOP_PLACE")
    else:
        set_user_data(user_id, "place_title", message.text)
        bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_ADD_VOTE_USER_ID")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_ADD_VOTE_USER_ID")
def handle_admin_add_vote_user_id(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_ADD_VOTE_TITLE")
    elif message.text.isdigit():
        numeric_id = int(message.text)
        owner = get_user_by_numeric_id(numeric_id)
        
        if owner:
            set_user_data(user_id, "owner_id", numeric_id)
            bot.send_message(user_id, "لطفاً تعداد رای‌ها را وارد کنید:", reply_markup=back_button_only())
            set_user_state(user_id, "ADMIN_ADD_VOTE_COUNT")
        else:
            bot.send_message(user_id, "کاربری با این شناسه یافت نشد. لطفاً دوباره وارد کنید:", reply_markup=back_button_only())
    else:
        bot.send_message(user_id, "لطفاً یک شناسه عددی معتبر وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_ADD_VOTE_COUNT")
def handle_admin_add_vote_count(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_ADD_VOTE_USER_ID")
    elif message.text.isdigit() and int(message.text) > 0:
        set_user_data(user_id, "vote_count", int(message.text))
        bot.send_message(user_id, "لطفاً امتیاز رای‌ها را وارد کنید (بین 0 تا 10):", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_ADD_VOTE_RATING")
    else:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_ADD_VOTE_RATING")
def handle_admin_add_vote_rating(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً تعداد رای‌ها را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_ADD_VOTE_COUNT")
    elif message.text.replace('.', '', 1).isdigit():
        rating = float(message.text)
        if 0 <= rating <= 10:
            set_user_data(user_id, "vote_rating", rating)
            
            # نمایش اطلاعات برای تأیید
            place_title = get_user_data(user_id, "place_title")
            owner_id = get_user_data(user_id, "owner_id")
            vote_count = get_user_data(user_id, "vote_count")
            
            confirm_text = f"""
{EMOJIS['info']} اطلاعات رای‌ها:

{EMOJIS['document']} عنوان مکان: {place_title}
{EMOJIS['user']} شناسه صاحب مکان: {owner_id}
{EMOJIS['vote']} تعداد رای: {vote_count}
{EMOJIS['star']} امتیاز: {rating}

آیا از افزودن این رای‌ها اطمینان دارید؟
            """
            
            bot.send_message(user_id, confirm_text, reply_markup=confirm_cancel_buttons())
            set_user_state(user_id, "ADMIN_ADD_VOTE_CONFIRM")
        else:
            bot.send_message(user_id, "لطفاً امتیازی بین 0 تا 10 وارد کنید:", reply_markup=back_button_only())
    else:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_ADD_VOTE_CONFIRM")
def handle_admin_add_vote_confirm(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تایید":
        place_title = get_user_data(user_id, "place_title")
        owner_id = get_user_data(user_id, "owner_id")
        vote_count = get_user_data(user_id, "vote_count")
        vote_rating = get_user_data(user_id, "vote_rating")
        
        # پیدا کردن مکان
        owner = get_user_by_numeric_id(owner_id)
        if owner:
            user_places = get_user_places(owner[0])
            target_place = None
            
            for place in user_places:
                if place[4] == place_title:  # عنوان مکان
                    target_place = place
                    break
            
            if target_place:
                # افزودن رای‌ها
                for _ in range(vote_count):
                    # استفاده از یک user_id ساختگی برای رای ادمین
                    fake_user_id = -1 * random.randint(1000, 9999)
                    add_rating(target_place[0], fake_user_id, vote_rating)
                
                bot.send_message(user_id, f"{EMOJIS['success']} رای‌ها با موفقیت اضافه شدند!", reply_markup=top_place_menu())
                
                # اطلاع به صاحب مکان
                try:
                    bot.send_message(owner[0], f"{EMOJIS['star']} مکان شما '{place_title}' با موفقیت به بخش مکان‌های برتر اضافه شد! تبریک می‌گوییم!")
                except:
                    pass
            else:
                bot.send_message(user_id, "مکانی با این عنوان برای کاربر یافت نشد.", reply_markup=top_place_menu())
        else:
            bot.send_message(user_id, "کاربری با این شناسه یافت نشد.", reply_markup=top_place_menu())
        
        # پاک کردن داده‌های موقت
        keys_to_remove = ['place_title', 'owner_id', 'vote_count', 'vote_rating']
        for key in keys_to_remove:
            if key in user_data.get(user_id, {}):
                del user_data[user_id][key]
        
        set_user_state(user_id, "ADMIN_TOP_PLACE")
        
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        # پاک کردن داده‌های موقت
        keys_to_remove = ['place_title', 'owner_id', 'vote_count', 'vote_rating']
        for key in keys_to_remove:
            if key in user_data.get(user_id, {}):
                del user_data[user_id][key]
        
        bot.send_message(user_id, "عملیات لغو شد.", reply_markup=top_place_menu())
        set_user_state(user_id, "ADMIN_TOP_PLACE")
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های بالا را انتخاب کنید:", reply_markup=confirm_cancel_buttons())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['remove_score']} کم کردن رای" and get_user_state(message.from_user.id) == "ADMIN_TOP_PLACE")
def handle_admin_remove_vote(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
    set_user_state(user_id, "ADMIN_REMOVE_VOTE_TITLE")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_REMOVE_VOTE_TITLE")
def handle_admin_remove_vote_title(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['star']} مدیریت مکان‌های برتر", reply_markup=top_place_menu())
        set_user_state(user_id, "ADMIN_TOP_PLACE")
    else:
        set_user_data(user_id, "place_title", message.text)
        bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_REMOVE_VOTE_USER_ID")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_REMOVE_VOTE_USER_ID")
def handle_admin_remove_vote_user_id(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_REMOVE_VOTE_TITLE")
    elif message.text.isdigit():
        numeric_id = int(message.text)
        owner = get_user_by_numeric_id(numeric_id)
        
        if owner:
            set_user_data(user_id, "owner_id", numeric_id)
            bot.send_message(user_id, "لطفاً تعداد رای‌هایی که می‌خواهید حذف کنید را وارد کنید:", reply_markup=back_button_only())
            set_user_state(user_id, "ADMIN_REMOVE_VOTE_COUNT")
        else:
            bot.send_message(user_id, "کاربری با این شناسه یافت نشد. لطفاً دوباره وارد کنید:", reply_markup=back_button_only())
    else:
        bot.send_message(user_id, "لطفاً یک شناسه عددی معتبر وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_REMOVE_VOTE_COUNT")
def handle_admin_remove_vote_count(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_REMOVE_VOTE_USER_ID")
    elif message.text.isdigit() and int(message.text) > 0:
        set_user_data(user_id, "vote_count", int(message.text))
        
        # نمایش اطلاعات برای تأیید
        place_title = get_user_data(user_id, "place_title")
        owner_id = get_user_data(user_id, "owner_id")
        
        confirm_text = f"""
{EMOJIS['info']} اطلاعات حذف رای‌ها:

{EMOJIS['document']} عنوان مکان: {place_title}
{EMOJIS['user']} شناسه صاحب مکان: {owner_id}
{EMOJIS['vote']} تعداد رای برای حذف: {int(message.text)}

آیا از حذف این تعداد رای اطمینان دارید؟
        """
        
        bot.send_message(user_id, confirm_text, reply_markup=confirm_cancel_buttons())
        set_user_state(user_id, "ADMIN_REMOVE_VOTE_CONFIRM")
    else:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_REMOVE_VOTE_CONFIRM")
def handle_admin_remove_vote_confirm(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تایید":
        place_title = get_user_data(user_id, "place_title")
        owner_id = get_user_data(user_id, "owner_id")
        vote_count = get_user_data(user_id, "vote_count")
        
        # پیدا کردن مکان
        owner = get_user_by_numeric_id(owner_id)
        if owner:
            user_places = get_user_places(owner[0])
            target_place = None
            
            for place in user_places:
                if place[4] == place_title:  # عنوان مکان
                    target_place = place
                    break
            
            if target_place:
                # حذف برخی از رای‌ها (در واقعیت باید منطق پیچیده‌تری داشته باشیم)
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                
                # دریافت تعدادی از رای‌ها برای حذف
                c.execute("SELECT rowid FROM place_ratings WHERE place_id = ? LIMIT ?", (target_place[0], vote_count))
                ratings_to_delete = c.fetchall()
                
                if ratings_to_delete:
                    # حذف رای‌ها
                    for rating in ratings_to_delete:
                        c.execute("DELETE FROM place_ratings WHERE rowid = ?", (rating[0],))
                    
                    # به‌روزرسانی امتیاز مکان
                    c.execute("SELECT SUM(rating), COUNT(rating) FROM place_ratings WHERE place_id = ?", (target_place[0],))
                    result = c.fetchone()
                    
                    if result and result[1] > 0:
                        new_rating_sum = result[0] or 0
                        new_rating_count = result[1]
                        c.execute("UPDATE places SET rating_sum = ?, rating_count = ? WHERE place_id = ?", 
                                 (new_rating_sum, new_rating_count, target_place[0]))
                    else:
                        c.execute("UPDATE places SET rating_sum = 0, rating_count = 0 WHERE place_id = ?", 
                                 (target_place[0],))
                    
                    conn.commit()
                    conn.close()
                    
                    bot.send_message(user_id, f"{EMOJIS['success']} رای‌ها با موفقیت حذف شدند!", reply_markup=top_place_menu())
                    
                    # اطلاع به صاحب مکان در صورت حذف کامل از برترها
                    current_rating = get_place_rating(target_place[0])
                    if current_rating < 5:  # حداقل امتیاز برای مکان برتر
                        try:
                            bot.send_message(owner[0], f"{EMOJIS['warning']} مکان شما '{place_title}' از بخش مکان‌های برتر حذف شد.")
                        except:
                            pass
                else:
                    conn.close()
                    bot.send_message(user_id, "رای‌ای برای حذف یافت نشد.", reply_markup=top_place_menu())
            else:
                bot.send_message(user_id, "مکانی با این عنوان برای کاربر یافت نشد.", reply_markup=top_place_menu())
        else:
            bot.send_message(user_id, "کاربری با این شناسه یافت نشد.", reply_markup=top_place_menu())
        
        # پاک کردن داده‌های موقت
        keys_to_remove = ['place_title', 'owner_id', 'vote_count']
        for key in keys_to_remove:
            if key in user_data.get(user_id, {}):
                del user_data[user_id][key]
        
        set_user_state(user_id, "ADMIN_TOP_PLACE")
        
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        # پاک کردن داده‌های موقت
        keys_to_remove = ['place_title', 'owner_id', 'vote_count']
        for key in keys_to_remove:
            if key in user_data.get(user_id, {}):
                del user_data[user_id][key]
        
        bot.send_message(user_id, "عملیات لغو شد.", reply_markup=top_place_menu())
        set_user_state(user_id, "ADMIN_TOP_PLACE")
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های بالا را انتخاب کنید:", reply_markup=confirm_cancel_buttons())

@bot.message_handler(func=lambda message: message.text == "مدیریت نظرات" and get_user_state(message.from_user.id) == "ADMIN")
def handle_admin_manage_comments(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
    set_user_state(user_id, "ADMIN_MANAGE_COMMENTS_TITLE")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_MANAGE_COMMENTS_TITLE")
def handle_admin_manage_comments_title(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, f"{EMOJIS['admin']} بخش مدیریت ادمین", reply_markup=admin_menu())
        set_user_state(user_id, "ADMIN")
    else:
        set_user_data(user_id, "place_title", message.text)
        bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_MANAGE_COMMENTS_USER_ID")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_MANAGE_COMMENTS_USER_ID")
def handle_admin_manage_comments_user_id(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_MANAGE_COMMENTS_TITLE")
    elif message.text.isdigit():
        numeric_id = int(message.text)
        owner = get_user_by_numeric_id(numeric_id)
        
        if owner:
            set_user_data(user_id, "owner_id", numeric_id)
            bot.send_message(user_id, "لطفاً کلمه اول نظر مورد نظر برای حذف را وارد کنید:", reply_markup=back_button_only())
            set_user_state(user_id, "ADMIN_MANAGE_COMMENTS_KEYWORD")
        else:
            bot.send_message(user_id, "کاربری با این شناسه یافت نشد. لطفاً دوباره وارد کنید:", reply_markup=back_button_only())
    else:
        bot.send_message(user_id, "لطفاً یک شناسه عددی معتبر وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_MANAGE_COMMENTS_KEYWORD")
def handle_admin_manage_comments_keyword(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_MANAGE_COMMENTS_USER_ID")
    else:
        set_user_data(user_id, "keyword", message.text)
        bot.send_message(user_id, "لطفاً شناسه عددی کاربری که نظر داده را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_MANAGE_COMMENTS_COMMENTER_ID")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_MANAGE_COMMENTS_COMMENTER_ID")
def handle_admin_manage_comments_commenter_id(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "لطفاً کلمه اول نظر مورد نظر برای حذف را وارد کنید:", reply_markup=back_button_only())
        set_user_state(user_id, "ADMIN_MANAGE_COMMENTS_KEYWORD")
    elif message.text.isdigit():
        commenter_numeric_id = int(message.text)
        commenter = get_user_by_numeric_id(commenter_numeric_id)
        
        if commenter:
            set_user_data(user_id, "commenter_id", commenter_numeric_id)
            
            # نمایش اطلاعات برای تأیید
            place_title = get_user_data(user_id, "place_title")
            owner_id = get_user_data(user_id, "owner_id")
            keyword = get_user_data(user_id, "keyword")
            
            confirm_text = f"""
{EMOJIS['info']} اطلاعات حذف نظر:

{EMOJIS['document']} عنوان مکان: {place_title}
{EMOJIS['user']} شناسه صاحب مکان: {owner_id}
{EMOJIS['edit']} کلمه کلیدی: {keyword}
{EMOJIS['user']} شناسه نظر دهنده: {commenter_numeric_id}

آیا از حذف این نظر اطمینان دارید؟
            """
            
            bot.send_message(user_id, confirm_text, reply_markup=confirm_cancel_buttons())
            set_user_state(user_id, "ADMIN_MANAGE_COMMENTS_CONFIRM")
        else:
            bot.send_message(user_id, "کاربری با این شناسه یافت نشد. لطفاً دوباره وارد کنید:", reply_markup=back_button_only())
    else:
        bot.send_message(user_id, "لطفاً یک شناسه عددی معتبر وارد کنید:", reply_markup=back_button_only())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == "ADMIN_MANAGE_COMMENTS_CONFIRM")
def handle_admin_manage_comments_confirm(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تایید":
        place_title = get_user_data(user_id, "place_title")
        owner_id = get_user_data(user_id, "owner_id")
        keyword = get_user_data(user_id, "keyword")
        commenter_id = get_user_data(user_id, "commenter_id")
        
        # پیدا کردن مکان و نظر
        owner = get_user_by_numeric_id(owner_id)
        commenter = get_user_by_numeric_id(commenter_id)
        
        if owner and commenter:
            user_places = get_user_places(owner[0])
            target_place = None
            
            for place in user_places:
                if place[4] == place_title:  # عنوان مکان
                    target_place = place
                    break
            
            if target_place:
                # پیدا کردن نظر بر اساس کلمه کلیدی
                comments = get_comments(target_place[0])
                target_comment = None
                
                for comment in comments:
                    if comment[1] == target_place[0] and comment[2] == commenter[0] and comment[3].startswith(keyword):
                        target_comment = comment
                        break
                
                if target_comment:
                    # حذف نظر
                    delete_comment(target_comment[0])
                    
                    bot.send_message(user_id, f"{EMOJIS['success']} نظر با موفقیت حذف شد!", reply_markup=admin_menu())
                    
                    # اطلاع به نظر دهنده
                    try:
                        bot.send_message(commenter[0], f"{EMOJIS['warning']} نظر شما در مکان '{place_title}' به دلیل نقض قوانین توسط ادمین حذف شد.")
                    except:
                        pass
                else:
                    bot.send_message(user_id, "نظری با این مشخصات یافت نشد.", reply_markup=admin_menu())
            else:
                bot.send_message(user_id, "مکانی با این عنوان برای کاربر یافت نشد.", reply_markup=admin_menu())
        else:
            bot.send_message(user_id, "کاربری با این شناسه یافت نشد.", reply_markup=admin_menu())
        
        # پاک کردن داده‌های موقت
        keys_to_remove = ['place_title', 'owner_id', 'keyword', 'commenter_id']
        for key in keys_to_remove:
            if key in user_data.get(user_id, {}):
                del user_data[user_id][key]
        
        set_user_state(user_id, "ADMIN")
        
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        # پاک کردن داده‌های موقت
        keys_to_remove = ['place_title', 'owner_id', 'keyword', 'commenter_id']
        for key in keys_to_remove:
            if key in user_data.get(user_id, {}):
                del user_data[user_id][key]
        
        bot.send_message(user_id, "عملیات لغو شد.", reply_markup=admin_menu())
        set_user_state(user_id, "ADMIN")
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های بالا را انتخاب کنید:", reply_markup=confirm_cancel_buttons())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['back']} برگشت" and get_user_state(message.from_user.id) in ["PROFILE", "PLACES", "ADMIN", "ADMIN_TOP_PLACE"])
def handle_back(message):
    user_id = message.from_user.id
    current_state = get_user_state(user_id)
    
    if current_state == "PROFILE":
        bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")
    elif current_state == "PLACES":
        bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")
    elif current_state == "ADMIN":
        bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu(user_id))
        set_user_state(user_id, "HOME")
    elif current_state == "ADMIN_TOP_PLACE":
        bot.send_message(user_id, f"{EMOJIS['admin']} بخش مدیریت ادمین", reply_markup=admin_menu())
        set_user_state(user_id, "ADMIN")

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['home']} صفحه اصلی")
def handle_home(message):
    user_id = message.from_user.id
    bot.send_message(user_id, f"{EMOJIS['home']} صفحه اصلی", reply_markup=main_menu(user_id))
    set_user_state(user_id, "HOME")

@bot.callback_query_handler(func=lambda call: call.data.startswith('help_'))
def handle_help_callback(call):
    user_id = call.from_user.id
    
    if call.data.startswith('help_next_'):
        page = int(call.data.split('_')[2])
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, 
                             text=get_help_message(page), reply_markup=get_help_keyboard(page))
    
    elif call.data.startswith('help_prev_'):
        page = int(call.data.split('_')[2])
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, 
                             text=get_help_message(page), reply_markup=get_help_keyboard(page))

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['help']} راهنما" and get_user_state(message.from_user.id) == "HOME")
def handle_help(message):
    user_id = message.from_user.id
    bot.send_message(user_id, get_help_message(1), reply_markup=get_help_keyboard(1))

# هندلر برای سایر پیام‌ها
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    user_id = message.from_user.id
    current_state = get_user_state(user_id)
    
    if current_state == "HOME":
        bot.send_message(user_id, "لطفاً از منوی زیر انتخاب کنید:", reply_markup=main_menu(user_id))
    else:
        bot.send_message(user_id, "لطفاً از دکمه‌های کیبورد استفاده کنید.", reply_markup=back_home_buttons())

# راه‌اندازی ربات
if __name__ == "__main__":
    print("ربات در حال راه‌اندازی است...")
    
    # حذف webhook قبلی
    bot.remove_webhook()
    
    # تنظیم webhook جدید
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    
    # راه‌اندازی سرور Flask
    app.run(host="0.0.0.0", port=PORT)