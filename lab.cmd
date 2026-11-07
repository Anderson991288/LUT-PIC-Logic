@echo off
rem Run course scripts with the IPKISS (ipkiss3) Python; this machine has no system Python.
rem Usage (PowerShell or cmd):  .\lab design\m0_env\s1_check\check_env.py
rem Script paths are relative to the project root; lab.cmd switches to the root first, so it also works from other folders.
rem Python location: env var LAB_PYTHON if set, otherwise the default Luceda install.
rem Keep this file ASCII-only: cmd.exe parses .cmd files in the console code page, not UTF-8.
setlocal
if defined LAB_PYTHON (set "PY=%LAB_PYTHON%") else (set "PY=C:\Luceda\luceda_2026033\envs\ipkiss3\python.exe")
if not exist "%PY%" (
  echo IPKISS Python not found: %PY%
  echo Set LAB_PYTHON to the full path of python.exe in the ipkiss3 environment.
  exit /b 9009
)
pushd "%~dp0"
"%PY%" %*
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
