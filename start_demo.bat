@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set OLLAMA_MODEL=gemma2:2b
set LOCAL_ONLY=1
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:5001/demo"
python relay_server.py
pause
