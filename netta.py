from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__, template_folder='.', static_folder='static')
app.config['SECRET_KEY'] = 'netta-secret-key-2024-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///netta.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модель пользователя
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создаем статическую папку для CSS
if not os.path.exists('static'):
    os.makedirs('static')

# Создаем CSS файл с фиолетовым дизайном
css_content = '''
:root {
    --primary-purple: #8a2be2;
    --dark-purple: #6a0dad;
    --light-purple: #9b30ff;
    --neon-purple: #bf00ff;
    --background: #0f0b1a;
    --card-bg: #1a1525;
    --text: #ffffff;
    --text-secondary: #b39ddb;
    --success: #7b1fa2;
    --error: #ff4081;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: var(--background);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background-image: 
        radial-gradient(circle at 20% 80%, rgba(138, 43, 226, 0.15) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(191, 0, 255, 0.1) 0%, transparent 50%);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Header */
.header {
    background: rgba(26, 21, 37, 0.9);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(138, 43, 226, 0.3);
    position: sticky;
    top: 0;
    z-index: 1000;
}

.navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
}

.logo {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text);
}

.logo-icon {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, var(--neon-purple), var(--primary-purple));
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    font-weight: bold;
    color: white;
    box-shadow: 0 0 20px rgba(191, 0, 255, 0.5);
    animation: glow 2s ease-in-out infinite alternate;
}

@keyframes glow {
    from {
        box-shadow: 0 0 20px rgba(191, 0, 255, 0.5);
    }
    to {
        box-shadow: 0 0 30px rgba(191, 0, 255, 0.8), 0 0 40px rgba(191, 0, 255, 0.3);
    }
}

.nav-links {
    display: flex;
    gap: 2rem;
    align-items: center;
}

.nav-link {
    color: var(--text-secondary);
    text-decoration: none;
    transition: color 0.3s;
    font-weight: 500;
}

.nav-link:hover {
    color: var(--neon-purple);
}

/* Auth Forms */
.auth-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
}

.auth-card {
    background: var(--card-bg);
    border-radius: 20px;
    padding: 3rem;
    width: 100%;
    max-width: 450px;
    border: 1px solid rgba(138, 43, 226, 0.3);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
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
    background: linear-gradient(90deg, var(--neon-purple), var(--primary-purple));
}

.auth-title {
    text-align: center;
    margin-bottom: 2rem;
    font-size: 2rem;
    background: linear-gradient(45deg, var(--neon-purple), var(--primary-purple));
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
}

.form-input {
    width: 100%;
    padding: 1rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(138, 43, 226, 0.3);
    border-radius: 10px;
    color: var(--text);
    font-size: 1rem;
    transition: all 0.3s;
}

.form-input:focus {
    outline: none;
    border-color: var(--neon-purple);
    box-shadow: 0 0 0 3px rgba(191, 0, 255, 0.1);
}

.btn {
    display: block;
    width: 100%;
    padding: 1rem;
    background: linear-gradient(135deg, var(--primary-purple), var(--dark-purple));
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(138, 43, 226, 0.3);
}

.btn:active {
    transform: translateY(0);
}

.auth-switch {
    text-align: center;
    margin-top: 2rem;
    color: var(--text-secondary);
}

.auth-link {
    color: var(--neon-purple);
    text-decoration: none;
    font-weight: 500;
    margin-left: 5px;
}

.auth-link:hover {
    text-decoration: underline;
}

/* Messages */
.flash-messages {
    position: fixed;
    top: 100px;
    right: 20px;
    z-index: 1000;
}

.flash-message {
    padding: 1rem 2rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    animation: slideIn 0.3s ease-out;
    min-width: 300px;
    backdrop-filter: blur(10px);
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.flash-success {
    background: rgba(123, 31, 162, 0.9);
    border: 1px solid var(--success);
}

.flash-error {
    background: rgba(255, 64, 129, 0.9);
    border: 1px solid var(--error);
}

/* Dashboard */
.dashboard {
    padding: 3rem 0;
}

.welcome-card {
    background: linear-gradient(135deg, rgba(138, 43, 226, 0.1), rgba(26, 21, 37, 0.8));
    border-radius: 20px;
    padding: 3rem;
    text-align: center;
    border: 1px solid rgba(138, 43, 226, 0.3);
    margin-bottom: 2rem;
}

.welcome-title {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    background: linear-gradient(45deg, var(--neon-purple), var(--primary-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.welcome-text {
    color: var(--text-secondary);
    font-size: 1.2rem;
    max-width: 600px;
    margin: 0 auto;
}

.features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 2rem;
    margin-top: 3rem;
}

.feature-card {
    background: var(--card-bg);
    padding: 2rem;
    border-radius: 15px;
    border: 1px solid rgba(138, 43, 226, 0.2);
    transition: transform 0.3s, border-color 0.3s;
}

.feature-card:hover {
    transform: translateY(-5px);
    border-color: var(--neon-purple);
}

.feature-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

.feature-title {
    font-size: 1.3rem;
    margin-bottom: 1rem;
    color: var(--neon-purple);
}

.feature-description {
    color: var(--text-secondary);
    line-height: 1.6;
}

/* Footer */
.footer {
    text-align: center;
    padding: 2rem;
    color: var(--text-secondary);
    border-top: 1px solid rgba(138, 43, 226, 0.3);
    margin-top: auto;
}

/* Responsive */
@media (max-width: 768px) {
    .navbar {
        flex-direction: column;
        gap: 1rem;
    }
    
    .nav-links {
        gap: 1rem;
    }
    
    .auth-card {
        padding: 2rem;
        margin: 1rem;
    }
    
    .welcome-card {
        padding: 2rem;
        margin: 1rem;
    }
    
    .features {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 480px) {
    .auth-card {
        padding: 1.5rem;
    }
    
    .welcome-title {
        font-size: 2rem;
    }
    
    .logo {
        font-size: 1.5rem;
    }
}
'''

