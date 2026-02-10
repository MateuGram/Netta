from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import random

# ============ ИНИЦИАЛИЗАЦИЯ ============
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'netta-mega-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///netta.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ============ МОДЕЛИ ============
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text, default='Исследователь вселенной Netta 🌌')
    avatar_color = db.Column(db.String(7), default='#7c3aed')
    level = db.Column(db.Integer, default=1)
    coins = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    posts_count = db.Column(db.Integer, default=0)
    friends_count = db.Column(db.Integer, default=0)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', backref='user_posts')

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============ HTML ШАБЛОНЫ ============
BASE_STYLE = '''
<style>
    :root {
        --purple-neon: #bf00ff;
        --purple-deep: #7c3aed;
        --purple-light: #a855f7;
        --purple-dark: #5b21b6;
        --space-bg: #0a0a1a;
        --card-bg: rgba(20, 15, 40, 0.9);
        --gradient: linear-gradient(135deg, #7c3aed 0%, #bf00ff 100%);
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: var(--space-bg);
        color: white;
        min-height: 100vh;
    }
    .container { max-width: 1200px; margin: 0 auto; padding: 0 1rem; }
    .header {
        background: rgba(10, 5, 25, 0.95);
        border-bottom: 2px solid var(--purple-deep);
        padding: 1rem 0;
        position: sticky;
        top: 0;
        z-index: 1000;
        backdrop-filter: blur(10px);
    }
    .navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .logo {
        display: flex;
        align-items: center;
        gap: 10px;
        text-decoration: none;
        font-size: 1.5rem;
        font-weight: 800;
        color: white;
    }
    .logo-icon {
        width: 40px;
        height: 40px;
        background: var(--gradient);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        font-weight: 900;
        color: white;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 20px var(--purple-neon); }
        50% { box-shadow: 0 0 40px var(--purple-neon); }
    }
    .auth-container {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        padding: 2rem;
        background: var(--space-bg);
        background-image: 
            radial-gradient(circle at 20% 80%, rgba(124, 58, 237, 0.15) 0%, transparent 40%),
            radial-gradient(circle at 80% 20%, rgba(168, 85, 247, 0.1) 0%, transparent 40%);
    }
    .auth-card {
        background: var(--card-bg);
        border: 2px solid rgba(124, 58, 237, 0.3);
        border-radius: 20px;
        padding: 3rem;
        width: 100%;
        max-width: 500px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    }
    .auth-title {
        text-align: center;
        margin-bottom: 2rem;
        font-size: 2rem;
        background: var(--gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .form-group { margin-bottom: 1.5rem; }
    .form-control {
        width: 100%;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border: 2px solid rgba(124, 58, 237, 0.3);
        border-radius: 10px;
        color: white;
        font-size: 1rem;
        transition: 0.3s;
    }
    .form-control:focus {
        outline: none;
        border-color: var(--purple-neon);
        box-shadow: 0 0 20px rgba(191, 0, 255, 0.3);
    }
    .btn-primary {
        width: 100%;
        padding: 1rem;
        background: var(--gradient);
        border: none;
        border-radius: 10px;
        color: white;
        font-weight: 600;
        font-size: 1rem;
        cursor: pointer;
        transition: 0.3s;
    }
    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(191, 0, 255, 0.3);
    }
    .auth-links {
        text-align: center;
        margin-top: 2rem;
        color: #a855f7;
    }
    .auth-link {
        color: var(--purple-light);
        text-decoration: none;
        font-weight: 500;
    }
    .auth-link:hover { text-decoration: underline; }
    .flash-message {
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 10px;
        text-align: center;
        animation: slideIn 0.3s ease-out;
    }
    @keyframes slideIn {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    .flash-success {
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid #10b981;
    }
    .flash-error {
        background: rgba(239, 68, 68, 0.2);
        border: 1px solid #ef4444;
    }
    .main-layout {
        display: grid;
        grid-template-columns: 250px 1fr 300px;
        gap: 2rem;
        padding: 2rem 0;
    }
    @media (max-width: 992px) {
        .main-layout {
            grid-template-columns: 1fr;
        }
    }
    .card {
        background: var(--card-bg);
        border: 2px solid rgba(124, 58, 237, 0.3);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(10px);
    }
    .user-avatar {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 1.2rem;
        border: 2px solid var(--purple-light);
    }
    .post-editor {
        width: 100%;
        min-height: 100px;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border: 2px solid rgba(124, 58, 237, 0.3);
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
        resize: vertical;
    }
    .btn {
        padding: 0.8rem 2rem;
        background: var(--gradient);
        border: none;
        border-radius: 10px;
        color: white;
        font-weight: 600;
        cursor: pointer;
        transition: 0.3s;
    }
    .btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(191, 0, 255, 0.3);
    }
    .nav-icon {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(124, 58, 237, 0.1);
        border: 2px solid rgba(124, 58, 237, 0.3);
        border-radius: 50%;
        color: #a855f7;
        text-decoration: none;
        transition: 0.3s;
    }
    .nav-icon:hover {
        background: rgba(124, 58, 237, 0.2);
        transform: translateY(-3px);
    }
    .badge {
        position: absolute;
        top: -5px;
        right: -5px;
        background: var(--gradient);
        color: white;
        font-size: 0.7rem;
        font-weight: bold;
        min-width: 18px;
        height: 18px;
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
</style>
'''

