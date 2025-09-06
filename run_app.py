# run_app.py
"""
Simple launcher for the Streamlit Customer Support Agent
Run this file to start the web interface: python run_app.py
"""
import subprocess
import sys
import os

def main():
    print("🚀 Starting Langie Customer Support Agent...")
    print("📍 Web interface will open at: http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the server")
    
    try:
        # Run streamlit app
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Stopping Langie... Goodbye!")
    except FileNotFoundError:
        print("❌ Streamlit not found. Please install it with: pip install streamlit")
    except Exception as e:
        print(f"❌ Error starting app: {e}")

if __name__ == "__main__":
    main()
