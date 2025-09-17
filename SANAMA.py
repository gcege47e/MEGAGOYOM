from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import re
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2'

# دیتابیس ساده برای ذخیره کاربران
users_db = {}

# دیتابیس ساده برای ذخیره مکان‌ها
places_db = []

# لیست شهرها
CITIES = [
    "شهرک صدرا", "شهرک گلستان", "معالی آباد", "شهرک کشن", "شهرک مهدیه",
    "شهرک زینبیه", "شهرک بعثت", "شهرک والفجر", "شهرک صنعتی عفیف آباد",
    "کوی امام رضا", "شهرک گویم", "شهرک بزین", "شهرک رحمت آباد", "شهرک خورشید",
    "شهرک سلامت", "شهرک فرهنگیان", "کوی زاگرس", "کوی پاسداران", "شهرک عرفان",
    "شهرک هنرستان"
]

# دسته‌بندی‌ها و زیردسته‌ها
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
        "آزمایشگاه پزشکی و رADIولوژی (آزمایشگاه، سونوگرافی)",
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
        "مراکز آموزش علوم مختلف (ریاضی، فیزik، شیمی)",
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
        "پیست اسki و ورزش‌های زمستانی (اسکی، ورزش زمستانی)",
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

# HTML template for registration page
REGISTRATION_HTML = """
<!DOCTYPE html>
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
            padding: 30px;
            text-align: center;
            color: var(--light);
        }
        
        .header h1 {
            font-size: 24px;
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
            padding: 12px 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        select.form-control {
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23006769' viewBox='0 0 16 16'%3E%3Cpath d='M8 12L2 6h12L8 12z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: left 15px center;
            background-size: 12px;
            padding-right: 15px;
        }
        
        .form-control:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(0, 103, 105, 0.2);
            outline: none;
        }
        
        .form-control.success {
            border-color: var(--success);
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
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .login-link {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
        }
        
        .login-link a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes successAnimation {
            0% { transform: scale(0.8); opacity: 0; }
            50% { transform: scale(1.05); opacity: 1; }
            100% { transform: scale(1); opacity: 1; }
        }
        
        .success-checkmark {
            display: flex;
            justify-content: center;
            margin: 25px 0;
        }
        
        .checkmark {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: block;
            stroke-width: 5;
            stroke: #4caf50;
            stroke-miterlimit: 10;
            box-shadow: 0 0 15px #4caf50;
            animation: fill .4s ease-in-out .4s forwards, scale .3s ease-in-out .9s both;
        }
        
        .checkmark-circle {
            stroke-dasharray: 166;
            stroke-dashoffset: 166;
            stroke-width: 5;
            stroke-miterlimit: 10;
            stroke: #4caf50;
            fill: none;
            animation: stroke .6s cubic-bezier(0.650, 0.000, 0.450, 1.000) forwards;
        }
        
        .checkmark-check {
            transform-origin: 50% 50%;
            stroke-dasharray: 48;
            stroke-dashoffset: 48;
            animation: stroke .3s cubic-bezier(0.650, 0.000, 0.450, 1.000) .8s forwards;
        }
        
        @keyframes stroke {
            100% { stroke-dashoffset: 0; }
        }
        
        @keyframes scale {
            0%, 100% { transform: none; }
            50% { transform: scale3d(1.1, 1.1, 1); }
        }
        
        @keyframes fill {
            100% { box-shadow: inset 0px 0px 0px 30px #4caf50; }
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ایجاد حساب کاربری در گویم نما</h1>
            <p>برای دسترسی به تمام امکانات سایت ثبت نام کنید</p>
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
                
                <div class="login-link">
                    قبلاً حساب دارید؟ <a href="/login">وارد شوید</a>
                </div>
            </form>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('registrationForm');
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
                
                // اعتبارسنجی نام کاربری
                const fullname = document.getElementById('fullname');
                const fullnameError = document.getElementById('fullname-error');
                const usernamePattern = /^[a-zA-Zآ-ی][a-zA-Z0-9آ-ی_]{2,}$/;
                
                if (!usernamePattern.test(fullname.value)) {
                    fullname.classList.add('error');
                    fullnameError.textContent = 'نام کاربری باید با حرف شروع شود و حداقل ۳ کاراکتر داشته باشد';
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
                
                // اعتبارسنجی تلفن همراه
                const phone = document.getElementById('phone');
                const phoneError = document.getElementById('phone-error');
                const phonePattern = /^09\\d{9}$/;
                if (!phonePattern.test(phone.value)) {
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
                                alert('خطا در ثبت نام: ' + data.message);
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('خطا در ارسال اطلاعات');
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
    </script>
</body>
</html>
"""

