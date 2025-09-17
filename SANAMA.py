import os
import uuid
import random
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2'
app.config['PORT'] = 5000
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# دسته‌بندی‌ها
CATEGORIES = {
    "🍽️ خوراکی و نوشیدنی": [
        "رستوران‌ها (سنتی، فست‌فود، بین‌المللی، دریایی، گیاهخواری)",
        "کافه و کافی‌شاپ (کافه‌رستوران، قهوه تخصصی)",
        "بستنی‌فروشی و آبمیوه‌فروشی (بستنی سنتی، بستنی ایتالیایی)",
        "شیرینی‌پزی و نانوایی (نانوایی سنتی، قنادی)",
        "سفره‌خانه و چایخانه (قهوه‌خانه سنتی، چایخانه مدرن)",
        "فودکورت و مراکز غذاخوری",
        "کبابی و جگرکی (کباب‌فروشی، جگرکی، دیزی‌سرا)",
        "ساندویچ‌فروشی و پیتزافروشی",
        "قنادی و شکلات‌فروشی",
        "آجیل‌فروشی و خشکبار",
        "سوپرمارکت محلی و هایپر",
        "قصابی و مرغ‌فروشی",
        "میوه‌فروشی و تره‌بار",
        "ماهی‌فروشی و غذاهای دریایی",
        "فروشگاه مواد غذایی محلی",
        "عسل‌فروشی و محصولات زنبورداری",
        "محصولات محلی و منطقه‌ای",
        "فروشگاه محصولات ارگانیک",
        "فروشگاه مواد غذایی منجمد",
        "فروشگاه محصولات لبنی و پنیر",
        "نان‌فروشی تخصصی (نان باگت، نان سنگک)",
        "غذاهای محلی و قومی"
    ],
    "🛍️ خرید و فروش": [
        "پاساژها و مراکز خرید (مال، مرکز خرید، بازارچه)",
        "سوپرمارکت و هایپرمارکت",
        "فروشگاه زنجیره‌ای",
        "بازار سنتی و بازارچه‌های محلی",
        "فروشگاه پوشاک و کیف و کفش",
        "فروشگاه لوازم خانگی و الکترونیک",
        "فروشگاه لوازم ورزشی",
        "کتاب‌فروشی و لوازم‌التحریر",
        "مغازه موبایل و لپ‌تاپ (فروش، تعمیر، لوازم جانبی)",
        "گل‌فروشی و گیاهان آپارتمانی",
        "عینک‌فروشی و اپتیک",
        "عطر و ادکلن‌فروشی",
        "طلا و جواهرفروشی",
        "ساعت‌فروشی",
        "لوازم آرایشی و بهداشتی",
        "اسباب‌بازی‌فروشی",
        "صنایع‌دستی و سوغاتی‌فروشی",
        "دکوراسیون و لوازم منزل",
        "فرش و گلیم‌فروشی",
        "پارچه‌فروشی و خیاطی",
        "چرم‌فروشی و کیف‌سازی",
        "فروشگاه لوازم آشپزخانه",
        "فروشگاه لوازم باغبانی",
        "فروشگاه حیوانات خانگی",
        "فروشگاه دوچرخه و اسکوتر",
        "فروشگاه ابزارآلات",
        "فروشگاه کامپیوتر و گیم",
        "فروشگاه لباس عروس و مراسم",
        "فروشگاه کادو و هدیه",
        "فروشگاه محصولات فرهنگی",
        "فروشگاه محصولات دست‌دوم",
        "فروشگاه محصولات سلامت و تندرستی",
        "فروشگاه محصولات روستایی و محلی"
    ],
    "✂️ زیبایی و آرایشی": [
        "آرایشگاه مردانه",
        "آرایشگاه زنانه",
        "سالن‌های زیبایی و اسپا",
        "مژه و ابرو (اکستنشن، میکروبلیدینگ)",
        "ناخن‌کاری (مانیکور، پدیکور)",
        "تتو و میکروپیگمنتیشن",
        "مراکز خدمات پوست و مو",
        "فروشگاه لوازم آرایشی حرفه‌ای",
        "مراکز ماساژ و ریلکسیشن",
        "مراکز اپیلاسیون و لیزر",
        "سالن‌های برنزه کردن",
        "مراکز مشاوره زیبایی",
        "آموزشگاه‌های آرایشگری",
        "مراکز خدمات بهداشتی مردانه"
    ],
    "🏥 درمان و سلامت": [
        "بیمارستان و مراکز درمانی",
        "درمانگاه و کلینیک‌های تخصصی",
        "داروخانه (شبانه‌روزی، گیاهی)",
        "دندان‌پزشکی و ارتودنسی",
        "آزمایشگاه پزشکی و رادیولوژی",
        "کلینیک زیبایی و لیزر",
        "مراکز فیزیوتراپی و کاردرمانی",
        "دامپزشکی و کلینیک حیوانات",
        "مراکز توانبخشی",
        "مراکز مشاوره و روانشناسی",
        "شنوایی‌سنجی و سمعک",
        "بینایی‌سنجی و عینک‌سازی",
        "پرستاری در منزل",
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
        "باشگاه ورزشی و بدنسازی",
        "استخر و مجموعه ورزشی",
        "سالن فوتسال و بسکتبال",
        "سینما و تئاتر",
        "شهربازی و پارک بازی",
        "بیلیارد و بولینگ",
        "مراکز تفریحی خانوادگی",
        "مراکز فرهنگی و هنری",
        "سالن‌های کنسرت و نمایش",
        "گیم‌نت و مراکز بازی",
        "باشگاه تیراندازی",
        "مراکز آموزشی موسیقی",
        "کتابخانه عمومی",
        "نگارخانه و نمایشگاه هنری",
        "مراکز بازی اتاق فرار",
        "مراکز پینت‌بال و لیزرتگ",
        "باشگاه‌های رقص و باله",
        "مراکز یوگا و مدیتیشن",
        "باشگاه‌های ورزش‌های رزمی",
        "مراکز اسکیت و رولر",
        "باشگاه‌های بوکس",
        "مراکز ورزش‌های آبی",
        "باشگاه‌های گلف و تنیس",
        "مراکز ماهیگیری و شکار",
        "باشگاه‌های سوارکاری"
    ],
    "🏨 اقامت و سفر": [
        "هتل و هتل آپارتمان",
        "مسافرخانه و مهمانپذیر",
        "اقامتگاه بوم‌گردی",
        "ویلا و سوئیت اجاره‌ای",
        "کمپینگ و اردوگاه",
        "آژانس مسافرتی و گردشگری",
        "ایستگاه قطار و اتوبوس",
        "فرودگاه و پایانه مسافری",
        "مراکز رزرواسیون",
        "خدمات ویزا و پاسپورت",
        "اجاره خودرو و دوچرخه",
        "راهنمایان گردشگری",
        "مراکز اطلاعات گردشگری",
        "خدمات ترجمه و راهنمای محلی",
        "مراکز کرایه اتومبیل",
        "خدمات انتقال مسافر",
        "مراکز رزرواسیون آنلاین",
        "خدمات بیمه مسافرتی",
        "مراکز خدمات جهانگردی"
    ],
    "🏛️ خدمات عمومی و اداری": [
        "بانک و خودپرداز",
        "اداره پست",
        "دفاتر پیشخوان خدمات دولت",
        "شهرداری و مراکز خدمات شهری",
        "اداره برق، آب، گاز",
        "پلیس +۱۰ و مراکز انتظامی",
        "دادگاه و مراجع قضایی",
        "کلانتری و پاسگاه",
        "دفاتر اسناد رسمی",
        "مراکز صدور گواهینامه",
        "ادارات دولتی و وزارتخانه‌ها",
        "کنسولگری و سفارتخانه‌ها",
        "مراکز خدمات الکترونیک",
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
        "پمپ بنزین و CNG",
        "کارواش و خدمات خودرو",
        "تعمیرگاه خودرو و موتورسیکلت",
        "تاکسی‌سرویس و تاکسی اینترنتی",
        "پارکینگ عمومی",
        "مکانیکی و برق خودرو",
        "لاستیک‌فروشی و لوازم یدکی",
        "خدمات نقاشی و ترمیم خودرو",
        "مراکز معاینه فنی",
        "خدمات امداد خودرو",
        "نمایندگی خودرو",
        "فروشگاه لوازم جانبی خودرو",
        "خدمات تنظیم موتور و انژکتور",
        "خدمات صافکاری و جلوبندی",
        "خدمات تعویض روغن و فیلتر",
        "خدمات سیستم تهویه و کولر",
        "خدمات تعمیرات تخصصی خودرو",
        "خدمات کارت‌خوان و پرداخت",
        "خدمات پخش محصولات خودرویی",
        "خدمات حمل‌ونقل معلولین و سالمندان"
    ],
    "📚 آموزش و فرهنگ": [
        "مدرسه و آموزشگاه",
        "دانشگاه و مراکز آموزش عالی",
        "آموزشگاه زبان",
        "آموزشگاه فنی‌وحرفه‌ای",
        "کتابخانه عمومی",
        "فرهنگسرا و خانه فرهنگ",
        "موزه و گالری",
        "مراکز آموزشی کامپیوتر",
        "مراکز مشاوره تحصیلی",
        "آموزشگاه‌های هنری",
        "مراکز آموزشی رانندگی",
        "مهدکودک و پیش‌دبستانی",
        "مراکز آموزش علوم مختلف",
        "مراکز آموزش مهارت‌های زندگی",
        "آموزشگاه‌های آشپزی و شیرینی‌پزی",
        "مراکز آموزش خلاقیت کودکان",
        "آموزشگاه‌های کنکور و آزمون",
        "مراکز آموزش از راه دور",
        "آموزشگاه‌های مهارت‌آموزی",
        "مراکز آموزش صنایع‌دستی",
        "آموزشگاه‌های خیاطی و طراحی لباس",
        "مراکز آموزش عکاسی و فیلمبرداری",
        "آموزشگاه‌های ورزشی تخصصی",
        "مراکز آموزش موسیقی محلی",
        "آموزشگاه‌های زبان اشاره",
        "خدمات آموزش مجازی و آنلاین"
    ],
    "🕌 مذهبی و معنوی": [
        "مسجد و مصلی",
        "حسینیه و هیئت",
        "کلیسا و مراکز مسیحی",
        "کنیسه و مراکز یهودی",
        "معابد و پرستشگاه‌ها",
        "مراکز عرفانی و معنوی",
        "کتابفروشی‌های مذهبی",
        "مراکز خیریه و نیکوکاری",
        "انتشارات مذهبی",
        "مراکز حفظ قرآن و معارف اسلامی",
        "مراکز خدمات حج و زیارت",
        "مراکز مشاوره مذهبی و دینی",
        "مراکز آموزش احکام و معارف",
        "مراکز خدمات اوقاف و امور خیریه",
        "مراکز خدمات مذهبی سیار",
        "مراکز برگزاری مراسم مذهبی"
    ],
    "🌳 طبیعت و تفریح آزاد": [
        "پارک و بوستان",
        "باغ وحش و آکواریوم",
        "باغ گیاه‌شناسی",
        "پیست دوچرخه‌سواری",
        "کوهستان و مسیرهای طبیعت‌گردی",
        "ساحل و دریاچه",
        "آبشار و چشمه",
        "جنگل و منطقه حفاظت‌شده",
        "کمپینگ و پیکنیک",
        "مراکز اکوتوریسم",
        "پیست اسکی و ورزش‌های زمستانی",
        "سالن‌های بولدرینگ و صخره‌نوردی",
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
        "دفتر کار و شرکت‌ها",
        "کارخانه‌ها و واحدهای تولیدی",
        "کارگاه‌های صنعتی",
        "دفاتر املاک و مشاورین املاک",
        "دفاتر بیمه",
        "شرکت‌های تبلیغاتی و بازاریابی",
        "مراکز طراحی و چاپ",
        "شرکت‌های معماری و عمران",
        "دفاتر حقوقی و وکالت",
        "شرکت‌های مشاوره مدیریت",
        "مراکز خدمات مالی و حسابداری",
        "شرکت‌های فناوری اطلاعات",
        "استودیوهای عکاسی و فیلمبرداری",
        "مراکز خدمات اداری و کپی",
        "شرکت‌های حمل‌ونقل و باربری",
        "خدمات نظافتی و نگهداری",
        "شرکت‌های رسانه‌ای و انتشاراتی",
        "مراکز تحقیقاتی و توسعه",
        "شرکت‌های مشاوره منابع انسانی",
        "مراکز خدمات مشاوره کسب‌وکار",
        "شرکت‌های طراحی سایت و بهینه‌سازی موتور جستجو",
        "مراکز خدمات ترجمه و مترجم",
        "شرکت‌های خدمات امنیتی",
        "مراکز خدمات پشتیبانی فناوری اطلاعات",
        "شرکت‌های خدمات مشاوره مالیاتی",
        "مراکز خدمات برندینگ و هویت‌سازی",
        "خدمات مشاوره انرژی و بهینه‌سازی"
    ],
    "🧰 خدمات تخصصی و فنی": [
        "تعمیرگاه لوازم خانگی",
        "تعمیرگاه موبایل و کامپیوتر",
        "خدمات برق ساختمان",
        "خدمات لوله‌کشی و تاسیسات",
        "خدمات نقاشی ساختمان",
        "خدمات کابینت‌سازی و نجاری",
        "خدمات آهنگری و جوشکاری",
        "خدمات کلیدسازی و قفل‌سازی",
        "خدمات شیشه‌بری و آینه‌کاری",
        "خدمات فرش‌شویی و مبل‌شویی",
        "خدمات نظافت منزل و اداره",
        "خدمات باغبانی و فضای سبز",
        "خدمات حشره‌کشی و ضدعفونی",
        "خدمات امنیتی و نگهبانی",
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
        "خدمات اجاره تجهیزات و لوازم"
    ]
}

