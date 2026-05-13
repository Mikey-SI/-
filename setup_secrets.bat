@echo off
chcp 65001 >nul
title Alpha Signal - Setup GitHub Secrets
echo.
echo  ============================================
echo    Setting up GitHub Actions Secrets
echo  ============================================
echo.

set PATH=%PATH%;C:\Program Files\GitHub CLI
cd /d "%~dp0"

echo Setting DEEPSEEK_API_KEY...
gh secret set DEEPSEEK_API_KEY -b "sk-a16821d80dcd4ceebc995d150e37d5d9" -R Mikey-SI/-

echo Setting RESEND_API_KEY...
gh secret set RESEND_API_KEY -b "re_ALaDbJMg_6MBF69ANXTPgYScK4CVy14YN" -R Mikey-SI/-

echo Setting EMAIL_RECEIVER...
gh secret set EMAIL_RECEIVER -b "a2735559771@gmail.com" -R Mikey-SI/-

echo.
echo  Done! GitHub Actions will now send daily emails.
echo  Triggering first run...
gh workflow run daily_email.yml -R Mikey-SI/-

pause
