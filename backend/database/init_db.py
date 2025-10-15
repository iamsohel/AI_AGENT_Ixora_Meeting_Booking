"""Initialize database and create default admin user."""

import os
import sys
import warnings
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress bcrypt warnings
warnings.filterwarnings("ignore", message=".*bcrypt.*")

from dotenv import load_dotenv
from database.database import init_db, get_db_session
from admin.auth import create_admin_user

load_dotenv()


def main():
    """Initialize database and create default admin user."""
    print("=" * 60)
    print("Initializing Ixora AI Assistant Database")
    print("=" * 60)

    # Initialize database
    print("\n1. Creating database tables...")
    init_db()

    # Create default admin user
    print("\n2. Creating default admin user...")

    db = get_db_session()
    try:
        # Get credentials from environment or use defaults
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "changeme123")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@ixorasolution.com")

        try:
            admin = create_admin_user(
                db=db,
                username=admin_username,
                password=admin_password,
                email=admin_email,
                full_name="Ixora Administrator",
                is_superuser=True
            )

            print(f"✅ Admin user created successfully!")
            print(f"   Username: {admin.username}")
            print(f"   Email: {admin.email}")
            print(f"\n⚠️  IMPORTANT: Change the default password in production!")

        except ValueError as e:
            print(f"ℹ️  Admin user already exists: {admin_username}")
        except Exception as e:
            print(f"❌ Error creating admin user: {type(e).__name__}: {e}")

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Database initialization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
