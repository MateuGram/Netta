from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from functools import wraps
import json

# ============ ИНИЦИАЛИЗАЦИЯ ============
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Конфигурация
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'netta-super-secret-key-2026-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///netta.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

# Создаем необходимые директории
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему'

# ============ МОДЕЛИ БАЗЫ ДАННЫХ ============

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    profile_pic = db.Column(db.String(200), default='default-avatar.png')
    cover_pic = db.Column(db.String(200), default='default-cover.jpg')
    location = db.Column(db.String(100))
    website = db.Column(db.String(200))
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    friendships = db.relationship('Friendship', foreign_keys='Friendship.user_id', backref='user', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', backref='user', lazy=True)
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_friends(self):
        friends = []
        for friendship in self.friendships:
            if friendship.status == 'accepted':
                friends.append(friendship.friend)
        return friends

    def get_pending_requests(self):
        return Friendship.query.filter_by(friend_id=self.id, status='pending').all()

    def get_unread_notifications(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'profile_pic': self.profile_pic,
            'bio': self.bio,
            'is_online': (datetime.utcnow() - self.last_seen).seconds < 300  # 5 минут
        }

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    video_url = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    privacy = db.Column(db.String(20), default='public')  # public, friends, private
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    shares_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    # Убрана связь с shares чтобы избежать циклических зависимостей

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    likes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Friendship(db.Model):
    __tablename__ = 'friendships'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    friend = db.relationship('User', foreign_keys=[friend_id])

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50))  # friend_request, like, comment, message, mention
    content = db.Column(db.Text)
    reference_id = db.Column(db.Integer)  # ID связанного объекта
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Убрана модель Share для упрощения

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        return unique_filename
    return None

def create_notification(user_id, type, content, reference_id=None):
    notification = Notification(
        user_id=user_id,
        type=type,
        content=content,
        reference_id=reference_id
    )
    db.session.add(notification)
    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создаем базовые HTML шаблоны
