import sqlite3
from werkzeug.security import check_password_hash

# Check admin account
conn = sqlite3.connect('database.db')
c = conn.cursor()

print("=" * 50)
print("ADMIN ACCOUNT VERIFICATION")
print("=" * 50)

c.execute("SELECT id, name, email, password, is_admin FROM users WHERE email = 'admin@homemade.com'")
admin = c.fetchone()

if admin:
    print("[OK] Admin account found!")
    print(f"  ID: {admin[0]}")
    print(f"  Name: {admin[1]}")
    print(f"  Email: {admin[2]}")
    print(f"  is_admin: {admin[4]}")
    
    # Test password
    password_valid = check_password_hash(admin[3], 'admin123')
    print(f"  Password 'admin123' valid: {password_valid}")
    
    if admin[4] == 1 and password_valid:
        print("\n[OK] Admin account is properly configured!")
        print("\nLogin with:")
        print("  Email: admin@homemade.com")
        print("  Password: admin123")
    else:
        print("\n[ERROR] Admin account has issues")
else:
    print("[ERROR] Admin account not found!")
    print("\nCreating admin account...")
    from werkzeug.security import generate_password_hash
    admin_password = generate_password_hash('admin123')
    c.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)",
             ('Admin', 'admin@homemade.com', admin_password, 1))
    conn.commit()
    print("[OK] Admin account created!")

print("\n" + "=" * 50)
print("ALL USERS IN DATABASE")
print("=" * 50)
c.execute("SELECT id, name, email, is_admin FROM users")
users = c.fetchall()
for user in users:
    print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Admin: {user[3]}")

conn.close()
