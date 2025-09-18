from flask import Flask, request, jsonify, send_from_directory
import json
import os
import uuid
from datetime import datetime
import re

app = Flask(__name__)

# تنظیم دایرکتوری برای ذخیره داده‌ها
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
LOCATIONS_FILE = os.path.join(DATA_DIR, 'locations.json')
COMMENTS_FILE = os.path.join(DATA_DIR, 'comments.json')
CHAT_FILE = os.path.join(DATA_DIR, 'chat.json')
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, 'notifications.json')

# ایجاد دایرکتوری اگر وجود نداشته باشد
os.makedirs(DATA_DIR, exist_ok=True)
for file in [USERS_FILE, LOCATIONS_FILE, COMMENTS_FILE, CHAT_FILE, NOTIFICATIONS_FILE]:
    if not os.path.exists(file):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)

# دایرکتوری برای ذخیره عکس‌ها
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# لیست شهرها/شهرک‌ها
CITIES = [
    "شهرک صدرا", "شهرک گلستان", "معالی آباد", "شهرک کشن", "شهرک مهدیه",
    "شهرک زینبیه", "شهرک بعثت", "شهرک والفجر", "شهرک صنعتی عفیف آباد",
    "کوی امام رضا", "شهرک گویم", "شهرک بزین", "شهرک رحمت آباد", "شهرک خورشید",
    "شهرک سلامت", "شهرک فرهنگیان", "کوی زاگرس", "کوی پاسداران", "شهرک عرفان",
    "شهرک هنرستان"
]

# دسته‌بندی‌ها و زیر دسته‌ها
CATEGORIES = {
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
        "خدمات گازکشی و تعمیرات گاز (گازکشی، تعمیر گاز)",
        "خدمات تعمیرات لوازم برقی (تعمیر لوازم برقی، لوازم خانگی)",
        "خدمات کولر و سیستم‌های سرمایشی (کولر، سرمایش)",
        "خدمات گرمایشی و پکیج (گرمایش، پکیج)",
        "خدمات آنتن و تلویزیون (آنتن، تلویزیون)",
        "خدمات اینترنت و شبکه (اینترنت، شبکه)",
        "خدمات تعمیرات موبایل و تبلت (تعمیر موبایل، تبلت)",
        "خدمات تعمیرات لپ‌تاپ و کامپیوتر (تعمیر لپ‌تاپ، کامپیوتر)",
        "خدمات تعمیرات کنسول بازی (تعمیر کنسول، بازی)",
        "خدمات تعمیرات ساعت و جواهر (تعمیر ساعت، جواهر)",
        "خدمات تعمیرات لوازم صوتی و تصویری (صوتی، تصویری)",
        "خدمات تعمیرات لوازم خانگی بزرگ (یخچال، لباس‌شویی)",
        "خدمات تعمیرات لوازم خانگی کوچک (مایکروویو، قهوه‌ساز)",
        "خدمات تعمیرات لوازم نجاری و چوبی (نجاری، چوب)",
        "خدمات تعمیرات لوازم سفالین و سرامیک (سفال، سرامیک)",
        "خدمات تعمیرات لوازم فلزی و آهنی (فلزی، آهنی)",
        "خدمات تعمیرات لوازم پلاستیکی (پلاستیک، تعمیر)",
        "خدمات تعمیرات لوازم کفش و چرم (کفش، چرم)",
        "خدمات تعمیرات لوازم نساجی و پارچه (نساجی، پارچه)",
        "خدمات تعمیرات لوازم آشپزخانه (آشپزخانه، تعمیر)",
        "خدمات تعمیرات لوازم تعمیراتی (تعمیرات، خدمات)",
        "خدمات تعمیرات لوازم خدماتی (خدمات، تعمیرات)"
    ],
    "🏠 خدمات خانگی و ساختمانی": [
        "خدمات نجاری و چوب‌کاری (نجاری، چوب‌کاری)",
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

# HTML template for custom alert
CUSTOM_ALERT_HTML = """
<div id="customAlert" class="custom-alert">
    <div class="alert-content">
        <div class="alert-header">
            <span class="alert-title" id="alertTitle"></span>
            <span class="alert-close" onclick="hideCustomAlert()">&times;</span>
        </div>
        <div class="alert-body" id="alertMessage"></div>
        <div class="alert-footer">
            <button class="alert-btn" onclick="hideCustomAlert()">تایید</button>
        </div>
    </div>
</div>
"""

# HTML template for registration page (updated with custom alert)
REGISTER_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ثبت نام در گویم نما</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap');
        :root {
            --primary: #006769;
            --secondary: #40A578;
            --success: #4caf50;
            --error: #f44336;
            --background: #f8f9fa;
            --text: #333;
            --light: #fff;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Vazirmatn', sans-serif;
        }
        body {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background-color: var(--light);
            border-radius: 20px;
            box-shadow: var(--shadow);
            width: 100%;
            max-width: 500px;
            overflow: hidden;
            animation: fadeIn 0.5s ease-out;
        }
        .header {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        .form-container {
            padding: 30px;
        }
        .form-group {
            margin-bottom: 20px;
            position: relative;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--text);
        }
        .form-control {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5eb;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-control:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(0, 103, 105, 0.2);
            outline: none;
        }
        .form-control.error {
            border-color: var(--error);
        }
        .error-message {
            color: var(--error);
            font-size: 12px;
            margin-top: 5px;
            display: none;
        }
        .show-password {
            position: absolute;
            left: 15px;
            top: 40px;
            cursor: pointer;
            color: #777;
        }
        .btn {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            border: none;
            padding: 15px;
            border-radius: 10px;
            width: 100%;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }
        .btn:active {
            transform: translateY(0);
        }
        .register-link {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
        }
        .register-link a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 576px) {
            .container {
                border-radius: 10px;
            }
            .header {
                padding: 20px;
            }
            .form-container {
                padding: 20px;
            }
        }
        /* Custom Alert Styles */
        .custom-alert {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .alert-content {
            background-color: white;
            border-radius: 10px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            overflow: hidden;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateY(-50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .alert-header {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .alert-title {
            font-size: 18px;
            font-weight: 500;
        }
        .alert-close {
            font-size: 24px;
            cursor: pointer;
            background: none;
            border: none;
            color: white;
        }
        .alert-body {
            padding: 20px;
            text-align: center;
            font-size: 16px;
            color: var(--text);
        }
        .alert-footer {
            padding: 20px;
            text-align: center;
            border-top: 1px solid #eee;
        }
        .alert-btn {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        /* Success Checkmark */
        .success-checkmark {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            display: block;
            stroke-width: 2;
            stroke: #4caf50;
            stroke-miterlimit: 10;
            box-shadow: inset 0px 0px 0px #4caf50;
            animation: fill .4s ease-in-out .4s forwards, scale .3s ease-in-out .9s both;
            position: relative;
            top: 5px;
            right: 5px;
            margin: 0 auto;
        }
        .checkmark-circle {
            stroke-dasharray: 166;
            stroke-dashoffset: 166;
            stroke-width: 2;
            stroke-miterlimit: 10;
            stroke: #4caf50;
            fill: none;
            animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
        }
        .checkmark-check {
            transform-origin: 50% 50%;
            stroke-dasharray: 48;
            stroke-dashoffset: 48;
            animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;
        }
        @keyframes stroke {
            100% {
                stroke-dashoffset: 0;
            }
        }
        @keyframes scale {
            0%, 100% {
                transform: none;
            }
            50% {
                transform: scale3d(1.1, 1.1, 1);
            }
        }
        @keyframes fill {
            100% {
                box-shadow: inset 0px 0px 0px 30px #4caf50;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ثبت نام در گویم نما</h1>
            <p>حساب کاربری جدید بسازید</p>
        </div>
        <div class="form-container">
            <form id="registrationForm">
                <div class="form-group">
                    <label for="fullname">نام کاربری</label>
                    <input type="text" id="fullname" class="form-control" placeholder="نام کاربری خود را وارد کنید">
                    <div class="error-message" id="fullname-error">لطفاً نام کاربری معتبر وارد کنید (نباید تکراری باشد)</div>
                </div>
                <div class="form-group">
                    <label for="city">شهر</label>
                    <select id="city" class="form-control">
                        <option value="">لطفاً شهر خود را انتخاب کنید</option>
                        {% for city in cities %}
                        <option value="{{ city }}">{{ city }}</option>
                        {% endfor %}
                    </select>
                    <div class="error-message" id="city-error">لطفاً شهر خود را انتخاب کنید</div>
                </div>
                <div class="form-group">
                    <label for="phone">تلفن همراه</label>
                    <input type="tel" id="phone" class="form-control" placeholder="09xxxxxxxxx">
                    <div class="error-message" id="phone-error">لطفاً شماره تلفن معتبر وارد کنید</div>
                </div>
                <div class="form-group">
                    <label for="password">رمز عبور</label>
                    <input type="password" id="password" class="form-control" placeholder="رمز عبور قوی انتخاب کنید">
                    <span class="show-password" id="togglePassword">نمایش</span>
                    <div class="error-message" id="password-error">رمز عبور باید حداقل ۶ کاراکتر داشته باشد</div>
                </div>
                <div class="form-group">
                    <label for="confirmPassword">تکرار رمز عبور</label>
                    <input type="password" id="confirmPassword" class="form-control" placeholder="رمز عبور را تکرار کنید">
                    <div class="error-message" id="confirmPassword-error">رمزهای عبور مطابقت ندارند</div>
                </div>
                <button type="submit" class="btn">ثبت نام</button>
                <div class="register-link">قبلاً حساب دارید؟ <a href="/login">وارد شوید</a></div>
            </form>
        </div>
    </div>
""" + CUSTOM_ALERT_HTML + """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('registrationForm');
            const togglePassword = document.getElementById('togglePassword');
            const passwordInput = document.getElementById('password');
            const confirmPasswordInput = document.getElementById('confirmPassword');
            
            // نمایش/مخفی کردن رمز عبور
            togglePassword.addEventListener('click', function() {
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    togglePassword.textContent = 'پنهان';
                } else {
                    passwordInput.type = 'password';
                    togglePassword.textContent = 'نمایش';
                }
            });
            
            // اعتبارسنجی فرم
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                let isValid = true;
                
                // اعتبارسنجی نام کاربری
                const fullname = document.getElementById('fullname');
                const fullnameError = document.getElementById('fullname-error');
                if (fullname.value.trim() === '' || fullname.value.length < 3) {
                    fullname.classList.add('error');
                    fullnameError.style.display = 'block';
                    isValid = false;
                } else {
                    fullname.classList.remove('error');
                    fullnameError.style.display = 'none';
                }
                
                // اعتبارسنجی شهر
                const city = document.getElementById('city');
                const cityError = document.getElementById('city-error');
                if (city.value === '') {
                    city.classList.add('error');
                    cityError.style.display = 'block';
                    isValid = false;
                } else {
                    city.classList.remove('error');
                    cityError.style.display = 'none';
                }
                
                // اعتبارسنجی تلفن
                const phone = document.getElementById('phone');
                const phoneError = document.getElementById('phone-error');
                const phoneRegex = /^09\d{9}$/;
                if (!phoneRegex.test(phone.value)) {
                    phone.classList.add('error');
                    phoneError.style.display = 'block';
                    isValid = false;
                } else {
                    phone.classList.remove('error');
                    phoneError.style.display = 'none';
                }
                
                // اعتبارسنجی رمز عبور
                const password = document.getElementById('password');
                const passwordError = document.getElementById('password-error');
                if (password.value.length < 6) {
                    password.classList.add('error');
                    passwordError.style.display = 'block';
                    isValid = false;
                } else {
                    password.classList.remove('error');
                    passwordError.style.display = 'none';
                }
                
                // اعتبارسنجی تکرار رمز عبور
                const confirmPassword = document.getElementById('confirmPassword');
                const confirmPasswordError = document.getElementById('confirmPassword-error');
                if (confirmPassword.value !== password.value) {
                    confirmPassword.classList.add('error');
                    confirmPasswordError.style.display = 'block';
                    isValid = false;
                } else {
                    confirmPassword.classList.remove('error');
                    confirmPasswordError.style.display = 'none';
                }
                
                // اگر فرم معتبر است، ارسال شود
                if (isValid) {
                    // ایجاد شیء داده‌ها
                    const formData = {
                        username: fullname.value,
                        city: city.value,
                        phone: phone.value,
                        password: password.value,
                        timestamp: new Date().toISOString()
                    };
                    
                    // ارسال درخواست به سرور
                    fetch('/register', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // نمایش انیمیشن موفقیت
                            document.querySelector('.form-container').innerHTML = `
                                <div class="success-checkmark">
                                    <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                                        <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
                                        <path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                                    </svg>
                                </div>
                                <h2 style="text-align: center; color: #4caf50;">ثبت نام با موفقیت انجام شد!</h2>
                                <p style="text-align: center; margin-top: 20px;">در حال انتقال به صفحه اصلی...</p>
                            `;
                            
                            // انتقال به صفحه اصلی پس از 3 ثانیه
                            setTimeout(() => {
                                window.location.href = '/main?username=' + encodeURIComponent(data.user.username);
                            }, 3000);
                        } else {
                            if (data.message.includes('تکراری')) {
                                fullname.classList.add('error');
                                fullnameError.textContent = data.message;
                                fullnameError.style.display = 'block';
                            } else {
                                showCustomAlert('خطا', 'خطا در ثبت نام: ' + data.message, 'hideCustomAlert()');
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showCustomAlert('خطا', 'خطا در ارسال اطلاعات', 'hideCustomAlert()');
                    });
                }
            });
            
            // اعتبارسنجی در حین تایپ
            const inputs = form.querySelectorAll('input');
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    this.classList.remove('error');
                    const errorElement = document.getElementById(this.id + '-error');
                    if (errorElement) {
                        errorElement.style.display = 'none';
                    }
                });
            });
        });
        
        // نمایش پنجره هشدار سفارشی
        function showCustomAlert(title, message, callback) {
            document.getElementById('alertTitle').textContent = title;
            document.getElementById('alertMessage').textContent = message;
            document.getElementById('customAlert').style.display = 'flex';
            
            // تنظیم کال‌بک برای دکمه تایید
            document.querySelector('.alert-btn').onclick = function() {
                hideCustomAlert();
                if (callback && typeof callback === 'string') {
                    eval(callback);
                } else if (callback && typeof callback === 'function') {
                    callback();
                }
            };
        }
        
        // مخفی کردن پنجره هشدار سفارشی
        function hideCustomAlert() {
            document.getElementById('customAlert').style.display = 'none';
        }
    </script>
