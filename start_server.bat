@echo off
cd /d "%~dp0"
echo Starting SELLFLOW Dashboard...
echo Server will be available at http://localhost:8000
echo Press Ctrl+C to stop
echo.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
