@echo off
setlocal

python build_nuitka.py
if errorlevel 1 exit /b 1

echo Build complete.
