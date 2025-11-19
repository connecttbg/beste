
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///beste_negler.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


def get_lang():
    lang = session.get('lang')
    if lang not in ['no', 'en']:
        lang = 'no'
        session['lang'] = lang
    return lang


@app.context_processor
def inject_globals():
    lang = get_lang()
    labels = {
        'no': {
            'title': 'Beste Negler',
            'home': 'Start',
            'shop': 'Butikk',
            'login': 'Logg inn',
            'logout': 'Logg ut',
            'register': 'Registrer deg',
            'cart': 'Handlekurv',
            'admin': 'Admin',
        },
        'en': {
            'title': 'Beste Negler',
            'home': 'Home',
            'shop': 'Shop',
            'login': 'Login',
            'logout': 'Logout',
            'register': 'Register',
            'cart': 'Cart',
            'admin': 'Admin',
        }
    }
    return {
        'current_lang': lang,
        'labels': labels[lang]
    }


def translate_text(text, target_lang='en'):
    """Placeholder for automatic translation.
    For real use, integrate an external translation service.
    Currently returns the original text if translation is not available.
    """
    # TODO: integrate e.g. googletrans or DeepL API here
    return text


def clean_html(raw):
    """Remove basic HTML tags & entities from imported descriptions."""
    if not raw:
        return ''
    import re, html as _html
    text = _html.unescape(str(raw))
    text = re.sub('<[^<]+?>', ' ', text)
    text = ' '.join(text.split())
    return text


def to_float(val, default=0.0):
    if val is None:
        return default
    s = str(val).strip().replace('%', '').replace(' ', '').replace(',', '.')
    if s == '':
        return default
    try:
        return float(s)
    except ValueError:
        return default


def to_int(val, default=0):
    if val is None:
        return default
    s = str(val).strip()
    if s == '':
        return default
    try:
        return int(float(s.replace(',', '.')))
    except ValueError:
        return default



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=False)
    ean = db.Column(db.String(64))
    name = db.Column(db.String(255), nullable=False)
    description_no = db.Column(db.Text)
    description_en = db.Column(db.Text)
    category = db.Column(db.String(128))
    weight = db.Column(db.Float)
    qty = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, default=0.0)
    brand = db.Column(db.String(128))
    image_url = db.Column(db.String(512))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    payment_method = db.Column(db.String(64))
    shipping_method = db.Column(db.String(64))
    total_amount = db.Column(db.Float)
    currency = db.Column(db.String(8), default='NOK')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in ['no', 'en']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


@app.route('/')
def index():
    products = Product.query.limit(8).all()
    return render_template('index.html', products=products)


@app.route('/products')
def product_list():
    category = request.args.get('category')
    query = Product.query
    if category:
        query = query.filter_by(category=category)
    products = query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    return render_template('product_list.html', products=products, categories=categories)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)


@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.query.filter(Product.id.in_(product_ids)).all() if product_ids else []
    items = []
    total = 0.0
    for p in products:
        qty = cart[str(p.id)]
        subtotal = p.price * qty
        total += subtotal
        items.append({'product': p, 'qty': qty, 'subtotal': subtotal})
    return render_template('cart.html', items=items, total=total)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    qty = int(request.form.get('qty', 1))
    cart = session.get('cart', {})
    cart[str(product.id)] = cart.get(str(product.id), 0) + qty
    session['cart'] = cart
    flash('Product added to cart', 'success')
    return redirect(url_for('cart'))


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    cart.pop(str(product_id), None)
    session['cart'] = cart
    flash('Product removed from cart', 'info')
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Cart is empty', 'warning')
        return redirect(url_for('product_list'))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        shipping_method = request.form.get('shipping_method')

        product_ids = [int(pid) for pid in cart.keys()]
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        total = 0.0
        for p in products:
            qty = cart[str(p.id)]
            total += p.price * qty

        order = Order(
            user_id=current_user.id if current_user.is_authenticated else None,
            payment_method=payment_method,
            shipping_method=shipping_method,
            total_amount=total,
            currency='NOK'
        )
        db.session.add(order)
        db.session.flush()

        for p in products:
            qty = cart[str(p.id)]
            item = OrderItem(
                order_id=order.id,
                product_id=p.id,
                quantity=qty,
                unit_price=p.price
            )
            db.session.add(item)
            p.qty = max(0, (p.qty or 0) - qty)

        db.session.commit()
        session['cart'] = {}
        flash('Order created. Integrate with payment provider (card, Klarna, Vipps).', 'success')
        return redirect(url_for('index'))

    return render_template('checkout.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'warning')
            return redirect(url_for('register'))
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created, you can log in now.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('index'))


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin_products.html', products=products)


