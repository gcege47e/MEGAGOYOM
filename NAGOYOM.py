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
    "cancel": "❌",
    "location": "🗺️",
    "phone": "📞",
    "time": "⏰"
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
user_blocked_contacts = {}  # برای ذخیره کاربرانی که بلاک شده‌اند

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
    c.execute('''CREATE TABLE IF NOT EXISTS blocked_contacts (
                 block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 blocker_id INTEGER,
                 blocked_id INTEGER,
                 place_id INTEGER,
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
        "فروشگاه لوازم خانگی و الکترونیک (لوازم برقی، دیجital)",
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
        "تتو و микропیگمنتیشن (تاتو، میکروپیگمنتیشن)",
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
        "باشگاه‌های گolf و تنیس",
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
        "مراکز رزرواسیون (رزرو هotel، بلیط)",
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
        "اداره پost (پست، پیک موتوری)",
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
        "مراکز آموزش علوم مختلف (ریاضی، فیزiku، شیمی)",
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
        "مراکز اکوتوریism (اکوتوریسم، گردشگری طبیعت)",
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

def is_contact_blocked(blocker_id, blocked_id, place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM blocked_contacts WHERE blocker_id = ? AND blocked_id = ? AND place_id = ?", 
              (blocker_id, blocked_id, place_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def block_contact(blocker_id, blocked_id, place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO blocked_contacts (blocker_id, blocked_id, place_id) VALUES (?, ?, ?)",
              (blocker_id, blocked_id, place_id))
    conn.commit()
    conn.close()

def unblock_contact(blocker_id, blocked_id, place_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM blocked_contacts WHERE blocker_id = ? AND blocked_id = ? AND place_id = ?",
              (blocker_id, blocked_id, place_id))
    conn.commit()
    conn.close()

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
    keyboard.row(f"{EMOJIS['edit']} ویرایش پروفایل", f"{EMOJIS['view']} مشاهده پروفایل")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def places_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['add']} افزودن مکان", f"{EMOJIS['view']} مشاهده مکان‌ها")
    keyboard.row(f"{EMOJIS['location']} جستجوی مکان‌ها")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def admin_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['add']} اضافه کردن رای", f"{EMOJIS['remove_score']} کم کردن رای")
    keyboard.row(f"{EMOJIS['document']} مدیریت نظرات")
    keyboard.row(f"{EMOJIS['news']} مدیریت اخبار", f"{EMOJIS['view']} مشاهده گزارش‌ها")
    keyboard.row(f"{EMOJIS['view']} مشاهده درخواست‌های مکان برتر")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def back_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def back_home_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def confirm_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['confirm']} تأیید", f"{EMOJIS['cancel']} انصراف")
    return keyboard

def comment_menu(has_comment=False):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if has_comment:
        keyboard.row(f"{EMOJIS['delete']} حذف نظر")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def message_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['reply']} جواب دادن", f"{EMOJIS['block']} بلاک کردن")
    keyboard.row(f"{EMOJIS['unblock']} رفع بلاک", f"{EMOJIS['back']} برگشت")
    return keyboard

def help_menu(page=1):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if page == 1:
        keyboard.row(f"{EMOJIS['next']} صفحه بعدی")
    elif page == 2:
        keyboard.row(f"{EMOJIS['previous']} صفحه قبلی", f"{EMOJIS['next']} صفحه بعدی")
    elif page == 3:
        keyboard.row(f"{EMOJIS['previous']} صفحه قبلی")
    keyboard.row(f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

# راهنمای تعاملی
HELP_PAGES = [
    f"""
{EMOJIS['help']} راهنمای بخش‌های اصلی {EMOJIS['help']}

{EMOJIS['profile']} بخش پروفایل:
- مشاهده و ویرایش اطلاعات شخصی
- شناسه عددی یکتا برای هر کاربر
- امتیاز کاربر بر اساس فعالیت‌ها

{EMOJIS['places']} بخش مکان‌ها:
- افزودن مکان جدید با جزئیات کامل
- مشاهده و جستجوی مکان‌ها
- مدیریت مکان‌های اضافه شده

{EMOJIS['rating']} بخش مکان‌های برتر:
- مشاهده مکان‌های دارای امتیاز برتر
- درخواست قرارگیری مکان در بخش برترها
    """,
    
    f"""
{EMOJIS['help']} راهنمای بخش‌های ویژه {EMOJIS['help']}

{EMOJIS['star']} بخش کاربران برتر:
- مشاهده کاربران فعال و پرامتیاز
- رقابت برای کسب امتیاز بیشتر

{EMOJIS['link']} بخش لینک‌ها:
- دسترسی سریع به لینک‌های مهم
- اشتراک‌گذاری لینک ربات

{EMOJIS['report']} بخش گزارش:
- ارسال گزارش و مشکلات به ادمین
- پیگیری گزارش‌های ارسالی

{EMOJIS['buy']} بخش خرید مکان برتر:
- درخواست قرارگیری مکان در بخش برترها
- پرداخت هزینه و بررسی توسط ادمین
    """,
    
    f"""
{EMOJIS['help']} راهنمای تعامل با مکان‌ها {EMOJIS['help']}

{EMOJIS['comment']} بخش نظرات:
- ثبت نظر برای مکان‌های مختلف
- مشاهده نظرات دیگر کاربران
- مدیریت نظرات ارسالی

{EMOJIS['message']} بخش پیام به صاحب مکان:
- ارسال پیام مستقیم به صاحب مکان
- امکان پاسخگویی و ارتباط
- مدیریت بلاک و آنبلاک کاربران

{EMOJIS['admin']} بخش ادمین (فقط برای مدیران):
- مدیریت کاربران و مکان‌ها
- بررسی گزارش‌ها و درخواست‌ها
- اعطا و کاهش امتیاز
    """
]

# هندلرها
@app.route('/' + API_TOKEN, methods=['POST'])
def get_message():
    json_update = request.stream.read().decode('utf-8')
    update = types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + '/' + API_TOKEN)
    return 'Hello from GoyimNama!', 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # ذخیره کاربر در دیتابیس
    save_user(user_id, user_name, None, None)
    
    # نمایش پیام خوش‌آمدگویی
    bot.send_message(user_id, WELCOME_MESSAGE, reply_markup=types.ReplyKeyboardRemove())
    
    # ایجاد دکمه‌های تأیید قوانین
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['confirm']} قوانین را می‌پذیرم", f"{EMOJIS['cancel']} نمی‌پذیرم")
    
    bot.send_message(user_id, "لطفاً گزینه مورد نظر را انتخاب کنید:", reply_markup=keyboard)
    
    # تنظیم حالت کاربر
    user_states[user_id] = "waiting_for_rules_acceptance"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_rules_acceptance")
def handle_rules_acceptance(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} قوانین را می‌پذیرم":
        bot.send_message(user_id, f"{EMOJIS['success']} قوانین با موفقیت تأیید شد! اکنون می‌توانید از امکانات ربات استفاده کنید.")
        user_states[user_id] = None
        show_main_menu(user_id)
    elif message.text == f"{EMOJIS['cancel']} نمی‌پذیرم":
        bot.send_message(user_id, f"{EMOJIS['error']} متأسفیم که قوانین را نمی‌پذیرید. بدون پذیرش قوانین نمی‌توانید از ربات استفاده کنید.")
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های بالا را انتخاب کنید.")

def show_main_menu(user_id):
    bot.send_message(user_id, "منوی اصلی:", reply_markup=main_menu(user_id))

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['profile']} پروفایل")
def handle_profile(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "بخش پروفایل:", reply_markup=profile_menu())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['places']} مکان‌ها")
def handle_places(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "بخش مکان‌ها:", reply_markup=places_menu())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['back']} برگشت")
def handle_back(message):
    user_id = message.from_user.id
    show_main_menu(user_id)

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['home']} صفحه اصلی")
def handle_home(message):
    user_id = message.from_user.id
    show_main_menu(user_id)

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['edit']} ویرایش پروفایل")
def handle_edit_profile(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً نام خود را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_name"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_name")
def handle_name_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "ویرایش پروفایل لغو شد.", reply_markup=profile_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id] = {"name": message.text}
    bot.send_message(user_id, "لطفاً سن خود را وارد کنید (عدد انگلیسی):", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_age"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_age")
def handle_age_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "ویرایش پروفایل لغو شد.", reply_markup=profile_menu())
        user_states[user_id] = None
        return
    
    try:
        age = int(message.text)
        if age < 1 or age > 120:
            bot.send_message(user_id, "لطفاً سن معتبر وارد کنید (بین 1 تا 120):", reply_markup=back_menu())
            return
        
        user_data[user_id]["age"] = age
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("مرد", "زن")
        keyboard.row(f"{EMOJIS['back']} برگشت")
        
        bot.send_message(user_id, "لطفاً جنسیت خود را انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "waiting_for_gender"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_gender")
def handle_gender_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "ویرایش پروفایل لغو شد.", reply_markup=profile_menu())
        user_states[user_id] = None
        return
    
    if message.text not in ["مرد", "زن"]:
        bot.send_message(user_id, "لطفاً جنسیت معتبر انتخاب کنید:", reply_markup=back_menu())
        return
    
    user_data[user_id]["gender"] = message.text
    
    # ذخیره اطلاعات کاربر
    save_user(user_id, user_data[user_id]["name"], user_data[user_id]["age"], user_data[user_id]["gender"])
    
    bot.send_message(user_id, f"{EMOJIS['success']} پروفایل شما با موفقیت به‌روزرسانی شد!", reply_markup=profile_menu())
    user_states[user_id] = None

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['view']} مشاهده پروفایل")
def handle_view_profile(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user:
        profile_text = f"""
{EMOJIS['profile']} اطلاعات پروفایل:

{EMOJIS['user']} نام: {user[1]}
{EMOJIS['time']} سن: {user[2] if user[2] else 'تعیین نشده'}
{EMOJIS['info']} جنسیت: {user[3] if user[3] else 'تعیین نشده'}
{EMOJIS['score']} امتیاز: {user[4]}
{EMOJIS['document']} شناسه عددی: {user[5]}
        """
        bot.send_message(user_id, profile_text, reply_markup=profile_menu())
    else:
        bot.send_message(user_id, f"{EMOJIS['error']} اطلاعات پروفایل یافت نشد. لطفاً ابتدا پروفایل خود را تکمیل کنید.", reply_markup=profile_menu())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['add']} افزودن مکان")
def handle_add_place(message):
    user_id = message.from_user.id
    
    # ایجاد کیبورد برای انتخاب دسته‌بندی
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    categories = list(PLACE_CATEGORIES.keys())
    
    # تقسیم دسته‌بندی‌ها به ردیف‌های 2 تایی
    for i in range(0, len(categories), 2):
        if i + 1 < len(categories):
            keyboard.row(categories[i], categories[i + 1])
        else:
            keyboard.row(categories[i])
    
    keyboard.row(f"{EMOJIS['back']} برگشت")
    
    bot.send_message(user_id, "لطفاً دسته‌بندی مکان خود را انتخاب کنید:", reply_markup=keyboard)
    user_states[user_id] = "waiting_for_category"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_category")
def handle_category_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    if message.text not in PLACE_CATEGORIES:
        bot.send_message(user_id, "لطفاً یک دسته‌بندی معتبر انتخاب کنید:", reply_markup=back_menu())
        return
    
    user_data[user_id] = {"category": message.text}
    
    # ایجاد کیبورد برای انتخاب زیردسته
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    subcategories = PLACE_CATEGORIES[message.text]
    
    for subcat in subcategories:
        keyboard.row(subcat)
    
    keyboard.row(f"{EMOJIS['back']} برگشت")
    
    bot.send_message(user_id, "لطفاً زیردسته مکان خود را انتخاب کنید:", reply_markup=keyboard)
    user_states[user_id] = "waiting_for_subcategory"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_subcategory")
def handle_subcategory_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id]["subcategory"] = message.text
    bot.send_message(user_id, "لطفاً عنوان مکان را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_title"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_title")
def handle_title_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id]["title"] = message.text
    bot.send_message(user_id, "لطفاً توضیحات مکان را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_description"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_description")
def handle_description_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id]["description"] = message.text
    bot.send_message(user_id, "لطفاً آدرس مکان را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_address"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_address")
def handle_address_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id]["address"] = message.text
    bot.send_message(user_id, "لطفاً شماره تلفن مکان را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_phone"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_phone")
def handle_phone_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id]["phone"] = message.text
    bot.send_message(user_id, "لطفاً ساعت کاری صبح مکان را وارد کنید (مثال: 8:00-12:00):", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_morning_shift"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_morning_shift")
def handle_morning_shift_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id]["morning_shift"] = message.text
    bot.send_message(user_id, "لطفاً ساعت کاری عصر مکان را وارد کنید (مثال: 16:00-20:00):", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_afternoon_shift"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_afternoon_shift")
def handle_afternoon_shift_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id]["afternoon_shift"] = message.text
    bot.send_message(user_id, "لطفاً عکس مکان را ارسال کنید (حداکثر 8 عکس):", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_photo"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_photo", content_types=['photo'])
def handle_photo_input(message):
    user_id = message.from_user.id
    
    if 'photo' not in user_data[user_id]:
        user_data[user_id]['photo'] = []
    
    # ذخیره file_id عکس
    user_data[user_id]['photo'].append(message.photo[-1].file_id)
    
    if len(user_data[user_id]['photo']) >= 8:
        # کاربر حداکثر عکس را ارسال کرده
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row(f"{EMOJIS['confirm']} تأیید و ثبت مکان")
        keyboard.row(f"{EMOJIS['cancel']} انصراف")
        
        bot.send_message(user_id, f"{EMOJIS['success']} حداکثر عکس دریافت شد. برای ثبت مکان تأیید کنید.", reply_markup=keyboard)
        user_states[user_id] = "waiting_for_place_confirmation"
    else:
        bot.send_message(user_id, f"{EMOJIS['success']} عکس دریافت شد. می‌توانید تا 8 عکس ارسال کنید یا برای ثبت مکان تأیید کنید.", reply_markup=confirm_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_photo")
def handle_photo_text_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تأیید":
        if 'photo' not in user_data[user_id] or not user_data[user_id]['photo']:
            bot.send_message(user_id, "لطفاً حداقل یک عکس ارسال کنید.", reply_markup=back_menu())
            return
        
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row(f"{EMOJIS['confirm']} تأیید و ثبت مکان")
        keyboard.row(f"{EMOJIS['cancel']} انصراف")
        
        bot.send_message(user_id, "برای ثبت مکان تأیید کنید:", reply_markup=keyboard)
        user_states[user_id] = "waiting_for_place_confirmation"
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
    else:
        bot.send_message(user_id, "لطفاً عکس مکان را ارسال کنید یا برای ثبت مکان تأیید کنید:", reply_markup=confirm_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_place_confirmation")
def handle_place_confirmation(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تأیید و ثبت مکان":
        # ذخیره مکان در دیتابیس
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # تبدیل لیست عکس‌ها به رشته جدا شده با کاما
        photos_str = ",".join(user_data[user_id]['photo'])
        
        c.execute('''INSERT INTO places 
                    (user_id, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (user_id, user_data[user_id]['category'], user_data[user_id]['subcategory'],
                  user_data[user_id]['title'], user_data[user_id]['description'],
                  user_data[user_id]['address'], user_data[user_id]['phone'],
                  photos_str, user_data[user_id]['morning_shift'],
                  user_data[user_id]['afternoon_shift']))
        
        conn.commit()
        place_id = c.lastrowid
        conn.close()
        
        # ارسال تأییدیه
        bot.send_message(user_id, f"{EMOJIS['success']} مکان شما با موفقیت ثبت شد!", reply_markup=places_menu())
        
        # ارسال اطلاعات مکان
        place_info = f"""
{EMOJIS['places']} مکان ثبت شده:

{EMOJIS['info']} دسته‌بندی: {user_data[user_id]['category']}
{EMOJIS['info']} زیردسته: {user_data[user_id]['subcategory']}
{EMOJIS['document']} عنوان: {user_data[user_id]['title']}
{EMOJIS['info']} توضیحات: {user_data[user_id]['description']}
{EMOJIS['location']} آدرس: {user_data[user_id]['address']}
{EMOJIS['phone']} تلفن: {user_data[user_id]['phone']}
{EMOJIS['time']} ساعت کاری صبح: {user_data[user_id]['morning_shift']}
{EMOJIS['time']} ساعت کاری عصر: {user_data[user_id]['afternoon_shift']}
        """
        
        # ارسال عکس‌ها به صورت گروهی
        if len(user_data[user_id]['photo']) > 0:
            media = [types.InputMediaPhoto(photo) for photo in user_data[user_id]['photo']]
            bot.send_media_group(user_id, media)
        
        bot.send_message(user_id, place_info, reply_markup=places_menu())
        
        # پاک کردن داده‌های موقت
        if user_id in user_data:
            del user_data[user_id]
        user_states[user_id] = None
        
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        bot.send_message(user_id, "افزودن مکان لغو شد.", reply_markup=places_menu())
        
        # پاک کردن داده‌های موقت
        if user_id in user_data:
            del user_data[user_id]
        user_states[user_id] = None
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=confirm_menu())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['view']} مشاهده مکان‌ها")
def handle_view_places(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM places WHERE user_id = ?", (user_id,))
    places = c.fetchall()
    conn.close()
    
    if not places:
        bot.send_message(user_id, f"{EMOJIS['error']} شما هیچ مکانی ثبت نکرده‌اید.", reply_markup=places_menu())
        return
    
    for place in places:
        place_info = f"""
{EMOJIS['places']} مکان شما:

{EMOJIS['info']} دسته‌بندی: {place[2]}
{EMOJIS['info']} زیردسته: {place[3]}
{EMOJIS['document']} عنوان: {place[4]}
{EMOJIS['info']} توضیحات: {place[5]}
{EMOJIS['location']} آدرس: {place[6]}
{EMOJIS['phone']} تلفن: {place[7]}
{EMOJIS['time']} ساعت کاری صبح: {place[9]}
{EMOJIS['time']} ساعت کاری عصر: {place[10]}
{EMOJIS['score']} امتیاز: {place[11] / place[12] if place[12] > 0 else 0:.1f} ({place[12]} رأی)
        """
        
        # ارسال عکس‌ها اگر وجود دارند
        if place[8]:
            photo_ids = place[8].split(',')
            if len(photo_ids) > 0:
                media = [types.InputMediaPhoto(photo_id) for photo_id in photo_ids]
                bot.send_media_group(user_id, media)
        
        bot.send_message(user_id, place_info, reply_markup=places_menu())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['location']} جستجوی مکان‌ها")
