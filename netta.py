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
    shares = db.relationship('Share', backref='original_post', lazy=True)

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

class Share(db.Model):
    __tablename__ = 'shares'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    original_post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

# ============ СТИЛИ ============

css_content = '''
/* ============ CSS VARIABLES ============ */
:root {
    /* Фиолетовая цветовая палитра */
    --primary-purple: #7c3aed;
    --purple-dark: #5b21b6;
    --purple-light: #8b5cf6;
    --purple-neon: #a855f7;
    --purple-pastel: #c4b5fd;
    --purple-gradient: linear-gradient(135deg, #7c3aed 0%, #a855f7 50%, #d946ef 100%);
    
    /* Основные цвета */
    --bg-primary: #0f0b1a;
    --bg-secondary: #1a1525;
    --bg-card: rgba(26, 21, 37, 0.8);
    --bg-overlay: rgba(15, 11, 26, 0.9);
    
    /* Текст */
    --text-primary: #ffffff;
    --text-secondary: #d1d5db;
    --text-muted: #9ca3af;
    
    /* Акценты */
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --info: #3b82f6;
    
    /* Эффекты */
    --shadow-sm: 0 1px 2px 0 rgba(124, 58, 237, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(124, 58, 237, 0.1), 0 2px 4px -1px rgba(124, 58, 237, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(124, 58, 237, 0.1), 0 4px 6px -2px rgba(124, 58, 237, 0.05);
    --shadow-xl: 0 20px 25px -5px rgba(124, 58, 237, 0.1), 0 10px 10px -5px rgba(124, 58, 237, 0.04);
    
    /* Границы */
    --border-radius: 16px;
    --border-radius-lg: 24px;
    --border-radius-sm: 8px;
    
    /* Анимации */
    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-normal: 300ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-slow: 500ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ============ БАЗОВЫЕ СТИЛИ ============ */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    overflow-x: hidden;
    min-height: 100vh;
    background-image: 
        radial-gradient(circle at 10% 20%, rgba(124, 58, 237, 0.1) 0%, transparent 20%),
        radial-gradient(circle at 90% 80%, rgba(168, 85, 247, 0.1) 0%, transparent 20%),
        radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.05) 0%, transparent 50%);
}

/* ============ КОНТЕЙНЕРЫ ============ */
.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 1rem;
}

.main-container {
    display: grid;
    grid-template-columns: 280px 1fr 320px;
    gap: 1.5rem;
    padding: 1.5rem;
    min-height: calc(100vh - 70px);
}

/* ============ ШАПКА ============ */
.header {
    position: sticky;
    top: 0;
    z-index: 1000;
    background: var(--bg-secondary);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(124, 58, 237, 0.2);
    padding: 1rem 0;
}

.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
}

.logo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    text-decoration: none;
    font-size: 1.75rem;
    font-weight: 800;
    color: var(--text-primary);
    transition: var(--transition-normal);
}

.logo:hover {
    color: var(--purple-neon);
}

.logo-icon {
    width: 40px;
    height: 40px;
    background: var(--purple-gradient);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 900;
    color: white;
    box-shadow: 0 0 30px rgba(168, 85, 247, 0.4);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% {
        box-shadow: 0 0 20px rgba(168, 85, 247, 0.4);
    }
    50% {
        box-shadow: 0 0 40px rgba(168, 85, 247, 0.8);
    }
}

.search-bar {
    flex: 1;
    max-width: 600px;
    position: relative;
}

.search-input {
    width: 100%;
    padding: 0.875rem 1rem 0.875rem 3rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(124, 58, 237, 0.3);
    border-radius: var(--border-radius);
    color: var(--text-primary);
    font-size: 0.95rem;
    transition: var(--transition-fast);
}

.search-input:focus {
    outline: none;
    border-color: var(--purple-neon);
    box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1);
}

.search-icon {
    position: absolute;
    left: 1rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--purple-pastel);
}

.nav-icons {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.nav-icon {
    position: relative;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 50%;
    color: var(--text-secondary);
    text-decoration: none;
    transition: var(--transition-fast);
}

.nav-icon:hover {
    background: rgba(124, 58, 237, 0.2);
    color: var(--purple-neon);
    transform: translateY(-2px);
}

.nav-icon-badge {
    position: absolute;
    top: -4px;
    right: -4px;
    background: var(--danger);
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
    min-width: 18px;
    height: 18px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 4px;
}

.user-menu {
    position: relative;
}

.user-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--purple-neon);
    cursor: pointer;
    transition: var(--transition-fast);
}

.user-avatar:hover {
    transform: scale(1.05);
    box-shadow: 0 0 20px rgba(168, 85, 247, 0.4);
}

/* ============ САЙДБАР ============ */
.sidebar {
    position: sticky;
    top: 90px;
    height: fit-content;
}

.sidebar-card {
    background: var(--bg-card);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: var(--border-radius-lg);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.sidebar-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.sidebar-nav {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.sidebar-link {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    color: var(--text-secondary);
    text-decoration: none;
    border-radius: var(--border-radius-sm);
    transition: var(--transition-fast);
}

.sidebar-link:hover,
.sidebar-link.active {
    background: rgba(124, 58, 237, 0.1);
    color: var(--purple-neon);
}

.sidebar-link i {
    width: 20px;
    text-align: center;
    font-size: 1.1rem;
}

.sidebar-link-badge {
    margin-left: auto;
    background: var(--purple-neon);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.5rem;
    border-radius: 10px;
}

/* ============ ПОСТЫ ============ */
.feed {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.create-post-card {
    background: var(--bg-card);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: var(--border-radius-lg);
    padding: 1.5rem;
}

.post-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.post-input {
    width: 100%;
    min-height: 100px;
    padding: 1rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: var(--border-radius);
    color: var(--text-primary);
    font-size: 1rem;
    resize: vertical;
    transition: var(--transition-fast);
}

.post-input:focus {
    outline: none;
    border-color: var(--purple-neon);
    box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1);
}

.post-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}

.post-attachments {
    display: flex;
    gap: 0.5rem;
}

.attachment-btn {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(124, 58, 237, 0.1);
    border: none;
    border-radius: 50%;
    color: var(--purple-neon);
    cursor: pointer;
    transition: var(--transition-fast);
}

.attachment-btn:hover {
    background: rgba(124, 58, 237, 0.2);
    transform: translateY(-2px);
}

.post-btn {
    padding: 0.75rem 2rem;
    background: var(--purple-gradient);
    border: none;
    border-radius: var(--border-radius);
    color: white;
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-fast);
}

.post-btn:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
}

/* ============ КАРТОЧКА ПОСТА ============ */
.post-card {
    background: var(--bg-card);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: var(--border-radius-lg);
    overflow: hidden;
    transition: var(--transition-normal);
}

.post-card:hover {
    border-color: rgba(124, 58, 237, 0.4);
    transform: translateY(-4px);
    box-shadow: var(--shadow-xl);
}

.post-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.5rem;
    border-bottom: 1px solid rgba(124, 58, 237, 0.1);
}

.post-user {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.post-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--purple-neon);
}

.post-user-info h3 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
}

.post-user-info span {
    font-size: 0.875rem;
    color: var(--text-muted);
}

.post-time {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--text-muted);
    font-size: 0.875rem;
}

.post-content {
    padding: 1.5rem;
    line-height: 1.7;
}

.post-media {
    margin-top: 1rem;
    border-radius: var(--border-radius);
    overflow: hidden;
}

.post-media img,
.post-media video {
    width: 100%;
    max-height: 500px;
    object-fit: cover;
}

.post-stats {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.5rem;
    border-top: 1px solid rgba(124, 58, 237, 0.1);
    color: var(--text-muted);
    font-size: 0.875rem;
}

.post-actions-bar {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    padding: 0.5rem 1.5rem;
    border-top: 1px solid rgba(124, 58, 237, 0.1);
}

.post-action {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.75rem;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    border-radius: var(--border-radius-sm);
    transition: var(--transition-fast);
}

.post-action:hover {
    background: rgba(124, 58, 237, 0.1);
    color: var(--purple-neon);
}

.post-action.active {
    color: var(--purple-neon);
}

/* ============ ПРАВАЯ КОЛОНКА ============ */
.right-sidebar {
    position: sticky;
    top: 90px;
    height: fit-content;
}

.friends-card,
.trending-card,
.events-card {
    background: var(--bg-card);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: var(--border-radius-lg);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.friends-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.friend-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border-radius: var(--border-radius-sm);
    transition: var(--transition-fast);
}

.friend-item:hover {
    background: rgba(124, 58, 237, 0.1);
}

.friend-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--purple-neon);
}

.friend-info {
    flex: 1;
}

.friend-name {
    font-weight: 600;
    font-size: 0.95rem;
}

.friend-status {
    font-size: 0.75rem;
    color: var(--text-muted);
}

.friend-online {
    color: var(--success);
}

.trending-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.trending-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem;
    border-radius: var(--border-radius-sm);
    transition: var(--transition-fast);
}

.trending-item:hover {
    background: rgba(124, 58, 237, 0.1);
}

.trending-number {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--purple-gradient);
    color: white;
    font-weight: 700;
    font-size: 0.75rem;
    border-radius: 6px;
}

/* ============ ФУТЕР ============ */
.footer {
    margin-top: 3rem;
    padding: 2rem 0;
    border-top: 1px solid rgba(124, 58, 237, 0.2);
    text-align: center;
    color: var(--text-muted);
    font-size: 0.875rem;
}

.footer-links {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-bottom: 1rem;
}

.footer-link {
    color: var(--text-secondary);
    text-decoration: none;
    transition: var(--transition-fast);
}

.footer-link:hover {
    color: var(--purple-neon);
}

/* ============ АВТОРИЗАЦИЯ ============ */
.auth-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    background: var(--bg-primary);
    background-image: 
        radial-gradient(circle at 20% 80%, rgba(124, 58, 237, 0.15) 0%, transparent 40%),
        radial-gradient(circle at 80% 20%, rgba(168, 85, 247, 0.1) 0%, transparent 40%);
}

.auth-card {
    width: 100%;
    max-width: 450px;
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(124, 58, 237, 0.3);
    border-radius: var(--border-radius-lg);
    padding: 3rem;
    box-shadow: var(--shadow-xl);
    position: relative;
    overflow: hidden;
}

.auth-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--purple-gradient);
}

.auth-logo {
    text-align: center;
    margin-bottom: 2rem;
}

.auth-title {
    font-size: 2rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 2rem;
    background: var(--purple-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.form-group {
    margin-bottom: 1.5rem;
}

.form-label {
    display: block;
    margin-bottom: 0.5rem;
    color: var(--text-secondary);
    font-weight: 500;
    font-size: 0.95rem;
}

.form-control {
    width: 100%;
    padding: 0.875rem 1rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(124, 58, 237, 0.3);
    border-radius: var(--border-radius);
    color: var(--text-primary);
    font-size: 1rem;
    transition: var(--transition-fast);
}

.form-control:focus {
    outline: none;
    border-color: var(--purple-neon);
    box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1);
}

.btn-primary {
    width: 100%;
    padding: 1rem;
    background: var(--purple-gradient);
    border: none;
    border-radius: var(--border-radius);
    color: white;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    transition: var(--transition-fast);
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
}

.auth-switch {
    text-align: center;
    margin-top: 2rem;
    color: var(--text-secondary);
}

.auth-link {
    color: var(--purple-neon);
    text-decoration: none;
    font-weight: 500;
    margin-left: 0.5rem;
}

.auth-link:hover {
    text-decoration: underline;
}

/* ============ АДАПТИВНОСТЬ ============ */
@media (max-width: 1200px) {
    .main-container {
        grid-template-columns: 250px 1fr;
    }
    
    .right-sidebar {
        display: none;
    }
}

@media (max-width: 992px) {
    .main-container {
        grid-template-columns: 1fr;
        padding: 1rem;
    }
    
    .sidebar {
        display: none;
    }
    
    .navbar {
        flex-wrap: wrap;
        gap: 1rem;
    }
    
    .search-bar {
        order: 3;
        width: 100%;
        max-width: 100%;
    }
}

@media (max-width: 768px) {
    .auth-card {
        padding: 2rem;
        margin: 1rem;
    }
    
    .post-actions-bar {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 576px) {
    .header {
        padding: 0.75rem 0;
    }
    
    .nav-icons {
        gap: 0.5rem;
    }
    
    .post-header,
    .post-content,
    .post-stats,
    .post-actions-bar {
        padding: 1rem;
    }
    
    .auth-card {
        padding: 1.5rem;
    }
}
'''