LOGIN_HTML = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌌 Netta | Вход в метавселенную</title>
    {BASE_STYLE}
</head>
<body>
    <div class="auth-container">
        <div class="auth-card">
            <div style="text-align: center; margin-bottom: 2rem;">
                <div class="logo" style="justify-content: center;">
                    <div class="logo-icon">N</div>
                    <div style="font-size: 2rem; font-weight: 900; background: linear-gradient(45deg, #a855f7, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">etta</div>
                </div>
            </div>
            
            <h1 class="auth-title">ВОЙТИ В МЕТАВСЕЛЕННУЮ</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST" action="/login">
                <div class="form-group">
                    <input type="text" name="username" class="form-control" required placeholder="👤 Имя пользователя или Email">
                </div>
                
                <div class="form-group">
                    <input type="password" name="password" class="form-control" required placeholder="🔒 Пароль">
                </div>
                
                <button type="submit" class="btn-primary">
                    🚀 ПРОДОЛЖИТЬ ПУТЕШЕСТВИЕ
                </button>
            </form>
            
            <div class="auth-links">
                Еще нет аккаунта? <a href="/register" class="auth-link">✨ СОЗДАТЬ АККАУНТ</a>
            </div>
        </div>
    </div>
</body>
</html>'''

REGISTER_HTML = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌌 Netta | Стать частью вселенной</title>
    {BASE_STYLE}
</head>
<body>
    <div class="auth-container">
        <div class="auth-card">
            <div style="text-align: center; margin-bottom: 2rem;">
                <div class="logo" style="justify-content: center;">
                    <div class="logo-icon">N</div>
                    <div style="font-size: 2rem; font-weight: 900; background: linear-gradient(45deg, #a855f7, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">etta</div>
                </div>
            </div>
            
            <h1 class="auth-title">СТАТЬ ЧАСТЬЮ ВСЕЛЕННОЙ</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST" action="/register">
                <div class="form-group">
                    <input type="text" name="username" class="form-control" required placeholder="👤 Имя пользователя">
                </div>
                
                <div class="form-group">
                    <input type="email" name="email" class="form-control" required placeholder="📧 Email адрес">
                </div>
                
                <div class="form-group">
                    <input type="password" name="password" class="form-control" required placeholder="🔒 Пароль">
                </div>
                
                <div class="form-group">
                    <input type="password" name="confirm_password" class="form-control" required placeholder="🔁 Подтвердите пароль">
                </div>
                
                <div class="form-group">
                    <input type="text" name="full_name" class="form-control" placeholder="🌟 Ваше имя (необязательно)">
                </div>
                
                <button type="submit" class="btn-primary">
                    🪐 СОЗДАТЬ ПРОСТРАНСТВО
                </button>
            </form>
            
            <div class="auth-links">
                Уже есть аккаунт? <a href="/login" class="auth-link">← ВЕРНУТЬСЯ К ВХОДУ</a>
            </div>
        </div>
    </div>
</body>
</html>'''

