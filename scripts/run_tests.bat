@echo off
echo ============================================
echo   SkillTwin AI - Run All Tests
echo ============================================
cd /d d:\QRFileTransfer\skilltwin-ai\backend
call venv\Scripts\activate
python -m pytest ..\tests\ -v --tb=short 2>&1
