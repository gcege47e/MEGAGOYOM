import os
import uuid
import threading
import time
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# ذخیره اطلاعات اتاق‌ها در حافظه موقت سرور
ROOMS = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تیک‌تاک‌تو نئونی خطی پیشرفته</title>
    <link href="https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/styles/font-face.css" rel="stylesheet" type="text/css" />
    <style>
        :root {
            --bg-color: #060610;
            --neon-cyan: #00f3ff;
            --neon-magenta: #ff0055;
            --neon-purple: #9d4edd;
            --neon-amber: #ffb703;
            --text-color: #ffffff;
            --panel-bg: rgba(15, 15, 35, 0.7);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Vazirmatn', sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow-x: hidden;
            background-image: radial-gradient(circle at 50% 50%, #120e2e 0%, #060610 100%);
        }

        .container {
            width: 100%;
            max-width: 450px;
            padding: 15px;
        }

        .card {
            background: var(--panel-bg);
            border: 1px solid rgba(157, 78, 221, 0.2);
            backdrop-filter: blur(16px);
            border-radius: 24px;
            padding: 25px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
        }

        h1 {
            text-align: center;
            font-size: 1.8rem;
            margin-bottom: 25px;
            color: #fff;
            text-shadow: 0 0 10px var(--neon-purple), 0 0 20px var(--neon-purple);
        }

        .form-group {
            margin-bottom: 16px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-size: 0.85rem;
            color: #aaa;
            text-align: right;
        }

        /* ترفند ضد اخطار پسورد گوگل: استفاده از text و ماسک امنیتی */
        input.security-mask-input {
            -webkit-text-security: disc;
            text-security: disc;
        }

        input {
            width: 100%;
            padding: 12px 15px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(157, 78, 221, 0.3);
            border-radius: 10px;
            color: #fff;
            font-size: 0.95rem;
            transition: all 0.3s;
            text-align: right;
        }

        input:focus {
            outline: none;
            border-color: var(--neon-cyan);
            box-shadow: 0 0 12px rgba(0, 243, 255, 0.3);
        }

        .btn {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }

        .btn-cyan {
            background: transparent;
            color: var(--neon-cyan);
            border: 2px solid var(--neon-cyan);
        }

        .btn-cyan:hover {
            background: var(--neon-cyan);
            color: #000;
            box-shadow: 0 0 20px var(--neon-cyan);
        }

        .btn-magenta {
            background: transparent;
            color: var(--neon-magenta);
            border: 2px solid var(--neon-magenta);
        }

        .btn-magenta:hover {
            background: var(--neon-magenta);
            color: #fff;
            box-shadow: 0 0 20px var(--neon-magenta);
        }

        .hidden { display: none !important; }

        /* سیستم اعلان بالای لایوت با انیمیشن مدرن کشویی */
        .notification-banner {
            background: rgba(10, 5, 25, 0.9);
            border: 1px solid var(--neon-purple);
            box-shadow: 0 0 15px var(--neon-purple);
            color: #fff;
            padding: 12px 15px;
            border-radius: 12px;
            text-align: center;
            font-weight: bold;
            margin-bottom: 15px;
            opacity: 0;
            transform: translateY(-20px);
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            font-size: 0.95rem;
        }

        .notification-banner.show {
            opacity: 1;
            transform: translateY(0);
        }

        /* بخش کپی لینک در فرم اول زیر دکمه */
        .link-section {
            background: rgba(0,0,0,0.5);
            padding: 15px;
            border-radius: 12px;
            margin-top: 20px;
            border: 1px dashed var(--neon-cyan);
            text-align: center;
        }
        .link-text {
            font-size: 0.8rem;
            color: var(--neon-cyan);
            word-break: break-all;
            margin-bottom: 10px;
            display: block;
        }

        /* کنترلر موزیک فانتزی هدر بازی */
        .game-header-actions {
            display: flex;
            justify-content: center;
            margin-bottom: 15px;
        }
        
        .music-toggle-btn {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--neon-cyan);
            box-shadow: 0 0 8px rgba(0, 243, 255, 0.2);
            color: var(--neon-cyan);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .music-toggle-btn.muted {
            border-color: var(--neon-magenta);
            color: var(--neon-magenta);
            box-shadow: 0 0 8px rgba(255, 0, 85, 0.2);
        }

        .scoreboard {
            display: flex;
            justify-content: space-between;
            background: rgba(0,0,0,0.3);
            padding: 12px;
            border-radius: 14px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.05);
        }

        .player-score { text-align: center; flex: 1; }
        .score-num { font-size: 1.6rem; font-weight: 800; color: var(--neon-cyan); }

        /* طراحی جدول به صورت خط کشی نئونی بنفش متقارن و بدون قطع شدن خطوط */
        .board-container {
            position: relative;
            margin: 0 auto 20px auto;
            width: 280px;
            height: 280px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            width: 100%;
            height: 100%;
            position: relative;
        }

        .cell {
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 2.6rem;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s, box-shadow 0.3s;
            position: relative;
        }
        
        /* بازسازی دقیق ساختار مرز نئونی برای تصحیح خانه پایین سمت چپ */
        .cell:nth-child(1), .cell:nth-child(2), .cell:nth-child(3),
        .cell:nth-child(4), .cell:nth-child(5), .cell:nth-child(6) {
            border-bottom: 3px solid var(--neon-purple);
        }
        
        .cell:nth-child(1), .cell:nth-child(2),
        .cell:nth-child(4), .cell:nth-child(5),
        .cell:nth-child(7), .cell:nth-child(8) {
            border-left: 3px solid var(--neon-purple);
        }

        /* اعمال سایه نئونی درونی متوازن روی کل ساختار گرید */
        .cell {
            box-shadow: 0 0 2px rgba(157, 78, 221, 0.2);
        }

        /* انیمیشن پاپ‌آپ ظهور نرم علائم */
        @keyframes neonPopIn {
            0% {
                transform: scale(0.4);
                opacity: 0;
                filter: blur(4px);
            }
            70% {
                transform: scale(1.15);
                filter: blur(0px);
            }
            100% {
                transform: scale(1);
                opacity: 1;
            }
        }

        .cell.cell-x { 
            color: var(--neon-cyan); 
            text-shadow: 0 0 12px var(--neon-cyan); 
            animation: neonPopIn 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }
        .cell.cell-o { 
            color: var(--neon-magenta); 
            text-shadow: 0 0 12px var(--neon-magenta); 
            animation: neonPopIn 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }

        /* استایل جدید نئونی شدن خانه‌های برنده به رنگ آبی نئونی */
        .cell.winner-neon-cell {
            background: rgba(0, 243, 255, 0.25) !important;
            box-shadow: inset 0 0 15px rgba(0, 243, 255, 0.6), 0 0 15px rgba(0, 243, 255, 0.4) !important;
            border-color: var(--neon-cyan) !important;
        }

        .status-bar {
            text-align: center;
            font-size: 1.1rem;
            padding: 10px;
            background: rgba(0,0,0,0.4);
            border-radius: 10px;
            border-bottom: 2px solid var(--neon-purple);
            margin-bottom: 15px;
        }

        /* پاپ آپ تمام صفحه انتخاب علامت هوشمند راندها */
        .overlay-choice {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(6, 6, 16, 0.96);
            border-radius: 24px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 20;
            padding: 20px;
            text-align: center;
        }

        .choice-container { display: flex; gap: 20px; margin-top: 20px; }
        .choice-btn {
            width: 75px; height: 75px; border-radius: 50%;
            border: 3px solid #fff; font-size: 2.2rem; font-weight: bold;
            cursor: pointer; background: transparent; transition: all 0.3s;
        }
        .btn-x-choice { color: var(--neon-cyan); border-color: var(--neon-cyan); }
        .btn-x-choice:hover { background: var(--neon-cyan); color: #000; box-shadow: 0 0 20px var(--neon-cyan); }
        .btn-o-choice { color: var(--neon-magenta); border-color: var(--neon-magenta); }
        .btn-o-choice:hover { background: var(--neon-magenta); color: #fff; box-shadow: 0 0 20px var(--neon-magenta); }

        /* پاپ آپ مدرن و شیک تایید خروج نئونی */
        .custom-modal-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(5, 5, 12, 0.85);
            backdrop-filter: blur(8px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 2000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }
        .custom-modal-overlay.show {
            opacity: 1;
            pointer-events: auto;
        }
        .custom-modal {
            background: rgba(20, 15, 40, 0.95);
            border: 2px solid var(--neon-magenta);
            box-shadow: 0 0 25px rgba(255, 0, 85, 0.4);
            border-radius: 20px;
            width: 90%;
            max-width: 380px;
            padding: 25px;
            text-align: center;
            transform: scale(0.8);
            transition: transform 0.3s ease;
        }
        .custom-modal-overlay.show .custom-modal {
            transform: scale(1);
        }
        .custom-modal h3 {
            font-size: 1.3rem;
            margin-bottom: 15px;
            color: #fff;
            text-shadow: 0 0 8px var(--neon-magenta);
        }
        .custom-modal p {
            font-size: 0.95rem;
            color: #ccc;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        .modal-buttons {
            display: flex;
            gap: 15px;
        }
    </style>
</head>
<body>

<div class="container">
    <div id="auth-notification-container" class="notification-banner"></div>

    <div id="auth-panel" class="card">
        <h1 id="auth-title">ایجاد اتاق بازی</h1>
        <div class="form-group">
            <label>نام کاربری شما</label>
            <input type="text" id="username" placeholder="نام خود را وارد کنید...">
        </div>
        <div class="form-group">
            <label>رمز عبور اتاق</label>
            <input type="text" id="password" class="security-mask-input" placeholder="یک رمز عبور دلخواه...">
        </div>
        
        <button class="btn btn-cyan" id="btn-submit" onclick="joinOrCreateRoom()">ساخت اتاق بازی</button>

        <div id="setup-link-box" class="link-section hidden">
            <span class="link-text" id="setup-link-str"></span>
            <button class="btn btn-cyan" style="padding: 6px; margin: 0; font-size: 0.85rem;" onclick="copySetupLink()">کپی کردن لینک دعوت</button>
        </div>
    </div>

    <div id="game-panel" class="card hidden">
        <div class="game-header-actions">
            <button id="music-toggle" class="music-toggle-btn" onclick="toggleMusicState()">
                <span>🎵</span> <span>موزیک: روشن</span>
            </button>
        </div>

        <div id="toast-notification" class="notification-banner"></div>

        <div class="scoreboard">
            <div class="player-score">
                <div id="p1-name" style="color: var(--neon-cyan)">بازیکن ۱ (-)</div>
                <div id="p1-score" class="score-num">0</div>
            </div>
            <div style="align-self: center; font-weight: bold; color: #444; margin: 0 10px;">VS</div>
            <div class="player-score">
                <div id="p2-name" style="color: var(--neon-magenta)">بازیکن ۲ (-)</div>
                <div id="p2-score" class="score-num">0</div>
            </div>
        </div>

        <div class="board-container">
            
            <div id="choice-overlay" class="overlay-choice hidden">
                <div id="choice-msg-text" style="font-size: 1.2rem; font-weight: bold; line-height: 1.6;">در انتظار ورود حریف...</div>
                <div id="choice-buttons" class="choice-container hidden">
                    <button class="choice-btn btn-x-choice" onclick="chooseSign('X')">X</button>
                    <button class="choice-btn btn-o-choice" onclick="chooseSign('O')">O</button>
                </div>
            </div>

            <div class="grid" id="board">
                <div class="cell" onclick="makeMove(0)"></div>
                <div class="cell" onclick="makeMove(1)"></div>
                <div class="cell" onclick="makeMove(2)"></div>
                <div class="cell" onclick="makeMove(3)"></div>
                <div class="cell" onclick="makeMove(4)"></div>
                <div class="cell" onclick="makeMove(5)"></div>
                <div class="cell" onclick="makeMove(6)"></div>
                <div class="cell" onclick="makeMove(7)"></div>
                <div class="cell" onclick="makeMove(8)"></div>
            </div>
        </div>

        <div class="status-bar" id="turn-status">در انتظار حریف...</div>
        <button class="btn btn-magenta" onclick="triggerExitFlow()">خروج از بازی</button>
    </div>
</div>

<div id="exit-modal" class="custom-modal-overlay">
    <div class="custom-modal">
        <h3 id="modal-title-text">تایید خروج از اتاق</h3>
        <p id="modal-body-text">آیا مطمئن هستید که می‌خواهید از بازی خارج شوید؟</p>
        <div class="modal-buttons">
            <button class="btn btn-magenta" style="margin:0;" onclick="confirmExit()">بله، خروج</button>
            <button class="btn btn-cyan" style="margin:0;" onclick="closeExitModal()">ماندن در بازی</button>
        </div>
    </div>
</div>

<script>
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    let bgOsc1 = null, bgOsc2 = null, bgGain = null, lowpassFilter = null;
    let isMusicEnabled = true; 
    let musicTimeoutId = null;
    
    function playSound(type) {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain); gain.connect(audioCtx.destination);

        if (type === 'click' || type === 'write') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(type === 'click' ? 450 : 250, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(10, audioCtx.currentTime + 0.08);
            gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.08);
            osc.start(); osc.stop(audioCtx.currentTime + 0.08);
        } else if (type === 'win') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(260, audioCtx.currentTime);
            osc.frequency.setValueAtTime(390, audioCtx.currentTime + 0.1);
            osc.frequency.setValueAtTime(520, audioCtx.currentTime + 0.2);
            gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);
            osc.start(); osc.stop(audioCtx.currentTime + 0.35);
        } else if (type === 'draw') {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(150, audioCtx.currentTime);
            gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
            osc.start(); osc.stop(audioCtx.currentTime + 0.25);
        } else if (type === 'alert') {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(220, audioCtx.currentTime);
            osc.frequency.linearRampToValueAtTime(120, audioCtx.currentTime + 0.3);
            gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
            osc.start(); osc.stop(audioCtx.currentTime + 0.3);
        }
    }

    // بازسازی کامل سیستم موسیقی امبینت به سبک بازی ماینکرفت (نرمال، آرامش‌بخش، بدون فرکانس‌های خیلی ضخیم یا خیلی زیر)
    function startAmbientBackgroundMusic() {
        if (!isMusicEnabled || bgGain) return;
        
        bgGain = audioCtx.createGain();
        bgGain.gain.setValueAtTime(0.04, audioCtx.currentTime); 
        
        lowpassFilter = audioCtx.createBiquadFilter();
        lowpassFilter.type = 'lowpass';
        lowpassFilter.frequency.setValueAtTime(350, audioCtx.currentTime); 
        
        bgGain.connect(lowpassFilter);
        lowpassFilter.connect(audioCtx.destination);

        const playNotesCycle = () => {
            if (!bgGain || !isMusicEnabled) return;
            
            bgOsc1 = audioCtx.createOscillator();
            bgOsc2 = audioCtx.createOscillator();
            
            bgOsc1.type = 'sine';
            bgOsc2.type = 'sine'; 
            
            // نوت‌های بسیار آرامش‌بخش و معتدل در محدوده میانی گام ماینکرفتی
            const minecraftMelodyNotes = [196.00, 220.00, 246.94, 261.63, 293.66, 329.63, 349.23, 392.00];
            const baseNote = minecraftMelodyNotes[Math.floor(Math.random() * minecraftMelodyNotes.length)];
            // انتخاب نوت دوم در فواصل سوم یا پنجم ایده آل و ملایم
            const companionNote = baseNote * 1.25; 
            
            bgOsc1.frequency.setValueAtTime(baseNote, audioCtx.currentTime);
            bgOsc2.frequency.setValueAtTime(companionNote, audioCtx.currentTime);
            
            bgOsc1.connect(bgGain);
            bgOsc2.connect(bgGain);
            
            bgOsc1.start();
            bgOsc2.start();
            
            let cycleDuration = 2000;
            musicTimeoutId = setTimeout(() => {
                try {
                    if(bgOsc1) bgOsc1.stop();
                    if(bgOsc2) bgOsc2.stop();
                } catch(e){}
                playNotesCycle();
            }, cycleDuration);
        };
        
        playNotesCycle();
    }

    function stopAmbientMusic() {
        clearTimeout(musicTimeoutId);
        if (bgOsc1) { try { bgOsc1.stop(); }catch(e){} bgOsc1 = null; }
        if (bgOsc2) { try { bgOsc2.stop(); }catch(e){} bgOsc2 = null; }
        if (bgGain) { try { bgGain.disconnect(); } catch(e){} bgGain = null; }
        if (lowpassFilter) { try { lowpassFilter.disconnect(); } catch(e){} lowpassFilter = null; }
    }

    function toggleMusicState() {
        playSound('click');
        const btn = document.getElementById('music-toggle');
        if (isMusicEnabled) {
            isMusicEnabled = false;
            stopAmbientMusic();
            btn.classList.add('muted');
            btn.innerHTML = `<span>🔇</span> <span>موزیک: خاموش</span>`;
        } else {
            isMusicEnabled = true;
            btn.classList.remove('muted');
            btn.innerHTML = `<span>🎵</span> <span>موزیک: روشن</span>`;
            if (!document.getElementById('game-panel').classList.contains('hidden')) {
                startAmbientBackgroundMusic();
            }
        }
    }

    function lockAndInterceptBackButton() {
        window.history.pushState({page: "game"}, "", window.location.href);
        window.onpopstate = function(event) {
            window.history.pushState({page: "game"}, "", window.location.href);
            const isGameActive = !document.getElementById('game-panel').classList.contains('hidden');
            if (isGameActive) {
                triggerExitFlow();
            }
        };
    }
    
    lockAndInterceptBackButton();

    const urlParams = new URLSearchParams(window.location.search);
    let urlRoomId = urlParams.get('room');
    let preAuthInterval = null; 

    if(urlRoomId) {
        document.getElementById('auth-title').innerText = "ورود به اتاق بازی دعوت شده";
        document.getElementById('btn-submit').innerText = "ورود به اتاق بازی";
        preAuthInterval = setInterval(monitorRoomExistenceBeforeJoin, 1200);
    }

    function monitorRoomExistenceBeforeJoin() {
        if (!urlRoomId) return;
        fetch(`/api/room/${urlRoomId}`)
        .then(res => {
            if (res.status === 404) {
                clearInterval(preAuthInterval);
                handleRoomDestroyedByCreator();
            }
        }).catch(e => {});
    }

    document.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', () => playSound('write'));
    });

    let currentRoom = null;
    let myUser = "";
    let mySign = ""; 
    let pollingInterval = null;
    let localRoundNum = 0;
    let isCreator = false; 
    let lastKnownOpponentState = null; 

    function showToast(message, duration = 3000, isAuthPanel = false) {
        const toastId = isAuthPanel ? 'auth-notification-container' : 'toast-notification';
        const toast = document.getElementById(toastId);
        if(!toast) return;
        toast.innerText = message;
        toast.classList.add('show');
        setTimeout(() => { toast.classList.remove('show'); }, duration);
    }

    function joinOrCreateRoom() {
        playSound('click');
        if (audioCtx.state === 'suspended') { audioCtx.resume(); }
        
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        const isInAuthView = document.getElementById('game-panel').classList.contains('hidden');

        if(!username) {
            showToast('⚠️ لطفا نام کاربری خود را وارد کنید.', 3000, isInAuthView);
            return;
        }
        if(!password) {
            showToast('⚠️ رمز عبور اتاق را وارد نکرده‌اید.', 3000, isInAuthView);
            return;
        }

        myUser = username;

        fetch('/api/join', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password, room_id: urlRoomId || ""})
        })
        .then(res => res.json())
        .then(data => {
            if(data.error) { 
                showToast('❌ ' + data.error, 3500, isInAuthView); 
                return; 
            }
            currentRoom = data.room_id;
            if(preAuthInterval) clearInterval(preAuthInterval); 
            
            if(!urlRoomId) {
                isCreator = true;
                const inviteUrl = window.location.origin + window.location.pathname + '?room=' + currentRoom;
                document.getElementById('setup-link-str').innerText = inviteUrl;
                document.getElementById('setup-link-box').classList.remove('hidden');
                showToast('🎉 اتاق ساخته شد! لینک دعوت را برای حریف بفرستید.', 4000, true);
            } else {
                isCreator = false;
                document.getElementById('auth-panel').classList.add('hidden');
                document.getElementById('game-panel').classList.remove('hidden');
                lastKnownOpponentState = true; 
                startAmbientBackgroundMusic();
                pollingInterval = setInterval(updateGameState, 800);
            }
        });
    }

    function copySetupLink() {
        playSound('click');
        const linkText = document.getElementById('setup-link-str').innerText;
        navigator.clipboard.writeText(linkText).then(() => {
            showToast('📋 لینک دعوت کپی شد! در حال انتقال به تالار انتظار بازی...', 2000, true);
            setTimeout(() => {
                document.getElementById('auth-panel').classList.add('hidden');
                document.getElementById('game-panel').classList.remove('hidden');
                lastKnownOpponentState = false; 
                startAmbientBackgroundMusic();
                pollingInterval = setInterval(updateGameState, 800);
            }, 1500);
        });
    }

    function updateGameState() {
        if (!currentRoom) return;

        fetch(`/api/room/${currentRoom}`)
        .then(res => {
            if (res.status === 404) {
                // اگر سازنده نبود و اتاق بسته شد، صفحه قفل شود
                if(!isCreator) {
                    handleRoomDestroyedByCreator();
                }
                return null;
            }
            return res.json();
        })
        .then(room => {
            if (!room) return;

            let currentOpponentExists = !!room.p2;
            if (lastKnownOpponentState !== null && lastKnownOpponentState !== currentOpponentExists) {
                if (currentOpponentExists) {
                    showToast(`⚔️ حریف شما (${room.p2}) وارد اتاق شد! بازی آغاز شد.`);
                } else {
                    showToast("⚠️ حریف از بازی خارج شد! جدول ریست و امتیازها صفر شد.");
                }
            }
            lastKnownOpponentState = currentOpponentExists;

            document.getElementById('p1-name').innerText = room.p1 + (room.p1_sign ? ` (${room.p1_sign})` : '');
            document.getElementById('p1-score').innerText = room.scores[room.p1] || 0;
            
            if(room.p2) {
                document.getElementById('p2-name').innerText = room.p2 + (room.p2_sign ? ` (${room.p2_sign})` : '');
                document.getElementById('p2-score').innerText = room.scores[room.p2] || 0;
            } else {
                document.getElementById('p2-name').innerText = "در انتظار حریف...";
                document.getElementById('p2-score').innerText = "0";
            }

            const choiceOverlay = document.getElementById('choice-overlay');
            const choiceMsgText = document.getElementById('choice-msg-text');
            const choiceButtons = document.getElementById('choice-buttons');

            if (!room.p2) {
                choiceOverlay.classList.remove('hidden');
                choiceMsgText.innerText = "منتظر ورود بازیکن دوم با لینک دعوت باشید...";
                choiceButtons.classList.add('hidden');
                
                const cells = document.querySelectorAll('.cell');
                cells.forEach(c => { c.innerText = ''; c.className = 'cell'; });
                document.getElementById('turn-status').innerText = "در انتظار حریف...";
                return;
            }

            if (!room.signs_chosen) {
                choiceOverlay.classList.remove('hidden');
                if (myUser === room.chooser_turn) {
                    choiceMsgText.innerText = "شما انتخاب‌کننده علامت این راند هستید! انتخاب کنید:";
                    choiceButtons.classList.remove('hidden');
                } else {
                    choiceMsgText.innerText = `در انتظار انتخاب علامت توسط حریف (${room.chooser_turn}) باشید...`;
                    choiceButtons.classList.add('hidden');
                }
                return;
            }

            if (room.signs_chosen && localRoundNum !== room.round_count) {
                mySign = (myUser === room.p1) ? room.p1_sign : room.p2_sign;
                let oppSign = (mySign === 'X') ? 'O' : 'X';
                
                choiceMsgText.innerHTML = `علامت‌ها مشخص شد!<br><span style="color:var(--neon-cyan)">شما: ${mySign}</span><br><span style="color:var(--neon-magenta)">حریف: ${oppSign}</span>`;
                choiceButtons.classList.add('hidden');
                
                setTimeout(() => {
                    choiceOverlay.classList.add('hidden');
                    localRoundNum = room.round_count; 
                }, 2000);
                return;
            }

            mySign = (myUser === room.p1) ? room.p1_sign : room.p2_sign;

            const turnStatus = document.getElementById('turn-status');
            if(room.winner_status) {
                turnStatus.innerText = "پایان این راند - در حال بروزرسانی...";
            } else {
                if(room.current_turn === mySign) {
                    turnStatus.innerText = "نوبت شماست! یک خانه را خط بزنید.";
                    turnStatus.style.borderBottomColor = "var(--neon-cyan)";
                } else {
                    let oppName = (mySign === room.p1_sign) ? room.p2 : room.p1;
                    turnStatus.innerText = `نوبت بازیکن ${oppName} (${room.current_turn})`;
                    turnStatus.style.borderBottomColor = "var(--neon-magenta)";
                }
            }

            const cells = document.querySelectorAll('.cell');
            room.board.forEach((val, index) => {
                if(!room.winner_status) {
                    cells[index].classList.remove('winner-neon-cell');
                }
                
                // در زمان اضافه شدن علامت، اگر خانه قبلا خالی بوده کلاس انیمیشن پاپ‌آپ حفظ می‌شود
                if(val) {
                    if (cells[index].innerText !== val) {
                        cells[index].innerText = val;
                        cells[index].className = 'cell ' + (val === 'X' ? 'cell-x' : 'cell-o');
                    }
                } else { 
                    cells[index].innerText = ''; 
                    cells[index].className = 'cell';
                }
            });

            if(room.winner_status && !room.local_notified) {
                handleRoundEnd(room);
            }
        });
    }

    function chooseSign(sign) {
        playSound('click');
        fetch('/api/choose_sign', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({room_id: currentRoom, username: myUser, sign: sign})
        }).then(() => updateGameState());
    }

    function makeMove(index) {
        if(!currentRoom || !mySign) return;
        fetch('/api/move', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({room_id: currentRoom, sign: mySign, index: index})
        }).then(() => updateGameState());
    }

    function handleRoundEnd(room) {
        room.local_notified = true;
        if(room.winner_status === 'draw') {
            playSound('draw');
            showToast('راند مساوی شد! هیچکس امتیاز نگرفت.');
        } else {
            playSound('win');
            let winnerName = room.winner_status === room.p1_sign ? room.p1 : room.p2;
            showToast(`بازیکن ${winnerName} (${room.winner_status}) این راند را برد! 🎉`);
            
            if(room.win_pattern) {
                const cells = document.querySelectorAll('.cell');
                room.win_pattern.forEach(index => {
                    cells[index].classList.add('winner-neon-cell');
                });
            }
        }
        setTimeout(() => { updateGameState(); }, 3000);
    }

    function triggerExitFlow() {
        playSound('alert');
        const modal = document.getElementById('exit-modal');
        const title = document.getElementById('modal-title-text');
        const body = document.getElementById('modal-body-text');
        
        if(isCreator) {
            title.innerText = "بستن و حذف اتاق (سازنده)";
            body.innerText = "شما سازنده اتاق هستید. با خروج شما اتاق کاملاً بسته شده و حریف بیرون انداخته می‌شود. مایل به ادامه هستید؟";
        } else {
            title.innerText = "خروج از اتاق بازی (مهمان)";
            body.innerText = "آیا می‌خواهید از این بازی خارج شوید؟ امتیازات شما صفر شده و به صفحه ورود باز می‌گردید.";
        }
        modal.classList.add('show');
    }

    function closeExitModal() {
        playSound('click');
        document.getElementById('exit-modal').classList.remove('show');
    }

    function confirmExit() {
        playSound('click');
        document.getElementById('exit-modal').classList.remove('show');
        stopAmbientMusic();

        if (isCreator) {
            if(currentRoom) {
                fetch('/api/leave', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_id: currentRoom, action: 'destroy'})
                }).then(() => { executeCreatorExitRedirect(); });
            } else { executeCreatorExitRedirect(); }
        } else {
            if(currentRoom) {
                fetch('/api/leave', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_id: currentRoom, username: myUser, action: 'guest_leave'})
                }).then(() => { executeGuestExitRedirect(); });
            } else { executeGuestExitRedirect(); }
        }
    }

    // تغییر رفتار: وقتی سازنده بازی رو تموم میکنه خودش مستقیما به لایوت ساخت اتاق برمیگرده
    function executeCreatorExitRedirect() {
        clearInterval(pollingInterval);
        currentRoom = null;
        window.history.pushState({}, "", window.location.pathname);
        urlRoomId = null;
        isCreator = false;
        lastKnownOpponentState = null;
        
        document.getElementById('auth-title').innerText = "ایجاد اتاق بازی";
        document.getElementById('btn-submit').innerText = "ساخت اتاق بازی";
        document.getElementById('setup-link-box').classList.add('hidden');
        
        document.getElementById('game-panel').classList.add('hidden');
        document.getElementById('auth-panel').classList.remove('hidden');
    }

    function executeGuestExitRedirect() {
        clearInterval(pollingInterval);
        const savedRoomId = currentRoom;
        currentRoom = null;
        lastKnownOpponentState = null;
        
        window.history.pushState({}, "", window.location.pathname + "?room=" + savedRoomId);
        urlRoomId = savedRoomId;
        
        document.getElementById('auth-title').innerText = "ورود به اتاق بازی دعوت شده";
        document.getElementById('btn-submit').innerText = "ورود به اتاق بازی";
        document.getElementById('setup-link-box').classList.add('hidden');
        
        document.getElementById('game-panel').classList.add('hidden');
        document.getElementById('auth-panel').classList.remove('hidden');
        
        preAuthInterval = setInterval(monitorRoomExistenceBeforeJoin, 1200);
    }

    function handleRoomDestroyedByCreator() {
        clearInterval(pollingInterval);
        if(preAuthInterval) clearInterval(preAuthInterval);
        currentRoom = null;
        stopAmbientMusic();
        
        const container = document.querySelector('.container');
        container.innerHTML = `
            <div class="card" style="border-color: var(--neon-magenta); box-shadow: 0 0 30px rgba(255,0,85,0.5); text-align:center; padding:35px 20px;">
                <h2 style="color:var(--neon-magenta); text-shadow:0 0 12px var(--neon-magenta); margin-bottom:20px; font-size:1.6rem;">اتاق بازی بسته شد!</h2>
                <p style="color:#ddd; font-size:1rem; line-height:1.8; margin-bottom:30px;">سازنده اصلی، اتاق بازی را ترک کرد و این اتاق برای همیشه حذف شد.</p>
                <button class="btn btn-cyan" onclick="window.location.href='https://www.google.com'">انتقال به سایت گوگل</button>
            </div>
        `;
        
        window.onpopstate = function() {
            window.location.href = "https://www.google.com";
        };
    }
