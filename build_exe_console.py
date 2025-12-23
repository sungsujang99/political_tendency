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
        try:
            shutil.rmtree(folder)
            print(f"  Removed {folder}/")
        except PermissionError:
            print(f"  Warning: Could not remove {folder}/ (file may be in use)")
            print(f"           Please close any programs using files in {folder}/")
            print(f"           PyInstaller will try to overwrite files...")
        except Exception as e:
            print(f"  Warning: Could not remove {folder}/: {e}")

# Remove old spec file if exists
if os.path.exists('app.spec'):
    try:
        os.remove('app.spec')
        print("  Removed app.spec")
    except PermissionError:
        print("  Warning: Could not remove app.spec (file may be in use)")
    except Exception as e:
        print(f"  Warning: Could not remove app.spec: {e}")

print("\nBuilding executable with PyInstaller (console version)...\n")

# PyInstaller arguments
args = [
    'app.py',                    # Main script
    '--name=정치편향무드등',      # Executable name
    '--onefile',                 # Single executable file
    '--console',                 # Show console window (for debugging)
    '--add-data=templates;templates',  # Include templates folder
    '--add-data=progressive.xlsx;.',   # Include keyword files
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


