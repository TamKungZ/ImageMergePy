@echo off
setlocal

set IMAGEMERGE_ONEFILE=
set IMAGEMERGE_ONEFILE_STRICT=
set IMAGEMERGE_BINARY_ONLY=
set IMAGEMERGE_WINDOWS_BOTH=1

python build_nuitka.py
if errorlevel 1 exit /b 1

echo Build complete.
