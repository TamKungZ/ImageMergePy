@echo off
setlocal

pyinstaller --noconfirm --clean --onefile --windowed --name ImageMerge --add-data "assets;assets" --add-data "locales;locales" MainApp.py
if errorlevel 1 exit /b 1

echo Build complete: dist\ImageMerge.exe
