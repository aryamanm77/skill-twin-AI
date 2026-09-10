@echo off
echo ============================================
echo   SkillTwin AI - Backend Server
echo ============================================
cd /d d:\QRFileTransfer\skilltwin-ai\backend
call venv\Scripts\activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
