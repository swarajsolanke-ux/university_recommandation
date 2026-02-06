import sys
import os
import sqlite3
from unittest.mock import MagicMock

# Create a mock for dotenv
mock_dotenv = MagicMock()
sys.modules["dotenv"] = mock_dotenv

# Set environment variable for DB name
os.environ["DATABASE_NAME"] = "University.db"

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.application_service import ApplicationService

DB_PATH = '/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander_copy/University.db'

def verify():
    # Only run if DB exists
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Get a university with majors
    print("Finding a university...")
    cursor.execute("SELECT id, name FROM universities WHERE is_active=1 LIMIT 1")
    uni = cursor.fetchone()
    if not uni:
        print("No active universities found.")
        return
    uni_id, uni_name = uni
    print(f"Selected University: {uni_name} (ID: {uni_id})")

    # 2. Get majors for this university (Simulating the Fixed API logic)
    print("\nFetching majors (API Logic)...")
    # Using the exact logic I implemented in the fix
    cursor.execute("""
        SELECT id, major_name
        FROM university_majors
        WHERE university_id = ?
        ORDER BY major_name ASC
    """, (uni_id,))
    majors = cursor.fetchall()
    
    if not majors:
        print("No majors found for this university.")
        return

    print(f"Found {len(majors)} majors.")
    for m in majors:
        print(f" - ID: {m[0]}, Name: {m[1]}")

    # 3. Pick a major
    if len(majors) > 1:
        target_major = majors[1] # Pick the second one
    else:
        target_major = majors[0]
        
    major_id = target_major[0]
    major_name = target_major[1]
    print(f"\nSelected Major to Apply: {major_name} (ID: {major_id})")

    # 4. Get a user
    cursor.execute("SELECT id FROM users LIMIT 1")
    user = cursor.fetchone()
    if not user:
        # Create dummy user if none exists
        try:
            cursor.execute("INSERT INTO users (email, password_hash) VALUES ('test@example.com', 'hash')")
            user_id = cursor.lastrowid
            conn.commit()
        except:
             # Fallback if users table structure is different
             print("Could not create user, trying to find any.")
             pass
        user_id = 1 
    else:
        user_id = user[0]
    
    print(f"Using User ID: {user_id}")

    conn.close()

    # 5. Create Application (Using Service directly)
    print("\nCreating Application...")
    
    # We need to clean up existing application for this combo to avoid "already exists" error
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM applications WHERE user_id=? AND university_id=? AND major_id=?", (user_id, uni_id, major_id))
    conn.commit()
    conn.close()

    try:
        result = ApplicationService.create_application(
            user_id=user_id,
            university_id=uni_id,
            major_id=major_id,
            notes="Verification Test"
        )
        
        if "error" in result:
            print(f"Error creating application: {result['error']}")
            return

        app_id = result["application_id"]
        print(f"Application Created! ID: {app_id}")

        # 6. Verify Application Details
        print("\nVerifying Application Details...")
        details = ApplicationService.get_application_details(app_id)
        
        if not details:
            print("Failed to fetch application details.")
            return

        print(f"Application Major Name: {details['major_name']}")
        print(f"Expected Major Name: {major_name}")

        if details['major_name'] == major_name:
            print("\nSUCCESS: Major name matches!")
        else:
            print(f"\nFAILURE: Major name mismatch! Expected '{major_name}', got '{details['major_name']}'")
            
    except Exception as e:
        print(f"Exception during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
