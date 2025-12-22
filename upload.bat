@echo off
REM GitHub 快速上傳腳本 (Windows)

echo ========================================
echo GitHub 快速上傳工具
echo ========================================
echo.

REM 檢查 Git 是否已初始化
if not exist .git (
    echo 初始化 Git 儲存庫...
    git init
    echo.
)

REM 顯示當前狀態
echo 當前狀態:
git status
echo.

REM 添加所有檔案
echo 添加檔案...
git add .
echo.

REM 提交
set /p commit_msg="請輸入 commit 訊息: "
git commit -m "%commit_msg%"
echo.

REM 檢查是否已設定 remote
git remote -v | findstr origin >nul
if errorlevel 1 (
    echo.
    echo 尚未設定遠端儲存庫！
    echo.
    set /p repo_url="請輸入 GitHub 儲存庫 URL: "
    git remote add origin %repo_url%
    git branch -M main
    echo.
)

REM 推送
echo 推送到 GitHub...
git push -u origin main

echo.
echo ========================================
echo 上傳完成！
echo ========================================
pause
