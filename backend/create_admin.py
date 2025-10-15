#!/usr/bin/env python3
"""Script to create an admin user."""

from database.database import SessionLocal, engine, Base
from admin.auth import create_admin_user

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Create database session
db = SessionLocal()

try:
    # Create admin user
    admin = create_admin_user(
        db=db,
        username="admin@gmail.com",
        password="654123",
        email="admin@gmail.com",
        full_name="Admin User",
        is_superuser=True
    )

    print("✅ Admin user created successfully!")
    print(f"Username: {admin.username}")
    print(f"Email: {admin.email}")
    print(f"Full Name: {admin.full_name}")
    print(f"Is Superuser: {admin.is_superuser}")
    print("\nYou can now login with:")
    print(f"  Email: admin@gmail.com")
    print(f"  Password: 654123")

except ValueError as e:
    print(f"❌ Error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
