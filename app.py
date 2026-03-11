from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'homemade_pickles_secret_key_2024'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Users table (added is_admin field)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_first_order INTEGER DEFAULT 1,
        is_admin INTEGER DEFAULT 0
    )''')
    
    # Add is_admin column if it doesn't exist (for existing databases)
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except:
        pass
    
    # Add is_first_order column if it doesn't exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_first_order INTEGER DEFAULT 1")
    except:
        pass
    
    # Addresses table
    c.execute('''CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        address TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        pincode TEXT NOT NULL,
        phone TEXT NOT NULL,
        is_default INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Cart table
    c.execute('''CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        weight TEXT NOT NULL,
        price INTEGER NOT NULL,
        image TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Add weight column if it doesn't exist
    try:
        c.execute("ALTER TABLE cart ADD COLUMN weight TEXT")
    except:
        pass
    
    # Add image column to cart if it doesn't exist
    try:
        c.execute("ALTER TABLE cart ADD COLUMN image TEXT")
    except:
        pass
    
    # Orders table (added address_id and status)
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        address_id INTEGER,
        items TEXT NOT NULL,
        total_amount INTEGER NOT NULL,
        discount_applied INTEGER DEFAULT 0,
        final_amount INTEGER NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'Pending',
        payment_method TEXT DEFAULT 'COD',
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (address_id) REFERENCES addresses(id)
    )''')
    
    # Add address_id column if it doesn't exist
    try:
        c.execute("ALTER TABLE orders ADD COLUMN address_id INTEGER")
    except:
        pass
    
    # Add status column if it doesn't exist
    try:
        c.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'")
    except:
        pass
    
    # Add discount_applied column if it doesn't exist
    try:
        c.execute("ALTER TABLE orders ADD COLUMN discount_applied INTEGER DEFAULT 0")
    except:
        pass
    
    # Add payment_method column if it doesn't exist
    try:
        c.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'COD'")
    except:
        pass
    
    # Products table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        benefits TEXT,
        ingredients TEXT,
        shelf_life TEXT,
        storage TEXT,
        image TEXT,
        variants TEXT,
        is_new INTEGER DEFAULT 1,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Coupons table
    c.execute('''CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_percent INTEGER NOT NULL,
        min_amount INTEGER DEFAULT 0,
        description TEXT
    )''')
    
    # Insert default coupons
    c.execute("SELECT COUNT(*) FROM coupons")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO coupons (code, discount_percent, min_amount, description) VALUES ('FIRST30', 30, 0, 'First Order - 30% Off')")
        c.execute("INSERT INTO coupons (code, discount_percent, min_amount, description) VALUES ('SAVE20', 20, 1000, 'Orders above ₹1000 - 20% Off')")
        c.execute("INSERT INTO coupons (code, discount_percent, min_amount, description) VALUES ('WELCOME10', 10, 500, 'Welcome Coupon - 10% Off')")
    
    # Create admin account if not exists
    c.execute("SELECT COUNT(*) FROM users WHERE email = 'admin@homemade.com'")
    if c.fetchone()[0] == 0:
        admin_password = generate_password_hash('admin123')
        c.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)",
                 ('Admin', 'admin@homemade.com', admin_password, 1))
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, name, email, is_admin=False):
        self.id = id
        self.name = name
        self.email = email
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, name, email, is_admin FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2], bool(user[3]))
    return None

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    cart_count = 0
    if current_user.is_authenticated:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (current_user.id,))
        cart_count = c.fetchone()[0]
        conn.close()
    return render_template("home.html", cart_count=cart_count)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, name, email, password, is_admin FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            # Check if user is admin
            if user[4]:  # is_admin
                flash('Please use admin login page', 'error')
                return redirect(url_for('admin_login'))
            
            user_obj = User(user[0], user[1], user[2], bool(user[4]))
            login_user(user_obj)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template("login.html")

@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, name, email, password, is_admin FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            # Check if user is admin
            if not user[4]:  # not admin
                flash('Access denied. Admin credentials required.', 'error')
                return redirect(url_for('admin_login'))
            
            user_obj = User(user[0], user[1], user[2], bool(user[4]))
            login_user(user_obj)
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'error')
    
    return render_template("admin_login.html")

@app.route("/admin/signup", methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        admin_key = request.form.get('admin_key')
        
        # Admin registration key (change this to your secret key)
        ADMIN_REGISTRATION_KEY = "ADMIN2024SECRET"
        
        if admin_key != ADMIN_REGISTRATION_KEY:
            flash('Invalid admin registration key', 'error')
            return redirect(url_for('admin_signup'))
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            c.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)", 
                     (name, email, hashed_password, 1))
            conn.commit()
            flash('Admin account created successfully! Please login.', 'success')
            return redirect(url_for('admin_login'))
        except sqlite3.IntegrityError:
            flash('Email already exists', 'error')
        finally:
            conn.close()
    
    return render_template("admin_signup.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", 
                     (name, email, hashed_password))
            conn.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists', 'error')
        finally:
            conn.close()
    
    return render_template("signup.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route("/admin/products", methods=['GET'])
@login_required
def admin_products():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products ORDER BY created_date DESC")
    products = c.fetchall()
    conn.close()
    
    return render_template("admin_products.html", products=products)

@app.route("/admin/products/add", methods=['POST'])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    name = request.form.get('name')
    category = request.form.get('category')
    description = request.form.get('description')
    benefits = request.form.get('benefits')
    ingredients = request.form.get('ingredients')
    shelf_life = request.form.get('shelf_life')
    storage = request.form.get('storage')
    image = request.form.get('image')
    
    # Get variants
    weights = request.form.getlist('variant_weight[]')
    prices = request.form.getlist('variant_price[]')
    
    # Create variants JSON string
    variants = []
    for i in range(len(weights)):
        if weights[i] and prices[i]:
            variants.append({"weight": weights[i], "price": int(prices[i])})
    
    import json
    variants_json = json.dumps(variants)
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""INSERT INTO products (name, category, description, benefits, ingredients, 
                 shelf_life, storage, image, variants, is_new) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
             (name, category, description, benefits, ingredients, shelf_life, storage, image, variants_json))
    conn.commit()
    conn.close()
    
    flash(f'Product "{name}" added successfully!', 'success')
    return redirect(url_for('admin_products'))

