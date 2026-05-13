@echo off
chcp 65001 >nul
title Alpha Signal - Run Strategy (private)
echo.
echo  ============================================
echo    Running private strategy locally...
echo    1) compute signal via yfinance
echo    2) encrypt rules + signal into payload.enc
echo    3) push only the encrypted payload to GitHub
echo  ============================================
echo.

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

python strategy_runner.py
if errorlevel 1 (
  echo [error] strategy_runner failed
  pause
  exit /b 1
)

git add docs/data/strategy_payload.enc
git diff --staged --quiet
if errorlevel 1 (
  git commit -m "Update encrypted strategy payload"
  git push origin main
) else (
  echo [info] no payload changes to commit
)

echo.
echo  Done. Open https://mikey-si.github.io/-/ -> 🔐 My Strategy -> enter password.
pause
