from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import base64
import os

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///places.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
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
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    mobile = db.Column(db.String(20), nullable=True)
    morning_shift = db.Column(db.String(50), nullable=True)
    evening_shift = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    images = db.Column(db.Text, nullable=True)  # base64 encoded images
    ratings = db.relationship('Rating', backref='place', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Templates
base_template = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مکان‌ها</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {
            font-family: 'Vazir', 'Tahoma', sans-serif;
            background-color: #f8f9fa;
        }
        .navbar-brand {
            font-weight: bold;
        }
        .card {
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .card-img-top {
            height: 150px;
            object-fit: cover;
        }
        .footer {
            background-color: #343a40;
            color: white;
            padding: 20px 0;
            margin-top: 40px;
        }
        .btn-green {
            background-color: #28a745;
            border-color: #28a745;
        }
        .btn-green:hover {
            background-color: #218838;
            border-color: #1e7e34;
        }
        .rtl {
            direction: rtl;
            text-align: right;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">مکان‌ها</a>
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
                        <a class="nav-link" href="{{ url_for('add_place') }}">ثبت مکان</a>
                    </li>
                    {% endif %}
                </ul>
                <ul class="navbar-nav">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('profile') }}">حساب من</a>
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
                    <div class="alert alert-{{ 'success' if category == 'success' else 'danger' }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <footer class="footer mt-5">
        <div class="container text-center">
            <p class="mb-0">&copy; 2023 مکان‌ها. تمامی حقوق محفوظ است.</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
'''

index_template = '''
{% extends "base.html" %}
{% block content %}
<div class="row mb-4">
    <div class="col-md-8 mx-auto">
        <form method="GET" action="{{ url_for('index') }}" class="d-flex">
            <input type="text" name="q" class="form-control me-2" placeholder="جستجو در مکان‌ها..." value="{{ request.args.get('q', '') }}">
            <select name="category" class="form-select me-2">
                <option value="">همه دسته‌بندی‌ها</option>
                {% for cat in categories %}
                <option value="{{ cat }}" {% if request.args.get('category') == cat %}selected{% endif %}>{{ cat }}</option>
                {% endfor %}
            </select>
            <select name="city" class="form-select me-2">
                <option value="">همه شهرها</option>
                {% for c in cities %}
                <option value="{{ c }}" {% if request.args.get('city') == c %}selected{% endif %}>{{ c }}</option>
                {% endfor %}
            </select>
            {% if current_user.is_authenticated %}
            <a href="{{ url_for('index', only_my_city='true') }}" class="btn btn-outline-primary">فقط شهرکمون</a>
            {% endif %}
            <button class="btn btn-primary" type="submit">جستجو</button>
        </form>
    </div>
</div>

<div class="row">
    {% for place in places %}
    <div class="col-lg-4 col-md-6 mb-4">
        <div class="card h-100">
            {% if place.images %}
                <img src="data:image/jpeg;base64,{{ place.images.split(',')[0] }}" class="card-img-top" alt="{{ place.title }}">
            {% else %}
                <div class="card-img-top bg-light d-flex align-items-center justify-content-center" style="height: 150px;">
                    <i class="fas fa-image fa-3x text-muted"></i>
                </div>
            {% endif %}
            <div class="card-body">
                <h5 class="card-title">{{ place.title }}</h5>
                <p class="card-text">{{ place.description[:100] }}...</p>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">{{ place.city }}</small>
                    <small class="text-muted">{{ place.category }}</small>
                </div>
                {% if place.morning_shift %}
                <small class="text-muted"><i class="fas fa-sun"></i> {{ place.morning_shift }}</small>
                {% endif %}
                {% if place.evening_shift %}
                <small class="text-muted"><i class="fas fa-moon"></i> {{ place.evening_shift }}</small>
                {% endif %}
            </div>
            <div class="card-footer">
                <a href="{{ url_for('place_detail', place_id=place.id) }}" class="btn btn-primary btn-sm">مشاهده</a>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<nav aria-label="صفحه‌بندی">
    <ul class="pagination justify-content-center">
        {% if pagination.has_prev %}
        <li class="page-item">
            <a class="page-link" href="{{ url_for('index', page=pagination.prev_num, q=request.args.get('q'), category=request.args.get('category'), city=request.args.get('city')) }}">قبلی</a>
        </li>
        {% endif %}
        {% for page_num in pagination.iter_pages() %}
            {% if page_num %}
                {% if page_num != pagination.page %}
                <li class="page-item">
                    <a class="page-link" href="{{ url_for('index', page=page_num, q=request.args.get('q'), category=request.args.get('category'), city=request.args.get('city')) }}">{{ page_num }}</a>
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
        {% if pagination.has_next %}
        <li class="page-item">
            <a class="page-link" href="{{ url_for('index', page=pagination.next_num, q=request.args.get('q'), category=request.args.get('category'), city=request.args.get('city')) }}">بعدی</a>
        </li>
        {% endif %}
    </ul>
</nav>
{% endblock %}
'''

register_template = '''
{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">ثبت‌نام</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">نام کاربری یا شماره موبایل</label>
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
                            {% for c in cities %}
                            <option value="{{ c }}">{{ c }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" class="btn btn-green w-100">ثبت‌نام</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

login_template = '''
{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">ورود</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">نام کاربری یا شماره موبایل</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">رمز عبور</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-green w-100">ورود</button>
                </form>
                <div class="text-center mt-3">
                    <a href="#" class="text-decoration-none">ورود با OTP</a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

profile_template = '''
{% extends "base.html" %}
{% block content %}
<div class="row">
    <div class="col-md-8 mx-auto">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">حساب من</h4>
            </div>
            <div class="card-body">
                <p><strong>نام کاربری:</strong> {{ current_user.username }}</p>
                <p><strong>شهر:</strong> {{ current_user.city }}</p>
                
                <form method="POST" class="mt-4">
                    <div class="mb-3">
                        <label for="city" class="form-label">تغییر شهر</label>
                        <select class="form-select" id="city" name="city" required>
                            {% for c in cities %}
                            <option value="{{ c }}" {% if c == current_user.city %}selected{% endif %}>{{ c }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" class="btn btn-green">به‌روزرسانی</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

add_place_template = '''
{% extends "base.html" %}
{% block content %}
<div class="row">
    <div class="col-md-8 mx-auto">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">ثبت مکان جدید</h4>
            </div>
            <div class="card-body">
                <form method="POST" enctype="multipart/form-data">
                    <!-- Step 1 -->
                    <div id="step1">
                        <h5>مرحله 1: اطلاعات اصلی</h5>
                        <div class="mb-3">
                            <label for="title" class="form-label">عنوان مکان</label>
                            <input type="text" class="form-control" id="title" name="title" required>
                        </div>
                        <div class="mb-3">
                            <label for="description" class="form-label">توضیحات</label>
                            <textarea class="form-control" id="description" name="description" rows="4" required></textarea>
                        </div>
                        <button type="button" class="btn btn-primary" onclick="nextStep(2)">مرحله بعد</button>
                    </div>
                    
                    <!-- Step 2 -->
                    <div id="step2" style="display:none;">
                        <h5>مرحله 2: آدرس و تماس</h5>
                        <div class="mb-3">
                            <label for="address" class="form-label">آدرس کامل</label>
                            <input type="text" class="form-control" id="address" name="address" required>
                        </div>
                        <div class="mb-3">
                            <label for="mobile" class="form-label">شماره تماس (اختیاری)</label>
                            <input type="text" class="form-control" id="mobile" name="mobile">
                        </div>
                        <button type="button" class="btn btn-secondary" onclick="prevStep(1)">مرحله قبل</button>
                        <button type="button" class="btn btn-primary" onclick="nextStep(3)">مرحله بعد</button>
                    </div>
                    
                    <!-- Step 3 -->
                    <div id="step3" style="display:none;">
                        <h5>مرحله 3: شیفت‌های کاری</h5>
                        <div class="mb-3">
                            <label for="morning_shift" class="form-label">شیفت صبح (مثال: 8:00-12:00)</label>
                            <input type="text" class="form-control" id="morning_shift" name="morning_shift">
                        </div>
                        <div class="mb-3">
                            <label for="evening_shift" class="form-label">شیفت عصر (مثال: 16:00-20:00)</label>
                            <input type="text" class="form-control" id="evening_shift" name="evening_shift">
                        </div>
                        <button type="button" class="btn btn-secondary" onclick="prevStep(2)">مرحله قبل</button>
                        <button type="button" class="btn btn-primary" onclick="nextStep(4)">مرحله بعد</button>
                    </div>
                    
                    <!-- Step 4 -->
                    <div id="step4" style="display:none;">
                        <h5>مرحله 4: دسته‌بندی و شهر</h5>
                        <div class="mb-3">
                            <label for="category" class="form-label">دسته‌بندی</label>
                            <select class="form-select" id="category" name="category" required onchange="updateSubcategories()">
                                <option value="">انتخاب دسته‌بندی</option>
                                {% for cat in categories %}
                                <option value="{{ cat }}">{{ cat }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="subcategory" class="form-label">زیردسته‌بندی</label>
                            <select class="form-select" id="subcategory" name="subcategory" required>
                                <option value="">انتخاب زیردسته‌بندی</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="city" class="form-label">شهر</label>
                            <select class="form-select" id="city" name="city" required>
                                <option value="">انتخاب شهر</option>
                                {% for c in cities %}
                                <option value="{{ c }}">{{ c }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="images" class="form-label">تصاویر (اختیاری - حداکثر 5 عدد)</label>
                            <input type="file" class="form-control" id="images" name="images" multiple accept="image/*">
                        </div>
                        <button type="button" class="btn btn-secondary" onclick="prevStep(3)">مرحله قبل</button>
                        <button type="submit" class="btn btn-green">انتشار مکان</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    function nextStep(step) {
        document.getElementById('step' + (step - 1)).style.display = 'none';
        document.getElementById('step' + step).style.display = 'block';
    }
    
    function prevStep(step) {
        document.getElementById('step' + (step + 1)).style.display = 'none';
        document.getElementById('step' + step).style.display = 'block';
    }
    
    function updateSubcategories() {
        const category = document.getElementById('category').value;
        const subcategorySelect = document.getElementById('subcategory');
        subcategorySelect.innerHTML = '<option value="">انتخاب زیردسته‌بندی</option>';
        
        const subcategories = {{ subcategories|tojson }};
        if (category && subcategories[category]) {
            subcategories[category].forEach(sub => {
                const option = document.createElement('option');
                option.value = sub;
                option.textContent = sub;
                subcategorySelect.appendChild(option);
            });
        }
    }
</script>
{% endblock %}
'''

place_detail_template = '''
{% extends "base.html" %}
{% block content %}
<div class="row">
    <div class="col-md-8 mx-auto">
        <div class="card">
            <div class="card-body">
                <h2>{{ place.title }}</h2>
                <p>{{ place.description }}</p>
                
                <div class="row mb-3">
                    <div class="col-md-6">
                        <p><i class="fas fa-map-marker-alt"></i> {{ place.address }}</p>
                        {% if place.mobile %}
                        <p><i class="fas fa-phone"></i> <a href="tel:{{ place.mobile }}">{{ place.mobile }}</a></p>
                        {% endif %}
                    </div>
                    <div class="col-md-6">
                        {% if place.morning_shift %}
                        <p><i class="fas fa-sun"></i> شیفت صبح: {{ place.morning_shift }}</p>
                        {% endif %}
                        {% if place.evening_shift %}
                        <p><i class="fas fa-moon"></i> شیفت عصر: {{ place.evening_shift }}</p>
                        {% endif %}
                    </div>
                </div>
                
                <div class="mb-3">
                    <span class="badge bg-primary">{{ place.category }}</span>
                    <span class="badge bg-secondary">{{ place.subcategory }}</span>
                    <span class="badge bg-success">{{ place.city }}</span>
                </div>
                
                {% if place.images %}
                <div class="row mb-3">
                    {% for img in place.images.split(',') %}
                    <div class="col-md-3 mb-2">
                        <img src="data:image/jpeg;base64,{{ img }}" class="img-fluid" alt="تصویر مکان">
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if current_user.is_authenticated and current_user.id != place.owner_id %}
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#chatModal">چت با صاحب</button>
                {% endif %}
                
                <hr>
                
                <h4>امتیازات و نظرات</h4>
                {% if current_user.is_authenticated %}
                <form method="POST" action="{{ url_for('add_rating', place_id=place.id) }}" class="mb-4">
                    <div class="mb-3">
                        <label class="form-label">امتیاز شما</label>
                        <div>
                            {% for i in range(1, 6) %}
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="radio" name="rating" id="rating{{ i }}" value="{{ i }}" required>
                                <label class="form-check-label" for="rating{{ i }}">{{ i }} ستاره</label>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="mb-3">
                        <label for="comment" class="form-label">نظر شما</label>
                        <textarea class="form-control" id="comment" name="comment" rows="3"></textarea>
                    </div>
                    <button type="submit" class="btn btn-green">ارسال نظر</button>
                </form>
                {% endif %}
                
                <div class="row">
                    {% for rating in ratings %}
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6>{{ rating.user.username }}</h6>
                                <div>
                                    {% for i in range(rating.rating) %}
                                    <i class="fas fa-star text-warning"></i>
                                    {% endfor %}
                                    {% for i in range(5 - rating.rating) %}
                                    <i class="far fa-star text-warning"></i>
                                    {% endfor %}
                                </div>
                                <p>{{ rating.comment }}</p>
                                <small class="text-muted">{{ rating.timestamp.strftime('%Y/%m/%d %H:%M') }}</small>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
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
                <input type="text" id="messageInput" class="form-control" placeholder="پیام خود را بنویسید...">
                <button class="btn btn-green" onclick="sendMessage()">ارسال</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    const socket = io();
    const roomId = "{{ place.id }}_{{ place.owner_id }}_{{ current_user.id }}";
    
    socket.emit('join', {room: roomId});
    
    socket.on('receive_message', function(data) {
        const messagesDiv = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.innerHTML = `<strong>${data.sender}</strong>: ${data.message} <small class="text-muted">${data.timestamp}</small>`;
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    });
    
    function sendMessage() {
        const input = document.getElementById('messageInput');
        if (input.value.trim() !== '') {
            socket.emit('send_message', {
                room: roomId,
                message: input.value,
                sender: "{{ current_user.username }}"
            });
            input.value = '';
        }
    }
    
    // Load chat history
    fetch("{{ url_for('get_chat_history', place_id=place.id) }}")
        .then(response => response.json())
        .then(data => {
            const messagesDiv = document.getElementById('chatMessages');
            data.messages.forEach(msg => {
                const messageElement = document.createElement('div');
                messageElement.innerHTML = `<strong>${msg.sender}</strong>: ${msg.message} <small class="text-muted">${msg.timestamp}</small>`;
                messagesDiv.appendChild(messageElement);
            });
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        });
</script>
{% endblock %}
'''

# Routes
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    category = request.args.get('category', '')
    city = request.args.get('city', '')
    only_my_city = request.args.get('only_my_city', '')
    
    query = Place.query
    
    if q:
        query = query.filter(Place.title.contains(q) | Place.description.contains(q))
    
    if category:
        query = query.filter_by(category=category)
    
    if city:
        query = query.filter_by(city=city)
    
    if only_my_city and current_user.is_authenticated:
        query = query.filter_by(city=current_user.city)
    
    places = query.paginate(page=page, per_page=20)
    
    return render_template_string(index_template, 
                                  places=places.items, 
                                  pagination=places,
                                  categories=CATEGORIES.keys(),
                                  cities=CITIES)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        city = request.form['city']
        
        if User.query.filter_by(username=username).first():
            flash('نام کاربری قبلاً استفاده شده است', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password, city=city)
        db.session.add(user)
        db.session.commit()
        
        flash('ثبت‌نام موفق! لطفاً وارد شوید', 'success')
        return redirect(url_for('login'))
    
    return render_template_string(register_template, cities=CITIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('با موفقیت وارد شدید', 'success')
            return redirect(url_for('index'))
        else:
            flash('نام کاربری یا رمز اشتباه است', 'danger')
    
    return render_template_string(login_template)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('با موفقیت خارج شدید', 'success')
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
    
    return render_template_string(profile_template, cities=CITIES)

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
        
        # Handle image uploads
        images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files[:5]:  # Limit to 5 images
                if file and file.filename:
                    file_content = file.read()
                    encoded = base64.b64encode(file_content).decode('utf-8')
                    images.append(encoded)
        
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
            owner_id=current_user.id,
            images=','.join(images) if images else None
        )
        
        db.session.add(place)
        db.session.commit()
        
        flash('مکان با موفقیت اضافه شد!', 'success')
        return redirect(url_for('index'))
    
    return render_template_string(add_place_template, 
                                  categories=CATEGORIES.keys(),
                                  cities=CITIES,
                                  subcategories=CATEGORIES)

@app.route('/place/<int:place_id>')
def place_detail(place_id):
    place = Place.query.get_or_404(place_id)
    ratings = Rating.query.filter_by(place_id=place_id).all()
    return render_template_string(place_detail_template, 
                                  place=place, 
                                  ratings=ratings)

@app.route('/place/<int:place_id>/rating', methods=['POST'])
@login_required
def add_rating(place_id):
    place = Place.query.get_or_404(place_id)
    
    # Prevent owner from rating their own place
    if place.owner_id == current_user.id:
        flash('شما نمی‌توانید به مکان خودتان امتیاز دهید', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))
    
    rating_value = int(request.form['rating'])
    comment = request.form.get('comment', '')
    
    # Check if user already rated this place
    existing_rating = Rating.query.filter_by(
        place_id=place_id, 
        user_id=current_user.id
    ).first()
    
    if existing_rating:
        existing_rating.rating = rating_value
        existing_rating.comment = comment
    else:
        rating = Rating(
            place_id=place_id,
            user_id=current_user.id,
            rating=rating_value,
            comment=comment
        )
        db.session.add(rating)
    
    db.session.commit()
    flash('نظر شما ثبت شد', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

@app.route('/chat/history/<int:place_id>')
@login_required
def get_chat_history(place_id):
    place = Place.query.get_or_404(place_id)
    
    # Determine sender and receiver IDs
    if current_user.id < place.owner_id:
        sender_id, receiver_id = current_user.id, place.owner_id
    else:
        sender_id, receiver_id = place.owner_id, current_user.id
    
    # Get chat history
    messages = Chat.query.filter(
        ((Chat.sender_id == sender_id) & (Chat.receiver_id == receiver_id)) |
        ((Chat.sender_id == receiver_id) & (Chat.receiver_id == sender_id))
    ).order_by(Chat.timestamp).all()
    
    return jsonify({
        'messages': [{
            'sender': User.query.get(msg.sender_id).username,
            'message': msg.message,
            'timestamp': msg.timestamp.strftime('%Y/%m/%d %H:%M')
        } for msg in messages]
    })

# SocketIO events
@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)

@socketio.on('send_message')
def handle_send_message(data):
    room = data['room']
    message = data['message']
    sender = data['sender']
    
    # Parse room to get sender and receiver IDs
    parts = room.split('_')
    if len(parts) >= 3:
        place_id, receiver_id, sender_id = int(parts[0]), int(parts[1]), int(parts[2])
        
        # Save message to database
        chat = Chat(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message
        )
        db.session.add(chat)
        db.session.commit()
        
        # Emit message to room
        emit('receive_message', {
            'sender': sender,
            'message': message,
            'timestamp': datetime.now().strftime('%Y/%m/%d %H:%M')
        }, room=room)

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    socketio.run(app, debug=True)