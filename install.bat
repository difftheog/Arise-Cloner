@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Arise Cloner - Setup
cd /d "%~dp0"

rem Python release offered for download when no usable Python is installed.
set "PY_VERSION=3.13.16"
set "VENV_PY=.venv\Scripts\python.exe"
set "FROM_START="
set "PROBE_FILE=%TEMP%\arise-python-probe.txt"
if /i "%~1"=="--from-start" set "FROM_START=1"

echo ==========================================
echo  Arise Cloner - setup
echo ==========================================
echo.

echo [1/4] Looking for Python 3.10 or newer...
call :find_python
if defined PY_CMD goto python_ready

echo.
echo Python 3.10 or newer was not found on this computer.
echo.
echo This script can download the official Python installer from python.org
echo and open it for you. You will see the normal Python Setup window and
echo click "Install Now" yourself. Nothing is installed silently.
echo.
choice /c YN /n /m "Download and open the Python installer now? [Y/N] "
if errorlevel 2 goto python_declined

call :download_python
if errorlevel 1 goto fail

echo.
echo Opening the Python installer...
echo   - Click "Install Now" in the Python Setup window.
echo   - Tip: tick "Add python.exe to PATH" at the bottom of that window first.
echo   - When it says "Setup was successful", click Close.
echo This window continues once the installer has been closed.
echo.
start "" /wait "%DL_EXE%"

del /q "%DL_EXE%" >nul 2>nul
rmdir "%DL_DIR%" >nul 2>nul

call :refresh_path
call :find_python
if defined PY_CMD goto python_ready

echo.
echo ERROR: Python still was not found after the installer closed.
echo   - If you cancelled the installer, run install.bat again.
echo   - If the installation finished, close this window and run install.bat again
echo     so Windows picks up the new Python.
goto fail

:python_declined
echo.
echo Python is required. Install Python 3.10 or newer from
echo   https://www.python.org/downloads/windows/
echo then run install.bat again.
goto fail

:python_ready
del /q "%PROBE_FILE%" >nul 2>nul
echo Found:
%PY_CMD% --version
if errorlevel 1 goto python_broken
echo.

echo [2/4] Checking pip...
%PY_CMD% -m pip --version >nul 2>nul
if not errorlevel 1 goto pip_ok
echo pip was not found. Trying to set it up with ensurepip...
%PY_CMD% -m ensurepip --upgrade
%PY_CMD% -m pip --version >nul 2>nul
if errorlevel 1 goto pip_missing
:pip_ok
%PY_CMD% -m pip --version
echo.

echo [3/4] Preparing the virtual environment (.venv)...
if not exist "%VENV_PY%" goto venv_create
"%VENV_PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto venv_ready
echo The existing .venv is broken or uses an unsupported Python. Recreating it...
rmdir /s /q ".venv"
if exist ".venv" goto venv_failed
:venv_create
%PY_CMD% -m venv .venv
if errorlevel 1 goto venv_failed
if not exist "%VENV_PY%" goto venv_failed
:venv_ready
echo Virtual environment ready.
echo.

echo [4/4] Installing dependencies...
"%VENV_PY%" -m pip install --upgrade pip --disable-pip-version-check
if errorlevel 1 echo WARNING: Could not upgrade pip. Continuing with the current version.

rem Older versions of this tool used discord.py 1.7.3 and the "asyncio" backport.
rem discord.py shares the "discord" package with discord.py-self, so it has to go.
set "PIP_FORCE="
"%VENV_PY%" -m pip show discord.py >nul 2>nul
if errorlevel 1 goto no_old_discord
echo Removing the old discord.py from .venv...
"%VENV_PY%" -m pip uninstall -y discord.py
set "PIP_FORCE=--force-reinstall"
:no_old_discord
"%VENV_PY%" -m pip show asyncio >nul 2>nul
if not errorlevel 1 "%VENV_PY%" -m pip uninstall -y asyncio

"%VENV_PY%" -m pip install %PIP_FORCE% -r requirements.txt --disable-pip-version-check
if errorlevel 1 goto deps_failed

echo.
echo Checking the installation...
"%VENV_PY%" src\check_env.py
if errorlevel 1 goto deps_failed

echo.
echo ==========================================
echo  Setup complete. Run start.bat to launch.
echo ==========================================
if not defined FROM_START pause
endlocal
exit /b 0

:python_broken
echo.
echo ERROR: Python was found but could not be run.
goto fail