js_content = '''
// Основные функции JavaScript для Netta

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация
    initNetta();
    
    // Лайки
    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', handleLike);
    });
    
    // Комментарии
    document.querySelectorAll('.comment-form').forEach(form => {
        form.addEventListener('submit', handleComment);
    });
    
    // Поиск
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // Уведомления
    initNotifications();
    
    // WebSocket для чата (заглушка)
    initChat();
});

// Инициализация приложения
function initNetta() {
    console.log('Netta Social Network запущена!');
    
    // Анимация появления элементов
    animateOnScroll();
    
    // Инициализация tooltips
    initTooltips();
    
    // Загрузка уведомлений
    loadNotifications();
}

// Обработка лайков
function handleLike(event) {
    const button = event.currentTarget;
    const postId = button.dataset.postId;
    const isLiked = button.classList.contains('active');
    
    // Визуальная обратная связь
    button.classList.toggle('active');
    
    // Отправка запроса на сервер
    fetch('/api/like', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            post_id: postId,
            action: isLiked ? 'unlike' : 'like'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Обновление счетчика
            const likeCount = button.querySelector('.like-count');
            if (likeCount) {
                likeCount.textContent = data.likes_count;
            }
            
            // Анимация сердца
            if (!isLiked) {
                animateHeart(button);
            }
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        button.classList.toggle('active'); // Откат
    });
}

// Анимация сердца
function animateHeart(element) {
    const heart = document.createElement('div');
    heart.innerHTML = '❤️';
    heart.style.position = 'absolute';
    heart.style.fontSize = '24px';
    heart.style.pointerEvents = 'none';
    heart.style.zIndex = '1000';
    
    const rect = element.getBoundingClientRect();
    heart.style.left = (rect.left + rect.width / 2 - 12) + 'px';
    heart.style.top = (rect.top - 24) + 'px';
    
    document.body.appendChild(heart);
    
    // Анимация
    const animation = heart.animate([
        { transform: 'translateY(0) scale(1)', opacity: 1 },
        { transform: 'translateY(-50px) scale(1.5)', opacity: 0 }
    ], {
        duration: 800,
        easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
    });
    
    animation.onfinish = () => {
        document.body.removeChild(heart);
    };
}

// Обработка комментариев
function handleComment(event) {
    event.preventDefault();
    
    const form = event.target;
    const postId = form.dataset.postId;
    const content = form.querySelector('textarea').value;
    
    if (!content.trim()) return;
    
    // Отправка комментария
    fetch('/api/comment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            post_id: postId,
            content: content
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Добавление комментария в список
            addCommentToList(data.comment);
            
            // Очистка формы
            form.querySelector('textarea').value = '';
            
            // Обновление счетчика
            const commentCount = form.closest('.post-card').querySelector('.comment-count');
            if (commentCount) {
                commentCount.textContent = data.comments_count;
            }
        }
    });
}

// Добавление комментария в DOM
function addCommentToList(comment) {
    const commentsList = document.querySelector(`.comments-list[data-post-id="${comment.post_id}"]`);
    if (!commentsList) return;
    
    const commentElement = document.createElement('div');
    commentElement.className = 'comment-item';
    commentElement.innerHTML = `
        <div class="comment-avatar">
            <img src="${comment.author.profile_pic}" alt="${comment.author.username}">
        </div>
        <div class="comment-content">
            <div class="comment-header">
                <strong>${comment.author.username}</strong>
                <span class="comment-time">только что</span>
            </div>
            <p>${comment.content}</p>
        </div>
    `;
    
    commentsList.prepend(commentElement);
}

// Поиск
function handleSearch(event) {
    const query = event.target.value.trim();
    
    if (query.length < 2) {
        hideSearchResults();
        return;
    }
    
    // Дебаунсинг
    clearTimeout(window.searchTimeout);
    window.searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 300);
}

function performSearch(query) {
    fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            showSearchResults(data);
        });
}

function showSearchResults(results) {
    // Реализация выпадающего списка с результатами
    console.log('Результаты поиска:', results);
}

function hideSearchResults() {
    // Скрытие результатов поиска
}

// Уведомления
function initNotifications() {
    // Проверка новых уведомлений каждые 30 секунд
    setInterval(checkNewNotifications, 30000);
    
    // Открытие уведомлений
    document.querySelectorAll('.notifications-btn').forEach(btn => {
        btn.addEventListener('click', showNotifications);
    });
}

function loadNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            updateNotificationBadge(data.unread_count);
        });
}

function checkNewNotifications() {
    fetch('/api/notifications/check')
        .then(response => response.json())
        .then(data => {
            if (data.new_notifications > 0) {
                showNotificationToast(data.new_notifications);
                updateNotificationBadge(data.total_unread);
            }
        });
}

function updateNotificationBadge(count) {
    const badges = document.querySelectorAll('.notification-badge');
    badges.forEach(badge => {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    });
}

function showNotificationToast(count) {
    // Показ toast-уведомления
    console.log(`У вас ${count} нов${count === 1 ? 'ое' : 'ых'} уведомлений!`);
}

function showNotifications() {
    // Показ модального окна с уведомлениями
    console.log('Показать уведомления');
}

// Анимация при скролле
function animateOnScroll() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, {
        threshold: 0.1
    });
    
    document.querySelectorAll('.post-card, .friend-item, .trending-item').forEach(el => {
        observer.observe(el);
    });
}

// Tooltips
function initTooltips() {
    const elements = document.querySelectorAll('[data-tooltip]');
    
    elements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const element = event.target;
    const tooltipText = element.dataset.tooltip;
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = tooltipText;
    
    document.body.appendChild(tooltip);
    
    const rect = element.getBoundingClientRect();
    tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
    
    element.tooltip = tooltip;
}

function hideTooltip(event) {
    const element = event.target;
    if (element.tooltip) {
        document.body.removeChild(element.tooltip);
        element.tooltip = null;
    }
}

// Чат (заглушка для WebSocket)
function initChat() {
    // Здесь будет реализация WebSocket для чата
    console.log('Чат инициализирован');
}

// Темная/светлая тема
function toggleTheme() {
    document.body.classList.toggle('light-theme');
    localStorage.setItem('theme', document.body.classList.contains('light-theme') ? 'light' : 'dark');
}

// Проверка предпочтений темы
if (localStorage.getItem('theme') === 'light') {
    document.body.classList.add('light-theme');
}
'''

