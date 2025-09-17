from flask import Flask, render_template_string, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-key-for-development-12345')

# تنظیمات Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# مدل کاربر
class User(UserMixin):
    def init(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name

# ایجاد دیتابیس ساده
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, name TEXT)''')
    conn.commit()
    conn.close()

init_db()

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data:
        return User(id=user_data[0], email=user_data[1], name=user_data[3])
    return None

# HTML templates as strings
LOGIN_HTML = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <title>ورود</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; padding: 20px; }
        .login-container { max-width: 400px; margin: 100px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-container">
            <h2 class="text-center mb-4">ورود به حساب کاربری</h2>
            
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <div class="alert alert-danger">
                        {% for message in messages %}
                            {{ message }}
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="mb-3">
                    <label for="email" class="form-label">ایمیل:</label>
                    <input type="email" class="form-control" id="email" name="email" required>
                </div>
                <div class="mb-3">
                    <label for="password" class="form-label">رمز عبور:</label>
                    <input type="password" class="form-control" id="password" name="password" required>
                </div>
                <button type="submit" class="btn btn-primary w-100">ورود</button>
            </form>
            
            <div class="text-center mt-3">
                <a href="{{ url_for('signup') }}">حساب کاربری ندارید؟ ثبت نام کنید</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

SIGNUP_HTML = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <title>ثبت نام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; padding: 20px; }
        .signup-container { max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <div class="signup-container">
            <h2 class="text-center mb-4">ثبت نام جدید</h2>
            
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <div class="alert alert-danger">
                        {% for message in messages %}
                            {{ message }}

{% endfor %}
                    </div>
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="mb-3">
                    <label for="email" class="form-label">ایمیل:</label>
                    <input type="email" class="form-control" id="email" name="email" required>
                </div>
                <div class="mb-3">
                    <label for="password" class="form-label">رمز عبور:</label>
                    <input type="password" class="form-control" id="password" name="password" required>
                </div>
                <div class="mb-3">
                    <label for="name" class="form-label">نام:</label>
                    <input type="text" class="form-control" id="name" name="name" required>
                </div>
                <button type="submit" class="btn btn-success w-100">ثبت نام</button>
            </form>
            
            <div class="text-center mt-3">
                <a href="{{ url_for('login') }}">قبلا حساب دارید؟ وارد شوید</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

PROFILE_HTML = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <title>پروفایل</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; padding: 20px; }
        .profile-card { max-width: 500px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <div class="profile-card">
            <h2 class="text-center mb-4">پروفایل کاربری</h2>
            <hr>
            
            <div class="mb-3">
                <strong>نام:</strong> {{ user.name }}
            </div>
            
            <div class="mb-3">
                <strong>ایمیل:</strong> {{ user.email }}
            </div>
            
            <div class="text-center">
                <a href="{{ url_for('logout') }}" class="btn btn-danger">خروج (Sign Out)</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

# روت‌های اصلی
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user_data = c.fetchone()
        conn.close()
        
        if user_data:
            user = User(id=user_data[0], email=user_data[1], name=user_data[3])
            login_user(user)
            return redirect(url_for('profile'))
        else:
            flash('ایمیل یا رمز عبور اشتباه است')
    
    return render_template_string(LOGIN_HTML)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                     (email, password, name))
            conn.commit()
            user_id = c.lastrowid
            conn.close()
            
            user = User(id=user_id, email=email, name=name)
            login_user(user)
            return redirect(url_for('profile'))
        except:
            flash('این ایمیل قبلا ثبت شده است')
    
    return render_template_string(SIGNUP_HTML)

@app.route('/profile')
@login_required
def profile():
    return render_template_string(PROFILE_HTML, user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# انتهای فایل SANAMA.py باید اینطوری باشه:

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)