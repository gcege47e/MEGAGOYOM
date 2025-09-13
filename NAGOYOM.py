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
    "remove_score": "⬇️"
}

# پیام خوش‌آمدگویی و قوانین
WELCOME_MESSAGE = f"""
{EMOJIS['home']}به ربات گویم‌نما خوش آمدید! {EMOJIS['success']}

برای استفاده از این ربات، لطفاً قوانین زیر را مطالعه و تأیید کنید:

{EMOJIS['info']} قوانین استفاده از ربات:

1. در صورتی که صاحب یک مکان هستید، مسئولیت هرگونه مشکل یا اتفاق مرتبط با مکان ثبت‌شده بر عهده شماست.
2. از ارسال محتوای غیراخلاقی، توهین‌آمیز یا نقض‌کننده قوانین ربات جداً خودداری کنید.
3. اطلاعات مکان‌ها را با دقت و صحت وارد کنید.
4. هرگونه سوءاستفاده از اطلاعات مکان‌ها ممنوع بوده و منجر به مسدود شدن حساب کاربری شما خواهد شد.
5. در صورت نقض قوانین، حساب شما مسدود شده و برای رفع مسدودیت نیاز به پرداخت هزینه‌ای اندک خواهد بود.

{EMOJIS['warning']} توجه: هرگونه استفاده غیرمجاز از اطلاعات مکان‌ها پیگرد قانونی دارد.

لطفاً با دقت قوانین را مطالعه کرده و گزینه مناسب را انتخاب کنید: """

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

