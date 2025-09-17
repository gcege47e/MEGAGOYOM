import os
import sqlite3
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-key-for-development-12345')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# ایجاد پوشه آپلود اگر وجود ندارد
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ایجاد دیتابیس و جداول
def init_db():
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # جدول کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  age INTEGER NOT NULL,
                  gender TEXT NOT NULL,
                  password TEXT NOT NULL,
                  score INTEGER DEFAULT 0,
                  unique_id TEXT UNIQUE NOT NULL,
                  is_admin INTEGER DEFAULT 0,
                  is_blocked INTEGER DEFAULT 0,
                  free_places INTEGER DEFAULT 2,
                  premium_until DATE)''')
    
    # جدول مکان‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS places
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  category TEXT NOT NULL,
                  subcategory TEXT NOT NULL,
                  title TEXT NOT NULL,
                  description TEXT NOT NULL,
                  address TEXT NOT NULL,
                  phone TEXT,
                  images TEXT,
                  morning_shift TEXT,
                  evening_shift TEXT,
                  total_score INTEGER DEFAULT 0,
                  vote_count INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # جدول امتیازات
    c.execute('''CREATE TABLE IF NOT EXISTS ratings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  place_id INTEGER NOT NULL,
                  rating INTEGER NOT NULL,
                  rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  FOREIGN KEY (place_id) REFERENCES places (id),
                  UNIQUE(user_id, place_id))''')
    
    # جدول نظرات
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  place_id INTEGER NOT NULL,
                  comment TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  FOREIGN KEY (place_id) REFERENCES places (id))''')
    
    # جدول پیام‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender_id INTEGER NOT NULL,
                  receiver_id INTEGER NOT NULL,
                  message TEXT NOT NULL,
                  message_type TEXT DEFAULT 'text',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (sender_id) REFERENCES users (id),
                  FOREIGN KEY (receiver_id) REFERENCES users (id))''')
    
    # جدول بلاک‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS blocks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  blocker_id INTEGER NOT NULL,
                  blocked_id INTEGER NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (blocker_id) REFERENCES users (id),
                  FOREIGN KEY (blocked_id) REFERENCES users (id),
                  UNIQUE(blocker_id, blocked_id))''')
    
    # جدول اخبار
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  content TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول گزارش‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  content TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # ایجاد کاربر ادمین پیش‌فرض
    c.execute("SELECT * FROM users WHERE is_admin = 1")
    admin = c.fetchone()
    if not admin:
        admin_unique_id = str(random.randint(100000000, 999999999))
        c.execute("INSERT INTO users (username, age, gender, password, unique_id, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                  ('admin', 30, 'دیگر', generate_password_hash('admin123'), admin_unique_id, 1))
    
    conn.commit()
    conn.close()

init_db()

# تابع برای تولید شناسه تصادفی
def generate_unique_id():
    return str(random.randint(100000000, 999999999))

# تابع برای بررسی اینکه کاربر ادمین است یا نه
def is_admin():
    if 'user_id' in session:
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        c.execute("SELECT is_admin FROM users WHERE id = ?", (session['user_id'],))
        user = c.fetchone()
        conn.close()
        return user and user[0] == 1
    return False

# تابع برای بررسی اینکه کاربر بلاک شده است یا نه
def is_blocked():
    if 'user_id' in session:
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        c.execute("SELECT is_blocked FROM users WHERE id = ?", (session['user_id'],))
        user = c.fetchone()
        conn.close()
        return user and user[0] == 1
    return False

# صفحه اصلی
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('welcome'))
    
    if is_blocked():
        return render_template('blocked.html')
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # دریافت مکان‌های برتر
    c.execute('''SELECT p.*, u.username 
                 FROM places p 
                 JOIN users u ON p.user_id = u.id 
                 WHERE p.vote_count >= 100 AND (p.total_score * 1.0 / p.vote_count) >= 8 
                 ORDER BY (p.total_score * 1.0 / p.vote_count) DESC 
                 LIMIT 10''')
    top_places = c.fetchall()
    
    # دریافت آخرین مکان‌ها
    c.execute('''SELECT p.*, u.username 
                 FROM places p 
                 JOIN users u ON p.user_id = u.id 
                 ORDER BY p.created_at DESC 
                 LIMIT 20''')
    recent_places = c.fetchall()
    
    # دریافت دسته‌بندی‌ها
    categories = [
        "🍽️ خوراکی و نوشیدنی",
        "🛍️ خرید و فروش",
        "✂️ زیبایی و آرایشی",
        "🏥 درمان و سلامت",
        "⚽ ورزش و سرگرمی",
        "🏨 اقامت و سفر",
        "🏛️ خدمات عمومی و اداری",
        "🚗 خدمات شهری و حمل‌ونقل",
        "📚 آموزش و فرهنگ",
        "🕌 مذهبی و معنوی",
        "🌳 طبیعت و تفریح آزاد",
        "💼 کسب‌وکار و حرفه‌ای",
        "🧰 خدمات تخصصی و فنی"
    ]
    
    conn.close()
    
    return render_template('index.html', 
                         top_places=top_places, 
                         recent_places=recent_places,
                         categories=categories,
                         is_admin=is_admin())