@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required
def admin_new_product():
    if request.method == 'POST':
        sku = request.form['sku']
        name = request.form['name']
        description_no = request.form.get('description_no')
        description_en = request.form.get('description_en') or translate_text(description_no or '', 'en')
        product = Product(
            sku=sku,
            ean=request.form.get('ean'),
            name=name,
            description_no=description_no,
            description_en=description_en,
            category=request.form.get('category'),
            weight=float(request.form.get('weight') or 0),
            qty=int(request.form.get('qty') or 0),
            price=float(request.form.get('price') or 0),
            tax=float(request.form.get('tax') or 0),
            brand=request.form.get('brand'),
            image_url=request.form.get('image_url')
        )
        db.session.add(product)
        db.session.commit()
        flash('Product created', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=None)


@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.sku = request.form['sku']
        product.ean = request.form.get('ean')
        product.name = request.form['name']
        product.description_no = request.form.get('description_no')
        product.description_en = request.form.get('description_en') or translate_text(product.description_no or '', 'en')
        product.category = request.form.get('category')
        product.weight = float(request.form.get('weight') or 0)
        product.qty = int(request.form.get('qty') or 0)
        product.price = float(request.form.get('price') or 0)
        product.tax = float(request.form.get('tax') or 0)
        product.brand = request.form.get('brand')
        product.image_url = request.form.get('image_url')
        db.session.commit()
        flash('Product updated', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=product)


@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted', 'info')
    return redirect(url_for('admin_products'))


@app.route('/admin/import', methods=['GET', 'POST'])
@admin_required
def admin_import():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file uploaded', 'warning')
            return redirect(url_for('admin_import'))
        content = file.read().decode('utf-8-sig')
        f = io.StringIO(content)
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        skipped = 0
        for row in reader:
            try:
                sku = row.get('sku')
                if not sku:
                    skipped += 1
                    continue
                existing = Product.query.filter_by(sku=sku).first()
                description_no = clean_html(row.get('description'))
                description_en = translate_text(description_no or '', 'en')
                data = {
                    'sku': sku,
                    'ean': row.get('EAN'),
                    'name': row.get('name'),
                    'description_no': description_no,
                    'description_en': description_en,
                    'category': row.get('category'),
                    'weight': to_float(row.get('weight')),
                    'qty': to_int(row.get('qty')),
                    'price': to_float(row.get('price')),
                    'tax': to_float(row.get('tax')),
                    'brand': row.get('brand'),
                    'image_url': (row.get('images') or '').split(',')[0].strip() if row.get('images') else None
                }
                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    product = Product(**data)
                    db.session.add(product)
                count += 1
            except Exception as e:
                # skip problematic row but don't break whole import
                skipped += 1
                print(f"CSV import: skipped row due to error: {e} | row={row}")
                continue
        db.session.commit()
        msg = f'Importert/oppdatert {count} produkter'
        if skipped:
            msg += f' (hoppet over {skipped} rader med feil)'
        flash(msg, 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_import.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)


def init_db_and_admin():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(email="admin@bestenegler.no").first()
        if not admin:
            u = User(email="admin@bestenegler.no")
            u.set_password("Admin123")
            u.is_admin = True
            db.session.add(u)
            db.session.commit()
            print("AUTO (Render): Admin account created.")
        else:
            print("AUTO (Render): Admin already exists.")

init_db_and_admin()

if __name__ == '__main__':
    app.run()
