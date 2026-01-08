@echo off
REM Build script for History Clipboard Manager
REM Double-click this file to build the executable

echo ============================================================
echo History Clipboard Manager - Build Script
echo ============================================================
echo.

REM Check if UV is available
where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using UV to run build script...
    uv run python build_exe.py
) else (
    echo UV not found, using system Python...
    python build_exe.py
)

echo.
echo ============================================================
echo Build complete!
echo ============================================================
echo.
echo The executable is located at:
echo src\dist\history_clipboard_manager.exe
echo.
pause
