"""
Simple script to run the Flask server with proper network configuration
"""
from app import app
import sys

if __name__ == '__main__':
    print("=" * 50)
    print("Educational Management System")
    print("=" * 50)
    print("\nStarting server...")
    print("Server will be accessible at:")
    print("  - http://localhost:5000")
    print("  - http://127.0.0.1:5000")
    print("  - http://10.195.233.1:5000 (if on same network)")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 50)
    print()
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError starting server: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure port 5000 is not used by another application")
        print("2. Check Windows Firewall settings")
        print("3. Try running as Administrator")
        sys.exit(1)


