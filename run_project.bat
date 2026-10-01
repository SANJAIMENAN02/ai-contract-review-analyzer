@echo off
REM Starts FastAPI and Streamlit in two separate windows (Windows).
cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    set "ACTIVATE=call venv\Scripts\activate.bat &&"
) else (
    set "ACTIVATE="
    echo [info] No venv\ folder found - using the Python on your PATH.
)

if not exist .env if exist .env.example copy .env.example .env >nul

start "FastAPI - port 8000" cmd /k "%ACTIVATE% uvicorn app.main:app --app-dir backend --port 8000 --reload"
timeout /t 3 /nobreak >nul
start "Streamlit - port 8501" cmd /k "%ACTIVATE% streamlit run streamlit_app/app.py"

echo.
echo FastAPI:   http://127.0.0.1:8000/docs
echo Streamlit: http://localhost:8501
