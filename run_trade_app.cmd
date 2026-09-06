@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_trade_app.ps1" %*
