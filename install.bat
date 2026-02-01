@echo off
chcp 65001 >nul
echo ========================================
echo   依赖安装脚本
echo ========================================
echo.

echo 正在安装 Python 依赖包...
echo.

python -m pip install Flask==3.0.0
if %errorlevel% neq 0 (
    echo 安装 Flask 失败
    pause
    exit /b 1
)

python -m pip install APScheduler==3.10.4
if %errorlevel% neq 0 (
    echo 安装 APScheduler 失败
    pause
    exit /b 1
)

python -m pip install requests==2.31.0
if %errorlevel% neq 0 (
    echo 安装 requests 失败
    pause
    exit /b 1
)

python -m pip install SQLAlchemy==2.0.23
if %errorlevel% neq 0 (
    echo 安装 SQLAlchemy 失败
    pause
    exit /b 1
)

python -m pip install lxml==4.9.3
if %errorlevel% neq 0 (
    echo 安装 lxml 失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 依赖安装完成！
echo 现在可以运行 run.bat 启动应用
echo ========================================
echo.

pause
