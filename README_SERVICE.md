# SELLFLOW Server - Windows Service

## Install as Windows Service

Run **install_service.bat** as Administrator. The server will:
- Start automatically when Windows starts
- Run in the background
- Auto-restart if it crashes

## Manage the Service

```
nssm stop SELLFLOW      - Stop the server
nssm start SELLFLOW     - Start the server
nssm restart SELLFLOW   - Restart the server
nssm remove SELLFLOW    - Uninstall the service
```

## Access

Once installed, the server runs at: **http://localhost:8000**

## Requirements

- Administrator rights to install service
- Python virtual environment (.venv) already created