# HTML шаблоны
login_template = '''
<!DOCTYPE html>
<html lang="ru" class="dark-theme">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в Netta | Социальная сеть нового поколения</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='favicon.ico') }}">
</head>
<body>
    <div class="auth-page">
        <div class="auth-card">
            <div class="auth-logo">
                <div class="logo">
                    <div class="logo-icon">N</div>
                    <span>Netta</span>
                </div>
            </div>
            
            <h1 class="auth-title">С возвращением!</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <div class="flash-messages">
                        {% for category, message in messages %}
                            <div class="flash-message flash-{{ category }}">
                                <i class="fas fa-{% if category == 'success' %}check-circle{% else %}exclamation-circle{% endif %}"></i>
                                {{ message }}
                            </div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}
            
            <form method="POST" action="{{ url_for('login') }}">
                <div class="form-group">
                    <label for="username" class="form-label">
                        <i class="fas fa-user"></i> Имя пользователя или Email
                    </label>
                    <input type="text" id="username" name="username" class="form-control" required placeholder="Введите ваш username или email">
                </div>
                
                <div class="form-group">
                    <label for="password" class="form-label">
                        <i class="fas fa-lock"></i> Пароль
                    </label>
                    <input type="password" id="password" name="password" class="form-control" required placeholder="Введите ваш пароль">
                    <div class="password-toggle" style="text-align: right; margin-top: 5px;">
                        <button type="button" class="btn-text" onclick="togglePassword()" style="background: none; border: none; color: var(--purple-neon); cursor: pointer;">
                            <i class="fas fa-eye"></i> Показать пароль
                        </button>
                    </div>
                </div>
                
                <div class="form-group" style="display: flex; justify-content: space-between; align-items: center;">
                    <label class="checkbox-label">
                        <input type="checkbox" name="remember"> Запомнить меня
                    </label>
                    <a href="#" class="auth-link">Забыли пароль?</a>
                </div>
                
                <button type="submit" class="btn-primary">
                    <i class="fas fa-sign-in-alt"></i> Войти в систему
                </button>
            </form>
            
            <div class="auth-switch">
                Еще нет аккаунта?
                <a href="{{ url_for('register') }}" class="auth-link">Создать новый аккаунт</a>
            </div>
            
            <div class="auth-divider">
                <span>или войти через</span>
            </div>
            
            <div class="social-auth">
                <button type="button" class="btn-social google">
                    <i class="fab fa-google"></i> Google
                </button>
                <button type="button" class="btn-social github">
                    <i class="fab fa-github"></i> GitHub
                </button>
            </div>
        </div>
    </div>

    <script>
    function togglePassword() {
        const passwordInput = document.getElementById('password');
        const toggleBtn = event.currentTarget;
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i> Скрыть пароль';
        } else {
            passwordInput.type = 'password';
            toggleBtn.innerHTML = '<i class="fas fa-eye"></i> Показать пароль';
        }
    }
    </script>
</body>
</html>
'''

