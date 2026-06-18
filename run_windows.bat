@echo off
REM ARC-AGI-3 Human Skills — Windows Launcher
REM Run this from C:\Users\redga\projects\arc-human-skills

echo =============================================
echo  ARC-AGI-3 Human Skills Trainer - Windows
echo =============================================
echo.

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Install from https://python.org or Microsoft Store
    pause
    exit /b 1
)

REM Check project directory
if not exist "arc_human_skills" (
    echo ERROR: Run from project root (C:\Users\redga\projects\arc-human-skills)
    pause
    exit /b 1
)

REM Check dependencies
echo Checking dependencies...
python -c "import pywinauto, pyautogui, cv2, numpy, requests, yaml, qdrant_client" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -e .
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Test Paint
echo.
echo Testing Paint automation...
python -c "
import sys
sys.path.insert(0, '.')
from arc_human_skills.paint_automation import PaintController, IS_WINDOWS, PYAUTOGUI_AVAILABLE
print(f'Windows: {IS_WINDOWS}')
print(f'pyautogui: {PYAUTOGUI_AVAILABLE}')
if IS_WINDOWS and PYAUTOGUI_AVAILABLE:
    ctrl = PaintController()
    try:
        ctrl.launch()
        ctrl.setup_canvas(800, 600)
        print('SUCCESS: Paint launched and canvas ready')
        ctrl.close()
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
else:
    print('SKIP: Not on Windows or pyautogui unavailable')
" 
if errorlevel 1 (
    echo.
    echo Paint test failed. Common fixes:
    echo  - Run as Administrator
    echo  - Check C:\Windows\System32\mspaint.exe exists
    echo  - Disable any screen recording/overlay software
    pause
    exit /b 1
)

REM Test LocalAI
echo.
echo Testing LocalAI connection (EUREKAI:8080)...
python -c "
import requests, sys
try:
    r = requests.get('http://192.168.1.47:8080/v1/models', timeout=10)
    models = r.json()
    print(f'LocalAI OK: {len(models.get(\"data\", []))} models')
    for m in models.get('data', [])[:5]:
        print(f'  - {m.get(\"id\", m)}')
except Exception as e:
    print(f'WARNING: LocalAI not reachable: {e}')
    print('  Check EUREKAI (192.168.1.47) is on and port 8080 open')
"

REM Menu
echo.
echo =============================================
echo  SELECT MODE
echo =============================================
echo 1. Full Training (30 min sessions, Ctrl+C to stop)
echo 2. Quick Test (1 session, headless)
echo 3. Benchmark Only
echo 4. Writing Only
echo 5. Reading Only
echo 6. Painting Only
echo 7. Custom Session
echo.
set /p choice="Enter choice [1-7]: "

if "%choice%"=="1" (
    echo Starting full training...
    python -m arc_human_skills.trainer --max-sessions 0 --duration 30
) else if "%choice%"=="2" (
    echo Quick headless test...
    python -m arc_human_skills.trainer --headless --max-sessions 1 --duration 1
) else if "%choice%"=="3" (
    echo Running benchmark...
    python -m arc_human_skills.benchmark
) else if "%choice%"=="4" (
    echo Writing practice...
    python -m arc_human_skills.trainer --max-sessions 3 --duration 20 --domains writing
) else if "%choice%"=="5" (
    echo Reading practice...
    python -m arc_human_skills.trainer --max-sessions 3 --duration 20 --domains reading
) else if "%choice%"=="6" (
    echo Painting practice...
    python -m arc_human_skills.trainer --max-sessions 3 --duration 30 --domains painting
) else if "%choice%"=="7" (
    set /p sessions="Max sessions (0=infinite): "
    set /p duration="Session duration minutes: "
    set /p domains="Domains (space-separated, e.g. writing reading): "
    python -m arc_human_skills.trainer --max-sessions %sessions% --duration %duration% --domains %domains%
) else (
    echo Invalid choice
)

echo.
echo Done. Check training_progress.json for results.
pause