@echo off
chcp 65001 >nul
title Alpha Signal - 一键更新网页AI报告
echo.
echo  ============================================
echo    正在生成最新的 AI 晨报和5维度选股分析...
echo    这通常需要 2-3 分钟，请耐心等待。
echo  ============================================
echo.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

:: 1. 运行日常AI新闻分析
echo [1/3] 正在运行日常AI晨报 (DeepSeek + Gemini)...
python run_daily.py --no-email

:: 2. 运行5维度选股分析
echo.
echo [2/3] 正在运行5维度深度选股分析...
python full_analysis.py

:: 3. 复制数据并推送到GitHub
echo.
echo [3/3] 正在将最新数据推送到网站...
copy /Y latest_data.json docs\data\latest.json
for /f "delims=" %%a in ('dir /b /o-d full_analysis_*.json') do (
    copy /Y "%%a" docs\data\analysis.json
    goto :done_copy
)
:done_copy

git add docs/data/latest.json docs/data/analysis.json
git commit -m "Manual update AI data from local"
git push origin main

echo.
echo  ============================================
echo    更新成功！
echo    请等待1-2分钟后刷新网页：
echo    https://Mikey-SI.github.io/-/
echo  ============================================
pause