def handle_search_places(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً آدرس یا نام مکان مورد نظر را برای جستجو وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_search_query"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_search_query")
def handle_search_query(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "جستجو لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    search_query = message.text.lower()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM places")
    all_places = c.fetchall()
    conn.close()
    
    found_places = []
    
    for place in all_places:
        # جستجو در عنوان، توضیحات و آدرس
        title = place[4].lower() if place[4] else ""
        description = place[5].lower() if place[5] else ""
        address = place[6].lower() if place[6] else ""
        
        # جستجوی پیشرفته با تقسیم کلمات
        query_words = search_query.split()
        title_words = title.split()
        address_words = address.split()
        
        # بررسی تطابق کلمات
        title_match = any(word in title for word in query_words) or any(title_word in search_query for title_word in title_words)
        address_match = any(word in address for word in query_words) or any(address_word in search_query for address_word in address_words)
        description_match = any(word in description for word in query_words)
        
        if title_match or address_match or description_match:
            found_places.append(place)
    
    if not found_places:
        bot.send_message(user_id, f"{EMOJIS['error']} هیچ مکانی با مشخصات وارد شده یافت نشد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    # نمایش مکان‌های یافت شده
    for place in found_places:
        place_info = f"""
{EMOJIS['places']} مکان یافت شده:

{EMOJIS['info']} دسته‌بندی: {place[2]}
{EMOJIS['info']} زیردسته: {place[3]}
{EMOJIS['document']} عنوان: {place[4]}
{EMOJIS['info']} توضیحات: {place[5]}
{EMOJIS['location']} آدرس: {place[6]}
{EMOJIS['phone']} تلفن: {place[7]}
{EMOJIS['time']} ساعت کاری صبح: {place[9]}
{EMOJIS['time']} ساعت کاری عصر: {place[10]}
{EMOJIS['score']} امتیاز: {place[11] / place[12] if place[12] > 0 else 0:.1f} ({place[12]} رأی)
        """
        
        # ارسال عکس‌ها اگر وجود دارند
        if place[8]:
            photo_ids = place[8].split(',')
            if len(photo_ids) > 0:
                media = [types.InputMediaPhoto(photo_id) for photo_id in photo_ids]
                bot.send_media_group(user_id, media)
        
        # ایجاد دکمه‌های تعامل با مکان
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton(f"{EMOJIS['comment']} نظر دادن", callback_data=f"comment_{place[0]}"),
            types.InlineKeyboardButton(f"{EMOJIS['message']} ارسال پیام", callback_data=f"message_{place[0]}")
        )
        keyboard.row(
            types.InlineKeyboardButton(f"{EMOJIS['view']} مشاهده نظرات", callback_data=f"view_comments_{place[0]}")
        )
        
        bot.send_message(user_id, place_info, reply_markup=keyboard)
    
    user_states[user_id] = None