# مناطق شیراز
REGIONS = {
    "شهر شیراز": [
        "معالی‌آباد", "زرهی", "فرهنگ‌شهر", "قدوسی", "قصردشت", "ملاصدرا", "چمران", 
        "عفیف‌آباد", "ستارخان", "ارم", "اطلسي", "زرگری", "تاجارا", "گلستان", 
        "شهرک گلستان", "شهرک صدرا (فاز 1)", "شهرک صدرا (فاز 2)"
    ],
    "محله‌های جنوبی": [
        "شهرک‌های صنعتی", "شهرک رکن‌آباد", "شهرک والفجر", "شهرک بزين", 
        "شهرک میانرود", "شهرک دستغیب"
    ],
    "محله‌های شرقی": [
        "بلوار نیایش", "بلوار مدرس", "شهرک سعدی", "شهرک آرین", "شهرک جوادالائمه"
    ],
    "محله‌های غربی": [
        "شهرک استقلال", "شهرک بهشتی", "شهرک مطهری", "شهرک پرواز"
    ],
    "محله‌های شمالی": [
        "شهرک‌های قصر قمشه", "شهرک کوشک میدان", "شهرک آرین"
    ],
    "شهرک‌ها و مناطق اطراف شیراز": [
        "صدرا (فاز 1)", "صدرا (فاز 2)", "شهرک صنعتی بزرگ شیراز", 
        "شهرک صنعتی آب‌باریک", "شهرک صنعتی لپویی", "شهرک صنعتی دستغیب", 
        "شهرک صنعتی زرقان", "شهرک گویم"
    ],
    "روستاهای اطراف شیراز": [
        "روستای قلات", "روستای بیدزرد", "روستای خیرآباد", "روستای دودمان", 
        "روستای کوشک بیدک", "روستای سلطان‌آباد", "روستای گردخون", 
        "روستای دوکوهک", "روستای سیاخ دارنگون", "روستای تنگ سرخ", 
        "روستای کودیان", "روستای جره", "روستای باجگاه", "روستای اکبرآباد"
    ]
}