</body>
</html>"""

# HTML template for login page (updated with custom alert)
LOGIN_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود به گویم نما</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap');
        :root {
            --primary: #006769;
            --secondary: #40A578;
            --success: #4caf50;
            --error: #f44336;
            --background: #f8f9fa;
            --text: #333;
            --light: #fff;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Vazirmatn', sans-serif;
        }
        body {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background-color: var(--light);
            border-radius: 20px;
            box-shadow: var(--shadow);
            width: 100%;
            max-width: 500px;
            overflow: hidden;
            animation: fadeIn 0.5s ease-out;
        }
        .header {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        .form-container {
            padding: 30px;
        }
        .form-group {
            margin-bottom: 20px;
            position: relative;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--text);
        }
        .form-control {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5eb;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-control:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(0, 103, 105, 0.2);
            outline: none;
        }
        .form-control.error {
            border-color: var(--error);
        }
        .error-message {
            color: var(--error);
            font-size: 12px;
            margin-top: 5px;
            display: none;
        }
        .show-password {
            position: absolute;
            left: 15px;
            top: 40px;
            cursor: pointer;
            color: #777;
        }
        .btn {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            border: none;
            padding: 15px;
            border-radius: 10px;
            width: 100%;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }
        .btn:active {
            transform: translateY(0);
        }
        .register-link {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
        }
        .register-link a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 576px) {
            .container {
                border-radius: 10px;
            }
            .header {
                padding: 20px;
            }
            .form-container {
                padding: 20px;
            }
        }
        /* Custom Alert Styles */
        .custom-alert {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .alert-content {
            background-color: white;
            border-radius: 10px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            overflow: hidden;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateY(-50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .alert-header {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .alert-title {
            font-size: 18px;
            font-weight: 500;
        }
        .alert-close {
            font-size: 24px;
            cursor: pointer;
            background: none;
            border: none;
            color: white;
        }
        .alert-body {
            padding: 20px;
            text-align: center;
            font-size: 16px;
            color: var(--text);
        }
        .alert-footer {
            padding: 20px;
            text-align: center;
            border-top: 1px solid #eee;
        }
        .alert-btn {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        /* Success Checkmark */
        .success-checkmark {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            display: block;
            stroke-width: 2;
            stroke: #4caf50;
            stroke-miterlimit: 10;
            box-shadow: inset 0px 0px 0px #4caf50;
            animation: fill .4s ease-in-out .4s forwards, scale .3s ease-in-out .9s both;
            position: relative;
            top: 5px;
            right: 5px;
            margin: 0 auto;
        }
        .checkmark-circle {
            stroke-dasharray: 166;
            stroke-dashoffset: 166;
            stroke-width: 2;
            stroke-miterlimit: 10;
            stroke: #4caf50;
            fill: none;
            animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
        }
        .checkmark-check {
            transform-origin: 50% 50%;
            stroke-dasharray: 48;
            stroke-dashoffset: 48;
            animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;
        }
        @keyframes stroke {
            100% {
                stroke-dashoffset: 0;
            }
        }
        @keyframes scale {
            0%, 100% {
                transform: none;
            }
            50% {
                transform: scale3d(1.1, 1.1, 1);
            }
        }
        @keyframes fill {
            100% {
                box-shadow: inset 0px 0px 0px 30px #4caf50;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ورود به گویم نما</h1>
            <p>برای دسترسی به حساب خود وارد شوید</p>
        </div>
        <div class="form-container">
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">نام کاربری یا شماره تلفن</label>
                    <input type="text" id="username" class="form-control" placeholder="نام کاربری یا شماره تلفن خود را وارد کنید">
                    <div class="error-message" id="username-error">لطفاً نام کاربری یا شماره تلفن معتبر وارد کنید</div>
                </div>
                <div class="form-group">
                    <label for="password">رمز عبور</label>
                    <input type="password" id="password" class="form-control" placeholder="رمز عبور خود را وارد کنید">
                    <span class="show-password" id="togglePassword">نمایش</span>
                    <div class="error-message" id="password-error">لطفاً رمز عبور خود را وارد کنید</div>
                </div>
                <button type="submit" class="btn">ورود</button>
                <div class="register-link">حساب ندارید؟ <a href="/">ثبت نام کنید</a></div>
            </form>
        </div>
    </div>
""" + CUSTOM_ALERT_HTML + """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('loginForm');
            const togglePassword = document.getElementById('togglePassword');
            const passwordInput = document.getElementById('password');
            
            // نمایش/مخفی کردن رمز عبور
            togglePassword.addEventListener('click', function() {
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    togglePassword.textContent = 'پنهان';
                } else {
                    passwordInput.type = 'password';
                    togglePassword.textContent = 'نمایش';
                }
            });
            
            // اعتبارسنجی فرم
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                let isValid = true;
                
                // اعتبارسنجی نام کاربری/تلفن
                const username = document.getElementById('username');
                const usernameError = document.getElementById('username-error');
                if (username.value.trim() === '') {
                    username.classList.add('error');
                    usernameError.style.display = 'block';
                    isValid = false;
                } else {
                    username.classList.remove('error');
                    usernameError.style.display = 'none';
                }
                
                // اعتبارسنجی رمز عبور
                const password = document.getElementById('password');
                const passwordError = document.getElementById('password-error');
                if (password.value.trim() === '') {
                    password.classList.add('error');
                    passwordError.style.display = 'block';
                    isValid = false;
                } else {
                    password.classList.remove('error');
                    passwordError.style.display = 'none';
                }
                
                // اگر فرم معتبر است، ارسال شود
                if (isValid) {
                    // ایجاد شیء داده‌ها
                    const formData = {
                        username: username.value,
                        password: password.value
                    };
                    
                    // ارسال درخواست به سرور
                    fetch('/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // نمایش انیمیشن موفقیت
                            document.querySelector('.form-container').innerHTML = `
                                <div class="success-checkmark">
                                    <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                                        <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
                                        <path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                                    </svg>
                                </div>
                                <h2 style="text-align: center; color: #4caf50;">ورود با موفقیت انجام شد!</h2>
                                <p style="text-align: center; margin-top: 20px;">در حال انتقال به صفحه اصلی...</p>
                            `;
                            
                            // انتقال به صفحه اصلی پس از 2 ثانیه
                            setTimeout(() => {
                                window.location.href = '/main?username=' + encodeURIComponent(data.user.username);
                            }, 2000);
                        } else {
                            showCustomAlert('خطا', data.message, 'hideCustomAlert()');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showCustomAlert('خطا', 'خطا در ارسال اطلاعات', 'hideCustomAlert()');
                    });
                }
            });
            
            // اعتبارسنجی در حین تایپ
            const inputs = form.querySelectorAll('input');
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    this.classList.remove('error');
                    const errorElement = document.getElementById(this.id + '-error');
                    if (errorElement) {
                        errorElement.style.display = 'none';
                    }
                });
            });
        });
        
        // نمایش پنجره هشدار سفارشی
        function showCustomAlert(title, message, callback) {
            document.getElementById('alertTitle').textContent = title;
            document.getElementById('alertMessage').textContent = message;
            document.getElementById('customAlert').style.display = 'flex';
            
            // تنظیم کال‌بک برای دکمه تایید
            document.querySelector('.alert-btn').onclick = function() {
                hideCustomAlert();
                if (callback && typeof callback === 'string') {
                    eval(callback);
                } else if (callback && typeof callback === 'function') {
                    callback();
                }
            };
        }
        
        // مخفی کردن پنجره هشدار سفارشی
        function hideCustomAlert() {
            document.getElementById('customAlert').style.display = 'none';
        }
    </script>
</body>
</html>"""