</script>
</body>
</html>
"""

@app.route('/api/join', methods=['POST'])
def join_room():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    room_id = data.get('room_id')

    if not room_id:
        room_id = str(uuid.uuid4())[:8]
        ROOMS[room_id] = {
            'p1': username, 'password': password, 'p1_sign': None,
            'p2': None, 'p2_sign': None,
            'signs_chosen': False,
            'chooser_turn': username, 
            'round_count': 1,
            'board': ["" for _ in range(9)],
            'current_turn': 'X',
            'first_turn_next_round': 'O',
            'scores': {username: 0},
            'winner_status': None,
            'win_pattern': None
        }
        return jsonify({'room_id': room_id})
    else:
        if room_id not in ROOMS:
            return jsonify({'error': 'این اتاق وجود ندارد یا توسط سازنده بسته شده است!'}), 404
        
        room = ROOMS[room_id]
        if room['password'] != password:
            return jsonify({'error': 'رمز عبور اتاق نادرست است!'}), 400

        if room['p1'] != username and room['p2'] is None:
            room['p2'] = username
            room['scores'][username] = 0

        return jsonify({'room_id': room_id})

@app.route('/api/choose_sign', methods=['POST'])
def choose_sign():
    data = request.json
    room_id = data.get('room_id')
    username = data.get('username')
    sign = data.get('sign')

    room = ROOMS.get(room_id)
    if room and not room['signs_chosen']:
        opp_sign = 'O' if sign == 'X' else 'X'
        if room['p1'] == username:
            room['p1_sign'] = sign
            room['p2_sign'] = opp_sign
        else:
            room['p2_sign'] = sign
            room['p1_sign'] = opp_sign
        room['signs_chosen'] = True
    return jsonify({'success': True})

@app.route('/api/room/<room_id>', methods=['GET'])
def get_room(room_id):
    if room_id in ROOMS:
        return jsonify(ROOMS[room_id])
    return jsonify({'error': 'اتاق یافت نشد'}), 404

@app.route('/api/move', methods=['POST'])
def make_move():
    data = request.json
    room_id = data.get('room_id')
    sign = data.get('sign')
    index = int(data.get('index'))

    room = ROOMS.get(room_id)
    if not room or room['winner_status'] or not room['signs_chosen']:
        return jsonify({'error': 'غیرمجاز'}), 400

    if room['current_turn'] != sign or room['board'][index] != "":
        return jsonify({'error': 'حرکت اشتباه'}), 400

    room['board'][index] = sign
    
    win_conditions = [[0,1,2], [3,4,5], [6,7,8], [0,3,6], [1,4,7], [2,5,8], [0,4,8], [2,4,6]]
    won = False
    for condition in win_conditions:
        if room['board'][condition[0]] == room['board'][condition[1]] == room['board'][condition[2]] == sign:
            won = True
            room['winner_status'] = sign
            room['win_pattern'] = condition
            winner_name = room['p1'] if room['p1_sign'] == sign else room['p2']
            room['scores'][winner_name] += 1
            break

    if not won and "" not in room['board']:
        room['winner_status'] = 'draw'

    if room['winner_status']:
        def reset_board():
            time.sleep(3)
            if room_id in ROOMS:
                room['board'] = ["" for _ in range(9)]
                room['winner_status'] = None
                room['win_pattern'] = None
                room['signs_chosen'] = False 
                room['round_count'] += 1
                room['chooser_turn'] = room['p2'] if room['chooser_turn'] == room['p1'] and room['p2'] else room['p1']
                room['current_turn'] = room['first_turn_next_round']
                room['first_turn_next_round'] = 'O' if room['first_turn_next_round'] == 'X' else 'X'
            
        threading.Thread(target=reset_board).start()
    else:
        room['current_turn'] = 'O' if sign == 'X' else 'X'

    return jsonify(room)

@app.route('/api/leave', methods=['POST'])
def leave_room():
    data = request.json
    room_id = data.get('room_id')
    action = data.get('action')
    
    if room_id in ROOMS:
        if action == 'destroy':
            del ROOMS[room_id]
        elif action == 'guest_leave':
            room = ROOMS[room_id]
            guest_username = room['p2']
            if guest_username in room['scores']:
                del room['scores'][guest_username]
            
            room['p2'] = None
            room['p2_sign'] = None
            room['p1_sign'] = None
            room['signs_chosen'] = False
            room['board'] = ["" for _ in range(9)]
            room['current_turn'] = 'X'
            room['scores'][room['p1']] = 0 
            room['winner_status'] = None
            room['win_pattern'] = None
            
    return jsonify({'success': True})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