@bot.callback_query_handler(func=lambda call: call.data.startswith('comment_'))
def handle_comment_callback(call):
    user_id = call.from_user.id
    place_id = int(call.data.split('_')[1])
    
    bot.send_message(user_id, "لطفاً نظر خود را برای این مکان وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = f"waiting_for_comment_{place_id}"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, '').startswith('waiting_for_comment_'))
def handle_comment_input(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    place_id = int(state.split('_')[-1])
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "ثبت نظر لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    comment_text = message.text
    
    # ذخیره نظر در دیتابیس
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO comments (place_id, user_id, comment_text) VALUES (?, ?, ?)",
              (place_id, user_id, comment_text))
    conn.commit()
    
    # دریافت اطلاعات مکان
    c.execute("SELECT title, user_id FROM places WHERE place_id = ?", (place_id,))
    place = c.fetchone()
    conn.close()
    
    if place:
        place_title = place[0]
        place_owner_id = place[1]
        
        # ارسال تأییدیه به کاربر
        bot.send_message(user_id, f"{EMOJIS['success']} نظر شما با موفقیت ثبت شد!", reply_markup=places_menu())
        
        # ارسال اطلاعیه به صاحب مکان (اگر با کاربر فعلی متفاوت است)
        if place_owner_id != user_id:
            owner_user = get_user(place_owner_id)
            if owner_user:
                owner_name = owner_user[1]
                commenter_user = get_user(user_id)
                commenter_name = commenter_user[1] if commenter_user else "ناشناس"
                commenter_age = commenter_user[2] if commenter_user and commenter_user[2] else "نامشخص"
                commenter_gender = commenter_user[3] if commenter_user and commenter_user[3] else "نامشخص"
                commenter_numeric_id = commenter_user[5] if commenter_user else "نامشخص"
                
                notification_text = f"""
{EMOJIS['comment']} اطلاعیه نظر جدید:

کاربر {commenter_name} ({commenter_age} سال، {commenter_gender}) نظر جدیدی برای مکان شما "{place_title}" ثبت کرده است.

متن نظر:
{comment_text}

شناسه عددی کاربر: {commenter_numeric_id}
                """
                
                bot.send_message(place_owner_id, notification_text)
    
    user_states[user_id] = None

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_comments_'))
def handle_view_comments_callback(call):
    user_id = call.from_user.id
    place_id = int(call.data.split('_')[2])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT c.comment_text, u.name, u.age, u.gender, u.numeric_id FROM comments c JOIN users u ON c.user_id = u.user_id WHERE c.place_id = ?", (place_id,))
    comments = c.fetchall()
    conn.close()
    
    if not comments:
        bot.send_message(user_id, f"{EMOJIS['error']} هیچ نظری برای این مکان ثبت نشده است.")
        return
    
    comments_text = f"{EMOJIS['comment']} نظرات مکان:\n\n"
    
    for i, comment in enumerate(comments, 1):
        comment_text, commenter_name, commenter_age, commenter_gender, commenter_numeric_id = comment
        comments_text += f"{i}. {commenter_name} ({commenter_age} سال، {commenter_gender}):\n{comment_text}\n"
        comments_text += f"شناسه عددی: {commenter_numeric_id}\n"
        comments_text += "─" * 20 + "\n"
    
    bot.send_message(user_id, comments_text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('message_'))
def handle_message_callback(call):
    user_id = call.from_user.id
    place_id = int(call.data.split('_')[1])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, title FROM places WHERE place_id = ?", (place_id,))
    place = c.fetchone()
    conn.close()
    
    if not place:
        bot.send_message(user_id, f"{EMOJIS['error']} مکان مورد نظر یافت نشد.")
        return
    
    place_owner_id = place[0]
    place_title = place[1]
    
    # بررسی آیا کاربر بلاک شده است
    if is_contact_blocked(place_owner_id, user_id, place_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما توسط صاحب این مکان بلاک شده‌اید و نمی‌توانید پیام ارسال کنید.")
        return
    
    user_data[user_id] = {
        "message_place_id": place_id,
        "message_owner_id": place_owner_id,
        "message_place_title": place_title
    }
    
    bot.send_message(user_id, "لطفاً پیامی که می‌خواهید برای صاحب مکان ارسال کنید را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_message_text"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_message_text")
def handle_message_text_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "ارسال پیام لغو شد.", reply_markup=places_menu())
        user_states[user_id] = None
        return
    
    message_text = message.text
    place_id = user_data[user_id]["message_place_id"]
    place_owner_id = user_data[user_id]["message_owner_id"]
    place_title = user_data[user_id]["message_place_title"]
    
    # ارسال پیام به صاحب مکان
    sender_user = get_user(user_id)
    sender_name = sender_user[1] if sender_user else "ناشناس"
    sender_age = sender_user[2] if sender_user and sender_user[2] else "نامشخص"
    sender_gender = sender_user[3] if sender_user and sender_user[3] else "نامشخص"
    sender_numeric_id = sender_user[5] if sender_user else "نامشخص"
    
    message_to_owner = f"""
{EMOJIS['message']} پیام جدید از کاربر:

از: {sender_name} ({sender_age} سال، {sender_gender})
برای مکان: {place_title}

متن پیام:
{message_text}

شناسه عددی کاربر: {sender_numeric_id}
    """
    
    # ایجاد دکمه‌های پاسخ، بلاک و آنبلاک
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(f"{EMOJIS['reply']} پاسخ", callback_data=f"reply_{user_id}_{place_id}"),
        types.InlineKeyboardButton(f"{EMOJIS['block']} بلاک", callback_data=f"block_{user_id}_{place_id}")
    )
    keyboard.row(
        types.InlineKeyboardButton(f"{EMOJIS['unblock']} آنبلاک", callback_data=f"unblock_{user_id}_{place_id}")
    )
    
    bot.send_message(place_owner_id, message_to_owner, reply_markup=keyboard)
    
    # تأیید به کاربر
    bot.send_message(user_id, f"{EMOJIS['success']} پیام شما با موفقیت ارسال شد!", reply_markup=places_menu())
    
    user_states[user_id] = None

@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def handle_reply_callback(call):
    user_id = call.from_user.id
    data_parts = call.data.split('_')
    target_user_id = int(data_parts[1])
    place_id = int(data_parts[2])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT title FROM places WHERE place_id = ?", (place_id,))
    place = c.fetchone()
    conn.close()
    
    if place:
        place_title = place[0]
        
        user_data[user_id] = {
            "reply_target_id": target_user_id,
            "reply_place_id": place_id,
            "reply_place_title": place_title
        }
        
        bot.send_message(user_id, "لطفاً پاسخ خود را وارد کنید:", reply_markup=back_menu())
        user_states[user_id] = "waiting_for_reply_text"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_reply_text")
def handle_reply_text_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "ارسال پاسخ لغو شد.")
        user_states[user_id] = None
        return
    
    reply_text = message.text
    target_user_id = user_data[user_id]["reply_target_id"]
    place_id = user_data[user_id]["reply_place_id"]
    place_title = user_data[user_id]["reply_place_title"]
    
    # ارسال پاسخ به کاربر
    replier_user = get_user(user_id)
    replier_name = replier_user[1] if replier_user else "ناشناس"
    replier_age = replier_user[2] if replier_user and replier_user[2] else "نامشخص"
    replier_gender = replier_user[3] if replier_user and replier_user[3] else "نامشخص"
    
    reply_message = f"""
{EMOJIS['message']} پاسخ از صاحب مکان:

از: {replier_name} ({replier_age} سال، {replier_gender})
برای مکان: {place_title}

متن پاسخ:
{reply_text}
    """
    
    bot.send_message(target_user_id, reply_message)
    
    # تأیید به صاحب مکان
    bot.send_message(user_id, f"{EMOJIS['success']} پاسخ شما با موفقیت ارسال شد!")
    
    user_states[user_id] = None