# صفحه خوش‌آمدگویی
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

# ثبت‌نام کاربر
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        age = int(request.form['age'])
        gender = request.form['gender']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        accept_rules = 'accept_rules' in request.form
        
        if not accept_rules:
            flash('لطفاً قوانین را بپذیرید', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('رمز عبور و تکرار آن مطابقت ندارند', 'error')
            return redirect(url_for('register'))
        
        if age < 13 or age > 70:
            flash('سن باید بین 13 تا 70 سال باشد', 'error')
            return redirect(url_for('register'))
        
        unique_id = generate_unique_id()
        hashed_password = generate_password_hash(password)
        
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO users (username, age, gender, password, unique_id) VALUES (?, ?, ?, ?, ?)",
                      (username, age, gender, hashed_password, unique_id))
            conn.commit()
            flash('ثبت‌نام با موفقیت انجام شد. لطفاً وارد شوید.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('نام کاربری قبلاً استفاده شده است', 'error')
            return redirect(url_for('register'))
        finally:
            conn.close()
    
    return render_template('register.html')

# ورود کاربر
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[4], password):
            if user[8] == 1:  # کاربر بلاک شده
                flash('حساب شما مسدود شده است. لطفاً با ادمین تماس بگیرید.', 'error')
                return redirect(url_for('login'))
            
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[7] == 1
            flash('ورود موفقیت‌آمیز بود', 'success')
            return redirect(url_for('index'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

# خروج کاربر
@app.route('/logout')
def logout():
    session.clear()
    flash('با موفقیت خارج شدید', 'success')
    return redirect(url_for('index'))

# پروفایل کاربر
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = c.fetchone()
    
    # دریافت مکان‌های کاربر
    c.execute("SELECT * FROM places WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],))
    user_places = c.fetchall()
    
    conn.close()
    
    return render_template('profile.html', user=user, user_places=user_places, is_admin=is_admin())

# ویرایش پروفایل
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        username = request.form['username']
        age = int(request.form['age'])
        gender = request.form['gender']
        
        try:
            c.execute("UPDATE users SET username = ?, age = ?, gender = ? WHERE id = ?",
                      (username, age, gender, session['user_id']))
            conn.commit()
            session['username'] = username
            flash('پروفایل با موفقیت به‌روزرسانی شد', 'success')
            return redirect(url_for('profile'))
        except sqlite3.IntegrityError:
            flash('نام کاربری قبلاً استفاده شده است', 'error')
            return redirect(url_for('edit_profile'))
    
    c.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = c.fetchone()
    conn.close()
    
    return render_template('edit_profile.html', user=user)

# تبدیل به ادمین
@app.route('/become_admin', methods=['POST'])
def become_admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    admin_code = request.form['admin_code']
    
    # کد ادمین (فقط شما می‌دانید)
    if admin_code == 'YOUR_SECRET_ADMIN_CODE':
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (session['user_id'],))
        conn.commit()
        conn.close()
        
        session['is_admin'] = True
        flash('تبدیل به ادمین با موفقیت انجام شد', 'success')
    else:
        flash('کد ادمین اشتباه است', 'error')
    
    return redirect(url_for('profile'))

# اضافه کردن مکان
@app.route('/add_place', methods=['GET', 'POST'])
def add_place():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if is_blocked():
        return render_template('blocked.html')
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    c.execute("SELECT free_places, premium_until FROM users WHERE id = ?", (session['user_id'],))
    user = c.fetchone()
    
    free_places = user[0]
    premium_until = user[1]
    
    # بررسی امکان اضافه کردن مکان
    can_add = free_places > 0 or (premium_until and datetime.strptime(premium_until, '%Y-%m-%d').date() >= datetime.now().date())
    
    if not can_add and not is_admin():
        flash('امکان اضافه کردن مکان جدید وجود ندارد. لطفاً حساب خود را ارتقا دهید.', 'error')
        return redirect(url_for('premium'))
    
    if request.method == 'POST':
        category = request.form['category']
        subcategory = request.form['subcategory']
        title = request.form['title']
        description = request.form['description']
        address = request.form['address']
        phone = request.form.get('phone', '')
        morning_shift = request.form.get('morning_shift', '')
        evening_shift = request.form.get('evening_shift', '')
        
        # بررسی حداقل طول توضیحات
        if len(description.split()) < 10:
            flash('توضیحات باید حداقل 10 کلمه باشد', 'error')
            return redirect(url_for('add_place'))
        
        # بررسی شماره تلفن
        if phone and (not phone.startswith('09') or len(phone) != 11 or not phone.isdigit()):
            flash('شماره تلفن باید با 09 شروع شده و 11 رقمی باشد', 'error')
            return redirect(url_for('add_place'))
        
        # آپلود عکس‌ها
        images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    images.append(filename)
        
        # ذخیره مکان در دیتابیس
        images_str = json.dumps(images) if images else None
        
        c.execute('''INSERT INTO places 
                    (user_id, category, subcategory, title, description, address, phone, images, morning_shift, evening_shift) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (session['user_id'], category, subcategory, title, description, address, phone, images_str, morning_shift, evening_shift))
        
        # کاهش تعداد مکان‌های رایگان کاربر
        if not is_admin() and free_places > 0:
            c.execute("UPDATE users SET free_places = free_places - 1 WHERE id = ?", (session['user_id'],))
        
        # افزایش امتیاز کاربر
        c.execute("UPDATE users SET score = score + 83 WHERE id = ?", (session['user_id'],))
        
        conn.commit()
        conn.close()
        
        flash('مکان با موفقیت اضافه شد', 'success')
        return redirect(url_for('index'))
    
    # دریافت زیردسته‌ها بر اساس دسته انتخاب شده
    selected_category = request.args.get('category', '')
    subcategories = []
    
    if selected_category:
        # اینجا می‌توانید زیردسته‌های مربوط به هر دسته را تعریف کنید
        subcategories_dict = {
            "🍽️ خوراکی و نوشیدنی": ["رستوران‌ها", "کافه و کافی‌شاپ", "بستنی‌فروشی و آبمیوه‌فروشی", "شیرینی‌پزی و نانوایی"],
            "🛍️ خرید و فروش": ["پاساژها و مراکز خرید", "سوپرمارکت و هایپرمارکت", "فروشگاه پوشاک", "فروشگاه لوازم خانگی"],
            # سایر دسته‌ها و زیردسته‌ها
        }
        subcategories = subcategories_dict.get(selected_category, [])
    
    conn.close()
    
    return render_template('add_place.html', 
                         categories=categories,
                         subcategories=subcategories,
                         free_places=free_places,
                         premium_until=premium_until,
                         is_admin=is_admin())

# مشاهده مکان‌ها
@app.route('/places')
def places():
    category = request.args.get('category', '')
    subcategory = request.args.get('subcategory', '')
    area = request.args.get('area', '')
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    query = '''SELECT p.*, u.username, 
               (p.total_score * 1.0 / p.vote_count) as avg_rating 
               FROM places p 
               JOIN users u ON p.user_id = u.id 
               WHERE 1=1'''
    params = []
    
    if category:
        query += " AND p.category = ?"
        params.append(category)
    
    if subcategory:
        query += " AND p.subcategory = ?"
        params.append(subcategory)
    
    if area:
        query += " AND p.address LIKE ?"
        params.append(f'%{area}%')
    
    query += " ORDER BY p.created_at DESC"
    
    c.execute(query, params)
    places_list = c.fetchall()
    
    conn.close()
    
    return render_template('places.html', 
                         places=places_list, 
                         category=category,
                         subcategory=subcategory,
                         area=area,
                         is_admin=is_admin())

# جستجوی مکان‌ها
@app.route('/search')
def search():
    query = request.args.get('q', '')
    
    if not query:
        return redirect(url_for('places'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # جستجو در عنوان و آدرس
    search_query = '''SELECT p.*, u.username, 
                     (p.total_score * 1.0 / p.vote_count) as avg_rating 
                     FROM places p 
                     JOIN users u ON p.user_id = u.id 
                     WHERE p.title LIKE ? OR p.address LIKE ? 
                     ORDER BY p.created_at DESC'''
    
    search_param = f'%{query}%'
    c.execute(search_query, (search_param, search_param))
    results = c.fetchall()
    
    conn.close()
    
    return render_template('search.html', 
                         results=results, 
                         query=query,
                         is_admin=is_admin())

# جزئیات مکان
@app.route('/place/<int:place_id>')
def place_detail(place_id):
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # دریافت اطلاعات مکان
    c.execute('''SELECT p.*, u.username, u.unique_id,
                 (p.total_score * 1.0 / p.vote_count) as avg_rating 
                 FROM places p 
                 JOIN users u ON p.user_id = u.id 
                 WHERE p.id = ?''', (place_id,))
    place = c.fetchone()
    
    if not place:
        flash('مکان مورد نظر یافت نشد', 'error')
        return redirect(url_for('index'))
    
    # دریافت نظرات
    c.execute('''SELECT c.*, u.username, u.age, u.gender, u.unique_id 
                 FROM comments c 
                 JOIN users u ON c.user_id = u.id 
                 WHERE c.place_id = ? 
                 ORDER BY c.created_at DESC''', (place_id,))
    comments = c.fetchall()
    
    # بررسی آیا کاربر قبلاً به این مکان امتیاز داده است
    user_rated = False
    if 'user_id' in session:
        c.execute("SELECT * FROM ratings WHERE user_id = ? AND place_id = ?", 
                 (session['user_id'], place_id))
        user_rated = c.fetchone() is not None
    
    conn.close()
    
    # تبدیل رشته JSON عکس‌ها به لیست
    images = json.loads(place[8]) if place[8] else []
    
    return render_template('place_detail.html', 
                         place=place, 
                         comments=comments,
                         images=images,
                         user_rated=user_rated,
                         is_admin=is_admin())

# امتیازدهی به مکان
@app.route('/rate_place/<int:place_id>', methods=['POST'])
def rate_place(place_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if is_blocked():
        return render_template('blocked.html')
    
    rating = int(request.form['rating'])
    
    if rating < 0 or rating > 10:
        flash('امتیاز باید بین 0 تا 10 باشد', 'error')
        return redirect(url_for('place_detail', place_id=place_id))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # بررسی آیا کاربر قبلاً به این مکان امتیاز داده است
    c.execute("SELECT * FROM ratings WHERE user_id = ? AND place_id = ?", 
             (session['user_id'], place_id))
    
    if c.fetchone():
        flash('شما قبلاً به این مکان امتیاز داده‌اید', 'error')
        conn.close()
        return redirect(url_for('place_detail', place_id=place_id))
    
    # ثبت امتیاز
    c.execute("INSERT INTO ratings (user_id, place_id, rating) VALUES (?, ?, ?)",
             (session['user_id'], place_id, rating))
    
    # به‌روزرسانی امتیاز کلی مکان
    c.execute("UPDATE places SET total_score = total_score + ?, vote_count = vote_count + 1 WHERE id = ?",
             (rating, place_id))
    
    conn.commit()
    
    # بررسی آیا مکان به لیست برترها اضافه شده یا از آن خارج شده
    c.execute('''SELECT total_score, vote_count FROM places WHERE id = ?''', (place_id,))
    place_data = c.fetchone()
    avg_rating = place_data[0] / place_data[1] if place_data[1] > 0 else 0
    
    c.execute("SELECT title FROM places WHERE id = ?", (place_id,))
    place_title = c.fetchone()[0]
    
    c.execute("SELECT user_id FROM places WHERE id = ?", (place_id,))
    owner_id = c.fetchone()[0]
    
    # اگر مکان به برترها اضافه شده
    if place_data[1] >= 100 and avg_rating >= 8:
        # ارسال پیام به صاحب مکان
        message = f"مکان شما با نام '{place_title}' وارد بخش مکان‌های برتر شد، به شما تبریک می‌گویم"
        c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (0, owner_id, message))  # sender_id=0 برای سیستم
    
    # اگر مکان از برترها خارج شده
    elif place_data[1] >= 100 and avg_rating < 8:
        # ارسال پیام به صاحب مکان
        message = f"دیگر مکان شما '{place_title}' در مکان‌های برتر نیست"
        c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (0, owner_id, message))  # sender_id=0 برای سیستم
    
    conn.commit()
    conn.close()
    
    flash('امتیاز شما با موفقیت ثبت شد', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

# اضافه کردن نظر
@app.route('/add_comment/<int:place_id>', methods=['POST'])
def add_comment(place_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if is_blocked():
        return render_template('blocked.html')
    
    comment = request.form['comment']
    
    if not comment:
        flash('لطفاً نظر خود را وارد کنید', 'error')
        return redirect(url_for('place_detail', place_id=place_id))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # ثبت نظر
    c.execute("INSERT INTO comments (user_id, place_id, comment) VALUES (?, ?, ?)",
             (session['user_id'], place_id, comment))
    
    # ارسال پیام به صاحب مکان
    c.execute("SELECT user_id, title FROM places WHERE id = ?", (place_id,))
    place_data = c.fetchone()
    owner_id = place_data[0]
    place_title = place_data[1]
    
    c.execute("SELECT username, age, gender FROM users WHERE id = ?", (session['user_id'],))
    user_data = c.fetchone()
    username = user_data[0]
    age = user_data[1]
    gender = user_data[2]
    
    gender_text = {
        'پسر': 'پسر',
        'دختر': 'دختر',
        'دیگر': 'دیگر'
    }.get(gender, 'دیگر')
    
    message = f"کاربر {username} ({age} ساله، {gender_text}) این نظر را برای مکان '{place_title}' داده است: {comment}"
    
    c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
             (0, owner_id, message))  # sender_id=0 برای سیستم
    
    conn.commit()
    conn.close()
    
    flash('نظر شما با موفقیت ثبت شد', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

# حذف نظر
@app.route('/delete_comment/<int:comment_id>')
def delete_comment(comment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # بررسی آیا نظر متعلق به کاربر است یا کاربر ادمین است
    c.execute("SELECT user_id, place_id FROM comments WHERE id = ?", (comment_id,))
    comment = c.fetchone()
    
    if not comment:
        flash('نظر مورد نظر یافت نشد', 'error')
        return redirect(url_for('index'))
    
    user_id, place_id = comment
    
    if user_id != session['user_id'] and not is_admin():
        flash('شما اجازه حذف این نظر را ندارید', 'error')
        return redirect(url_for('place_detail', place_id=place_id))
    
    # حذف نظر
    c.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()
    
    flash('نظر با موفقیت حذف شد', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

# ارسال پیام به صاحب مکان
@app.route('/send_message/<int:place_id>', methods=['POST'])
def send_message(place_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if is_blocked():
        return render_template('blocked.html')
    
    message = request.form['message']
    
    if not message:
        flash('لطفاً پیام خود را وارد کنید', 'error')
        return redirect(url_for('place_detail', place_id=place_id))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # دریافت شناسه صاحب مکان
    c.execute("SELECT user_id FROM places WHERE id = ?", (place_id,))
    owner_id = c.fetchone()[0]
    
    # بررسی آیا کاربر بلاک شده است
    c.execute("SELECT * FROM blocks WHERE blocker_id = ? AND blocked_id = ?", 
             (owner_id, session['user_id']))
    
    if c.fetchone():
        flash('شما توسط صاحب این مکان بلاک شده‌اید', 'error')
        conn.close()
        return redirect(url_for('place_detail', place_id=place_id))
    
    # ارسال پیام
    c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
             (session['user_id'], owner_id, message))
    
    conn.commit()
    conn.close()
    
    flash('پیام شما با موفقیت ارسال شد', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

# بلاک کردن کاربر
@app.route('/block_user/<int:user_id>')
def block_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # بررسی آیا کاربر صاحب مکان است یا ادمین
    c.execute("SELECT id FROM places WHERE user_id = ?", (session['user_id'],))
    user_places = c.fetchall()
    
    if not user_places and not is_admin():
        flash('شما اجازه این عمل را ندارید', 'error')
        return redirect(url_for('index'))
    
    # بلاک کردن کاربر
    try:
        c.execute("INSERT INTO blocks (blocker_id, blocked_id) VALUES (?, ?)",
                 (session['user_id'], user_id))
        conn.commit()
        
        # ارسال پیام به کاربر بلاک شده
        c.execute("SELECT username FROM users WHERE id = ?", (session['user_id'],))
        blocker_username = c.fetchone()[0]
        
        c.execute("SELECT title FROM places WHERE user_id = ? LIMIT 1", (session['user_id'],))
        place_title = c.fetchone()
        place_title = place_title[0] if place_title else "مکان نامشخص"
        
        message = f"صاحب مکان '{place_title}' شما را بلاک کرده است"
        c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (0, user_id, message))  # sender_id=0 برای سیستم
        
        conn.commit()
        flash('کاربر با موفقیت بلاک شد', 'success')
    except sqlite3.IntegrityError:
        flash('این کاربر قبلاً بلاک شده است', 'error')
    
    conn.close()
    return redirect(request.referrer or url_for('index'))

# رفع بلاک کاربر
@app.route('/unblock_user/<int:user_id>')
def unblock_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # رفع بلاک کاربر
    c.execute("DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?",
             (session['user_id'], user_id))
    
    if c.rowcount > 0:
        # ارسال پیام به کاربر
        c.execute("SELECT username FROM users WHERE id = ?", (session['user_id'],))
        unblocker_username = c.fetchone()[0]
        
        c.execute("SELECT title FROM places WHERE user_id = ? LIMIT 1", (session['user_id'],))
        place_title = c.fetchone()
        place_title = place_title[0] if place_title else "مکان نامشخص"
        
        message = f"شما از طرف صاحب مکان '{place_title}' رفع بلاک شده‌اید و می‌توانید دوباره پیام ارسال کنید"
        c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (0, user_id, message))  # sender_id=0 برای سیستم
        
        conn.commit()
        flash('بلاک کاربر با موفقیت برداشته شد', 'success')
    else:
        flash('این کاربر بلاک نشده بود', 'error')
    
    conn.close()
    return redirect(request.referrer or url_for('index'))

# پنل ادمین
@app.route('/admin')
def admin_panel():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # آمار کاربران
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
    blocked_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE gender = 'پسر'")
    male_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE gender = 'دختر'")
    female_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE gender = 'دیگر'")
    other_users = c.fetchone()[0]
    
    # آمار مکان‌ها
    c.execute("SELECT COUNT(*) FROM places")
    total_places = c.fetchone()[0]
    
    conn.close()
    
    return render_template('admin_panel.html',
                         total_users=total_users,
                         blocked_users=blocked_users,
                         male_users=male_users,
                         female_users=female_users,
                         other_users=other_users,
                         total_places=total_places,
                         is_admin=is_admin())

# مدیریت کاربران توسط ادمین
@app.route('/admin/users')
def admin_users():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    c.execute('''SELECT id, username, age, gender, score, unique_id, is_blocked 
                 FROM users 
                 ORDER BY score DESC''')
    users = c.fetchall()
    
    conn.close()
    
    return render_template('admin_users.html', users=users, is_admin=is_admin())

# مسدود کردن کاربر توسط ادمین
@app.route('/admin/block_user/<int:user_id>')
def admin_block_user(user_id):
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    c.execute("UPDATE users SET is_blocked = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash('کاربر با موفقیت مسدود شد', 'success')
    return redirect(url_for('admin_users'))

# رفع مسدودیت کاربر توسط ادمین
@app.route('/admin/unblock_user/<int:user_id>')
def admin_unblock_user(user_id):
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    c.execute("UPDATE users SET is_blocked = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash('مسدودیت کاربر با موفقیت برداشته شد', 'success')
    return redirect(url_for('admin_users'))

# مدیریت مکان‌ها توسط ادمین
@app.route('/admin/places')
def admin_places():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    c.execute('''SELECT p.*, u.username 
                 FROM places p 
                 JOIN users u ON p.user_id = u.id 
                 ORDER BY p.created_at DESC''')
    places = c.fetchall()
    
    conn.close()
    
    return render_template('admin_places.html', places=places, is_admin=is_admin())

# حذف مکان توسط ادمین
@app.route('/admin/delete_place/<int:place_id>')
def admin_delete_place(place_id):
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM places WHERE id = ?", (place_id,))
    c.execute("DELETE FROM ratings WHERE place_id = ?", (place_id,))
    c.execute("DELETE FROM comments WHERE place_id = ?", (place_id,))
    
    conn.commit()
    conn.close()
    
    flash('مکان با موفقیت حذف شد', 'success')
    return redirect(url_for('admin_places'))

# ویرایش مکان توسط ادمین
@app.route('/admin/edit_place/<int:place_id>', methods=['GET', 'POST'])
def admin_edit_place(place_id):
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        category = request.form['category']
        subcategory = request.form['subcategory']
        title = request.form['title']
        description = request.form['description']
        address = request.form['address']
        phone = request.form.get('phone', '')
        morning_shift = request.form.get('morning_shift', '')
        evening_shift = request.form.get('evening_shift', '')
        
        # آپلود عکس‌های جدید
        images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    images.append(filename)
        
        # اگر عکس جدید آپلود شده، جایگزین عکس‌های قبلی می‌شود
        if images:
            images_str = json.dumps(images)
            c.execute('''UPDATE places 
                         SET category=?, subcategory=?, title=?, description=?, address=?, phone=?, images=?, morning_shift=?, evening_shift=?
                         WHERE id=?''',
                     (category, subcategory, title, description, address, phone, images_str, morning_shift, evening_shift, place_id))
        else:
            c.execute('''UPDATE places 
                         SET category=?, subcategory=?, title=?, description=?, address=?, phone=?, morning_shift=?, evening_shift=?
                         WHERE id=?''',
                     (category, subcategory, title, description, address, phone, morning_shift, evening_shift, place_id))
        
        conn.commit()
        conn.close()
        
        flash('مکان با موفقیت ویرایش شد', 'success')
        return redirect(url_for('admin_places'))
    
    c.execute("SELECT * FROM places WHERE id = ?", (place_id,))
    place = c.fetchone()
    
    conn.close()
    
    # تبدیل رشته JSON عکس‌ها به لیست
    images = json.loads(place[8]) if place[8] else []
    
    return render_template('admin_edit_place.html', 
                         place=place, 
                         images=images,
                         categories=categories,
                         is_admin=is_admin())

# ارسال خبر گروهی
@app.route('/admin/send_news', methods=['GET', 'POST'])
def admin_send_news():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        content = request.form['content']
        
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        
        c.execute("INSERT INTO news (content) VALUES (?)", (content,))
        conn.commit()
        conn.close()
        
        flash('خبر با موفقیت ارسال شد', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin_send_news.html', is_admin=is_admin())

# حذف آخرین خبر
@app.route('/admin/delete_last_news')
def admin_delete_last_news():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    c.execute("SELECT id FROM news ORDER BY id DESC LIMIT 1")
    last_news = c.fetchone()
    
    if last_news:
        c.execute("DELETE FROM news WHERE id = ?", (last_news[0],))
        conn.commit()
        flash('آخرین خبر با موفقیت حذف شد', 'success')
    else:
        flash('خبری برای حذف وجود ندارد', 'error')
    
    conn.close()
    return redirect(url_for('admin_panel'))

# ارسال خبر به کاربر خاص
@app.route('/admin/send_news_to_user', methods=['GET', 'POST'])
def admin_send_news_to_user():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        content = request.form['content']
        
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        
        c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (0, user_id, content))  # sender_id=0 برای سیستم
        
        conn.commit()
        conn.close()
        
        flash('خبر با موفقیت ارسال شد', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin_send_news_to_user.html', is_admin=is_admin())

# مدیریت امتیاز کاربران
@app.route('/admin/manage_scores', methods=['GET', 'POST'])
def admin_manage_scores():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        score_change = int(request.form['score_change'])
        
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        
        c.execute("UPDATE users SET score = score + ? WHERE id = ?", (score_change, user_id))
        conn.commit()
        conn.close()
        
        flash('امتیاز کاربر با موفقیت تغییر کرد', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin_manage_scores.html', is_admin=is_admin())

# قرارگیری مکان برتر (افزودن یا کم کردن رای)
@app.route('/admin/manage_ratings', methods=['GET', 'POST'])
def admin_manage_ratings():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form['action']  # add یا remove
        place_title = request.form['place_title']
        owner_unique_id = request.form['owner_unique_id']
        vote_count = int(request.form['vote_count'])
        rating_avg = float(request.form['rating_avg'])
        
        if rating_avg < 0 or rating_avg > 10:
            flash('امتیاز باید بین 0 تا 10 باشد', 'error')
            return redirect(url_for('admin_manage_ratings'))
        
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        
        # یافتن مکان بر اساس عنوان و شناسه صاحب
        c.execute('''SELECT p.id, p.total_score, p.vote_count 
                     FROM places p 
                     JOIN users u ON p.user_id = u.id 
                     WHERE p.title = ? AND u.unique_id = ?''', 
                 (place_title, owner_unique_id))
        
        place = c.fetchone()
        
        if not place:
            flash('مکان مورد نظر یافت نشد', 'error')
            conn.close()
            return redirect(url_for('admin_manage_ratings'))
        
        place_id, current_total, current_count = place
        
        if action == 'add':
            new_total = current_total + (rating_avg * vote_count)
            new_count = current_count + vote_count
        else:  # remove
            new_total = max(0, current_total - (rating_avg * vote_count))
            new_count = max(0, current_count - vote_count)
        
        # به‌روزرسانی امتیاز مکان
        c.execute("UPDATE places SET total_score = ?, vote_count = ? WHERE id = ?",
                 (new_total, new_count, place_id))
        
        conn.commit()
        conn.close()
        
        flash('رای‌های مکان با موفقیت تغییر کرد', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin_manage_ratings.html', is_admin=is_admin())

# مدیریت نظرات
@app.route('/admin/manage_comments', methods=['GET', 'POST'])
def admin_manage_comments():
    if not is_admin():
        flash('شما اجازه دسترسی به این صفحه را ندارید', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        place_title = request.form['place_title']
        owner_unique_id = request.form['owner_unique_id']
        comment_start = request.form['comment_start']
        commenter_unique_id = request.form['commenter_unique_id']
        
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        
        # یافتن نظر بر اساس معیارها
        c.execute('''SELECT c.id 
                     FROM comments c 
                     JOIN places p ON c.place_id = p.id 
                     JOIN users u1 ON p.user_id = u1.id 
                     JOIN users u2 ON c.user_id = u2.id 
                     WHERE p.title = ? AND u1.unique_id = ? 
                     AND c.comment LIKE ? AND u2.unique_id = ?''',
                 (place_title, owner_unique_id, f'{comment_start}%', commenter_unique_id))
        
        comment = c.fetchone()
        
        if not comment:
            flash('نظر مورد نظر یافت نشد', 'error')
            conn.close()
            return redirect(url_for('admin_manage_comments'))
        
        comment_id = comment[0]
        
        # حذف نظر
        c.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        
        # ارسال پیام به کاربر
        c.execute("SELECT user_id FROM comments WHERE id = ?", (comment_id,))
        commenter_id = c.fetchone()[0]
        
        message = f"نظر شما در نظرات مکان '{place_title}' توسط ادمین به دلیل نقض قوانین حذف شد"
        c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (0, commenter_id, message))  # sender_id=0 برای سیستم
        
        conn.commit()
        conn.close()
        
        flash('نظر با موفقیت حذف شد', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin_manage_comments.html', is_admin=is_admin())

# صفحه گزارش
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if is_blocked():
        return render_template('blocked.html')
    
    if request.method == 'POST':
        content = request.form['content']
        
        conn = sqlite3.connect('goimnama.db')
        c = conn.cursor()
        
        # ثبت گزارش
        c.execute("INSERT INTO reports (user_id, content) VALUES (?, ?)",
                 (session['user_id'], content))
        
        # ارسال گزارش به ادمین
        c.execute("SELECT username, age, gender, unique_id FROM users WHERE id = ?", (session['user_id'],))
        user_data = c.fetchone()
        
        admin_message = f"گزارش جدید:\n{content}\n\nاطلاعات کاربر:\nنام: {user_data[0]}\nسن: {user_data[1]}\nجنسیت: {user_data[2]}\nشناسه: {user_data[3]}"
        
        # یافتن ادمین
        c.execute("SELECT id FROM users WHERE is_admin = 1")
        admin_id = c.fetchone()[0]
        
        c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (0, admin_id, admin_message))  # sender_id=0 برای سیستم
        
        conn.commit()
        conn.close()
        
        flash('گزارش شما با موفقیت ارسال شد و پیگیری خواهد شد', 'success')
        return redirect(url_for('index'))
    
    return render_template('report.html', is_admin=is_admin())

# درخواست خرید مکان برتر
@app.route('/request_premium_placement', methods=['GET', 'POST'])
def request_premium_placement():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if is_blocked():
        return render_template('blocked.html')
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # دریافت مکان‌های کاربر
    c.execute("SELECT id, title FROM places WHERE user_id = ?", (session['user_id'],))
    user_places = c.fetchall()
    
    if request.method == 'POST':
        place_id = request.form['place_id']
        
        # دریافت اطلاعات مکان
        c.execute("SELECT title FROM places WHERE id = ?", (place_id,))
        place_title = c.fetchone()[0]
        
        # دریافت اطلاعات کاربر
        c.execute("SELECT username, age, gender, unique_id FROM users WHERE id = ?", (session['user_id'],))
        user_data = c.fetchone()
        
        # ارسال درخواست به ادمین
        message = f"کاربر {user_data[0]} ({user_data[1]} سال، {user_data[2]}) برای شما درخواستی ارسال کرده که این مکان: '{place_title}' برود در بخش مکان‌های برتر. شناسه کاربر: {user_data[3]}"
        
        # یافتن ادمین
        c.execute("SELECT id FROM users WHERE is_admin = 1")
        admin_id = c.fetchone()[0]
        
        c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (0, admin_id, message))  # sender_id=0 برای سیستم
        
        conn.commit()
        conn.close()
        
        flash('درخواست شما با موفقیت ارسال شد', 'success')
        return redirect(url_for('index'))
    
    conn.close()
    
    return render_template('request_premium_placement.html', 
                         user_places=user_places,
                         is_admin=is_admin())

# صفحه ارتقاء حساب
@app.route('/premium')
def premium():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('premium.html', is_admin=is_admin())

# پرداخت برای ارتقاء حساب
@app.route('/payment', methods=['POST'])
def payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # در اینجا کد اتصال به درگاه پرداخت بانک ملی یا کشاورزی قرار می‌گیرد
    # برای نمونه، فرض می‌کنیم پرداخت موفقیت‌آمیز بوده
    
    conn = sqlite3.connect('goimnama.db')
    c = conn.cursor()
    
    # تمدید حساب کاربر به مدت 30 روز
    new_premium_until = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    c.execute("UPDATE users SET premium_until = ? WHERE id = ?", (new_premium_until, session['user_id']))
    
    conn.commit()
    conn.close()
    
    flash('پرداخت با موفقیت انجام شد و حساب شما به مدت 30 روز تمدید شد', 'success')
    return redirect(url_for('profile'))

# صفحه راهنما
@app.route('/help')
def help():
    return render_template('help.html', is_admin=is_admin())

if __name__ == '__main__':
    app.run(debug=True)