from flask import Flask, render_template_string, request, jsonify
import re
import json
from datetime import datetime

app = Flask(__name__)

# HTML template as a string
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>فرم ثبت نام پیشرفته</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap');
        
        :root {
            --primary: #6c63ff;
            --secondary: #ff6584;
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
            box-shadow: 0 0 0 2px rgba(108, 99, 255, 0.2);
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
        
        .success-message {
            display: none;
            background-color: var(--success);
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-top: 20px;
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
            <h1>ایجاد حساب کاربری</h1>
            <p>برای دسترسی به تمام امکانات سایت ثبت نام کنید</p>
        </div>
        
        <div class="form-container">
            <form id="registrationForm">
                <div class="form-group">
                    <label for="fullname">نام کامل</label>
                    <input type="text" id="fullname" class="form-control" placeholder="نام و نام خانوادگی خود را وارد کنید">
                    <div class="error-message" id="fullname-error">لطفاً نام خود را وارد کنید</div>
                </div>
                
                <div class="form-group">
                    <label for="email">ایمیل</label>
                    <input type="email" id="email" class="form-control" placeholder="example@domain.com">
                    <div class="error-message" id="email-error">لطفاً یک ایمیل معتبر وارد کنید</div>
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
                
                <div class="success-message" id="successMessage">
                    ثبت نام با موفقیت انجام شد!
                </div>
                
                <div class="login-link">
                    قبلاً حساب دارید؟ <a href="#">وارد شوید</a>
                </div>
            </form>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('registrationForm');
            const togglePassword = document.getElementById('togglePassword');
            const passwordInput = document.getElementById('password');
            const successMessage = document.getElementById('successMessage');
            
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
                
                // اعتبارسنجی نام
                const fullname = document.getElementById('fullname');
                const fullnameError = document.getElementById('fullname-error');
                if (fullname.value.trim() === '') {
                    fullname.classList.add('error');
                    fullnameError.style.display = 'block';
                    isValid = false;
                } else {
                    fullname.classList.remove('error');
                    fullnameError.style.display = 'none';
                }
                
                // اعتبارسنجی ایمیل
                const email = document.getElementById('email');
                const emailError = document.getElementById('email-error');
                const emailPattern = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
                if (!emailPattern.test(email.value)) {
                    email.classList.add('error');
                    emailError.style.display = 'block';
                    isValid = false;
                } else {
                    email.classList.remove('error');
                    emailError.style.display = 'none';
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
                        fullname: fullname.value,
                        email: email.value,
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
                            // نمایش پیام موفقیت
                            successMessage.style.display = 'block';
                            form.reset();
                            
                            // پنهان کردن پیام پس از 3 ثانیه
                            setTimeout(() => {
                                successMessage.style.display = 'none';
                            }, 3000);
                        } else {
                            alert('خطا در ثبت نام: ' + data.message);
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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/register', methods=['POST'])
def register():
    try:
        # دریافت داده‌های JSON از درخواست
        data = request.get_json()
        
        # اعتبارسنجی داده‌ها در سمت سرور
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': 'داده‌های ناقص ارسال شده است'})
        
        # بررسی ایمیل
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(data['email']):
            return jsonify({'success': False, 'message': 'ایمیل معتبر نیست'})
        
        # بررسی شماره تلفن
        if 'phone' in data:
            phone_pattern = re.compile(r'^09\d{9}$')
            if not phone_pattern.match(data['phone']):
                return jsonify({'success': False, 'message': 'شماره تلفن معتبر نیست'})
        
        # بررسی رمز عبور
        if len(data['password']) < 6:
            return jsonify({'success': False, 'message': 'رمز عبور باید حداقل ۶ کاراکتر باشد'})
        
        # در اینجا معمولاً اطلاعات در دیتابیس ذخیره می‌شوند
        # برای نمونه، فقط داده‌ها را چاپ می‌کنیم
        print("ثبت نام جدید:")
        print(f"نام: {data.get('fullname', '')}")
        print(f"ایمیل: {data['email']}")
        print(f"تلفن: {data.get('phone', '')}")
        print(f"زمان: {data.get('timestamp', '')}")
        
        # پاسخ موفقیت‌آمیز
        return jsonify({
            'success': True, 
            'message': 'ثبت نام با موفقیت انجام شد',
            'user': {
                'email': data['email'],
                'name': data.get('fullname', ''),
                'registered_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"خطا در پردازش درخواست: {e}")
        return jsonify({'success': False, 'message': 'خطای سرور داخلی'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)