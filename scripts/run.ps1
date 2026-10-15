$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
