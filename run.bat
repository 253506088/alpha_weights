@echo off
chcp 65001 >nul
echo ========================================
echo   中国基金实时监控 Web 应用
echo ========================================
echo.

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python，请先安装 Python 3.8 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✓ Python 环境正常
echo.

echo [2/3] 安装/更新依赖包...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖包安装失败
    pause
    exit /b 1
)
echo ✓ 依赖包安装完成
echo.

echo [3/3] 启动应用...
echo.
echo ========================================
echo 应用已启动！
echo 请在浏览器中访问: http://localhost:5000
echo 按 Ctrl+C 停止应用
echo ========================================
echo.

python app.py

pause
