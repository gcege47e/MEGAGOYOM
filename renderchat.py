# -*- coding: utf-8 -*-
from flask import Flask, request, render_template_string, jsonify
import json
import os
import secrets
from datetime import datetime

app = Flask(__name__)

# استفاده از مسیر موقت در Render (قابل نوشتن)
DATA_DIR = os.environ.get('DATA_DIR', '/tmp/hidden_chat_data')
os.makedirs(DATA_DIR, exist_ok=True)

def load_users():
    path = os.path.join(DATA_DIR, "users.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    path = os.path.join(DATA_DIR, "users.json")
    with open(path, "w", encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def load_messages(link_id):
    path = os.path.join(DATA_DIR, f"msgs_{link_id}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding='utf-8') as f:
        return json.load(f)

def save_messages(link_id, msgs):
    path = os.path.join(DATA_DIR, f"msgs_{link_id}.json")
    with open(path, "w", encoding='utf-8') as f:
        json.dump(msgs, f, indent=2, ensure_ascii=False)

def time_ago(dt_str):
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)} s"
    elif seconds < 3600:
        return f"{int(seconds//60)} min"
    elif seconds < 86400:
        return f"{int(seconds//3600)} h"
    else:
        return f"{int(seconds//86400)} d"

# ================== صفحه اصلی (ساخت لینک) ==================
INDEX_HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HIDDEN CHAT - ساخت لینک ناشناس</title>
    <style>
        * { margin:0; padding:0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            font-family: 'Segoe UI', Roboto, sans-serif;
            direction: rtl;
            padding: 2rem 1rem;
            color: #ddd;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .container { max-width: 500px; margin: 0 auto; flex: 1; }
        h1 {
            text-align: center;
            font-size: 2rem;
            letter-spacing: 2px;
            margin-bottom: 2rem;
            color: #fff;
            text-shadow: 0 0 10px #6b8cff, 0 0 5px #9bff8c;
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 5px #6b8cff, 0 0 3px #9bff8c; }
            to { text-shadow: 0 0 15px #6b8cff, 0 0 8px #9bff8c; }
        }
        .card {
            background: #111;
            border-radius: 28px;
            padding: 1.8rem;
            border: 1px solid #2a2a2a;
            box-shadow: 0 0 15px rgba(107, 140, 255, 0.1);
        }
        input {
            width: 100%;
            padding: 1rem;
            margin: 0.7rem 0;
            background: #1e1e1e;
            border: 1px solid #333;
            border-radius: 24px;
            color: white;
            font-size: 1rem;
            transition: all 0.3s;
        }
        input:focus { outline: none; border-color: #9bff8c; box-shadow: 0 0 8px rgba(155, 255, 140, 0.3); }
        button {
            width: 100%;
            padding: 1rem;
            margin-top: 1rem;
            background: #1e1e1e;
            border: 1px solid #9bff8c;
            color: #9bff8c;
            font-weight: bold;
            border-radius: 60px;
            font-size: 1rem;
            cursor: pointer;
            transition: 0.3s;
        }
        button:hover { background: #2a2a2a; transform: scale(0.98); box-shadow: 0 0 12px rgba(155, 255, 140, 0.3); }
        .error { color: #ff8888; margin-top: 0.8rem; text-align: center; }
        .link-box {
            margin-top: 1.5rem;
            padding: 1rem;
            background: #1a1a1a;
            border-radius: 20px;
            word-break: break-all;
            text-align: center;
            box-shadow: 0 0 10px rgba(107, 140, 255, 0.1);
        }
        .link-box a {
            color: #9bff8c;
            text-decoration: none;
            font-size: 0.9rem;
        }
        .copy-btn {
            background: #2a2a2a;
            border: 1px solid #9bff8c;
            color: #9bff8c;
            padding: 0.6rem;
            font-size: 0.9rem;
            margin-top: 0.8rem;
            width: auto;
            display: inline-block;
        }
        .flex-center { text-align: center; }
        footer {
            text-align: center;
            padding: 2rem 1rem 1rem;
            color: #888;
            font-size: 0.8rem;
            direction: ltr;
        }
        footer a {
            color: #9bff8c;
            text-decoration: none;
        }
        .persian-footer {
            direction: rtl;
            margin-bottom: 0.5rem;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>HIDDEN CHAT</h1>
    <div class="card">
        <input type="text" id="name" placeholder="نام شما" autocomplete="off">
        <input type="password" id="password" placeholder="رمز (حداقل 4 رقم)">
        <button id="createBtn">ساختن لینک ناشناس</button>
        <div id="result" class="error"></div>
        <div id="linkContainer" class="link-box" style="display:none;"></div>
    </div>
</div>
<footer>
    <div class="persian-footer">سازنده : محمدرضا</div>
    <div>آیدی سازنده در اپ‌ها برای ارتباط : <a href="https://t.me/MMDAIDEN666" target="_blank">@MMDAIDEN666</a></div>
</footer>
<script>
    document.getElementById('createBtn').onclick = async () => {
        let name = document.getElementById('name').value.trim();
        let pwd = document.getElementById('password').value.trim();
        if(!name || !pwd || pwd.length < 4) {
            document.getElementById('result').innerText = 'نام و رمز (حداقل 4 رقم) الزامی است';
            document.getElementById('linkContainer').style.display = 'none';
            return;
        }
        let res = await fetch('/api/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, password: pwd})
        });
        let data = await res.json();
        if(res.ok) {
            let link = window.location.origin + '/c/' + data.link_id;
            document.getElementById('result').innerHTML = '';
            document.getElementById('linkContainer').innerHTML = `
                <div style="margin-bottom: 0.5rem; color:#9bff8c;">🔗 لينك شما:</div>
                <a href="${link}" target="_blank">${link}</a>
                <div class="flex-center">
                    <button class="copy-btn" id="copyLinkBtn">📋 كپي کردن لينک</button>
                </div>
            `;
            document.getElementById('linkContainer').style.display = 'block';
            
            document.getElementById('name').value = '';
            document.getElementById('password').value = '';
            
            document.getElementById('copyLinkBtn').onclick = () => {
                navigator.clipboard.writeText(link).then(() => {
                    let btn = document.getElementById('copyLinkBtn');
                    let originalText = btn.innerText;
                    btn.innerText = '✅ كپي شد!';
                    setTimeout(() => {
                        btn.innerText = originalText;
                    }, 2000);
                }).catch(() => {
                    alert('لطفا لينک را دستي كپي كنيد');
                });
            };
        } else {
            document.getElementById('result').innerText = data.error;
            document.getElementById('linkContainer').style.display = 'none';
        }
    };
</script>
</body>
</html>
"""

# ================== صفحه ارسال پیام ناشناس ==================
MSG_PAGE_HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ارسال پيام ناشناس - HIDDEN CHAT</title>
    <style>
        * { margin:0; padding:0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            font-family: 'Segoe UI', sans-serif;
            direction: rtl;
            padding: 2rem 1rem;
            color: #ddd;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .container { max-width: 550px; margin: 0 auto; flex: 1; width: 100%; }
        h1 {
            text-align: center;
            font-size: 1.8rem;
            margin-bottom: 1rem;
            color: #fff;
            text-shadow: 0 0 10px #6b8cff, 0 0 5px #9bff8c;
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 5px #6b8cff, 0 0 3px #9bff8c; }
            to { text-shadow: 0 0 15px #6b8cff, 0 0 8px #9bff8c; }
        }
        .subtitle { text-align: center; margin-bottom: 1.5rem; color: #9bff8c; text-shadow: 0 0 5px rgba(155,255,140,0.3); }
        .card {
            background: #111;
            border-radius: 28px;
            padding: 1.5rem;
            border: 1px solid #2a2a2a;
            box-shadow: 0 0 15px rgba(107, 140, 255, 0.1);
        }
        textarea {
            width: 100%;
            padding: 1rem;
            background: #1e1e1e;
            border: 1px solid #333;
            border-radius: 24px;
            color: white;
            font-size: 1rem;
            resize: vertical;
            font-family: inherit;
            transition: 0.3s;
        }
        textarea:focus { outline: none; border-color: #9bff8c; box-shadow: 0 0 8px rgba(155,255,140,0.3); }
        button {
            width: 100%;
            padding: 1rem;
            margin-top: 1rem;
            background: #1e1e1e;
            border: 1px solid #9bff8c;
            color: #9bff8c;
            font-weight: bold;
            border-radius: 60px;
            cursor: pointer;
            transition: 0.3s;
        }
        button:hover { background: #2a2a2a; transform: scale(0.98); box-shadow: 0 0 12px rgba(155,255,140,0.3); }
        .btn-secondary {
            border-color: #6b8cff;
            color: #6b8cff;
        }
        .toast {
            position: fixed;
            bottom: 30px;
            left: 20px;
            right: 20px;
            background: #1e2a2a;
            border-right: 4px solid #9bff8c;
            padding: 0.8rem;
            border-radius: 16px;
            text-align: center;
            font-size: 0.9rem;
            z-index: 999;
            animation: fadein 0.3s;
        }
        @keyframes fadein { from { opacity: 0; transform: translateY(20px);} to { opacity: 1; transform: translateY(0);} }
        footer {
            text-align: center;
            padding: 2rem 1rem 1rem;
            color: #888;
            font-size: 0.8rem;
            direction: ltr;
        }
        footer a {
            color: #9bff8c;
            text-decoration: none;
        }
        .persian-footer {
            direction: rtl;
            margin-bottom: 0.5rem;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>HIDDEN CHAT</h1>
    <div class="subtitle">به صورت ناشناس هر چي تو دلت هست به «{{ name }}» بگو...</div>
    <div class="card">
        <textarea id="msgBox" rows="4" placeholder="متن پيام ناشناس..."></textarea>
        <button id="sendBtn">ارسال پيام ناشناس</button>
        <button id="viewMyMessagesBtn" class="btn-secondary">مشاهده پيام هاي من</button>
        <button id="createNewLinkBtn" class="btn-secondary">ساختن لينک ناشناس</button>
    </div>
</div>
<footer>
    <div class="persian-footer">سازنده : محمدرضا</div>
    <div>آیدی سازنده در اپ‌ها برای ارتباط : <a href="https://t.me/MMDAIDEN666" target="_blank">@MMDAIDEN666</a></div>
</footer>
<script>
    const linkId = "{{ link_id }}";
    const targetName = "{{ name }}";
    
    async function sendMsg() {
        let text = document.getElementById('msgBox').value.trim();
        if(!text) return;
        let btn = document.getElementById('sendBtn');
        btn.disabled = true;
        btn.innerText = "در حال ارسال...";
        let res = await fetch('/api/send_msg', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({link_id: linkId, text: text})
        });
        let data = await res.json();
        if(res.ok) {
            showToast(`پيام شما ثبت و ارسال شد برای ${targetName}، منتظر جواب او باشید`);
            document.getElementById('msgBox').value = '';
        } else {
            showToast("خطا: " + (data.error || "مشکل در ارسال"));
        }
        btn.disabled = false;
        btn.innerText = "ارسال پيام ناشناس";
    }
    
    function showToast(msg) {
        let t = document.createElement('div');
        t.className = 'toast';
        t.innerText = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 3000);
    }
    
    document.getElementById('sendBtn').addEventListener('click', sendMsg);
    document.getElementById('viewMyMessagesBtn').addEventListener('click', () => {
        window.location.href = "/view/" + linkId;
    });
    document.getElementById('createNewLinkBtn').addEventListener('click', () => {
        window.location.href = "/";
    });
</script>
</body>
</html>
"""

# ================== صفحه ورود رمز برای دیدن پیام‌ها ==================
VIEW_PASSWORD_HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مشاهده پيام‌ها - HIDDEN CHAT</title>
    <style>
        * { margin:0; padding:0; box-sizing: border-box; }
        body { background:#0a0a0a; font-family: 'Segoe UI', sans-serif; direction:rtl; padding:2rem 1rem; color:#ddd; min-height:100vh; display:flex; flex-direction:column; }
        .container { max-width:500px; margin:0 auto; flex:1; width:100%; }
        .back-btn {
            display: inline-block;
            background: transparent;
            border: 1px solid #9bff8c;
            color: #9bff8c;
            padding: 0.5rem 1rem;
            border-radius: 40px;
            text-decoration: none;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
        h1 { text-align:center; margin-bottom:2rem; text-shadow:0 0 10px #6b8cff, 0 0 5px #9bff8c; animation:glow 2s infinite alternate; }
        @keyframes glow {
            from { text-shadow: 0 0 5px #6b8cff, 0 0 3px #9bff8c; }
            to { text-shadow: 0 0 15px #6b8cff, 0 0 8px #9bff8c; }
        }
        .card { background:#111; border-radius:28px; padding:1.8rem; border:1px solid #2a2a2a; box-shadow:0 0 15px rgba(107,140,255,0.1); }
        input { width:100%; padding:1rem; margin:0.5rem 0; background:#1e1e1e; border:1px solid #333; border-radius:24px; color:white; }
        input:focus { outline:none; border-color:#9bff8c; box-shadow:0 0 8px rgba(155,255,140,0.3); }
        button { width:100%; padding:1rem; background:#1e1e1e; border:1px solid #9bff8c; color:#9bff8c; border-radius:60px; margin-top:0.8rem; cursor:pointer; }
        .error { color:#ff8888; margin-top:1rem; text-align:center; }
        footer {
            text-align: center;
            padding: 2rem 1rem 1rem;
            color: #888;
            font-size: 0.8rem;
            direction: ltr;
        }
        footer a { color: #9bff8c; text-decoration: none; }
        .persian-footer { direction: rtl; margin-bottom: 0.5rem; }
    </style>
</head>
<body>
<div class="container">
    <a href="javascript:history.back()" class="back-btn">← برگشت</a>
    <h1>HIDDEN CHAT</h1>
    <div class="card">
        <input type="password" id="pwd" placeholder="رمز خود را وارد کنید">
        <button id="viewBtn">ديدن پيام هاي من</button>
        <div id="errorMsg" class="error"></div>
        <hr style="margin: 1.5rem 0; border-color:#222;">
        <button id="createAgainBtn">ساختن لينک ناشناس</button>
    </div>
</div>
<footer>
    <div class="persian-footer">سازنده : محمدرضا</div>
    <div>آیدی سازنده در اپ‌ها برای ارتباط : <a href="https://t.me/MMDAIDEN666" target="_blank">@MMDAIDEN666</a></div>
</footer>
<script>
    document.getElementById('viewBtn').onclick = async () => {
        let pwd = document.getElementById('pwd').value;
        let res = await fetch('/api/check_pwd', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({link_id: "{{ link_id }}", password: pwd})
        });
        let data = await res.json();
        if(res.ok) {
            window.location.href = "/view_msgs/{{ link_id }}";
        } else {
            document.getElementById('errorMsg').innerText = data.error;
        }
    };
    document.getElementById('createAgainBtn').onclick = () => {
        window.location.href = "/";
    };
</script>
</body>
</html>
"""

# ================== صفحه نمایش لیست پیام‌ها ==================
VIEW_MSGS_HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پيام‌های من - HIDDEN CHAT</title>
    <style>
        * { margin:0; padding:0; box-sizing: border-box; }
        body { background:#0a0a0a; font-family: 'Segoe UI', sans-serif; direction:rtl; padding:2rem 1rem; color:#ddd; min-height:100vh; display:flex; flex-direction:column; }
        .container { max-width:650px; margin:0 auto; flex:1; width:100%; }
        .back-btn {
            display: inline-block;
            background: transparent;
            border: 1px solid #9bff8c;
            color: #9bff8c;
            padding: 0.5rem 1rem;
            border-radius: 40px;
            text-decoration: none;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
        h1 { text-align:center; margin-bottom:1rem; text-shadow:0 0 10px #6b8cff, 0 0 5px #9bff8c; animation:glow 2s infinite alternate; }
        @keyframes glow {
            from { text-shadow: 0 0 5px #6b8cff, 0 0 3px #9bff8c; }
            to { text-shadow: 0 0 15px #6b8cff, 0 0 8px #9bff8c; }
        }
        .msg-card {
            background:#111;
            border-radius:24px;
            padding:1.2rem;
            margin-bottom:1rem;
            border-right:3px solid #9bff8c;
            box-shadow:0 0 10px rgba(155,255,140,0.1);
            transition:0.3s;
        }
        .msg-card:hover { box-shadow:0 0 15px rgba(155,255,140,0.2); }
        .msg-text { 
            font-size: 1rem; 
            line-height: 1.5; 
            word-wrap: break-word;
            word-break: break-all;
            white-space: normal;
            overflow-wrap: anywhere;
        }
        .msg-time { font-size:0.7rem; color:#9bff8c; text-align:left; margin-top:0.6rem; font-family:monospace; }
        footer {
            text-align: center;
            padding: 2rem 1rem 1rem;
            color: #888;
            font-size: 0.8rem;
            direction: ltr;
        }
        footer a { color: #9bff8c; text-decoration: none; }
        .persian-footer { direction: rtl; margin-bottom: 0.5rem; }
    </style>
</head>
<body>
<div class="container">
    <a href="javascript:history.back()" class="back-btn">← برگشت</a>
    <h1>پيام‌های شما</h1>
    <div id="msgsList">
        <div style="text-align:center;">در حال بارگيري...</div>
    </div>
</div>
<footer>
    <div class="persian-footer">سازنده : محمدرضا</div>
    <div>آیدی سازنده در اپ‌ها برای ارتباط : <a href="https://t.me/MMDAIDEN666" target="_blank">@MMDAIDEN666</a></div>
</footer>
<script>
    async function loadMsgs() {
        let res = await fetch('/api/get_msgs/{{ link_id }}');
        let msgs = await res.json();
        let container = document.getElementById('msgsList');
        if(msgs.length === 0) {
            container.innerHTML = '<div style="text-align:center;">📭 هنوز پيامي دريافت نشده</div>';
            return;
        }
        container.innerHTML = msgs.map(m => `
            <div class="msg-card">
                <div class="msg-text">${escapeHtml(m.text)}</div>
                <div class="msg-time">${m.time_ago}</div>
            </div>
        `).join('');
    }
    function escapeHtml(str) {
        return str.replace(/[&<>]/g, function(m) {
            if(m === '&') return '&amp;';
            if(m === '<') return '&lt;';
            if(m === '>') return '&gt;';
            return m;
        });
    }
    loadMsgs();
    setInterval(loadMsgs, 5000);
</script>
</body>
</html>
"""

# ================== روت‌های اصلی ==================
@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/api/create', methods=['POST'])
def create_link():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '').strip()
    if not name or not password or len(password) < 4:
        return jsonify({"error": "نام و رمز (حداقل 4 رقم) الزامی است"}), 400
    users = load_users()
    link_id = secrets.token_urlsafe(8)
    while link_id in users:
        link_id = secrets.token_urlsafe(8)
    users[link_id] = {
        "name": name,
        "password": password,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)
    return jsonify({"link_id": link_id})

@app.route('/c/<link_id>')
def msg_page(link_id):
    users = load_users()
    if link_id not in users:
        return "لينک نامعتبر", 404
    return render_template_string(MSG_PAGE_HTML, name=users[link_id]['name'], link_id=link_id)

@app.route('/api/send_msg', methods=['POST'])
def send_msg():
    data = request.json
    link_id = data.get('link_id')
    text = data.get('text', '').strip()
    if not link_id or not text:
        return jsonify({"error": "متن پيام نمی‌تواند خالی باشد"}), 400
    users = load_users()
    if link_id not in users:
        return jsonify({"error": "لينک نامعتبر"}), 404
    msgs = load_messages(link_id)
    msgs.append({
        "text": text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_messages(link_id, msgs)
    return jsonify({"status": "ok"})

@app.route('/view/<link_id>')
def view_password_page(link_id):
    users = load_users()
    if link_id not in users:
        return "لينک نامعتبر", 404
    return render_template_string(VIEW_PASSWORD_HTML, link_id=link_id)

@app.route('/api/check_pwd', methods=['POST'])
def check_pwd():
    data = request.json
    link_id = data.get('link_id')
    pwd = data.get('password')
    users = load_users()
    if link_id not in users or users[link_id]['password'] != pwd:
        return jsonify({"error": "رمز اشتباه است"}), 401
    return jsonify({"ok": True})

@app.route('/view_msgs/<link_id>')
def view_msgs(link_id):
    users = load_users()
    if link_id not in users:
        return "دسترسی غیرمجاز", 403
    return render_template_string(VIEW_MSGS_HTML, link_id=link_id)

@app.route('/api/get_msgs/<link_id>')
def get_msgs_api(link_id):
    msgs = load_messages(link_id)
    for m in msgs:
        m['time_ago'] = time_ago(m['timestamp'])
    return jsonify(msgs[::-1])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)