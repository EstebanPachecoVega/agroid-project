@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
start "AgroID Chat" /min .venv\Scripts\python.exe -m streamlit run agroid/chat_app.py --server.headless true --server.address localhost --server.port 8502 --browser.gatherUsageStats false
start "AgroID Dashboard" /min .venv\Scripts\python.exe -m streamlit run agroid/dashboard/app.py --server.headless true --server.address localhost --server.port 8501 --browser.gatherUsageStats false
timeout /t 7 /nobreak >nul
start "" http://localhost:8502
start "" http://localhost:8501
