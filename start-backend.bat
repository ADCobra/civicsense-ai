@echo off
cd /d "%~dp0"
echo Starting CivicSense API on http://localhost:8000
echo.
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
) else (
    python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
)
pause
