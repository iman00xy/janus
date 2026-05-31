from flask import render_template, redirect, url_for, flash, request
from redrum import app, db, bcrypt, s, mail
from flask_mail import Message
from redrum.forms import RegistrationForm, LoginForm
from redrum.models import Users, Product, Order, PostalCard
from itsdangerous import SignatureExpired
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from zarinpal import ZarinPal, RequestInput, VerifyInput
from flask_login import login_user, current_user, logout_user, login_required
import os
import qrcode

zarinpal = ZarinPal(merchant_id='مرچنت ایدی که سایت میده')

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        text = request.form.get('text')

        image = request.files.get('image')
        image_filename = None
        if image:
            image_filename = image.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)

        audio = request.files.get('audio')
        audio_filename = None
        if audio:
            if audio.content_type.startswith('audio/'):
                audio_filename = audio.filename
                audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
                audio.save(audio_path)
            else:
                flash('لطفاً فقط فایل‌های صوتی را آپلود کنید.', 'danger')
                return redirect(url_for('upload'))

        qr_filename = None
        if text:
            user_profile_url = url_for('profile', _external=True)
            qr_filename = f'qr_{len(text)}.png'
            qr_path = os.path.join(app.config['UPLOAD_FOLDER'], qr_filename)
            qr = qrcode.make(user_profile_url)
            qr.save(qr_path)

        new_upload = PostalCard(text=text, image_filename=image_filename, audio_filename=audio_filename, qr_filename=qr_filename)
        db.session.add(new_upload)
        db.session.commit()

        flash('فایل‌ها با موفقیت آپلود شدند و QR Code تولید شد', 'success')
        return redirect(url_for('upload'))

    return render_template('upload.html')


@app.route('/')
def home():
    categories = Product.query.with_entities(Product.category).distinct().all()
    products = Product.query.all()
    return render_template('home.html', products=products, categories=categories)


@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    total_price = product.price * quantity

    # اگه قبلاً همین محصول توی سبد هست، تعدادش رو اضافه کن
    existing = Order.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if existing:
        existing.quantity += quantity
        existing.total_price = existing.product.price * existing.quantity
    else:
        order = Order(
            user_id=current_user.id,
            product_id=product.id,
            quantity=quantity,
            total_price=total_price
        )
        db.session.add(order)

    db.session.commit()
    flash('محصول به سبد خرید اضافه شد', 'success')
    return redirect(url_for('home'))


@app.route('/remove-from-cart/<int:order_id>', methods=['POST'])
@login_required
def remove_from_cart(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('cart'))
    db.session.delete(order)
    db.session.commit()
    flash('محصول از سبد خرید حذف شد', 'success')
    return redirect(url_for('cart'))


@app.route('/cart')
@login_required
def cart():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in orders)
    return render_template('cart.html', orders=orders, total=total)


@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in orders)

    request_data = RequestInput(
        amount=total,
        description='خرید از فروشگاه جانوس',
        email=current_user.email,
        mobile=current_user.mobile_number,
        callback_url=url_for('payment_callback', _external=True)
    )

    result = zarinpal.request(request_data)

    if result.status == 100:
        return redirect(result.payment_link)
    else:
        flash('خطا در ایجاد تراکنش', 'danger')
        return redirect(url_for('cart'))


@app.route('/payment_callback')
@login_required
def payment_callback():
    status = request.args.get('Status')
    authority = request.args.get('Authority')

    orders = Order.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in orders)

    if status == 'OK':
        verify_data = VerifyInput(amount=total, authority=authority)
        result = zarinpal.verify(verify_data)
        if result.status == 100:
            flash('پرداخت با موفقیت انجام شد', 'success')
            Order.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
        else:
            flash('پرداخت ناموفق بود', 'danger')
    else:
        flash('پرداخت توسط کاربر لغو شد', 'warning')
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            hashed_pass = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = Users(
                username=form.username.data,
                email=form.email.data,
                mobile_number=form.mobile_number.data,
                password=hashed_pass
            )
            db.session.add(user)
            db.session.commit()

            token = s.dumps(user.email, salt='email-confirm')
            msg = Message('تأیید حساب کاربری جانوس', sender='noreply@example.com', recipients=[user.email])
            link = url_for('confirm_email', token=token, _external=True)
            msg.html = f'''
            <p>سلام {user.username},</p>
            <p>از ثبت‌نام شما سپاسگزاریم. لطفاً برای تأیید حساب خود روی دکمه زیر کلیک کنید:</p>
            <p><a href="{link}" style="padding: 10px; background-color: #c9a84c; color: black; text-decoration: none; border-radius: 4px;">تأیید حساب</a></p>
            <p>با تشکر،<br>تیم جانوس</p>'''
            mail.send(msg)

            flash("ایمیل تأییدی برای شما ارسال شد. لطفاً ایمیل خود را بررسی کنید.", "info")
            return redirect(url_for('Login'))

        except SQLAlchemyError:
            db.session.rollback()
            flash("یک خطا رخ داده است. لطفاً دوباره تلاش کنید.", "danger")

    return render_template('register.html', form=form)


@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        flash('لینک تأیید منقضی شده است.', 'danger')
        return redirect(url_for('register'))

    user = Users.query.filter_by(email=email).first_or_404()
    if user.is_confirmed:
        flash('حساب کاربری شما قبلاً تأیید شده است.', 'info')
    else:
        user.is_confirmed = True
        user.confirmed_on = datetime.utcnow()
        db.session.commit()
        flash('حساب کاربری شما تأیید شد.', 'success')
    return redirect(url_for('Login'))


