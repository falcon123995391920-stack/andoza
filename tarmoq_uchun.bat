@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Idoradagi boshqa kompyuterlar ochishi uchun. PAROLNI O'ZGARTIRING!
set OBJ_PASSWORD=ParolniOzgartiring123
python -m pip install -q -r requirements.txt
echo Boshqa kompyuterlardan: http://BU-KOMPYUTER-IP:8000   (login: istalgan, parol yuqoridagi)
python server.py --host 0.0.0.0 --no-browser
pause
