@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Arise Cloner
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "VENV_PY=.venv\Scripts\python.exe"
set "CHECK_LOG=%TEMP%\arise-env-check.txt"
set "TRIED_SETUP="

:check
if not exist "%VENV_PY%" goto not_ready

"%VENV_PY%" src\check_env.py >"%CHECK_LOG%" 2>&1
if errorlevel 1 goto env_problem

type "%CHECK_LOG%"
"%VENV_PY%" --version
echo.
"%VENV_PY%" src\main.py
set "EXIT_CODE=%errorlevel%"

echo.
if not "%EXIT_CODE%"=="0" echo Arise Cloner stopped with error code %EXIT_CODE%.
echo Program exited.
pause
endlocal & exit /b %EXIT_CODE%

:not_ready
echo The Python environment (.venv) has not been set up yet.
goto offer_setup

:env_problem
echo The Python environment has a problem:
type "%CHECK_LOG%"
goto offer_setup

:offer_setup
if defined TRIED_SETUP goto setup_failed
echo.
choice /c YN /n /m "Run the setup (install.bat) now to fix this? [Y/N] "
if errorlevel 2 goto declined
set "TRIED_SETUP=1"
echo.
call install.bat --from-start
echo.
goto check

:declined
echo.
echo Run install.bat when you are ready, then start this again.
pause
endlocal
exit /b 1

:setup_failed
echo.
echo The environment is still not usable after running the setup.
echo Check the messages above, then run install.bat again.
pause
endlocal
exit /b 1