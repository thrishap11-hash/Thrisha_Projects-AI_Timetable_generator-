"""
Database Migration Script
Adds notification_type column to existing Notification table
Run this once to update your database
"""

from app import app, db
from sqlalchemy import text

def migrate_database():
    with app.app_context():
        try:
            # Check if notification_type column exists
            result = db.session.execute(text("PRAGMA table_info(notification)"))
            columns = [row[1] for row in result]
            
            # Check and add notification_type column
            if 'notification_type' not in columns:
                print("Adding notification_type column to Notification table...")
                db.session.execute(text("""
                    ALTER TABLE notification 
                    ADD COLUMN notification_type VARCHAR(50) DEFAULT 'general'
                """))
                db.session.commit()
                
                db.session.execute(text("""
                    UPDATE notification 
                    SET notification_type = 'general' 
                    WHERE notification_type IS NULL
                """))
                db.session.commit()
                print("[OK] Added notification_type column")
            else:
                print("[OK] notification_type column already exists")
            
            # Check and add target_audience column
            if 'target_audience' not in columns:
                print("Adding target_audience column to Notification table...")
                db.session.execute(text("""
                    ALTER TABLE notification 
                    ADD COLUMN target_audience VARCHAR(20) DEFAULT 'all'
                """))
                db.session.commit()
                
                db.session.execute(text("""
                    UPDATE notification 
                    SET target_audience = 'all' 
                    WHERE target_audience IS NULL
                """))
                db.session.commit()
                print("[OK] Added target_audience column")
            else:
                print("[OK] target_audience column already exists")
            
            print("\n[SUCCESS] Database migration completed!")
            print("All notification columns are up to date.")
                
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            print("Trying alternative method...")
            
            # Alternative: Drop and recreate (WARNING: This will lose data!)
            try:
                response = input("Do you want to recreate the database? This will DELETE ALL DATA! (yes/no): ")
                if response.lower() == 'yes':
                    print("Dropping and recreating database...")
                    db.drop_all()
                    db.create_all()
                    print("[SUCCESS] Database recreated. You need to run init_sample_data.py again.")
                else:
                    print("Migration cancelled. Please backup your data first.")
            except:
                print("Could not complete migration. Please check your database manually.")

if __name__ == '__main__':
    migrate_database()