register_template = '''
<!DOCTYPE html>
<html lang="ru" class="dark-theme">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Регистрация в Netta | Присоединяйтесь к сообществу</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='favicon.ico') }}">
</head>
<body>
    <div class="auth-page">
        <div class="auth-card">
            <div class="auth-logo">
                <div class="logo">
                    <div class="logo-icon">N</div>
                    <span>Netta</span>
                </div>
            </div>
            
            <h1 class="auth-title">Создайте аккаунт</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <div class="flash-messages">
                        {% for category, message in messages %}
                            <div class="flash-message flash-{{ category }}">
                                <i class="fas fa-{% if category == 'success' %}check-circle{% else %}exclamation-circle{% endif %}"></i>
                                {{ message }}
                            </div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}
            
            <form method="POST" action="{{ url_for('register') }}">
                <div class="form-group">
                    <label for="username" class="form-label">
                        <i class="fas fa-user"></i> Имя пользователя
                    </label>
                    <input type="text" id="username" name="username" class="form-control" required placeholder="Придумайте уникальное имя">
                </div>
                
                <div class="form-group">
                    <label for="email" class="form-label">
                        <i class="fas fa-envelope"></i> Email адрес
                    </label>
                    <input type="email" id="email" name="email" class="form-control" required placeholder="example@domain.com">
                </div>
                
                <div class="form-group">
                    <label for="full_name" class="form-label">
                        <i class="fas fa-id-card"></i> Полное имя (необязательно)
                    </label>
                    <input type="text" id="full_name" name="full_name" class="form-control" placeholder="Как вас зовут?">
                </div>
                
                <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="form-group">
                        <label for="password" class="form-label">
                            <i class="fas fa-lock"></i> Пароль
                        </label>
                        <input type="password" id="password" name="password" class="form-control" required placeholder="Минимум 8 символов">
                    </div>
                    
                    <div class="form-group">
                        <label for="confirm_password" class="form-label">
                            <i class="fas fa-lock"></i> Подтвердите пароль
                        </label>
                        <input type="password" id="confirm_password" name="confirm_password" class="form-control" required placeholder="Повторите пароль">
                    </div>
                </div>
                
                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="terms" name="terms" required>
                        <label for="terms">
                            Я соглашаюсь с <a href="#" class="auth-link">Условиями использования</a> и <a href="#" class="auth-link">Политикой конфиденциальности</a>
                        </label>
                    </div>
                </div>
                
                <button type="submit" class="btn-primary">
                    <i class="fas fa-user-plus"></i> Создать аккаунт
                </button>
            </form>
            
            <div class="auth-switch">
                Уже есть аккаунт?
                <a href="{{ url_for('login') }}" class="auth-link">Войти в систему</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

dashboard_template = '''
<!DOCTYPE html>
<html lang="ru" class="dark-theme">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netta | Главная</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='favicon.ico') }}">
</head>
<body>
    <!-- Шапка -->
    <header class="header">
        <div class="container">
            <nav class="navbar">
                <!-- Логотип -->
                <a href="{{ url_for('index') }}" class="logo">
                    <div class="logo-icon">N</div>
                    <span>Netta</span>
                </a>

                <!-- Поиск -->
                <div class="search-bar">
                    <i class="fas fa-search search-icon"></i>
                    <input type="text" class="search-input" placeholder="Поиск друзей, постов, сообществ...">
                </div>

                <!-- Иконки навигации -->
                <div class="nav-icons">
                    <a href="{{ url_for('index') }}" class="nav-icon" data-tooltip="Главная">
                        <i class="fas fa-home"></i>
                    </a>
                    
                    <a href="#" class="nav-icon" data-tooltip="Друзья">
                        <i class="fas fa-user-friends"></i>
                    </a>
                    
                    <a href="#" class="nav-icon notifications-btn" data-tooltip="Уведомления">
                        <i class="fas fa-bell"></i>
                        {% if current_user.get_unread_notifications() > 0 %}
                        <span class="nav-icon-badge">{{ current_user.get_unread_notifications() }}</span>
                        {% endif %}
                    </a>
                    
                    <a href="#" class="nav-icon" data-tooltip="Сообщения">
                        <i class="fas fa-comments"></i>
                        <span class="nav-icon-badge">3</span>
                    </a>
                    
                    <div class="user-menu">
                        <img src="{{ url_for('static', filename='uploads/' + current_user.profile_pic) }}" 
                             alt="{{ current_user.username }}" 
                             class="user-avatar"
                             data-tooltip="Меню профиля">
                    </div>
                </div>
            </nav>
        </div>
    </header>

    <!-- Основной контент -->
    <main class="main-container">
        <!-- Левый сайдбар -->
        <aside class="sidebar">
            <div class="sidebar-card">
                <div class="user-profile">
                    <img src="{{ url_for('static', filename='uploads/' + current_user.profile_pic) }}" 
                         alt="{{ current_user.username }}" 
                         class="profile-avatar">
                    <h3 class="profile-name">{{ current_user.full_name or current_user.username }}</h3>
                    <p class="profile-username">@{{ current_user.username }}</p>
                    <p class="profile-bio">{{ current_user.bio or 'Добавьте описание в профиле' }}</p>
                    
                    <div class="profile-stats">
                        <div class="stat">
                            <strong>{{ current_user.posts|length }}</strong>
                            <span>Постов</span>
                        </div>
                        <div class="stat">
                            <strong>{{ current_user.get_friends()|length }}</strong>
                            <span>Друзей</span>
                        </div>
                        <div class="stat">
                            <strong>0</strong>
                            <span>Лайков</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="sidebar-card">
                <h3 class="sidebar-title">Навигация</h3>
                <nav class="sidebar-nav">
                    <a href="#" class="sidebar-link active">
                        <i class="fas fa-newspaper"></i> Новости
                    </a>
                    <a href="#" class="sidebar-link">
                        <i class="fas fa-user-friends"></i> Друзья
                        <span class="sidebar-link-badge">{{ current_user.get_pending_requests()|length }}</span>
                    </a>
                    <a href="#" class="sidebar-link">
                        <i class="fas fa-users"></i> Сообщества
                    </a>
                    <a href="#" class="sidebar-link">
                        <i class="fas fa-photo-video"></i> Медиа
                    </a>
                    <a href="#" class="sidebar-link">
                        <i class="fas fa-calendar-alt"></i> События
                    </a>
                    <a href="#" class="sidebar-link">
                        <i class="fas fa-cog"></i> Настройки
                    </a>
                </nav>
            </div>

            <div class="sidebar-card">
                <h3 class="sidebar-title">Быстрые ссылки</h3>
                <nav class="sidebar-nav">
                    <a href="#" class="sidebar-link">
                        <i class="fas fa-gamepad"></i> Игры
                    </a>
                    <a href="#" class="sidebar-link">
                        <i class="fas fa-shopping-bag"></i> Магазин
                    </a>
                    <a href="#" class="sidebar-link">
                        <i class="fas fa-heart"></i> Избранное
                    </a>
                </nav>
            </div>
        </aside>

        <!-- Центральная лента -->
        <section class="feed">
            <!-- Создание поста -->
            <div class="create-post-card">
                <form class="post-form" id="create-post-form">
                    <div class="post-user">
                        <img src="{{ url_for('static', filename='uploads/' + current_user.profile_pic) }}" 
                             alt="{{ current_user.username }}" 
                             class="post-avatar">
                        <div>
                            <h3>{{ current_user.full_name or current_user.username }}</h3>
                            <select name="privacy" class="privacy-select">
                                <option value="public">🌍 Публичный</option>
                                <option value="friends">👥 Только друзья</option>
                                <option value="private">🔒 Только я</option>
                            </select>
                        </div>
                    </div>
                    
                    <textarea class="post-input" placeholder="Что у вас нового, {{ current_user.username }}?"></textarea>
                    
                    <div class="post-actions">
                        <div class="post-attachments">
                            <button type="button" class="attachment-btn" data-tooltip="Фото/Видео">
                                <i class="fas fa-image"></i>
                            </button>
                            <button type="button" class="attachment-btn" data-tooltip="Чувства">
                                <i class="fas fa-smile"></i>
                            </button>
                            <button type="button" class="attachment-btn" data-tooltip="Теги">
                                <i class="fas fa-tag"></i>
                            </button>
                            <button type="button" class="attachment-btn" data-tooltip="Опрос">
                                <i class="fas fa-poll"></i>
                            </button>
                        </div>
                        
                        <button type="submit" class="post-btn">
                            <i class="fas fa-paper-plane"></i> Опубликовать
                        </button>
                    </div>
                </form>
            </div>

            <!-- Посты -->
            {% for post in posts %}
            <div class="post-card">
                <div class="post-header">
                    <div class="post-user">
                        <img src="{{ url_for('static', filename='uploads/' + post.author.profile_pic) }}" 
                             alt="{{ post.author.username }}" 
                             class="post-avatar">
                        <div class="post-user-info">
                            <h3>{{ post.author.full_name or post.author.username }}</h3>
                            <span>{{ post.created_at.strftime('%d %b %Y в %H:%M') }}</span>
                        </div>
                    </div>
                    
                    <div class="post-time">
                        <i class="fas fa-globe"></i>
                        {% if post.privacy == 'public' %}
                        <span>Публичный</span>
                        {% elif post.privacy == 'friends' %}
                        <span>Только друзья</span>
                        {% else %}
                        <span>Только я</span>
                        {% endif %}
                    </div>
                </div>
                
                <div class="post-content">
                    <p>{{ post.content }}</p>
                    
                    {% if post.image_url %}
                    <div class="post-media">
                        <img src="{{ url_for('static', filename='uploads/' + post.image_url) }}" alt="Пост {{ post.author.username }}">
                    </div>
                    {% endif %}
                </div>
                
                <div class="post-stats">
                    <div class="likes-stat">
                        <i class="fas fa-heart"></i>
                        <span>{{ post.likes_count }} лайков</span>
                    </div>
                    <div class="comments-stat">
                        <i class="fas fa-comment"></i>
                        <span>{{ post.comments_count }} комментариев</span>
                    </div>
                    <div class="shares-stat">
                        <i class="fas fa-share"></i>
                        <span>{{ post.shares_count }} репостов</span>
                    </div>
                </div>
                
                <div class="post-actions-bar">
                    <button class="post-action like-btn {% if post.id in liked_posts %}active{% endif %}" data-post-id="{{ post.id }}">
                        <i class="fas fa-heart"></i>
                        <span>Нравится</span>
                    </button>
                    
                    <button class="post-action comment-btn" data-post-id="{{ post.id }}">
                        <i class="fas fa-comment"></i>
                        <span>Комментировать</span>
                    </button>
                    
                    <button class="post-action share-btn" data-post-id="{{ post.id }}">
                        <i class="fas fa-share"></i>
                        <span>Поделиться</span>
                    </button>
                    
                    <button class="post-action save-btn" data-post-id="{{ post.id }}">
                        <i class="fas fa-bookmark"></i>
                        <span>Сохранить</span>
                    </button>
                </div>
                
                <!-- Комментарии -->
                <div class="comments-section" style="display: none;" data-post-id="{{ post.id }}">
                    <div class="comments-list">
                        {% for comment in post.comments[:3] %}
                        <div class="comment-item">
                            <img src="{{ url_for('static', filename='uploads/' + comment.author.profile_pic) }}" 
                                 alt="{{ comment.author.username }}" 
                                 class="comment-avatar">
                            <div class="comment-content">
                                <strong>{{ comment.author.username }}</strong>
                                <p>{{ comment.content }}</p>
                                <span class="comment-time">{{ comment.created_at.strftime('%H:%M') }}</span>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    
                    <form class="comment-form" data-post-id="{{ post.id }}">
                        <input type="text" placeholder="Напишите комментарий..." class="comment-input">
                        <button type="submit" class="comment-submit">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </section>

        <!-- Правый сайдбар -->
        <aside class="right-sidebar">
            <div class="friends-card">
                <h3 class="sidebar-title">Друзья онлайн</h3>
                <div class="friends-list">
                    {% for friend in online_friends[:5] %}
                    <div class="friend-item">
                        <img src="{{ url_for('static', filename='uploads/' + friend.profile_pic) }}" 
                             alt="{{ friend.username }}" 
                             class="friend-avatar">
                        <div class="friend-info">
                            <div class="friend-name">{{ friend.full_name or friend.username }}</div>
                            <div class="friend-status friend-online">
                                <i class="fas fa-circle"></i> В сети
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="trending-card">
                <h3 class="sidebar-title">Тренды</h3>
                <div class="trending-list">
                    {% for trend in trends %}
                    <div class="trending-item">
                        <div class="trending-number">{{ loop.index }}</div>
                        <div class="trending-content">
                            <div class="trending-title">{{ trend.title }}</div>
                            <div class="trending-count">{{ trend.count }} постов</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="events-card">
                <h3 class="sidebar-title">Ближайшие события</h3>
                <div class="events-list">
                    {% for event in events %}
                    <div class="event-item">
                        <div class="event-date">
                            <span class="event-day">{{ event.date.day }}</span>
                            <span class="event-month">{{ event.date.strftime('%b') }}</span>
                        </div>
                        <div class="event-info">
                            <div class="event-title">{{ event.title }}</div>
                            <div class="event-time">{{ event.time }}</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </aside>
    </main>

    <!-- Футер -->
    <footer class="footer">
        <div class="container">
            <div class="footer-links">
                <a href="#" class="footer-link">О нас</a>
                <a href="#" class="footer-link">Помощь</a>
                <a href="#" class="footer-link">Реклама</a>
                <a href="#" class="footer-link">Вакансии</a>
                <a href="#" class="footer-link">Конфиденциальность</a>
                <a href="#" class="footer-link">Условия</a>
                <a href="#" class="footer-link">Язык</a>
            </div>
            
            <div class="copyright">
                <p>© 2026 Netta Social Network. Все права защищены.</p>
                <p>Сделано с <i class="fas fa-heart" style="color: var(--purple-neon);"></i> для лучшего общения</p>
            </div>
        </div>
    </footer>

    <!-- JavaScript -->
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    <script>
    // Инициализация
    document.addEventListener('DOMContentLoaded', function() {
        // Переключение комментариев
        document.querySelectorAll('.comment-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const postId = this.dataset.postId;
                const commentsSection = document.querySelector(`.comments-section[data-post-id="${postId}"]`);
                commentsSection.style.display = commentsSection.style.display === 'none' ? 'block' : 'none';
            });
        });
        
        // Создание поста
        document.getElementById('create-post-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const content = this.querySelector('.post-input').value;
            const privacy = this.querySelector('.privacy-select').value;
            
            // Отправка AJAX запроса
            fetch('/api/create_post', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    privacy: privacy
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                }
            });
        });
    });
    </script>
