@echo off
title NSE Swing Trader
cd /d "%~dp0"

echo.
echo  ========================================
echo    NSE Swing Trader - Starting up...
echo  ========================================
echo.

echo  Checking dependencies...
pip install -r requirements.txt --quiet 2>nul

echo  Launching app in your browser...
echo  (Press Ctrl+C in this window to stop the server)
echo.

streamlit run app.py --server.headless false --browser.serverAddress localhost

pause
