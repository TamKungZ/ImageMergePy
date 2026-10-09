@echo off
setlocal

pushd "%~dp0.."
if errorlevel 1 exit /b 1

python scripts\build_nuitka.py
if errorlevel 1 (
    popd
    exit /b 1
)

echo Build complete.
popd
