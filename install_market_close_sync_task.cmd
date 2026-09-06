@echo off
set "TASK_NAME=TradeMarketCloseSync"
set "SYNC_CMD=%~dp0sync_trade_data.cmd"
schtasks /Create /TN "%TASK_NAME%" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:55 /TR "\"%SYNC_CMD%\"" /F
echo Installed %TASK_NAME% to sync spreadsheet data after market close at 16:55, Monday-Friday.