@app.route("/admin/products/delete/<int:product_id>")
@login_required
def admin_delete_product(product_id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

# Admin Routes
@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Get all orders with user info
    c.execute('''SELECT o.id, o.items, o.total_amount, o.discount_applied, 
                o.final_amount, o.order_date, o.status, u.name, u.email, o.payment_method 
                FROM orders o 
                JOIN users u ON o.user_id = u.id 
                ORDER BY o.order_date DESC''')
    orders = c.fetchall()
    
    # Get stats
    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'")
    pending_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    
    c.execute("SELECT SUM(final_amount) FROM orders WHERE status = 'Delivered'")
    total_revenue = c.fetchone()[0] or 0
    
    conn.close()
    
    return render_template("admin.html", orders=orders, pending_count=pending_count, 
                         total_orders=total_orders, total_revenue=total_revenue)

@app.route("/admin/update_order/<int:order_id>/<status>")
@login_required
def update_order(order_id, status):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    
    flash(f'Order #{order_id} {status}', 'success')
    return redirect(url_for('admin_dashboard'))

# Address Routes
@app.route("/addresses", methods=['GET', 'POST'])
@login_required
def addresses():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        pincode = request.form.get('pincode')
        phone = request.form.get('phone')
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""INSERT INTO addresses (user_id, full_name, address, city, state, pincode, phone) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (current_user.id, full_name, address, city, state, pincode, phone))
        conn.commit()
        conn.close()
        flash('Address added successfully!', 'success')
        return redirect(url_for('addresses'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM addresses WHERE user_id = ?", (current_user.id,))
    addresses = c.fetchall()
    conn.close()
    
    return render_template("addresses.html", addresses=addresses)

@app.route("/delete_address/<int:address_id>")
@login_required
def delete_address(address_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM addresses WHERE id = ? AND user_id = ?", (address_id, current_user.id))
    conn.commit()
    conn.close()
    flash('Address deleted', 'success')
    return redirect(url_for('addresses'))

# Product Routes
@app.route("/veg_pickles")
def veg_pickles():
    cart_count = 0
    if current_user.is_authenticated:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (current_user.id,))
        cart_count = c.fetchone()[0]
        
        # Get admin-added products
        c.execute("SELECT * FROM products WHERE category = 'veg' ORDER BY created_date DESC")
        db_products = c.fetchall()
        conn.close()
    else:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE category = 'veg' ORDER BY created_date DESC")
        db_products = c.fetchall()
        conn.close()
    
    # Convert database products to the same format
    import json
    admin_products = []
    for p in db_products:
        variants = json.loads(p[9]) if p[9] else []
        admin_products.append({
            "id": p[0],
            "name": p[1],
            "image": p[8] if p[8] else "/static/images/Background.jpg",
            "description": p[3],
            "benefits": p[4],
            "ingredients": p[5],
            "shelf_life": p[6],
            "storage": p[7],
            "variants": variants,
            "is_new": p[10]
        })
    
    products = [
        {
            "id": 1, 
            "name": "Gongura Pickle", 
            "image": "/static/images/Gongura.jpg",
            "description": "Traditional Andhra-style Gongura pickle made from fresh sorrel leaves. Rich in vitamins and minerals, this tangy pickle is a beloved delicacy in South Indian cuisine. Made with premium quality gongura leaves, handpicked at the right maturity.",
            "benefits": "Rich in Iron, Vitamins C & K, Aids Digestion, Boost Immunity",
            "ingredients": "Gongura Leaves, Red Chilli Powder, Salt, Garlic, Fenugreek, Mustard Seeds, Sesame Oil",
            "shelf_life": "6 months from date of manufacture",
            "storage": "Store in a cool, dry place. Refrigerate after opening.",
            "variants": [
                {"weight": "250g", "price": 220},
                {"weight": "500g", "price": 400},
                {"weight": "1kg", "price": 750}
            ]
        },
        {
            "id": 2, 
            "name": "Lemon Pickle", 
            "image": "/static/images/Lemon pickel.jpg",
            "description": "Zesty lemon pickle made with fresh lemons marinated in a perfect blend of spices. A household favorite that adds tang to any meal. Our lemons are carefully selected for optimal juice content and tanginess.",
            "benefits": "Rich in Vitamin C, Antioxidants, Aids Digestion, Boosts Metabolism",
            "ingredients": "Fresh Lemons, Red Chilli Powder, Salt, Fenugreek, Turmeric, Asafoetida, Sesame Oil",
            "shelf_life": "12 months from date of manufacture",
            "storage": "Store in a cool, dry place. Refrigerate after opening.",
            "variants": [
                {"weight": "250g", "price": 180},
                {"weight": "500g", "price": 320},
                {"weight": "1kg", "price": 600}
            ]
        },
        {
            "id": 3, 
            "name": "Mango Pickle", 
            "image": "/static/images/MangoPickel.jpg",
            "description": "Authentic Rayalaseema-style mango pickle made from raw mangoes. The perfect balance of spice and tanginess that reminds you of grandmother's kitchen. Made with organically grown raw mangoes.",
            "benefits": "Rich in Vitamins A, C & E, Good for Skin, Improves Digestion",
            "ingredients": "Raw Mangoes, Red Chilli Powder, Salt, Fenugreek, Mustard, Gingelly Oil",
            "shelf_life": "12 months from date of manufacture",
            "storage": "Store in a cool, dry place away from direct sunlight.",
            "variants": [
                {"weight": "250g", "price": 200},
                {"weight": "500g", "price": 360},
                {"weight": "1kg", "price": 680}
            ]
        },
        {
            "id": 4, 
            "name": "Tomato Pickle", 
            "image": "/static/images/Tomato pickle.jpg",
            "description": "Delicious tomato pickle made from ripe, juicy tomatoes. Perfect blend of sweetness and spice that goes well with rice, chapati, or as a side dish. Made from farm-fresh tomatoes.",
            "benefits": "Rich in Lycopene, Vitamin C, Potassium, Supports Heart Health",
            "ingredients": "Fresh Tomatoes, Red Chilli Powder, Salt, Garlic, Ginger, Spices, Mustard Oil",
            "shelf_life": "6 months from date of manufacture",
            "storage": "Refrigerate after opening for best taste.",
            "variants": [
                {"weight": "250g", "price": 170},
                {"weight": "500g", "price": 300},
                {"weight": "1kg", "price": 550}
            ]
        },
        {
            "id": 5, 
            "name": "Bitter Gourd Pickle", 
            "image": "/static/images/kakarakayapickle_1_1.jpg",
            "description": "Unique bitter gourd pickle that transforms the bitterness into a delicious delicacy. Made using a special process to reduce bitterness while preserving the health benefits.",
            "benefits": "Controls Blood Sugar, Purifies Blood, Good for Liver, Weight Management",
            "ingredients": "Bitter Gourd, Red Chilli Powder, Salt, Tamarind, Jaggery, Spices, Sesame Oil",
            "shelf_life": "6 months from date of manufacture",
            "storage": "Store in a cool, dry place. Refrigerate after opening.",
            "variants": [
                {"weight": "250g", "price": 190},
                {"weight": "500g", "price": 340},
                {"weight": "1kg", "price": 650}
            ]
        },
    ]
    
    # Combine admin products with default products
    all_products = admin_products + products
    
    return render_template("veg_pickles.html", products=all_products, cart_count=cart_count)

@app.route("/non_veg_pickles")
def non_veg_pickles():
    cart_count = 0
    if current_user.is_authenticated:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (current_user.id,))
        cart_count = c.fetchone()[0]
        
        # Get admin-added products
        c.execute("SELECT * FROM products WHERE category = 'nonveg' ORDER BY created_date DESC")
        db_products = c.fetchall()
        conn.close()
    else:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE category = 'nonveg' ORDER BY created_date DESC")
        db_products = c.fetchall()
        conn.close()
    
    # Convert database products to the same format
    import json
    admin_products = []
    for p in db_products:
        variants = json.loads(p[9]) if p[9] else []
        admin_products.append({
            "id": p[0],
            "name": p[1],
            "image": p[8] if p[8] else "/static/images/Background.jpg",
            "description": p[3],
            "benefits": p[4],
            "ingredients": p[5],
            "shelf_life": p[6],
            "storage": p[7],
            "variants": variants,
            "is_new": p[10]
        })
    
    products = [
        {
            "id": 1, 
            "name": "Chicken Boneless Pickle", 
            "image": "/static/images/chicken-boneless-pickle.jpg",
            "description": "Premium quality boneless chicken pickle made from tender chicken pieces. Slow-cooked in a rich blend of spices for that authentic flavor. Each piece is carefully selected for maximum tenderness.",
            "benefits": "High Protein, Rich in B Vitamins, Supports Muscle Growth, Energy Boost",
            "ingredients": "Chicken (Boneless), Red Chilli Powder, Salt, Ginger, Garlic, Garam Masala, Curry Leaves, Groundnut Oil",
            "shelf_life": "3 months from date of manufacture",
            "storage": "Refrigerate and consume within 15 days after opening.",
            "variants": [
                {"weight": "250g", "price": 380},
                {"weight": "500g", "price": 700},
                {"weight": "1kg", "price": 1300}
            ]
        },
        {
            "id": 2, 
            "name": "Fish Pickle", 
            "image": "/static/images/fish pickle.JPG",
            "description": "Traditional fish pickle made from fresh sea fish. Carefully deboned and marinated in our special spice blend. A coastal delicacy that brings the taste of the sea to your plate.",
            "benefits": "High in Omega-3, Protein, Calcium, Supports Brain Function",
            "ingredients": "Fish (Seer Fish/Surmai), Red Chilli, Turmeric, Salt, Ginger, Garlic, Curry Leaves, Coconut Oil",
            "shelf_life": "2 months from date of manufacture",
            "storage": "Always refrigerate. Best consumed within 10 days of opening.",
            "variants": [
                {"weight": "250g", "price": 350},
                {"weight": "500g", "price": 650},
                {"weight": "1kg", "price": 1200}
            ]
        },
        {
            "id": 3, 
            "name": "Mutton Pickle", 
            "image": "/static/images/mutton pickle.jpg",
            "description": "Rich and flavorful mutton pickle made from tender mutton pieces. Slow-cooked for hours to achieve the perfect texture and taste. A royal delicacy for meat lovers.",
            "benefits": "High Protein, Iron, Zinc, Vitamin B12, Supports Hemoglobin",
            "ingredients": "Mutton, Red Chilli Powder, Salt, Garam Masala, Ginger, Garlic, Curd, Mustard Oil",
            "shelf_life": "3 months from date of manufacture",
            "storage": "Refrigerate and consume within 15 days after opening.",
            "variants": [
                {"weight": "250g", "price": 420},
                {"weight": "500g", "price": 800},
                {"weight": "1kg", "price": 1500}
            ]
        },
        {
            "id": 4, 
            "name": "Gongura Chicken Pickle", 
            "image": "/static/images/gongurachicken.jpg",
            "description": "Signature dish combining the tanginess of gongura with tender chicken. A unique fusion that's become extremely popular. The sour gongura perfectly complements the savory chicken.",
            "benefits": "High Protein, Probiotics from Gongura, Vitamin C, Iron",
            "ingredients": "Chicken, Gongura Leaves, Red Chilli, Salt, Spices, Sesame Oil, Curry Leaves",
            "shelf_life": "3 months from date of manufacture",
            "storage": "Refrigerate after opening. Best within 15 days.",
            "variants": [
                {"weight": "250g", "price": 390},
                {"weight": "500g", "price": 720},
                {"weight": "1kg", "price": 1350}
            ]
        },
        {
            "id": 5, 
            "name": "Prawns Gongura Pickle", 
            "image": "/static/images/prawns_gongura.jpg",
            "description": "Exquisite prawns pickle with gongura - a coastal specialty. Juicy prawns cooked in tangy gongura paste creates a delightful burst of flavors. Made with fresh water prawns.",
            "benefits": "High Protein, Low Fat, Omega-3, Selenium, Vitamin B12",
            "ingredients": "Prawns, Gongura, Red Chilli, Salt, Spices, Coconut Oil, Curry Leaves",
            "shelf_life": "2 months from date of manufacture",
            "storage": "Always refrigerate. Best within 10 days of opening.",
            "variants": [
                {"weight": "250g", "price": 410},
                {"weight": "500g", "price": 760},
                {"weight": "1kg", "price": 1400}
            ]
        },
        {
            "id": 6, 
            "name": "Gongura Mutton Pickle", 
            "image": "/static/images/GonguraMutton-1.jpg",
            "description": "Premium mutton pickle with gongura - a royal delicacy. The combination of tender mutton with sour gongura creates an unforgettable taste. Slow-cooked to perfection.",
            "benefits": "High Protein, Iron, B Vitamins, Probiotics from Gongura",
            "ingredients": "Mutton, Gongura Leaves, Red Chilli, Garam Masala, Salt, Sesame Oil, Spices",
            "shelf_life": "3 months from date of manufacture",
            "storage": "Refrigerate and consume within 15 days after opening.",
            "variants": [
                {"weight": "250g", "price": 430},
                {"weight": "500g", "price": 820},
                {"weight": "1kg", "price": 1550}
            ]
        },
    ]
    
    # Combine admin products with default products
    all_products = admin_products + products
    
    return render_template("non_veg_pickles.html", products=all_products, cart_count=cart_count)

@app.route("/snacks")
def snacks():
    cart_count = 0
    if current_user.is_authenticated:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (current_user.id,))
        cart_count = c.fetchone()[0]
        
        # Get admin-added products
        c.execute("SELECT * FROM products WHERE category = 'snacks' ORDER BY created_date DESC")
        db_products = c.fetchall()
        conn.close()
    else:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE category = 'snacks' ORDER BY created_date DESC")
        db_products = c.fetchall()
        conn.close()
    
    # Convert database products to the same format
    import json
    admin_products = []
    for p in db_products:
        variants = json.loads(p[9]) if p[9] else []
        admin_products.append({
            "id": p[0],
            "name": p[1],
            "image": p[8] if p[8] else "/static/images/Background.jpg",
            "description": p[3],
            "benefits": p[4],
            "ingredients": p[5],
            "shelf_life": p[6],
            "storage": p[7],
            "variants": variants,
            "is_new": p[10]
        })
    
    products = [
        {
            "id": 1, 
            "name": "Ariselu", 
            "image": "/static/images/ariselu-side_2x_99b04b77-a741-48f1-b272-36f7a775f780.jpg",
            "description": "Traditional Telugu sweet made during Sankranti festival. Soft, melt-in-your-mouth rice flour laddoos with the perfect blend of sweetness. Handcrafted using authentic recipes passed down generations.",
            "benefits": "Energy Boost, Easy to Digest, Traditional Delicacy, Cultural Significance",
            "ingredients": "Rice Flour, Jaggery, Ghee, Cashew Nuts, Cardamom",
            "shelf_life": "15 days from date of manufacture",
            "storage": "Store in an airtight container. Keep away from moisture.",
            "variants": [
                {"weight": "250g", "price": 120},
                {"weight": "500g", "price": 220},
                {"weight": "1kg", "price": 400}
            ]
        },
        {
            "id": 2, 
            "name": "Aam Papad", 
            "image": "/static/images/Aam-Papad.jpg",
            "description": "Delicious mango papad made from ripe mango pulp. Thin, chewy, and full of natural mango flavor. A popular Indian snack that's both tasty and refreshing.",
            "benefits": "Natural Fruit Content, Vitamin A, Energy Source, No Artificial Colors",
            "ingredients": "Mango Pulp, Sugar, Citric Acid",
            "shelf_life": "6 months from date of manufacture",
            "storage": "Store in a cool, dry place. Avoid humidity.",
            "variants": [
                {"weight": "250g", "price": 100},
                {"weight": "500g", "price": 180},
                {"weight": "1kg", "price": 350}
            ]
        },
        {
            "id": 3, 
            "name": "Boondhi Acchu", 
            "image": "/static/images/Boondhi Acchu.jpg",
            "description": "Crispy boondi laddoos with a twist - boondi acchu is a crunchy, savory snack. Perfectly round boondi fried to golden perfection and mixed with spicy chutney.",
            "benefits": "Instant Energy, Protein from Besan, Satisfying Crunch",
            "ingredients": "Gram Flour (Besan), Salt, Soda, Curry Leaves, Spices, Oil for Frying",
            "shelf_life": "30 days from date of manufacture",
            "storage": "Store in an airtight container to maintain crunchiness.",
            "variants": [
                {"weight": "250g", "price": 90},
                {"weight": "500g", "price": 160},
                {"weight": "1kg", "price": 300}
            ]
        },
        {
            "id": 4, 
            "name": "Boondi Laddu", 
            "image": "/static/images/boondi-laddu-665537.jpg",
            "description": "Classic Indian sweet - soft and fragrant boondi laddoos. Each ladoo is hand-rolled to perfection with the right amount of sweetness and ghee.",
            "benefits": "Good Source of Protein, Energy Boosting, Traditional Sweet",
            "ingredients": "Gram Flour, Sugar, Ghee, Cardamom, Cashew Nuts, Raisins",
            "shelf_life": "15 days from date of manufacture",
            "storage": "Store in an airtight container in a cool place.",
            "variants": [
                {"weight": "250g", "price": 150},
                {"weight": "500g", "price": 280},
                {"weight": "1kg", "price": 500}
            ]
        },
        {
            "id": 5, 
            "name": "Dry Fruit Laddu", 
            "image": "/static/images/Dry fruit laddo.jpg",
            "description": "Premium dry fruit laddos loaded with cashews, almonds, and raisins. A luxurious sweet that's not just delicious but also nutritious. Made with generous amounts of ghee.",
            "benefits": "Rich in Omega-3, Vitamin E, Calcium, Heart Healthy Fats",
            "ingredients": "Almonds, Cashews, Raisins, Dates, Ghee, Jaggery, Cardamom",
            "shelf_life": "30 days from date of manufacture",
            "storage": "Refrigerate for longer shelf life. Bring to room temperature before consuming.",
            "variants": [
                {"weight": "250g", "price": 180},
                {"weight": "500g", "price": 340},
                {"weight": "1kg", "price": 650}
            ]
        },
        {
            "id": 6, 
            "name": "Sunnundalu", 
            "image": "/static/images/Sunnundalu.jpg",
            "description": "Traditional Andhra sweet made with rava (semolina), jaggery, and ghee. Heart-shaped laddoos that are a staple during festivals and special occasions.",
            "benefits": "Good Source of Iron, Provides Energy, Easy to Digest",
            "ingredients": "Semolina (Rava), Jaggery, Ghee, Cardamom, Cashew Nuts",
            "shelf_life": "15 days from date of manufacture",
            "storage": "Store in an airtight container.",
            "variants": [
                {"weight": "250g", "price": 160},
                {"weight": "500g", "price": 300},
                {"weight": "1kg", "price": 550}
            ]
        },
        {
            "id": 7, 
            "name": "Rava Laddu", 
            "image": "/static/images/rava-ladoo-featured.jpg",
            "description": "Soft and moist rava laddoos made with semolina, coconut, and ghee. A popular South Indian sweet that's perfect for tea-time snacking or as a dessert.",
            "benefits": "Provides Energy, Contains Coconut (Healthy Fats), Easy to Make",
            "ingredients": "Semolina, Coconut, Sugar, Ghee, Cashew Nuts, Cardamom",
            "shelf_life": "15 days from date of manufacture",
            "storage": "Store in an airtight container.",
            "variants": [
                {"weight": "250g", "price": 140},
                {"weight": "500g", "price": 260},
                {"weight": "1kg", "price": 480}
            ]
        },
        {
            "id": 8, 
            "name": "Chekka Pakodi", 
            "image": "/static/images/Chekka Pakodi.jpg",
            "description": "Crispy gram flour pakodis made from finely chopped vegetables. Perfect monsoon snack that's crunchy and addictive. Best enjoyed with a cup of hot tea.",
            "benefits": "High Protein, Fiber, Satisfying Crunch, Tea-Time Perfect",
            "ingredients": "Gram Flour, Chopped Vegetables, Salt, Spices, Curry Leaves, Oil for Frying",
            "shelf_life": "7 days from date of manufacture",
            "storage": "Store in an airtight container. Best consumed fresh for maximum crunch.",
            "variants": [
                {"weight": "250g", "price": 110},
                {"weight": "500g", "price": 200},
                {"weight": "1kg", "price": 380}
            ]
        },
        {
            "id": 9, 
            "name": "Kara Boondi", 
            "image": "/static/images/Kara-Boondi-4.jpg",
            "description": "Spicy boondi - crispy gram flour pearls mixed with spicy chutney. A popular savory snack that's perfect for munching anytime. Tastes just like the traditional teatime snack.",
            "benefits": "Protein Rich, Satisfying Snack, No Cholesterol",
            "ingredients": "Gram Flour, Salt, Chilli Powder, Curry Leaves, Soda, Oil for Frying",
            "shelf_life": "30 days from date of manufacture",
            "storage": "Store in an airtight container to maintain crispness.",
            "variants": [
                {"weight": "250g", "price": 100},
                {"weight": "500g", "price": 180},
                {"weight": "1kg", "price": 350}
            ]
        },
    ]
    
    # Combine admin products with default products
    all_products = admin_products + products
    
    return render_template("snacks.html", products=all_products, cart_count=cart_count)