# ============ МАРШРУТЫ ============
@app.route('/')
def index():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        # Получаем посты
        posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
        
        # Получаем лайки пользователя
        liked_posts = [like.post_id for like in current_user.user_likes]
        
        # Генерируем HTML для постов
        posts_html = ''
        for post in posts:
            is_liked = post.id in liked_posts
            posts_html += f'''
            <div class="card" style="transition: 0.3s;" onmouseover="this.style.borderColor='var(--purple-neon)';" onmouseout="this.style.borderColor='rgba(124, 58, 237, 0.3)';">
                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                    <div class="user-avatar" style="background: {post.author.avatar_color}; margin-right: 1rem;">
                        {post.author.username[0].upper()}
                    </div>
                    <div>
                        <div style="font-weight: bold; display: flex; align-items: center; gap: 0.5rem;">
                            {post.author.full_name or post.author.username}
                            <span style="background: var(--gradient); color: white; padding: 0.2rem 0.6rem; border-radius: 10px; font-size: 0.8rem;">
                                Ур. {post.author.level}
                            </span>
                        </div>
                        <div style="color: #9ca3af; font-size: 0.9rem;">
                            {post.created_at.strftime('%d %b в %H:%M')}
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 1rem; line-height: 1.6;">
                    {post.content}
                </div>
                
                <div style="display: flex; gap: 2rem; color: #9ca3af;">
                    <form method="POST" action="/like/{post.id}" style="display: inline;">
                        <button type="submit" style="background: none; border: none; color: {'var(--purple-neon)' if is_liked else 'inherit'}; cursor: pointer; display: flex; align-items: center; gap: 0.5rem;">
                            <i class="fas fa-heart"></i> {post.likes_count}
                        </button>
                    </form>
                    <span style="display: flex; align-items: center; gap: 0.5rem;">
                        <i class="fas fa-comment"></i> {post.comments_count}
                    </span>
                </div>
            </div>
            '''
        
        # Возвращаем полную HTML страницу
        return f'''
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>🌌 Netta | Космическая лента</title>
            {BASE_STYLE}
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        </head>
        <body>
            <!-- ШАПКА -->
            <header class="header">
                <div class="container">
                    <nav class="navbar">
                        <a href="/" class="logo">
                            <div class="logo-icon">N</div>
                            <div style="font-size: 1.5rem; font-weight: 900; background: linear-gradient(45deg, #a855f7, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">etta</div>
                        </a>
                        
                        <div style="display: flex; gap: 1rem; align-items: center;">
                            <a href="#" class="nav-icon" title="Уведомления" style="position: relative;">
                                <i class="fas fa-bell"></i>
                                <span class="badge">3</span>
                            </a>
                            
                            <a href="#" class="nav-icon" title="Сообщения" style="position: relative;">
                                <i class="fas fa-comments"></i>
                                <span class="badge">5</span>
                            </a>
                            
                            <a href="/logout" class="nav-icon" title="Выйти">
                                <i class="fas fa-sign-out-alt"></i>
                            </a>
                        </div>
                    </nav>
                </div>
            </header>
            
            <!-- ОСНОВНОЙ КОНТЕНТ -->
            <main class="container">
                <div class="main-layout">
                    <!-- ЛЕВЫЙ САЙДБАР -->
                    <aside>
                        <div class="card">
                            <div style="text-align: center;">
                                <div class="user-avatar" style="margin: 0 auto 1rem; background: {current_user.avatar_color}; width: 80px; height: 80px; font-size: 2rem;">
                                    {current_user.username[0].upper()}
                                </div>
                                <h3 style="margin-bottom: 0.5rem;">{current_user.full_name or current_user.username}</h3>
                                <p style="color: var(--purple-light); margin-bottom: 1rem;">@{current_user.username}</p>
                                
                                <div style="display: flex; justify-content: center; gap: 1rem; margin-bottom: 1rem;">
                                    <div style="text-align: center;">
                                        <div style="font-size: 1.2rem; font-weight: bold;">{current_user.posts_count}</div>
                                        <div style="font-size: 0.8rem; color: #9ca3af;">Постов</div>
                                    </div>
                                    <div style="text-align: center;">
                                        <div style="font-size: 1.2rem; font-weight: bold;">{current_user.friends_count}</div>
                                        <div style="font-size: 0.8rem; color: #9ca3af;">Друзей</div>
                                    </div>
                                    <div style="text-align: center;">
                                        <div style="font-size: 1.2rem; font-weight: bold;">{current_user.level}</div>
                                        <div style="font-size: 0.8rem; color: #9ca3af;">Уровень</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <h3 style="margin-bottom: 1rem; color: var(--purple-light);">
                                <i class="fas fa-rocket"></i> Навигация
                            </h3>
                            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                <a href="#" style="color: white; text-decoration: none; padding: 0.8rem; border-radius: 10px; transition: 0.3s;" onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" onmouseout="this.style.background='transparent';">
                                    <i class="fas fa-compass"></i> Исследовать
                                </a>
                                <a href="#" style="color: white; text-decoration: none; padding: 0.8rem; border-radius: 10px; transition: 0.3s;" onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" onmouseout="this.style.background='transparent';">
                                    <i class="fas fa-users"></i> Сообщества
                                </a>
                                <a href="#" style="color: white; text-decoration: none; padding: 0.8rem; border-radius: 10px; transition: 0.3s;" onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" onmouseout="this.style.background='transparent';">
                                    <i class="fas fa-gamepad"></i> Игры
                                </a>
                                <a href="#" style="color: white; text-decoration: none; padding: 0.8rem; border-radius: 10px; transition: 0.3s;" onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" onmouseout="this.style.background='transparent';">
                                    <i class="fas fa-cog"></i> Настройки
                                </a>
                            </div>
                        </div>
                    </aside>
                    
                    <!-- ЦЕНТРАЛЬНАЯ ЛЕНТА -->
                    <section>
                        <!-- СОЗДАНИЕ ПОСТА -->
                        <div class="card">
                            <form method="POST" action="/create_post">
                                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                                    <div class="user-avatar" style="background: {current_user.avatar_color}; margin-right: 1rem;">
                                        {current_user.username[0].upper()}
                                    </div>
                                    <div>
                                        <div style="font-weight: bold;">{current_user.full_name or current_user.username}</div>
                                        <select style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(124, 58, 237, 0.3); color: white; padding: 0.3rem; border-radius: 5px; font-size: 0.8rem;">
                                            <option>🌍 Публичный</option>
                                            <option>👥 Только друзья</option>
                                            <option>🔒 Только я</option>
                                        </select>
                                    </div>
                                </div>
                                
                                <textarea name="content" class="post-editor" placeholder="🌌 Что происходит в вашей вселенной, {current_user.username}?"></textarea>
                                
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div style="display: flex; gap: 1rem;">
                                        <button type="button" style="background: none; border: none; color: #a855f7; font-size: 1.2rem; cursor: pointer;" title="Добавить фото">
                                            <i class="fas fa-image"></i>
                                        </button>
                                        <button type="button" style="background: none; border: none; color: #a855f7; font-size: 1.2rem; cursor: pointer;" title="Добавить видео">
                                            <i class="fas fa-video"></i>
                                        </button>
                                        <button type="button" style="background: none; border: none; color: #a855f7; font-size: 1.2rem; cursor: pointer;" title="Добавить эмоцию">
                                            <i class="fas fa-smile"></i>
                                        </button>
                                    </div>
                                    <button type="submit" class="btn">
                                        <i class="fas fa-paper-plane"></i> Опубликовать
                                    </button>
                                </div>
                            </form>
                        </div>
                        
                        <!-- ПОСТЫ -->
                        {posts_html}
                    </section>
                    
                    <!-- ПРАВАЯ КОЛОНКА -->
                    <aside>
                        <!-- ОНЛАЙН ДРУЗЬЯ -->
                        <div class="card">
                            <h3 style="margin-bottom: 1rem; color: var(--purple-light);">
                                <i class="fas fa-satellite"></i> В сети сейчас
                            </h3>
                            <div style="display: flex; flex-direction: column; gap: 0.8rem;">
                                <div style="display: flex; align-items: center; gap: 0.8rem; padding: 0.5rem; border-radius: 10px; transition: 0.3s;" onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" onmouseout="this.style.background='transparent';">
                                    <div class="user-avatar" style="background: #a855f7; width: 40px; height: 40px; border: 2px solid #10b981;">
                                        C
                                    </div>
                                    <div>
                                        <div style="font-weight: bold;">Космонавт</div>
                                        <div style="font-size: 0.8rem; color: #10b981;">
                                            <i class="fas fa-circle" style="font-size: 0.6rem;"></i> Онлайн
                                        </div>
                                    </div>
                                </div>
                                <div style="display: flex; align-items: center; gap: 0.8rem; padding: 0.5rem; border-radius: 10px; transition: 0.3s;" onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';" onmouseout="this.style.background='transparent';">
                                    <div class="user-avatar" style="background: #7c3aed; width: 40px; height: 40px; border: 2px solid #10b981;">
                                        З
                                    </div>
                                    <div>
                                        <div style="font-weight: bold;">Звездочёт</div>
                                        <div style="font-size: 0.8rem; color: #10b981;">
                                            <i class="fas fa-circle" style="font-size: 0.6rem;"></i> Онлайн
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- ТРЕНДЫ -->
                        <div class="card">
                            <h3 style="margin-bottom: 1rem; color: var(--purple-light);">
                                <i class="fas fa-fire"></i> Тренды вселенной
                            </h3>
                            <div style="display: flex; flex-direction: column; gap: 0.8rem;">
                                <div style="padding: 0.8rem; background: rgba(255, 255, 255, 0.03); border-radius: 10px; transition: 0.3s;" onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';">
                                    <div style="font-weight: bold; color: var(--purple-light);">#NettaLaunch</div>
                                    <div style="font-size: 0.9rem; color: #9ca3af;">1.2K постов</div>
                                </div>
                                <div style="padding: 0.8rem; background: rgba(255, 255, 255, 0.03); border-radius: 10px; transition: 0.3s;" onmouseover="this.style.background='rgba(124, 58, 237, 0.1)';">
                                    <div style="font-weight: bold; color: var(--purple-light);">#ФиолетоваяВселенная</div>
                                    <div style="font-size: 0.9rem; color: #9ca3af;">856 постов</div>
                                </div>
                            </div>
                        </div>
                    </aside>
                </div>
            </main>
            
            <!-- ФУТЕР -->
            <footer style="text-align: center; padding: 2rem; color: rgba(255, 255, 255, 0.5); border-top: 1px solid rgba(124, 58, 237, 0.2);">
                <div style="max-width: 1200px; margin: 0 auto;">
                    <div style="margin-bottom: 1rem;">
                        <span style="color: var(--purple-light); font-weight: bold;">Netta</span> 
                        — Социальная сеть нового поколения 🌌
                    </div>
                    <div style="font-size: 0.9rem;">
                        © 2026 Netta Universe. Все права защищены.
                    </div>
                </div>
            </footer>
            
            <script>
                // Анимация лайков
                document.addEventListener('DOMContentLoaded', function() {{
                    document.querySelectorAll('form[action^="/like/"] button').forEach(button => {{
                        button.addEventListener('click', function(e) {{
                            setTimeout(() => {{
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
                                
                                heart.animate([
                                    {{ transform: 'translateY(0) scale(1)', opacity: 1 }},
                                    {{ transform: 'translateY(-100px) scale(1.5)', opacity: 0 }}
                                ], {{
                                    duration: 800,
                                    easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
                                }}).onfinish = () => heart.remove();
                            }}, 100);
                        }});
                    }});
                }});
            </script>
        </body>
        </html>
        '''
    
    return LOGIN_HTML

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user and user.check_password(password):
            user.last_seen = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash('Добро пожаловать в метавселенную Netta! 🌌', 'success')
            return redirect('/')
        else:
            flash('Неверные данные. Попробуйте снова.', 'error')
    
    return LOGIN_HTML

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '')
        
        # Валидация
        if not username or not email or not password:
            flash('Заполните все обязательные поля', 'error')
            return REGISTER_HTML
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return REGISTER_HTML
        
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято', 'error')
            return REGISTER_HTML
        
        if User.query.filter_by(email=email).first():
            flash('Этот email уже используется', 'error')
            return REGISTER_HTML
        
        if len(password) < 6:
            flash('Пароль должен быть минимум 6 символов', 'error')
            return REGISTER_HTML
        
        # Создание пользователя
        colors = ['#7c3aed', '#a855f7', '#bf00ff', '#5b21b6', '#8b5cf6']
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            avatar_color=random.choice(colors)
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Ваше пространство создано! Добро пожаловать в Netta! 🚀', 'success')
            return redirect('/login')
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при создании аккаунта. Попробуйте снова.', 'error')
    
    return REGISTER_HTML

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы покинули вселенную Netta. Возвращайтесь скорее! 👋', 'success')
    return redirect('/login')

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content', '')
    
    if content.strip():
        post = Post(
            content=content,
            user_id=current_user.id
        )
        current_user.posts_count += 1
        
        try:
            db.session.add(post)
            db.session.commit()
            flash('Ваш пост запущен в космос! 🌠', 'success')
        except:
            db.session.rollback()
            flash('Ошибка при публикации поста', 'error')
    
    return redirect('/')

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get(post_id)
    
    if post:
        # Проверяем, не лайкал ли уже
        existing_like = Like.query.filter_by(
            user_id=current_user.id,
            post_id=post_id
        ).first()
        
        if existing_like:
            # Удаляем лайк
            db.session.delete(existing_like)
            post.likes_count = max(0, post.likes_count - 1)
        else:
            # Добавляем лайк
            like = Like(user_id=current_user.id, post_id=post_id)
            db.session.add(like)
            post.likes_count += 1
        
        try:
            db.session.commit()
        except:
            db.session.rollback()
    
    return redirect('/')

