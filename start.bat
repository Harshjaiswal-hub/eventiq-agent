@echo off
REM ============================================================
REM  EventIQ Agent — Windows Startup Helper
REM  Launches the Python HTTP server on http://localhost:3000
REM ============================================================

title EventIQ Agent — Starting...

echo.
echo  =====================================================
echo   EventIQ Agent ^| Smart Event Analytics
echo   http://localhost:3000
echo  =====================================================
echo.

REM ── 1. Locate a Python interpreter ──────────────────────────
SET PYTHON_EXE=

REM Try plain "python" first (added to PATH by most installers)
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET PYTHON_EXE=python
    GOTO :found_python
)

REM Try "python3" (common on machines with multiple versions)
python3 --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET PYTHON_EXE=python3
    GOTO :found_python
)

REM Try the known user-level install path for Python 3.11
IF EXIST "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    SET PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
    GOTO :found_python
)

REM Try the Windows Store launcher
py --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET PYTHON_EXE=py
    GOTO :found_python
)

REM ── Python not found ─────────────────────────────────────────
echo  [ERROR] Python was not found on this machine.
echo.
echo  To fix this:
echo    1. Download Python 3.11+ from https://www.python.org/downloads/
echo    2. During installation, check "Add Python to PATH".
echo    3. Re-open this terminal and run start.bat again.
echo.
pause
EXIT /B 1

:found_python
echo  [OK] Python interpreter found: %PYTHON_EXE%

REM ── 2. Check whether port 3000 is already in use ─────────────
netstat -ano | findstr ":3000 " | findstr "LISTENING" >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo.
    echo  [WARNING] Port 3000 is already occupied.
    echo.
    echo  Another process (possibly a previous server instance) is
    echo  listening on port 3000. Options:
    echo.
    echo    A) Open http://localhost:3000 in your browser — the
    echo       existing server may already be running correctly.
    echo.
    echo    B) To find and stop the process manually:
    echo         netstat -ano ^| findstr ":3000"
    echo       Note the PID shown, then run:
    echo         taskkill /PID ^<pid^> /F
    echo       Then re-run start.bat.
    echo.
    echo  Press any key to attempt starting anyway (this may fail).
    pause >nul
    echo.
)

REM ── 3. Verify server.py is present ───────────────────────────
IF NOT EXIST "%~dp0server.py" (
    echo  [ERROR] server.py not found in %~dp0
    echo  Make sure you are running start.bat from the project root.
    echo.
    pause
    EXIT /B 1
)

REM ── 4. Launch the server ─────────────────────────────────────
echo  [INFO] Starting EventIQ Agent server...
echo  [INFO] Open your browser at: http://localhost:3000
echo  [INFO] Press Ctrl+C to stop the server.
echo.

title EventIQ Agent — Running on http://localhost:3000
"%PYTHON_EXE%" "%~dp0server.py"

REM ── If the server exits, pause so the window stays open ──────
echo.
echo  [INFO] Server stopped.
pause