</body>
</html>
'''

# Создание файлов
with open('templates/login.html', 'w', encoding='utf-8') as f:
    f.write(login_template)

with open('templates/register.html', 'w', encoding='utf-8') as f:
    f.write(register_template)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(dashboard_template)

with open('static/css/style.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

with open('static/js/main.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

# ============ МАРШРУТЫ ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        # Получаем посты для ленты
        posts = Post.query.filter(
            (Post.privacy == 'public') | 
            ((Post.privacy == 'friends') & (Post.author.id.in_([f.id for f in current_user.get_friends()]))) |
            (Post.user_id == current_user.id)
        ).order_by(Post.created_at.desc()).limit(20).all()
        
        # Получаем друзей онлайн
        online_friends = [friend for friend in current_user.get_friends() 
                         if (datetime.utcnow() - friend.last_seen).seconds < 300]
        
        # Тренды (заглушка)
        trends = [
            {'title': '#NettaLaunch', 'count': 1250},
            {'title': '#ФиолетовыйДизайн', 'count': 890},
            {'title': 'Новые функции', 'count': 540},
            {'title': 'Социальные сети', 'count': 420},
            {'title': 'Web 3.0', 'count': 310}
        ]
        
        # События (заглушка)
        events = [
            {'title': 'Вебинар: Новые технологии', 'date': datetime.utcnow() + timedelta(days=1), 'time': '19:00'},
            {'title': 'Митап разработчиков', 'date': datetime.utcnow() + timedelta(days=3), 'time': '18:30'},
            {'title': 'Релиз Netta 2.0', 'date': datetime.utcnow() + timedelta(days=7), 'time': '12:00'}
        ]
        
        # ID постов, которые лайкнул пользователь
        liked_posts = [like.post_id for like in current_user.likes]
        
        return render_template('dashboard.html', 
                             posts=posts, 
                             online_friends=online_friends, 
                             trends=trends, 
                             events=events,
                             liked_posts=liked_posts)
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
            login_user(user, remember='remember' in request.form)
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
        full_name = request.form.get('full_name', '')
        
        # Валидация
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

# API маршруты
@app.route('/api/create_post', methods=['POST'])
@login_required
def create_post():
    data = request.json
    post = Post(
        content=data['content'],
        user_id=current_user.id,
        privacy=data.get('privacy', 'public')
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'success': True, 'post_id': post.id})

@app.route('/api/like', methods=['POST'])
@login_required
def like_post():
    data = request.json
    post_id = data['post_id']
    action = data['action']
    
    post = Post.query.get_or_404(post_id)
    
    if action == 'like':
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        post.likes_count += 1
        
        # Создание уведомления
        if post.author.id != current_user.id:
            create_notification(
                user_id=post.author.id,
                type='like',
                content=f'{current_user.username} понравился ваш пост',
                reference_id=post_id
            )
    else:
        like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        if like:
            db.session.delete(like)
            post.likes_count = max(0, post.likes_count - 1)
    
    db.session.commit()
    return jsonify({'success': True, 'likes_count': post.likes_count})

@app.route('/api/comment', methods=['POST'])
@login_required
def add_comment():
    data = request.json
    post_id = data['post_id']
    content = data['content']
    
    post = Post.query.get_or_404(post_id)
    comment = Comment(
        content=content,
        user_id=current_user.id,
        post_id=post_id
    )
    
    post.comments_count += 1
    
    db.session.add(comment)
    db.session.commit()
    
    # Создание уведомления
    if post.author.id != current_user.id:
        create_notification(
            user_id=post.author.id,
            type='comment',
            content=f'{current_user.username} прокомментировал ваш пост',
            reference_id=post_id
        )
    
    return jsonify({
        'success': True, 
        'comments_count': post.comments_count,
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'author': current_user.to_dict()
        }
    })

@app.route('/api/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(20).all()
    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.type,
            'content': n.content,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        } for n in notifications],
        'unread_count': current_user.get_unread_notifications()
    })

# Статические файлы
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# Обработка 404
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# Запуск приложения
if __name__ == '__main__':
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
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
