"""
Build script using spec file for more control
Run: python build_exe_spec.py
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

print("\nBuilding executable using spec file...\n")

try:
    # Use the spec file for more control
    PyInstaller.__main__.run([
        '정치편향무드등.spec',
        '--clean',
        '--noconfirm',
    ])
    print("\n" + "="*50)
    print("Build completed successfully!")
    print("="*50)
    print("\nExecutable location: dist/정치편향무드등.exe")
    print("\nAll files are bundled inside the executable.")
except Exception as e:
    print(f"\nError building executable: {e}")
    import traceback
    traceback.print_exc()