@bot.callback_query_handler(func=lambda call: call.data.startswith('block_'))
def handle_block_callback(call):
    user_id = call.from_user.id
    data_parts = call.data.split('_')
    target_user_id = int(data_parts[1])
    place_id = int(data_parts[2])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT title FROM places WHERE place_id = ?", (place_id,))
    place = c.fetchone()
    conn.close()
    
    if place:
        place_title = place[0]
        
        # بلاک کردن کاربر
        block_contact(user_id, target_user_id, place_id)
        
        # اطلاع به صاحب مکان
        bot.send_message(user_id, f"{EMOJIS['success']} کاربر با موفقیت بلاک شد. این کاربر دیگر نمی‌تواند برای مکان '{place_title}' پیام ارسال کند.")
        
        # اطلاع به کاربر بلاک شده
        blocked_user = get_user(target_user_id)
        if blocked_user:
            blocked_name = blocked_user[1]
            bot.send_message(target_user_id, f"{EMOJIS['warning']} شما توسط صاحب مکان '{place_title}' بلاک شده‌اید و دیگر نمی‌توانید برای این مکان پیام ارسال کنید.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('unblock_'))
def handle_unblock_callback(call):
    user_id = call.from_user.id
    data_parts = call.data.split('_')
    target_user_id = int(data_parts[1])
    place_id = int(data_parts[2])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT title FROM places WHERE place_id = ?", (place_id,))
    place = c.fetchone()
    conn.close()
    
    if place:
        place_title = place[0]
        
        # آنبلاک کردن کاربر
        unblock_contact(user_id, target_user_id, place_id)
        
        # اطلاع به صاحب مکان
        bot.send_message(user_id, f"{EMOJIS['success']} کاربر با موفقیت آنبلاک شد. این کاربر اکنون می‌تواند برای مکان '{place_title}' پیام ارسال کند.")
        
        # اطلاع به کاربر آنبلاک شده
        unblocked_user = get_user(target_user_id)
        if unblocked_user:
            unblocked_name = unblocked_user[1]
            bot.send_message(target_user_id, f"{EMOJIS['success']} شما توسط صاحب مکان '{place_title}' آنبلاک شده‌اید و اکنون می‌توانید برای این مکان پیام ارسال کنید.")

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['report']} گزارش")
def handle_report(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "لطفاً اگر گزارشی دارید بنویسید تا به ادمین ارسال شود:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_report"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_report")
def handle_report_input(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "ارسال گزارش لغو شد.", reply_markup=main_menu(user_id))
        user_states[user_id] = None
        return
    
    report_text = message.text
    
    # ذخیره گزارش در دیتابیس
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO reports (user_id, report_text) VALUES (?, ?)", (user_id, report_text))
    conn.commit()
    conn.close()
    
    # ارسال گزارش به ادمین
    reporter_user = get_user(user_id)
    reporter_name = reporter_user[1] if reporter_user else "ناشناس"
    reporter_age = reporter_user[2] if reporter_user and reporter_user[2] else "نامشخص"
    reporter_gender = reporter_user[3] if reporter_user and reporter_user[3] else "نامشخص"
    reporter_numeric_id = reporter_user[5] if reporter_user else "نامشخص"
    
    report_message = f"""
{EMOJIS['report']} گزارش جدید:

از: {reporter_name} ({reporter_age} سال، {reporter_gender})
شناسه عددی: {reporter_numeric_id}

متن گزارش:
{report_text}
    """
    
    bot.send_message(ADMIN_ID, report_message)
    
    # تأیید به کاربر
    bot.send_message(user_id, f"{EMOJIS['success']} گزارش شما با موفقیت ارسال شد و پیگیری خواهد شد!", reply_markup=main_menu(user_id))
    
    user_states[user_id] = None

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['buy']} خرید مکان برتر")
def handle_buy_top_place(message):
    user_id = message.from_user.id
    
    # دریافت مکان‌های کاربر
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT place_id, title FROM places WHERE user_id = ?", (user_id,))
    user_places = c.fetchall()
    conn.close()
    
    if not user_places:
        bot.send_message(user_id, f"{EMOJIS['error']} شما هیچ مکانی برای درخواست قرارگیری در بخش برترها ندارید.", reply_markup=main_menu(user_id))
        return
    
    # ایجاد کیبورد با مکان‌های کاربر
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for place in user_places:
        keyboard.row(place[1])
    keyboard.row(f"{EMOJIS['back']} برگشت")
    
    bot.send_message(user_id, "لطفاً اسم مکانی که می‌خواهید در بخش مکان‌های برتر قرار گیرد را انتخاب کنید:", reply_markup=keyboard)
    user_states[user_id] = "waiting_for_top_place_selection"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_top_place_selection")