def create_basic_templates():
    # Создаем базовые шаблоны если их нет
    templates = {
        'login.html': '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в Netta</title>
    <style>
        :root {
            --primary-purple: #7c3aed;
            --purple-dark: #5b21b6;
            --purple-light: #8b5cf6;
            --bg-primary: #0f0b1a;
            --bg-card: #1a1525;
            --text-primary: #ffffff;
            --text-secondary: #d1d5db;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background-image: 
                radial-gradient(circle at 20% 80%, rgba(124, 58, 237, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.1) 0%, transparent 40%);
        }
        .auth-card {
            background: var(--bg-card);
            border: 1px solid rgba(124, 58, 237, 0.3);
            border-radius: 20px;
            padding: 3rem;
            width: 100%;
            max-width: 450px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
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
            background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 900;
            color: white;
            box-shadow: 0 0 30px rgba(124, 58, 237, 0.4);
        }
        .auth-title {
            text-align: center;
            margin-bottom: 2rem;
            font-size: 1.8rem;
            background: linear-gradient(45deg, #7c3aed, #8b5cf6);
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
            border: 1px solid rgba(124, 58, 237, 0.3);
            border-radius: 10px;
            color: var(--text-primary);
            font-size: 1rem;
            transition: 0.3s;
        }
        .form-control:focus {
            outline: none;
            border-color: #8b5cf6;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
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
            transition: 0.3s;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(124, 58, 237, 0.3);
        }
        .auth-switch {
            text-align: center;
            margin-top: 2rem;
            color: var(--text-secondary);
        }
        .auth-link {
            color: #8b5cf6;
            text-decoration: none;
            font-weight: 500;
            margin-left: 5px;
        }
        .auth-link:hover {
            text-decoration: underline;
        }
        .flash-message {
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 10px;
            text-align: center;
        }
        .flash-success {
            background: rgba(123, 31, 162, 0.2);
            border: 1px solid #7b1fa2;
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
        
        <h1 class="auth-title">С возвращением!</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-message flash-{{ category }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" action="{{ url_for('login') }}">
            <div class="form-group">
                <input type="text" name="username" class="form-control" required placeholder="Имя пользователя или Email">
            </div>
            
            <div class="form-group">
                <input type="password" name="password" class="form-control" required placeholder="Пароль">
            </div>
            
            <button type="submit" class="btn-primary">Войти в систему</button>
        </form>
        
        <div class="auth-switch">
            Еще нет аккаунта?
            <a href="{{ url_for('register') }}" class="auth-link">Создать новый аккаунт</a>
        </div>
    </div>
</body>
</html>
        ''',
        
        'register.html': '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Регистрация в Netta</title>
    <style>
        :root {
            --primary-purple: #7c3aed;
            --purple-dark: #5b21b6;
            --purple-light: #8b5cf6;
            --bg-primary: #0f0b1a;
            --bg-card: #1a1525;
            --text-primary: #ffffff;
            --text-secondary: #d1d5db;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background-image: 
                radial-gradient(circle at 20% 80%, rgba(124, 58, 237, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.1) 0%, transparent 40%);
        }
        .auth-card {
            background: var(--bg-card);
            border: 1px solid rgba(124, 58, 237, 0.3);
            border-radius: 20px;
            padding: 3rem;
            width: 100%;
            max-width: 450px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
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
            background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 900;
            color: white;
            box-shadow: 0 0 30px rgba(124, 58, 237, 0.4);
        }
        .auth-title {
            text-align: center;
            margin-bottom: 2rem;
            font-size: 1.8rem;
            background: linear-gradient(45deg, #7c3aed, #8b5cf6);
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
            border: 1px solid rgba(124, 58, 237, 0.3);
            border-radius: 10px;
            color: var(--text-primary);
            font-size: 1rem;
            transition: 0.3s;
        }
        .form-control:focus {
            outline: none;
            border-color: #8b5cf6;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
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
            transition: 0.3s;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(124, 58, 237, 0.3);
        }
        .auth-switch {
            text-align: center;
            margin-top: 2rem;
            color: var(--text-secondary);
        }
        .auth-link {
            color: #8b5cf6;
            text-decoration: none;
            font-weight: 500;
            margin-left: 5px;
        }
        .auth-link:hover {
            text-decoration: underline;
        }
        .flash-message {
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 10px;
            text-align: center;
        }
        .flash-success {
            background: rgba(123, 31, 162, 0.2);
            border: 1px solid #7b1fa2;
        }
        .flash-error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="logo">
            <div class="logo-icon">N</div>
            <span>Netta</span>
        </div>
        
        <h1 class="auth-title">Создайте аккаунт</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-message flash-{{ category }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" action="{{ url_for('register') }}">
            <div class="form-group">
                <input type="text" name="username" class="form-control" required placeholder="Имя пользователя">
            </div>
            
            <div class="form-group">
                <input type="email" name="email" class="form-control" required placeholder="Email адрес">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <input type="password" name="password" class="form-control" required placeholder="Пароль">
                </div>
                
                <div class="form-group">
                    <input type="password" name="confirm_password" class="form-control" required placeholder="Подтвердите пароль">
                </div>
            </div>
            
            <div class="form-group">
                <input type="text" name="full_name" class="form-control" placeholder="Полное имя (необязательно)">
            </div>
            
            <button type="submit" class="btn-primary">Создать аккаунт</button>
        </form>
        
        <div class="auth-switch">
            Уже есть аккаунт?
            <a href="{{ url_for('login') }}" class="auth-link">Войти в систему</a>
        </div>
    </div>
</body>
</html>
        ''',
        
        'dashboard.html': '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netta | Главная</title>
    <style>
        :root {
            --primary-purple: #7c3aed;
            --purple-dark: #5b21b6;
            --purple-light: #8b5cf6;
            --bg-primary: #0f0b1a;
            --bg-secondary: #1a1525;
            --bg-card: rgba(26, 21, 37, 0.8);
            --text-primary: #ffffff;
            --text-secondary: #d1d5db;
            --text-muted: #9ca3af;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid rgba(124, 58, 237, 0.2);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 1000;
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
            text-decoration: none;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 900;
            color: white;
            box-shadow: 0 0 20px rgba(124, 58, 237, 0.4);
        }
        .main-container {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            gap: 1.5rem;
            padding: 1.5rem;
            min-height: calc(100vh - 70px);
        }
        .sidebar-card {
            background: var(--bg-card);
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            backdrop-filter: blur(10px);
        }
        .profile-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: 3px solid var(--primary-purple);
            margin-bottom: 1rem;
        }
        .feed {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        .post-card {
            background: var(--bg-card);
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            backdrop-filter: blur(10px);
        }
        .post-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: 2px solid var(--primary-purple);
        }
        .post-user {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }
        .create-post {
            background: var(--bg-card);
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .post-input {
            width: 100%;
            min-height: 100px;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(124, 58, 237, 0.3);
            border-radius: 10px;
            color: var(--text-primary);
            font-size: 1rem;
            margin-bottom: 1rem;
            resize: vertical;
        }
        .post-btn {
            padding: 0.75rem 2rem;
            background: linear-gradient(135deg, #7c3aed, #5b21b6);
            border: none;
            border-radius: 10px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: 0.3s;
        }
        .post-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(124, 58, 237, 0.3);
        }
        .nav-links {
            display: flex;
            gap: 1rem;
            align-items: center;
        }
        .nav-link {
            color: var(--text-secondary);
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 10px;
            transition: 0.3s;
        }
        .nav-link:hover {
            background: rgba(124, 58, 237, 0.1);
            color: var(--purple-light);
        }
        .btn-logout {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 0.5rem 1rem;
            border-radius: 10px;
            cursor: pointer;
            text-decoration: none;
            transition: 0.3s;
        }
        .btn-logout:hover {
            background: rgba(239, 68, 68, 0.2);
        }
        @media (max-width: 1200px) {
            .main-container {
                grid-template-columns: 250px 1fr;
            }
        }
        @media (max-width: 992px) {
            .main-container {
                grid-template-columns: 1fr;
            }
        }
        .welcome-title {
            font-size: 2.5rem;
            background: linear-gradient(45deg, #7c3aed, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        .welcome-card {
            text-align: center;
            padding: 3rem;
            background: var(--bg-card);
            border-radius: 20px;
            border: 1px solid rgba(124, 58, 237, 0.3);
            margin-bottom: 2rem;
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="container">
            <nav class="navbar">
                <a href="{{ url_for('index') }}" class="logo">
                    <div class="logo-icon">N</div>
                    <span>Netta</span>
                </a>
                
                <div class="nav-links">
                    <span style="color: var(--purple-light);">Привет, {{ current_user.username }}!</span>
                    <a href="{{ url_for('logout') }}" class="btn-logout">Выйти</a>
                </div>
            </nav>
        </div>
    </header>

    <main class="main-container">
        <!-- Левый сайдбар -->
        <aside class="sidebar">
            <div class="sidebar-card">
                <div class="user-profile">
                    <img src="https://ui-avatars.com/api/?name={{ current_user.username }}&background=7c3aed&color=fff" 
                         alt="{{ current_user.username }}" 
                         class="profile-avatar">
                    <h3>{{ current_user.full_name or current_user.username }}</h3>
                    <p style="color: var(--text-muted);">@{{ current_user.username }}</p>
                    <p style="margin-top: 1rem;">{{ current_user.bio or 'Добавьте описание в профиле' }}</p>
                </div>
            </div>
        </aside>

        <!-- Центральная лента -->
        <section class="feed">
            <div class="welcome-card">
                <h1 class="welcome-title">Добро пожаловать в Netta!</h1>
                <p style="color: var(--text-secondary); font-size: 1.2rem; max-width: 600px; margin: 0 auto;">
                    Ваша социальная сеть нового поколения с современным фиолетовым дизайном.
                    Здесь вы можете общаться с друзьями, делиться моментами и открывать новое.
                </p>
            </div>

            <div class="create-post">
                <form method="POST" action="{{ url_for('create_post') }}">
                    <textarea name="content" class="post-input" placeholder="Что у вас нового, {{ current_user.username }}?"></textarea>
                    <button type="submit" class="post-btn">Опубликовать</button>
                </form>
            </div>

            {% for post in posts %}
            <div class="post-card">
                <div class="post-user">
                    <img src="https://ui-avatars.com/api/?name={{ post.author.username }}&background=7c3aed&color=fff" 
                         alt="{{ post.author.username }}" 
                         class="post-avatar">
                    <div>
                        <h3>{{ post.author.full_name or post.author.username }}</h3>
                        <span style="color: var(--text-muted); font-size: 0.875rem;">
                            {{ post.created_at.strftime('%d %b %Y в %H:%M') }}
                        </span>
                    </div>
                </div>
                
                <div style="margin-bottom: 1rem;">
                    {{ post.content }}
                </div>
                
                <div style="display: flex; gap: 2rem; color: var(--text-muted);">
                    <form method="POST" action="{{ url_for('like_post', post_id=post.id) }}" style="display: inline;">
                        <button type="submit" style="background: none; border: none; color: var(--purple-light); cursor: pointer;">
                            ❤️ {{ post.likes_count }} лайков
                        </button>
                    </form>
                    <span>💬 {{ post.comments_count }} комментариев</span>
                </div>
            </div>
            {% endfor %}
        </section>

        <!-- Правый сайдбар -->
        <aside class="right-sidebar">
            <div class="sidebar-card">
                <h3 style="margin-bottom: 1rem; color: var(--purple-light);">Статистика</h3>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    <div>Постов: {{ current_user.posts|length }}</div>
                    <div>Друзей: {{ current_user.get_friends()|length }}</div>
                    <div>В сети: {{ online_friends|length }}</div>
                </div>
            </div>
        </aside>
    </main>
</body>
</html>
        '''
    }
    
    for filename, content in templates.items():
        filepath = os.path.join('templates', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

# ============ МАРШРУТЫ ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        # Получаем посты для ленты
        posts = Post.query.filter(
            (Post.privacy == 'public') | 
            (Post.user_id == current_user.id)
        ).order_by(Post.created_at.desc()).limit(20).all()
        
        # Получаем друзей онлайн
        online_friends = [friend for friend in current_user.get_friends() 
                         if (datetime.utcnow() - friend.last_seen).seconds < 300]
        
        return render_template('dashboard.html', 
                             posts=posts, 
                             online_friends=online_friends)
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Проверяем, это email или username
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user and user.check_password(password):
            user.last_seen = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash('Успешный вход в систему!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

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
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email уже используется', 'error')
            return render_template('register.html')
        
        if len(password) < 8:
            flash('Пароль должен содержать минимум 8 символов', 'error')
            return render_template('register.html')
        
        # Создание пользователя
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            profile_pic='default-avatar.png',
            cover_pic='default-cover.jpg'
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Аккаунт успешно создан! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('login'))

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form['content']
    post = Post(
        content=content,
        user_id=current_user.id,
        privacy='public'
    )
    db.session.add(post)
    db.session.commit()
    flash('Пост успешно опубликован!', 'success')
    return redirect(url_for('index'))

@app.route('/like_post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Проверяем, не лайкал ли уже пользователь
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        post.likes_count = max(0, post.likes_count - 1)
        flash('Лайк удален', 'info')
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        post.likes_count += 1
        flash('Пост понравился!', 'success')
    
    db.session.commit()
    return redirect(url_for('index'))

# Статические файлы
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# Обработка 404
@app.errorhandler(404)
def not_found(error):
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Страница не найдена</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #0f0b1a;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                text-align: center;
                background-image: 
                    radial-gradient(circle at 20% 80%, rgba(124, 58, 237, 0.15) 0%, transparent 40%),
                    radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.1) 0%, transparent 40%);
            }
            .error-container {
                max-width: 600px;
                padding: 2rem;
            }
            h1 {
                font-size: 4rem;
                margin: 0;
                background: linear-gradient(45deg, #7c3aed, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            p {
                font-size: 1.2rem;
                color: #d1d5db;
                margin: 1rem 0;
            }
            .btn {
                display: inline-block;
                margin-top: 2rem;
                padding: 1rem 2rem;
                background: linear-gradient(135deg, #7c3aed, #5b21b6);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: 600;
                transition: 0.3s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(124, 58, 237, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="error-container">
            <h1>404</h1>
            <h2>Страница не найдена</h2>
            <p>К сожалению, запрашиваемая страница не существует.</p>
            <a href="/" class="btn">Вернуться на главную</a>
        </div>
    </body>
    </html>
    ''', 404

# Запуск приложения
if __name__ == '__main__':
    # Создаем шаблоны
    create_basic_templates()
    
    with app.app_context():
        db.create_all()
        print("База данных создана!")
        
        # Создаем тестового пользователя, если его нет
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@netta.com',
                full_name='Администратор Netta',
                bio='Основатель социальной сети Netta'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Тестовый пользователь создан: admin / admin123")
        
        if not User.query.filter_by(username='demo').first():
            demo = User(
                username='demo',
                email='demo@netta.com',
                full_name='Демо Пользователь',
                bio='Тестовый аккаунт для демонстрации'
            )
            demo.set_password('demo123')
            db.session.add(demo)
            db.session.commit()
            print("Демо пользователь создан: demo / demo123")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
