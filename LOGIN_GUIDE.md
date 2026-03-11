# HomeMade Pickles - Login System

## Separate Login System for Customers and Admins

### Customer Login
- **URL**: http://127.0.0.1:5000/login
- **Purpose**: For customers to shop and place orders
- **Features**: 
  - Browse products
  - Add to cart
  - Place orders
  - View order history
  - Manage addresses

### Admin Login
- **URL**: http://127.0.0.1:5000/admin/login
- **Purpose**: For administrators to manage orders
- **Features**:
  - View all orders
  - Accept/Reject orders
  - Mark orders as delivered
  - View statistics (pending orders, total orders, revenue)

### Admin Signup
- **URL**: http://127.0.0.1:5000/admin/signup
- **Purpose**: For creating new admin accounts
- **Requires**: Admin Registration Key
- **Key**: ADMIN2024SECRET

---

## Default Admin Credentials
- **Email**: admin@homemade.com
- **Password**: admin123

## Admin Registration Key
- **Key**: ADMIN2024SECRET
- **Purpose**: Required to create new admin accounts
- **Note**: Change this key in app.py (line ~235) for security

---

## How to Use

### For Customers:
1. Go to homepage: http://127.0.0.1:5000/
2. Click "Customer Login" or go to /login
3. If new user, click "Sign up here" to create account
4. After login, browse products and shop

### For Admin:
1. Go to homepage: http://127.0.0.1:5000/
2. Click "Admin Login" or go to /admin/login
3. **New Admin?** Click "Sign up here" and use registration key: **ADMIN2024SECRET**
4. **Existing Admin?** Login with your credentials (default: admin@homemade.com / admin123)
5. Manage orders from the admin dashboard

---

## Security Features
- Customers cannot access admin panel
- Admins are redirected to admin login if they try customer login
- Passwords are hashed using werkzeug security
- Session-based authentication using Flask-Login

---

## Navigation Updates
- Homepage now shows both "Customer Login" and "Admin Login" buttons
- Customer login page has link to admin login
- Admin login page has link back to homepage
- Clear separation between customer and admin interfaces

---

## Testing
Run the application:
```bash
python app.py
```

Then visit:
- Customer Login: http://127.0.0.1:5000/login
- Customer Signup: http://127.0.0.1:5000/signup
- Admin Login: http://127.0.0.1:5000/admin/login
- Admin Signup: http://127.0.0.1:5000/admin/signup (Use key: ADMIN2024SECRET)
