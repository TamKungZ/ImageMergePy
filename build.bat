@echo off
setlocal

set IMAGEMERGE_ONEFILE=
set IMAGEMERGE_ONEFILE_STRICT=
set IMAGEMERGE_BINARY_ONLY=

python build_nuitka.py
if errorlevel 1 exit /b 1

echo Build complete.
