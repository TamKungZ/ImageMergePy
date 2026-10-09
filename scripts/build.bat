@echo off
setlocal

pushd "%~dp0.."
if errorlevel 1 exit /b 1

set IMAGEMERGE_ONEFILE=
set IMAGEMERGE_ONEFILE_STRICT=
set IMAGEMERGE_BINARY_ONLY=
set IMAGEMERGE_WINDOWS_BOTH=1

python scripts\build_nuitka.py
if errorlevel 1 (
    popd
    exit /b 1
)

echo Build complete.
popd
