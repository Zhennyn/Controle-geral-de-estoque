#!/usr/bin/env python
import os
from inventory_app import create_app, db
from inventory_app.models import User

def check_database():
    app = create_app()
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
            # Get database info
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print("=" * 50)
            print("DATABASE STATUS")
            print("=" * 50)
            print(f"Database File: estoque.db")
            print(f"File Exists: {os.path.exists('estoque.db')}")
            print(f"Total Tables: {len(tables)}")
            print()
            print("Tables:")
            for table in sorted(tables):
                cols = len(inspector.get_columns(table))
                print(f"  [OK] {table:<25} ({cols} columns)")
            
            print()
            print("Users:")
            admin = User.query.filter_by(username='admin').first()
            total_users = User.query.count()
            print(f"  Admin user: {'YES' if admin else 'NO - MISSING'}")
            print(f"  Total users: {total_users}")
            
            if os.path.exists('estoque.db'):
                db_size = os.path.getsize('estoque.db') / 1024
                print(f"\nDatabase Size: {db_size:.1f} KB")
            
            print("\nStatus: READY")
        finally:
            db.session.remove()

if __name__ == '__main__':
    check_database()
