"""
Build script for creating executable with PyInstaller
Run: python build_exe.py
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

print("\nBuilding executable with PyInstaller...\n")

# PyInstaller arguments
args = [
    'app.py',                    # Main script
    '--name=정치편향무드등',      # Executable name
    '--onefile',                 # Single executable file
    '--windowed',                # No console window (use --noconsole for Windows)
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
    '--icon=NONE',               # No icon (can add .ico file later)
]

try:
    PyInstaller.__main__.run(args)
    print("\n" + "="*50)
    print("Build completed successfully!")
    print("="*50)
    print("\nExecutable location: dist/정치편향무드등.exe")
    print("\nTo distribute:")
    print("  1. Copy the .exe file from dist/ folder")
    print("  2. Make sure templates/ folder and keyword files are in the same directory")
    print("     OR they will be bundled inside the executable")
    print("\nNote: First run may take a moment to extract bundled files.")
except Exception as e:
    print(f"\nError building executable: {e}")
    import traceback
    traceback.print_exc()


