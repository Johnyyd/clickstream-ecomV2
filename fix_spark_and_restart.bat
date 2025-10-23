@echo off
echo ========================================
echo Fixing Spark File System Error
echo ========================================
echo.

echo Step 1: Cleaning up Spark temporary files...
python cleanup_spark_tmp.py

echo.
echo Step 2: Killing existing Python processes...
taskkill /F /IM python.exe /T 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    ^> Python processes stopped
) else (
    echo    ^> No Python processes to stop
)

echo.
echo Step 3: Waiting 2 seconds...
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo Fix Applied! Ready to restart server.
echo ========================================
echo.
echo NEXT STEPS:
echo 1. Run: python main.py
echo 2. Test ML analytics in browser
echo.
echo Press any key to exit...
pause >nul
