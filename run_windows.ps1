# ARC-AGI-3 Human Skills — Windows PowerShell Launcher
# Run from: C:\Users\redga\projects\arc-human-skills

param(
    [string]$Mode = "menu",           # menu, train, benchmark, test
    [int]$MaxSessions = 0,            # 0 = infinite
    [int]$Duration = 30,              # minutes per session
    [string[]]$Domains = @("writing","reading","painting"),
    [switch]$Headless,
    [switch]$BenchmarkOnly
)

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  ARC-AGI-3 Human Skills Trainer - PowerShell" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python not found in PATH. Install from https://python.org"
    exit 1
}
Write-Host "Python: $($python.Source)" -ForegroundColor Green

# Check project
$projectRoot = Get-Location
if (-not (Test-Path "$projectRoot\arc_human_skills")) {
    Write-Error "Run from project root: C:\Users\redga\projects\arc-human-skills"
    exit 1
}

# Install deps
Write-Host "`nChecking dependencies..." -ForegroundColor Yellow
try {
    python -c "import pywinauto, pyautogui, cv2, numpy, requests, yaml, qdrant_client" 2>$null
    Write-Host "Dependencies OK" -ForegroundColor Green
} catch {
    Write-Host "Installing..." -ForegroundColor Yellow
    python -m pip install -e . | Out-Null
    Write-Host "Done" -ForegroundColor Green
}

# Test Paint
Write-Host "`nTesting Paint automation..." -ForegroundColor Yellow
$result = python -c "
import sys
sys.path.insert(0, '.')
from arc_human_skills.paint_automation import PaintController, IS_WINDOWS, PYAUTOGUI_AVAILABLE
print(f'IS_WINDOWS={IS_WINDOWS}')
print(f'PYAUTOGUI_AVAILABLE={PYAUTOGUI_AVAILABLE}')
if IS_WINDOWS and PYAUTOGUI_AVAILABLE:
    ctrl = PaintController()
    try:
        ctrl.launch()
        ctrl.setup_canvas(800, 600)
        print('PAINT_OK=True')
        ctrl.close()
    except Exception as e:
        print(f'PAINT_ERROR={e}')
        sys.exit(1)
else:
    print('PAINT_SKIP=Not Windows or pyautogui unavailable')
" 2>&1

if ($result -match "PAINT_ERROR") {
    Write-Error "Paint test failed:`n$result"
    Write-Host "Fixes:" -ForegroundColor Yellow
    Write-Host "  - Run PowerShell as Administrator"
    Write-Host "  - Check C:\Windows\System32\mspaint.exe"
    Write-Host "  - Disable screen recording/overlay software"
    exit 1
} elseif ($result -match "PAINT_OK") {
    Write-Host "Paint: READY" -ForegroundColor Green
} else {
    Write-Host "Paint: SKIPPED (Linux/WSL)" -ForegroundColor Yellow
}

# Test LocalAI
Write-Host "`nTesting LocalAI (EUREKAI:8080)..." -ForegroundColor Yellow
$localai = python -c "
import requests, sys
try:
    r = requests.get('http://192.168.1.47:8080/v1/models', timeout=10)
    models = r.json()
    count = len(models.get('data', []))
    print(f'LOCALAI_OK={count}')
    for m in models.get('data', [])[:5]:
        print(f'  MODEL={m.get(\"id\", m)}')
except Exception as e:
    print(f'LOCALAI_WARN={e}')
" 2>&1

if ($localai -match "LOCALAI_OK") {
    Write-Host "LocalAI: CONNECTED ($($matches['LOCALAI_OK']) models)" -ForegroundColor Green
    $localai | Select-String "MODEL=" | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
} else {
    Write-Warning "LocalAI not reachable - vision/transcription will fail"
    Write-Host "  Check EUREKAI (192.168.1.47) is on, port 8080 open" -ForegroundColor Yellow
}

# Execute mode
switch ($Mode) {
    "train" {
        Write-Host "`nStarting training..." -ForegroundColor Cyan
        $args = @(
            "-m", "arc_human_skills.trainer",
            "--max-sessions", $MaxSessions,
            "--duration", $Duration,
            "--domains", $Domains
        )
        if ($Headless) { $args += "--headless" }
        python @args
    }
    "benchmark" {
        Write-Host "`nRunning benchmark..." -ForegroundColor Cyan
        python -m arc_human_skills.benchmark
    }
    "test" {
        Write-Host "`nQuick headless test..." -ForegroundColor Cyan
        python -m arc_human_skills.trainer --headless --max-sessions 1 --duration 1
    }
    default {
        # Interactive menu
        Write-Host "`n Select Mode:" -ForegroundColor Cyan
        Write-Host "  1. Full Training (30 min, Ctrl+C to stop)" -ForegroundColor White
        Write-Host "  2. Writing Focus (20 min x 3 sessions)" -ForegroundColor White
        Write-Host "  3. Reading Focus (20 min x 3 sessions)" -ForegroundColor White
        Write-Host "  4. Painting Focus (30 min x 3 sessions)" -ForegroundColor White
        Write-Host "  5. Benchmark Only" -ForegroundColor White
        Write-Host "  6. Quick Headless Test" -ForegroundColor White
        Write-Host "  7. Custom" -ForegroundColor White
        
        $choice = Read-Host "Enter choice [1-7]"
        
        switch ($choice) {
            "1" { python -m arc_human_skills.trainer --max-sessions 0 --duration 30 }
            "2" { python -m arc_human_skills.trainer --max-sessions 3 --duration 20 --domains writing }
            "3" { python -m arc_human_skills.trainer --max-sessions 3 --duration 20 --domains reading }
            "4" { python -m arc_human_skills.trainer --max-sessions 3 --duration 30 --domains painting }
            "5" { python -m arc_human_skills.benchmark }
            "6" { python -m arc_human_skills.trainer --headless --max-sessions 1 --duration 1 }
            "7" {
                $sessions = Read-Host "Max sessions (0=infinite)" -Default "0"
                $dur = Read-Host "Minutes per session" -Default "30"
                $doms = Read-Host "Domains (space-separated)" -Default "writing reading painting"
                python -m arc_human_skills.trainer --max-sessions $sessions --duration $dur --domains $doms.Split(' ')
            }
            default { Write-Error "Invalid choice" }
        }
    }
}

Write-Host "`nDone. Check training_progress.json for results." -ForegroundColor Green