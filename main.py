"""
DR.Xmail — main entry point
Run the Streamlit dashboard:
    python main.py
(or) streamlit run drxmail/ui/app.py
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    ui = os.path.join(os.path.dirname(__file__), "drxmail", "ui", "app.py")
    sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", ui]))
