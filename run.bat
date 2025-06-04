@echo off
cd /d %~dp0
set FLASK_APP=app.py
set FLASK_ENV=development
flask run
pause