# API route to get product details
@app.route("/product/<int:product_id>/<category>")
def get_product_details(product_id, category):
    all_products = []
    
    if category == 'veg':
        all_products = [
        {
            "id": 1, "name": "Gongura Pickle", "image": "/static/images/Gongura.jpg",
            "description": "Traditional Andhra-style Gongura pickle made from fresh sorrel leaves.",
            "benefits": "Rich in Iron, Vitamins C & K", "ingredients": "Gongura Leaves, Red Chilli, Salt, Garlic",
            "variants": [{"weight": "250g", "price": 220}, {"weight": "500g", "price": 400}, {"weight": "1kg", "price": 750}]
        },
        {
            "id": 2, "name": "Lemon Pickle", "image": "/static/images/Lemon pickel.jpg",
            "description": "Zesty lemon pickle made with fresh lemons marinated in spices.",
            "benefits": "Rich in Vitamin C, Antioxidants", "ingredients": "Fresh Lemons, Red Chilli, Salt, Fenugreek",
            "variants": [{"weight": "250g", "price": 180}, {"weight": "500g", "price": 320}, {"weight": "1kg", "price": 600}]
        },
        {
            "id": 3, "name": "Mango Pickle", "image": "/static/images/MangoPickel.jpg",
            "description": "Authentic Rayalaseema-style mango pickle from raw mangoes.",
            "benefits": "Rich in Vitamins A, C & E", "ingredients": "Raw Mangoes, Red Chilli, Salt, Fenugreek",
            "variants": [{"weight": "250g", "price": 200}, {"weight": "500g", "price": 360}, {"weight": "1kg", "price": 680}]
        },
        {
            "id": 4, "name": "Tomato Pickle", "image": "/static/images/Tomato pickle.jpg",
            "description": "Delicious tomato pickle made from ripe, juicy tomatoes.",
            "benefits": "Rich in Lycopene, Vitamin C", "ingredients": "Fresh Tomatoes, Red Chilli, Garlic, Ginger",
            "variants": [{"weight": "250g", "price": 170}, {"weight": "500g", "price": 300}, {"weight": "1kg", "price": 550}]
        },
        {
            "id": 5, "name": "Bitter Gourd Pickle", "image": "/static/images/kakarakayapickle_1_1.jpg",
            "description": "Unique bitter gourd pickle that transforms bitterness into delicacy.",
            "benefits": "Controls Blood Sugar, Purifies Blood", "ingredients": "Bitter Gourd, Red Chilli, Tamarind, Jaggery",
            "variants": [{"weight": "250g", "price": 190}, {"weight": "500g", "price": 340}, {"weight": "1kg", "price": 650}]
        },
    ]
    elif category == 'nonveg':
        all_products = [
        {
            "id": 1, "name": "Chicken Boneless Pickle", "image": "/static/images/chicken-boneless-pickle.jpg",
            "description": "Premium boneless chicken pickle made from tender chicken pieces.",
            "benefits": "High Protein, Rich in B Vitamins", "ingredients": "Chicken, Red Chilli, Garam Masala, Curry Leaves",
            "variants": [{"weight": "250g", "price": 380}, {"weight": "500g", "price": 700}, {"weight": "1kg", "price": 1300}]
        },
        {
            "id": 2, "name": "Fish Pickle", "image": "/static/images/fish pickle.JPG",
            "description": "Traditional fish pickle made from fresh sea fish.",
            "benefits": "High in Omega-3, Calcium", "ingredients": "Fish, Red Chilli, Turmeric, Coconut Oil",
            "variants": [{"weight": "250g", "price": 350}, {"weight": "500g", "price": 650}, {"weight": "1kg", "price": 1200}]
        },
        {
            "id": 3, "name": "Mutton Pickle", "image": "/static/images/mutton pickle.jpg",
            "description": "Rich and flavorful mutton pickle made from tender mutton.",
            "benefits": "High Protein, Iron, Zinc", "ingredients": "Mutton, Red Chilli, Garam Masala, Mustard Oil",
            "variants": [{"weight": "250g", "price": 420}, {"weight": "500g", "price": 800}, {"weight": "1kg", "price": 1500}]
        },
        {
            "id": 4, "name": "Gongura Chicken Pickle", "image": "/static/images/gongurachicken.jpg",
            "description": "Signature dish combining gongura with tender chicken.",
            "benefits": "High Protein, Vitamin C, Iron", "ingredients": "Chicken, Gongura Leaves, Red Chilli, Sesame Oil",
            "variants": [{"weight": "250g", "price": 390}, {"weight": "500g", "price": 720}, {"weight": "1kg", "price": 1350}]
        },
        {
            "id": 5, "name": "Prawns Gongura Pickle", "image": "/static/images/prawns_gongura.jpg",
            "description": "Exquisite prawns pickle with gongura - a coastal specialty.",
            "benefits": "High Protein, Omega-3, Selenium", "ingredients": "Prawns, Gongura, Red Chilli, Coconut Oil",
            "variants": [{"weight": "250g", "price": 410}, {"weight": "500g", "price": 760}, {"weight": "1kg", "price": 1400}]
        },
        {
            "id": 6, "name": "Gongura Mutton Pickle", "image": "/static/images/GonguraMutton-1.jpg",
            "description": "Premium mutton pickle with gongura - a royal delicacy.",
            "benefits": "High Protein, Iron, B Vitamins", "ingredients": "Mutton, Gongura, Red Chilli, Sesame Oil",
            "variants": [{"weight": "250g", "price": 430}, {"weight": "500g", "price": 820}, {"weight": "1kg", "price": 1550}]
        },
    ]
    elif category == 'snacks':
        all_products = [
        {
            "id": 1, "name": "Ariselu", "image": "/static/images/ariselu-side_2x_99b04b77-a741-48f1-b272-36f7a775f780.jpg",
            "description": "Traditional Telugu sweet made during Sankranti festival. Soft, melt-in-your-mouth rice flour laddoos with the perfect blend of sweetness.",
            "benefits": "Energy Boost, Easy to Digest, Traditional Delicacy", "ingredients": "Rice Flour, Jaggery, Ghee, Cashew Nuts, Cardamom",
            "shelf_life": "15 days from date of manufacture", "storage": "Store in an airtight container. Keep away from moisture.",
            "variants": [{"weight": "250g", "price": 120}, {"weight": "500g", "price": 220}, {"weight": "1kg", "price": 400}]
        },
        {
            "id": 2, "name": "Aam Papad", "image": "/static/images/Aam-Papad.jpg",
            "description": "Delicious mango papad made from ripe mango pulp. Thin, chewy, and full of natural mango flavor.",
            "benefits": "Natural Fruit Content, Vitamin A, Energy Source", "ingredients": "Mango Pulp, Sugar, Citric Acid",
            "shelf_life": "6 months from date of manufacture", "storage": "Store in a cool, dry place. Avoid humidity.",
            "variants": [{"weight": "250g", "price": 100}, {"weight": "500g", "price": 180}, {"weight": "1kg", "price": 350}]
        },
        {
            "id": 3, "name": "Boondhi Acchu", "image": "/static/images/Boondhi Acchu.jpg",
            "description": "Crispy boondi snack with a spicy twist. Perfectly round boondi fried to golden perfection.",
            "benefits": "Instant Energy, Protein from Besan", "ingredients": "Gram Flour, Salt, Curry Leaves, Spices",
            "shelf_life": "30 days from date of manufacture", "storage": "Store in an airtight container to maintain crunchiness.",
            "variants": [{"weight": "250g", "price": 90}, {"weight": "500g", "price": 160}, {"weight": "1kg", "price": 300}]
        },
        {
            "id": 4, "name": "Boondi Laddu", "image": "/static/images/boondi-laddu-665537.jpg",
            "description": "Classic Indian sweet - soft and fragrant boondi laddoos. Each ladoo is hand-rolled to perfection.",
            "benefits": "Good Source of Protein, Energy Boosting", "ingredients": "Gram Flour, Sugar, Ghee, Cardamom",
            "shelf_life": "15 days from date of manufacture", "storage": "Store in an airtight container in a cool place.",
            "variants": [{"weight": "250g", "price": 150}, {"weight": "500g", "price": 280}, {"weight": "1kg", "price": 500}]
        },
        {
            "id": 5, "name": "Dry Fruit Laddu", "image": "/static/images/Dry fruit laddo.jpg",
            "description": "Premium dry fruit laddos loaded with cashews, almonds, and raisins. A luxurious sweet that's nutritious.",
            "benefits": "Rich in Omega-3, Vitamin E, Calcium", "ingredients": "Almonds, Cashews, Dates, Ghee, Jaggery",
            "shelf_life": "30 days from date of manufacture", "storage": "Refrigerate for longer shelf life. Bring to room temperature before consuming.",
            "variants": [{"weight": "250g", "price": 180}, {"weight": "500g", "price": 340}, {"weight": "1kg", "price": 650}]
        },
        {
            "id": 6, "name": "Sunnundalu", "image": "/static/images/Sunnundalu.jpg",
            "description": "Traditional Andhra sweet made with rava and jaggery. Heart-shaped laddoos for festivals.",
            "benefits": "Good Source of Iron, Provides Energy", "ingredients": "Semolina, Jaggery, Ghee, Cardamom",
            "shelf_life": "15 days from date of manufacture", "storage": "Store in an airtight container.",
            "variants": [{"weight": "250g", "price": 160}, {"weight": "500g", "price": 300}, {"weight": "1kg", "price": 550}]
        },
        {
            "id": 7, "name": "Rava Laddu", "image": "/static/images/rava-ladoo-featured.jpg",
            "description": "Soft and moist rava laddoos with coconut and ghee. Perfect for tea-time snacking.",
            "benefits": "Provides Energy, Healthy Fats", "ingredients": "Semolina, Coconut, Sugar, Ghee",
            "shelf_life": "15 days from date of manufacture", "storage": "Store in an airtight container.",
            "variants": [{"weight": "250g", "price": 140}, {"weight": "500g", "price": 260}, {"weight": "1kg", "price": 480}]
        },
        {
            "id": 8, "name": "Chekka Pakodi", "image": "/static/images/Chekka Pakodi.jpg",
            "description": "Crispy gram flour pakodis with chopped vegetables. Perfect monsoon snack.",
            "benefits": "High Protein, Fiber, Satisfying Crunch", "ingredients": "Gram Flour, Vegetables, Curry Leaves, Spices",
            "shelf_life": "7 days from date of manufacture", "storage": "Store in an airtight container. Best consumed fresh.",
            "variants": [{"weight": "250g", "price": 110}, {"weight": "500g", "price": 200}, {"weight": "1kg", "price": 380}]
        },
        {
            "id": 9, "name": "Kara Boondi", "image": "/static/images/Kara-Boondi-4.jpg",
            "description": "Spicy boondi - crispy gram flour pearls with chutney. Popular savory snack.",
            "benefits": "Protein Rich, Satisfying Snack", "ingredients": "Gram Flour, Chilli Powder, Curry Leaves",
            "shelf_life": "30 days from date of manufacture", "storage": "Store in an airtight container to maintain crispness.",
            "variants": [{"weight": "250g", "price": 100}, {"weight": "500g", "price": 180}, {"weight": "1kg", "price": 350}]
        },
    ]
    
    # Find the selected product
    selected_product = None
    for p in all_products:
        if p['id'] == product_id:
            selected_product = p
            break
    
    if not selected_product:
        return {"error": "Product not found"}, 404
    
    # Get related products (same category, excluding current product)
    related_products = [p for p in all_products if p['id'] != product_id][:4]
    
    return {
        "product": selected_product,
        "related_products": related_products
    }