# دسته‌بندی مکان‌ها (کامل و به‌روز شده)
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
        "غذاهای محلی و Ethnic Cuisine"
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
        "فروشگاه محصولات سلامت و wellness",
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
        "مراکز یوга و مدیتیشن",
        "باشگاه‌های ورزش‌های رزمی",
        "مراکز اسکیت و رولر",
        "باشگاه‌های بوکس و MMA",
        "مراکز ورزش‌های آبی",
        "باشگاه‌های گلف و تنیس",
        "مراکز ماهیگیری و شکار",
        "باشگاه‌های سوارکاری"
    ],
    "🏨 اقامت و سفر": [
        "هتل و هتل آپارتمان (هتل، هتل آпارتمان)",
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
        "خدمات انتقال مسافر (شیپینگ، ترانسفر)",
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
        "خدمات پخش محصولات خودرویی"
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
        "مراکز آموزش علوم مختلف (ریاضی، فیزیک، شímica)",
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
        "آموزشگاه‌های زبان اشاره"
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
        "پیست دوچرخه‌سواری (دوچرخه‌سواری, BMX)",
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
        "مسیرهای پیاده‌روی و trekking",
        "مراکز چادرزنی و caravanning",
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
        "شرکت‌های فناوری اطلاعات (IT، نرم‌افزار)",
        "استودیوهای عکاسی و فیلمبرداری (عکاسی، فیلمبرداری)",
        "مراکز خدمات اداری و کپی (خدمات اداری، کپی)",
        "شرکت‌های حمل و نقل و باربری (حمل نقل، باربری)",
        "خدمات نظافتی و نگهداری (نظافتی، نگهداری)",
        "شرکت‌های رسانه‌ای و انتشاراتی",
        "مراکز تحقیقاتی و توسعه",
        "شرکت‌های مشاوره منابع انسانی",
        "مراکز خدمات مشاوره کسب‌وکار",
        "شرکت‌های طراحی سایت و سئو",
        "مراکز خدمات ترجمه و interpreter",
        "شرکت‌های خدمات امنیتی",
        "مراکز خدمات پشتیبانی IT",
        "شرکت‌های خدمات مشاوره مالیاتی",
        "مراکز خدمات برندینگ و هویت سازی"
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
        "خدمات حمل و نقل معلولین و سالمندان",
        "خدمات آموزش مجازی و آنلاین",
        "خدمات مشاوره انرژی و بهینه‌سازی",
        "خدمات اجاره تجهیزات و لوازم"
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

# منوها
def main_menu(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{EMOJIS['profile']} پروفایل")
    keyboard.row(f"{EMOJIS['places']} مکان‌ها", f"{EMOJIS['rating']} مکان‌های برتر")
    keyboard.row(f"{EMOJIS['star']} کاربران برتر")
    keyboard.row(f"{EMOJIS['link']} لینک‌ها", f"{EMOJIS['help']} راهنما")
    if user_id == ADMIN_ID:
        keyboard.row(f"{EMOJIS['admin']} ادمین")
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

def search_options_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("مغازه های آدرس مورد نظر")
    keyboard.row("جستجوی مغازه مورد نظر")
    keyboard.row(f"{EMOJIS['back']} برگشت", f"{EMOJIS['home']} صفحه اصلی")
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

# مدیریت پیام‌ها - بهبود برای کارکرد بدون نیاز به /start
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, f"{EMOJIS['error']} شما به دلیل نقض قوانین از طرف ادمین مسدود شده اید❌برای رفع مسدودیت باید هزینه ای اندک بپردازید ‼️ برای هماهنگی به ایدی ادمین پیام دهید: @Sedayegoyom10")
        return
    
    state = user_states.get(user_id, "")
    text = message.text
    
    # مدیریت حالت‌های مختلف
    if state == "awaiting_name":
        user_data[user_id]['name'] = text
        bot.send_message(user_id, f"{EMOJIS['profile']} سن خود را وارد کنید:")
        user_states[user_id] = "awaiting_age"
    
    elif state == "awaiting_age":
        if not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} سن باید یک عدد باشد. لطفاً دوباره وارد کنید:")
            return
        user_data[user_id]['age'] = int(text)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("مرد", "زن")
        bot.send_message(user_id, f"{EMOJIS['profile']} جنسیت خود را انتخاب کنید:", reply_markup=keyboard)
        user_states[user_id] = "awaiting_gender"
    
    elif state == "awaiting_gender":
        if text not in ["مرد", "زن"]:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً از گزینه‌های ارائه شده استفاده کنید:")
            return
        user_data[user_id]['gender'] = text
        save_user(user_id, user_data[user_id]['name'], user_data[user_id]['age'], user_data[user_id]['gender'])
        bot.send_message(user_id, f"{EMOJIS['success']} ثبت نام شما با موفقیت انجام شد!", reply_markup=main_menu(user_id))
        user_states[user_id] = "main_menu"
    
    elif state == "main_menu":
        if text == f"{EMOJIS['profile']} پروفایل":
            bot.send_message(user_id, f"{EMOJIS['profile']} بخش پروفایل", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
        
        elif text == f"{EMOJIS['places']} مکان‌ها":
            bot.send_message(user_id, f"{EMOJIS['places']} بخش مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        
        elif text == f"{EMOJIS['help']} راهنما":
            help_text = f"""
{EMOJIS['help']} راهنمای استفاده از ربات گویم‌نما:

{EMOJIS['profile']} پروفایل: مشاهده و ویرایش اطلاعات شخصی
{EMOJIS['places']} مکان‌ها: مدیریت مکان‌های ثبت شده

در بخش مکان‌ها می‌توانید:
{EMOJIS['add']} اضافه کردن مکان: ثبت مکان جدید با جزئیات کامل
{EMOJIS['view']} مشاهده مکان‌ها: دیدن همه مکان‌های ثبت شده
{EMOJIS['view']} مکان‌های من: دیدن مکان‌های ثبت شده توسط شما
{EMOJIS['view']} جستجو: جستجوی پیشرفته مکان‌ها

{EMOJIS['rating']} مکان‌های برتر: مشاهده مکان‌های با امتیاز بالا
{EMOJIS['star']} کاربران برتر: مشاهده کاربران فعال
{EMOJIS['link']} لینک‌ها: دسترسی به لینک‌های مفید

دسته‌بندی‌های مکان‌ها:
🍽️ خوراکی و نوشیدنی: رستوران، کافه، فست فود و...
🛍️ خرید و فروش: فروشگاه، پاساژ، سوپرمارکت و...
✂️ زیبایی و آرایشی: آرایشگاه، سالن زیبایی و...
🏥 درمان و سلامت: بیمارستان، داروخانه، کلینیک و...
⚽ ورزش و سرگرمی: باشگاه، سینما، شهربازی و...
🏨 اقامت و سفر: هتل، مسافرخانه، آژانس مسافرتی و...
🏛️ خدمات عمومی و اداری: بانک، شهرداری، پلیس و...
🚗 خدمات شهری و حمل‌ونقل: پمپ بنزین، تعمیرگاه، پارکینگ و...
📚 آموزش و فرهنگ: مدرسه، دانشگاه، کتابخانه و...
🕌 مذهبی و معنوی: مسجد، حسینیه، کلیسا و...
🌳 طبیعت و تفریح آزاد: پارک، باغ وحش، ساحل و...
💼 کسب‌وکار و حرفه‌ای: شرکت، دفتر کار، کارخانه و...
🧰 خدمات تخصصی و فنی: تعمیرات، نصب، خدمات فنی و...

برای جستجو می‌توانید از دو روش استفاده کنید:
1. مغازه های آدرس مورد نظر: جستجو بر اساس آدرس
2. جستجوی مغازه مورد نظر: جستجو بر اساس نام و آدرس

امکانات ادمین فقط برای مدیران سیستم قابل دسترسی است.
            """
            bot.send_message(user_id, help_text, reply_markup=main_menu(user_id))
        
        elif text == f"{EMOJIS['admin']} ادمین" and user_id == ADMIN_ID:
            bot.send_message(user_id, f"{EMOJIS['admin']} به پنل ادمین خوش آمدید!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    
    elif state == "profile_menu":
        if text == "مشاهده پروفایل":
            user = get_user(user_id)
            if user:
                profile_text = f"""
{EMOJIS['profile']} اطلاعات پروفایل:

نام: {user[1]}
سن: {user[2]}
جنسیت: {user[3]}
امتیاز: {user[4]}
شناسه عددی: {user[5]}
                """
                bot.send_message(user_id, profile_text, reply_markup=profile_menu())
            else:
                bot.send_message(user_id, f"{EMOJIS['error']} اطلاعات پروفایل یافت نشد!", reply_markup=profile_menu())
        
        elif text == "تغییر نام":
            bot.send_message(user_id, f"{EMOJIS['edit']} نام جدید خود را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "profile_edit_name"
        
        elif text == "تغییر سن":
            bot.send_message(user_id, f"{EMOJIS['edit']} سن جدید خود را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "profile_edit_age"
        
        elif text == "تغییر جنسیت":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("مرد", "زن")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['edit']} جنسیت جدید خود را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "profile_edit_gender"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} بازگشت به صفحه اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    
    elif state == "profile_edit_name":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به پروفایل", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
        else:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET name = ? WHERE user_id = ?", (text, user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} نام شما با موفقیت به‌روزرسانی شد!", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
    
    elif state == "profile_edit_age":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به پروفایل", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
        elif not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} سن باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        else:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET age = ? WHERE user_id = ?", (int(text), user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} سن شما با موفقیت به‌روزرسانی شد!", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
    
    elif state == "profile_edit_gender":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به پروفایل", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
        elif text not in ["مرد", "زن"]:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً از گزینه‌های ارائه شده استفاده کنید:")
        else:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET gender = ? WHERE user_id = ?", (text, user_id))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} جنسیت شما با موفقیت به‌روزرسانی شد!", reply_markup=profile_menu())
            user_states[user_id] = "profile_menu"
    
    elif state == "place_menu":
        if text == f"{EMOJIS['add']} اضافه کردن مکان":
            if user_id != ADMIN_ID:
                bot.send_message(user_id, f"{EMOJIS['error']} فقط ادمین می‌تواند مکان اضافه کند!", reply_markup=get_place_menu())
                return
            
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for category in PLACE_CATEGORIES.keys():
                keyboard.row(category)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            
            bot.send_message(user_id, f"{EMOJIS['add']} دسته‌بندی مکان را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_add_category"
            user_data[user_id] = {}
        
        elif text == f"{EMOJIS['view']} مشاهده مکان‌ها":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM places ORDER BY place_id DESC LIMIT 10")
            places = c.fetchall()
            conn.close()
            
            if not places:
                bot.send_message(user_id, f"{EMOJIS['error']} هیچ مکانی ثبت نشده است!", reply_markup=get_place_menu())
                return
            
            for place in places:
                place_id, user_id_place, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift, rating_sum, rating_count = place
                
                # پیدا کردن کاربر صاحب مکان
                owner = get_user(user_id_place)
                owner_numeric_id = owner[5] if owner else "نامشخص"
                
                rating_avg = rating_sum / rating_count if rating_count > 0 else 0
                
                place_text = f"""
{EMOJIS['places']} {title}
{EMOJIS['info']} دسته: {category} - {subcategory}
{EMOJIS['document']} توضیحات: {description}
{EMOJIS['link']} آدرس: {address}
{EMOJIS['user']} تماس: {phone}
{EMOJIS['rating']} امتیاز: {rating_avg:.1f} از 10 ({rating_count} رأی)
{EMOJIS['star']} شیفت صبح: {morning_shift if morning_shift else 'تعیین نشده'}
{EMOJIS['star']} شیفت عصر: {afternoon_shift if afternoon_shift else 'تعیین نشده'}
{EMOJIS['user']} شناسه صاحب مکان: {owner_numeric_id}
                """
                
                if photo:
                    bot.send_photo(user_id, photo, caption=place_text, reply_markup=place_view_result_menu())
                else:
                    bot.send_message(user_id, place_text, reply_markup=place_view_result_menu())
            
            user_states[user_id] = "place_view_result"
        
        elif text == f"{EMOJIS['view']} مکان‌های من":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM places WHERE user_id = ? ORDER BY place_id DESC", (user_id,))
            places = c.fetchall()
            conn.close()
            
            if not places:
                bot.send_message(user_id, f"{EMOJIS['error']} شما هیچ مکانی ثبت نکرده‌اید!", reply_markup=get_place_menu())
                return
            
            for place in places:
                place_id, user_id_place, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift, rating_sum, rating_count = place
                
                rating_avg = rating_sum / rating_count if rating_count > 0 else 0
                
                place_text = f"""
{EMOJIS['places']} {title}
{EMOJIS['info']} دسته: {category} - {subcategory}
{EMOJIS['document']} توضیحات: {description}
{EMOJIS['link']} آدرس: {address}
{EMOJIS['user']} تماس: {phone}
{EMOJIS['rating']} امتیاز: {rating_avg:.1f} از 10 ({rating_count} رأی)
{EMOJIS['star']} شیفت صبح: {morning_shift if morning_shift else 'تعیین نشده'}
{EMOJIS['star']} شیفت عصر: {afternoon_shift if afternoon_shift else 'تعیین نشده'}
                """
                
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place_id}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place_id}"))
                
                if photo:
                    bot.send_photo(user_id, photo, caption=place_text, reply_markup=keyboard)
                else:
                    bot.send_message(user_id, place_text, reply_markup=keyboard)
            
            bot.send_message(user_id, f"{EMOJIS['success']} مکان‌های شما نمایش داده شدند.", reply_markup=get_place_menu())
        
        elif text == f"{EMOJIS['view']} جستجو":
            bot.send_message(user_id, f"{EMOJIS['info']} روش جستجو را انتخاب کنید:", reply_markup=search_options_menu())
            user_states[user_id] = "search_options"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} بازگشت به صفحه اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    
    elif state == "search_options":
        if text == "مغازه های آدرس مورد نظر":
            bot.send_message(user_id, f"{EMOJIS['info']} آدرس مورد نظر یا محدوده دلخواه را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "search_by_address"
        
        elif text == "جستجوی مغازه مورد نظر":
            bot.send_message(user_id, f"{EMOJIS['info']} نام مکان مورد نظر را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "search_by_name_input"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} بازگشت به صفحه اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    
    elif state == "search_by_address":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به روش‌های جستجو", reply_markup=search_options_menu())
            user_states[user_id] = "search_options"
        else:
            address_query = text
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM places WHERE address LIKE ? ORDER BY place_id DESC", (f"%{address_query}%",))
            places = c.fetchall()
            conn.close()
            
            if not places:
                bot.send_message(user_id, f"{EMOJIS['error']} هیچ مکانی در این محدوده ثبت نشده است!", reply_markup=search_result_menu())
                user_states[user_id] = "search_result"
                return
            
            for place in places:
                place_id, user_id_place, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift, rating_sum, rating_count = place
                
                # پیدا کردن کاربر صاحب مکان
                owner = get_user(user_id_place)
                owner_numeric_id = owner[5] if owner else "نامشخص"
                
                rating_avg = rating_sum / rating_count if rating_count > 0 else 0
                
                place_text = f"""
{EMOJIS['places']} {title}
{EMOJIS['info']} دسته: {category} - {subcategory}
{EMOJIS['document']} توضیحات: {description}
{EMOJIS['link']} آدرس: {address}
{EMOJIS['user']} تماس: {phone}
{EMOJIS['rating']} امتیاز: {rating_avg:.1f} از 10 ({rating_count} رأی)
{EMOJIS['star']} شیفت صبح: {morning_shift if morning_shift else 'تعیین نشده'}
{EMOJIS['star']} شیفت عصر: {afternoon_shift if afternoon_shift else 'تعیین نشده'}
{EMOJIS['user']} شناسه صاحب مکان: {owner_numeric_id}
                """
                
                if photo:
                    bot.send_photo(user_id, photo, caption=place_text)
                else:
                    bot.send_message(user_id, place_text)
            
            bot.send_message(user_id, f"{EMOJIS['success']} جستجو بر اساس آدرس '{address_query}' انجام شد.", reply_markup=search_result_menu())
            user_states[user_id] = "search_result"
    
    elif state == "search_by_name_input":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به روش‌های جستجو", reply_markup=search_options_menu())
            user_states[user_id] = "search_options"
        else:
            user_data[user_id] = {'search_name': text}
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row("رد کردن")
            keyboard.row(f"{EMOJIS['back']} برگشت")
            bot.send_message(user_id, f"{EMOJIS['info']} آدرس مورد نظر را وارد کنید یا 'رد کردن' را بزنید:", reply_markup=keyboard)
            user_states[user_id] = "search_by_name_address"
    
    elif state == "search_by_name_address":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به روش‌های جستجو", reply_markup=search_options_menu())
            user_states[user_id] = "search_options"
        else:
            name_query = user_data[user_id]['search_name']
            address_query = text if text != "رد کردن" else ""
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            if address_query:
                # جستجو هم بر اساس نام و هم آدرس
                c.execute("SELECT * FROM places WHERE (title LIKE ? OR category LIKE ? OR subcategory LIKE ?) AND address LIKE ? ORDER BY place_id DESC", 
                         (f"%{name_query}%", f"%{name_query}%", f"%{name_query}%", f"%{address_query}%"))
            else:
                # جستجو فقط بر اساس نام
                c.execute("SELECT * FROM places WHERE title LIKE ? OR category LIKE ? OR subcategory LIKE ? ORDER BY place_id DESC", 
                         (f"%{name_query}%", f"%{name_query}%", f"%{name_query}%"))
            
            places = c.fetchall()
            conn.close()
            
            if not places:
                bot.send_message(user_id, f"{EMOJIS['error']} هیچ مکانی با این مشخصات یافت نشد!", reply_markup=search_result_menu())
                user_states[user_id] = "search_result"
                return
            
            for place in places:
                place_id, user_id_place, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift, rating_sum, rating_count = place
                
                # پیدا کردن کاربر صاحب مکان
                owner = get_user(user_id_place)
                owner_numeric_id = owner[5] if owner else "نامشخص"
                
                rating_avg = rating_sum / rating_count if rating_count > 0 else 0
                
                place_text = f"""
{EMOJIS['places']} {title}
{EMOJIS['info']} دسته: {category} - {subcategory}
{EMOJIS['document']} توضیحات: {description}
{EMOJIS['link']} آدرس: {address}
{EMOJIS['user']} تماس: {phone}
{EMOJIS['rating']} امتیاز: {rating_avg:.1f} از 10 ({rating_count} رأی)
{EMOJIS['star']} شیفت صبح: {morning_shift if morning_shift else 'تعیین نشده'}
{EMOJIS['star']} شیفت عصر: {afternoon_shift if afternoon_shift else 'تعیین نشده'}
{EMOJIS['user']} شناسه صاحب مکان: {owner_numeric_id}
                """
                
                if photo:
                    bot.send_photo(user_id, photo, caption=place_text)
                else:
                    bot.send_message(user_id, place_text)
            
            search_type = f"نام '{name_query}' و آدرس '{address_query}'" if address_query else f"نام '{name_query}'"
            bot.send_message(user_id, f"{EMOJIS['success']} جستجو بر اساس {search_type} انجام شد.", reply_markup=search_result_menu())
            user_states[user_id] = "search_result"
    
    elif state == "search_result":
        if text == "جستجو دوباره":
            bot.send_message(user_id, f"{EMOJIS['info']} روش جستجو را انتخاب کنید:", reply_markup=search_options_menu())
            user_states[user_id] = "search_options"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} بازگشت به صفحه اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    
    elif state == "place_view_result":
        if text == "مشاهده دوباره":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM places ORDER BY place_id DESC LIMIT 10")
            places = c.fetchall()
            conn.close()
            
            if not places:
                bot.send_message(user_id, f"{EMOJIS['error']} هیچ مکانی ثبت نشده است!", reply_markup=get_place_menu())
                user_states[user_id] = "place_menu"
                return
            
            for place in places:
                place_id, user_id_place, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift, rating_sum, rating_count = place
                
                # پیدا کردن کاربر صاحب مکان
                owner = get_user(user_id_place)
                owner_numeric_id = owner[5] if owner else "نامشخص"
                
                rating_avg = rating_sum / rating_count if rating_count > 0 else 0
                
                place_text = f"""
{EMOJIS['places']} {title}
{EMOJIS['info']} دسته: {category} - {subcategory}
{EMOJIS['document']} توضیحات: {description}
{EMOJIS['link']} آدرس: {address}
{EMOJIS['user']} تماس: {phone}
{EMOJIS['rating']} امتیاز: {rating_avg:.1f} از 10 ({rating_count} رأی)
{EMOJIS['star']} شیفت صبح: {morning_shift if morning_shift else 'تعیین نشده'}
{EMOJIS['star']} شیفت عصر: {afternoon_shift if afternoon_shift else 'تعیین نشده'}
{EMOJIS['user']} شناسه صاحب مکان: {owner_numeric_id}
                """
                
                if photo:
                    bot.send_photo(user_id, photo, caption=place_text, reply_markup=place_view_result_menu())
                else:
                    bot.send_message(user_id, place_text, reply_markup=place_view_result_menu())
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} بازگشت به صفحه اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    
    elif state == "place_add_category":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        elif text in PLACE_CATEGORIES:
            user_data[user_id]['category'] = text
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for subcategory in PLACE_CATEGORIES[text]:
                keyboard.row(subcategory)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            
            bot.send_message(user_id, f"{EMOJIS['add']} زیردسته مکان را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_add_subcategory"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً از گزینه‌های ارائه شده استفاده کنید:")
    
    elif state == "place_add_subcategory":
        if text == f"{EMOJIS['back']} برگشت":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for category in PLACE_CATEGORIES.keys():
                keyboard.row(category)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            
            bot.send_message(user_id, f"{EMOJIS['add']} دسته‌بندی مکان را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_add_category"
        elif text in PLACE_CATEGORIES[user_data[user_id]['category']]:
            user_data[user_id]['subcategory'] = text
            bot.send_message(user_id, f"{EMOJIS['add']} عنوان مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_title"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً از گزینه‌های ارائه شده استفاده کنید:")
    
    elif state == "place_add_title":
        if text == f"{EMOJIS['back']} برگشت":
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for subcategory in PLACE_CATEGORIES[user_data[user_id]['category']]:
                keyboard.row(subcategory)
            keyboard.row(f"{EMOJIS['back']} برگشت")
            
            bot.send_message(user_id, f"{EMOJIS['add']} زیردسته مکان را انتخاب کنید:", reply_markup=keyboard)
            user_states[user_id] = "place_add_subcategory"
        else:
            user_data[user_id]['title'] = text
            bot.send_message(user_id, f"{EMOJIS['add']} توضیحات مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_description"
    
    elif state == "place_add_description":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} عنوان مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_title"
        else:
            user_data[user_id]['description'] = text
            bot.send_message(user_id, f"{EMOJIS['add']} آدرس مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_address"
    
    elif state == "place_add_address":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} توضیحات مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_description"
        else:
            user_data[user_id]['address'] = text
            bot.send_message(user_id, f"{EMOJIS['add']} شماره تماس مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_phone"
    
    elif state == "place_add_phone":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} آدرس مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_address"
        else:
            user_data[user_id]['phone'] = text
            bot.send_message(user_id, f"{EMOJIS['add']} عکس مکان را ارسال کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_photo"
    
    elif state == "place_add_photo":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} شماره تماس مکان را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_phone"
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} لطفاً یک عکس ارسال کنید!")
    
    elif state == "place_add_morning_shift":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} عکس مکان را ارسال کنید:", reply_markup=back_button_only())
            user_states[user_id] = "place_add_photo"
        elif text == "رد کردن":
            user_data[user_id]['morning_shift'] = None
        else:
            user_data[user_id]['morning_shift'] = text
        
        bot.send_message(user_id, f"{EMOJIS['add']} شیفت عصر را وارد کنید (مثال: 16:00-20:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
        user_states[user_id] = "place_add_afternoon_shift"
    
    elif state == "place_add_afternoon_shift":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['add']} شیفت صبح را وارد کنید (مثال: 8:00-12:00 یا 'رد کردن' برای خالی کردن):", reply_markup=skip_button())
            user_states[user_id] = "place_add_morning_shift"
        elif text == "رد کردن":
            user_data[user_id]['afternoon_shift'] = None
        else:
            user_data[user_id]['afternoon_shift'] = text
        
        # ذخیره مکان در پایگاه داده
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO places 
                    (user_id, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (user_id, user_data[user_id]['category'], user_data[user_id]['subcategory'], 
                  user_data[user_id]['title'], user_data[user_id]['description'], user_data[user_id]['address'], 
                  user_data[user_id]['phone'], user_data[user_id].get('photo'), 
                  user_data[user_id].get('morning_shift'), user_data[user_id].get('afternoon_shift')))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"{EMOJIS['success']} مکان با موفقیت ثبت شد!", reply_markup=get_place_menu())
        user_states[user_id] = "place_menu"
    
    elif state == "edit_place_menu":
        if text == f"{EMOJIS['edit']} ویرایش عنوان":
            bot.send_message(user_id, f"{EMOJIS['edit']} عنوان جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_title"
        
        elif text == f"{EMOJIS['edit']} ویرایش توضیحات":
            bot.send_message(user_id, f"{EMOJIS['edit']} توضیحات جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_description"
        
        elif text == f"{EMOJIS['edit']} ویرایش آدرس":
            bot.send_message(user_id, f"{EMOJIS['edit']} آدرس جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_address"
        
        elif text == f"{EMOJIS['edit']} ویرایش تماس":
            bot.send_message(user_id, f"{EMOJIS['edit']} شماره تماس جدید را وارد کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_phone"
        
        elif text == f"{EMOJIS['edit']} ویرایش عکس":
            bot.send_message(user_id, f"{EMOJIS['edit']} عکس جدید را ارسال کنید:", reply_markup=back_button_only())
            user_states[user_id] = "edit_place_photo"
        
        elif text == f"{EMOJIS['edit']} ویرایش شیفت صبح":
            bot.send_message(user_id, f"{EMOJIS['edit']} شیفت صبح جدید را وارد کنید:", reply_markup=skip_button())
            user_states[user_id] = "edit_place_morning_shift"
        
        elif text == f"{EMOJIS['edit']} ویرایش شیفت عصر":
            bot.send_message(user_id, f"{EMOJIS['edit']} شیفت عصر جدید را وارد کنید:", reply_markup=skip_button())
            user_states[user_id] = "edit_place_afternoon_shift"
        
        elif text == f"{EMOJIS['back']} برگشت":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM places WHERE user_id = ? ORDER BY place_id DESC", (user_id,))
            places = c.fetchall()
            conn.close()
            
            if not places:
                bot.send_message(user_id, f"{EMOJIS['error']} شما هیچ مکانی ثبت نکرده‌اید!", reply_markup=get_place_menu())
                user_states[user_id] = "place_menu"
                return
            
            for place in places:
                place_id, user_id_place, category, subcategory, title, description, address, phone, photo, morning_shift, afternoon_shift, rating_sum, rating_count = place
                
                rating_avg = rating_sum / rating_count if rating_count > 0 else 0
                
                place_text = f"""
{EMOJIS['places']} {title}
{EMOJIS['info']} دسته: {category} - {subcategory}
{EMOJIS['document']} توضیحات: {description}
{EMOJIS['link']} آدرس: {address}
{EMOJIS['user']} تماس: {phone}
{EMOJIS['rating']} امتیاز: {rating_avg:.1f} از 10 ({rating_count} رأی)
{EMOJIS['star']} شیفت صبح: {morning_shift if morning_shift else 'تعیین نشده'}
{EMOJIS['star']} شیفت عصر: {afternoon_shift if afternoon_shift else 'تعیین نشده'}
                """
                
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['edit']} ویرایش", callback_data=f"edit_place_{place_id}"))
                keyboard.add(types.InlineKeyboardButton(f"{EMOJIS['delete']} حذف", callback_data=f"delete_place_{place_id}"))
                
                if photo:
                    bot.send_photo(user_id, photo, caption=place_text, reply_markup=keyboard)
                else:
                    bot.send_message(user_id, place_text, reply_markup=keyboard)
            
            bot.send_message(user_id, f"{EMOJIS['success']} مکان‌های شما نمایش داده شدند.", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} بازگشت به صفحه اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    
    elif state == "edit_place_title":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ویرایش", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        else:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET title = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                     (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} عنوان مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_description":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ویرایش", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        else:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET description = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                     (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} توضیحات مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_address":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ویرایش", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        else:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET address = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                     (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} آدرس مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_phone":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ویرایش", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        else:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE places SET phone = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                     (text, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f"{EMOJIS['success']} شماره تماس مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_morning_shift":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ویرایش", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        elif text == "رد کردن":
            new_value = None
        else:
            new_value = text
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET morning_shift = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (new_value, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} شیفت صبح مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    
    elif state == "edit_place_afternoon_shift":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ویرایش", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
            user_states[user_id] = "edit_place_menu"
        elif text == "رد کردن":
            new_value = None
        else:
            new_value = text
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE places SET afternoon_shift = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (new_value, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"{EMOJIS['success']} شیفت عصر مکان به‌روزرسانی شد!", reply_markup=edit_place_menu(user_data[user_id]['edit_place_id']))
        user_states[user_id] = "edit_place_menu"
    
    elif state == "place_rate":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی مکان‌ها", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
        elif not text.isdigit() or not (0 <= int(text) <= 10):
            bot.send_message(user_id, f"{EMOJIS['error']} امتیاز باید بین 0 تا 10 باشد. لطفاً دوباره وارد کنید:")
        else:
            rating = int(text)
            place_id = user_data[user_id]['place_id']
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            # بررسی آیا کاربر قبلاً به این مکان امتیاز داده است
            c.execute("SELECT rating FROM place_ratings WHERE place_id = ? AND user_id = ?", (place_id, user_id))
            existing_rating = c.fetchone()
            
            if existing_rating:
                # به‌روزرسانی امتیاز قبلی
                old_rating = existing_rating[0]
                c.execute("UPDATE place_ratings SET rating = ? WHERE place_id = ? AND user_id = ?", (rating, place_id, user_id))
                c.execute("UPDATE places SET rating_sum = rating_sum - ? + ? WHERE place_id = ?", (old_rating, rating, place_id))
            else:
                # افزودن امتیاز جدید
                c.execute("INSERT INTO place_ratings (place_id, user_id, rating) VALUES (?, ?, ?)", (place_id, user_id, rating))
                c.execute("UPDATE places SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE place_id = ?", (rating, place_id))
            
            conn.commit()
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['success']} امتیاز شما با موفقیت ثبت شد!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
    
    elif state == "admin_menu":
        if text == "👥 کاربران فعال":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            user_count = c.fetchone()[0]
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['user']} تعداد کاربران فعال: {user_count}", reply_markup=admin_menu())
        
        elif text == f"{EMOJIS['news']} ارسال خبر":
            bot.send_message(user_id, f"{EMOJIS['news']} بخش ارسال خبر", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
        
        elif text == "🛡️ مدیر مکان‌ها":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM places")
            place_count = c.fetchone()[0]
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['places']} تعداد مکان‌های ثبت شده: {place_count}", reply_markup=admin_menu())
        
        elif text == "🚫 مسدود کردن کاربر":
            bot.send_message(user_id, f"{EMOJIS['error']} شناسه عددی کاربری که می‌خواهید مسدود کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_block_user"
        
        elif text == "🔓 رفع مسدودیت":
            bot.send_message(user_id, f"{EMOJIS['success']} شناسه عددی کاربری که می‌خواهید رفع مسدودیت کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_unblock_user"
        
        elif text == f"{EMOJIS['score']} امتیاز کاربران":
            bot.send_message(user_id, f"{EMOJIS['score']} بخش مدیریت امتیاز کاربران", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
        
        elif text == f"{EMOJIS['home']} صفحه اصلی":
            bot.send_message(user_id, f"{EMOJIS['home']} بازگشت به صفحه اصلی", reply_markup=main_menu(user_id))
            user_states[user_id] = "main_menu"
    
    elif state == "admin_news_menu":
        if text == f"{EMOJIS['group']} ارسال خبر گروهی":
            bot.send_message(user_id, f"{EMOJIS['news']} خبری که می‌خواهید برای همه کاربران ارسال کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_news_group"
        
        elif text == f"{EMOJIS['user']} ارسال خبر به کاربر":
            bot.send_message(user_id, f"{EMOJIS['news']} شناسه عددی کاربری که می‌خواهید برایش خبر ارسال کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_news_user_id"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    
    elif state == "admin_news_group":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی اخبار", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        else:
            # ذخیره خبر در پایگاه داده
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO news (content) VALUES (?)", (text,))
            conn.commit()
            
            # ارسال خبر به همه کاربران
            c.execute("SELECT user_id FROM users")
            users = c.fetchall()
            conn.close()
            
            success_count = 0
            fail_count = 0
            
            for user in users:
                try:
                    bot.send_message(user[0], f"{EMOJIS['news']} خبر جدید:\n\n{text}")
                    success_count += 1
                except:
                    fail_count += 1
            
            bot.send_message(user_id, f"{EMOJIS['success']} خبر به {success_count} کاربر ارسال شد. {fail_count} ارسال ناموفق بود.", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
    
    elif state == "admin_news_user_id":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی اخبار", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} شناسه عددی باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        else:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            
            if not target_user:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربر با شناسه عددی {numeric_id} یافت نشد!", reply_markup=admin_news_menu())
                user_states[user_id] = "admin_news_menu"
                return
            
            user_data[user_id] = {'news_user_id': target_user[0]}
            bot.send_message(user_id, f"{EMOJIS['news']} خبری که می‌خواهید برای کاربر {target_user[1]} ارسال کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_news_user_content"
    
    elif state == "admin_news_user_content":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی اخبار", reply_markup=admin_news_menu())
            user_states[user_id] = "admin_news_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        else:
            target_user_id = user_data[user_id]['news_user_id']
            
            try:
                bot.send_message(target_user_id, f"{EMOJIS['news']} خبر جدید از ادمین:\n\n{text}")
                bot.send_message(user_id, f"{EMOJIS['success']} خبر با موفقیت ارسال شد!", reply_markup=admin_news_menu())
            except:
                bot.send_message(user_id, f"{EMOJIS['error']} ارسال خبر ناموفق بود. ممکن است کاربر ربات را مسدود کرده باشد.", reply_markup=admin_news_menu())
            
            user_states[user_id] = "admin_news_menu"
    
    elif state == "admin_block_user":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} شناسه عددی باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        else:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            
            if not target_user:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربر با شناسه عددی {numeric_id} یافت نشد!", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
                return
            
            block_user(target_user[0])
            bot.send_message(user_id, f"{EMOJIS['success']} کاربر {target_user[1]} با شناسه عددی {numeric_id} مسدود شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    
    elif state == "admin_unblock_user":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} شناسه عددی باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        else:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            
            if not target_user:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربر با شناسه عددی {numeric_id} یافت نشد!", reply_markup=admin_menu())
                user_states[user_id] = "admin_menu"
                return
            
            unblock_user(target_user[0])
            bot.send_message(user_id, f"{EMOJIS['success']} کاربر {target_user[1]} با شناسه عددی {numeric_id} رفع مسدودیت شد!", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    
    elif state == "admin_score_menu":
        if text == f"{EMOJIS['add_score']} اضافه کردن امتیاز":
            bot.send_message(user_id, f"{EMOJIS['add_score']} شناسه عددی کاربری که می‌خواهید به آن امتیاز اضافه کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_add_score_id"
        
        elif text == f"{EMOJIS['remove_score']} کم کردن امتیاز":
            bot.send_message(user_id, f"{EMOJIS['remove_score']} شناسه عددی کاربری که می‌خواهید از آن امتیاز کم کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_remove_score_id"
        
        elif text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
    
    elif state == "admin_add_score_id":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی امتیاز", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} شناسه عددی باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        else:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            
            if not target_user:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربر با شناسه عددی {numeric_id} یافت نشد!", reply_markup=admin_score_menu())
                user_states[user_id] = "admin_score_menu"
                return
            
            user_data[user_id] = {'score_user_id': target_user[0], 'score_user_name': target_user[1]}
            bot.send_message(user_id, f"{EMOJIS['add_score']} تعداد امتیازی که می‌خواهید به کاربر {target_user[1]} اضافه کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_add_score_amount"
    
    elif state == "admin_add_score_amount":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی امتیاز", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} تعداد امتیاز باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        else:
            amount = int(text)
            target_user_id = user_data[user_id]['score_user_id']
            target_user_name = user_data[user_id]['score_user_name']
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (amount, target_user_id))
            conn.commit()
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['success']} {amount} امتیاز به کاربر {target_user_name} اضافه شد!", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
    
    elif state == "admin_remove_score_id":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی امتیاز", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} شناسه عددی باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        else:
            numeric_id = int(text)
            target_user = get_user_by_numeric_id(numeric_id)
            
            if not target_user:
                bot.send_message(user_id, f"{EMOJIS['error']} کاربر با شناسه عددی {numeric_id} یافت نشد!", reply_markup=admin_score_menu())
                user_states[user_id] = "admin_score_menu"
                return
            
            user_data[user_id] = {'score_user_id': target_user[0], 'score_user_name': target_user[1]}
            bot.send_message(user_id, f"{EMOJIS['remove_score']} تعداد امتیازی که می‌خواهید از کاربر {target_user[1]} کم کنید را وارد کنید:", reply_markup=admin_sub_menu())
            user_states[user_id] = "admin_remove_score_amount"
    
    elif state == "admin_remove_score_amount":
        if text == f"{EMOJIS['back']} برگشت":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی امتیاز", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
        elif text == "برگشت به ادمین":
            bot.send_message(user_id, f"{EMOJIS['success']} بازگشت به منوی ادمین", reply_markup=admin_menu())
            user_states[user_id] = "admin_menu"
        elif not text.isdigit():
            bot.send_message(user_id, f"{EMOJIS['error']} تعداد امتیاز باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        else:
            amount = int(text)
            target_user_id = user_data[user_id]['score_user_id']
            target_user_name = user_data[user_id]['score_user_name']
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET score = score - ? WHERE user_id = ?", (amount, target_user_id))
            conn.commit()
            conn.close()
            
            bot.send_message(user_id, f"{EMOJIS['success']} {amount} امتیاز از کاربر {target_user_name} کم شد!", reply_markup=admin_score_menu())
            user_states[user_id] = "admin_score_menu"
    
    else:
        # اگر کاربر در هیچ حالتی نبود، به منوی اصلی هدایت شود
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
        c.execute("UPDATE places SET photo = ? WHERE place_id = ? AND (user_id = ? OR ? = ?)", 
                 (photo_id, user_data[user_id]['edit_place_id'], user_id, user_id, ADMIN_ID))
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
    
    elif data.startswith("delete_place_"):
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
    
    elif data.startswith("edit_place_"):
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
        else:
            bot.send_message(user_id, f"{EMOJIS['error']} شما مجاز به ویرایش این مکان نیستید!", reply_markup=get_place_menu())
            user_states[user_id] = "place_menu"
    
    elif data.startswith("rate_place_"):
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