# Initialize database
def init_db():
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT UNIQUE,
                  name TEXT,
                  age INTEGER,
                  gender TEXT,
                  score INTEGER DEFAULT 0,
                  is_admin INTEGER DEFAULT 0,
                  is_blocked INTEGER DEFAULT 0,
                  free_places INTEGER DEFAULT 2,
                  subscription_date TEXT,
                  region TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create places table
    c.execute('''CREATE TABLE IF NOT EXISTS places
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  place_id TEXT UNIQUE,
                  user_id TEXT,
                  category TEXT,
                  subcategory TEXT,
                  title TEXT,
                  description TEXT,
                  address TEXT,
                  phone TEXT,
                  images TEXT,
                  morning_shift TEXT,
                  evening_shift TEXT,
                  total_score INTEGER DEFAULT 0,
                  vote_count INTEGER DEFAULT 0,
                  average_score REAL DEFAULT 0,
                  is_top_place INTEGER DEFAULT 0,
                  region TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Create votes table
    c.execute('''CREATE TABLE IF NOT EXISTS votes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  place_id TEXT,
                  user_id TEXT,
                  score INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (place_id) REFERENCES places (place_id),
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Create comments table
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  place_id TEXT,
                  user_id TEXT,
                  comment TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (place_id) REFERENCES places (place_id),
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Create messages table
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender_id TEXT,
                  receiver_id TEXT,
                  message TEXT,
                  message_type TEXT DEFAULT 'text',
                  is_read INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (sender_id) REFERENCES users (user_id),
                  FOREIGN KEY (receiver_id) REFERENCES users (user_id))''')
    
    # Create news table
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  content TEXT,
                  is_global INTEGER DEFAULT 1,
                  target_user_id TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (target_user_id) REFERENCES users (user_id))''')
    
    # Create notifications table
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  content TEXT,
                  is_read INTEGER DEFAULT 0,
                  related_place_id TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id),
                  FOREIGN KEY (related_place_id) REFERENCES places (place_id))''')
    
    # Create blocks table
    c.execute('''CREATE TABLE IF NOT EXISTS blocks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  blocker_id TEXT,
                  blocked_id TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (blocker_id) REFERENCES users (user_id),
                  FOREIGN KEY (blocked_id) REFERENCES users (user_id))''')
    
    # Create reports table
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  reporter_id TEXT,
                  content TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (reporter_id) REFERENCES users (user_id))''')
    
    # Create top_place_requests table
    c.execute('''CREATE TABLE IF NOT EXISTS top_place_requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  place_id TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id),
                  FOREIGN KEY (place_id) REFERENCES places (place_id))''')
    
    conn.commit()
    conn.close()

# Helper functions
def generate_user_id():
    return str(random.randint(100000000, 999999999))

def generate_place_id():
    return str(uuid.uuid4())[:8]

def get_db_connection():
    conn = sqlite3.connect('goimnama.db')
    conn.row_factory = sqlite3.Row
    return conn

def is_logged_in():
    return 'user_id' in session

def is_admin():
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT is_admin FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
        conn.close()
        return user and user['is_admin'] == 1
    return False