@app.route("/add_to_cart", methods=['POST'])
@login_required
def add_to_cart():
    product_name = request.form.get('product_name')
    weight = request.form.get('weight', '250g')
    price = int(request.form.get('price'))
    image = request.form.get('image', '')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO cart (user_id, product_name, weight, price, image) VALUES (?, ?, ?, ?, ?)",
             (current_user.id, product_name, weight, price, image))
    conn.commit()
    conn.close()
    
    flash(f'{product_name} ({weight}) added to cart!', 'success')
    return redirect(request.referrer or url_for('home'))

@app.route("/cart")
@login_required
def cart():
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, product_name, weight, price, image FROM cart WHERE user_id = ?", (current_user.id,))
    cart_items = c.fetchall()
    
    total = sum(item[3] for item in cart_items)
    
    # Get available coupons
    c.execute("SELECT * FROM coupons")
    coupons = c.fetchall()
    
    # Get user addresses
    c.execute("SELECT * FROM addresses WHERE user_id = ?", (current_user.id,))
    addresses = c.fetchall()
    
    # Check first order
    c.execute("SELECT is_first_order FROM users WHERE id = ?", (current_user.id,))
    is_first_order = c.fetchone()[0]
    
    discount = 0
    if is_first_order:
        discount = int(total * 30 / 100)
    elif total > 1000:
        discount = int(total * 20 / 100)
    
    # Get cart count
    cart_count = len(cart_items)
    
    # Calculate delivery date (3 days from now)
    delivery_date = (datetime.now() + timedelta(days=3)).strftime('%a, %d %b')
    
    conn.close()
    
    return render_template("cart.html", cart_items=cart_items, total=total, coupons=coupons, 
                         addresses=addresses, is_first_order=is_first_order, discount=discount, 
                         cart_count=cart_count, delivery_date=delivery_date)

