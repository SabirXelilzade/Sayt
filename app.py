from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import requests
from flask import Response
from flask_mail import Mail, Message
app = Flask(__name__)
app.config['SECRET_KEY'] = 'azerbaycan_nexus_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexus.db'
# Flask-Mail Konfiqurasiyası
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sabirxelilzade0089@gmail.com'
app.config['MAIL_PASSWORD'] = 'zkcqmkqrwqnpayyn'
app.config['MAIL_DEFAULT_SENDER'] = ('Nexus Support', 'sabirxelilzade0089@gmail.com')

mail = Mail(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- VERİLƏNLƏR BAZASI MODELLƏRİ ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    bio = db.Column(db.String(250), default="nexus istifadəçisi")

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref='posts', lazy=True)

with app.app_context():
    db.create_all()

# --- SƏHİFƏLƏR VƏ MARŞRUTLAR ---

@app.route('/')
@login_required
def index():
    posts = Post.query.all()
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Yalnız @gmail.com ünvanı ilə qeydiyyat yoxlaması
        if not email.endswith('@gmail.com'):
            flash('Yalnız @gmail.com ünvanı ilə qeydiyyatdan keçə bilərsiniz!')
            return redirect(url_for('register'))
            
        # İstifadəçi adı və ya e-poçt bazada artıq mövcuddursa yoxlayaq
        user_by_username = User.query.filter_by(username=username).first()
        user_by_email = User.query.filter_by(email=email).first()
        
        if user_by_username:
            flash('Bu istifadəçi adı artıq istifadə olunur!')
            return redirect(url_for('register'))
            
        if user_by_email:
            flash('Bu Gmail ünvanı ilə artıq bir hesab yaradılıb!')
            return redirect(url_for('register'))
            
        # Şifrəni şifrələyib bazaya əlavə edirik
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Qeydiyyat uğurla tamamlandı! İndi daxil ola bilərsiniz.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Giriş uğursuz oldu. E-poçt və ya şifrə yanlışdır.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@app.route('/cixis')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/maraqli')
@login_required
def maraqli():
    return render_template('maraqli.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/dostlar')
@login_required
def dostlar():
    all_users = User.query.all()
    return render_template('dostlar.html', users=all_users)

@app.route('/messages')
@login_required
def messages():
    return render_template('messages.html')

@app.route('/bildirisler')
@login_required
def bildirisler():
    return render_template('bildirisler.html')

@app.route('/games')
@login_required
def games():
    return render_template('game.html')

@app.route('/ayarlar')
@login_required
def ayarlar():
    return render_template('ayarlar.html')

@app.route('/games/butulka')
@login_required
def butulka():
    return render_template('butulka.html')

@app.route('/add_post', methods=['POST'])
@login_required
def add_post():
    content = request.form.get('content')
    if content:
        post = Post(content=content, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
    return redirect(url_for('index'))

# --- ADMIN PANELİ ---
@app.route('/admin')
@login_required
def admin():
    if current_user.username != 'sabir':
        return "<h1>Sən sabir deyilsən!</h1><p>Bu səhifəyə daxil olmaq üçün admin hüquqlarınız yoxdur.</p>", 403
    
    users = User.query.all()
    return render_template('admin.html', users=users)

from itsdangerous import URLSafeTimedSerializer as Serializer

# Serializer obyektini app-in yuxarı hissəsində təyin et (məsələn, app.config['SECRET_KEY'] altında)
s = Serializer(app.config['SECRET_KEY'])

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        user_email = request.form.get('email')
        
        try:
            # İstifadəçi üçün təhlükəsiz 1 saatlıq token yaradırıq
            token = s.dumps(user_email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            
            msg = Message('Nexus - Şifrə sıfırlama sorğusu', recipients=[user_email])
            msg.body = f"Salam,\n\nNexus hesabınızın şifrəsini bərpa etmək üçün aşağıdakı keçidə daxil olun (Keçid 1 saat ərzində etibarlıdır):\n\n{reset_url}"
            
            mail.send(msg)
            flash('Şifrə bərpa keçidi e-poçt ünvanınıza göndərildi!', 'success')
        except Exception as e:
            flash(f'E-poçt göndərilerken xəta baş verdi: {e}', 'danger')
        
        return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Tokenin etibarlılığını yoxlayırıq (1 saat = 3650 saniyə və ya istədiyin vaxt)
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception:
        flash('Sıfırlama linki etibarsızdır və ya vaxtı bitib.', 'danger')
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        new_password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Şifrəni yeniləyirik (Əgər hash işlədirsənsə generate_password_hash istifadə et)
            user.password = new_password  # Və ya hash funksiyan necədirsə
            db.session.commit()
            flash('Şifrəniz uğurla yeniləndi! İndi daxil ola bilərsiniz.', 'success')
            return redirect(url_for('login'))
            
    return render_template('reset_password.html')
if __name__ == '__main__':
    app.run(debug=True)