def get_user_info(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def get_place_info(place_id):
    conn = get_db_connection()
    place = conn.execute('SELECT * FROM places WHERE place_id = ?', (place_id,)).fetchone()
    conn.close()
    return place

def add_notification(user_id, content, place_id=None):
    conn = get_db_connection()
    conn.execute('INSERT INTO notifications (user_id, content, related_place_id) VALUES (?, ?, ?)',
                 (user_id, content, place_id))
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('لطفاً ابتدا وارد حساب کاربری خود شوید', 'warning')
            return redirect(url_for('welcome'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('لطفاً ابتدا وارد حساب کاربری خود شوید', 'warning')
            return redirect(url_for('welcome'))
        if not is_admin():
            flash('شما دسترسی ادمین ندارید', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def welcome():
    if is_logged_in():
        return redirect(url_for('index'))
    return render_template('welcome.html')

@app.route('/accept_rules', methods=['POST'])
def accept_rules():
    session['rules_accepted'] = True
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if not session.get('rules_accepted'):
        return redirect(url_for('welcome'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        region = request.form.get('region')
        
        if not name or not age or not gender or not region:
            flash('لطفاً تمام فیلدها را پر کنید', 'danger')
            return render_template('register.html', regions=REGIONS)
        
        try:
            age = int(age)
            if age < 13 or age > 70:
                flash('سن باید بین 13 تا 70 سال باشد', 'danger')
                return render_template('register.html', regions=REGIONS)
        except ValueError:
            flash('سن باید یک عدد باشد', 'danger')
            return render_template('register.html', regions=REGIONS)
        
        user_id = generate_user_id()
        session['user_id'] = user_id
        
        conn = get_db_connection()
        conn.execute('INSERT INTO users (user_id, name, age, gender, region) VALUES (?, ?, ?, ?, ?)',
                     (user_id, name, age, gender, region))
        conn.commit()
        conn.close()
        
        flash('ثبت‌نام با موفقیت انجام شد', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html', regions=REGIONS)

@app.route('/index')
@login_required
def index():
    conn = get_db_connection()
    
    # Get top places
    top_places = conn.execute('''
        SELECT * FROM places 
        WHERE is_top_place = 1 
        ORDER BY created_at DESC 
        LIMIT 10
    ''').fetchall()
    
    # Get recent places
    recent_places = conn.execute('''
        SELECT * FROM places 
        ORDER BY created_at DESC 
        LIMIT 20
    ''').fetchall()
    
    # Get user info
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    # Get unread notifications count
    notification_count = conn.execute('''
        SELECT COUNT(*) as count FROM notifications 
        WHERE user_id = ? AND is_read = 0
    ''', (session['user_id'],)).fetchone()['count']
    
    conn.close()
    
    return render_template('index.html', 
                         top_places=top_places, 
                         recent_places=recent_places,
                         user=user,
                         notification_count=notification_count,
                         categories=CATEGORIES,
                         regions=REGIONS)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    region = request.args.get('region', '')
    
    conn = get_db_connection()
    
    # Build search query
    sql = 'SELECT * FROM places WHERE 1=1'
    params = []
    
    if query:
        sql += ' AND (title LIKE ? OR address LIKE ? OR description LIKE ?)'
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
    
    if category:
        sql += ' AND category = ?'
        params.append(category)
    
    if region:
        sql += ' AND region = ?'
        params.append(region)
    
    sql += ' ORDER BY created_at DESC'
    
    places = conn.execute(sql, params).fetchall()
    conn.close()
    
    return render_template('search.html', 
                         places=places, 
                         query=query,
                         category=category,
                         region=region,
                         categories=CATEGORIES,
                         regions=REGIONS)

@app.route('/place/<place_id>')
@login_required
def place_detail(place_id):
    conn = get_db_connection()
    
    # Get place details
    place = conn.execute('SELECT * FROM places WHERE place_id = ?', (place_id,)).fetchone()
    
    if not place:
        flash('مکان مورد نظر یافت نشد', 'danger')
        return redirect(url_for('index'))
    
    # Get user vote for this place
    user_vote = conn.execute('SELECT * FROM votes WHERE place_id = ? AND user_id = ?', 
                            (place_id, session['user_id'])).fetchone()
    
    # Get comments for this place
    comments = conn.execute('''
        SELECT c.*, u.name, u.age, u.gender, u.user_id as commenter_id 
        FROM comments c 
        JOIN users u ON c.user_id = u.user_id 
        WHERE c.place_id = ? 
        ORDER BY c.created_at DESC
    ''', (place_id,)).fetchall()
    
    # Check if user is blocked by place owner
    is_blocked = conn.execute('''
        SELECT * FROM blocks 
        WHERE blocker_id = ? AND blocked_id = ?
    ''', (place['user_id'], session['user_id'])).fetchone()
    
    conn.close()
    
    return render_template('place_detail.html', 
                         place=place, 
                         user_vote=user_vote,
                         comments=comments,
                         is_blocked=is_blocked)

@app.route('/vote/<place_id>', methods=['POST'])
@login_required
def vote(place_id):
    score = request.form.get('score')
    
    try:
        score = int(score)
        if score < 0 or score > 10:
            flash('امتیاز باید بین 0 تا 10 باشد', 'danger')
            return redirect(url_for('place_detail', place_id=place_id))
    except (ValueError, TypeError):
        flash('امتیاز نامعتبر است', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))
    
    conn = get_db_connection()
    
    # Check if user already voted
    existing_vote = conn.execute('SELECT * FROM votes WHERE place_id = ? AND user_id = ?', 
                                (place_id, session['user_id'])).fetchone()
    
    if existing_vote:
        flash('شما قبلاً به این مکان امتیاز داده‌اید', 'warning')
        return redirect(url_for('place_detail', place_id=place_id))
    
    # Add vote
    conn.execute('INSERT INTO votes (place_id, user_id, score) VALUES (?, ?, ?)',
                 (place_id, session['user_id'], score))
    
    # Update place score
    place = conn.execute('SELECT * FROM places WHERE place_id = ?', (place_id,)).fetchone()
    new_total_score = place['total_score'] + score
    new_vote_count = place['vote_count'] + 1
    new_average_score = new_total_score / new_vote_count
    
    conn.execute('''
        UPDATE places 
        SET total_score = ?, vote_count = ?, average_score = ? 
        WHERE place_id = ?
    ''', (new_total_score, new_vote_count, new_average_score, place_id))
    
    # Check if place becomes top place
    if new_vote_count >= 100 and new_average_score >= 8 and not place['is_top_place']:
        conn.execute('UPDATE places SET is_top_place = 1 WHERE place_id = ?', (place_id,))
        add_notification(place['user_id'], f'مکان شما با نام "{place["title"]}" وارد بخش مکان‌های برتر شد، به شما تبریک می‌گویم', place_id)
    
    # Check if place loses top place status
    elif place['is_top_place'] and (new_vote_count < 100 or new_average_score < 8):
        conn.execute('UPDATE places SET is_top_place = 0 WHERE place_id = ?', (place_id,))
        add_notification(place['user_id'], f'دیگر مکان شما "{place["title"]}" در مکان‌های برتر نیست', place_id)
    
    conn.commit()
    conn.close()
    
    flash('امتیاز شما با موفقیت ثبت شد', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

@app.route('/add_comment/<place_id>', methods=['POST'])
@login_required
def add_comment(place_id):
    comment = request.form.get('comment')
    
    if not comment or len(comment.strip()) < 5:
        flash('نظر باید حداقل 5 کاراکتر داشته باشد', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))
    
    conn = get_db_connection()
    
    # Get place info
    place = conn.execute('SELECT * FROM places WHERE place_id = ?', (place_id,)).fetchone()
    
    # Add comment
    conn.execute('INSERT INTO comments (place_id, user_id, comment) VALUES (?, ?, ?)',
                 (place_id, session['user_id'], comment))
    
    # Notify place owner
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    add_notification(place['user_id'], 
                    f'کاربر {user["name"]} ({user["age"]} ساله، {user["gender"]}) این نظر را برای مکان "{place["title"]}" داده است: {comment}', 
                    place_id)
    
    conn.commit()
    conn.close()
    
    flash('نظر شما با موفقیت ثبت شد', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

@app.route('/delete_comment/<comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    conn = get_db_connection()
    
    # Get comment info
    comment = conn.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    
    if not comment:
        flash('نظر مورد نظر یافت نشد', 'danger')
        return redirect(url_for('index'))
    
    # Check if user is comment owner or admin
    user = get_user_info(session['user_id'])
    if comment['user_id'] != session['user_id'] and not user['is_admin']:
        flash('شما اجازه حذف این نظر را ندارید', 'danger')
        return redirect(url_for('place_detail', place_id=comment['place_id']))
    
    # Delete comment
    conn.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    
    # Notify comment owner if deleted by admin
    if user['is_admin'] and comment['user_id'] != session['user_id']:
        place = conn.execute('SELECT * FROM places WHERE place_id = ?', (comment['place_id'],)).fetchone()
        add_notification(comment['user_id'], 
                        f'نظر شما در نظرات مکان "{place["title"]}" توسط ادمین به دلیل نقض قوانین حذف شد')
    
    conn.commit()
    conn.close()
    
    flash('نظر با موفقیت حذف شد', 'success')
    return redirect(url_for('place_detail', place_id=comment['place_id']))

@app.route('/send_message/<place_id>', methods=['POST'])
@login_required
def send_message(place_id):
    message = request.form.get('message')
    
    if not message or len(message.strip()) < 5:
        flash('پیام باید حداقل 5 کاراکتر داشته باشد', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))
    
    conn = get_db_connection()
    
    # Get place info
    place = conn.execute('SELECT * FROM places WHERE place_id = ?', (place_id,)).fetchone()
    
    # Check if user is blocked by place owner
    is_blocked = conn.execute('''
        SELECT * FROM blocks 
        WHERE blocker_id = ? AND blocked_id = ?
    ''', (place['user_id'], session['user_id'])).fetchone()
    
    if is_blocked:
        flash('شما توسط صاحب این مکان مسدود شده‌اید', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))
    
    # Send message
    conn.execute('INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)',
                 (session['user_id'], place['user_id'], message))
    
    conn.commit()
    conn.close()
    
    flash('پیام شما با موفقیت ارسال شد', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

@app.route('/messages')
@login_required
def messages():
    conn = get_db_connection()
    
    # Get user messages
    user_messages = conn.execute('''
        SELECT m.*, u.name as sender_name 
        FROM messages m 
        JOIN users u ON m.sender_id = u.user_id 
        WHERE m.receiver_id = ? 
        ORDER BY m.created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('messages.html', messages=user_messages)

@app.route('/reply_message/<message_id>', methods=['POST'])
@login_required
def reply_message(message_id):
    reply = request.form.get('reply')
    
    if not reply or len(reply.strip()) < 5:
        flash('پیام باید حداقل 5 کاراکتر داشته باشد', 'danger')
        return redirect(url_for('messages'))
    
    conn = get_db_connection()
    
    # Get original message
    original_message = conn.execute('SELECT * FROM messages WHERE id = ?', (message_id,)).fetchone()
    
    if not original_message:
        flash('پیام مورد نظر یافت نشد', 'danger')
        return redirect(url_for('messages'))
    
    # Send reply
    conn.execute('INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)',
                 (session['user_id'], original_message['sender_id'], reply))
    
    conn.commit()
    conn.close()
    
    flash('پاسخ شما با موفقیت ارسال شد', 'success')
    return redirect(url_for('messages'))

@app.route('/block_user/<user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    conn = get_db_connection()
    
    # Check if already blocked
    existing_block = conn.execute('''
        SELECT * FROM blocks 
        WHERE blocker_id = ? AND blocked_id = ?
    ''', (session['user_id'], user_id)).fetchone()
    
    if existing_block:
        flash('این کاربر قبلاً مسدود شده است', 'warning')
        return redirect(url_for('messages'))
    
    # Block user
    conn.execute('INSERT INTO blocks (blocker_id, blocked_id) VALUES (?, ?)',
                 (session['user_id'], user_id))
    
    # Notify blocked user
    blocker = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    add_notification(user_id, f'شما توسط کاربر {blocker["name"]} مسدود شده‌اید')
    
    conn.commit()
    conn.close()
    
    flash('کاربر با موفقیت مسدود شد', 'success')
    return redirect(url_for('messages'))

@app.route('/unblock_user/<user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    conn = get_db_connection()
    
    # Unblock user
    conn.execute('DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?',
                 (session['user_id'], user_id))
    
    # Notify unblocked user
    unblocker = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    add_notification(user_id, f'شما توسط کاربر {unblocker["name"]} رفع مسدودیت شده‌اید')
    
    conn.commit()
    conn.close()
    
    flash('کاربر با موفقیت رفع مسدودیت شد', 'success')
    return redirect(url_for('messages'))

@app.route('/add_place', methods=['GET', 'POST'])
@login_required
def add_place():
    user = get_user_info(session['user_id'])
    
    # Check if user has free places left
    if user['free_places'] <= 0 and not user['is_admin']:
        flash('شما هیچ مکان رایگان دیگری ندارید. لطفاً برای افزودن مکان جدید اشتراک خریداری کنید.', 'warning')
        return redirect(url_for('payment'))
    
    if request.method == 'POST':
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        title = request.form.get('title')
        description = request.form.get('description')
        address = request.form.get('address')
        phone = request.form.get('phone')
        morning_shift = request.form.get('morning_shift')
        evening_shift = request.form.get('evening_shift')
        region = request.form.get('region')
        
        # Validate required fields
        if not category or not subcategory or not title or not description or not address or not region:
            flash('لطفاً تمام فیلدهای ضروری را پر کنید', 'danger')
            return render_template('add_place.html', categories=CATEGORIES, regions=REGIONS)
        
        # Validate description length
        if len(description.split()) < 10:
            flash('توضیحات باید حداقل 10 کلمه باشد', 'danger')
            return render_template('add_place.html', categories=CATEGORIES, regions=REGIONS)
        
        # Validate phone if provided
        if phone and (not phone.startswith('09') or len(phone) != 11 or not phone.isdigit()):
            flash('شماره تماس باید 11 رقمی و با 09 شروع شود', 'danger')
            return render_template('add_place.html', categories=CATEGORIES, regions=REGIONS)
        
        # Handle image uploads
        images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    images.append(filename)
        
        place_id = generate_place_id()
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO places 
            (place_id, user_id, category, subcategory, title, description, address, phone, images, morning_shift, evening_shift, region) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (place_id, session['user_id'], category, subcategory, title, description, address, phone, 
              json.dumps(images), morning_shift, evening_shift, region))
        
        # Update user free places count if not admin
        if not user['is_admin']:
            conn.execute('UPDATE users SET free_places = free_places - 1 WHERE user_id = ?', (session['user_id'],))
        
        # Add score for adding place
        conn.execute('UPDATE users SET score = score + 83 WHERE user_id = ?', (session['user_id'],))
        
        # Notify users in the same region
        users_in_region = conn.execute('SELECT user_id FROM users WHERE region = ? AND user_id != ?', 
                                      (region, session['user_id'])).fetchall()
        
        for user_in_region in users_in_region:
            add_notification(user_in_region['user_id'], 
                            f'مکان جدیدی در منطقه {region} اضافه شد: {title} - {address}')
        
        conn.commit()
        conn.close()
        
        flash('مکان با موفقیت اضافه شد', 'success')
        return redirect(url_for('place_detail', place_id=place_id))
    
    return render_template('add_place.html', categories=CATEGORIES, regions=REGIONS)

@app.route('/edit_place/<place_id>', methods=['GET', 'POST'])
@login_required
def edit_place(place_id):
    conn = get_db_connection()
    place = conn.execute('SELECT * FROM places WHERE place_id = ?', (place_id,)).fetchone()
    
    if not place:
        flash('مکان مورد نظر یافت نشد', 'danger')
        return redirect(url_for('index'))
    
    # Check if user is owner or admin
    user = get_user_info(session['user_id'])
    if place['user_id'] != session['user_id'] and not user['is_admin']:
        flash('شما اجازه ویرایش این مکان را ندارید', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))
    
    if request.method == 'POST':
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        title = request.form.get('title')
        description = request.form.get('description')
        address = request.form.get('address')
        phone = request.form.get('phone')
        morning_shift = request.form.get('morning_shift')
        evening_shift = request.form.get('evening_shift')
        region = request.form.get('region')
        
        # Validate required fields
        if not category or not subcategory or not title or not description or not address or not region:
            flash('لطفاً تمام فیلدهای ضروری را پر کنید', 'danger')
            return render_template('edit_place.html', place=place, categories=CATEGORIES, regions=REGIONS)
        
        # Validate description length
        if len(description.split()) < 10:
            flash('توضیحات باید حداقل 10 کلمه باشد', 'danger')
            return render_template('edit_place.html', place=place, categories=CATEGORIES, regions=REGIONS)
        
        # Validate phone if provided
        if phone and (not phone.startswith('09') or len(phone) != 11 or not phone.isdigit()):
            flash('شماره تماس باید 11 رقمی و با 09 شروع شود', 'danger')
            return render_template('edit_place.html', place=place, categories=CATEGORIES, regions=REGIONS)
        
        # Handle image uploads
        images = json.loads(place['images']) if place['images'] else []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    images.append(filename)
        
        # Update place
        conn.execute('''
            UPDATE places 
            SET category = ?, subcategory = ?, title = ?, description = ?, address = ?, 
                phone = ?, images = ?, morning_shift = ?, evening_shift = ?, region = ?
            WHERE place_id = ?
        ''', (category, subcategory, title, description, address, phone, 
              json.dumps(images), morning_shift, evening_shift, region, place_id))
        
        conn.commit()
        conn.close()
        
        flash('مکان با موفقیت ویرایش شد', 'success')
        return redirect(url_for('place_detail', place_id=place_id))
    
    conn.close()
    return render_template('edit_place.html', place=place, categories=CATEGORIES, regions=REGIONS)

@app.route('/delete_place/<place_id>', methods=['POST'])
@login_required
def delete_place(place_id):
    conn = get_db_connection()
    place = conn.execute('SELECT * FROM places WHERE place_id = ?', (place_id,)).fetchone()
    
    if not place:
        flash('مکان مورد نظر یافت نشد', 'danger')
        return redirect(url_for('index'))
    
    # Check if user is owner or admin
    user = get_user_info(session['user_id'])
    if place['user_id'] != session['user_id'] and not user['is_admin']:
        flash('شما اجازه حذف این مکان را ندارید', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))
    
    # Delete place
    conn.execute('DELETE FROM places WHERE place_id = ?', (place_id,))
    conn.execute('DELETE FROM votes WHERE place_id = ?', (place_id,))
    conn.execute('DELETE FROM comments WHERE place_id = ?', (place_id,))
    
    conn.commit()
    conn.close()
    
    flash('مکان با موفقیت حذف شد', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    
    # Get user info
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    # Get user places
    user_places = conn.execute('SELECT * FROM places WHERE user_id = ? ORDER BY created_at DESC', 
                              (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('profile.html', user=user, places=user_places)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        region = request.form.get('region')
        
        if not name or not age or not gender or not region:
            flash('لطفاً تمام فیلدها را پر کنید', 'danger')
            return render_template('edit_profile.html', user=user, regions=REGIONS)
        
        try:
            age = int(age)
            if age < 13 or age > 70:
                flash('سن باید بین 13 تا 70 سال باشد', 'danger')
                return render_template('edit_profile.html', user=user, regions=REGIONS)
        except ValueError:
            flash('سن باید یک عدد باشد', 'danger')
            return render_template('edit_profile.html', user=user, regions=REGIONS)
        
        # Update user profile
        conn.execute('''
            UPDATE users 
            SET name = ?, age = ?, gender = ?, region = ?
            WHERE user_id = ?
        ''', (name, age, gender, region, session['user_id']))
        
        conn.commit()
        conn.close()
        
        flash('پروفایل با موفقیت ویرایش شد', 'success')
        return redirect(url_for('profile'))
    
    conn.close()
    return render_template('edit_profile.html', user=user, regions=REGIONS)

@app.route('/become_admin', methods=['POST'])
@login_required
def become_admin():
    admin_code = request.form.get('admin_code')
    
    if admin_code == 'YOUR_SECRET_ADMIN_CODE':  # Replace with your actual admin code
        conn = get_db_connection()
        conn.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
        
        flash('شما اکنون ادمین هستید', 'success')
    else:
        flash('کد ادمین نامعتبر است', 'danger')
    
    return redirect(url_for('profile'))

@app.route('/admin')
@admin_required
def admin_panel():
    conn = get_db_connection()
    
    # Get statistics
    user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    place_count = conn.execute('SELECT COUNT(*) as count FROM places').fetchone()['count']
    top_place_count = conn.execute('SELECT COUNT(*) as count FROM places WHERE is_top_place = 1').fetchone()['count']
    
    # Get users by gender
    male_count = conn.execute('SELECT COUNT(*) as count FROM users WHERE gender = "پسر"').fetchone()['count']
    female_count = conn.execute('SELECT COUNT(*) as count FROM users WHERE gender = "دختر"').fetchone()['count']
    other_count = conn.execute('SELECT COUNT(*) as count FROM users WHERE gender = "دیگر"').fetchone()['count']
    
    # Get recent users
    recent_users = conn.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT 10').fetchall()
    
    # Get recent places
    recent_places = conn.execute('SELECT * FROM places ORDER BY created_at DESC LIMIT 10').fetchall()
    
    conn.close()
    
    return render_template('admin.html',
                         user_count=user_count,
                         place_count=place_count,
                         top_place_count=top_place_count,
                         male_count=male_count,
                         female_count=female_count,
                         other_count=other_count,
                         recent_users=recent_users,
                         recent_places=recent_places)

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/block_user/<user_id>', methods=['POST'])
@admin_required
def admin_block_user(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_blocked = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash('کاربر با موفقیت مسدود شد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/unblock_user/<user_id>', methods=['POST'])
@admin_required
def admin_unblock_user(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_blocked = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash('کاربر با موفقیت رفع مسدودیت شد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/places')
@admin_required
def admin_places():
    conn = get_db_connection()
    places = conn.execute('SELECT * FROM places ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_places.html', places=places)

@app.route('/admin/add_score/<user_id>', methods=['POST'])
@admin_required
def admin_add_score(user_id):
    score = request.form.get('score')
    
    try:
        score = int(score)
    except ValueError:
        flash('امتیاز باید یک عدد باشد', 'danger')
        return redirect(url_for('admin_users'))
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (score, user_id))
    conn.commit()
    conn.close()
    
    flash('امتیاز با موفقیت اضافه شد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/subtract_score/<user_id>', methods=['POST'])
@admin_required
def admin_subtract_score(user_id):
    score = request.form.get('score')
    
    try:
        score = int(score)
    except ValueError:
        flash('امتیاز باید یک عدد باشد', 'danger')
        return redirect(url_for('admin_users'))
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET score = score - ? WHERE user_id = ?', (score, user_id))
    conn.commit()
    conn.close()
    
    flash('امتیاز با موفقیت کسر شد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/manage_votes', methods=['GET', 'POST'])
@admin_required
def admin_manage_votes():
    if request.method == 'POST':
        action = request.form.get('action')
        place_title = request.form.get('place_title')
        user_id = request.form.get('user_id')
        vote_count = request.form.get('vote_count')
        vote_score = request.form.get('vote_score')
        
        try:
            vote_count = int(vote_count)
            vote_score = float(vote_score)
            
            if vote_score < 0 or vote_score > 10:
                flash('امتیاز باید بین 0 تا 10 باشد', 'danger')
                return redirect(url_for('admin_manage_votes'))
        except ValueError:
            flash('تعداد رای و امتیاز باید عدد باشند', 'danger')
            return redirect(url_for('admin_manage_votes'))
        
        conn = get_db_connection()
        
        # Find place by title and user_id
        place = conn.execute('SELECT * FROM places WHERE title = ? AND user_id = ?', 
                            (place_title, user_id)).fetchone()
        
        if not place:
            flash('مکان مورد نظر یافت نشد', 'danger')
            return redirect(url_for('admin_manage_votes'))
        
        if action == 'add':
            new_total_score = place['total_score'] + (vote_count * vote_score)
            new_vote_count = place['vote_count'] + vote_count
            new_average_score = new_total_score / new_vote_count
            
            conn.execute('''
                UPDATE places 
                SET total_score = ?, vote_count = ?, average_score = ? 
                WHERE place_id = ?
            ''', (new_total_score, new_vote_count, new_average_score, place['place_id']))
            
            flash('رای‌ها با موفقیت اضافه شدند', 'success')
        
        elif action == 'subtract':
            new_total_score = max(0, place['total_score'] - (vote_count * vote_score))
            new_vote_count = max(0, place['vote_count'] - vote_count)
            new_average_score = new_total_score / new_vote_count if new_vote_count > 0 else 0
            
            conn.execute('''
                UPDATE places 
                SET total_score = ?, vote_count = ?, average_score = ? 
                WHERE place_id = ?
            ''', (new_total_score, new_vote_count, new_average_score, place['place_id']))
            
            flash('رای‌ها با موفقیت کسر شدند', 'success')
        
        # Check if place becomes top place
        if new_vote_count >= 100 and new_average_score >= 8 and not place['is_top_place']:
            conn.execute('UPDATE places SET is_top_place = 1 WHERE place_id = ?', (place['place_id'],))
            add_notification(place['user_id'], f'مکان شما با نام "{place["title"]}" وارد بخش مکان‌های برتر شد، به شما تبریک می‌گویم', place['place_id'])
        
        # Check if place loses top place status
        elif place['is_top_place'] and (new_vote_count < 100 or new_average_score < 8):
            conn.execute('UPDATE places SET is_top_place = 0 WHERE place_id = ?', (place['place_id'],))
            add_notification(place['user_id'], f'دیگر مکان شما "{place["title"]}" در مکان‌های برتر نیست', place['place_id'])
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_manage_votes'))
    
    return render_template('admin_manage_votes.html')

@app.route('/admin/manage_comments', methods=['GET', 'POST'])
@admin_required
def admin_manage_comments():
    if request.method == 'POST':
        place_title = request.form.get('place_title')
        user_id = request.form.get('user_id')
        comment_text = request.form.get('comment_text')
        commenter_id = request.form.get('commenter_id')
        
        conn = get_db_connection()
        
        # Find place by title and user_id
        place = conn.execute('SELECT * FROM places WHERE title = ? AND user_id = ?', 
                            (place_title, user_id)).fetchone()
        
        if not place:
            flash('مکان مورد نظر یافت نشد', 'danger')
            return redirect(url_for('admin_manage_comments'))
        
        # Find comment by text and commenter_id
        comment = conn.execute('''
            SELECT * FROM comments 
            WHERE place_id = ? AND user_id = ? AND comment LIKE ?
        ''', (place['place_id'], commenter_id, f'%{comment_text}%')).fetchone()
        
        if not comment:
            flash('نظر مورد نظر یافت نشد', 'danger')
            return redirect(url_for('admin_manage_comments'))
        
        # Delete comment
        conn.execute('DELETE FROM comments WHERE id = ?', (comment['id'],))
        
        # Notify commenter
        add_notification(commenter_id, 
                        f'نظر شما در نظرات مکان "{place_title}" توسط ادمین به دلیل نقض قوانین حذف شد')
        
        conn.commit()
        conn.close()
        
        flash('نظر با موفقیت حذف شد', 'success')
        return redirect(url_for('admin_manage_comments'))
    
    return render_template('admin_manage_comments.html')

@app.route('/admin/send_news', methods=['GET', 'POST'])
@admin_required
def admin_send_news():
    if request.method == 'POST':
        content = request.form.get('content')
        is_global = request.form.get('is_global')
        target_user_id = request.form.get('target_user_id')
        
        if not content:
            flash('لطفاً محتوای خبر را وارد کنید', 'danger')
            return redirect(url_for('admin_send_news'))
        
        conn = get_db_connection()
        
        if is_global == '1':
            # Send to all users
            users = conn.execute('SELECT user_id FROM users').fetchall()
            for user in users:
                add_notification(user['user_id'], content)
            
            flash('خبر با موفقیت برای همه کاربران ارسال شد', 'success')
        else:
            # Send to specific user
            if not target_user_id:
                flash('لطفاً شناسه کاربری هدف را وارد کنید', 'danger')
                return redirect(url_for('admin_send_news'))
            
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (target_user_id,)).fetchone()
            if not user:
                flash('کاربر مورد نظر یافت نشد', 'danger')
                return redirect(url_for('admin_send_news'))
            
            add_notification(target_user_id, content)
            flash('خبر با موفقیت برای کاربر مورد نظر ارسال شد', 'success')
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_send_news'))
    
    return render_template('admin_send_news.html')

@app.route('/notifications')
@login_required
def notifications():
    conn = get_db_connection()
    
    # Get user notifications
    user_notifications = conn.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Mark as read
    conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        content = request.form.get('content')
        
        if not content or len(content.strip()) < 10:
            flash('لطفاً گزارش خود را با حداقل 10 کاراکتر وارد کنید', 'danger')
            return render_template('report.html')
        
        conn = get_db_connection()
        
        # Add report
        conn.execute('INSERT INTO reports (reporter_id, content) VALUES (?, ?)',
                     (session['user_id'], content))
        
        # Get admin user
        admin = conn.execute('SELECT * FROM users WHERE is_admin = 1 LIMIT 1').fetchone()
        
        if admin:
            # Get reporter info
            reporter = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
            
            # Send notification to admin
            admin_message = f'''
گزارش جدید:
{content}

اطلاعات گزارش‌دهنده:
نام: {reporter['name']}
سن: {reporter['age']}
جنسیت: {reporter['gender']}
شناسه: {reporter['user_id']}
            '''
            
            add_notification(admin['user_id'], admin_message)
        
        conn.commit()
        conn.close()
        
        flash('گزارش شما با موفقیت ارسال شد و پیگیری خواهد شد', 'success')
        return redirect(url_for('index'))
    
    return render_template('report.html')

@app.route('/request_top_place', methods=['GET', 'POST'])
@login_required
def request_top_place():
    conn = get_db_connection()
    
    # Get user places
    user_places = conn.execute('SELECT * FROM places WHERE user_id = ?', (session['user_id'],)).fetchall()
    
    if request.method == 'POST':
        place_id = request.form.get('place_id')
        
        if not place_id:
            flash('لطفاً یک مکان انتخاب کنید', 'danger')
            return render_template('request_top_place.html', places=user_places)
        
        # Check if already requested
        existing_request = conn.execute('''
            SELECT * FROM top_place_requests 
            WHERE user_id = ? AND place_id = ?
        ''', (session['user_id'], place_id)).fetchone()
        
        if existing_request:
            flash('شما قبلاً برای این مکان درخواست داده‌اید', 'warning')
            return render_template('request_top_place.html', places=user_places)
        
        # Add request
        conn.execute('INSERT INTO top_place_requests (user_id, place_id) VALUES (?, ?)',
                     (session['user_id'], place_id))
        
        # Get admin user
        admin = conn.execute('SELECT * FROM users WHERE is_admin = 1 LIMIT 1').fetchone()
        
        if admin:
            # Get user and place info
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
            place = conn.execute('SELECT * FROM places WHERE place_id = ?', (place_id,)).fetchone()
            
            # Send notification to admin
            admin_message = f'''
کاربر {user['name']} ({user['age']} ساله، {user['gender']}) برای شما درخواستی ارسال کرده که این مکان: "{place['title']}" برود در بخش مکان‌های برتر.

شناسه صاحب مکان: {user['user_id']}
            '''
            
            add_notification(admin['user_id'], admin_message)
        
        conn.commit()
        conn.close()
        
        flash('درخواست شما با موفقیت ارسال شد', 'success')
        return redirect(url_for('index'))
    
    conn.close()
    return render_template('request_top_place.html', places=user_places)

@app.route('/payment')
@login_required
def payment():
    return render_template('payment.html')

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    # Simulate payment processing
    # In a real application, you would integrate with a payment gateway
    
    conn = get_db_connection()
    
    # Update user subscription
    conn.execute('''
        UPDATE users 
        SET free_places = free_places + 5, subscription_date = ?
        WHERE user_id = ?
    ''', (datetime.now().isoformat(), session['user_id']))
    
    conn.commit()
    conn.close()
    
    flash('پرداخت با موفقیت انجام شد و 5 مکان به حساب شما اضافه شد', 'success')
    return redirect(url_for('index'))

@app.route('/help')
@login_required
def help():
    return render_template('help.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('شما با موفقیت خارج شدید', 'success')
    return redirect(url_for('welcome'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Template filters
@app.template_filter('to_persian_numbers')
def to_persian_numbers(value):
    if value is None:
        return ''
    
    value = str(value)
    english_to_persian = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return value.translate(english_to_persian)

@app.template_filter('format_date')
def format_date(value):
    if value is None:
        return ''
    
    try:
        date_obj = datetime.fromisoformat(value)
        return date_obj.strftime('%Y/%m/%d %H:%M')
    except (ValueError, TypeError):
        return value

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=app.config['PORT'])