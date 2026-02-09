from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'netta-ultra-mega-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///netta.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text, default='Исследователь вселенной Netta')
    avatar_color = db.Column(db.String(7), default='#7c3aed')
    cover_color = db.Column(db.String(7), default='#5b21b6')
    is_verified = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    coins = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    privacy = db.Column(db.String(20), default='public')
    posts_count = db.Column(db.Integer, default=0)
    friends_count = db.Column(db.Integer, default=0)
    likes_received = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    theme = db.Column(db.String(20), default='dark')
    notifications = db.Column(db.Boolean, default=True)
    email_notifications = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.level * 100:
            self.xp -= self.level * 100
            self.level += 1
            self.coins += 50
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