# Main HTML template (updated with all sections and functionalities)
MAIN_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>گویم نما - صفحه اصلی</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap');
        :root {
            --primary: #006769;
            --secondary: #40A578;
            --success: #4caf50;
            --error: #f44336;
            --background: #f8f9fa;
            --text: #333;
            --light: #fff;
            --gray: #f0f0f0;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Vazirmatn', sans-serif;
        }
        body {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding-bottom: 80px;
        }
        .welcome-header {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            padding: 20px;
            text-align: center;
        }
        .welcome-header h2 {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .welcome-header p {
            font-size: 14px;
            opacity: 0.9;
        }
        .content-section {
            display: none;
            padding: 20px;
            animation: fadeIn 0.5s ease-out;
        }
        .content-section.active {
            display: block;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h3 {
            color: var(--primary);
            margin-bottom: 20px;
            font-weight: 700;
        }
        /* Home Section */
        .locations-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 15px;
        }
        .location-tile {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--shadow);
            cursor: pointer;
            transition: transform 0.3s;
        }
        .location-tile:hover {
            transform: translateY(-5px);
        }
        .location-image {
            height: 120px;
            background-size: cover;
            background-position: center;
        }
        .location-info {
            padding: 10px;
        }
        .location-title {
            font-weight: 500;
            font-size: 14px;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .location-city {
            font-size: 12px;
            color: #666;
        }
        /* Location Detail Section */
        .location-detail {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: var(--shadow);
        }
        .location-detail-image {
            height: 200px;
            background-size: cover;
            background-position: center;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .location-detail-title {
            font-size: 20px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 10px;
        }
        .detail-field {
            margin-bottom: 15px;
        }
        .detail-label {
            font-weight: 500;
            color: #666;
            font-size: 14px;
        }
        .detail-value {
            font-size: 16px;
            color: var(--text);
            margin-top: 5px;
        }
        .action-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .action-btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
        }
        .chat-btn {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
        }
        .edit-btn {
            background: var(--gray);
            color: var(--text);
        }
        .back-arrow {
            font-size: 24px;
            cursor: pointer;
            margin-bottom: 20px;
            display: inline-block;
        }
        /* Add Location Section */
        .add-container {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: var(--shadow);
        }
        .add-step {
            display: none;
        }
        .add-step.active {
            display: block;
        }
        .photo-upload {
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        .photo-upload:hover {
            border-color: var(--primary);
            background-color: rgba(0, 103, 105, 0.05);
        }
        .photo-preview {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        .preview-item {
            position: relative;
            width: 80px;
            height: 80px;
        }
        .preview-item img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 5px;
        }
        .remove-photo {
            position: absolute;
            top: -5px;
            right: -5px;
            background: var(--error);
            color: white;
            border: none;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 12px;
            cursor: pointer;
        }
        .set-main-photo {
            position: absolute;
            bottom: -5px;
            left: -5px;
            background: var(--success);
            color: white;
            border: none;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 12px;
            cursor: pointer;
        }
        .main-photo-indicator {
            position: absolute;
            top: 5px;
            left: 5px;
            background: var(--success);
            color: white;
            border-radius: 3px;
            padding: 2px 5px;
            font-size: 10px;
        }
        .form-field {
            margin-bottom: 20px;
        }
        .form-field label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--text);
        }
        .form-field label.required::after {
            content: " *";
            color: var(--error);
        }
        .form-field input, .form-field textarea, .form-field select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5eb;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-field input:focus, .form-field textarea:focus, .form-field select:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(0, 103, 105, 0.2);
            outline: none;
        }
        .nav-buttons {
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
        }
        .nav-btn {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }
        .back-btn {
            background: var(--gray);
            color: var(--text);
        }
        .next-btn, .submit-btn {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
        }
        /* Profile Section */
        .profile-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: var(--shadow);
        }
        .profile-item {
            margin-bottom: 20px;
        }
        .profile-label {
            font-weight: 500;
            color: #666;
            font-size: 14px;
        }
        .profile-value {
            font-size: 16px;
            color: var(--text);
            margin-top: 5px;
        }
        .profile-actions {
            margin-top: 30px;
        }
        .action-button {
            width: 100%;
            padding: 15px;
            background: var(--gray);
            border: none;
            border-radius: 10px;
            font-weight: 500;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .action-button:hover {
            background: #e0e0e0;
        }
        .edit-form {
            display: none;
            margin-top: 15px;
        }
        .edit-form input {
            width: 100%;
            padding: 10px;
            border: 2px solid #e1e5eb;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .form-actions {
            display: flex;
            gap: 10px;
        }
        .save-btn, .cancel-btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 5px;
            font-weight: 500;
            cursor: pointer;
        }
        .save-btn {
            background: var(--success);
            color: white;
        }
        .cancel-btn {
            background: var(--gray);
            color: var(--text);
        }
        /* Chat Section */
        .chat-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .chat-item {
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: var(--shadow);
            cursor: pointer;
            transition: all 0.3s;
        }
        .chat-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }
        .chat-user {
            font-weight: 500;
            margin-bottom: 5px;
        }
        .chat-last-message {
            font-size: 14px;
            color: #666;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .chat-messages {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: var(--shadow);
            height: 70vh;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        .message {
            margin-bottom: 15px;
            max-width: 80%;
        }
        .message.sent {
            margin-left: auto;
            text-align: right;
        }
        .message.received {
            margin-right: auto;
        }
        .message-content {
            display: inline-block;
            padding: 10px 15px;
            border-radius: 18px;
            font-size: 14px;
        }
        .sent .message-content {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
        }
        .received .message-content {
            background: var(--gray);
            color: var(--text);
        }
        .message-time {
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }
        .chat-input {
            display: flex;
            gap: 10px;
        }
        .chat-input input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e1e5eb;
            border-radius: 10px;
            font-size: 14px;
        }
        .chat-input input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(0, 103, 105, 0.2);
            outline: none;
        }
        .chat-send-btn {
            padding: 15px 20px;
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 500;
            cursor: pointer;
        }
        /* Notifications Section */
        .notifications-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .notification-item {
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: var(--shadow);
        }
        .notification-title {
            font-weight: 500;
            margin-bottom: 5px;
        }
        .notification-message {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        .notification-time {
            font-size: 12px;
            color: #999;
        }
        /* Comments Section */
        .comments-section {
            margin-top: 30px;
        }
        .comment-form {
            margin-bottom: 20px;
        }
        .star-rating {
            display: flex;
            justify-content: center;
            margin-bottom: 10px;
        }
        .star {
            font-size: 24px;
            color: #ddd;
            cursor: pointer;
            transition: color 0.3s;
        }
        .star.filled {
            color: #ffc107;
        }
        .comments-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .comment-item {
            background: var(--gray);
            padding: 15px;
            border-radius: 10px;
        }
        .comment-user {
            font-weight: 500;
            margin-bottom: 5px;
        }
        .comment-stars {
            color: #ffc107;
            margin-bottom: 5px;
        }
        .comment-text {
            color: #666;
        }
        /* Bottom Navigation */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            display: flex;
            justify-content: space-around;
            padding: 10px 0;
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
            z-index: 100;
        }
        .nav-item {
            text-align: center;
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .nav-item.active {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
        }
        .nav-icon {
            font-size: 20px;
            margin-bottom: 5px;
        }
        .nav-text {
            font-size: 12px;
        }
        /* Custom Alert Styles */
        .custom-alert {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .alert-content {
            background-color: white;
            border-radius: 10px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            overflow: hidden;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateY(-50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .alert-header {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .alert-title {
            font-size: 18px;
            font-weight: 500;
        }
        .alert-close {
            font-size: 24px;
            cursor: pointer;
            background: none;
            border: none;
            color: white;
        }
        .alert-body {
            padding: 20px;
            text-align: center;
            font-size: 16px;
            color: var(--text);
        }
        .alert-footer {
            padding: 20px;
            text-align: center;
            border-top: 1px solid #eee;
        }
        .alert-btn {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        /* Success Checkmark */
        .success-checkmark {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            display: block;
            stroke-width: 2;
            stroke: #4caf50;
            stroke-miterlimit: 10;
            box-shadow: inset 0px 0px 0px #4caf50;
            animation: fill .4s ease-in-out .4s forwards, scale .3s ease-in-out .9s both;
            position: relative;
            top: 5px;
            right: 5px;
            margin: 0 auto;
        }
        .checkmark-circle {
            stroke-dasharray: 166;
            stroke-dashoffset: 166;
            stroke-width: 2;
            stroke-miterlimit: 10;
            stroke: #4caf50;
            fill: none;
            animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
        }
        .checkmark-check {
            transform-origin: 50% 50%;
            stroke-dasharray: 48;
            stroke-dashoffset: 48;
            animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;
        }
        @keyframes stroke {
            100% {
                stroke-dashoffset: 0;
            }
        }
        @keyframes scale {
            0%, 100% {
                transform: none;
            }
            50% {
                transform: scale3d(1.1, 1.1, 1);
            }
        }
        @keyframes fill {
            100% {
                box-shadow: inset 0px 0px 0px 30px #4caf50;
            }
        }
    </style>
</head>
<body>
    <div class="welcome-header">
        <h2>خوش آمدید، {{ username }}!</h2>
        <p>به اپلیکیشن گویم نما خوش آمدید</p>
    </div>
    
    <div id="homeSection" class="content-section active">
        <h3>صفحه اصلی</h3>
        <div class="locations-list">
            {% for loc in all_locations %}
            <div class="location-tile" onclick="showLocationDetails('{{ loc.id }}')">
                <div class="location-image" style="background-image: url('/uploads/{{ loc.photos[0] }}');"></div>
                <div class="location-info">
                    <div class="location-title">{{ loc.title }}</div>
                    <div class="location-city">{{ loc.city }}</div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <div id="locationDetailSection" class="content-section">
        <span class="back-arrow" onclick="showSection('homeSection', document.querySelector('.nav-item[onclick*=\"homeSection\"]'))">⬅️</span>
        <div class="location-detail">
            <div class="location-detail-image" id="locImage"></div>
            <div class="location-detail-title" id="locTitle"></div>
            <div class="detail-field">
                <div class="detail-label">توضیحات</div>
                <div class="detail-value" id="locDesc"></div>
            </div>
            <div class="detail-field">
                <div class="detail-label">شهرک</div>
                <div class="detail-value" id="locCity"></div>
            </div>
            <div class="detail-field">
                <div class="detail-label">آدرس</div>
                <div class="detail-value" id="locAddress"></div>
            </div>
            <div class="detail-field" id="locPhoneField">
                <div class="detail-label">شماره موبایل</div>
                <div class="detail-value" id="locPhone"></div>
            </div>
            <div class="detail-field" id="locShiftsField">
                <div class="detail-label">شیفت‌ها</div>
                <div class="detail-value" id="locShifts"></div>
            </div>
            <div class="detail-field">
                <div class="detail-label">دسته</div>
                <div class="detail-value" id="locCategory"></div>
            </div>
            <div class="detail-field">
                <div class="detail-label">زیر دسته</div>
                <div class="detail-value" id="locSubcategory"></div>
            </div>
            <div class="action-buttons" id="locActions"></div>
            <div class="comments-section">
                <h4>نظرات</h4>
                <div class="comment-form">
                    <textarea id="commentText" placeholder="نظر خود را بنویسید"></textarea>
                    <div class="star-rating">
                        <span class="star" onclick="setRating(1)">★</span>
                        <span class="star" onclick="setRating(2)">★</span>
                        <span class="star" onclick="setRating(3)">★</span>
                        <span class="star" onclick="setRating(4)">★</span>
                        <span class="star" onclick="setRating(5)">★</span>
                    </div>
                    <button class="submit-btn" onclick="submitComment()">ارسال نظر</button>
                </div>
                <div class="comments-list" id="commentsList"></div>
            </div>
        </div>
    </div>
    
    <div id="addSection" class="content-section">
        <h3>افزودن مکان</h3>
        <div class="add-container">
            <div id="addStep1" class="add-step active">
                <div class="photo-upload" onclick="document.getElementById('photoInput').click()">
                    <span style="font-size: 50px;">+</span>
                    <p>اضافه کردن عکس</p>
                </div>
                <input type="file" id="photoInput" multiple accept="image/*" style="display: none;" onchange="previewPhotos()">
                <div class="photo-preview" id="photoPreview"></div>
                <div class="form-field">
                    <label class="required">عنوان مکان</label>
                    <input type="text" id="locTitleInput" placeholder="عنوان را وارد کنید">
                </div>
                <div class="form-field">
                    <label class="required">شهرک</label>
                    <select id="locCitySelect">
                        <option value="">انتخاب شهرک</option>
                        {% for city in cities %}
                        <option value="{{ city }}">{{ city }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-field">
                    <label class="required">آدرس</label>
                    <textarea id="locAddressInput" placeholder="آدرس را وارد کنید"></textarea>
                </div>
                <div class="nav-buttons">
                    <div></div> <!-- Empty div for spacing -->
                    <button class="next-btn" onclick="nextStep(1)">بعدی</button>
                </div>
            </div>
            
            <div id="addStep2" class="add-step">
                <div class="form-field">
                    <label>شماره موبایل</label>
                    <input type="tel" id="locPhoneInput" placeholder="09xxxxxxxxx">
                </div>
                <div class="form-field">
                    <label>شیفت صبحگاهی</label>
                    <input type="text" id="morningShift" placeholder="مثال: 8:00 تا 14:00">
                </div>
                <div class="form-field">
                    <label>شیفت عصرگاهی</label>
                    <input type="text" id="eveningShift" placeholder="مثال: 14:00 تا 22:00">
                </div>
                <div class="form-field">
                    <label>توضیحات</label>
                    <textarea id="locDescInput" placeholder="توضیحات را وارد کنید"></textarea>
                </div>
                <div class="form-field">
                    <label>دسته</label>
                    <select id="categorySelect" onchange="loadSubcategories()">
                        <option value="">انتخاب دسته</option>
                        {% for cat in categories.keys() %}
                        <option value="{{ cat }}">{{ cat }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-field" id="subcategoryField" style="display: none;">
                    <label>زیر دسته</label>
                    <select id="subcategorySelect">
                        <option value="">انتخاب زیر دسته</option>
                    </select>
                </div>
                <div class="nav-buttons">
                    <div class="back-btn" onclick="prevStep(2)">برگشت</div>
                    <div class="next-btn" onclick="nextStep(2)">بعدی</div>
                </div>
            </div>
            
            <div id="addStep3" class="add-step">
                <div class="form-field">
                    <label class="required">نام کاربری مالک</label>
                    <input type="text" id="locOwnerInput" placeholder="نام کاربری مالک مکان را وارد کنید">
                </div>
                <div class="nav-buttons">
                    <div class="back-btn" onclick="prevStep(3)">برگشت</div>
                    <div class="submit-btn" onclick="submitLocation()">ثبت</div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="editLocationSection" class="content-section">
        <span class="back-arrow" onclick="showMyLocations()">⬅️</span>
        <h3>ویرایش مکان</h3>
        <!-- Similar to add section but pre-filled -->
        <div class="add-container">
            <!-- ... (duplicate add steps with pre-fill logic in JS) ... -->
        </div>
    </div>
    
    <div id="profileSection" class="content-section">
        <div class="profile-card">
            <h3>پروفایل کاربری</h3>
            <div class="profile-item">
                <div class="profile-label">نام کاربری</div>
                <div class="profile-value" id="profileUsername">{{ username }}</div>
                <div class="edit-form" id="usernameForm">
                    <input type="text" id="newUsername" placeholder="نام کاربری جدید">
                    <div class="form-actions">
                        <button class="cancel-btn" onclick="toggleEditForm('usernameForm')">لغو</button>
                        <button class="save-btn" onclick="updateUsername()">ذخیره</button>
                    </div>
                </div>
            </div>
            <div class="profile-item">
                <div class="profile-label">شهر</div>
                <div class="profile-value" id="profileCity">{{ user_city }}</div>
                <div class="edit-form" id="cityForm">
                    <select id="newCity">
                        {% for city in cities %}
                        <option value="{{ city }}" {% if city == user_city %}selected{% endif %}>{{ city }}</option>
                        {% endfor %}
                    </select>
                    <div class="form-actions">
                        <button class="cancel-btn" onclick="toggleEditForm('cityForm')">لغو</button>
                        <button class="save-btn" onclick="updateCity()">ذخیره</button>
                    </div>
                </div>
            </div>
            <div class="profile-item">
                <div class="profile-label">تلفن همراه</div>
                <div class="profile-value" id="profilePhone">{{ user_phone }}</div>
                <div class="edit-form" id="phoneForm">
                    <input type="tel" id="newPhone" placeholder="09xxxxxxxxx" value="{{ user_phone }}">
                    <div class="form-actions">
                        <button class="cancel-btn" onclick="toggleEditForm('phoneForm')">لغو</button>
                        <button class="save-btn" onclick="updatePhone()">ذخیره</button>
                    </div>
                </div>
            </div>
            <div class="profile-actions">
                <button class="action-button" onclick="toggleEditForm('usernameForm')">ویرایش نام کاربری</button>
                <button class="action-button" onclick="toggleEditForm('cityForm')">ویرایش شهر</button>
                <button class="action-button" onclick="toggleEditForm('phoneForm')">ویرایش تلفن</button>
                <button class="action-button" onclick="showChangePasswordForm()">تغییر رمز عبور</button>
                <button class="action-button" onclick="showMyLocations()">مکان های من</button>
                <button class="action-button" onclick="logout()">خروج از حساب</button>
            </div>
            <div class="edit-form" id="passwordForm">
                <input type="password" id="newPassword" placeholder="رمز عبور جدید" class="form-control">
                <input type="password" id="confirmNewPassword" placeholder="تکرار رمز عبور" class="form-control" style="margin-top: 10px;">
                <div class="form-actions">
                    <button class="cancel-btn" onclick="toggleEditForm('passwordForm')">لغو</button>
                    <button class="save-btn" onclick="updatePassword()">ذخیره</button>
                </div>
            </div>
        </div>
    </div>
    
    <div id="chatSection" class="content-section">
        <h3>چت</h3>
        <div class="chat-list" id="chatList"></div>
    </div>
    
    <div id="chatRoomSection" class="content-section">
        <span class="back-arrow" onclick="showSection('chatSection', document.querySelector('.nav-item[onclick*=\"chatSection\"]'))">⬅️</span>
        <h3 id="chatUserTitle"></h3>
        <div class="chat-messages" id="chatMessages"></div>
        <div class="chat-input">
            <input type="text" id="chatInput" placeholder="پیام خود را بنویسید...">
            <button class="chat-send-btn" onclick="sendMessage()">ارسال</button>
        </div>
    </div>
    
    <div id="notificationsSection" class="content-section">
        <span class="back-arrow" onclick="backFromNotifications()">⬅️</span>
        <h3>اعلان‌ها</h3>
        <div class="notifications-list" id="notificationsList"></div>
    </div>
    
    <div class="bottom-nav">
        <div class="nav-item" onclick="showSection('profileSection', this)">
            <div class="nav-icon">👤</div>
            <div class="nav-text">پروفایل</div>
        </div>
        <div class="nav-item" onclick="showSection('chatSection', this)">
            <div class="nav-icon">💬</div>
            <div class="nav-text">چت</div>
        </div>
        <div class="nav-item active" onclick="showSection('homeSection', this)">
            <div class="nav-icon">🏠</div>
            <div class="nav-text">صفحه اصلی</div>
        </div>
        <div class="nav-item" onclick="showSection('addSection', this)">
            <div class="nav-icon">➕</div>
            <div class="nav-text">اضافه کردن</div>
        </div>
    </div>
    
""" + CUSTOM_ALERT_HTML + """
    <script>
        let currentSection = 'homeSection';
        let previousSection = '';
        let addStep = 1;
        let photos = [];
        let mainPhotoIndex = 0;
        let currentLocationId = '';
        let isMyLocation = false;
        let rating = 0;
        let chatPartner = '';
        
        function showSection(sectionId, element) {
            previousSection = currentSection;
            currentSection = sectionId;
            
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });
            document.getElementById(sectionId).classList.add('active');
            
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            if (element) {
                element.classList.add('active');
            }
        }
        
        function showLocationDetails(locationId) {
            fetch('/get_location/' + locationId)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const loc = data.location;
                    document.getElementById('locImage').style.backgroundImage = `url('/uploads/${loc.photos[loc.main_photo]}')`;
                    document.getElementById('locTitle').textContent = loc.title;
                    document.getElementById('locDesc').textContent = loc.description || 'بدون توضیح';
                    document.getElementById('locCity').textContent = loc.city;
                    document.getElementById('locAddress').textContent = loc.address;
                    
                    if (loc.phone) {
                        document.getElementById('locPhone').textContent = loc.phone;
                        document.getElementById('locPhoneField').style.display = 'block';
                    } else {
                        document.getElementById('locPhoneField').style.display = 'none';
                    }
                    
                    if (loc.morning_shift || loc.evening_shift) {
                        let shifts = '';
                        if (loc.morning_shift) shifts += `صبحگاهی: ${loc.morning_shift}`;
                        if (loc.evening_shift) shifts += ` | عصرگاهی: ${loc.evening_shift}`;
                        document.getElementById('locShifts').textContent = shifts;
                        document.getElementById('locShiftsField').style.display = 'block';
                    } else {
                        document.getElementById('locShiftsField').style.display = 'none';
                    }
                    
                    document.getElementById('locCategory').textContent = loc.category || 'بدون دسته';
                    document.getElementById('locSubcategory').textContent = loc.subcategory || 'بدون زیر دسته';
                    
                    // تنظیم دکمه‌های عملیات
                    const actionsDiv = document.getElementById('locActions');
                    actionsDiv.innerHTML = '';
                    
                    const chatBtn = document.createElement('button');
                    chatBtn.className = 'action-btn chat-btn';
                    chatBtn.textContent = 'چت با مالک';
                    chatBtn.onclick = () => openChat(loc.owner);
                    actionsDiv.appendChild(chatBtn);
                    
                    // اگر کاربر مالک مکان باشد، دکمه ویرایش نمایش داده شود
                    if (loc.owner === '{{ username }}') {
                        const editBtn = document.createElement('button');
                        editBtn.className = 'action-btn edit-btn';
                        editBtn.textContent = 'ویرایش';
                        editBtn.onclick = () => editLocation(locationId);
                        actionsDiv.appendChild(editBtn);
                        isMyLocation = true;
                    } else {
                        isMyLocation = false;
                    }
                    
                    currentLocationId = locationId;
                    showSection('locationDetailSection');
                    loadComments(locationId);
                }
            });
        }
        
        function loadComments(locationId) {
            fetch('/get_comments/' + locationId)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const commentsList = document.getElementById('commentsList');
                    commentsList.innerHTML = '';
                    data.comments.forEach(comment => {
                        const commentDiv = document.createElement('div');
                        commentDiv.className = 'comment-item';
                        let stars = '';
                        for (let i = 0; i < comment.rating; i++) {
                            stars += '★';
                        }
                        commentDiv.innerHTML = `
                            <div class="comment-user">${comment.user}</div>
                            <div class="comment-stars">${stars}</div>
                            <div class="comment-text">${comment.text}</div>
                        `;
                        commentsList.appendChild(commentDiv);
                    });
                }
            });
        }
        
        function setRating(ratingValue) {
            rating = ratingValue;
            const stars = document.querySelectorAll('.star-rating .star');
            stars.forEach((star, index) => {
                if (index < ratingValue) {
                    star.classList.add('filled');
                } else {
                    star.classList.remove('filled');
                }
            });
        }
        
        function submitComment() {
            const text = document.getElementById('commentText').value;
            if (!text.trim() || rating === 0) {
                showCustomAlert('خطا', 'لطفاً نظر و امتیاز خود را وارد کنید');
                return;
            }
            
            const data = {
                location_id: currentLocationId,
                text: text,
                rating: rating
            };
            
            fetch('/add_comment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('commentText').value = '';
                    setRating(0);
                    loadComments(currentLocationId);
                    showCustomAlert('موفقیت', 'نظر شما ثبت شد');
                } else {
                    showCustomAlert('خطا', data.message);
                }
            });
        }
        
        function nextStep(step) {
            if (step === 1) {
                const title = document.getElementById('locTitleInput').value;
                const city = document.getElementById('locCitySelect').value;
                const address = document.getElementById('locAddressInput').value;
                
                if (!title || !city || !address) {
                    showCustomAlert('خطا', 'لطفاً تمام فیلدهای اجباری را پر کنید');
                    return;
                }
            }
            
            document.getElementById('addStep' + step).classList.remove('active');
            document.getElementById('addStep' + (step + 1)).classList.add('active');
            addStep = step + 1;
        }
        
        function prevStep(step) {
            document.getElementById('addStep' + step).classList.remove('active');
            document.getElementById('addStep' + (step - 1)).classList.add('active');
            addStep = step - 1;
        }
        
        function previewPhotos() {
            const files = document.getElementById('photoInput').files;
            const preview = document.getElementById('photoPreview');
            preview.innerHTML = '';
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                if (!file.type.match('image.*')) continue;
                
                const reader = new FileReader();
                reader.onload = (function(theFile, index) {
                    return function(e) {
                        const div = document.createElement('div');
                        div.className = 'preview-item';
                        div.innerHTML = `
                            <img src="${e.target.result}" alt="Preview">
                            <button class="remove-photo" onclick="removePhoto(${index})">×</button>
                            <button class="set-main-photo" onclick="setMainPhoto(${index})">M</button>
                            ${index === mainPhotoIndex ? '<div class="main-photo-indicator">اصلی</div>' : ''}
                        `;
                        preview.appendChild(div);
                    };
                })(file, i);
                
                reader.readAsDataURL(file);
                photos.push(file);
            }
        }
        
        function removePhoto(index) {
            photos.splice(index, 1);
            if (mainPhotoIndex >= photos.length) {
                mainPhotoIndex = photos.length - 1;
            }
            previewPhotos();
        }
        
        function setMainPhoto(index) {
            mainPhotoIndex = index;
            previewPhotos();
        }
        
        function loadSubcategories() {
            const category = document.getElementById('categorySelect').value;
            const subcategoryField = document.getElementById('subcategoryField');
            const subcategorySelect = document.getElementById('subcategorySelect');
            
            if (category) {
                subcategoryField.style.display = 'block';
                subcategorySelect.innerHTML = '<option value="">انتخاب زیر دسته</option>';
                
                const subcategories = {
                    {% for cat, subs in categories.items() %}
                    "{{ cat }}": [
                        {% for sub in subs %}
                        "{{ sub }}",
                        {% endfor %}
                    ],
                    {% endfor %}
                };
                
                subcategories[category].forEach(sub => {
                    const option = document.createElement('option');
                    option.value = sub;
                    option.textContent = sub;
                    subcategorySelect.appendChild(option);
                });
            } else {
                subcategoryField.style.display = 'none';
            }
        }
        
        function submitLocation() {
            const title = document.getElementById('locTitleInput').value;
            const city = document.getElementById('locCitySelect').value;
            const address = document.getElementById('locAddressInput').value;
            const phone = document.getElementById('locPhoneInput').value;
            const morning_shift = document.getElementById('morningShift').value;
            const evening_shift = document.getElementById('eveningShift').value;
            const description = document.getElementById('locDescInput').value;
            const category = document.getElementById('categorySelect').value;
            const subcategory = document.getElementById('subcategorySelect').value;
            const owner = document.getElementById('locOwnerInput').value;
            
            if (!title || !city || !address || !owner) {
                showCustomAlert('خطا', 'لطفاً تمام فیلدهای اجباری را پر کنید');
                return;
            }
            
            const formData = new FormData();
            formData.append('title', title);
            formData.append('city', city);
            formData.append('address', address);
            formData.append('phone', phone);
            formData.append('morning_shift', morning_shift);
            formData.append('evening_shift', evening_shift);
            formData.append('description', description);
            formData.append('category', category);
            formData.append('subcategory', subcategory);
            formData.append('owner', owner);
            formData.append('main_photo', mainPhotoIndex.toString());
            
            for (let i = 0; i < photos.length; i++) {
                formData.append('photos', photos[i]);
            }
            
            fetch('/add_location', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showCustomAlert('موفقیت', 'مکان ثبت شد', "showSection('homeSection', document.querySelector('.nav-item[onclick*=\"homeSection\"]'))");
                    resetAddForm();
                } else {
                    showCustomAlert('خطا', data.message);
                }
            });
        }
        
        function resetAddForm() {
            document.getElementById('addStep' + addStep).classList.remove('active');
            document.getElementById('addStep1').classList.add('active');
            addStep = 1;
            
            document.getElementById('photoInput').value = '';
            document.getElementById('photoPreview').innerHTML = '';
            document.getElementById('locTitleInput').value = '';
            document.getElementById('locCitySelect').value = '';
            document.getElementById('locAddressInput').value = '';
            document.getElementById('locPhoneInput').value = '';
            document.getElementById('morningShift').value = '';
            document.getElementById('eveningShift').value = '';
            document.getElementById('locDescInput').value = '';
            document.getElementById('categorySelect').value = '';
            document.getElementById('subcategorySelect').innerHTML = '<option value="">انتخاب زیر دسته</option>';
            document.getElementById('subcategoryField').style.display = 'none';
            document.getElementById('locOwnerInput').value = '';
            
            photos = [];
            mainPhotoIndex = 0;
        }
        
        function toggleEditForm(formId) {
            const form = document.getElementById(formId);
            if (form.style.display === 'block') {
                form.style.display = 'none';
            } else {
                // مخفی کردن سایر فرم‌ها
                document.querySelectorAll('.edit-form').forEach(f => {
                    f.style.display = 'none';
                });
                form.style.display = 'block';
            }
        }
        
        function showChangePasswordForm() {
            toggleEditForm('passwordForm');
        }
        
        function updateUsername() {
            const newUsername = document.getElementById('newUsername').value;
            if (!newUsername) {
                showCustomAlert('خطا', 'لطفاً نام کاربری جدید را وارد کنید');
                return;
            }
            
            fetch('/update_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field: 'username', value: newUsername })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('profileUsername').textContent = newUsername;
                    document.getElementById('newUsername').value = '';
                    toggleEditForm('usernameForm');
                    showCustomAlert('موفقیت', 'نام کاربری با موفقیت تغییر کرد');
                } else {
                    showCustomAlert('خطا', data.message);
                }
            });
        }
        
        function updateCity() {
            const newCity = document.getElementById('newCity').value;
            fetch('/update_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field: 'city', value: newCity })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('profileCity').textContent = newCity;
                    toggleEditForm('cityForm');
                    showCustomAlert('موفقیت', 'شهر با موفقیت تغییر کرد');
                } else {
                    showCustomAlert('خطا', data.message);
                }
            });
        }
        
        function updatePhone() {
            const newPhone = document.getElementById('newPhone').value;
            const phoneRegex = /^09\d{9}$/;
            if (!phoneRegex.test(newPhone)) {
                showCustomAlert('خطا', 'لطفاً شماره تلفن معتبر وارد کنید');
                return;
            }
            
            fetch('/update_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field: 'phone', value: newPhone })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('profilePhone').textContent = newPhone;
                    document.getElementById('newPhone').value = '';
                    toggleEditForm('phoneForm');
                    showCustomAlert('موفقیت', 'شماره تلفن با موفقیت تغییر کرد');
                } else {
                    showCustomAlert('خطا', data.message);
                }
            });
        }
        
        function updatePassword() {
            const newPassword = document.getElementById('newPassword').value;
            const confirmNewPassword = document.getElementById('confirmNewPassword').value;
            
            if (newPassword.length < 6) {
                showCustomAlert('خطا', 'رمز عبور باید حداقل ۶ کاراکتر داشته باشد');
                return;
            }
            
            if (newPassword !== confirmNewPassword) {
                showCustomAlert('خطا', 'رمزهای عبور مطابقت ندارند');
                return;
            }
            
            fetch('/update_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field: 'password', value: newPassword })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('newPassword').value = '';
                    document.getElementById('confirmNewPassword').value = '';
                    toggleEditForm('passwordForm');
                    showCustomAlert('موفقیت', 'رمز عبور با موفقیت تغییر کرد');
                } else {
                    showCustomAlert('خطا', data.message);
                }
            });
        }
        
        function showMyLocations() {
            fetch('/my_locations')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // نمایش مکان‌های کاربر
                    // این قسمت نیاز به پیاده‌سازی بیشتری دارد
                    showCustomAlert('اطلاعات', 'این بخش در حال توسعه است');
                }
            });
        }
        
        function logout() {
            fetch('/logout', { method: 'POST' })
            .then(() => {
                window.location.href = '/';
            });
        }
        
        function openChat(partner) {
            chatPartner = partner;
            document.getElementById('chatUserTitle').textContent = `چت با ${partner}`;
            showSection('chatRoomSection');
            loadChatMessages(partner);
        }
        
        function loadChatMessages(partner) {
            fetch('/get_chat/' + partner)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const messagesDiv = document.getElementById('chatMessages');
                    messagesDiv.innerHTML = '';
                    data.messages.forEach(msg => {
                        const messageDiv = document.createElement('div');
                        messageDiv.className = `message ${msg.sender === '{{ username }}' ? 'sent' : 'received'}`;
                        messageDiv.innerHTML = `
                            <div class="message-content">${msg.text}</div>
                            <div class="message-time">${new Date(msg.timestamp).toLocaleTimeString('fa-IR')}</div>
                        `;
                        messagesDiv.appendChild(messageDiv);
                    });
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            });
        }
        
        function sendMessage() {
            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if (!text) return;
            
            const data = {
                partner: chatPartner,
                text: text
            };
            
            fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    input.value = '';
                    loadChatMessages(chatPartner);
                }
            });
        }
        
        function editLocation(locationId) {
            // پیاده‌سازی ویرایش مکان
            showCustomAlert('اطلاعات', 'این بخش در حال توسعه است');
        }
        
        // نمایش پنجره هشدار سفارشی
        function showCustomAlert(title, message, callback) {
            document.getElementById('alertTitle').textContent = title;
            document.getElementById('alertMessage').textContent = message;
            document.getElementById('customAlert').style.display = 'flex';
            
            // تنظیم کال‌بک برای دکمه تایید
            document.querySelector('.alert-btn').onclick = function() {
                hideCustomAlert();
                if (callback && typeof callback === 'string') {
                    eval(callback);
                } else if (callback && typeof callback === 'function') {
                    callback();
                }
            };
        }
        
        // مخفی کردن پنجره هشدار سفارشی
        function hideCustomAlert() {
            document.getElementById('customAlert').style.display = 'none';
        }
        
        // بارگذاری اولیه داده‌ها
        document.addEventListener('DOMContentLoaded', function() {
            // بارگذاری لیست چت‌ها
            fetch('/get_chats')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const chatList = document.getElementById('chatList');
                    chatList.innerHTML = '';
                    data.chats.forEach(chat => {
                        const chatDiv = document.createElement('div');
                        chatDiv.className = 'chat-item';
                        chatDiv.innerHTML = `
                            <div class="chat-user">${chat.partner}</div>
                            <div class="chat-last-message">${chat.last_message || 'بدون پیام'}</div>
                        `;
                        chatDiv.onclick = () => openChat(chat.partner);
                        chatList.appendChild(chatDiv);
                    });
                }
            });
            
            // بارگذاری اعلان‌ها
            fetch('/get_notifications')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const notificationsList = document.getElementById('notificationsList');
                    notificationsList.innerHTML = '';
                    data.notifications.forEach(notification => {
                        const notifDiv = document.createElement('div');
                        notifDiv.className = 'notification-item';
                        notifDiv.innerHTML = `
                            <div class="notification-title">${notification.title}</div>
                            <div class="notification-message">${notification.message}</div>
                            <div class="notification-time">${new Date(notification.timestamp).toLocaleString('fa-IR')}</div>
                        `;
                        notificationsList.appendChild(notifDiv);
                    });
                }
            });
        });
    </script>
