#!/usr/bin/env python3
"""
Setup script for PDF Toolkit
Creates virtual environment, installs dependencies, and verifies installation
"""
import subprocess
import sys
import os
from pathlib import Path
import venv

def run_command(cmd, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def setup_project():
    """Setup PDF Toolkit project"""
    
    print("=" * 60)
    print("PDF Toolkit - Setup Script")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    venv_dir = base_dir / "venv"
    
    # Check if Python is available
    success, stdout, stderr = run_command("python --version")
    if not success:
        print("❌ Error: Python is not installed or not in PATH")
        print("Please install Python 3.8+ from https://python.org")
        sys.exit(1)
    
    python_version = stdout.strip().split()[-1]
    print(f"✅ Python version: {python_version}")
    
    # Check if virtual environment exists
    if venv_dir.exists():
        print("✅ Virtual environment already exists")
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        print("🔧 Creating virtual environment...")
        venv.create(venv_dir, with_pip=True)
        print("✅ Virtual environment created")
        python_exe = venv_dir / "Scripts" / "python.exe"
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    requirements_file = base_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ Error: requirements.txt not found")
        sys.exit(1)
    
    success, stdout, stderr = run_command(f"{python_exe} -m pip install --upgrade pip")
    if not success:
        print("⚠️  Warning: Could not upgrade pip")
    
    success, stdout, stderr = run_command(
        f"{python_exe} -m pip install -r {requirements_file}",
        cwd=base_dir
    )
    
    if not success:
        print("❌ Error installing dependencies:")
        print(stderr)
        sys.exit(1)
    
    print("✅ Dependencies installed successfully")
    
    # Create storage directories
    print("\n📁 Creating storage directories...")
    (base_dir / "storage" / "uploads").mkdir(parents=True, exist_ok=True)
    (base_dir / "storage" / "outputs").mkdir(parents=True, exist_ok=True)
    print("✅ Storage directories created")
    
    print("\n" + "=" * 60)
    print("✅ Setup completed successfully!")
    print("=" * 60)
    print("\nTo start the application, run: start.bat")
    print("Or manually: python backend/main.py")
    
    return True

if __name__ == "__main__":
    setup_project()