@echo off
REM Text-to-Video Nature Generator - Windows Startup Script

echo ========================================
echo 🌊 Text-to-Video Nature Generator
echo ========================================

REM Check Python version
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Create necessary directories
echo Creating directories...
if not exist "outputs\videos" mkdir outputs\videos
if not exist "outputs\audio" mkdir outputs\audio
if not exist "outputs\frames" mkdir outputs\frames
if not exist "outputs\logs" mkdir outputs\logs
if not exist "models" mkdir models
if not exist "presets" mkdir presets

REM Check for FFmpeg
where ffmpeg >nul 2>nul
if %errorlevel% equ 0 (
    echo FFmpeg found
) else (
    echo WARNING: FFmpeg not found. Please install FFmpeg for video processing.
    echo Download from: https://ffmpeg.org/download.html
)

echo.
echo ========================================
echo Choose startup mode:
echo ========================================
echo 1) Start FastAPI backend only (port 8000)
echo 2) Start Gradio UI only (port 7860)
echo 3) Start both services
echo 4) Interactive Python shell
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" goto start_backend
if "%choice%"=="2" goto start_gradio
if "%choice%"=="3" goto start_both
if "%choice%"=="4" goto start_python
goto invalid_choice

:start_backend
echo.
echo Starting FastAPI backend...
echo    API docs: http://localhost:8000/docs
echo.
cd backend
python main.py
goto end

:start_gradio
echo.
echo Starting Gradio UI...
echo    UI: http://localhost:7860
echo.
python frontend\app.py
goto end

:start_both
echo.
echo Starting both services...
echo.

REM Start backend in background
cd backend
start "Backend" cmd /c "python main.py"
cd ..

timeout /t 3 /nobreak >nul

echo Starting Gradio UI...
python frontend\app.py
goto end

:start_python
echo.
echo Starting Python interactive shell...
python
goto end

:invalid_choice
echo Invalid choice
pause
exit /b 1

:end
pause