# HTML template for login page
LOGIN_HTML = """
<!DOCTYPE html>
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
            padding: 30px;
            text-align: center;
            color: var(--light);
        }
        
        .header h1 {
            font-size: 24px;
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
            padding: 12px 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
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
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
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
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
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
                
                <div class="register-link">
                    حساب ندارید؟ <a href="/">ثبت نام کنید</a>
                </div>
            </form>
        </div>
    </div>

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
                if (password.value === '') {
                    password.classList.add('error');
                    passwordError.style.display = 'block';
                    isValid = false;
                } else {
                    password.classList.remove('error');
                    passwordError.style.display = 'none';
                }
                
                // اگر فرم معتبر است, ارسال شود
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
                            // انتقال به صفحه اصلی
                            window.location.href = '/main?username=' + encodeURIComponent(data.user.username);
                        } else {
                            username.classList.add('error');
                            usernameError.textContent = data.message;
                            usernameError.style.display = 'block';
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('خطا در ارسال اطلاعات');
                    });
                }
            });
        });
    </script>
</body>
</html>
"""

# HTML template for main page
MAIN_HTML = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>گویم نما</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap');
        
        :root {
            --primary: #006769;
            --secondary: #40A578;
            --light: #fff;
            --text: #333;
            --gray: #f0f0f0;
            --shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Vazirmatn', sans-serif;
        }
        
        body {
            background-color: #f8f9fa;
            color: var(--text);
            padding-bottom: 70px;
        }
        
        .header {
            background-color: var(--primary);
            color: var(--light);
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            font-size: 20px;
            font-weight: bold;
            color: white;
            display: flex;
            align-items: center;
        }
        
        .header-icons {
            display: flex;
            gap: 15px;
        }
        
        .header-icon {
            color: white;
            font-size: 20px;
            cursor: pointer;
        }
        
        .main-content {
            padding: 20px;
            min-height: calc(100vh - 140px);
        }
        
        .welcome-section {
            background: linear-gradient(to right, var(--primary), var(--secondary));
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: var(--light);
            display: flex;
            justify-content: space-around;
            padding: 10px 0;
            border-top: 3px solid var(--primary);
            z-index: 100;
        }
        
        .nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            padding: 5px 15px;
            border-radius: 10px;
            transition: background-color 0.3s;
        }
        
        .nav-item.active {
            background-color: var(--gray);
        }
        
        .nav-icon {
            font-size: 24px;
            margin-bottom: 5px;
            color: var(--primary);
        }
        
        .nav-text {
            font-size: 12px;
            color: var(--text);
        }
        
        .nav-item.active .nav-icon,
        .nav-item.active .nav-text {
            color: var(--primary);
            font-weight: bold;
        }
        
        .content-section {
            display: none;
        }
        
        .content-section.active {
            display: block;
            animation: fadeIn 0.5s;
        }
        
        .profile-card {
            background-color: var(--light);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: var(--shadow);
        }
        
        .profile-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }
        
        .profile-item:last-child {
            border-bottom: none;
        }
        
        .profile-label {
            font-weight: 500;
        }
        
        .profile-value {
            color: #666;
        }
        
        .edit-icon {
            color: var(--primary);
            cursor: pointer;
            margin-right: 10px;
        }
        
        .profile-actions {
            margin-top: 20px;
        }
        
        .action-button {
            display: block;
            width: 100%;
            padding: 15px;
            background-color: var(--light);
            border: 1px solid #ddd;
            border-radius: 10px;
            margin-bottom: 10px;
            text-align: right;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        
        .action-button:hover {
            background-color: var(--gray);
        }
        
        .logout-btn {
            color: var(--error);
            font-weight: bold;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .edit-form {
            display: none;
            margin-top: 15px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 10px;
        }
        
        .edit-form.active {
            display: block;
        }
        
        .form-actions {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
        }
        
        .save-btn {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
        
        .cancel-btn {
            background-color: #ddd;
            color: #666;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
        
        /* استایل‌های جدید برای بخش افزودن مکان */
        .add-place-form {
            background-color: var(--light);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: var(--shadow);
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        
        .form-control {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        
        .form-control:focus {
            border-color: var(--primary);
            outline: none;
        }
        
        .submit-btn {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            width: 100%;
            font-size: 16px;
            cursor: pointer;
        }
        
        .my-city-toggle {
            background-color: #e0e0e0;
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            margin-left: 10px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .my-city-toggle.active {
            background-color: var(--primary);
            color: white;
        }
        
        .places-list {
            margin-top: 20px;
        }
        
        .place-card {
            background-color: var(--light);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: var(--shadow);
        }
        
        .place-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .place-category {
            color: #666;
            font-size: 14px;
            margin-bottom: 5px;
        }
        
        .place-city {
            color: var(--primary);
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">GOYOM NAMA</div>
        <div class="header-icons">
            <div class="header-icon">🔍</div>
            <div class="header-icon">🔔</div>
        </div>
    </div>
    
    <div class="main-content">
        <div class="welcome-section">
            <h2>خوش آمدید، {{ username }}!</h2>
            <p>به اپلیکیشن گویم نما خوش آمدید</p>
            <button id="myCityToggle" class="my-city-toggle">فقط شهرکمون</button>
        </div>
        
        <div id="homeSection" class="content-section active">
            <h3>صفحه اصلی</h3>
            <p>این بخش صفحه اصلی اپلیکیشن است.</p>
            
            <div class="places-list" id="placesList">
                <!-- لیست مکان‌ها اینجا نمایش داده می‌شود -->
            </div>
        </div>
        
        <div id="profileSection" class="content-section">
            <div class="profile-card">
                <h3>پروفایل کاربری</h3>
                
                <div class="profile-item">
                    <div class="profile-label">نام کاربری</div>
                    <div class="profile-value">{{ username }}</div>
                    <span class="edit-icon" onclick="toggleEditForm('usernameForm')">✏️</span>
                </div>
                <div id="usernameForm" class="edit-form">
                    <input type="text" id="newUsername" value="{{ username }}" class="form-control">
                    <div class="form-actions">
                        <button class="cancel-btn" onclick="toggleEditForm('usernameForm')">لغو</button>
                        <button class="save-btn" onclick="updateUsername()">ذخیره</button>
                    </div>
                </div>
                
                <div class="profile-item">
                    <div class="profile-label">شماره تلفن</div>
                    <div class="profile-value">{{ phone }}</div>
                    <span class="edit-icon" onclick="toggleEditForm('phoneForm')">✏️</span>
                </div>
                <div id="phoneForm" class="edit-form">
                    <input type="tel" id="newPhone" value="{{ phone }}" class="form-control">
                    <div class="form-actions">
                        <button class="cancel-btn" onclick="toggleEditForm('phoneForm')">لغو</button>
                        <button class="save-btn" onclick="updatePhone()">ذخیره</button>
                    </div>
                </div>
                
                <div class="profile-item">
                    <div class="profile-label">شهر</div>
                    <div class="profile-value">{{ city }}</div>
                    <span class="edit-icon" onclick="toggleEditForm('cityForm')">✏️</span>
                </div>
                <div id="cityForm" class="edit-form">
                    <select id="newCity" class="form-control">
                        {% for city in cities %}
                        <option value="{{ city }}" {% if city == user_city %}selected{% endif %}>{{ city }}</option>
                        {% endfor %}
                    </select>
                    <div class="form-actions">
                        <button class="cancel-btn" onclick="toggleEditForm('cityForm')">لغو</button>
                        <button class="save-btn" onclick="updateCity()">ذخیره</button>
                    </div>
                </div>
                
                <div class="profile-item">
                    <div class="profile-label">رمز عبور</div>
                    <div class="profile-value">•••••••</div>
                    <span class="edit-icon" onclick="toggleEditForm('passwordForm')">✏️</span>
                </div>
                <div id="passwordForm" class="edit-form">
                    <input type="password" id="newPassword" placeholder="رمز عبور جدید" class="form-control">
                    <input type="password" id="confirmNewPassword" placeholder="تکرار رمز عبور" class="form-control" style="margin-top: 10px;">
                    <div class="form-actions">
                        <button class="cancel-btn" onclick="toggleEditForm('passwordForm')">لغو</button>
                        <button class="save-btn" onclick="updatePassword()">ذخیره</button>
                    </div>
                </div>
            </div>
            
            <div class="profile-actions">
                <button class="action-button">مکان های من</button>
                <button class="action-button logout-btn" onclick="logout()">خروج از حساب</button>
            </div>
        </div>
        
        <div id="chatSection" class="content-section">
            <h3>چت</h3>
            <p>این بخش چت اپلیکیشن است.</p>
        </div>
        
        <div id="addSection" class="content-section">
            <h3>افزودن مکان جدید</h3>
            
            <div class="add-place-form">
                <form id="addPlaceForm">
                    <div class="form-group">
                        <label for="placeName">نام مکان</label>
                        <input type="text" id="placeName" class="form-control" placeholder="نام مکان را وارد کنید" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="mainCategory">دسته‌بندی اصلی</label>
                        <select id="mainCategory" class="form-control" onchange="updateSubcategories()" required>
                            <option value="">لطفاً دسته‌بندی اصلی را انتخاب کنید</option>
                            {% for category in categories %}
                            <option value="{{ category }}">{{ category }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="subCategory">زیردسته</label>
                        <select id="subCategory" class="form-control" disabled required>
                            <option value="">ابتدا دسته‌بندی اصلی را انتخاب کنید</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="placeCity">شهر</label>
                        <select id="placeCity" class="form-control" required>
                            <option value="">لطفاً شهر را انتخاب کنید</option>
                            {% for city in cities %}
                            <option value="{{ city }}">{{ city }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="placeAddress">آدرس</label>
                        <textarea id="placeAddress" class="form-control" placeholder="آدرس کامل مکان را وارد کنید" rows="3"></textarea>
                    </div>
                    
                    <button type="submit" class="submit-btn">ثبت مکان</button>
                </form>
            </div>
        </div>
    </div>
    
    <div class="bottom-nav">
        <div class="nav-item active" onclick="showSection('profileSection', this)">
            <div class="nav-icon">👤</div>
            <div class="nav-text">پروفایل</div>
        </div>
        <div class="nav-item" onclick="showSection('chatSection', this)">
            <div class="nav-icon">💬</div>
            <div class="nav-text">چت</div>
        </div>
        <div class="nav-item" onclick="showSection('homeSection', this)">
            <div class="nav-icon">◻️</div>
            <div class="nav-text">صفحه اصلی</div>
        </div>
        <div class="nav-item" onclick="showSection('addSection', this)">
            <div class="nav-icon">➕</div>
            <div class="nav-text">اضافه کردن</div>
        </div>
    </div>

    <script>
        // داده‌های دسته‌بندی‌ها
        const categories = {{ categories|tojson }};
        let myCityMode = false;
        
        function showSection(sectionId, element) {
            // مخفی کردن تمام بخش‌ها
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });
            
            // نمایش بخش انتخاب شده
            document.getElementById(sectionId).classList.add('active');
            
            // به روزرسانی وضعیت فعال در نوار پایین
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            
            element.classList.add('active');
            
            // اگر بخش صفحه اصلی است، مکان‌ها را بارگذاری کن
            if (sectionId === 'homeSection') {
                loadPlaces();
            }
        }
        
        function toggleEditForm(formId) {
            const form = document.getElementById(formId);
            form.classList.toggle('active');
        }
        
        function updateUsername() {
            const newUsername = document.getElementById('newUsername').value;
            alert('نام کاربری با موفقیت تغییر کرد به: ' + newUsername);
            document.querySelector('.profile-value').textContent = newUsername;
            toggleEditForm('usernameForm');
        }
        
        function updatePhone() {
            const newPhone = document.getElementById('newPhone').value;
            alert('شماره تلفن با موفقیت تغییر کرد به: ' + newPhone);
            document.querySelectorAll('.profile-value')[1].textContent = newPhone;
            toggleEditForm('phoneForm');
        }
        
        function updateCity() {
            const newCity = document.getElementById('newCity').value;
            alert('شهر با موفقیت تغییر کرد به: ' + newCity);
            document.querySelectorAll('.profile-value')[2].textContent = newCity;
            toggleEditForm('cityForm');
        }
        
        function updatePassword() {
            alert('رمز عبور با موفقیت تغییر کرد');
            toggleEditForm('passwordForm');
        }
        
        function logout() {
            if (confirm('آیا مطمئن هستید که می‌خواهید خارج شوید؟')) {
                window.location.href = '/login';
            }
        }
        
        // تابع برای به‌روزرسانی زیردسته‌ها بر اساس دسته‌بندی اصلی انتخاب شده
        function updateSubcategories() {
            const mainCategory = document.getElementById('mainCategory').value;
            const subCategorySelect = document.getElementById('subCategory');
            
            // پاک کردن گزینه‌های قبلی
            subCategorySelect.innerHTML = '';
            
            if (mainCategory) {
                // فعال کردن فیلد زیردسته
                subCategorySelect.disabled = false;
                
                // افزودن گزینه‌های زیردسته مربوط به دسته‌بندی اصلی انتخاب شده
                const subcategories = categories[mainCategory];
                subcategories.forEach(sub => {
                    const option = document.createElement('option');
                    option.value = sub;
                    option.textContent = sub;
                    subCategorySelect.appendChild(option);
                });
            } else {
                // غیرفعال کردن فیلد زیردسته اگر دسته‌بندی اصلی انتخاب نشده
                subCategorySelect.disabled = true;
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'ابتدا دسته‌بندی اصلی را انتخاب کنید';
                subCategorySelect.appendChild(option);
            }
        }
        
        // تابع برای ثبت مکان جدید
        document.getElementById('addPlaceForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const placeData = {
                name: document.getElementById('placeName').value,
                mainCategory: document.getElementById('mainCategory').value,
                subCategory: document.getElementById('subCategory').value,
                city: document.getElementById('placeCity').value,
                address: document.getElementById('placeAddress').value,
                addedBy: '{{ username }}'
            };
            
            // ارسال درخواست به سرور
            fetch('/add_place', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(placeData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('مکان با موفقیت ثبت شد!');
                    document.getElementById('addPlaceForm').reset();
                    document.getElementById('subCategory').disabled = true;
                } else {
                    alert('خطا در ثبت مکان: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('خطا در ارسال اطلاعات');
            });
        });
        
        // تابع برای بارگذاری مکان‌ها
        function loadPlaces() {
            fetch('/get_places')
                .then(response => response.json())
                .then(data => {
                    const placesList = document.getElementById('placesList');
                    placesList.innerHTML = '';
                    
                    if (data.places && data.places.length > 0) {
                        // فیلتر کردن مکان‌ها در صورت فعال بودن حالت "فقط شهرکمون"
                        let filteredPlaces = data.places;
                        if (myCityMode) {
                            filteredPlaces = data.places.filter(place => place.city === '{{ city }}');
                        }
                        
                        if (filteredPlaces.length === 0) {
                            placesList.innerHTML = '<p>هیچ مکانی برای نمایش وجود ندارد.</p>';
                            return;
                        }
                        
                        filteredPlaces.forEach(place => {
                            const placeCard = document.createElement('div');
                            placeCard.className = 'place-card';
                            placeCard.innerHTML = `
                                <div class="place-name">${place.name}</div>
                                <div class="place-category">${place.mainCategory} - ${place.subCategory}</div>
                                <div class="place-city">${place.city}</div>
                                ${place.address ? `<div class="place-address">${place.address}</div>` : ''}
                            `;
                            placesList.appendChild(placeCard);
                        });
                    } else {
                        placesList.innerHTML = '<p>هیچ مکانی برای نمایش وجود ندارد.</p>';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('placesList').innerHTML = '<p>خطا در بارگذاری مکان‌ها</p>';
                });
        }
        
        // فعال/غیرفعال کردن حالت "فقط شهرکمون"
        document.getElementById('myCityToggle').addEventListener('click', function() {
            myCityMode = !myCityMode;
            this.classList.toggle('active', myCityMode);
            this.textContent = myCityMode ? 'همه مکان‌ها' : 'فقط شهرکمون';
            loadPlaces();
        });
        
        // بارگذاری اولیه مکان‌ها
        document.addEventListener('DOMContentLoaded', function() {
            loadPlaces();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(REGISTRATION_HTML, cities=CITIES)

@app.route('/login')
def login():
    return render_template_string(LOGIN_HTML)

@app.route('/main')
def main():
    username = request.args.get('username', 'کاربر')
    user_data = users_db.get(username, {})
    return render_template_string(
        MAIN_HTML, 
        username=username,
        phone=user_data.get('phone', ''),
        city=user_data.get('city', ''),
        user_city=user_data.get('city', ''),
        cities=CITIES,
        categories=CATEGORIES
    )

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': 'داده‌های ناقص ارسال شده است'})
        
        # بررسی تکراری نبودن نام کاربری
        if data['username'] in users_db:
            return jsonify({'success': False, 'message': 'این نام کاربری قبلاً ثبت شده است'})
        
        # بررسی قالب نام کاربری
        username_pattern = re.compile(r'^[a-zA-Zآ-ی][a-zA-Z0-9آ-ی_]{2,}$')
        if not username_pattern.match(data['username']):
            return jsonify({'success': False, 'message': 'نام کاربری باید با حرف شروع شود و حداقل ۳ کاراکتر داشته باشد'})
        
        # بررسی شماره تلفن
        if 'phone' in data:
            phone_pattern = re.compile(r'^09\d{9}$')
            if not phone_pattern.match(data['phone']):
                return jsonify({'success': False, 'message': 'شماره تلفن معتبر نیست'})
        
        # بررسی رمز عبور
        if len(data['password']) < 6:
            return jsonify({'success': False, 'message': 'رمز عبور باید حداقل ۶ کاراکتر باشد'})
        
        # ذخیره کاربر در دیتابیس
        users_db[data['username']] = {
            'phone': data.get('phone', ''),
            'password': data['password'],
            'city': data.get('city', ''),
            'registered_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True, 
            'message': 'ثبت نام با موفقیت انجام شد',
            'user': {
                'username': data['username'],
                'phone': data.get('phone', ''),
                'city': data.get('city', ''),
                'registered_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"خطا در پردازش درخواست: {e}")
        return jsonify({'success': False, 'message': 'خطای سرور داخلی'})

@app.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': 'داده‌های ناقص ارسال شده است'})
        
        # جستجوی کاربر با نام کاربری یا شماره تلفن
        user = None
        for username, user_data in users_db.items():
            if username == data['username'] or user_data.get('phone') == data['username']:
                user = user_data
                user['username'] = username
                break
        
        if not user:
            return jsonify({'success': False, 'message': 'کاربری با این مشخصات یافت نشد'})
        
        # بررسی رمز عبور
        if user['password'] != data['password']:
            return jsonify({'success': False, 'message': 'رمز عبور اشتباه است'})
        
        return jsonify({
            'success': True, 
            'message': 'ورود موفقیت‌آمیز بود',
            'user': {
                'username': user['username'],
                'phone': user.get('phone', ''),
                'city': user.get('city', ''),
            }
        })
        
    except Exception as e:
        print(f"خطا در پردازش درخواست: {e}")
        return jsonify({'success': False, 'message': 'خطای سرور داخلی'})

@app.route('/add_place', methods=['POST'])
def add_place():
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'mainCategory' not in data or 'subCategory' not in data:
            return jsonify({'success': False, 'message': 'داده‌های ناقص ارسال شده است'})
        
        # افزودن مکان به دیتابیس
        place = {
            'id': len(places_db) + 1,
            'name': data['name'],
            'mainCategory': data['mainCategory'],
            'subCategory': data['subCategory'],
            'city': data['city'],
            'address': data.get('address', ''),
            'addedBy': data.get('addedBy', ''),
            'addedAt': datetime.now().isoformat()
        }
        
        places_db.append(place)
        
        return jsonify({
            'success': True, 
            'message': 'مکان با موفقیت ثبت شد',
            'place': place
        })
        
    except Exception as e:
        print(f"خطا در پردازش درخواست: {e}")
        return jsonify({'success': False, 'message': 'خطای سرور داخلی'})

@app.route('/get_places', methods=['GET'])
def get_places():
    return jsonify({
        'success': True,
        'places': places_db
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)