@app.route("/remove_from_cart/<int:cart_id>")
@login_required
def remove_from_cart(cart_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (cart_id, current_user.id))
    conn.commit()
    conn.close()
    
    flash('Item removed from cart', 'success')
    return redirect(url_for('cart'))

@app.route("/checkout", methods=['GET', 'POST'])
@login_required
def checkout():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute("SELECT id, product_name, weight, price, image FROM cart WHERE user_id = ?", (current_user.id,))
    cart_items = c.fetchall()
    
    if not cart_items:
        flash('Your cart is empty', 'error')
        return redirect(url_for('home'))
    
    total = sum(item[3] for item in cart_items)
    
    # Get addresses
    c.execute("SELECT * FROM addresses WHERE user_id = ?", (current_user.id,))
    addresses = c.fetchall()
    
    # Check for first order discount (30%)
    c.execute("SELECT is_first_order FROM users WHERE id = ?", (current_user.id,))
    is_first_order = c.fetchone()[0]
    
    discount = 0
    coupon_discount = 0
    
    if request.method == 'POST':
        address_id = request.form.get('address_id')
        coupon_code = request.form.get('coupon', '').strip().upper()
        payment_method = request.form.get('payment_method', 'COD')
        
        # Validate address
        if not address_id:
            flash('Please add an address first', 'error')
            conn.close()
            return redirect(url_for('checkout'))
        
        # Validate payment method
        if not payment_method:
            flash('Please select a payment method', 'error')
            conn.close()
            return redirect(url_for('checkout'))
        
        # Apply coupon if provided
        if coupon_code:
            c.execute("SELECT discount_percent, min_amount FROM coupons WHERE code = ?", (coupon_code,))
            coupon = c.fetchone()
            if coupon and total >= coupon[1]:
                coupon_discount = int(total * coupon[0] / 100)
        
        # First order discount (30%)
        if is_first_order:
            discount = int(total * 30 / 100)
        
        # Order above 1000 (20% - if not first order)
        elif total > 1000:
            discount = int(total * 20 / 100)
        
        final_amount = total - discount - coupon_discount
        
        # Save order with detailed items (product_name, weight, price)
        items_details = []
        for item in cart_items:
            items_details.append(f"{item[1]}: {item[2]} - ₹{item[3]}")
        items_str = " | ".join(items_details)
        
        c.execute("""INSERT INTO orders (user_id, address_id, items, total_amount, discount_applied, final_amount, payment_method) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (current_user.id, address_id, items_str, total, discount + coupon_discount, final_amount, payment_method))
        
        # Update first order status
        if is_first_order:
            c.execute("UPDATE users SET is_first_order = 0 WHERE id = ?", (current_user.id,))
        
        # Clear cart
        c.execute("DELETE FROM cart WHERE user_id = ?", (current_user.id,))
        conn.commit()
        conn.close()
        
        return redirect(url_for('success'))
    
    conn.close()
    return render_template("checkout.html", cart_items=cart_items, total=total, 
                          is_first_order=is_first_order, discount=discount, addresses=addresses)

@app.route("/success")
@login_required
def success():
    return render_template("success.html")

@app.route("/profile")
@login_required
def profile():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Get user info
    c.execute("SELECT name, email, is_first_order FROM users WHERE id = ?", (current_user.id,))
    user_info = c.fetchone()
    
    # Get orders
    c.execute("""SELECT o.id, o.items, o.total_amount, o.discount_applied, 
                o.final_amount, o.order_date, o.status, a.full_name, a.address, a.city, a.pincode, o.payment_method
                FROM orders o 
                LEFT JOIN addresses a ON o.address_id = a.id
                WHERE o.user_id = ? 
                ORDER BY o.order_date DESC""", (current_user.id,))
    orders = c.fetchall()
    
    # Get coupons
    c.execute("SELECT * FROM coupons")
    coupons = c.fetchall()
    
    # Get addresses
    c.execute("SELECT * FROM addresses WHERE user_id = ?", (current_user.id,))
    addresses = c.fetchall()
    
    conn.close()
    
    return render_template("profile.html", user_info=user_info, orders=orders, 
                         coupons=coupons, addresses=addresses)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# Contact form submission
@app.route("/submit_contact", methods=['POST'])
def submit_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    # In a real app, you'd save this to database or send email
    flash('Thank you for contacting us! We will get back to you soon.', 'success')
    return redirect(url_for('contact'))

if __name__ == "__main__":
    app.run(debug=True)

