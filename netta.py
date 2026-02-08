from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json

# ============ ИНИЦИАЛИЗАЦИЯ СУПЕР ПРИЛОЖЕНИЯ ============
app = Flask(__name__)

# Конфигурация
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'netta-mega-super-ultra-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///netta.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ============ МОДЕЛИ БАЗЫ ДАННЫХ ============

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    avatar_color = db.Column(db.String(7), default='#7c3aed')
    is_premium = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', backref='user_posts')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============ HTML ШАБЛОНЫ В КОДЕ ============

LOGIN_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌌 Netta | Вход в метавселенную</title>
    <style>
        /* ГЛОБАЛЬНЫЕ СТИЛИ */
        :root {
            --purple-neon: #bf00ff;
            --purple-deep: #7c3aed;
            --purple-light: #a855f7;
            --purple-dark: #5b21b6;
            --purple-gradient: linear-gradient(135deg, #7c3aed 0%, #bf00ff 100%);
            --space-bg: #0a0a1a;
            --card-bg: rgba(20, 15, 40, 0.9);
            --text-glow: 0 0 20px var(--purple-neon);
            --star-color: rgba(191, 0, 255, 0.3);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Orbitron', 'Segoe UI', sans-serif;
            background: var(--space-bg);
            color: white;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }
        
        /* КОСМИЧЕСКИЙ ФОН */
        .stars {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
        }
        
        .star {
            position: absolute;
            background: var(--star-color);
            border-radius: 50%;
            animation: twinkle 5s infinite;
        }
        
        @keyframes twinkle {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }
        
        /* ГЛАВНЫЙ КОНТЕЙНЕР */
        .main-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
        }
        
        /* КАРТОЧКА АВТОРИЗАЦИИ */
        .auth-matrix {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 2px solid transparent;
            border-radius: 30px;
            padding: 4rem;
            width: 100%;
            max-width: 500px;
            position: relative;
            overflow: hidden;
            box-shadow: 
                0 0 50px rgba(124, 58, 237, 0.3),
                inset 0 0 30px rgba(191, 0, 255, 0.1);
            animation: matrix-border 3s infinite linear;
            border-image: var(--purple-gradient) 1;
        }
        
        @keyframes matrix-border {
            0% { border-image-source: linear-gradient(0deg, #7c3aed, #bf00ff); }
            100% { border-image-source: linear-gradient(360deg, #7c3aed, #bf00ff); }
        }
        
        /* ЛОГОТИП NETTA */
        .logo-neon {
            text-align: center;
            margin-bottom: 3rem;
            position: relative;
        }
        
        .logo-neon .letter-n {
            display: inline-block;
            font-size: 5rem;
            font-weight: 900;
            background: var(--purple-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: var(--text-glow);
            animation: neon-pulse 2s infinite alternate;
        }
        
        @keyframes neon-pulse {
            from { filter: drop-shadow(0 0 10px var(--purple-neon)); }
            to { filter: drop-shadow(0 0 30px var(--purple-neon)); }
        }
        
        .logo-text {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(45deg, #a855f7, #ffffff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-left: 15px;
            letter-spacing: 3px;
        }
        
        /* ЗАГОЛОВОК */
        .auth-title {
            text-align: center;
            font-size: 2.2rem;
            margin-bottom: 2.5rem;
            background: var(--purple-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            position: relative;
        }
        
        .auth-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 3px;
            background: var(--purple-gradient);
            border-radius: 2px;
        }
        
        /* ФОРМА */
        .form-group {
            margin-bottom: 2rem;
            position: relative;
        }
        
        .input-neon {
            width: 100%;
            padding: 1.2rem 1.5rem;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 15px;
            color: white;
            font-size: 1.1rem;
            font-family: 'Segoe UI', sans-serif;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .input-neon:focus {
            outline: none;
            border-color: var(--purple-neon);
            box-shadow: 0 0 25px rgba(191, 0, 255, 0.4);
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
        }
        
        .input-neon::placeholder {
            color: rgba(255, 255, 255, 0.4);
        }
        
        /* КНОПКА */
        .btn-neon {
            width: 100%;
            padding: 1.3rem;
            background: var(--purple-gradient);
            border: none;
            border-radius: 15px;
            color: white;
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            z-index: 1;
        }
        
        .btn-neon::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: 0.5s;
            z-index: -1;
        }
        
        .btn-neon:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 
                0 10px 30px rgba(124, 58, 237, 0.4),
                0 0 50px rgba(191, 0, 255, 0.3);
        }
        
        .btn-neon:hover::before {
            left: 100%;
        }
        
        .btn-neon:active {
            transform: translateY(-2px) scale(1);
        }
        
        /* ССЫЛКИ */
        .auth-links {
            text-align: center;
            margin-top: 2.5rem;
            display: flex;
            justify-content: center;
            gap: 2rem;
        }
        
        .auth-link {
            color: #a855f7;
            text-decoration: none;
            font-weight: 500;
            position: relative;
            padding: 0.5rem 1rem;
            transition: 0.3s;
        }
        
        .auth-link::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 0;
            height: 2px;
            background: var(--purple-gradient);
            transition: width 0.3s;
        }
        
        .auth-link:hover {
            color: var(--purple-neon);
        }
        
        .auth-link:hover::after {
            width: 100%;
        }
        
        /* УВЕДОМЛЕНИЯ */
        .flash-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
        
        .flash-neon {
            padding: 1.2rem 2rem;
            margin-bottom: 1rem;
            border-radius: 15px;
            background: rgba(20, 15, 40, 0.95);
            border: 2px solid;
            backdrop-filter: blur(10px);
            animation: slide-in 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            gap: 10px;
            max-width: 400px;
        }
        
        @keyframes slide-in {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .flash-success {
            border-color: #10b981;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
        }
        
        .flash-error {
            border-color: #ef4444;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
        }
        
        /* ДОПОЛНИТЕЛЬНЫЕ ЭФФЕКТЫ */
        .matrix-code {
            position: absolute;
            color: rgba(191, 0, 255, 0.1);
            font-size: 0.9rem;
            font-family: monospace;
            user-select: none;
            z-index: -1;
        }
        
        /* АДАПТИВНОСТЬ */
        @media (max-width: 768px) {
            .auth-matrix {
                padding: 2.5rem 1.5rem;
                margin: 1rem;
            }
            
            .logo-neon .letter-n {
                font-size: 3.5rem;
            }
            
            .logo-text {
                font-size: 2rem;
            }
            
            .auth-title {
                font-size: 1.8rem;
            }
        }
        
        @media (max-width: 480px) {
            .auth-matrix {
                padding: 2rem 1rem;
            }
            
            .btn-neon, .input-neon {
                padding: 1rem;
            }
        }
        
        /* АНИМАЦИЯ ПОЯВЛЕНИЯ */
        @keyframes fade-in {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .auth-matrix {
            animation: fade-in 0.8s ease-out;
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&display=swap" rel="stylesheet">
</head>
<body>
    <!-- КОСМИЧЕСКИЙ ФОН -->
    <div class="stars" id="stars"></div>
    
    <div class="main-container">
        <div class="auth-matrix">
            <!-- ЛОГОТИП -->
            <div class="logo-neon">
                <span class="letter-n">N</span>
                <span class="logo-text">etta</span>
            </div>
            
            <!-- ЗАГОЛОВОК -->
            <h1 class="auth-title">ВОЙТИ В МЕТАВСЕЛЕННУЮ</h1>
            
            <!-- ФОРМА -->
            <form method="POST" action="{{ url_for('login') }}">
                <div class="form-group">
                    <input type="text" name="username" class="input-neon" required 
                           placeholder="👤 Имя пользователя или Email">
                </div>
                
                <div class="form-group">
                    <input type="password" name="password" class="input-neon" required 
                           placeholder="🔒 Пароль">
                </div>
                
                <button type="submit" class="btn-neon">
                    🚀 ПРОДОЛЖИТЬ ПУТЕШЕСТВИЕ
                </button>
            </form>
            
            <!-- ССЫЛКИ -->
            <div class="auth-links">
                <a href="{{ url_for('register') }}" class="auth-link">✨ СОЗДАТЬ АККАУНТ</a>
                <a href="#" class="auth-link">🌌 ДЕМО-РЕЖИМ</a>
            </div>
        </div>
    </div>
    
    <!-- СКРИПТ ДЛЯ ЗВЕЗД -->
    <script>
        // СОЗДАЕМ ЗВЕЗДНОЕ НЕБО
        function createStars() {
            const starsContainer = document.getElementById('stars');
            const starCount = 150;
            
            for (let i = 0; i < starCount; i++) {
                const star = document.createElement('div');
                star.classList.add('star');
                
                // Случайная позиция и размер
                const size = Math.random() * 3 + 1;
                const x = Math.random() * 100;
                const y = Math.random() * 100;
                const delay = Math.random() * 5;
                
                star.style.width = `${size}px`;
                star.style.height = `${size}px`;
                star.style.left = `${x}%`;
                star.style.top = `${y}%`;
                star.style.animationDelay = `${delay}s`;
                
                starsContainer.appendChild(star);
            }
        }
        
        // СЛУЧАЙНЫЕ ЦИФРЫ МАТРИЦЫ
        function createMatrixCode() {
            const codes = ['01001110', '01100101', '01110100', '01110100', '01100001',
                          '10101010', '11001100', '00110011', '11110000', '00001111'];
            
            const container = document.querySelector('.auth-matrix');
            for (let i = 0; i < 20; i++) {
                const code = document.createElement('div');
                code.classList.add('matrix-code');
                code.textContent = codes[Math.floor(Math.random() * codes.length)];
                code.style.left = `${Math.random() * 100}%`;
                code.style.top = `${Math.random() * 100}%`;
                code.style.opacity = Math.random() * 0.1 + 0.05;
                container.appendChild(code);
            }
        }
        
        // ИНИЦИАЛИЗАЦИЯ ПРИ ЗАГРУЗКЕ
        document.addEventListener('DOMContentLoaded', () => {
            createStars();
            createMatrixCode();
            
            // АНИМАЦИЯ ВВОДА
            const inputs = document.querySelectorAll('.input-neon');
            inputs.forEach(input => {
                input.addEventListener('focus', () => {
                    input.parentElement.style.transform = 'translateY(-5px)';
                });
                
                input.addEventListener('blur', () => {
                    input.parentElement.style.transform = 'translateY(0)';
                });
            });
            
            // ПРОВЕРКА УВЕДОМЛЕНИЙ
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    const flashContainer = document.createElement('div');
                    flashContainer.className = 'flash-container';
                    document.body.appendChild(flashContainer);
                    
                    {% for category, message in messages %}
                        const flash = document.createElement('div');
                        flash.className = `flash-neon flash-{{ category }}`;
                        flash.innerHTML = `
                            <span>{{ '✅' if category == 'success' else '⚠️' }}</span>
                            <span>{{ message }}</span>
                        `;
                        flashContainer.appendChild(flash);
                        
                        // АВТОМАТИЧЕСКОЕ УДАЛЕНИЕ
                        setTimeout(() => {
                            flash.style.animation = 'slide-out 0.5s forwards';
                            setTimeout(() => flash.remove(), 500);
                        }, 5000);
                    {% endfor %}
                    
                    // СТИЛЬ ДЛЯ ВЫХОДА
                    const style = document.createElement('style');
                    style.textContent = `
                        @keyframes slide-out {
                            from { transform: translateX(0); opacity: 1; }
                            to { transform: translateX(100%); opacity: 0; }
                        }
                    `;
                    document.head.appendChild(style);
                {% endif %}
            {% endwith %}
        });
    </script>
</body>
</html>'''

REGISTER_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌌 Netta | Стать частью вселенной</title>
    <style>
        /* СТИЛИ ТАКИЕ ЖЕ КАК В LOGIN, МЕНЯЕМ ТОЛЬКО ФОРМУ */
        :root {
            --purple-neon: #bf00ff;
            --purple-deep: #7c3aed;
            --purple-light: #a855f7;
            --purple-dark: #5b21b6;
            --purple-gradient: linear-gradient(135deg, #7c3aed 0%, #bf00ff 100%);
            --space-bg: #0a0a1a;
            --card-bg: rgba(20, 15, 40, 0.9);
            --text-glow: 0 0 20px var(--purple-neon);
            --star-color: rgba(191, 0, 255, 0.3);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Orbitron', 'Segoe UI', sans-serif;
            background: var(--space-bg);
            color: white;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }
        
        .stars { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; }
        
        .main-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .auth-matrix {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 2px solid transparent;
            border-radius: 30px;
            padding: 4rem;
            width: 100%;
            max-width: 600px;
            position: relative;
            overflow: hidden;
            box-shadow: 
                0 0 50px rgba(124, 58, 237, 0.3),
                inset 0 0 30px rgba(191, 0, 255, 0.1);
            animation: matrix-border 3s infinite linear, fade-in 0.8s ease-out;
            border-image: var(--purple-gradient) 1;
        }
        
        @keyframes matrix-border {
            0% { border-image-source: linear-gradient(0deg, #7c3aed, #bf00ff); }
            100% { border-image-source: linear-gradient(360deg, #7c3aed, #bf00ff); }
        }
        
        .logo-neon {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        .logo-neon .letter-n {
            display: inline-block;
            font-size: 5rem;
            font-weight: 900;
            background: var(--purple-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: var(--text-glow);
            animation: neon-pulse 2s infinite alternate;
        }
        
        @keyframes neon-pulse {
            from { filter: drop-shadow(0 0 10px var(--purple-neon)); }
            to { filter: drop-shadow(0 0 30px var(--purple-neon)); }
        }
        
        .logo-text {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(45deg, #a855f7, #ffffff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-left: 15px;
            letter-spacing: 3px;
        }
        
        .auth-title {
            text-align: center;
            font-size: 2.2rem;
            margin-bottom: 2.5rem;
            background: var(--purple-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            position: relative;
        }
        
        .auth-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 150px;
            height: 3px;
            background: var(--purple-gradient);
            border-radius: 2px;
        }
        
        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .form-group {
            position: relative;
        }
        
        .input-neon {
            width: 100%;
            padding: 1.2rem 1.5rem;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 15px;
            color: white;
            font-size: 1.1rem;
            font-family: 'Segoe UI', sans-serif;
            transition: all 0.4s;
        }
        
        .input-neon:focus {
            outline: none;
            border-color: var(--purple-neon);
            box-shadow: 0 0 25px rgba(191, 0, 255, 0.4);
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
        }
        
        .btn-neon {
            width: 100%;
            padding: 1.3rem;
            background: var(--purple-gradient);
            border: none;
            border-radius: 15px;
            color: white;
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.4s;
            position: relative;
            overflow: hidden;
        }
        
        .btn-neon:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 
                0 10px 30px rgba(124, 58, 237, 0.4),
                0 0 50px rgba(191, 0, 255, 0.3);
        }
        
        .auth-links {
            text-align: center;
            margin-top: 2.5rem;
        }
        
        .auth-link {
            color: #a855f7;
            text-decoration: none;
            font-weight: 500;
            position: relative;
            padding: 0.5rem 1rem;
            transition: 0.3s;
        }
        
        .auth-link::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 0;
            height: 2px;
            background: var(--purple-gradient);
            transition: width 0.3s;
        }
        
        .auth-link:hover::after {
            width: 100%;
        }
        
        .terms {
            margin: 2rem 0;
            text-align: center;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .form-grid {
                grid-template-columns: 1fr;
            }
            
            .auth-matrix {
                padding: 2.5rem 1.5rem;
                margin: 1rem;
            }
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&display=swap" rel="stylesheet">
</head>
<body>
    <div class="stars" id="stars"></div>
    
    <div class="main-container">
        <div class="auth-matrix">
            <div class="logo-neon">
                <span class="letter-n">N</span>
                <span class="logo-text">etta</span>
            </div>
            
            <h1 class="auth-title">СТАТЬ ЧАСТЬЮ ВСЕЛЕННОЙ</h1>
            
            <form method="POST" action="{{ url_for('register') }}">
                <div class="form-grid">
                    <div class="form-group">
                        <input type="text" name="username" class="input-neon" required 
                               placeholder="👤 Имя пользователя">
                    </div>
                    
                    <div class="form-group">
                        <input type="email" name="email" class="input-neon" required 
                               placeholder="📧 Email адрес">
                    </div>
                    
                    <div class="form-group">
                        <input type="password" name="password" class="input-neon" required 
                               placeholder="🔒 Пароль">
                    </div>
                    
                    <div class="form-group">
                        <input type="password" name="confirm_password" class="input-neon" required 
                               placeholder="🔁 Подтвердите пароль">
                    </div>
                </div>
                
                <div class="form-group">
                    <input type="text" name="full_name" class="input-neon" 
                           placeholder="🌟 Ваше имя (необязательно)">
                </div>
                
                <div class="terms">
                    Нажимая кнопку, вы соглашаетесь с правилами нашей вселенной
                </div>
                
                <button type="submit" class="btn-neon">
                    🪐 СОЗДАТЬ ПРОСТРАНСТВО
                </button>
            </form>
            
            <div class="auth-links">
                <a href="{{ url_for('login') }}" class="auth-link">← ВЕРНУТЬСЯ К ВХОДУ</a>
            </div>
        </div>
    </div>
    
    <script>
        // СОЗДАЕМ ЗВЕЗДЫ
        function createStars() {
            const starsContainer = document.getElementById('stars');
            for (let i = 0; i < 150; i++) {
                const star = document.createElement('div');
                star.classList.add('star');
                star.style.cssText = `
                    position: absolute;
                    background: rgba(191, 0, 255, 0.3);
                    border-radius: 50%;
                    width: ${Math.random() * 3 + 1}px;
                    height: ${Math.random() * 3 + 1}px;
                    left: ${Math.random() * 100}%;
                    top: ${Math.random() * 100}%;
                    animation: twinkle ${Math.random() * 5 + 3}s infinite;
                `;
                starsContainer.appendChild(star);
            }
            
            const style = document.createElement('style');
            style.textContent = `
                @keyframes twinkle {
                    0%, 100% { opacity: 0.3; }
                    50% { opacity: 1; }
                }
                .star { position: absolute; }
            `;
            document.head.appendChild(style);
        }
        
        document.addEventListener('DOMContentLoaded', createStars);
    </script>
</body>
</html>'''

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌌 Netta | Космическая лента</title>
    <style>
        :root {
            --purple-neon: #bf00ff;
            --purple-deep: #7c3aed;
            --purple-light: #a855f7;
            --purple-dark: #5b21b6;
            --purple-gradient: linear-gradient(135deg, #7c3aed 0%, #bf00ff 100%);
            --space-bg: #0a0a1a;
            --card-bg: rgba(20, 15, 40, 0.9);
            --sidebar-bg: rgba(10, 5, 25, 0.95);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Orbitron', 'Segoe UI', sans-serif;
            background: var(--space-bg);
            color: white;
            min-height: 100vh;
        }
        
        /* ШАПКА */
        .header {
            background: var(--sidebar-bg);
            backdrop-filter: blur(20px);
            border-bottom: 2px solid var(--purple-deep);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 5px 30px rgba(124, 58, 237, 0.2);
        }
        
        .navbar {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
        }
        
        .logo-icon {
            width: 45px;
            height: 45px;
            background: var(--purple-gradient);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            font-weight: 900;
            color: white;
            animation: neon-pulse 2s infinite alternate;
        }
        
        @keyframes neon-pulse {
            from { box-shadow: 0 0 20px var(--purple-neon); }
            to { box-shadow: 0 0 40px var(--purple-neon); }
        }
        
        .logo-text {
            font-size: 1.8rem;
            font-weight: 900;
            background: linear-gradient(45deg, #a855f7, #ffffff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* ПОИСК */
        .search-bar {
            flex: 1;
            max-width: 500px;
            margin: 0 2rem;
            position: relative;
        }
        
        .search-input {
            width: 100%;
            padding: 0.8rem 1.5rem 0.8rem 3rem;
            background: rgba(255, 255, 255, 0.07);
            border: 2px solid rgba(124, 58, 237, 0.4);
            border-radius: 25px;
            color: white;
            font-size: 1rem;
            transition: 0.3s;
        }
        
        .search-input:focus {
            outline: none;
            border-color: var(--purple-neon);
            box-shadow: 0 0 20px rgba(191, 0, 255, 0.3);
        }
        
        /* ИКОНКИ */
        .nav-icons {
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }
        
        .nav-icon {
            width: 45px;
            height: 45px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(124, 58, 237, 0.1);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 50%;
            color: #a855f7;
            text-decoration: none;
            font-size: 1.2rem;
            transition: 0.3s;
            position: relative;
        }
        
        .nav-icon:hover {
            background: rgba(124, 58, 237, 0.2);
            border-color: var(--purple-neon);
            transform: translateY(-3px);
            box-shadow: 0 5px 20px rgba(191, 0, 255, 0.3);
        }
        
        .badge {
            position: absolute;
            top: -5px;
            right: -5px;
            background: var(--purple-gradient);
            color: white;
            font-size: 0.7rem;
            font-weight: bold;
            min-width: 20px;
            height: 20px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 5px;
        }
        
        /* ОСНОВНОЙ КОНТЕНТ */
        .main-layout {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 2rem;
            display: grid;
            grid-template-columns: 280px 1fr 350px;
            gap: 2rem;
            min-height: calc(100vh - 80px);
        }
        
        /* САЙДБАР */
        .sidebar {
            position: sticky;
            top: 90px;
            height: fit-content;
        }
        
        .user-card {
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .user-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: {{ current_user.avatar_color }};
            margin: 0 auto 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            font-weight: bold;
            border: 3px solid var(--purple-neon);
            box-shadow: 0 0 20px {{ current_user.avatar_color }};
        }
        
        /* СОЗДАНИЕ ПОСТА */
        .create-post {
            background: var(--card-bg);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            backdrop-filter: blur(10px);
        }
        
        .post-editor {
            width: 100%;
            min-height: 120px;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 15px;
            color: white;
            font-size: 1rem;
            resize: vertical;
            margin-bottom: 1rem;
        }
        
        .post-editor:focus {
            outline: none;
            border-color: var(--purple-neon);
            box-shadow: 0 0 20px rgba(191, 0, 255, 0.2);
        }
        
        /* ПОСТЫ */
        .feed {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        .post {
            background: var(--card-bg);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 20px;
            padding: 1.5rem;
            backdrop-filter: blur(10px);
            transition: 0.3s;
        }
        
        .post:hover {
            border-color: var(--purple-neon);
            box-shadow: 0 10px 30px rgba(191, 0, 255, 0.2);
            transform: translateY(-5px);
        }
        
        /* ПРАВАЯ КОЛОНКА */
        .right-sidebar {
            position: sticky;
            top: 90px;
            height: fit-content;
        }
        
        .widget {
            background: var(--card-bg);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            backdrop-filter: blur(10px);
        }
        
        /* АДАПТИВНОСТЬ */
        @media (max-width: 1200px) {
            .main-layout {
                grid-template-columns: 250px 1fr;
            }
            .right-sidebar {
                display: none;
            }
        }
        
        @media (max-width: 992px) {
            .main-layout {
                grid-template-columns: 1fr;
                padding: 1rem;
            }
            .sidebar {
                display: none;
            }
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <!-- ШАПКА -->
    <header class="header">
        <nav class="navbar">
            <!-- ЛОГО -->
            <a href="{{ url_for('index') }}" class="logo">
                <div class="logo-icon">N</div>
                <div class="logo-text">etta</div>
            </a>
            
            <!-- ПОИСК -->
            <div class="search-bar">
                <input type="text" class="search-input" placeholder="🔍 Поиск во вселенной...">
            </div>
            
            <!-- ИКОНКИ -->
            <div class="nav-icons">
                <a href="#" class="nav-icon" title="Главная">
                    <i class="fas fa-home"></i>
                </a>
                
                <a href="#" class="nav-icon" title="Уведомления">
                    <i class="fas fa-bell"></i>
                    <span class="badge">3</span>
                </a>
                
                <a href="#" class="nav-icon" title="Сообщения">
                    <i class="fas fa-comments"></i>
                    <span class="badge">5</span>
                </a>
                
                <a href="#" class="nav-icon" title="Друзья">
                    <i class="fas fa-user-friends"></i>
                </a>
                
                <a href="{{ url_for('logout') }}" class="nav-icon" title="Выйти">
                    <i class="fas fa-sign-out-alt"></i>
                </a>
            </div>
        </nav>
    </header>
    
    <!-- ОСНОВНОЙ КОНТЕНТ -->
    <main class="main-layout">
        <!-- ЛЕВЫЙ САЙДБАР -->
        <aside class="sidebar">
            <!-- ПРОФИЛЬ -->
            <div class="user-card">
                <div class="user-avatar">
                    {{ current_user.username[0].upper() }}
                </div>
                <h3 style="text-align: center; margin-bottom: 0.5rem;">
                    {{ current_user.full_name or current_user.username }}
                </h3>
                <p style="text-align: center; color: #a855f7; margin-bottom: 1rem;">
                    @{{ current_user.username }}
                </p>
                <p style="text-align: center; color: rgba(255, 255, 255, 0.7); font-size: 0.9rem;">
                    {{ current_user.bio or 'Исследователь вселенной Netta 🌌' }}
                </p>
            </div>
            
            <!-- НАВИГАЦИЯ -->
            <div class="widget">
                <h3 style="margin-bottom: 1rem; color: var(--purple-light);">
                    <i class="fas fa-rocket"></i> Навигация
                </h3>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    <a href="#" style="color: white; text-decoration: none; padding: 0.8rem; border-radius: 10px; transition: 0.3s;"
                       onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" 
                       onmouseout="this.style.background='transparent';">
                        <i class="fas fa-compass"></i> Исследовать
                    </a>
                    <a href="#" style="color: white; text-decoration: none; padding: 0.8rem; border-radius: 10px; transition: 0.3s;"
                       onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" 
                       onmouseout="this.style.background='transparent';">
                        <i class="fas fa-users"></i> Сообщества
                    </a>
                    <a href="#" style="color: white; text-decoration: none; padding: 0.8rem; border-radius: 10px; transition: 0.3s;"
                       onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" 
                       onmouseout="this.style.background='transparent';">
                        <i class="fas fa-gamepad"></i> Игры
                    </a>
                    <a href="#" style="color: white; text-decoration: none; padding: 0.8rem; border-radius: 10px; transition: 0.3s;"
                       onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" 
                       onmouseout="this.style.background='transparent';">
                        <i class="fas fa-cog"></i> Настройки
                    </a>
                </div>
            </div>
        </aside>
        
        <!-- ЦЕНТРАЛЬНАЯ ЛЕНТА -->
        <section class="feed">
            <!-- СОЗДАНИЕ ПОСТА -->
            <div class="create-post">
                <form method="POST" action="{{ url_for('create_post') }}">
                    <textarea name="content" class="post-editor" 
                              placeholder="🌌 Что происходит в вашей вселенной, {{ current_user.username }}?"></textarea>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; gap: 1rem;">
                            <button type="button" style="background: none; border: none; color: #a855f7; font-size: 1.2rem; cursor: pointer;" 
                                    title="Добавить фото">
                                <i class="fas fa-image"></i>
                            </button>
                            <button type="button" style="background: none; border: none; color: #a855f7; font-size: 1.2rem; cursor: pointer;"
                                    title="Добавить видео">
                                <i class="fas fa-video"></i>
                            </button>
                            <button type="button" style="background: none; border: none; color: #a855f7; font-size: 1.2rem; cursor: pointer;"
                                    title="Добавить эмоцию">
                                <i class="fas fa-smile"></i>
                            </button>
                        </div>
                        <button type="submit" style="padding: 0.8rem 2rem; background: var(--purple-gradient); border: none; 
                                border-radius: 15px; color: white; font-weight: bold; cursor: pointer; transition: 0.3s;"
                                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 5px 20px rgba(191, 0, 255, 0.3)';"
                                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                            <i class="fas fa-paper-plane"></i> Опубликовать
                        </button>
                    </div>
                </form>
            </div>
            
            <!-- ПОСТЫ -->
            {% for post in posts %}
            <div class="post">
                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                    <div style="width: 50px; height: 50px; border-radius: 50%; background: {{ post.author.avatar_color }}; 
                         display: flex; align-items: center; justify-content: center; font-weight: bold; 
                         margin-right: 1rem; border: 2px solid var(--purple-light);">
                        {{ post.author.username[0].upper() }}
                    </div>
                    <div>
                        <div style="font-weight: bold;">
                            {{ post.author.full_name or post.author.username }}
                        </div>
                        <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.6);">
                            {{ post.created_at.strftime('%d %b в %H:%M') }}
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 1rem; line-height: 1.6;">
                    {{ post.content }}
                </div>
                
                <div style="display: flex; gap: 2rem; color: rgba(255, 255, 255, 0.7);">
                    <form method="POST" action="{{ url_for('like_post', post_id=post.id) }}" style="display: inline;">
                        <button type="submit" style="background: none; border: none; color: {% if post.id in liked_posts %}var(--purple-neon){% else %}inherit{% endif %}; 
                                cursor: pointer; display: flex; align-items: center; gap: 0.5rem; font-size: 1rem; transition: 0.3s;"
                                onmouseover="this.style.color='var(--purple-neon)';">
                            <i class="fas fa-heart"></i> {{ post.likes }} ❤️
                        </button>
                    </form>
                    <button style="background: none; border: none; color: inherit; cursor: pointer; 
                            display: flex; align-items: center; gap: 0.5rem; font-size: 1rem; transition: 0.3s;"
                            onmouseover="this.style.color='var(--purple-neon)';">
                        <i class="fas fa-comment"></i> Комментировать
                    </button>
                    <button style="background: none; border: none; color: inherit; cursor: pointer; 
                            display: flex; align-items: center; gap: 0.5rem; font-size: 1rem; transition: 0.3s;"
                            onmouseover="this.style.color='var(--purple-neon)';">
                        <i class="fas fa-share"></i> Поделиться
                    </button>
                </div>
            </div>
            {% endfor %}
        </section>
        
        <!-- ПРАВАЯ КОЛОНКА -->
        <aside class="right-sidebar">
            <!-- ТРЕНДЫ -->
            <div class="widget">
                <h3 style="margin-bottom: 1rem; color: var(--purple-light);">
                    <i class="fas fa-fire"></i> Тренды вселенной
                </h3>
                <div style="display: flex; flex-direction: column; gap: 0.8rem;">
                    {% for trend in trends %}
                    <div style="padding: 0.8rem; background: rgba(255, 255, 255, 0.03); border-radius: 10px; cursor: pointer; transition: 0.3s;"
                         onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';">
                        <div style="font-weight: bold; color: var(--purple-light);">#{{ trend.tag }}</div>
                        <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.6);">{{ trend.count }} постов</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- ОНЛАЙН ДРУЗЬЯ -->
            <div class="widget">
                <h3 style="margin-bottom: 1rem; color: var(--purple-light);">
                    <i class="fas fa-satellite"></i> В сети сейчас
                </h3>
                <div style="display: flex; flex-direction: column; gap: 0.8rem;">
                    {% for friend in online_friends %}
                    <div style="display: flex; align-items: center; gap: 0.8rem; padding: 0.5rem; border-radius: 10px; cursor: pointer; transition: 0.3s;"
                         onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';">
                        <div style="width: 40px; height: 40px; border-radius: 50%; background: {{ friend.avatar_color }}; 
                             display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid #10b981;">
                            {{ friend.username[0].upper() }}
                        </div>
                        <div>
                            <div style="font-weight: bold;">{{ friend.username }}</div>
                            <div style="font-size: 0.8rem; color: #10b981;">
                                <i class="fas fa-circle" style="font-size: 0.6rem;"></i> Онлайн
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </aside>
    </main>
    
    <!-- ФУТЕР -->
    <footer style="text-align: center; padding: 2rem; color: rgba(255, 255, 255, 0.5); border-top: 1px solid rgba(124, 58, 237, 0.2);">
        <div style="max-width: 1400px; margin: 0 auto;">
            <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem; flex-wrap: wrap;">
                <a href="#" style="color: rgba(255, 255, 255, 0.7); text-decoration: none; transition: 0.3s;"
                   onmouseover="this.style.color='var(--purple-light)';">
                    О Netta
                </a>
                <a href="#" style="color: rgba(255, 255, 255, 0.7); text-decoration: none; transition: 0.3s;"
                   onmouseover="this.style.color='var(--purple-light)';">
                    Помощь
                </a>
                <a href="#" style="color: rgba(255, 255, 255, 0.7); text-decoration: none; transition: 0.3s;"
                   onmouseover="this.style.color='var(--purple-light)';">
                    Конфиденциальность
                </a>
                <a href="#" style="color: rgba(255, 255, 255, 0.7); text-decoration: none; transition: 0.3s;"
                   onmouseover="this.style.color='var(--purple-light)';">
                    Условия
                </a>
                <a href="#" style="color: rgba(255, 255, 255, 0.7); text-decoration: none; transition: 0.3s;"
                   onmouseover="this.style.color='var(--purple-light)';">
                    Разработчикам
                </a>
            </div>
            <div style="margin-bottom: 1rem;">
                <span style="color: var(--purple-light); font-weight: bold;">Netta</span> 
                — Социальная сеть нового поколения 🌌
            </div>
            <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.4);">
                © 2026 Netta Universe. Все права защищены.
            </div>
        </div>
    </footer>
    
    <script>
        // АНИМАЦИИ И ЭФФЕКТЫ
        document.addEventListener('DOMContentLoaded', function() {
            // Анимация постов при прокрутке
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            });
            
            document.querySelectorAll('.post').forEach(post => {
                post.style.opacity = '0';
                post.style.transform = 'translateY(20px)';
                post.style.transition = 'opacity 0.5s, transform 0.5s';
                observer.observe(post);
            });
            
            // Эффект при наведении на кнопки лайков
            document.querySelectorAll('button[type="submit"]').forEach(button => {
                if (button.innerHTML.includes('fa-heart')) {
                    button.addEventListener('click', function(e) {
                        // Предотвращаем отправку для анимации
                        setTimeout(() => {
                            const heart = document.createElement('div');
                            heart.innerHTML = '❤️';
                            heart.style.position = 'fixed';
                            heart.style.fontSize = '2rem';
                            heart.style.color = '#bf00ff';
                            heart.style.zIndex = '10000';
                            heart.style.pointerEvents = 'none';
                            
                            const rect = button.getBoundingClientRect();
                            heart.style.left = (rect.left + rect.width/2 - 16) + 'px';
                            heart.style.top = (rect.top - 32) + 'px';
                            
                            document.body.appendChild(heart);
                            
                            // Анимация
                            heart.animate([
                                { transform: 'translateY(0) scale(1)', opacity: 1 },
                                { transform: 'translateY(-100px) scale(1.5)', opacity: 0 }
                            ], {
                                duration: 800,
                                easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
                            }).onfinish = () => heart.remove();
                        }, 100);
                    });
                }
            });
            
            // ЭФФЕКТ ПАДАЮЩИХ ЗВЕЗД
            function createFallingStars() {
                setInterval(() => {
                    if (Math.random() > 0.7) {
                        const star = document.createElement('div');
                        star.style.cssText = `
                            position: fixed;
                            width: 2px;
                            height: 20px;
                            background: linear-gradient(to bottom, transparent, #bf00ff, transparent);
                            top: -20px;
                            left: ${Math.random() * 100}%;
                            z-index: -1;
                            animation: fall 2s linear forwards;
                        `;
                        document.body.appendChild(star);
                        
                        setTimeout(() => star.remove(), 2000);
                    }
                }, 1000);
                
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes fall {
                        to { transform: translateY(100vh) rotate(360deg); }
                    }
                `;
                document.head.appendChild(style);
            }
            
            createFallingStars();
        });
    </script>
</body>
</html>'''

# ============ МАРШРУТЫ ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
        liked_posts = [like.post_id for like in current_user.likes]
        
        # Тестовые данные для правой колонки
        trends = [
            {'tag': 'NettaLaunch', 'count': '1.2K'},
            {'tag': 'ФиолетоваяВселенная', 'count': '856'},
            {'tag': 'КосмическийДизайн', 'count': '543'},
            {'tag': 'НовыеГоризонты', 'count': '321'}
        ]
        
        online_friends = [
            {'username': 'Космонавт', 'avatar_color': '#a855f7'},
            {'username': 'Звездочёт', 'avatar_color': '#7c3aed'},
            {'username': 'Галактика', 'avatar_color': '#bf00ff'},
            {'username': 'Нейтрон', 'avatar_color': '#5b21b6'}
        ]
        
        html = DASHBOARD_HTML.replace('{{ current_user.username }}', current_user.username)\
                            .replace('{{ current_user.full_name }}', current_user.full_name or current_user.username)\
                            .replace('{{ current_user.avatar_color }}', current_user.avatar_color)\
                            .replace('{{ current_user.bio }}', current_user.bio or '')
        
        # Добавляем посты
        posts_html = ''
        for post in posts:
            post_html = f'''
            <div class="post">
                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                    <div style="width: 50px; height: 50px; border-radius: 50%; background: {post.author.avatar_color}; 
                         display: flex; align-items: center; justify-content: center; font-weight: bold; 
                         margin-right: 1rem; border: 2px solid var(--purple-light);">
                        {post.author.username[0].upper()}
                    </div>
                    <div>
                        <div style="font-weight: bold;">
                            {post.author.full_name or post.author.username}
                        </div>
                        <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.6);">
                            {post.created_at.strftime('%d %b в %H:%M')}
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 1rem; line-height: 1.6;">
                    {post.content}
                </div>
                
                <div style="display: flex; gap: 2rem; color: rgba(255, 255, 255, 0.7);">
                    <form method="POST" action="/like/{post.id}" style="display: inline;">
                        <button type="submit" style="background: none; border: none; color: {"var(--purple-neon)" if post.id in liked_posts else "inherit"}; 
                                cursor: pointer; display: flex; align-items: center; gap: 0.5rem; font-size: 1rem; transition: 0.3s;"
                                onmouseover="this.style.color='var(--purple-neon)';">
                            <i class="fas fa-heart"></i> {post.likes} ❤️
                        </button>
                    </form>
                    <button style="background: none; border: none; color: inherit; cursor: pointer; 
                            display: flex; align-items: center; gap: 0.5rem; font-size: 1rem; transition: 0.3s;"
                            onmouseover="this.style.color='var(--purple-neon)';">
                        <i class="fas fa-comment"></i> Комментировать
                    </button>
                </div>
            </div>
            '''
            posts_html += post_html
        
        html = html.replace('{% for post in posts %}\n            {{ post.content }}\n            {% endfor %}', posts_html)
        
        # Добавляем тренды
        trends_html = ''
        for trend in trends:
            trends_html += f'''
                    <div style="padding: 0.8rem; background: rgba(255, 255, 255, 0.03); border-radius: 10px; cursor: pointer; transition: 0.3s;"
                         onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';">
                        <div style="font-weight: bold; color: var(--purple-light);">#{trend['tag']}</div>
                        <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.6);">{trend['count']} постов</div>
                    </div>
            '''
        
        html = html.replace('{% for trend in trends %}\n                    {{ trend.html }}\n                    {% endfor %}', trends_html)
        
        # Добавляем онлайн друзей
        friends_html = ''
        for friend in online_friends:
            friends_html += f'''
                    <div style="display: flex; align-items: center; gap: 0.8rem; padding: 0.5rem; border-radius: 10px; cursor: pointer; transition: 0.3s;"
                         onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';">
                        <div style="width: 40px; height: 40px; border-radius: 50%; background: {friend['avatar_color']}; 
                             display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid #10b981;">
                            {friend['username'][0].upper()}
                        </div>
                        <div>
                            <div style="font-weight: bold;">{friend['username']}</div>
                            <div style="font-size: 0.8rem; color: #10b981;">
                                <i class="fas fa-circle" style="font-size: 0.6rem;"></i> Онлайн
                            </div>
                        </div>
                    </div>
            '''
        
        html = html.replace('{% for friend in online_friends %}\n                    {{ friend.html }}\n                    {% endfor %}', friends_html)
        
        return html
    return LOGIN_HTML

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user and user.check_password(password):
            user.last_seen = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash('Добро пожаловать в метавселенную Netta! 🌌', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверные данные. Попробуйте снова.', 'error')
    
    return LOGIN_HTML

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form.get('full_name', '')
        
        # Валидация
        if password != confirm_password:
            flash('Пароли не совпадают! 🔐', 'error')
            return REGISTER_HTML
        
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято! 👤', 'error')
            return REGISTER_HTML
        
        if User.query.filter_by(email=email).first():
            flash('Этот email уже используется! 📧', 'error')
            return REGISTER_HTML
        
        if len(password) < 6:
            flash('Пароль должен быть минимум 6 символов! ⚠️', 'error')
            return REGISTER_HTML
        
        # Цвета для аватара
        colors = ['#7c3aed', '#a855f7', '#bf00ff', '#5b21b6', '#8b5cf6']
        import random
        
        # Создание пользователя
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            avatar_color=random.choice(colors)
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Ваше пространство создано! Добро пожаловать в Netta! 🚀', 'success')
        return redirect(url_for('login'))
    
    return REGISTER_HTML

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы покинули вселенную Netta. Возвращайтесь скорее! 👋', 'success')
    return redirect(url_for('login'))

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form['content']
    if content.strip():
        post = Post(content=content, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Ваш пост запущен в космос! 🌠', 'success')
    return redirect(url_for('index'))

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get(post_id)
    if post:
        existing_like = next((like for like in current_user.likes if like.post_id == post_id), None)
        if existing_like:
            db.session.delete(existing_like)
            post.likes = max(0, post.likes - 1)
        else:
            from flask_login import current_user
            like = type('Like', (), {})()
            like.user_id = current_user.id
            like.post_id = post_id
            like.created_at = datetime.utcnow()
            post.likes += 1
            # В реальной реализации нужно создать модель Like
        
        db.session.commit()
    
    return redirect(url_for('index'))

# Обработка 404
@app.errorhandler(404)
def not_found(error):
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Потерялся в космосе</title>
        <style>
            body {
                background: #0a0a1a;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                text-align: center;
                font-family: 'Orbitron', sans-serif;
            }
            .container {
                max-width: 600px;
                padding: 2rem;
            }
            h1 {
                font-size: 8rem;
                margin: 0;
                background: linear-gradient(45deg, #7c3aed, #bf00ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: neon-pulse 2s infinite alternate;
            }
            .btn {
                display: inline-block;
                margin-top: 2rem;
                padding: 1rem 2rem;
                background: linear-gradient(135deg, #7c3aed, #5b21b6);
                color: white;
                text-decoration: none;
                border-radius: 15px;
                font-weight: bold;
                transition: 0.3s;
            }
            .btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 30px rgba(191, 0, 255, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>404</h1>
            <h2>Вы потерялись в космосе</h2>
            <p>Эта планета еще не открыта. Возвращайтесь на базу!</p>
            <a href="/" class="btn">🚀 Вернуться на Землю</a>
        </div>
    </body>
    </html>
    ''', 404

# Запуск приложения
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Создаем тестовых пользователей если их нет
        if not User.query.first():
            test_users = [
                {'username': 'admin', 'email': 'admin@netta.com', 'password': 'admin123', 'full_name': 'Админ Вселенной', 'avatar_color': '#bf00ff'},
                {'username': 'cosmos', 'email': 'cosmos@netta.com', 'password': 'cosmos123', 'full_name': 'Космический Путешественник', 'avatar_color': '#7c3aed'},
                {'username': 'nebula', 'email': 'nebula@netta.com', 'password': 'nebula123', 'full_name': 'Туманность Андромеды', 'avatar_color': '#a855f7'},
            ]
            
            for user_data in test_users:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    full_name=user_data['full_name'],
                    avatar_color=user_data['avatar_color']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
            
            # Тестовые посты
            posts = [
                'Привет всем! Это новая социальная сеть Netta! 🌌',
                'Кто хочет исследовать новые галактики вместе? 🚀',
                'Сегодня наблюдал за звездопадом. Невероятное зрелище! ✨',
                'Разрабатываю новый космический корабль. Есть идеи? 🛸',
                'Фиолетовый - цвет бесконечности и тайн вселенной! 🟣'
            ]
            
            for i, content in enumerate(posts):
                post = Post(
                    content=content,
                    user_id=(i % 3) + 1,  # Распределяем по пользователям
                    likes=i * 2 + 1
                )
                db.session.add(post)
            
            db.session.commit()
            print("✅ База данных создана с тестовыми данными!")
            print("👤 Тестовые пользователи:")
            print("   admin / admin123")
            print("   cosmos / cosmos123")
            print("   nebula / nebula123")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