def handle_top_place_selection(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "درخواست مکان برتر لغو شد.", reply_markup=main_menu(user_id))
        user_states[user_id] = None
        return
    
    place_title = message.text
    
    # بررسی وجود مکان
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT place_id FROM places WHERE user_id = ? AND title = ?", (user_id, place_title))
    place = c.fetchone()
    conn.close()
    
    if not place:
        bot.send_message(user_id, f"{EMOJIS['error']} مکان مورد نظر یافت نشد. لطفاً از بین مکان‌های خود انتخاب کنید.")
        return
    
    # ذخیره درخواست
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO top_place_requests (user_id, place_title) VALUES (?, ?)", (user_id, place_title))
    conn.commit()
    conn.close()
    
    # ارسال درخواست به ادمین
    requester_user = get_user(user_id)
    requester_name = requester_user[1] if requester_user else "ناشناس"
    requester_age = requester_user[2] if requester_user and requester_user[2] else "نامشخص"
    requester_gender = requester_user[3] if requester_user and requester_user[3] else "نامشخص"
    requester_numeric_id = requester_user[5] if requester_user else "نامشخص"
    
    request_message = f"""
{EMOJIS['buy']} درخواست جدید برای مکان برتر:

از: {requester_name} ({requester_age} سال، {requester_gender})
شناسه عددی: {requester_numeric_id}

درخواست قرارگیری مکان "{place_title}" در بخش مکان‌های برتر
    """
    
    bot.send_message(ADMIN_ID, request_message)
    
    # تأیید به کاربر
    bot.send_message(user_id, f"{EMOJIS['success']} درخواست شما با موفقیت ارسال شد!", reply_markup=main_menu(user_id))
    
    user_states[user_id] = None

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['admin']} بخش ادمین")
def handle_admin(message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.send_message(user_id, f"{EMOJIS['error']} شما دسترسی به بخش ادمین ندارید.", reply_markup=main_menu(user_id))
        return
    
    bot.send_message(user_id, "بخش ادمین:", reply_markup=admin_menu())

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['add']} اضافه کردن رای")
def handle_add_vote(message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.send_message(user_id, f"{EMOJIS['error']} شما دسترسی به این بخش ندارید.", reply_markup=main_menu(user_id))
        return
    
    bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_vote_place_title"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_vote_place_title")
