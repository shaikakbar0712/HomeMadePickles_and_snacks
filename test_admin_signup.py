import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

print("=" * 60)
print("TESTING ADMIN SIGNUP FUNCTIONALITY")
print("=" * 60)

# Test admin registration key
ADMIN_KEY = "ADMIN2024SECRET"
print(f"\n[OK] Admin Registration Key: {ADMIN_KEY}")

# Check database structure
conn = sqlite3.connect('database.db')
c = conn.cursor()

print("\n" + "=" * 60)
print("CURRENT ADMIN ACCOUNTS")
print("=" * 60)

c.execute("SELECT id, name, email, is_admin FROM users WHERE is_admin = 1")
admins = c.fetchall()

if admins:
    for admin in admins:
        print(f"ID: {admin[0]}, Name: {admin[1]}, Email: {admin[2]}")
else:
    print("No admin accounts found")

print("\n" + "=" * 60)
print("HOW TO CREATE NEW ADMIN ACCOUNT")
print("=" * 60)
print("1. Go to: http://127.0.0.1:5000/admin/signup")
print("2. Fill in the form:")
print("   - Full Name: Your Name")
print("   - Admin Email: youremail@example.com")
print("   - Password: Your secure password")
print("   - Admin Registration Key: ADMIN2024SECRET")
print("3. Click 'Create Admin Account'")
print("4. Login at: http://127.0.0.1:5000/admin/login")

print("\n" + "=" * 60)
print("EXISTING ADMIN LOGIN")
print("=" * 60)
print("Email: admin@homemade.com")
print("Password: admin123")

conn.close()