:pip_missing
echo.
echo ERROR: pip is not available for this Python installation.
echo Re-run the Python installer (Modify) and make sure "pip" is selected.
goto fail

:venv_failed
echo.
echo ERROR: Could not create the .venv folder.
echo Close anything that may be using it (start.bat, a terminal, an editor),
echo delete the .venv folder by hand if it exists, and run install.bat again.
goto fail

:deps_failed
echo.
echo ERROR: Installing the dependencies failed.
echo   - Check your internet connection, proxy and firewall.
echo   - Run install.bat again; the message above shows what pip complained about.
goto fail

:fail
echo.
echo Setup did not finish. See the messages above.
if not defined FROM_START pause
endlocal
exit /b 1


:find_python
set "PY_CMD="
call :probe py -3.13
call :probe py -3.12
call :probe py -3.11
call :probe py -3.10
call :probe py -3
call :probe python
call :probe "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
call :probe "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
call :probe "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
call :probe "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
call :probe "%ProgramFiles%\Python313\python.exe"
call :probe "%ProgramFiles%\Python312\python.exe"
call :probe "%ProgramFiles%\Python311\python.exe"
call :probe "%ProgramFiles%\Python310\python.exe"
exit /b 0

:probe
rem The exit code alone isn't trusted: the Python install manager's "py" can
rem report success when no runtime is installed. The command has to actually
rem print 1 from inside a real interpreter.
if defined PY_CMD exit /b 0
set "PROBE="
%* -c "import sys; print(int(sys.version_info >= (3, 10)))" >"%PROBE_FILE%" 2>nul
set /p PROBE=<"%PROBE_FILE%"
if "%PROBE%"=="1" set "PY_CMD=%*"
exit /b 0

:refresh_path
rem A freshly installed Python is not on this window's PATH yet, so reload it.
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%P;%PATH%"
exit /b 0

:download_python
set "PY_ARCH=amd64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "PY_ARCH=arm64"
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "PY_ARCH=arm64"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PY_ARCH=win32"

set "PY_FILE=python-%PY_VERSION%-%PY_ARCH%.exe"
if "%PY_ARCH%"=="win32" set "PY_FILE=python-%PY_VERSION%.exe"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/%PY_FILE%"
set "DL_DIR=%TEMP%\arise-python-setup"
set "DL_EXE=%DL_DIR%\python-setup.exe"

if not exist "%DL_DIR%" mkdir "%DL_DIR%"
if exist "%DL_EXE%" del /q "%DL_EXE%"

echo.
echo Downloading %PY_FILE% from python.org...
echo   %PY_URL%
where curl.exe >nul 2>nul
if errorlevel 1 goto download_ps
curl.exe -L --fail --retry 3 --connect-timeout 20 -o "%DL_EXE%" "%PY_URL%"
if not errorlevel 1 goto download_check
echo curl failed, trying PowerShell instead...
if exist "%DL_EXE%" del /q "%DL_EXE%"

:download_ps
set "ARISE_URL=%PY_URL%"
set "ARISE_OUT=%DL_EXE%"
powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri $env:ARISE_URL -OutFile $env:ARISE_OUT } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 goto download_failed

:download_check
if not exist "%DL_EXE%" goto download_failed
for %%F in ("%DL_EXE%") do set "DL_SIZE=%%~zF"
if %DL_SIZE% LSS 1000000 goto download_failed

echo Verifying that the installer is signed by the Python Software Foundation...
set "ARISE_OUT=%DL_EXE%"
powershell -NoProfile -Command "$s = Get-AuthenticodeSignature -LiteralPath $env:ARISE_OUT; if ($s.Status -eq 'Valid' -and $s.SignerCertificate.Subject -like '*Python Software Foundation*') { exit 0 } else { Write-Host ('Signature check failed: ' + $s.Status); exit 1 }"
if errorlevel 1 goto download_untrusted
echo Signature OK.
exit /b 0

:download_untrusted
echo.
echo ERROR: The downloaded file is not a valid Python Software Foundation installer.
echo It has been deleted and will not be run. Download Python manually from
echo   https://www.python.org/downloads/windows/
del /q "%DL_EXE%" >nul 2>nul
exit /b 1

:download_failed
echo.
echo ERROR: Could not download the Python installer.
echo   - Check your internet connection, proxy and firewall.
echo   - Or download Python manually from https://www.python.org/downloads/windows/
echo     and run install.bat again.
if exist "%DL_EXE%" del /q "%DL_EXE%"
exit /b 1
