@echo off
echo Stopping Spark Java processes...
taskkill /F /IM java.exe 2>nul
if %errorlevel% == 0 (
    echo Java processes stopped.
) else (
    echo No Java processes found.
)
