@echo off
cd /d "%~dp0frontend"
echo Starting CivicSense frontend...
echo.
if not exist "node_modules" (
    echo First time: installing npm packages...
    call npm install
    echo.
)
call npm run dev
pause
