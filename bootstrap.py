#!/usr/bin/env python3
"""
Notivo Bootstrap
================
This script is the true entry point called by the C launcher.
It checks if all required Python packages are installed.
If not, it installs them automatically using pip, then launches app.py.

This script intentionally uses ONLY the Python standard library so it can
run even when third-party packages are not yet installed.
"""
import sys
import os
import subprocess

# Change to the script's directory so all relative paths work correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

REQUIREMENTS_FILE = "requirements.txt"

# Quick check: try importing the most critical packages
REQUIRED_IMPORTS = [
    ("PySide6", "PySide6"),
    ("sounddevice", "sounddevice"),
    ("soundfile", "soundfile"),
    ("numpy", "numpy"),
    ("faster_whisper", "faster-whisper"),
    ("torch", "torch"),
    ("requests", "requests"),
    ("markdown", "markdown"),
]

def check_packages():
    """Returns a list of package names that are missing."""
    missing = []
    for module_name, pip_name in REQUIRED_IMPORTS:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pip_name)
    return missing

def install_packages():
    """Install all requirements using pip."""
    print("=" * 60)
    print("  Notivo — First-time setup")
    print("  Installing required packages...")
    print("=" * 60)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE, "--quiet", "--break-system-packages"],
        check=False
    )
    if result.returncode != 0:
        print("\n[ERROR] Package installation failed.")
        print("Please run manually: pip install -r requirements.txt")
        input("\nPress Enter to exit...")
        sys.exit(1)
    print("\n  ✅ All packages installed successfully!")

def launch_app():
    """Replace this process with app.py."""
    os.execv(sys.executable, [sys.executable, "app.py"])

def main():
    missing = check_packages()
    if missing:
        print(f"\n[Notivo] Missing packages: {', '.join(missing)}")
        install_packages()
        # Re-check after install
        still_missing = check_packages()
        if still_missing:
            print(f"\n[ERROR] Could not install: {', '.join(still_missing)}")
            input("Press Enter to exit...")
            sys.exit(1)

    launch_app()

if __name__ == "__main__":
    main()
