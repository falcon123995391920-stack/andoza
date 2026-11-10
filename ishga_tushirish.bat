@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
%PY% -m pip install -q -r requirements.txt
echo Sayt ochilmoqda. Toxtatish: shu oynani yoping.
%PY% server.py
pause
