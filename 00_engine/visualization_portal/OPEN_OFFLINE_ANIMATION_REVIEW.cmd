@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_portal.ps1"
start "" "http://127.0.0.1:8765/00_engine/visualization_portal/#/runs/2026-08-18-cc-animation-p0-offline-review-v1"
endlocal