@app.route('/Login', methods=['GET', 'POST'])
def Login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        login_input = form.username.data

        user = Users.query.filter_by(username=login_input).first()
        if not user:
            user = Users.query.filter_by(mobile_number=login_input).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if user.is_confirmed:
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                flash("شما با موفقیت وارد شدید", "success")
                return redirect(next_page if next_page else url_for('home'))
            else:
                flash('حساب شما هنوز تأیید نشده است. لطفاً ایمیل خود را بررسی کنید.', 'warning')
        else:
            flash("نام کاربری، شماره موبایل یا رمز عبور اشتباه است", "danger")

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("شما با موفقیت از حساب کاربری خود خارج شدید", "success")
    return redirect(url_for('home'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return render_template('profile.html')

@app.route('/setup-db-temp-x7k2')
def setup_db():
    try:
        products = [
            Product(product_name='گردنبند طلایی کلاسیک', quantity=10, price=1250000, description='گردنبند ظریف با آویز شمع طلایی، مناسب برای مهمانی‌های رسمی', category='جواهرات', image_url='https://picsum.photos/seed/necklace/400/400', is_active=True),
            Product(product_name='کیف دستی هنری', quantity=5, price=3800000, description='کیف چرمی با نقش هندسی انحصاری، دست‌دوز و بادوام', category='کیف و کفش', image_url='https://picsum.photos/seed/handbag/400/400', is_active=True),
            Product(product_name='عطر اختصاصی جانوس', quantity=15, price=2100000, description='ترکیب عود و وانیل با رایحه‌ای ماندگار', category='عطر', image_url='https://picsum.photos/seed/perfume/400/400', is_active=True),
            Product(product_name='تابلوی نقاشی مینیمال', quantity=3, price=8500000, description='اثر هنری اصیل روی بوم، امضاشده توسط هنرمند', category='هنر تجسمی', image_url='https://picsum.photos/seed/painting/400/400', is_active=True),
            Product(product_name='ماگ سرامیکی جانوس', quantity=20, price=480000, description='ماگ دست‌ساز با لوگوی جانوس، مقاوم در برابر حرارت', category='لوازم خانگی', image_url='https://picsum.photos/seed/mug/400/400', is_active=True),
            Product(product_name='شال هنری بافته‌شده', quantity=8, price=1750000, description='شال ابریشمی با نقش‌های هندسی ایرانی', category='پوشاک', image_url='https://picsum.photos/seed/scarf/400/400', is_active=True),
            Product(product_name='دستبند طلا و سنگ یشم', quantity=8, price=980000, description='دستبند ظریف طلایی با سنگ یشم طبیعی، دست‌ساز', category='جواهرات', image_url='https://picsum.photos/seed/bracelet/400/400', is_active=True),
            Product(product_name='گوشواره آویز طلایی', quantity=12, price=750000, description='گوشواره آویز با طرح قطره، مناسب برای استفاده روزانه', category='جواهرات', image_url='https://picsum.photos/seed/earring/400/400', is_active=True),
            Product(product_name='کیف پول چرم دست‌دوز', quantity=15, price=1200000, description='کیف پول مردانه از چرم طبیعی با جای کارت و اسکناس', category='کیف و کفش', image_url='https://picsum.photos/seed/wallet/400/400', is_active=True),
            Product(product_name='کوله پشتی هنری', quantity=6, price=2800000, description='کوله چرمی با نقش‌برجسته هنری، مناسب برای استفاده شهری', category='کیف و کفش', image_url='https://picsum.photos/seed/backpack/400/400', is_active=True),
            Product(product_name='عطر گل رز و عنبر', quantity=10, price=1650000, description='ترکیب گل رز و عنبر با ماندگاری بالا، مناسب برای بانوان', category='عطر', image_url='https://picsum.photos/seed/rose-perfume/400/400', is_active=True),
            Product(product_name='عطر چوب صندل', quantity=10, price=1900000, description='رایحه گرم و خاکی چوب صندل با نت‌های وانیل', category='عطر', image_url='https://picsum.photos/seed/sandalwood/400/400', is_active=True),
            Product(product_name='مجسمه برنزی انتزاعی', quantity=4, price=12000000, description='مجسمه دست‌ساز از برنز خالص، اثر هنرمند ایرانی', category='هنر تجسمی', image_url='https://picsum.photos/seed/sculpture/400/400', is_active=True),
            Product(product_name='چاپ دستی سیلک‌اسکرین', quantity=7, price=3200000, description='پرینت هنری با تکنیک سیلک‌اسکرین، نسخه محدود', category='هنر تجسمی', image_url='https://picsum.photos/seed/silkscreen/400/400', is_active=True),
            Product(product_name='شمع معطر دست‌ریخته', quantity=20, price=320000, description='شمع سویا با رایحه لاوندر و وانیل، سوخت ۴۰ ساعته', category='لوازم خانگی', image_url='https://picsum.photos/seed/candle/400/400', is_active=True),
            Product(product_name='بشقاب سرامیکی نقش‌دار', quantity=10, price=580000, description='بشقاب دست‌ساز با نقش هندسی ایرانی', category='لوازم خانگی', image_url='https://picsum.photos/seed/plate/400/400', is_active=True),
            Product(product_name='کلاه پشمی بافته‌شده', quantity=14, price=620000, description='کلاه گرم زمستانی با بافت سنتی و رنگ‌های طبیعی', category='پوشاک', image_url='https://picsum.photos/seed/wool-hat/400/400', is_active=True),
            Product(product_name='جوراب هنری طرح‌دار', quantity=30, price=185000, description='جوراب نخی با نقش‌های هنری انحصاری، تولید محدود', category='پوشاک', image_url='https://picsum.photos/seed/art-socks/400/400', is_active=True),
        ]
        db.session.bulk_save_objects(products)
        db.session.commit()
        return 'محصولات با موفقیت اضافه شدند!'
    except Exception as e:
        db.session.rollback()
        return f'خطا: {str(e)}'
