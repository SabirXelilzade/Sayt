    import os
    import requests
    from flask import Flask, render_template, redirect, url_for, request, flash
    from flask_sqlalchemy import SQLAlchemy
    from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
    from flask_bcrypt import Bcrypt
    from itsdangerous import URLSafeTimedSerializer as Serializer

    app = Flask(__name__)

    # --- KONFİQURASİYA ---
    # Render -> Environment bölməsində SECRET_KEY əlavə edin (yeni, təsadüfi bir dəyər)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-ucun-muveqqeti-acar')

    # Render-də SQLite hər deploy-da silinir. Daimi baza üçün Render PostgreSQL yaradıb
    # DATABASE_URL dəyişənini əlavə edin. Yoxdursa, SQLite istifadə olunur.
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///nexus.db')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url

    db = SQLAlchemy(app)
    bcrypt = Bcrypt(app)
    s = Serializer(app.config['SECRET_KEY'])

    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    # ƏSAS DÜZƏLİŞ: "Please log in to access this page." mesajını söndürür.
    # Bu mesaj hər qorunan səhifəyə girişdə sessiyada yığılırdı və qeydiyyat
    # səhifəsində göstərilirdi.
    login_manager.login_message = None


    def send_reset_email(user_email, reset_url):
        resend_api_key = os.environ.get("RESEND_API_KEY")
        headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "from": "onboarding@resend.dev",
            "to": [user_email],
            "subject": "Şifrənin Bərpası - Sayt",
            "html": f"""
                <p>Şifrənizi bərpa etmək üçün aşağıdakı linkə klikləyin:</p>
                <p><a href="{reset_url}">Şifrəni bərpa et</a></p>
                <p>Əgər bu sorğunu siz etməmisinizsə, bu mesajı nəzərə almaya bilərsiniz.</p>
            """
        }
        try:
            response = requests.post("https://api.resend.com/emails", json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                print("E-poçt Resend vasitəsilə uğurla göndərildi!", flush=True)
            else:
                print(f"XƏTA (Resend): {response.text}", flush=True)
        except Exception as e:
            print(f"XƏTA BAŞ VERDİ: {e}", flush=True)


    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


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
        # Artıq daxil olubsa, qeydiyyat səhifəsini göstərmə
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        if request.method == 'POST':
            username = (request.form.get('username') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password') or ''

            if not username or not email or not password:
                flash('Bütün xanaları doldurun!', 'danger')
                return redirect(url_for('register'))

            # Yalnız @gmail.com ünvanı ilə qeydiyyat
            if not email.endswith('@gmail.com'):
                flash('Yalnız @gmail.com ünvanı ilə qeydiyyatdan keçə bilərsiniz!', 'danger')
                return redirect(url_for('register'))

            if User.query.filter_by(username=username).first():
                flash('Bu istifadəçi adı artıq istifadə olunur!', 'danger')
                return redirect(url_for('register'))

            if User.query.filter_by(email=email).first():
                flash('Bu Gmail ünvanı ilə artıq bir hesab yaradılıb!', 'danger')
                return redirect(url_for('register'))

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash('Qeydiyyat uğurla tamamlandı! İndi daxil ola bilərsiniz.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html')


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        if request.method == 'POST':
            email = (request.form.get('email') or '').strip().lower()
            user = User.query.filter_by(email=email).first()
            if user and bcrypt.check_password_hash(user.password, request.form.get('password') or ''):
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


    # --- ŞİFRƏNİN BƏRPASI ---
    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if request.method == 'POST':
            user_email = (request.form.get('email') or '').strip().lower()

            # Yalnız hesab varsa göndər, amma istifadəçiyə həmişə eyni cavabı göstər
            user = User.query.filter_by(email=user_email).first()
            if user:
                try:
                    token = s.dumps(user_email, salt='password-reset-salt')
                    reset_url = url_for('reset_password', token=token, _external=True)
                    send_reset_email(user_email, reset_url)
                except Exception as e:
                    print(f"XƏTA (forgot_password): {e}", flush=True)

            flash('Əgər bu e-poçt qeydiyyatdadırsa, bərpa keçidi göndərildi.', 'success')
            return redirect(url_for('forgot_password'))

        return render_template('forgot_password.html')


    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        try:
            email = s.loads(token, salt='password-reset-salt', max_age=3600)
        except Exception:
            flash('Sıfırlama linki etibarsızdır və ya vaxtı bitib.', 'danger')
            return redirect(url_for('forgot_password'))

        if request.method == 'POST':
            new_password = request.form.get('password') or ''
            user = User.query.filter_by(email=email).first()

            if user and new_password:
                # ƏSAS DÜZƏLİŞ: şifrə hash olunmalıdır, əks halda giriş işləməz
                user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                db.session.commit()
                flash('Şifrəniz uğurla yeniləndi! İndi daxil ola bilərsiniz.', 'success')
                return redirect(url_for('login'))

            flash('Şifrəni yeniləmək mümkün olmadı.', 'danger')

        return render_template('reset_password.html')


    if __name__ == '__main__':
        app.run(debug=os.environ.get('FLASK_DEBUG') == '1')