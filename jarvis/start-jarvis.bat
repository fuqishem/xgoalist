@echo off
cd /d "%~dp0"
if not exist config.json copy config.example.json config.json
:loop
node server.js
timeout /t 5 >nul
goto loop