</body>
</html>"""

# توابع کمکی برای کار با فایل‌های JSON
def load_data(filename):
    """بارگذاری داده‌ها از فایل JSON"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_data(filename, data):
    """ذخیره داده‌ها در فایل JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def find_user(username=None, phone=None):
    """پیدا کردن کاربر بر اساس نام کاربری یا شماره تلفن"""
    users = load_data(USERS_FILE)
    for user in users:
        if (username and user.get('username') == username) or (phone and user.get('phone') == phone):
            return user
    return None

def validate_phone(phone):
    """اعتبارسنجی شماره تلفن"""
    return re.match(r'^09\d{9}$', phone) is not None

def validate_password(password):
    """اعتبارسنجی رمز عبور"""
    return len(password) >= 6

# مسیرهای اپلیکیشن
@app.route('/')
def register():
    """صفحه ثبت نام"""
    return REGISTER_HTML.replace('{% for city in cities %}', ''.join([f'<option value="{city}">{city}</option>' for city in CITIES])).replace('{% endfor %}', '')

@app.route('/register', methods=['POST'])
def register_user():
    """ثبت نام کاربر"""
    data = request.get_json()
    username = data.get('username')
    city = data.get('city')
    phone = data.get('phone')
    password = data.get('password')
    
    # اعتبارسنجی داده‌ها
    if not username or len(username) < 3:
        return jsonify({'success': False, 'message': 'نام کاربری باید حداقل ۳ کاراکتر باشد'})
    
    if not city:
        return jsonify({'success': False, 'message': 'لطفاً شهر خود را انتخاب کنید'})
    
    if not validate_phone(phone):
        return jsonify({'success': False, 'message': 'لطفاً شماره تلفن معتبر وارد کنید'})
    
    if not validate_password(password):
        return jsonify({'success': False, 'message': 'رمز عبور باید حداقل ۶ کاراکتر داشته باشد'})
    
    # بررسی تکراری بودن نام کاربری یا شماره تلفن
    if find_user(username=username):
        return jsonify({'success': False, 'message': 'نام کاربری تکراری است'})
    
    if find_user(phone=phone):
        return jsonify({'success': False, 'message': 'شماره تلفن تکراری است'})
    
    # ایجاد کاربر جدید
    users = load_data(USERS_FILE)
    new_user = {
        'id': str(uuid.uuid4()),
        'username': username,
        'city': city,
        'phone': phone,
        'password': password,  # در یک اپلیکیشن واقعی باید رمز عبور هش شود
        'timestamp': data.get('timestamp')
    }
    users.append(new_user)
    save_data(USERS_FILE, users)
    
    return jsonify({'success': True, 'user': new_user, 'message': 'ثبت نام با موفقیت انجام شد'})

@app.route('/login')
def login():
    """صفحه ورود"""
    return LOGIN_HTML

@app.route('/login', methods=['POST'])
def login_user():
    """ورود کاربر"""
    data = request.get_json()
    username_or_phone = data.get('username')
    password = data.get('password')
    
    # پیدا کردن کاربر
    user = find_user(username=username_or_phone) or find_user(phone=username_or_phone)
    
    if user and user.get('password') == password:  # در یک اپلیکیشن واقعی باید رمز عبور مقایسه شود
        return jsonify({'success': True, 'user': user, 'message': 'ورود با موفقیت انجام شد'})
    else:
        return jsonify({'success': False, 'message': 'نام کاربری/تلفن یا رمز عبور اشتباه است'})

@app.route('/main')
def main_page():
    """صفحه اصلی اپلیکیشن"""
    username = request.args.get('username')
    if not username:
        return "خطا: نام کاربری مشخص نشده است"
    
    user = find_user(username=username)
    if not user:
        return "خطا: کاربر یافت نشد"
    
    # بارگذاری مکان‌ها
    locations = load_data(LOCATIONS_FILE)
    
    # جایگزین کردن متغیرهای تمپلیت
    html = MAIN_HTML.replace('{{ username }}', username)
    html = html.replace('{{ user_city }}', user.get('city', ''))
    html = html.replace('{{ user_phone }}', user.get('phone', ''))
    
    # جایگزین کردن لیست شهرها
    cities_options = ''.join([f'<option value="{city}">{city}</option>' for city in CITIES])
    html = html.replace('{% for city in cities %}', cities_options).replace('{% endfor %}', '')
    
    # جایگزین کردن دسته‌بندی‌ها
    categories_html = ''
    for cat, subs in CATEGORIES.items():
        categories_html += f'"{cat}": ['
        for sub in subs:
            categories_html += f'"{sub}",'
        categories_html += '],'
    html = html.replace('{% for cat, subs in categories.items() %}', '').replace('{% endfor %}', categories_html)
    
    # جایگزین کردن مکان‌ها
    locations_html = ''
    for loc in locations:
        locations_html += f'''
        <div class="location-tile" onclick="showLocationDetails('{loc["id"]}')">
            <div class="location-image" style="background-image: url('/uploads/{loc["photos"][0]}');"></div>
            <div class="location-info">
                <div class="location-title">{loc["title"]}</div>
                <div class="location-city">{loc["city"]}</div>
            </div>
        </div>
        '''
    html = html.replace('{% for loc in all_locations %}', locations_html).replace('{% endfor %}', '')
    
    return html

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """سرو کردن فایل‌های آپلود شده"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/add_location', methods=['POST'])
def add_location():
    """افزودن مکان جدید"""
    try:
        # دریافت داده‌ها از فرم
        title = request.form.get('title')
        city = request.form.get('city')
        address = request.form.get('address')
        phone = request.form.get('phone')
        morning_shift = request.form.get('morning_shift')
        evening_shift = request.form.get('evening_shift')
        description = request.form.get('description')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        owner = request.form.get('owner')
        main_photo = int(request.form.get('main_photo', 0))
        
        # اعتبارسنجی داده‌های اجباری
        if not title or not city or not address or not owner:
            return jsonify({'success': False, 'message': 'لطفاً تمام فیلدهای اجباری را پر کنید'})
        
        # ذخیره عکس‌ها
        photos = []
        photo_files = request.files.getlist('photos')
        for i, photo in enumerate(photo_files):
            if photo and photo.filename:
                filename = f"{uuid.uuid4()}_{photo.filename}"
                photo.save(os.path.join(UPLOAD_FOLDER, filename))
                photos.append(filename)
        
        if not photos:
            return jsonify({'success': False, 'message': 'لطفاً حداقل یک عکس آپلود کنید'})
        
        # ایجاد مکان جدید
        locations = load_data(LOCATIONS_FILE)
        new_location = {
            'id': str(uuid.uuid4()),
            'title': title,
            'city': city,
            'address': address,
            'phone': phone,
            'morning_shift': morning_shift,
            'evening_shift': evening_shift,
            'description': description,
            'category': category,
            'subcategory': subcategory,
            'owner': owner,
            'photos': photos,
            'main_photo': main_photo,
            'timestamp': datetime.now().isoformat()
        }
        locations.append(new_location)
        save_data(LOCATIONS_FILE, locations)
        
        # ایجاد اعلان برای کاربران هم‌شهری
        notifications = load_data(NOTIFICATIONS_FILE)
        users = load_data(USERS_FILE)
        for user in users:
            if user.get('city') == city and user.get('username') != owner:
                notifications.append({
                    'id': str(uuid.uuid4()),
                    'user': user.get('username'),
                    'title': 'مکان جدید',
                    'message': f'مکان جدید "{title}" در شهر شما ثبت شد',
                    'timestamp': datetime.now().isoformat()
                })
        save_data(NOTIFICATIONS_FILE, notifications)
        
        return jsonify({'success': True, 'message': 'مکان با موفقیت ثبت شد'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطا در ثبت مکان: {str(e)}'})

@app.route('/get_location/<location_id>')
def get_location(location_id):
    """دریافت اطلاعات یک مکان"""
    locations = load_data(LOCATIONS_FILE)
    location = next((loc for loc in locations if loc['id'] == location_id), None)
    if location:
        return jsonify({'success': True, 'location': location})
    else:
        return jsonify({'success': False, 'message': 'مکان یافت نشد'})

@app.route('/add_comment', methods=['POST'])
def add_comment():
    """افزودن نظر به مکان"""
    data = request.get_json()
    location_id = data.get('location_id')
    text = data.get('text')
    rating = data.get('rating')
    user = request.args.get('username')  # در یک اپلیکیشن واقعی باید از سشن استفاده شود
    
    if not location_id or not text or not rating or not user:
        return jsonify({'success': False, 'message': 'لطفاً تمام فیلدها را پر کنید'})
    
    comments = load_data(COMMENTS_FILE)
    new_comment = {
        'id': str(uuid.uuid4()),
        'location_id': location_id,
        'user': user,
        'text': text,
        'rating': rating,
        'timestamp': datetime.now().isoformat()
    }
    comments.append(new_comment)
    save_data(COMMENTS_FILE, comments)
    
    return jsonify({'success': True, 'message': 'نظر با موفقیت ثبت شد'})

@app.route('/get_comments/<location_id>')
def get_comments(location_id):
    """دریافت نظرات یک مکان"""
    comments = load_data(COMMENTS_FILE)
    location_comments = [comment for comment in comments if comment['location_id'] == location_id]
    return jsonify({'success': True, 'comments': location_comments})

@app.route('/get_chats')
def get_chats():
    """دریافت لیست چت‌ها"""
    user = request.args.get('username')  # در یک اپلیکیشن واقعی باید از سشن استفاده شود
    if not user:
        return jsonify({'success': False, 'message': 'کاربر مشخص نشده است'})
    
    chats = load_data(CHAT_FILE)
    user_chats = []
    partners = set()
    
    # پیدا کردن همه چت‌های کاربر
    for chat in chats:
        if chat['sender'] == user or chat['receiver'] == user:
            partner = chat['receiver'] if chat['sender'] == user else chat['sender']
            if partner not in partners:
                partners.add(partner)
                user_chats.append({
                    'partner': partner,
                    'last_message': chat['text']
                })
    
    return jsonify({'success': True, 'chats': user_chats})

@app.route('/get_chat/<partner>')
def get_chat(partner):
    """دریافت پیام‌های یک چت خاص"""
    user = request.args.get('username')  # در یک اپلیکیشن واقعی باید از سشن استفاده شود
    if not user:
        return jsonify({'success': False, 'message': 'کاربر مشخص نشده است'})
    
    chats = load_data(CHAT_FILE)
    chat_messages = [chat for chat in chats if 
                     (chat['sender'] == user and chat['receiver'] == partner) or 
                     (chat['sender'] == partner and chat['receiver'] == user)]
    
    # مرتب‌سازی پیام‌ها بر اساس زمان
    chat_messages.sort(key=lambda x: x['timestamp'])
    
    return jsonify({'success': True, 'messages': chat_messages})

@app.route('/send_message', methods=['POST'])
def send_message():
    """ارسال پیام در چت"""
    data = request.get_json()
    partner = data.get('partner')
    text = data.get('text')
    sender = request.args.get('username')  # در یک اپلیکیشن واقعی باید از سشن استفاده شود
    
    if not partner or not text or not sender:
        return jsonify({'success': False, 'message': 'لطفاً تمام فیلدها را پر کنید'})
    
    chats = load_data(CHAT_FILE)
    new_message = {
        'id': str(uuid.uuid4()),
        'sender': sender,
        'receiver': partner,
        'text': text,
        'timestamp': datetime.now().isoformat()
    }
    chats.append(new_message)
    save_data(CHAT_FILE, chats)
    
    return jsonify({'success': True, 'message': 'پیام با موفقیت ارسال شد'})

@app.route('/get_notifications')
def get_notifications():
    """دریافت اعلان‌ها"""
    user = request.args.get('username')  # در یک اپلیکیشن واقعی باید از سشن استفاده شود
    if not user:
        return jsonify({'success': False, 'message': 'کاربر مشخص نشده است'})
    
    notifications = load_data(NOTIFICATIONS_FILE)
    user_notifications = [notif for notif in notifications if notif['user'] == user]
    
    # مرتب‌سازی اعلان‌ها بر اساس زمان (جدیدترین اول)
    user_notifications.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({'success': True, 'notifications': user_notifications})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    """بروزرسانی پروفایل کاربر"""
    data = request.get_json()
    field = data.get('field')
    value = data.get('value')
    username = request.args.get('username')  # در یک اپلیکیشن واقعی باید از سشن استفاده شود
    
    if not field or not value or not username:
        return jsonify({'success': False, 'message': 'لطفاً تمام فیلدها را پر کنید'})
    
    users = load_data(USERS_FILE)
    user_index = next((i for i, user in enumerate(users) if user['username'] == username), None)
    
    if user_index is None:
        return jsonify({'success': False, 'message': 'کاربر یافت نشد'})
    
    # اعتبارسنجی بر اساس فیلد
    if field == 'phone' and not validate_phone(value):
        return jsonify({'success': False, 'message': 'لطفاً شماره تلفن معتبر وارد کنید'})
    
    if field == 'password' and not validate_password(value):
        return jsonify({'success': False, 'message': 'رمز عبور باید حداقل ۶ کاراکتر داشته باشد'})
    
    # در یک اپلیکیشن واقعی باید بررسی تکراری بودن نام کاربری و شماره تلفن انجام شود
    
    users[user_index][field] = value
    save_data(USERS_FILE, users)
    
    return jsonify({'success': True, 'message': 'پروفایل با موفقیت بروزرسانی شد'})

@app.route('/logout', methods=['POST'])
def logout():
    """خروج از حساب کاربری"""
    # در یک اپلیکیشن واقعی باید سشن پاک شود
    return jsonify({'success': True, 'message': 'خروج از حساب با موفقیت انجام شد'})

@app.route('/my_locations')
def my_locations():
    """دریافت مکان‌های ثبت شده توسط کاربر"""
    username = request.args.get('username')  # در یک اپلیکیشن واقعی باید از سشن استفاده شود
    if not username:
        return jsonify({'success': False, 'message': 'کاربر مشخص نشده است'})
    
    locations = load_data(LOCATIONS_FILE)
    user_locations = [loc for loc in locations if loc['owner'] == username]
    
    return jsonify({'success': True, 'locations': user_locations})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)