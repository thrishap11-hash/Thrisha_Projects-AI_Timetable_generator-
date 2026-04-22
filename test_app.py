"""Quick test script to check if the app runs correctly"""
from app import app

if __name__ == '__main__':
    print("Testing Flask app...")
    print("If you see this, the app should work!")
    print("\nStarting server on http://localhost:5000")
    print("Press Ctrl+C to stop")
    app.run(debug=True, host='127.0.0.1', port=5000)