# Создаем и сохраняем CSS файл
with open('static/style.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

# HTML шаблоны как строки
login_html = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в Netta</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <header class="header">
        <div class="container">
            <nav class="navbar">
                <a href="{{ url_for('index') }}" class="logo">
                    <div class="logo-icon">N</div>
                    Netta
                </a>
                <div class="nav-links">
                    <a href="{{ url_for('register') }}" class="nav-link">Регистрация</a>
                </div>
            </nav>
        </div>
    </header>

    <div class="auth-container">
        <div class="auth-card">
            <h1 class="auth-title">Вход в Netta</h1>
            <form method="POST" action="{{ url_for('login') }}">
                <div class="form-group">
                    <label for="username" class="form-label">Имя пользователя</label>
                    <input type="text" id="username" name="username" class="form-input" required>
                </div>
                <div class="form-group">
                    <label for="password" class="form-label">Пароль</label>
                    <input type="password" id="password" name="password" class="form-input" required>
                </div>
                <button type="submit" class="btn">Войти</button>
            </form>
            <div class="auth-switch">
                Нет аккаунта?
                <a href="{{ url_for('register') }}" class="auth-link">Зарегистрироваться</a>
            </div>
        </div>
    </div>

    <footer class="footer">
        <div class="container">
            <p>© 2024 Netta Social Network. Все права защищены.</p>
        </div>
    </footer>
</body>
</html>
'''

register_html = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Регистрация в Netta</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <header class="header">
        <div class="container">
            <nav class="navbar">
                <a href="{{ url_for('index') }}" class="logo">
                    <div class="logo-icon">N</div>
                    Netta
                </a>
                <div class="nav-links">
                    <a href="{{ url_for('login') }}" class="nav-link">Вход</a>
                </div>
            </nav>
        </div>
    </header>

    <div class="auth-container">
        <div class="auth-card">
            <h1 class="auth-title">Регистрация</h1>
            <form method="POST" action="{{ url_for('register') }}">
                <div class="form-group">
                    <label for="username" class="form-label">Имя пользователя</label>
                    <input type="text" id="username" name="username" class="form-input" required>
                </div>
                <div class="form-group">
                    <label for="email" class="form-label">Email</label>
                    <input type="email" id="email" name="email" class="form-input" required>
                </div>
                <div class="form-group">
                    <label for="password" class="form-label">Пароль</label>
                    <input type="password" id="password" name="password" class="form-input" required>
                </div>
                <div class="form-group">
                    <label for="confirm_password" class="form-label">Подтвердите пароль</label>
                    <input type="password" id="confirm_password" name="confirm_password" class="form-input" required>
                </div>
                <button type="submit" class="btn">Создать аккаунт</button>
            </form>
            <div class="auth-switch">
                Уже есть аккаунт?
                <a href="{{ url_for('login') }}" class="auth-link">Войти</a>
            </div>
        </div>
    </div>

    <footer class="footer">
        <div class="container">
            <p>© 2024 Netta Social Network. Все права защищены.</p>
        </div>
    </footer>
</body>
</html>
'''

dashboard_html = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netta - Добро пожаловать</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <header class="header">
        <div class="container">
            <nav class="navbar">
                <a href="{{ url_for('index') }}" class="logo">
                    <div class="logo-icon">N</div>
                    Netta
                </a>
                <div class="nav-links">
                    <span class="nav-link">Привет, {{ current_user.username }}!</span>
                    <a href="{{ url_for('logout') }}" class="nav-link">Выйти</a>
                </div>
            </nav>
        </div>
    </header>

    <main class="dashboard">
        <div class="container">
            <div class="welcome-card">
                <h1 class="welcome-title">Добро пожаловать в Netta!</h1>
                <p class="welcome-text">
                    Ваша социальная сеть нового поколения. Здесь вы можете общаться с друзьями, 
                    делиться моментами и открывать новое.
                </p>
            </div>

            <div class="features">
                <div class="feature-card">
                    <div class="feature-icon">👥</div>
                    <h3 class="feature-title">Друзья и сообщества</h3>
                    <p class="feature-description">
                        Находите друзей и присоединяйтесь к сообществам по интересам.
                    </p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">📱</div>
                    <h3 class="feature-title">Современный дизайн</h3>
                    <p class="feature-description">
                        Интуитивно понятный и адаптивный интерфейс для любого устройства.
                    </p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🔒</div>
                    <h3 class="feature-title">Безопасность</h3>
                    <p class="feature-description">
                        Ваши данные защищены с помощью современных технологий шифрования.
                    </p>
                </div>
            </div>
        </div>
    </main>

    <footer class="footer">
        <div class="container">
            <p>© 2024 Netta Social Network. Все права защищены.</p>
        </div>
    </footer>
</body>
</html>
'''

# Создаем директорию для статики и сохраняем CSS
if not os.path.exists('static'):
    os.makedirs('static')

with open('static/style.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

# Маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        return dashboard_html.replace('{{ current_user.username }}', current_user.username)
    return login_html

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return login_html

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return register_html
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'error')
            return register_html
        
        if User.query.filter_by(email=email).first():
            flash('Email уже используется', 'error')
            return register_html
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Аккаунт успешно создан! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    
    return register_html

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

# После if __name__ == '__main__': замени на:
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