@app.errorhandler(404)
def not_found(error):
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Netta</title>
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
                font-family: 'Segoe UI', sans-serif;
            }
            h1 {
                font-size: 8rem;
                margin: 0;
                background: linear-gradient(45deg, #7c3aed, #bf00ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
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
            }
        </style>
    </head>
    <body>
        <div>
            <h1>404</h1>
            <h2>Потерялись в космосе</h2>
            <p>Эта планета еще не открыта</p>
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
            colors = ['#7c3aed', '#a855f7', '#bf00ff', '#5b21b6']
            
            test_users = [
                ('admin', 'admin@netta.com', 'admin123', 'Администратор Вселенной'),
                ('cosmos', 'cosmos@netta.com', 'cosmos123', 'Космический Путешественник'),
                ('nebula', 'nebula@netta.com', 'nebula123', 'Туманность Андромеды'),
                ('stardust', 'stardust@netta.com', 'stardust123', 'Звездная Пыль')
            ]
            
            for i, (username, email, password, full_name) in enumerate(test_users):
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    avatar_color=colors[i % len(colors)],
                    level=random.randint(2, 10),
                    coins=random.randint(100, 1000)
                )
                user.set_password(password)
                db.session.add(user)
            
            # Создаем тестовые посты
            post_contents = [
                'Привет всем! Это новая социальная сеть Netta! 🌌',
                'Кто уже успел исследовать новые функции? 🚀',
                'Фиолетовый - цвет бесконечности и тайн вселенной! 🟣',
                'Сегодня достиг нового уровня в системе прокачки! 🎉',
                'Объявляю конкурс на лучший космический пост!',
                'Создал сообщество для исследователей космоса. Присоединяйтесь!',
                'Новый дизайн просто космический! Крутые анимации!',
                'Купил премиум статус за монеты. Очень круто! 💜',
                'Кто хочет вместе пройти квест на новой планете?',
                'Заметил баг? Пишите в поддержку! Мы все исправим!'
            ]
            
            users = User.query.all()
            for i, content in enumerate(post_contents):
                author = users[i % len(users)]
                post = Post(
                    content=content,
                    user_id=author.id,
                    likes_count=random.randint(5, 50),
                    comments_count=random.randint(0, 20),
                    created_at=datetime.utcnow()
                )
                db.session.add(post)
                author.posts_count += 1
            
            db.session.commit()
            print("✅ Netta успешно запущена!")
            print("👤 Тестовые пользователи созданы:")
            for user in User.query.all():
                print(f"   {user.username} / {user.email} / пароль из списка выше")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)           self.coins += 50
        return self.level

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    shares_count = db.Column(db.Integer, default=0)
    views_count = db.Column(db.Integer, default=0)
    media_type = db.Column(db.String(20))
    media_url = db.Column(db.String(500))
    poll_data = db.Column(db.Text)
    privacy = db.Column(db.String(20), default='public')
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author = db.relationship('User', backref='user_posts')

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    likes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', backref='user_comments')

