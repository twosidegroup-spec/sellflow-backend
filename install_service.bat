@echo off
echo Installing SELLFLOW as Windows Service...
echo.

echo Checking if NSSM is installed...
where nssm >nul 2>&1
if %errorlevel% neq 0 (
    echo NSSM not found. Downloading...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'nssm.zip'; Expand-Archive -Path 'nssm.zip' -DestinationPath '.' -Force}"
    
    echo Moving nssm.exe to PATH...
    copy nssm-2.24\win64\nssm.exe .\ >nul
    rmdir /s /q nssm-2.24
    rmdir /s /q __MACOSX
)

echo Installing SELLFLOW service...
nssm install SELLFLOW "%cd%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo Setting service to auto-start...
nssm set SELLFLOW Start SERVICE_AUTO_START

echo Starting service...
nssm start SELLFLOW

echo.
echo SELLFLOW server installed and started as a Windows service!
echo Access: http://localhost:8000
echo.
echo Commands:
echo   nssm stop SELLFLOW     - Stop the server
echo   nssm start SELLFLOW    - Start the server
echo   nssm restart SELLFLOW  - Restart the server
echo   nssm remove SELLFLOW   - Uninstall the service
echo.
pause
