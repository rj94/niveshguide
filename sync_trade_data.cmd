@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_trade_data.ps1" %*