class Friendship(db.Model):
    __tablename__ = 'friendships'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', foreign_keys=[user_id], backref='sent_friendships')
    friend = db.relationship('User', foreign_keys=[friend_id], backref='received_friendships')

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50))
    content = db.Column(db.Text)
    reference_id = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='user_notifications')

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='user_likes')
    post = db.relationship('Post', backref='post_likes')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

LOGIN_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netta | Вход</title>
    <style>
        :root {
            --purple-neon: #bf00ff;
            --purple-deep: #7c3aed;
            --purple-light: #a855f7;
            --purple-dark: #5b21b6;
            --space-bg: #0a0a1a;
            --card-bg: rgba(20, 15, 40, 0.9);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: var(--space-bg);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }
        .auth-card {
            background: var(--card-bg);
            border: 2px solid #7c3aed;
            border-radius: 20px;
            padding: 3rem;
            width: 100%;
            max-width: 500px;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 2rem;
            justify-content: center;
        }
        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #7c3aed, #bf00ff);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 900;
            color: white;
        }
        .auth-title {
            text-align: center;
            margin-bottom: 2rem;
            font-size: 1.8rem;
            background: linear-gradient(45deg, #7c3aed, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        .form-control {
            width: 100%;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 10px;
            color: white;
            font-size: 1rem;
        }
        .btn-primary {
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #7c3aed, #5b21b6);
            border: none;
            border-radius: 10px;
            color: white;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
        }
        .auth-switch {
            text-align: center;
            margin-top: 2rem;
            color: #d1d5db;
        }
        .auth-link {
            color: #a855f7;
            text-decoration: none;
        }
        .flash-message {
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 10px;
            text-align: center;
        }
        .flash-success {
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid #10b981;
        }
        .flash-error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
        }
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="logo">
            <div class="logo-icon">N</div>
            <span>Netta</span>
        </div>
        
        <h1 class="auth-title">ВОЙТИ В NETTA</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-message flash-{{ category }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" action="/login">
            <div class="form-group">
                <input type="text" name="username" class="form-control" required placeholder="👤 Имя пользователя или Email">
            </div>
            
            <div class="form-group">
                <input type="password" name="password" class="form-control" required placeholder="🔒 Пароль">
            </div>
            
            <button type="submit" class="btn-primary">🚀 ВОЙТИ</button>
        </form>
        
        <div class="auth-switch">
            Нет аккаунта? <a href="/register" class="auth-link">Создать</a>
        </div>
    </div>
</body>
</html>'''

REGISTER_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netta | Регистрация</title>
    <style>
        :root {
            --purple-neon: #bf00ff;
            --purple-deep: #7c3aed;
            --purple-light: #a855f7;
            --purple-dark: #5b21b6;
            --space-bg: #0a0a1a;
            --card-bg: rgba(20, 15, 40, 0.9);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: var(--space-bg);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }
        .auth-card {
            background: var(--card-bg);
            border: 2px solid #7c3aed;
            border-radius: 20px;
            padding: 3rem;
            width: 100%;
            max-width: 500px;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 2rem;
            justify-content: center;
        }
        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #7c3aed, #bf00ff);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 900;
            color: white;
        }
        .auth-title {
            text-align: center;
            margin-bottom: 2rem;
            font-size: 1.8rem;
            background: linear-gradient(45deg, #7c3aed, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        .form-control {
            width: 100%;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-radius: 10px;
            color: white;
            font-size: 1rem;
        }
        .btn-primary {
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #7c3aed, #5b21b6);
            border: none;
            border-radius: 10px;
            color: white;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
        }
        .auth-switch {
            text-align: center;
            margin-top: 2rem;
            color: #d1d5db;
        }
        .auth-link {
            color: #a855f7;
            text-decoration: none;
        }
        .flash-message {
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 10px;
            text-align: center;
        }
        .flash-success {
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid #10b981;
        }
        .flash-error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
        }
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="logo">
            <div class="logo-icon">N</div>
            <span>Netta</span>
        </div>
        
        <h1 class="auth-title">СОЗДАТЬ АККАУНТ</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-message flash-{{ category }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" action="/register">
            <div class="form-group">
                <input type="text" name="username" class="form-control" required placeholder="👤 Имя пользователя">
            </div>
            
            <div class="form-group">
                <input type="email" name="email" class="form-control" required placeholder="📧 Email адрес">
            </div>
            
            <div class="form-group">
                <input type="password" name="password" class="form-control" required placeholder="🔒 Пароль">
            </div>
            
            <div class="form-group">
                <input type="password" name="confirm_password" class="form-control" required placeholder="🔁 Подтвердите пароль">
            </div>
            
            <div class="form-group">
                <input type="text" name="full_name" class="form-control" placeholder="🌟 Ваше имя (необязательно)">
            </div>
            
            <button type="submit" class="btn-primary">🚀 СОЗДАТЬ АККАУНТ</button>
        </form>
        
        <div class="auth-switch">
            Уже есть аккаунт? <a href="/login" class="auth-link">Войти</a>
        </div>
    </div>
</body>
</html>'''

@app.route('/')
def index():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
        liked_posts = [like.post_id for like in current_user.user_likes]
        
        return render_template_string('''
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Netta | Главная</title>
            <style>
                :root {
                    --purple-neon: #bf00ff;
                    --purple-deep: #7c3aed;
                    --purple-light: #a855f7;
                    --purple-dark: #5b21b6;
                    --space-bg: #0a0a1a;
                    --card-bg: rgba(20, 15, 40, 0.9);
                }
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Segoe UI', sans-serif;
                    background: var(--space-bg);
                    color: white;
                }
                .header {
                    background: rgba(10, 5, 25, 0.95);
                    border-bottom: 2px solid #7c3aed;
                    padding: 1rem 0;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 0 1rem;
                }
                .navbar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .logo {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-size: 1.5rem;
                    font-weight: 800;
                    color: white;
                    text-decoration: none;
                }
                .logo-icon {
                    width: 40px;
                    height: 40px;
                    background: linear-gradient(135deg, #7c3aed, #bf00ff);
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.5rem;
                    font-weight: 900;
                    color: white;
                }
                .main-layout {
                    display: grid;
                    grid-template-columns: 250px 1fr 300px;
                    gap: 2rem;
                    padding: 2rem 0;
                }
                .card {
                    background: var(--card-bg);
                    border: 2px solid rgba(124, 58, 237, 0.3);
                    border-radius: 15px;
                    padding: 1.5rem;
                    margin-bottom: 1.5rem;
                }
                .post-editor {
                    width: 100%;
                    min-height: 100px;
                    padding: 1rem;
                    background: rgba(255, 255, 255, 0.05);
                    border: 2px solid rgba(124, 58, 237, 0.3);
                    border-radius: 10px;
                    color: white;
                    margin-bottom: 1rem;
                }
                .btn {
                    padding: 0.8rem 2rem;
                    background: linear-gradient(135deg, #7c3aed, #5b21b6);
                    border: none;
                    border-radius: 10px;
                    color: white;
                    font-weight: 600;
                    cursor: pointer;
                }
                .user-avatar {
                    width: 50px;
                    height: 50px;
                    border-radius: 50%;
                    background: ''' + current_user.avatar_color + ''';
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 1.2rem;
                }
            </style>
        </head>
        <body>
            <header class="header">
                <div class="container">
                    <nav class="navbar">
                        <a href="/" class="logo">
                            <div class="logo-icon">N</div>
                            <span>Netta</span>
                        </a>
                        <div>
                            <a href="/logout" style="color: #a855f7; text-decoration: none;">Выйти</a>
                        </div>
                    </nav>
                </div>
            </header>
            
            <main class="container">
                <div class="main-layout">
                    <aside>
                        <div class="card">
                            <div style="text-align: center;">
                                <div class="user-avatar" style="margin: 0 auto 1rem;">
                                    ''' + current_user.username[0].upper() + '''
                                </div>
                                <h3>''' + (current_user.full_name or current_user.username) + '''</h3>
                                <p style="color: #a855f7;">@''' + current_user.username + '''</p>
                                <p>Уровень: ''' + str(current_user.level) + '''</p>
                                <p>Монеты: ''' + str(current_user.coins) + '''</p>
                            </div>
                        </div>
                    </aside>
                    
                    <section>
                        <div class="card">
                            <form method="POST" action="/create_post">
                                <textarea name="content" class="post-editor" placeholder="Что нового?"></textarea>
                                <button type="submit" class="btn">Опубликовать</button>
                            </form>
                        </div>
                        
                        ''' + ''.join([f'''
                        <div class="card">
                            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                                <div class="user-avatar" style="background: {post.author.avatar_color}; margin-right: 1rem;">
                                    {post.author.username[0].upper()}
                                </div>
                                <div>
                                    <div style="font-weight: bold;">{post.author.full_name or post.author.username}</div>
                                    <div style="color: #9ca3af; font-size: 0.9rem;">
                                        {post.created_at.strftime('%d %b в %H:%M')}
                                    </div>
                                </div>
                            </div>
                            <div style="margin-bottom: 1rem;">
                                {post.content}
                            </div>
                            <div>
                                <form method="POST" action="/like/{post.id}" style="display: inline;">
                                    <button type="submit" style="background: none; border: none; color: {'#bf00ff' if post.id in liked_posts else 'white'}; cursor: pointer;">
                                        ❤️ {post.likes_count}
                                    </button>
                                </form>
                                <span style="margin-left: 1rem;">💬 {post.comments_count}</span>
                            </div>
                        </div>
                        ''' for post in posts]) + '''
                    </section>
                    
                    <aside>
                        <div class="card">
                            <h3>Онлайн сейчас</h3>
                            <p>Друзья в сети скоро здесь</p>
                        </div>
                        <div class="card">
                            <h3>Тренды</h3>
                            <p>#NettaLaunch</p>
                            <p>#ФиолетоваяВселенная</p>
                        </div>
                    </aside>
                </div>
            </main>
        </body>
        </html>
        ''')
    
    return LOGIN_HTML

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user and user.check_password(password):
            user.last_seen = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash('Добро пожаловать в Netta!', 'success')
            return redirect('/')
        else:
            flash('Неверный логин или пароль', 'error')
    
    return LOGIN_HTML

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form.get('full_name', '')
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return REGISTER_HTML
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'error')
            return REGISTER_HTML
        
        if User.query.filter_by(email=email).first():
            flash('Email уже используется', 'error')
            return REGISTER_HTML
        
        colors = ['#7c3aed', '#a855f7', '#bf00ff', '#5b21b6', '#8b5cf6']
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            avatar_color=random.choice(colors),
            cover_color=random.choice(colors)
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Аккаунт создан! Войдите в систему', 'success')
        return redirect('/login')
    
    return REGISTER_HTML

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'success')
    return redirect('/login')

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content', '')
    if content.strip():
        post = Post(
            content=content,
            user_id=current_user.id
        )
        current_user.posts_count += 1
        db.session.add(post)
        db.session.commit()
        flash('Пост опубликован!', 'success')
    
    return redirect('/')

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get(post_id)
    if post:
        existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        
        if existing_like:
            db.session.delete(existing_like)
            post.likes_count = max(0, post.likes_count - 1)
        else:
            like = Like(user_id=current_user.id, post_id=post_id)
            db.session.add(like)
            post.likes_count += 1
            current_user.add_xp(5)
        
        db.session.commit()
    
    return redirect('/')

@app.errorhandler(404)
def not_found(error):
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Netta</title>
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
            }
        </style>
    </head>
    <body>
        <div>
            <h1>404</h1>
            <p>Страница не найдена</p>
            <a href="/" style="color: #a855f7;">На главную</a>
        </div>
    </body>
    </html>
    ''', 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        if not User.query.first():
            users = [
                {'username': 'admin', 'email': 'admin@netta.com', 'password': 'admin123', 'full_name': 'Админ'},
                {'username': 'user1', 'email': 'user1@netta.com', 'password': 'user1123', 'full_name': 'Пользователь 1'},
                {'username': 'user2', 'email': 'user2@netta.com', 'password': 'user2123', 'full_name': 'Пользователь 2'}
            ]
            
            colors = ['#7c3aed', '#a855f7', '#bf00ff']
            
            for i, user_data in enumerate(users):
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    full_name=user_data['full_name'],
                    avatar_color=colors[i % len(colors)],
                    cover_color=colors[(i + 1) % len(colors)],
                    level=random.randint(1, 5),
                    coins=random.randint(100, 500)
                )
                user.set_password(user_data['password'])
                db.session.add(user)
            
            db.session.commit()
            print("База данных создана!")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
