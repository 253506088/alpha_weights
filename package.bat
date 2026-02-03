@echo off
setlocal
:: Ensure we are in the script's directory
cd /d "%~dp0"
:: Force UTF-8 encoding
chcp 65001 > nul

echo 正在安装打包工具 PyInstaller...
pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo 正在清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo.
echo 开始打包 AlphaWeights...

:: --noconfirm: 不确认覆盖
:: --onefile: 单文件模式
:: --add-data: 添加模板文件夹
:: --name: exe名称
:: 注意：这里去掉了可能导致问题的长注释

pyinstaller --noconfirm --onefile --name "AlphaWeights" ^
    --add-data "templates;templates" ^
    app.py

echo.
echo 打包完成！
echo.
echo 请将 dist 文件夹下的 AlphaWeights.exe 复制到任意目录即可运行。
echo 首次运行会自动生成 data 目录和数据库文件。
echo.
pause