def handle_vote_place_title(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن رأی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id] = {"vote_place_title": message.text}
    bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید (عدد انگلیسی):", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_vote_user_id"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_vote_user_id")
def handle_vote_user_id(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن رأی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    try:
        numeric_id = int(message.text)
        user_data[user_id]["vote_numeric_id"] = numeric_id
        bot.send_message(user_id, "لطفاً تعداد رأی‌ها را وارد کنید (عدد انگلیسی):", reply_markup=back_menu())
        user_states[user_id] = "waiting_for_vote_count"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_vote_count")
def handle_vote_count(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن رأی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    try:
        vote_count = int(message.text)
        if vote_count <= 0:
            bot.send_message(user_id, "لطفاً عددی بزرگتر از صفر وارد کنید:", reply_markup=back_menu())
            return
        
        user_data[user_id]["vote_count"] = vote_count
        bot.send_message(user_id, "لطفاً امتیاز رأی را وارد کنید (عدد بین 0 تا 10، انگلیسی):", reply_markup=back_menu())
        user_states[user_id] = "waiting_for_vote_score"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_vote_score")
def handle_vote_score(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "افزودن رأی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    try:
        vote_score = float(message.text)
        if vote_score < 0 or vote_score > 10:
            bot.send_message(user_id, "لطفاً عددی بین 0 تا 10 وارد کنید:", reply_markup=back_menu())
            return
        
        user_data[user_id]["vote_score"] = vote_score
        
        # نمایش اطلاعات و درخواست تأیید
        place_title = user_data[user_id]["vote_place_title"]
        numeric_id = user_data[user_id]["vote_numeric_id"]
        vote_count = user_data[user_id]["vote_count"]
        vote_score = user_data[user_id]["vote_score"]
        
        confirmation_text = f"""
{EMOJIS['info']} اطلاعات رأی:

عنوان مکان: {place_title}
شناسه عددی کاربر: {numeric_id}
تعداد رأی: {vote_count}
امتیاز رأی: {vote_score}

آیا از افزودن این رأی اطمینان دارید؟
        """
        
        bot.send_message(user_id, confirmation_text, reply_markup=confirm_menu())
        user_states[user_id] = "waiting_for_vote_confirmation"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_vote_confirmation")
def handle_vote_confirmation(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تأیید":
        place_title = user_data[user_id]["vote_place_title"]
        numeric_id = user_data[user_id]["vote_numeric_id"]
        vote_count = user_data[user_id]["vote_count"]
        vote_score = user_data[user_id]["vote_score"]
        
        # یافتن کاربر بر اساس شناسه عددی
        target_user = get_user_by_numeric_id(numeric_id)
        if not target_user:
            bot.send_message(user_id, f"{EMOJIS['error']} کاربر با شناسه عددی {numeric_id} یافت نشد.", reply_markup=admin_menu())
            user_states[user_id] = None
            return
        
        target_user_id = target_user[0]
        
        # یافتن مکان بر اساس عنوان و کاربر
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT place_id, rating_sum, rating_count FROM places WHERE user_id = ? AND title = ?", 
                 (target_user_id, place_title))
        place = c.fetchone()
        
        if not place:
            bot.send_message(user_id, f"{EMOJIS['error']} مکان با عنوان '{place_title}' برای کاربر یافت نشد.", reply_markup=admin_menu())
            conn.close()
            user_states[user_id] = None
            return
        
        place_id, current_rating_sum, current_rating_count = place
        
        # محاسبه امتیاز جدید
        new_rating_sum = current_rating_sum + (vote_count * vote_score)
        new_rating_count = current_rating_count + vote_count
        
        # به‌روزرسانی امتیاز مکان
        c.execute("UPDATE places SET rating_sum = ?, rating_count = ? WHERE place_id = ?",
                 (new_rating_sum, new_rating_count, place_id))
        conn.commit()
        conn.close()
        
        # اطلاع به صاحب مکان
        new_rating = new_rating_sum / new_rating_count if new_rating_count > 0 else 0
        notification_text = f"""
{EMOJIS['success']} مکان شما بروزرسانی شد!

مکان: {place_title}
تعداد رأی اضافه شده: {vote_count}
امتیاز اضافه شده: {vote_score}
امتیاز جدید: {new_rating:.1f} ({new_rating_count} رأی)
        """
        
        bot.send_message(target_user_id, notification_text)
        
        # تأیید به ادمین
        bot.send_message(user_id, f"{EMOJIS['success']} رأی با موفقیت اضافه شد!", reply_markup=admin_menu())
        
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        bot.send_message(user_id, "افزودن رأی لغو شد.", reply_markup=admin_menu())
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=confirm_menu())
        return
    
    user_states[user_id] = None

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['remove_score']} کم کردن رای")
def handle_remove_vote(message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.send_message(user_id, f"{EMOJIS['error']} شما دسترسی به این بخش ندارید.", reply_markup=main_menu(user_id))
        return
    
    bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_remove_vote_place_title"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_remove_vote_place_title")
def handle_remove_vote_place_title(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "کاهش رأی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id] = {"remove_vote_place_title": message.text}
    bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید (عدد انگلیسی):", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_remove_vote_user_id"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_remove_vote_user_id")
def handle_remove_vote_user_id(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "کاهش رأی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    try:
        numeric_id = int(message.text)
        user_data[user_id]["remove_vote_numeric_id"] = numeric_id
        bot.send_message(user_id, "لطفاً تعداد رأی‌هایی که می‌خواهید کم کنید را وارد کنید (عدد انگلیسی):", reply_markup=back_menu())
        user_states[user_id] = "waiting_for_remove_vote_count"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_remove_vote_count")
def handle_remove_vote_count(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "کاهش رأی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    try:
        vote_count = int(message.text)
        if vote_count <= 0:
            bot.send_message(user_id, "لطفاً عددی بزرگتر از صفر وارد کنید:", reply_markup=back_menu())
            return
        
        user_data[user_id]["remove_vote_count"] = vote_count
        bot.send_message(user_id, "لطفاً امتیاز رأی‌هایی که می‌خواهید کم کنید را وارد کنید (عدد بین 0 تا 10، انگلیسی):", reply_markup=back_menu())
        user_states[user_id] = "waiting_for_remove_vote_score"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_remove_vote_score")
def handle_remove_vote_score(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "کاهش رأی لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    try:
        vote_score = float(message.text)
        if vote_score < 0 or vote_score > 10:
            bot.send_message(user_id, "لطفاً عددی بین 0 تا 10 وارد کنید:", reply_markup=back_menu())
            return
        
        user_data[user_id]["remove_vote_score"] = vote_score
        
        # نمایش اطلاعات و درخواست تأیید
        place_title = user_data[user_id]["remove_vote_place_title"]
        numeric_id = user_data[user_id]["remove_vote_numeric_id"]
        vote_count = user_data[user_id]["remove_vote_count"]
        vote_score = user_data[user_id]["remove_vote_score"]
        
        confirmation_text = f"""
{EMOJIS['info']} اطلاعات کاهش رأی:

عنوان مکان: {place_title}
شناسه عددی کاربر: {numeric_id}
تعداد رأی: {vote_count}
امتیاز رأی: {vote_score}

آیا از کاهش این رأی اطمینان دارید؟
        """
        
        bot.send_message(user_id, confirmation_text, reply_markup=confirm_menu())
        user_states[user_id] = "waiting_for_remove_vote_confirmation"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_remove_vote_confirmation")
def handle_remove_vote_confirmation(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تأیید":
        place_title = user_data[user_id]["remove_vote_place_title"]
        numeric_id = user_data[user_id]["remove_vote_numeric_id"]
        vote_count = user_data[user_id]["remove_vote_count"]
        vote_score = user_data[user_id]["remove_vote_score"]
        
        # یافتن کاربر بر اساس شناسه عددی
        target_user = get_user_by_numeric_id(numeric_id)
        if not target_user:
            bot.send_message(user_id, f"{EMOJIS['error']} کاربر با شناسه عددی {numeric_id} یافت نشد.", reply_markup=admin_menu())
            user_states[user_id] = None
            return
        
        target_user_id = target_user[0]
        
        # یافتن مکان بر اساس عنوان و کاربر
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT place_id, rating_sum, rating_count FROM places WHERE user_id = ? AND title = ?", 
                 (target_user_id, place_title))
        place = c.fetchone()
        
        if not place:
            bot.send_message(user_id, f"{EMOJIS['error']} مکان با عنوان '{place_title}' برای کاربر یافت نشد.", reply_markup=admin_menu())
            conn.close()
            user_states[user_id] = None
            return
        
        place_id, current_rating_sum, current_rating_count = place
        
        # بررسی تعداد رأی‌های موجود
        if current_rating_count < vote_count:
            bot.send_message(user_id, f"{EMOJIS['error']} تعداد رأی‌های موجود ({current_rating_count}) کمتر از تعداد مورد نظر برای کاهش ({vote_count}) است.", reply_markup=admin_menu())
            conn.close()
            user_states[user_id] = None
            return
        
        # محاسبه امتیاز جدید
        new_rating_sum = max(0, current_rating_sum - (vote_count * vote_score))
        new_rating_count = max(0, current_rating_count - vote_count)
        
        # به‌روزرسانی امتیاز مکان
        c.execute("UPDATE places SET rating_sum = ?, rating_count = ? WHERE place_id = ?",
                 (new_rating_sum, new_rating_count, place_id))
        conn.commit()
        conn.close()
        
        # اطلاع به صاحب مکان
        new_rating = new_rating_sum / new_rating_count if new_rating_count > 0 else 0
        notification_text = f"""
{EMOJIS['warning']} مکان شما بروزرسانی شد!

مکان: {place_title}
تعداد رأی کم شده: {vote_count}
امتیاز کم شده: {vote_score}
امتیاز جدید: {new_rating:.1f} ({new_rating_count} رأی)
        """
        
        bot.send_message(target_user_id, notification_text)
        
        # تأیید به ادمین
        bot.send_message(user_id, f"{EMOJIS['success']} رأی با موفقیت کاهش یافت!", reply_markup=admin_menu())
        
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        bot.send_message(user_id, "کاهش رأی لغو شد.", reply_markup=admin_menu())
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=confirm_menu())
        return
    
    user_states[user_id] = None

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['document']} مدیریت نظرات")
def handle_manage_comments(message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.send_message(user_id, f"{EMOJIS['error']} شما دسترسی به این بخش ندارید.", reply_markup=main_menu(user_id))
        return
    
    bot.send_message(user_id, "لطفاً عنوان مکان مورد نظر را وارد کنید:", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_comment_manage_place_title"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_comment_manage_place_title")
def handle_comment_manage_place_title(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "مدیریت نظرات لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id] = {"comment_manage_place_title": message.text}
    bot.send_message(user_id, "لطفاً شناسه عددی کاربر صاحب مکان را وارد کنید (عدد انگلیسی):", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_comment_manage_user_id"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_comment_manage_user_id")
def handle_comment_manage_user_id(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "مدیریت نظرات لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    try:
        numeric_id = int(message.text)
        user_data[user_id]["comment_manage_numeric_id"] = numeric_id
        bot.send_message(user_id, "لطفاً کلمه اول نظر مورد نظر برای حذف را وارد کنید:", reply_markup=back_menu())
        user_states[user_id] = "waiting_for_comment_first_word"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_comment_first_word")
def handle_comment_first_word(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "مدیریت نظرات لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    user_data[user_id]["comment_first_word"] = message.text
    bot.send_message(user_id, "لطفاً شناسه عددی کاربری که نظر را داده وارد کنید (عدد انگلیسی):", reply_markup=back_menu())
    user_states[user_id] = "waiting_for_commenter_numeric_id"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_commenter_numeric_id")
def handle_commenter_numeric_id(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['back']} برگشت":
        bot.send_message(user_id, "مدیریت نظرات لغو شد.", reply_markup=admin_menu())
        user_states[user_id] = None
        return
    
    try:
        commenter_numeric_id = int(message.text)
        user_data[user_id]["commenter_numeric_id"] = commenter_numeric_id
        
        # نمایش اطلاعات و درخواست تأیید
        place_title = user_data[user_id]["comment_manage_place_title"]
        owner_numeric_id = user_data[user_id]["comment_manage_numeric_id"]
        first_word = user_data[user_id]["comment_first_word"]
        commenter_numeric_id = user_data[user_id]["commenter_numeric_id"]
        
        confirmation_text = f"""
{EMOJIS['info']} اطلاعات حذف نظر:

عنوان مکان: {place_title}
شناسه عددی صاحب مکان: {owner_numeric_id}
کلمه اول نظر: {first_word}
شناسه عددی نظر دهنده: {commenter_numeric_id}

آیا از حذف این نظر اطمینان دارید؟
        """
        
        bot.send_message(user_id, confirmation_text, reply_markup=confirm_menu())
        user_states[user_id] = "waiting_for_comment_delete_confirmation"
    except ValueError:
        bot.send_message(user_id, "لطفاً یک عدد معتبر وارد کنید:", reply_markup=back_menu())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_comment_delete_confirmation")
def handle_comment_delete_confirmation(message):
    user_id = message.from_user.id
    
    if message.text == f"{EMOJIS['confirm']} تأیید":
        place_title = user_data[user_id]["comment_manage_place_title"]
        owner_numeric_id = user_data[user_id]["comment_manage_numeric_id"]
        first_word = user_data[user_id]["comment_first_word"]
        commenter_numeric_id = user_data[user_id]["commenter_numeric_id"]
        
        # یافتن صاحب مکان بر اساس شناسه عددی
        owner_user = get_user_by_numeric_id(owner_numeric_id)
        if not owner_user:
            bot.send_message(user_id, f"{EMOJIS['error']} صاحب مکان با شناسه عددی {owner_numeric_id} یافت نشد.", reply_markup=admin_menu())
            user_states[user_id] = None
            return
        
        owner_user_id = owner_user[0]
        
        # یافتن نظر دهنده بر اساس شناسه عددی
        commenter_user = get_user_by_numeric_id(commenter_numeric_id)
        if not commenter_user:
            bot.send_message(user_id, f"{EMOJIS['error']} نظر دهنده با شناسه عددی {commenter_numeric_id} یافت نشد.", reply_markup=admin_menu())
            user_states[user_id] = None
            return
        
        commenter_user_id = commenter_user[0]
        
        # یافتن مکان بر اساس عنوان و صاحب
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT place_id FROM places WHERE user_id = ? AND title = ?", 
                 (owner_user_id, place_title))
        place = c.fetchone()
        
        if not place:
            bot.send_message(user_id, f"{EMOJIS['error']} مکان با عنوان '{place_title}' برای کاربر یافت نشد.", reply_markup=admin_menu())
            conn.close()
            user_states[user_id] = None
            return
        
        place_id = place[0]
        
        # یافتن نظر بر اساس مکان، نظر دهنده و کلمه اول
        c.execute("SELECT comment_id, comment_text FROM comments WHERE place_id = ? AND user_id = ? AND comment_text LIKE ?",
                 (place_id, commenter_user_id, f"{first_word}%"))
        comment = c.fetchone()
        
        if not comment:
            bot.send_message(user_id, f"{EMOJIS['error']} نظری با مشخصات وارد شده یافت نشد.", reply_markup=admin_menu())
            conn.close()
            user_states[user_id] = None
            return
        
        comment_id, comment_text = comment
        
        # حذف نظر
        c.execute("DELETE FROM comments WHERE comment_id = ?", (comment_id,))
        conn.commit()
        conn.close()
        
        # اطلاع به نظر دهنده
        notification_text = f"""
{EMOJIS['warning']} نظر شما حذف شد!

نظر شما در نظرات مکان "{place_title}" توسط ادمین به دلیل نقض قوانین حذف شد.

متن نظر حذف شده:
{comment_text}
        """
        
        bot.send_message(commenter_user_id, notification_text)
        
        # تأیید به ادمین
        bot.send_message(user_id, f"{EMOJIS['success']} نظر با موفقیت حذف شد!", reply_markup=admin_menu())
        
    elif message.text == f"{EMOJIS['cancel']} انصراف":
        bot.send_message(user_id, "حذف نظر لغو شد.", reply_markup=admin_menu())
    else:
        bot.send_message(user_id, "لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=confirm_menu())
        return
    
    user_states[user_id] = None

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['help']} راهنما")
def handle_help(message):
    user_id = message.from_user.id
    show_help_page(user_id, 1)

def show_help_page(user_id, page):
    if page < 1 or page > len(HELP_PAGES):
        return
    
    bot.send_message(user_id, HELP_PAGES[page-1], reply_markup=help_menu(page))

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['next']} صفحه بعدی")
def handle_next_page(message):
    user_id = message.from_user.id
    
    # پیدا کردن صفحه فعلی
    current_page = 1
    if user_id in user_data and "help_page" in user_data[user_id]:
        current_page = user_data[user_id]["help_page"]
    
    next_page = current_page + 1
    if next_page > len(HELP_PAGES):
        next_page = len(HELP_PAGES)
    
    user_data[user_id] = {"help_page": next_page}
    show_help_page(user_id, next_page)

@bot.message_handler(func=lambda message: message.text == f"{EMOJIS['previous']} صفحه قبلی")
def handle_previous_page(message):
    user_id = message.from_user.id
    
    # پیدا کردن صفحه فعلی
    current_page = 1
    if user_id in user_data and "help_page" in user_data[user_id]:
        current_page = user_data[user_id]["help_page"]
    
    prev_page = current_page - 1
    if prev_page < 1:
        prev_page = 1
    
    user_data[user_id] = {"help_page": prev_page}
    show_help_page(user_id, prev_page)

# هندلر برای مدیریت سایر پیام‌ها
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    
    if user_id in user_states:
        # اگر کاربر در حالتی است که منتظر ورودی است، از هندلرهای خاص استفاده می‌شود
        return
    
    # اگر پیام متنی معمولی است، منوی اصلی را نشان بده
    show_main_menu(user_id)

if __name__ == '__main__':
    print("Starting bot...")
    app.run(host='0.0.0.0', port=PORT)