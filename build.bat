@echo off
echo ========================================
echo 정치편향무드등 실행 파일 빌드
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python을 먼저 설치해주세요: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python 설치 확인 완료
echo.

REM Install/upgrade PyInstaller
echo PyInstaller 설치 중...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo [오류] PyInstaller 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo 빌드 방법 선택:
echo  1. Spec 파일 사용 (권장)
echo  2. 콘솔 버전
echo  3. 윈도우 버전 (콘솔 없음)
echo.
set /p choice="선택 (1-3, 기본값: 1): "
if "%choice%"=="" set choice=1
if "%choice%"=="1" (
    echo.
    echo Spec 파일로 빌드 중...
    python build_exe_spec.py
) else if "%choice%"=="2" (
    echo.
    echo 콘솔 버전 빌드 중...
    python build_exe_console.py
) else (
    echo.
    echo 윈도우 버전 빌드 중...
    python build_exe.py
)

if errorlevel 1 (
    echo.
    echo [오류] 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 빌드 완료!
echo ========================================
echo.
echo 실행 파일 위치: dist\정치편향무드등.exe
echo.
pause

