"""
Build script for creating executable with PyInstaller (WITH console window)
Run: python build_exe_console.py
This version shows console output for debugging.
"""

import PyInstaller.__main__
import os
import shutil

# Clean previous builds
print("Cleaning previous builds...")
for folder in ['build', 'dist', '__pycache__']:
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f"  Removed {folder}/")

# Remove old spec file if exists
if os.path.exists('app.spec'):
    os.remove('app.spec')
    print("  Removed app.spec")

print("\nBuilding executable with PyInstaller (console version)...\n")

# PyInstaller arguments
args = [
    'app.py',                    # Main script
    '--name=정치편향무드등',      # Executable name
    '--onefile',                 # Single executable file
    '--console',                 # Show console window (for debugging)
    '--add-data=templates;templates',  # Include templates folder
    '--add-data=progressive.json;.',   # Include keyword files
    '--add-data=conservative.json;.',
    '--add-data=progressive.xlsx;.',
    '--add-data=conservative.xlsx;.',
    '--hidden-import=flask',     # Ensure Flask is included
    '--hidden-import=werkzeug',
    '--hidden-import=requests',
    '--hidden-import=bs4',
    '--hidden-import=openpyxl',
    '--hidden-import=serial',
    '--hidden-import=serial.tools.list_ports',
    '--collect-all=flask',       # Collect all Flask data
    '--collect-all=werkzeug',
    '--collect-all=bs4',
    '--collect-all=openpyxl',
]

try:
    PyInstaller.__main__.run(args)
    print("\n" + "="*50)
    print("Build completed successfully!")
    print("="*50)
    print("\nExecutable location: dist/정치편향무드등.exe")
    print("\nThis version shows console output for debugging.")
except Exception as e:
    print(f"\nError building executable: {e}")
    import traceback
    traceback.print_exc()

