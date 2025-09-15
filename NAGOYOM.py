import telebot
from telebot import types
import sqlite3
import random
import re
import threading
import time
import os
from flask import Flask, request
import difflib  # برای جستجوی فازی

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
    "report": "🚨",
    "comment": "💬",
    "comments": "📝",
    "message": "✉️",
    "block": "🚫",
    "unblock": "🔓",
    "reply": "↩️"
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
user_blocks = {}  # برای بلاک‌های خاص مکان: {place_id: set(blocked_user_ids)}
place_photos = {}  # موقت برای جمع‌آوری عکس‌ها

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
                 photos TEXT,  -- کاما سپریتد file_ids
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
                 comment TEXT)''')
    try:
        c.execute("ALTER TABLE places ADD COLUMN subcategory TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE places ADD COLUMN photos TEXT")
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
        num_id = random.randint(100000000, 999999999)
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

def is_user_blocked_for_place(place_id, user_id):
    return user_id in user_blocks.get(place_id, set())

def block_user_for_place(place_id, user_id):
    if place_id not in user_blocks:
        user_blocks[place_id] = set()
    user_blocks[place_id].add(user_id)

def unblock_user_for_place(place_id, user_id):
    if place_id in user_blocks:
        user_blocks[place_id].discard(user_id)

def check_top_place_change(place_id, old_avg, new_avg):
    MIN_RATING_COUNT = 100
    MIN_AVG_RATING = 8.0
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, title FROM places WHERE place_id = ?", (place_id,))
    owner_id, title = c.fetchone()
    conn.close()
    was_top = (old_avg >= MIN_AVG_RATING)
    is_top = (new_avg >= MIN_AVG_RATING)
    if not was_top and is_top:
        try:
            bot.send_message(owner_id, f"{EMOJIS['success']} مکان شما با نام {title} وارد بخش مکان های برتر شد! به شما تبریک می‌گوییم! 🎉")
        except:
            pass
    elif was_top and not is_top:
        try:
            bot.send_message(owner_id, f"{EMOJIS['warning']} دیگر مکان شما با نام {title} در مکان های برتر نیست. ⚠️")
        except:
            pass

# منوها
def main_menu(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['profile']} پروفایل")
    keyboard.row(f"{EMOJIS['places']} مکان‌ها", f"{EMOJIS['rating']} مکان‌های برتر")
    keyboard.row(f"{EMOJIS['star']} کاربران برتر")
    keyboard.row(f"{EMOJIS['link']} لینک‌ها", f"{EMOJIS['help']} راهنما")
    keyboard.row(f"{EMOJIS['report']} گزارش")
    keyboard.row("خرید مکان برتر")
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
    keyboard.row("قرارگیری مکان برتر")
    keyboard.row("مدیریت نظرات")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
    return keyboard

def admin_top_place_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("اضافه کردن رای", "کم کردن رای")
    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
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

def confirm_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("بله", "خیر")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def comment_menu(has_comment):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['back']} برگشت")
    if has_comment:
        keyboard.row("حذف نظر")
    return keyboard

def message_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['reply']} جواب دادن")
    keyboard.row(f"{EMOJIS['block']} بلاک کردن", f"{EMOJIS['unblock']} رفع بلاک")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

def photo_confirm_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("تایید عکس‌ها")
    keyboard.row(f"{EMOJIS['back']} برگشت")
    return keyboard

# راهنمای تعاملی
HELP_PAGES = [
    f"{EMOJIS['help']} راهنمای استفاده از ربات گویم‌نما:\n\n"
    f"{EMOJIS['profile']} بخش پروفایل:\n"
    "• مشاهده اطلاعات شخصی خود\n"
    "• ویرایش نام، سن و جنسیت",

    f"{EMOJIS['places']} بخش مکان‌ها:\n"
    "• مشاهده مکان‌ها بر اساس دسته‌بندی\n"
    "• مدیریت مکان‌های خود (ویرایش/حذف برای ادمین)\n"
    "• برای اضافه کردن مکان با ادمین تماس بگیرید\n"
    "• جستجو بر اساس آدرس یا نام مکان (جزئی یا کامل)\n"
    "• هر مکان ۱۵ امتیاز برای کاربر مرتبط",

    f"{EMOJIS['rating']} مکان‌های برتر:\n"
    "• مشاهده مکان‌هایی با حداقل ۱۰۰ رای و میانگین امتیاز بالای ۸\n"
    "• هر کاربر فقط یک‌بار می‌تواند به هر مکان رای دهد",

    f"{EMOJIS['star']} کاربران برتر:\n"
    "• مشاهده کاربران با بیشترین امتیاز\n"
    "• حداقل ۱۰۰۰ امتیاز برای نمایش",

    f"{EMOJIS['link']} بخش لینک‌ها:\n"
    "• دسترسی به پیج اصلی\n"
    "• ارتباط با ادمین\n\n"
    f"{EMOJIS['report']} بخش گزارش:\n"
    "• ارسال گزارش به ادمین",

    f"{EMOJIS['info']} قوانین مهم:\n"
    "• محتوای مستهجن یا توهین‌آمیز مجاز نیست\n"
    "• اطلاعات واقعی و دقیق وارد کنید\n"
    "• رعایت ادب و احترام در تعاملات\n"
    "• تخلف از قوانین منجر به مسدودیت می‌شود\n\n"
    f"{EMOJIS['success']} موفق باشید!"
]

def send_help_page(user_id, page=0):
    msg = HELP_PAGES[page]
    keyboard = types.InlineKeyboardMarkup()
    if page > 0:
        keyboard.add(types.InlineKeyboardButton("صفحه قبلی", callback_data=f"help_prev_{page}"))
    if page < len(HELP_PAGES) - 1:
        keyboard.add(types.InlineKeyboardButton("صفحه بعدی", callback_data=f"help_next_{page}"))
    bot.send_message(user_id, msg, reply_markup=keyboard)

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

# مدیریت پیام‌ها - بهبود برای کارکرد بدون نیاز به /start
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'document'])
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
    content_type = message.content_type

    if text == f"{EMOJIS['home']} صفحه اصلی":
        bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu(user_id))
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
                       "place_top_rated", "place_rate", "place_rate_confirm", "place_search_title", "place_search_address", "place_search_result", "search_type", "search_by_address", "search_by_name", "search_by_name_address"]:
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
                       "admin_news_menu", "admin_news_user_content", "admin_news_user_numeric_id", "admin_news_user_confirm",
                       "admin_score_menu", "admin_add_score_numeric_id", "admin_add_score_amount", "admin_add_score_confirm",
                       "admin_remove_score_numeric_id", "admin_remove_score_amount", "admin_remove_score_confirm",
                       "admin_top_place_menu", "admin_add_rating_title", "admin_add_rating_numeric_id", "admin_add_rating_count", "admin_add_rating_value", "admin_add_rating_confirm",
                       "admin_remove_rating_title", "admin_remove_rating_numeric_id", "admin_remove_rating_count", "admin_remove_rating_value", "admin_remove_rating_confirm",
                       "admin_manage_comments_title", "admin_manage_comments_numeric_id", "admin_manage_comments_first_word", "admin_manage_comments_user_numeric_id", "admin_manage_comments_confirm"]:
            if state.startswith("admin_news"):
                bot.send_message(user_id, f"{EMOJIS['news']} بخش ارسال خبر:", reply_markup=admin_news_menu())
                user_states[user_id] = "admin_news_menu"
            elif state.startswith("admin_score"):
                bot.send_message(user_id, f"{EMOJIS['score']} بخش امتیاز کاربران:", reply_markup=admin_score_menu())
                user_states[user_id] = "admin_score_menu"
            elif state.startswith("admin_top"):
                bot.send_message(user_id, "بخش قرارگیری مکان برتر:", reply_markup=admin_top_place_menu())
                user_states[user_id] = "admin_top_place_menu"
            elif state == "admin_view_gender":
                bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['admin']} پنل ادمین:", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
            return
        elif state in ["report_menu", "report_content", "report_confirm"]:
            bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
            return
        elif state in ["buy_top_place", "buy_top_place_select", "buy_top_place_confirm"]:
            bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
            return
        elif state in ["comment_add", "comment_add_confirm", "comment_delete_confirm"]:
            bot.send_message(user_id, "بخش مکان‌ها:", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        elif state in ["message_to_owner", "message_to_owner_confirm", "message_reply", "message_reply_confirm", "message_block_confirm", "message_unblock_confirm"]:
            bot.send_message(user_id, "بخش مکان‌ها:", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        else:
            bot.send_message(user_id, "صفحه اصلی:", reply_markup=main_menu(user_id))
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
            bot.send_message(user_id, profile_msg, reply_markup=main_menu(user_id))
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
            MIN_RATING_COUNT = 100  # تغییر از 200 به 100
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
                    photos = place[8].split(',') if place[8] else []
                    if photos:
                        media = [types.InputMediaPhoto(photo_id) for photo_id in photos]
                        try:
                            bot.send_media_group(user_id, media)
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
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comment']} نظر دادن", callback_data=f"add_comment_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comments']} نظرات", callback_data=f"view_comments_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['message']} ارسال پیام به صاحب", callback_data=f"message_owner_{place[0]}"))
                    bot.send_message(user_id, msg, reply_markup=keyboard)
                bot.send_message(user_id, "انتخاب کنید:", reply_markup=main_menu(user_id))
                user_states[user_id] = "main_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} هنوز هیچ مکانی نتونسته مرتبه برتر را در مکان‌ها کسب کند!", reply_markup=main_menu(user_id))
                user_states[user_id] = "main_menu"
        elif text == f"{EMOJIS['star']} کاربران برتر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_id, name, score FROM users WHERE score >= 1000 ORDER BY score DESC")
            users = c.fetchall()
            conn.close()
            if users:
                msg = f"{EMOJIS['star']} کاربران برتر:\n\n"
                for user in users:
                    user_id_db = user[0]
                    user_name = user[1]
                    user_score = user[2]
                    
                    # دریافت مکان‌های کاربر
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("SELECT title FROM places WHERE user_id = ?", (user_id_db,))
                    places = c.fetchall()
                    conn.close()
                    
                    places_list = [place[0] for place in places]
                    places_str = ", ".join(places_list) if places_list else "هیچ مکانی ثبت نشده"
                    
                    msg += f"👤 نام: {user_name}\n🏆 امتیاز: {user_score}\n📍 مکان‌ها: {places_str}\n\n"
                    msg += "-------------------\n\n"
            else:
                msg = f"{EMOJIS['error']} هنوز کسی به ۱۰۰۰ امتیاز نرسیده است!"
            bot.send_message(user_id, msg, reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
        elif text == f"{EMOJIS['link']} لینک‌ها":
            link_text = f"{EMOJIS['link']} لینک‌های مفید:\n\n"
            link_text += f"{EMOJIS['link']} لینک پیج اصلی گویم‌نما:\n"
            link_text += "https://www.instagram.com/sedayegoyom?igsh=MXd0MTlkZGdzNzZ6bw==\n\n"
            link_text += f"{EMOJIS['admin']} ایدی ادمین گویم‌نما:\n"
            link_text += "@Sedayegoyom10"
            bot.send_message(user_id, link_text, reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
        elif text == f"{EMOJIS['help']} راهنما":
            send_help_page(user_id, 0)
            user_states[user_id] = "main_menu"
        elif text == f"{EMOJIS['report']} گزارش":
            bot.send_message(user_id, f"{EMOJIS['report']} لطفاً اگر گزارشی دارید بنویسید تا به ادمین ارسال شود:", reply_markup=back_button_only())
            user_states[user_id] = "report_content"
        elif text == "خرید مکان برتر":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT place_id, title FROM places WHERE user_id = ?", (user_id,))
            places = c.fetchall()
            conn.close()
            if places:
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for place in places:
                    keyboard.row(place[1])
                keyboard.row(f"{EMOJIS['back']} برگشت")
                bot.send_message(user_id, f"{EMOJIS['info']} لطفاً نام مکانی که می‌خواهید در بخش مکان‌های برتر قرار گیرد را انتخاب کنید:", reply_markup=keyboard)
                user_states[user_id] = "buy_top_place_select"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} شما هیچ مکانی ندارید!", reply_markup=main_menu(user_id))
                user_states[user_id] = "main_menu"
        elif text == f"{EMOJIS['admin']} بخش ادمین" and user_id == ADMIN_ID:
            bot.send_message(user_id, f"{EMOJIS['admin']} به پنل ادمین خوش آمدید!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    elif state == "report_content":
        if text.strip():
            user_data[user_id] = {'report_text': text}
            keyboard = confirm_keyboard()
            bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این گزارش را ارسال کنید؟\n\n{text}", reply_markup=keyboard)
            user_states[user_id] = "report_confirm"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} گزارش نمی‌تواند خالی باشد!")
    elif state == "report_confirm":
        if text == "بله":
            report_text = user_data[user_id]['report_text']
            user = get_user(user_id)
            msg_to_admin = f"{EMOJIS['report']} گزارش جدید:\n\n{report_text}\n\nپروفایل کاربر:\nنام: {user[1]}\nسن: {user[2]}\nجنسیت: {user[3]}\nشناسه عددی: {user[5]}"
            try:
                bot.send_message(ADMIN_ID, msg_to_admin)
                bot.send_message(user_id, f"{EMOJIS['success']} گزارش شما با موفقیت ارسال شد و پیگیری خواهد شد!", reply_markup=main_menu(user_id))
                # بازخورد بصری
                bot.send_animation(user_id, 'https://t.me/animated_gifs/confirmation.gif')  # گیف نمونه
            except:
                bot.send_message(user_id, f"{EMOJIS['error']} خطا در ارسال گزارش!", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} ارسال گزارش لغو شد.", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    elif state == "buy_top_place_select":
        title = text
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT place_id, user_id FROM places WHERE title = ? AND user_id = ?", (title, user_id))
        place = c.fetchone()
        conn.close()
        if place:
            user_data[user_id] = {'buy_place_id': place[0], 'buy_place_title': title}
            keyboard = confirm_keyboard()
            bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید درخواست خرید مکان برتر برای '{title}' ارسال کنید؟", reply_markup=keyboard)
            user_states[user_id] = "buy_top_place_confirm"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} مکان یافت نشد!", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    elif state == "buy_top_place_confirm":
        if text == "بله":
            place_id = user_data[user_id]['buy_place_id']
            title = user_data[user_id]['buy_place_title']
            user = get_user(user_id)
            numeric_id = user[5]
            msg_to_admin = f"{EMOJIS['info']} درخواست خرید مکان برتر:\nکاربر: {user[1]} ({user[2]} ساله، {user[3]})\nمکان: {title}\nشناسه عددی: {numeric_id}"
            try:
                bot.send_message(ADMIN_ID, msg_to_admin)
                bot.send_message(user_id, f"{EMOJIS['success']} درخواست شما با موفقیت ارسال شد!", reply_markup=main_menu(user_id))
            except:
                bot.send_message(user_id, f"{EMOJIS['error']} خطا در ارسال درخواست!", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} درخواست لغو شد.", reply_markup=main_menu(user_id))
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
            bot.send_message(user_id, f"{EMOJIS['edit']} سن جدید را انتخاب کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=keyboard)
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
                    photos = place[8].split(',') if place[8] else []
                    if photos:
                        media = [types.InputMediaPhoto(photo_id) for photo_id in photos]
                        try:
                            bot.send_media_group(user_id, media)
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
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comment']} نظر دادن", callback_data=f"add_comment_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comments']} نظرات", callback_data=f"view_comments_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['message']} ارسال پیام به صاحب", callback_data=f"message_owner_{place[0]}"))
                    bot.send_message(user_id, msg, reply_markup=keyboard)
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} شما مکانی ندارید!")
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=get_place_menu())
            user_states[user_id] = "place_my_places"
        elif text == f"{EMOJIS['view']} جستجو":
            bot.send_message(user_id, f"{EMOJIS['places']} نوع جستجو را انتخاب کنید:", reply_markup=search_type_menu())
            user_states[user_id] = "search_type"
    elif state == "search_type":
        if text == "مغازه های آدرس مورد نظر":
            bot.send_message(user_id, "آدرس مورد نظر یا محدوده دلخواه را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=back_button_only())
            user_states[user_id] = "search_by_address"
        elif text == "جستجوی مغازه مورد نظر":
            bot.send_message(user_id, "نام مکان مورد نظر را وارد کنید (مثلاً سوپری، هایپر مارکت، پوشاک):", reply_markup=back_button_only())
            user_states[user_id] = "search_by_name"
            user_data[user_id] = {}
    elif state == "search_by_address":
        address_query = text.lower()
        query_words = address_query.split()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT places.*, users.numeric_id FROM places JOIN users ON places.user_id = users.user_id")
        places = c.fetchall()
        conn.close()
        filtered_places = []
        for place in places:
            address_lower = place[6].lower() if place[6] else ""
            address_words = address_lower.split()
            match = False
            for q_word in query_words:
                for a_word in address_words:
                    if difflib.SequenceMatcher(None, q_word, a_word).ratio() > 0.8:  # مشابهت بیش از 80%
                        match = True
                        break
                if match:
                    break
            if match:
                filtered_places.append(place)
        if filtered_places:
            for place in filtered_places:
                photos = place[8].split(',') if place[8] else []
                if photos:
                    media = [types.InputMediaPhoto(photo_id) for photo_id in photos]
                    try:
                        bot.send_media_group(user_id, media)
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
                msg += f"امتیاز: {avg_rating:.1f} ({place[12]} رای)\n"
                msg += f"شناسه عددی صاحب: {place[13]}"
                keyboard = types.InlineKeyboardMarkup()
                if user_id == ADMIN_ID:
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['rating']} امتیاز", callback_data=f"rate_place_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comment']} نظر دادن", callback_data=f"add_comment_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comments']} نظرات", callback_data=f"view_comments_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['message']} ارسال پیام به صاحب", callback_data=f"message_owner_{place[0]}"))
                bot.send_message(user_id, msg, reply_markup=keyboard)
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=search_result_menu())
            user_states[user_id] = "place_search_result"
        else:
            bot.send_message(user_id, "هیچ مکانی در این محدوده ثبت نشده است!", reply_markup=search_result_menu())
            user_states[user_id] = "place_search_result"
    elif state == "search_by_name":
        if text.strip():
            user_data[user_id]['name_query'] = text.lower().split()
            bot.send_message(user_id, f"{EMOJIS['places']} آدرس مورد نظر را وارد کنید (یا 'رد کردن' برای جستجو بدون آدرس): (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=skip_button())
            user_states[user_id] = "search_by_name_address"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} نام نمی‌تواند خالی باشد!")
    elif state == "search_by_name_address":
        name_words = user_data[user_id]['name_query']
        address_query = None if text == "رد کردن" else text.lower()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        query = "SELECT places.*, users.numeric_id FROM places JOIN users ON places.user_id = users.user_id WHERE 1=1"
        params = []
        if address_query:
            query += " AND LOWER(address) LIKE ?"
            params.append(f"%{address_query}%")
        places = c.execute(query, params).fetchall()
        filtered_places = []
        for place in places:
            title_lower = place[4].lower()
            if any(word in title_lower for word in name_words):
                filtered_places.append(place)
        conn.close()
        if filtered_places:
            for place in filtered_places:
                photos = place[8].split(',') if place[8] else []
                if photos:
                    media = [types.InputMediaPhoto(photo_id) for photo_id in photos]
                    try:
                        bot.send_media_group(user_id, media)
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
                msg += f"امتیاز: {avg_rating:.1f} ({place[12]} رای)\n"
                msg += f"شناسه عددی صاحب: {place[13]}"
                keyboard = types.InlineKeyboardMarkup()
                if user_id == ADMIN_ID:
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place[0]}"))
                    keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['rating']} امتیاز", callback_data=f"rate_place_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comment']} نظر دادن", callback_data=f"add_comment_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comments']} نظرات", callback_data=f"view_comments_{place[0]}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['message']} ارسال پیام به صاحب", callback_data=f"message_owner_{place[0]}"))
                bot.send_message(user_id, msg, reply_markup=keyboard)
            bot.send_message(user_id, "انتخاب کنید:", reply_markup=search_result_menu())
            user_states[user_id] = "place_search_result"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} مکانی با این مشخصات یافت نشد!", reply_markup=search_result_menu())
            user_states[user_id] = "place_search_result"
    elif state == "place_search_result":
        if text == "جستجو دوباره":
            bot.send_message(user_id, f"{EMOJIS['places']} نوع جستجو را انتخاب کنید:", reply_markup=search_type_menu())
            user_states[user_id] = "search_type"
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
            bot.send_message(user_id, f"{EMOJIS['places']} آدرس را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=back_button_only())
            user_states[user_id] = "place_add_address"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} توضیحات باید حداقل 10 کلمه باشد! ({len(words)} کلمه وارد کرده‌اید)")
    elif state == "place_add_address":
        if text.strip():
            user_data[user_id]['address'] = text
            bot.send_message(user_id, f"{EMOJIS['places']} شماره تماس را وارد کنید (شماره باید با 09 شروع شود و 11 رقم باشد یا 'رد کردن' برای خالی کردن): (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=skip_button())
            user_states[user_id] = "place_add_phone"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} آدرس نمی‌تواند خالی باشد!")
    elif state == "place_add_phone":
        if text == "رد کردن":
            user_data[user_id]['phone'] = None
            bot.send_message(user_id, f"{EMOJIS['places']} تا 8 عکس برای مکان ارسال کنید، سپس 'تایید عکس‌ها' را بزنید:", reply_markup=photo_confirm_keyboard())
            user_states[user_id] = "place_add_photo"
            place_photos[user_id] = []
        elif re.match(r'^09\d{9}$', text):
            user_data[user_id]['phone'] = text
            bot.send_message(user_id, f"{EMOJIS['places']} تا 8 عکس برای مکان ارسال کنید، سپس 'تایید عکس‌ها' را بزنید:", reply_markup=photo_confirm_keyboard())
            user_states[user_id] = "place_add_photo"
            place_photos[user_id] = []
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شماره موبایل باید با 09 شروع شود و 11 رقم باشد یا 'رد کردن' را انتخاب کنید!")
    elif state == "place_add_photo":
        if text == "تایید عکس‌ها":
            if user_id in place_photos and len(place_photos[user_id]) > 0:
                user_data[user_id]['photos'] = ','.join(place_photos[user_id])
                bot.send_message(user_id, f"{EMOJIS['places']} شیفت صبح را وارد کنید (مثال: 8:00-12:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
                user_states[user_id] = "place_add_morning_shift"
                del place_photos[user_id]
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} حداقل یک عکس ارسال کنید!")
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً عکس ارسال کنید یا تایید کنید!")
    elif state == "place_add_morning_shift":
        user_data[user_id]['morning_shift'] = None if text == "رد کردن" else text
        bot.send_message(user_id, f"{EMOJIS['places']} شیفت عصر را وارد کنید (مثال: 14:00-20:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
        user_states[user_id] = "place_add_afternoon_shift"
    elif state == "place_add_afternoon_shift":
        user_data[user_id]['afternoon_shift'] = None if text == "رد کردن" else text
        bot.send_message(user_id, f"{EMOJIS['places']} شناسه عددی کاربر را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=back_button_only())
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
                c.execute("INSERT INTO places (user_id, category, subcategory, title, description, address, phone, photos, morning_shift, afternoon_shift) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (target_user_id, user_data[user_id]['category'], user_data[user_id]['subcategory'], user_data[user_id]['title'],
                           user_data[user_id]['description'], user_data[user_id]['address'], user_data[user_id].get('phone'),
                           user_data[user_id].get('photos'), user_data[user_id]['morning_shift'], user_data[user_id]['afternoon_shift']))
                c.execute("UPDATE users SET score = score + 83 WHERE user_id = ?", (target_user_id,))
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
                bot.send_message(user_id, f"{EMOJIS['success']} مکان با موفقیت  ثبت شد! ۸۳ امتیاز به کاربر با شناسه {numeric_id} اضافه شد.\nارسال به {success_count} کاربر.", reply_markup=get_place_menu())
                bot.send_animation(user_id, 'https://t.me/animated_gifs/success.gif')  # گیف تایید
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
                        photos = place[8].split(',') if place[8] else []
                        if photos:
                            media = [types.InputMediaPhoto(photo_id) for photo_id in photos]
                            try:
                                bot.send_media_group(user_id, media)
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
                        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comment']} نظر دادن", callback_data=f"add_comment_{place[0]}"))
                        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['comments']} نظرات", callback_data=f"view_comments_{place[0]}"))
                        keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['message']} ارسال پیام به صاحب", callback_data=f"message_owner_{place[0]}"))
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
    elif state == "edit_place_menu":
        if text == f"{EMOJIS['edit']} ویرایش عنوان":
            bot.send_message(user_id, f"{EMOJIS['edit']} عنوان جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_title"
        elif text == f"{EMOJIS['edit']} ویرایش توضیحات":
            bot.send_message(user_id, f"{EMOJIS['edit']} توضیحات جدید را وارد کنید (حداقل 10 کلمه):", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_description"
        elif text == f"{EMOJIS['edit']} ویرایش آدرس":
            bot.send_message(user_id, f"{EMOJIS['edit']} آدرس جدید را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_address"
        elif text == f"{EMOJIS['edit']} ویرایش تماس":
            bot.send_message(user_id, f"{EMOJIS['edit']} شماره تماس جدید را وارد کنید (شماره باید با 09 شروع شود و 11 رقم باشد или 'رد کردن' برای خالی کردن): (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=skip_button())
            user_states[user_id] = "edit_place_phone"
        elif text == f"{EMOJIS['edit']} ویرایش عکس":
            bot.send_message(user_id, f"{EMOJIS['edit']} تا 8 عکس جدید ارسال کنید، سپس 'تایید عکس‌ها' را بزنید:", reply_markup=photo_confirm_keyboard())
            user_states[user_id] = "edit_place_photo"
            place_photos[user_id] = []
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
    elif state == "edit_place_photo":
        if text == "تایید عکس‌ها":
            if user_id in place_photos and len(place_photos[user_id]) > 0:
                photos_str = ','.join(place_photos[user_id])
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("UPDATE places SET photos = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", (photos_str, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
                conn.commit()
                conn.close()
                bot.send_message(user_id, f"{EMOJIS['success']} عکس‌ها به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
                del place_photos[user_id]
                user_states[user_id] = "edit_place_menu"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} حداقل یک عکس ارسال کنید!")
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً عکس ارسال کنید یا تایید کنید!")
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
            msg = f"{EMOJIS['info']} تعداد کل کاربران فعال: {total_users}"
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
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر را برای مسدود کردن وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_block_user"
        elif text == "🔓 رفع مسدودیت":
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر را برای رفع مسدودیت وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_unblock_user"
        elif text == f"{EMOJIS['score']} امتیاز کاربران":
            bot.send_message(user_id, f"{EMOJIS['score']} بخش امتیاز کاربران:", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
        elif text == "قرارگیری مکان برتر":
            bot.send_message(user_id, "بخش قرارگیری مکان برتر:", reply_markup=admin_top_place_menu())
            user_states[user_id] = "admin_top_place_menu"
        elif text == "مدیریت نظرات":
            bot.send_message(user_id, f"{EMOJIS['info']} عنوان مکان را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_manage_comments_title"
    elif state == "admin_top_place_menu":
        if text == "اضافه کردن رای":
            bot.send_message(user_id, f"{EMOJIS['info']} عنوان مکان مورد نظر را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_add_rating_title"
        elif text == "کم کردن رای":
            bot.send_message(user_id, f"{EMOJIS['info']} عنوان مکان مورد نظر را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_remove_rating_title"
    elif state == "admin_add_rating_title":
        if text.strip():
            user_data[user_id] = {'rating_title': text}
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر صاحب مکان را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_add_rating_numeric_id"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان نمی‌تواند خالی باشد!")
    elif state == "admin_add_rating_numeric_id":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                user_data[user_id]['rating_numeric_id'] = numeric_id
                bot.send_message(user_id, f"{EMOJIS['info']} تعداد رای‌ها را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
                user_states[user_id] = "admin_add_rating_count"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه یافت نشد!")
            except ValueError:
                bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "admin_add_rating_count":
        try:
            count = int(text)
            if count > 0:
                user_data[user_id]['rating_count'] = count
                bot.send_message(user_id, f"{EMOJIS['info']} امتیاز هر رای (0 تا 10) را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
                user_states[user_id] = "admin_add_rating_value"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} تعداد باید مثبت باشد!")
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "admin_add_rating_value":
        try:
            value = int(text)
            if 0 <= value <= 10:
                user_data[user_id]['rating_value'] = value
                title = user_data[user_id]['rating_title']
                numeric_id = user_data[user_id]['rating_numeric_id']
                count = user_data[user_id]['rating_count']
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT place_id, rating_sum, rating_count FROM places WHERE title = ? AND user_id = (SELECT user_id FROM users WHERE numeric_id = ?)", (title, numeric_id))
                place = c.fetchone()
                if place:
                    place_id = place[0]
                    old_sum = place[1]
                    old_count = place[2]
                    old_avg = old_sum / old_count if old_count > 0 else 0
                    new_sum = old_sum + (count * value)
                    new_count = old_count + count
                    new_avg = new_sum / new_count if new_count > 0 else 0
                    keyboard = confirm_keyboard()
                    msg = f"{EMOJIS['info']} آیا مطمئن هستید؟\nعنوان: {title}\nتعداد رای: {count}\nامتیاز: {value}"
                    bot.send_message(user_id, msg, reply_markup=keyboard)
                    user_data[user_id]['place_id'] = place_id
                    user_data[user_id]['new_sum'] = new_sum
                    user_data[user_id]['new_count'] = new_count
                    user_data[user_id]['old_avg'] = old_avg
                    user_data[user_id]['new_avg'] = new_avg
                    user_states[user_id] = "admin_add_rating_confirm"
                else:
                    bot.send_message(user_id, f"{EMOJIS['error']} مکان یافت نشد!")
                conn.close()
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} امتیاز بین 0 تا 10!")
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "admin_add_rating_confirm":
        if text == "بله":
            place_id = user_data[user_id]['place_id']
            new_sum = user_data[user_id]['new_sum']
            new_count = user_data[user_id]['new_count']
            old_avg = user_data[user_id]['old_avg']
            new_avg = user_data[user_id]['new_avg']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET rating_sum = ?, rating_count = ? WHERE place_id = ?", (new_sum, new_count, place_id))
            conn.commit()
            conn.close()
            check_top_place_change(place_id, old_avg, new_avg)
            bot.send_message(user_id, f"{EMOJIS['success']} رای‌ها اضافه شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_top_place_menu())
            user_states[user_id] = "admin_top_place_menu"
    elif state == "admin_remove_rating_title":
        if text.strip():
            user_data[user_id] = {'rating_title': text}
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر صاحب مکان را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_remove_rating_numeric_id"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان نمی‌تواند خالی باشد!")
    elif state == "admin_remove_rating_numeric_id":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                user_data[user_id]['rating_numeric_id'] = numeric_id
                bot.send_message(user_id, f"{EMOJIS['info']} تعداد رای‌ها را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
                user_states[user_id] = "admin_remove_rating_count"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه یافت نشد!")
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "admin_remove_rating_count":
        try:
            count = int(text)
            if count > 0:
                user_data[user_id]['rating_count'] = count
                bot.send_message(user_id, f"{EMOJIS['info']} امتیاز هر رای (0 تا 10) را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
                user_states[user_id] = "admin_remove_rating_value"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} تعداد باید مثبت باشد!")
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "admin_remove_rating_value":
        try:
            value = int(text)
            if 0 <= value <= 10:
                user_data[user_id]['rating_value'] = value
                title = user_data[user_id]['rating_title']
                numeric_id = user_data[user_id]['rating_numeric_id']
                count = user_data[user_id]['rating_count']
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT place_id, rating_sum, rating_count FROM places WHERE title = ? AND user_id = (SELECT user_id FROM users WHERE numeric_id = ?)", (title, numeric_id))
                place = c.fetchone()
                if place:
                    place_id = place[0]
                    old_sum = place[1]
                    old_count = place[2]
                    if count > old_count:
                        bot.send_message(user_id, f"{EMOJIS['error']} تعداد رای بیشتر از موجود است!")
                    else:
                        old_avg = old_sum / old_count if old_count > 0 else 0
                        new_sum = old_sum - (count * value)
                        new_count = old_count - count
                        new_avg = new_sum / new_count if new_count > 0 else 0
                        keyboard = confirm_keyboard()
                        msg = f"{EMOJIS['info']} آیا مطمئن هستید؟\nعنوان: {title}\nتعداد رای: {count}\nامتیاز: {value}"
                        bot.send_message(user_id, msg, reply_markup=keyboard)
                        user_data[user_id]['place_id'] = place_id
                        user_data[user_id]['new_sum'] = new_sum
                        user_data[user_id]['new_count'] = new_count
                        user_data[user_id]['old_avg'] = old_avg
                        user_data[user_id]['new_avg'] = new_avg
                        user_states[user_id] = "admin_remove_rating_confirm"
                else:
                    bot.send_message(user_id, f"{EMOJIS['error']} مکان یافت نشد!")
                conn.close()
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} امتیاز بین 0 تا 10!")
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "admin_remove_rating_confirm":
        if text == "بله":
            place_id = user_data[user_id]['place_id']
            new_sum = user_data[user_id]['new_sum']
            new_count = user_data[user_id]['new_count']
            old_avg = user_data[user_id]['old_avg']
            new_avg = user_data[user_id]['new_avg']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET rating_sum = ?, rating_count = ? WHERE place_id = ?", (new_sum, new_count, place_id))
            conn.commit()
            conn.close()
            check_top_place_change(place_id, old_avg, new_avg)
            bot.send_message(user_id, f"{EMOJIS['success']} رای‌ها کم شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_top_place_menu())
            user_states[user_id] = "admin_top_place_menu"
    elif state == "admin_manage_comments_title":
        if text.strip():
            user_data[user_id] = {'manage_title': text}
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی صاحب مکان را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_manage_comments_numeric_id"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} عنوان نمی‌تواند خالی باشد!")
    elif state == "admin_manage_comments_numeric_id":
        try:
            numeric_id = int(text)
            user_data[user_id]['manage_numeric_id'] = numeric_id
            bot.send_message(user_id, f"{EMOJIS['info']} کلمه اول نظر را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_manage_comments_first_word"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "admin_manage_comments_first_word":
        if text.strip():
            user_data[user_id]['manage_first_word'] = text.lower()
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر نظر دهنده را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_manage_comments_user_numeric_id"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} کلمه نمی‌تواند خالی باشد!")
    elif state == "admin_manage_comments_user_numeric_id":
        try:
            user_numeric_id = int(text)
            title = user_data[user_id]['manage_title']
            owner_numeric_id = user_data[user_id]['manage_numeric_id']
            first_word = user_data[user_id]['manage_first_word']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT place_id FROM places WHERE title = ? AND user_id = (SELECT user_id FROM users WHERE numeric_id = ?)", (title, owner_numeric_id))
            place = c.fetchone()
            if place:
                place_id = place[0]
                c.execute("SELECT comment_id, user_id, comment FROM comments WHERE place_id = ? AND user_id = (SELECT user_id FROM users WHERE numeric_id = ?) AND LOWER(comment) LIKE ?", 
                          (place_id, user_numeric_id, f"{first_word}%"))
                comment = c.fetchone()
                if comment:
                    comment_id = comment[0]
                    comment_text = comment[2]
                    user_db_id = comment[1]
                    keyboard = confirm_keyboard()
                    msg = f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این نظر را حذف کنید؟\n\n{comment_text}"
                    bot.send_message(user_id, msg, reply_markup=keyboard)
                    user_data[user_id]['manage_comment_id'] = comment_id
                    user_data[user_id]['manage_user_id'] = user_db_id
                    user_data[user_id]['manage_place_title'] = title
                    user_states[user_id] = "admin_manage_comments_confirm"
                else:
                    bot.send_message(user_id, f"{EMOJIS['error']} نظر یافت نشد!")
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} مکان یافت نشد!")
            conn.close()
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} عدد معتبر وارد کنید!")
    elif state == "admin_manage_comments_confirm":
        if text == "بله":
            comment_id = user_data[user_id]['manage_comment_id']
            user_db_id = user_data[user_id]['manage_user_id']
            title = user_data[user_id]['manage_place_title']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM comments WHERE comment_id = ?", (comment_id,))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} نظر حذف شد!", reply_markup=admin_menu())
            try:
                bot.send_message(user_db_id, f"{EMOJIS['warning']} نظر شما در مکان {title} توسط ادمین به دلیل نقض قوانین حذف شد. ⚠️")
            except:
                pass
            user_states[user_id] = "admin_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    elif state == "admin_score_menu":
        if text == f"{EMOJIS['add_score']} اضافه کردن امتیاز":
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر را برای اضافه کردن امتیاز وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_add_score_numeric_id"
        elif text == f"{EMOJIS['remove_score']} کم کردن امتیاز":
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر را برای کم کردن امتیاز وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_remove_score_numeric_id"
    elif state == "admin_add_score_numeric_id":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                user_data[user_id] = {
                    'target_numeric_id': numeric_id,
                    'target_user_id': target_user[0],
                    'target_name': target_user[1],
                    'target_score': target_user[4]
                }
                bot.send_message(user_id, f"{EMOJIS['info']} چند امتیاز می‌خواهید به این کاربر اضافه کنید؟ (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
                user_states[user_id] = "admin_add_score_amount"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه عددی یافت نشد!", reply_markup=admin_score_menu())
                user_states[user_id] = "admin_score_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=admin_sub_menu())
    elif state == "admin_add_score_amount":
        try:
            score_amount = int(text)
            if score_amount > 0:
                user_data[user_id]['score_amount'] = score_amount
                
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.row("بله", "خیر")
                keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                
                msg = f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید {score_amount} امتیاز به کاربر زیر اضافه کنید؟\n\n"
                msg += f"👤 نام: {user_data[user_id]['target_name']}\n"
                msg += f"🏆 امتیاز فعلی: {user_data[user_id]['target_score']}\n"
                msg += f"➕ امتیاز جدید: {user_data[user_id]['target_score'] + score_amount}"
                
                bot.send_message(user_id, msg, reply_markup=keyboard)
                user_states[user_id] = "admin_add_score_confirm"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} تعداد امتیاز باید بیشتر از صفر باشد!", reply_markup=admin_sub_menu())
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً عدد معتبر وارد کنید!", reply_markup=admin_sub_menu())
    elif state == "admin_add_score_confirm":
        if text == "بله":
            target_user_id = user_data[user_id]['target_user_id']
            score_amount = user_data[user_id]['score_amount']
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (score_amount, target_user_id))
            conn.commit()
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['success']} {score_amount} امتیاز با موفقیت به کاربر اضافه شد!", reply_markup=admin_menu())
            
            # ارسال پیام به کاربر
            try:
                bot.send_message(target_user_id, f"{EMOJIS['success']} ادمین {score_amount} امتیاز به شما اضافه کرد! 🎉\nامتیاز جدید شما: {user_data[user_id]['target_score'] + score_amount}")
            except:
                pass
            
            user_states[user_id] = "admin_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
    elif state == "admin_remove_score_numeric_id":
        try:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            if target_user:
                user_data[user_id] = {
                    'target_numeric_id': numeric_id,
                    'target_user_id': target_user[0],
                    'target_name': target_user[1],
                    'target_score': target_user[4]
                }
                bot.send_message(user_id, f"{EMOJIS['info']} چند امتیاز می‌خواهید از این کاربر کم کنید؟ (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
                user_states[user_id] = "admin_remove_score_amount"
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربری با این شناسه عددی یافت نشد!", reply_markup=admin_score_menu())
                user_states[user_id] = "admin_score_menu"
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً شناسه عددی معتبر وارد کنید!", reply_markup=admin_sub_menu())
    elif state == "admin_remove_score_amount":
        try:
            score_amount = int(text)
            if score_amount > 0:
                if score_amount <= user_data[user_id]['target_score']:
                    user_data[user_id]['score_amount'] = score_amount
                    
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.row("بله", "خیر")
                    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                    
                    msg = f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید {score_amount} امتیاز از کاربر زیر کم کنید؟\n\n"
                    msg += f"👤 نام: {user_data[user_id]['target_name']}\n"
                    msg += f"🏆 امتیاز فعلی: {user_data[user_id]['target_score']}\n"
                    msg += f"➖ امتیاز جدید: {user_data[user_id]['target_score'] - score_amount}"
                    
                    bot.send_message(user_id, msg, reply_markup=keyboard)
                    user_states[user_id] = "admin_remove_score_confirm"
                else:
                    bot.send_message(user_id, f"{EMOJIS['error']} تعداد امتیاز برای کم کردن بیشتر از امتیاز فعلی کاربر است!", reply_markup=admin_sub_menu())
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} تعداد امتیاز باید بیشتر از صفر باشد!", reply_markup=admin_sub_menu())
        except ValueError:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً عدد معتبر وارد کنید!", reply_markup=admin_sub_menu())
    elif state == "admin_remove_score_confirm":
        if text == "بله":
            target_user_id = user_data[user_id]['target_user_id']
            score_amount = user_data[user_id]['score_amount']
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET score = score - ? WHERE user_id = ?", (score_amount, target_user_id))
            conn.commit()
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['success']} {score_amount} امتیاز با موفقیت از کاربر کم شد!", reply_markup=admin_menu())
            
            # ارسال پیام به کاربر
            try:
                bot.send_message(target_user_id, f"{EMOJIS['warning']} ادمین {score_amount} امتیاز از شما کم کرد! ⚠️\nامتیاز جدید شما: {user_data[user_id]['target_score'] - score_amount}")
            except:
                pass
            
            user_states[user_id] = "admin_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
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
            bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر مورد نظر را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
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
                username = target_user[1]
                user_data[user_id] = {'target_telegram_id': telegram_id, 'target_numeric_id': numeric_id}
                
                if is_user_blocked(telegram_id):
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.row("بله", "خیر")
                    keyboard.row(f"{EMOJIS['back']} برگشت", "برگشت به ادمین")
                    bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید کاربر {username} را از مسدودیت خارج کنید؟", reply_markup=keyboard)
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
                bot.send_message(user_id, f"{EMOJIS['info']} شناسه عددی کاربر مالک مکان را وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=admin_sub_menu())
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
            c.execute("DELETE FROM comments WHERE place_id = ?", (place_id,))
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
            old_sum = current[0]
            old_count = current[1]
            old_avg = old_sum / old_count if old_count > 0 else 0
            rating_sum = old_sum + rating
            rating_count = old_count + 1
            new_avg = rating_sum / rating_count if rating_count > 0 else 0
            c.execute("UPDATE places SET rating_sum = ?, rating_count = ? WHERE place_id = ?", (rating_sum, rating_count, place_id))
            # دریافت اطلاعات کاربر
            c.execute("SELECT name, age, gender FROM users WHERE user_id = ?", (user_id,))
            user_info = c.fetchone()
            owner_id = current[2]
            conn.commit()
            conn.close()
            check_top_place_change(place_id, old_avg, new_avg)
            # ارسال پیام به کاربر
            bot.send_message(user_id, f"{EMOJIS['success']} امتیاز شما ({rating}) ثبت شد! میانگین امتیاز: {new_avg:.1f}", reply_markup=get_place_menu())
            bot.send_animation(user_id, 'https://t.me/animated_gifs/success.gif')
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
    elif state == "comment_add":
        if text.strip():
            user_data[user_id]['comment_text'] = text
            keyboard = confirm_keyboard()
            bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این نظر را ثبت کنید؟\n\n{text}", reply_markup=keyboard)
            user_states[user_id] = "comment_add_confirm"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} نظر نمی‌تواند خالی باشد!")
    elif state == "comment_add_confirm":
        if text == "بله":
            place_id = user_data[user_id]['place_id']
            comment_text = user_data[user_id]['comment_text']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO comments (place_id, user_id, comment) VALUES (?, ?, ?)", (place_id, user_id, comment_text))
            conn.commit()
            # اطلاع به صاحب
            c.execute("SELECT user_id, title FROM places WHERE place_id = ?", (place_id,))
            owner_id, title = c.fetchone()
            c.execute("SELECT name, age, gender FROM users WHERE user_id = ?", (user_id,))
            user_info = c.fetchone()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} نظر شما با موفقیت ثبت شد!", reply_markup=get_place_menu())
            bot.send_animation(user_id, 'https://t.me/animated_gifs/success.gif')
            try:
                bot.send_message(owner_id, f"{EMOJIS['comment']} نظر جدید برای مکان {title}:\nاز: {user_info[0]} ({user_info[1]} ساله، {user_info[2]})\n\n{comment_text}")
            except:
                pass
            user_states[user_id] = "place_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} ثبت نظر لغو شد.", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
    elif state == "comment_delete_confirm":
        if text == "بله":
            place_id = user_data[user_id]['place_id']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM comments WHERE place_id = ? AND user_id = ?", (place_id, user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} نظر حذف شد!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
    elif state == "message_to_owner":
        if content_type == 'text':
            message_text = text
        else:
            message_text = "رسانه ارسال شده"
        user_data[user_id]['message_content'] = message.to_dict()  # ذخیره کل پیام
        keyboard = confirm_keyboard()
        bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این پیام را ارسال کنید؟", reply_markup=keyboard)
        user_states[user_id] = "message_to_owner_confirm"
    elif state == "message_to_owner_confirm":
        if text == "بله":
            place_id = user_data[user_id]['place_id']
            message_content = user_data[user_id]['message_content']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_id, title FROM places WHERE place_id = ?", (place_id,))
            owner_id, title = c.fetchone()
            c.execute("SELECT name, age, gender, numeric_id FROM users WHERE user_id = ?", (user_id,))
            user_info = c.fetchone()
            conn.close()
            if owner_id:
                try:
                    msg = f"{EMOJIS['message']} پیام جدید برای مکان {title}:\nاز: {user_info[0]} ({user_info[1]} ساله، {user_info[2]})\nشناسه عددی: {user_info[3]}\n\n"
                    bot.send_message(owner_id, msg)
                    # ارسال محتوای اصلی
                    bot.forward_message(owner_id, user_id, message_content['message_id'])
                    keyboard = message_menu()
                    bot.send_message(owner_id, "انتخاب کنید:", reply_markup=keyboard)
                    # ذخیره برای جواب
                    user_data[owner_id] = {'reply_to_user': user_id, 'reply_place_id': place_id}
                    bot.send_message(user_id, f"{EMOJIS['success']} پیام ارسال شد!", reply_markup=get_place_menu())
                    bot.send_animation(user_id, 'https://t.me/animated_gifs/success.gif')
                except:
                    bot.send_message(user_id, f"{EMOJIS['error']} خطا در ارسال!")
            user_states[user_id] = "place_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} ارسال لغو شد.", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
    elif state == "message_reply":
        if content_type == 'text':
            reply_text = text
        else:
            reply_text = "رسانه ارسال شده"
        user_data[user_id]['reply_content'] = message.to_dict()
        keyboard = confirm_keyboard()
        bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید این جواب را ارسال کنید؟", reply_markup=keyboard)
        user_states[user_id] = "message_reply_confirm"
    elif state == "message_reply_confirm":
        if text == "بله":
            reply_to_user = user_data[user_id]['reply_to_user']
            reply_content = user_data[user_id]['reply_content']
            place_id = user_data[user_id]['reply_place_id']
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT title FROM places WHERE place_id = ?", (place_id,))
            title = c.fetchone()[0]
            conn.close()
            try:
                bot.send_message(reply_to_user, f"{EMOJIS['reply']} جواب از صاحب مکان {title}:")
                bot.forward_message(reply_to_user, user_id, reply_content['message_id'])
                bot.send_message(user_id, f"{EMOJIS['success']} جواب ارسال شد!", reply_markup=admin_menu() if user_id == ADMIN_ID else get_place_menu())
            except:
                bot.send_message(user_id, f"{EMOJIS['error']} خطا در ارسال!")
            user_states[user_id] = "admin_menu" if user_id == ADMIN_ID else "place_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} ارسال لغو شد.", reply_markup=message_menu())
            user_states[user_id] = "main_menu"  # یا حالت قبلی
    elif state == "message_block_confirm":
        if text == "بله":
            reply_to_user = user_data[user_id]['reply_to_user']
            place_id = user_data[user_id]['reply_place_id']
            block_user_for_place(place_id, reply_to_user)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT title FROM places WHERE place_id = ?", (place_id,))
            title = c.fetchone()[0]
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} کاربر بلاک شد!", reply_markup=get_place_menu())
            try:
                bot.send_message(reply_to_user, f"{EMOJIS['warning']} شما توسط صاحب مکان {title} بلاک شده‌اید. ⚠️")
            except:
                pass
            user_states[user_id] = "place_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=message_menu())
    elif state == "message_unblock_confirm":
        if text == "بله":
            reply_to_user = user_data[user_id]['reply_to_user']
            place_id = user_data[user_id]['reply_place_id']
            unblock_user_for_place(place_id, reply_to_user)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT title FROM places WHERE place_id = ?", (place_id,))
            title = c.fetchone()[0]
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} کاربر رفع بلاک شد!", reply_markup=get_place_menu())
            try:
                bot.send_message(reply_to_user, f"{EMOJIS['success']} شما توسط صاحب مکان {title} رفع بلاک شده‌اید و می‌توانید پیام ارسال کنید. 🔥")
            except:
                pass
            user_states[user_id] = "place_menu"
        elif text == "خیر":
            bot.send_message(user_id, f"{EMOJIS['info']} عملیات لغو شد.", reply_markup=message_menu())

# مدیریت عکس‌ها
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما به دلیل نقض قوانین از طرف ادمین مسدود شده اید❌برای رفع مسدودیت باید هزینه ای اندک بپردازید ‼️ برای هماهنگی به ایدی ادمین پیام دهید: @Sedayegoyom10")
        return
    state = user_states.get(user_id, "")
    if state in ["place_add_photo", "edit_place_photo"]:
        if user_id != ADMIN_ID and state == "place_add_photo":
            bot.send_message(user_id, f"{EMOJIS['error']} فقط ادمین می‌تواند مکان اضافه کند!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        photo_id = message.photo[-1].file_id
        if user_id not in place_photos:
            place_photos[user_id] = []
        if len(place_photos[user_id]) < 8:
            place_photos[user_id].append(photo_id)
            bot.send_message(user_id, f"{EMOJIS['success']} عکس {len(place_photos[user_id])} اضافه شد. می‌توانید تا 8 عکس ارسال کنید.")
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} حداکثر 8 عکس مجاز است!")

# مدیریت کال‌بک‌ها
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
    elif data.startswith("delete_place"):
        place_id = int(data.split("_")[2])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id FROM places WHERE place_id = ?", (place_id,))
        place = c.fetchone()
        if place and (place[0] == user_id or user_id == ADMIN_ID):
            c.execute("DELETE FROM places WHERE place_id = ?", (place_id,))
            c.execute("DELETE FROM place_ratings WHERE place_id = ?", (place_id,))
            c.execute("DELETE FROM comments WHERE place_id = ?", (place_id,))
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
            bot.send_message(user_id, f"{EMOJIS['rating']} امتیازی بین 0 تا 10 برای این مکان وارد کنید: (شماره به انگلیسی باشه مثل 1 2 3 4 5 6 7 8 9)", reply_markup=back_button_only())
            user_states[user_id] = "place_rate"
    elif data.startswith("add_comment"):
        place_id = int(data.split("_")[2])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT comment_id FROM comments WHERE place_id = ? AND user_id = ?", (place_id, user_id))
        existing_comment = c.fetchone()
        conn.close()
        user_data[user_id] = {'place_id': place_id}
        if existing_comment:
            keyboard = comment_menu(True)
            bot.send_message(user_id, f"{EMOJIS['info']} شما قبلاً نظر داده‌اید. می‌توانید حذف کنید:", reply_markup=keyboard)
            user_states[user_id] = "comment_delete"
        else:
            bot.send_message(user_id, f"{EMOJIS['comment']} نظر خود را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "comment_add"
    elif data.startswith("view_comments"):
        place_id = int(data.split("_")[2])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT comments.comment, users.name, users.age, users.gender, users.numeric_id FROM comments JOIN users ON comments.user_id = users.user_id WHERE comments.place_id = ?", (place_id,))
        comments = c.fetchall()
        conn.close()
        if comments:
            msg = f"{EMOJIS['comments']} نظرات:\n\n"
            for com in comments:
                msg += f"{com[1]} ({com[2]} ساله، {com[3]}): {com[0]}\n"
                if user_id == ADMIN_ID:
                    msg += f"شناسه عددی: {com[4]}\n"
                msg += "-------------------\n"
            bot.send_message(user_id, msg, reply_markup=back_button_only())
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} هیچ نظری وجود ندارد!", reply_markup=back_button_only())
        user_states[user_id] = "place_menu"
    elif data.startswith("message_owner"):
        place_id = int(data.split("_")[2])
        if is_user_blocked_for_place(place_id, user_id):
            bot.send_message(user_id, f"{EMOJIS['error']} شما توسط صاحب این مکان بلاک شده‌اید!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
            return
        user_data[user_id] = {'place_id': place_id}
        bot.send_message(user_id, f"{EMOJIS['message']} پیام خود را برای صاحب مکان ارسال کنید (متن، عکس، ویس و ...):", reply_markup=back_button_only())
        user_states[user_id] = "message_to_owner"
    elif data.startswith("help_next"):
        page = int(data.split("_")[2]) + 1
        send_help_page(user_id, page)
    elif data.startswith("help_prev"):
        page = int(data.split("_")[2]) - 1
        send_help_page(user_id, page)
    elif data.startswith("comment_delete"):
        place_id = user_data[user_id]['place_id']
        keyboard = confirm_keyboard()
        bot.send_message(user_id, f"{EMOJIS['info']} آیا مطمئن هستید که می‌خواهید نظر خود را حذف کنید؟", reply_markup=keyboard)
        user_states[user_id] = "comment_delete_confirm"

# اجرای ربات در حالت وب هوک
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)