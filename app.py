from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import requests
from flask import Response

app = Flask(__name__)
app.config['SECRET_KEY'] = 'azerbaycan_azevip_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///azevip.db'

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
    bio = db.Column(db.String(250), default="Azevip istifadəçisi")

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
        hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=request.form['username'], email=request.form['email'], password=hashed_password)
        db.session.add(user)
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
    # İstəsəniz buraya yalnız öz e-poçtunuz üçün yoxlama qoya bilərsiniz, 
    # məsələn: if current_user.email == 'sizin_email@mail.com':
    users = User.query.all()
    return render_template('admin.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)