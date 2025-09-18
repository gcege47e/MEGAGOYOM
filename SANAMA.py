from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, leave_room, emit
import datetime
import base64
import os

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///places.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Data lists
CITIES = [
    "شهرک صدرا", "شهرک گلستان", "معالی آباد", "شهرک کشن", "شهرک مهدیه",
    "شهرک زینبیه", "شهرک بعثت", "شهرک والفجر", "شهرک صنعتی عفیف آباد",
    "کوی امام رضا", "شهرک گویم", "شهرک بزین", "شهرک رحمت آباد", "شهرک خورشید",
    "شهرک سلامت", "شهرک فرهنگیان", "کوی زاگرس", "کوی پاسداران", "شهرک عرفان",
    "شهرک هنرستان"
]

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
        "شرکت‌های حمل و نقل و باربری (حمل و نقل، باربری)",
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
        "مراکز خدمات برندینگ و هویت‌سازی",
        "خدمات مشاوره انرژی و بهینه‌سازی"
    ],
    "🧰 خدمات تخصصی و فنی": [
        "تعمیرگاه لوازم خانگی (تعمیر لوازم، سرویس)",
        "تعمیرگاه موبایل و کامپیوتر (تعمیر موبایل، کامپیوتر)",
        "خدمات برق ساختمان (برق‌کاری، سیم‌کشی)",
        "خدمات لوله‌کشی و تاسیسات (لوله‌کشی، تاسیسات)",
        "خدمات نقاشی ساختمان (نقاشی ساختمان، رنگ‌کاری)",
        "خدمات کابینت‌سازی و نجاری (کابینت‌سازی، نجاری)",
        "خدمات آهنگری و جوشکاری (آهنگری، جوشکاری)",
        "خدمات کلیدسازی و قفل‌سازی (کلیدسازی، قفل‌سازی)",
        "خدمات شیشه‌بری و آینه‌کاری (شیشه‌بری، آینه‌کاری)",
        "خدمات فرش‌شویی و مبل‌شویی (فرش‌شویی، مبل‌شویی)",
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

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    places = db.relationship('Place', backref='owner', lazy=True)

class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.String(300), nullable=False)
    mobile = db.Column(db.String(20), nullable=True)
    morning_shift = db.Column(db.String(50), nullable=True)
    evening_shift = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ratings = db.relationship('Rating', backref='place', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Templates
base_template = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>گویم نما | GOYOM NAMA</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --navy-blue: #0a192f;
            --light-navy: #112240;
            --white: #e6f1ff;
            --light-blue: #64ffda;
            --dark-blue: #022c43;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Vazirmatn', Tahoma, sans-serif;
            background: linear-gradient(135deg, #0a192f 0%, #112240 100%);
            color: #e6f1ff;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        /* Navbar Styles */
        .navbar {
            background: rgba(10, 25, 47, 0.95) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(100, 255, 218, 0.1);
            padding: 1rem 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            animation: slideDown 0.8s ease-out;
        }
        
        .navbar-brand {
            font-weight: 700;
            font-size: 1.8rem;
            background: linear-gradient(45deg, #64ffda, #022c43);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 0 20px rgba(100, 255, 218, 0.3);
            animation: glow 2s ease-in-out infinite alternate;
        }
        
        .nav-link {
            color: #8892b0 !important;
            font-weight: 500;
            transition: all 0.3s ease;
            position: relative;
            padding: 0.5rem 1rem;
        }
        
        .nav-link:hover {
            color: #64ffda !important;
            transform: translateY(-2px);
        }
        
        .nav-link::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            width: 0;
            height: 2px;
            background: linear-gradient(90deg, #64ffda, #022c43);
            transition: all 0.3s ease;
            transform: translateX(-50%);
        }
        
        .nav-link:hover::after {
            width: 80%;
        }
        
        /* Container and Cards */
        .container {
            padding: 2rem 1rem;
            animation: fadeIn 1s ease-out;
        }
        
        .card {
            background: rgba(17, 34, 64, 0.7) !important;
            border: 1px solid rgba(100, 255, 218, 0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            margin-bottom: 1.5rem;
            overflow: hidden;
        }
        
        .card:hover {
            transform: translateY(-10px) scale(1.02);
            box-shadow: 0 15px 40px rgba(100, 255, 218, 0.2);
            border-color: rgba(100, 255, 218, 0.3);
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #64ffda, #022c43);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }
        
        .card:hover::before {
            transform: scaleX(1);
        }
        
        .card-body {
            padding: 1.5rem;
        }
        
        .card-title {
            color: #64ffda;
            font-weight: 600;
            margin-bottom: 1rem;
            font-size: 1.3rem;
            animation: slideInLeft 0.6s ease-out;
        }
        
        .card-text {
            color: #a8b2d1;
            line-height: 1.6;
            animation: slideInRight 0.6s ease-out;
        }
        
        /* Buttons */
        .btn {
            border-radius: 25px;
            padding: 0.7rem 1.5rem;
            font-weight: 500;
            transition: all 0.3s ease;
            border: none;
            position: relative;
            overflow: hidden;
            z-index: 1;
        }
        
        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 0;
            height: 100%;
            background: linear-gradient(45deg, #64ffda, #022c43);
            transition: all 0.5s ease;
            z-index: -1;
        }
        
        .btn:hover::before {
            width: 100%;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #022c43, #112240);
            color: #64ffda !important;
            border: 1px solid rgba(100, 255, 218, 0.3);
        }
        
        .btn-primary:hover {
            color: #0a192f !important;
            box-shadow: 0 5px 15px rgba(100, 255, 218, 0.4);
            transform: translateY(-2px);
        }
        
        .btn-success {
            background: linear-gradient(45deg, #022c43, #112240);
            color: #64ffda !important;
            border: 1px solid rgba(100, 255, 218, 0.3);
        }
        
        .btn-success:hover {
            color: #0a192f !important;
            box-shadow: 0 5px 15px rgba(100, 255, 218, 0.4);
            transform: translateY(-2px);
        }
        
        .btn-outline-primary {
            border: 1px solid rgba(100, 255, 218, 0.5);
            color: #64ffda;
        }
        
        .btn-outline-primary:hover {
            background: linear-gradient(45deg, #64ffda, #022c43);
            color: #0a192f !important;
            border-color: transparent;
            transform: translateY(-2px);
        }
        
        /* Forms */
        .form-control, .form-select {
            background: rgba(10, 25, 47, 0.5) !important;
            border: 1px solid rgba(100, 255, 218, 0.2) !important;
            color: #e6f1ff !important;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            transition: all 0.3s ease;
        }
        
        .form-control:focus, .form-select:focus {
            background: rgba(17, 34, 64, 0.7) !important;
            border-color: #64ffda !important;
            box-shadow: 0 0 0 0.25rem rgba(100, 255, 218, 0.25) !important;
            color: #64ffda !important;
        }
        
        .form-label {
            color: #8892b0;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        /* Alerts */
        .alert {
            border-radius: 10px;
            border: none;
            backdrop-filter: blur(10px);
            animation: slideInDown 0.5s ease-out;
        }
        
        .alert-success {
            background: rgba(100, 255, 218, 0.15) !important;
            border: 1px solid rgba(100, 255, 218, 0.3);
            color: #64ffda !important;
        }
        
        .alert-danger {
            background: rgba(255, 100, 100, 0.15) !important;
            border: 1px solid rgba(255, 100, 100, 0.3);
            color: #ff6464 !important;
        }
        
        /* Map Container */
        .map-container {
            height: 300px;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            margin-bottom: 2rem;
            border: 1px solid rgba(100, 255, 218, 0.1);
            animation: fadeInUp 1s ease-out;
        }
        
        .map-container iframe {
            width: 100%;
            height: 100%;
            border: none;
            filter: grayscale(50%) brightness(0.8);
            transition: filter 0.3s ease;
        }
        
        .map-container:hover iframe {
            filter: grayscale(0%) brightness(1);
        }
        
        /* Sidebar */
        .sidebar {
            background: rgba(17, 34, 64, 0.7);
            border-radius: 15px;
            padding: 2rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(100, 255, 218, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            animation: slideInLeft 0.8s ease-out;
        }
        
        .sidebar h5 {
            color: #64ffda;
            font-weight: 600;
            margin-bottom: 1.5rem;
            text-align: center;
            position: relative;
            padding-bottom: 0.5rem;
        }
        
        .sidebar h5::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 50px;
            height: 3px;
            background: linear-gradient(90deg, #64ffda, #022c43);
            border-radius: 2px;
        }
        
        .sidebar ul li a {
            color: #8892b0;
            text-decoration: none;
            padding: 0.5rem 1rem;
            display: block;
            border-radius: 8px;
            transition: all 0.3s ease;
            margin-bottom: 0.3rem;
        }
        
        .sidebar ul li a:hover {
            background: rgba(100, 255, 218, 0.1);
            color: #64ffda;
            transform: translateX(5px);
        }
        
        /* Pagination */
        .pagination {
            justify-content: center;
            margin: 2rem 0;
        }
        
        .page-link {
            background: rgba(17, 34, 64, 0.7);
            border: 1px solid rgba(100, 255, 218, 0.2);
            color: #8892b0;
            transition: all 0.3s ease;
        }
        
        .page-link:hover {
            background: rgba(100, 255, 218, 0.1);
            color: #64ffda;
            border-color: rgba(100, 255, 218, 0.3);
        }
        
        .page-item.active .page-link {
            background: linear-gradient(45deg, #64ffda, #022c43);
            border-color: #64ffda;
            color: #0a192f;
        }
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideDown {
            from {
                transform: translateY(-100%);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes slideInLeft {
            from {
                transform: translateX(-50px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideInRight {
            from {
                transform: translateX(50px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideInDown {
            from {
                transform: translateY(-20px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes fadeInUp {
            from {
                transform: translateY(30px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes glow {
            from {
                text-shadow: 0 0 5px rgba(100, 255, 218, 0.3);
            }
            to {
                text-shadow: 0 0 20px rgba(100, 255, 218, 0.6), 0 0 30px rgba(100, 255, 218, 0.4);
            }
        }
        
        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
            100% { transform: translateY(0px); }
        }
        
        /* Floating animation for cards */
        .floating {
            animation: float 3s ease-in-out infinite;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .navbar-brand {
                font-size: 1.5rem;
            }
            
            .card {
                margin-bottom: 1rem;
            }
            
            .sidebar {
                margin-bottom: 2rem;
            }
        }
        
        /* Loading spinner */
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(100, 255, 218, 0.3);
            border-top: 4px solid #64ffda;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 2rem auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Modal styles */
        .modal-content {
            background: rgba(10, 25, 47, 0.95) !important;
            border: 1px solid rgba(100, 255, 218, 0.2);
            backdrop-filter: blur(10px);
        }
        
        .modal-header {
            border-bottom: 1px solid rgba(100, 255, 218, 0.1);
        }
        
        .modal-title {
            color: #64ffda;
            font-weight: 600;
        }
        
        .btn-close {
            filter: invert(1) grayscale(100%) brightness(200%);
        }
        
        /* Chat messages */
        #chatMessages {
            max-height: 300px;
            overflow-y: auto;
        }
        
        #chatMessages div {
            background: rgba(17, 34, 64, 0.5);
            border-radius: 10px;
            padding: 0.8rem;
            margin-bottom: 0.5rem;
            animation: fadeIn 0.3s ease-out;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem;
            color: #8892b0;
            font-size: 0.9rem;
            border-top: 1px solid rgba(100, 255, 218, 0.1);
            margin-top: 2rem;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark sticky-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">گویم نما | GOYOM NAMA</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">خانه</a>
                    </li>
                    {% if current_user.is_authenticated %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('add_place') }}">افزودن مکان</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('profile') }}">پروفایل</a>
                    </li>
                    {% endif %}
                </ul>
                <ul class="navbar-nav">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item">
                        <span class="navbar-text">شهر: {{ current_user.city }}</span>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('logout') }}">خروج</a>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('login') }}">ورود</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('register') }}">ثبت‌نام</a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <div class="footer">
        <p>© 2024 گویم نما | GOYOM NAMA - پلتفرم جامع مکان‌های محلی</p>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

index_template = """
<div class="row">
    <div class="col-md-3">
        <div class="sidebar">
            <h5>دسته‌بندی‌ها</h5>
            <ul class="list-unstyled">
                {% for category, subcategories in CATEGORIES.items() %}
                <li>
                    <a href="{{ url_for('index', category=category.split()[0]) }}">{{ category }}</a>
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
    <div class="col-md-9">
        <div class="map-container">
            <iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d103916.6998339214!2d51.3372975!3d35.694373!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3f8e00491ff3dcd9%3A0xf0b3697c521a41e4!2sTehran%2C%20Tehran%20Province%2C%20Iran!5e0!3m2!1sen!2s!4v1620000000000!5m2!1sen!2s" allowfullscreen="" loading="lazy"></iframe>
        </div>

        <form method="GET" class="mb-4">
            <div class="row">
                <div class="col-md-4">
                    <input type="text" name="search" class="form-control" placeholder="جستجو..." value="{{ request.args.get('search', '') }}">
                </div>
                <div class="col-md-3">
                    <select name="category" class="form-select">
                        <option value="">همه دسته‌بندی‌ها</option>
                        {% for category, subcategories in CATEGORIES.items() %}
                        <option value="{{ category.split()[0] }}" {{ 'selected' if request.args.get('category') == category.split()[0] }}>{{ category }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-3">
                    <select name="city" class="form-select">
                        <option value="">همه شهرها</option>
                        {% for city in CITIES %}
                        <option value="{{ city }}" {{ 'selected' if request.args.get('city') == city }}>{{ city }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-primary w-100">جستجو</button>
                </div>
            </div>
            {% if current_user.is_authenticated %}
            <div class="mt-2">
                <a href="{{ url_for('index', only_my_city='true') }}" class="btn btn-outline-primary">فقط شهرکمون</a>
            </div>
            {% endif %}
        </form>

        <div class="row">
            {% for place in places %}
            <div class="col-md-6 col-lg-4">
                <div class="card floating">
                    <div class="card-body">
                        <h5 class="card-title">{{ place.title }}</h5>
                        <p class="card-text">{{ place.description[:100] }}...</p>
                        <p class="text-muted">
                            <i class="fas fa-map-marker-alt"></i> {{ place.city }} - {{ place.address[:30] }}...
                        </p>
                        <p class="text-muted">
                            <i class="fas fa-clock"></i> 
                            {% if place.morning_shift %}صبح: {{ place.morning_shift }}{% endif %}
                            {% if place.evening_shift %}عصر: {{ place.evening_shift }}{% endif %}
                        </p>
                        <a href="{{ url_for('place_detail', place_id=place.id) }}" class="btn btn-primary">مشاهده جزئیات</a>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- Pagination -->
        <nav aria-label="Page navigation">
            <ul class="pagination justify-content-center">
                {% if places.has_prev %}
                <li class="page-item">
                    <a class="page-link" href="{{ url_for('index', page=places.prev_num, **request.args) }}">قبلی</a>
                </li>
                {% endif %}
                {% for page_num in places.iter_pages() %}
                    {% if page_num %}
                        {% if page_num != places.page %}
                        <li class="page-item">
                            <a class="page-link" href="{{ url_for('index', page=page_num, **request.args) }}">{{ page_num }}</a>
                        </li>
                        {% else %}
                        <li class="page-item active">
                            <span class="page-link">{{ page_num }}</span>
                        </li>
                        {% endif %}
                    {% else %}
                    <li class="page-item disabled">
                        <span class="page-link">…</span>
                    </li>
                    {% endif %}
                {% endfor %}
                {% if places.has_next %}
                <li class="page-item">
                    <a class="page-link" href="{{ url_for('index', page=places.next_num, **request.args) }}">بعدی</a>
                </li>
                {% endif %}
            </ul>
        </nav>
    </div>
</div>
"""

register_template = """
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card floating">
            <div class="card-header">
                <h4 class="text-center">ثبت‌نام</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">نام کاربری</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">رمز عبور</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="mb-3">
                        <label for="city" class="form-label">شهر</label>
                        <select class="form-select" id="city" name="city" required>
                            <option value="">انتخاب شهر</option>
                            {% for city in CITIES %}
                            <option value="{{ city }}">{{ city }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">ثبت‌نام</button>
                </form>
                <div class="text-center mt-3">
                    <a href="{{ url_for('login') }}">قبلاً ثبت‌نام کرده‌اید؟ ورود</a>
                </div>
            </div>
        </div>
    </div>
</div>
"""

login_template = """
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card floating">
            <div class="card-header">
                <h4 class="text-center">ورود</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">نام کاربری</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">رمز عبور</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">ورود</button>
                </form>
                <div class="text-center mt-3">
                    <a href="{{ url_for('register') }}">حساب کاربری ندارید؟ ثبت‌نام</a>
                </div>
            </div>
        </div>
    </div>
</div>
"""

profile_template = """
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card floating">
            <div class="card-header">
                <h4 class="text-center">پروفایل</h4>
            </div>
            <div class="card-body">
                <p><strong>نام کاربری:</strong> {{ current_user.username }}</p>
                <p><strong>شهر:</strong> {{ current_user.city }}</p>
                
                <h5 class="mt-4">مکان‌های من</h5>
                {% if current_user.places %}
                <ul class="list-group">
                    {% for place in current_user.places %}
                    <li class="list-group-item" style="background: rgba(17, 34, 64, 0.5); border: 1px solid rgba(100, 255, 218, 0.1); color: #a8b2d1;">
                        <a href="{{ url_for('place_detail', place_id=place.id) }}" style="color: #64ffda; text-decoration: none;">{{ place.title }}</a>
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <p>شما هنوز مکانی اضافه نکرده‌اید.</p>
                {% endif %}
                
                <h5 class="mt-4">ویرایش شهر</h5>
                <form method="POST">
                    <div class="mb-3">
                        <select class="form-select" name="city" required>
                            {% for city in CITIES %}
                            <option value="{{ city }}" {{ 'selected' if city == current_user.city }}>{{ city }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary">به‌روزرسانی</button>
                </form>
            </div>
        </div>
    </div>
</div>
"""

add_place_template = """
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card floating">
            <div class="card-header">
                <h4 class="text-center">افزودن مکان</h4>
            </div>
            <div class="card-body">
                <form method="POST" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label for="title" class="form-label">عنوان</label>
                        <input type="text" class="form-control" id="title" name="title" required>
                    </div>
                    <div class="mb-3">
                        <label for="description" class="form-label">توضیحات</label>
                        <textarea class="form-control" id="description" name="description" rows="4" required></textarea>
                    </div>
                    <div class="mb-3">
                        <label for="address" class="form-label">آدرس</label>
                        <input type="text" class="form-control" id="address" name="address" required>
                    </div>
                    <div class="mb-3">
                        <label for="mobile" class="form-label">شماره موبایل (اختیاری)</label>
                        <input type="text" class="form-control" id="mobile" name="mobile">
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="morning_shift" class="form-label">شیفت صبح (اختیاری)</label>
                                <input type="text" class="form-control" id="morning_shift" name="morning_shift" placeholder="8:00-12:00">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="evening_shift" class="form-label">شیفت عصر (اختیاری)</label>
                                <input type="text" class="form-control" id="evening_shift" name="evening_shift" placeholder="16:00-20:00">
                            </div>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label for="category" class="form-label">دسته‌بندی</label>
                        <select class="form-select" id="category" name="category" required>
                            <option value="">انتخاب دسته‌بندی</option>
                            {% for category, subcategories in CATEGORIES.items() %}
                            <option value="{{ category }}">{{ category }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="subcategory" class="form-label">زیرمجموعه</label>
                        <select class="form-select" id="subcategory" name="subcategory" required>
                            <option value="">ابتدا دسته‌بندی را انتخاب کنید</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="city" class="form-label">شهر</label>
                        <select class="form-select" id="city" name="city" required>
                            <option value="">انتخاب شهر</option>
                            {% for city in CITIES %}
                            <option value="{{ city }}">{{ city }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="image" class="form-label">عکس (اختیاری)</label>
                        <input type="file" class="form-control" id="image" name="image" accept="image/*">
                    </div>
                    <button type="submit" class="btn btn-primary w-100">افزودن مکان</button>
                </form>
            </div>
        </div>
    </div>
</div>
<script>
document.getElementById('category').addEventListener('change', function() {
    const category = this.value;
    const subcategorySelect = document.getElementById('subcategory');
    subcategorySelect.innerHTML = '<option value="">در حال بارگذاری...</option>';
    
    // Simulate loading subcategories from server
    setTimeout(() => {
        subcategorySelect.innerHTML = '<option value="">انتخاب زیرمجموعه</option>';
        if (category) {
            const subcategories = {{ CATEGORIES | tojson }};
            const categoryKey = Object.keys(subcategories).find(key => key.startsWith(category));
            if (categoryKey) {
                subcategories[categoryKey].forEach(sub => {
                    const option = document.createElement('option');
                    option.value = sub;
                    option.textContent = sub;
                    subcategorySelect.appendChild(option);
                });
            }
        }
    }, 500);
});
</script>
"""

place_detail_template = """
<div class="row">
    <div class="col-md-8">
        <div class="card floating">
            <div class="card-body">
                <h2>{{ place.title }}</h2>
                <p class="text-muted">
                    <i class="fas fa-map-marker-alt"></i> {{ place.city }} - {{ place.address }}
                </p>
                <p class="text-muted">
                    <i class="fas fa-user"></i> صاحب مکان: {{ place.owner.username }}
                </p>
                <p>
                    <i class="fas fa-list"></i> دسته‌بندی: {{ place.category }} - {{ place.subcategory }}
                </p>
                {% if place.mobile %}
                <p>
                    <i class="fas fa-phone"></i> 
                    <a href="tel:{{ place.mobile }}" style="color: #64ffda;">{{ place.mobile }}</a>
                </p>
                {% endif %}
                {% if place.morning_shift or place.evening_shift %}
                <p>
                    <i class="fas fa-clock"></i> 
                    {% if place.morning_shift %}صبح: {{ place.morning_shift }}{% endif %}
                    {% if place.evening_shift %}عصر: {{ place.evening_shift }}{% endif %}
                </p>
                {% endif %}
                <hr>
                <h5>توضیحات</h5>
                <p>{{ place.description }}</p>
                
                {% if current_user.is_authenticated and current_user.id != place.owner_id %}
                <button class="btn btn-success" data-bs-toggle="modal" data-bs-target="#chatModal">
                    <i class="fas fa-comment"></i> چت با صاحب مکان
                </button>
                {% endif %}
            </div>
        </div>
        
        <div class="card mt-4 floating">
            <div class="card-header">
                <h5>امتیازات و نظرات</h5>
            </div>
            <div class="card-body">
                {% if place.ratings %}
                <div class="mb-3">
                    <strong>میانگین امتیاز:</strong> 
                    {% set avg_rating = place.ratings | sum(attribute='rating') / place.ratings | length %}
                    {% for i in range(1, 6) %}
                        {% if i <= avg_rating %}
                        <i class="fas fa-star text-warning"></i>
                        {% else %}
                        <i class="far fa-star text-warning"></i>
                        {% endif %}
                    {% endfor %}
                    ({{ "{:.1f}".format(avg_rating) }} از 5)
                </div>
                {% endif %}
                
                {% for rating in place.ratings %}
                <div class="border-bottom pb-3 mb-3" style="border-color: rgba(100, 255, 218, 0.1) !important;">
                    <div>
                        {% for i in range(1, 6) %}
                            {% if i <= rating.rating %}
                            <i class="fas fa-star text-warning"></i>
                            {% else %}
                            <i class="far fa-star text-warning"></i>
                            {% endif %}
                        {% endfor %}
                        <small class="text-muted">{{ rating.user.username }} - {{ rating.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
                    </div>
                    {% if rating.comment %}
                    <p class="mt-2">{{ rating.comment }}</p>
                    {% endif %}
                </div>
                {% endfor %}
                
                {% if current_user.is_authenticated %}
                <h5 class="mt-4">ثبت امتیاز و نظر</h5>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">امتیاز</label>
                        <div>
                            {% for i in range(1, 6) %}
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="radio" name="rating" id="rating{{ i }}" value="{{ i }}" required>
                                <label class="form-check-label" for="rating{{ i }}">{{ i }}</label>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="mb-3">
                        <label for="comment" class="form-label">نظر (اختیاری)</label>
                        <textarea class="form-control" id="comment" name="comment" rows="3"></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">ثبت</button>
                </form>
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="map-container">
            <iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d103916.6998339214!2d51.3372975!3d35.694373!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3f8e00491ff3dcd9%3A0xf0b3697c521a41e4!2sTehran%2C%20Tehran%20Province%2C%20Iran!5e0!3m2!1sen!2s!4v1620000000000!5m2!1sen!2s" allowfullscreen="" loading="lazy"></iframe>
        </div>
    </div>
</div>

<!-- Chat Modal -->
<div class="modal fade" id="chatModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-scrollable">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">چت با {{ place.owner.username }}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="chatMessages">
                <!-- Messages will be loaded here -->
            </div>
            <div class="modal-footer">
                <input type="text" class="form-control" id="messageInput" placeholder="پیام خود را بنویسید...">
                <button class="btn btn-primary" id="sendMessageBtn">ارسال</button>
            </div>
        </div>
    </div>
</div>
<script>
const socket = io();
const placeId = {{ place.id }};
const ownerId = {{ place.owner_id }};
const currentUserId = {{ current_user.id if current_user.is_authenticated else 'null' }};

// Join chat room
socket.emit('join', {place_id: placeId, owner_id: ownerId, user_id: currentUserId});

// Load chat history
socket.on('load_history', function(data) {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '';
    data.messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'mb-2';
        messageDiv.innerHTML = `<strong>${msg.sender}</strong>: ${msg.text} <small class="text-muted">(${msg.time})</small>`;
        chatMessages.appendChild(messageDiv);
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
});

// Receive new message
socket.on('receive_message', function(data) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'mb-2';
    messageDiv.innerHTML = `<strong>${data.sender}</strong>: ${data.text} <small class="text-muted">(${data.time})</small>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
});

// Send message
document.getElementById('sendMessageBtn').addEventListener('click', function() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    if (message) {
        socket.emit('send_message', {
            place_id: placeId,
            owner_id: ownerId,
            user_id: currentUserId,
            message: message
        });
        messageInput.value = '';
    }
});

// Send message on Enter key
document.getElementById('messageInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        document.getElementById('sendMessageBtn').click();
    }
});
</script>
"""

# Routes
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    city = request.args.get('city', '')
    only_my_city = request.args.get('only_my_city', '')
    
    query = Place.query
    
    if search:
        query = query.filter(Place.title.contains(search) | Place.address.contains(search))
    
    if category:
        query = query.filter(Place.category.startswith(category))
    
    if city:
        query = query.filter_by(city=city)
    
    if only_my_city and current_user.is_authenticated:
        query = query.filter_by(city=current_user.city)
    
    places = query.paginate(page=page, per_page=20)
    
    return render_template_string(
        base_template.replace('{% block content %}{% endblock %}', '{% block content %}' + index_template + '{% endblock %}'),
        places=places,
        CATEGORIES=CATEGORIES,
        CITIES=CITIES
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        city = request.form['city']
        
        if User.query.filter_by(username=username).first():
            flash('نام کاربری قبلاً استفاده شده است', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password, city=city)
        db.session.add(user)
        db.session.commit()
        
        flash('ثبت‌نام موفق!', 'success')
        return redirect(url_for('login'))
    
    return render_template_string(
        base_template.replace('{% block content %}{% endblock %}', '{% block content %}' + register_template + '{% endblock %}'),
        CITIES=CITIES
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('ورود موفق!', 'success')
            return redirect(url_for('index'))
        else:
            flash('نام کاربری یا رمز اشتباه است', 'error')
    
    return render_template_string(
        base_template.replace('{% block content %}{% endblock %}', '{% block content %}' + login_template + '{% endblock %}')
    )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('خروج موفق!', 'success')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        city = request.form['city']
        current_user.city = city
        db.session.commit()
        flash('پروفایل به‌روزرسانی شد', 'success')
        return redirect(url_for('profile'))
    
    return render_template_string(
        base_template.replace('{% block content %}{% endblock %}', '{% block content %}' + profile_template + '{% endblock %}'),
        CITIES=CITIES
    )

@app.route('/add_place', methods=['GET', 'POST'])
@login_required
def add_place():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        address = request.form['address']
        mobile = request.form.get('mobile', '')
        morning_shift = request.form.get('morning_shift', '')
        evening_shift = request.form.get('evening_shift', '')
        category = request.form['category']
        subcategory = request.form['subcategory']
        city = request.form['city']
        
        # Handle image upload
        image_data = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                image_data = base64.b64encode(image.read()).decode('utf-8')
        
        place = Place(
            title=title,
            description=description,
            address=address,
            mobile=mobile,
            morning_shift=morning_shift,
            evening_shift=evening_shift,
            category=category,
            subcategory=subcategory,
            city=city,
            owner_id=current_user.id
        )
        
        db.session.add(place)
        db.session.commit()
        
        flash('مکان اضافه شد!', 'success')
        return redirect(url_for('index'))
    
    return render_template_string(
        base_template.replace('{% block content %}{% endblock %}', '{% block content %}' + add_place_template + '{% endblock %}'),
        CATEGORIES=CATEGORIES,
        CITIES=CITIES
    )

@app.route('/place/<int:place_id>', methods=['GET', 'POST'])
def place_detail(place_id):
    place = Place.query.get_or_404(place_id)
    
    if request.method == 'POST' and current_user.is_authenticated:
        rating_value = int(request.form['rating'])
        comment = request.form.get('comment', '')
        
        # Prevent owner from rating their own place
        if current_user.id == place.owner_id:
            flash('شما نمی‌توانید به مکان خودتان امتیاز دهید', 'error')
            return redirect(url_for('place_detail', place_id=place_id))
        
        rating = Rating(
            place_id=place_id,
            user_id=current_user.id,
            rating=rating_value,
            comment=comment
        )
        
        db.session.add(rating)
        db.session.commit()
        
        flash('نظر ثبت شد', 'success')
        return redirect(url_for('place_detail', place_id=place_id))
    
    return render_template_string(
        base_template.replace('{% block content %}{% endblock %}', '{% block content %}' + place_detail_template + '{% endblock %}'),
        place=place
    )

# SocketIO events
@socketio.on('join')
def handle_join(data):
    place_id = data['place_id']
    owner_id = data['owner_id']
    user_id = data['user_id']
    
    # Create a unique room name
    room = f"place_{place_id}_owner_{owner_id}"
    join_room(room)
    
    # Load chat history
    chats = Chat.query.filter(
        ((Chat.sender_id == user_id) & (Chat.receiver_id == owner_id)) |
        ((Chat.sender_id == owner_id) & (Chat.receiver_id == user_id))
    ).order_by(Chat.timestamp).all()
    
    messages = []
    for chat in chats:
        sender = User.query.get(chat.sender_id)
        messages.append({
            'sender': sender.username,
            'text': chat.message,
            'time': chat.timestamp.strftime('%H:%M')
        })
    
    emit('load_history', {'messages': messages})

@socketio.on('send_message')
def handle_send_message(data):
    place_id = data['place_id']
    owner_id = data['owner_id']
    user_id = data['user_id']
    message_text = data['message']
    
    # Save message to database
    chat = Chat(
        sender_id=user_id,
        receiver_id=owner_id,
        message=message_text
    )
    db.session.add(chat)
    db.session.commit()
    
    # Create room name
    room = f"place_{place_id}_owner_{owner_id}"
    
    # Get sender username
    sender = User.query.get(user_id)
    
    # Emit message to room
    emit('receive_message', {
        'sender': sender.username,
        'text': message_text,
        'time': chat.timestamp.strftime('%H:%M')
    }, room=room)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)