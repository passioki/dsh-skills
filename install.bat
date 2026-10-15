@echo off
REM ============================================================
REM  dsh-skills : install / sync wrapper
REM  Why this file exists:
REM    1) .ps1 may be blocked by the PowerShell execution policy
REM       (Unsigned / RemoteSigned) -> we pass -ExecutionPolicy Bypass
REM    2) double-click friendly
REM  Usage:  install.bat            (junction mode, default)
REM          install.bat -Copy      (copy mode)
REM          install.bat -WhatIf    (dry run)
REM ============================================================
chcp 65001 >nul
setlocal

set "PS=powershell"
where pwsh >nul 2>nul && set "PS=pwsh"

%PS% -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [FAILED] exit code = %RC%
) else (
  echo [OK] done.
)
pause
exit /b %RC%
