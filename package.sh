#!/bin/bash

# 确保脚本在当前目录执行
cd "$(dirname "$0")"

echo "正在安装打包工具 PyInstaller..."
pip3 install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""
echo "正在清理旧的构建文件..."
rm -rf build dist *.spec

echo ""
echo "开始打包 AlphaWeights..."

# --noconfirm: 不确认覆盖
# --onefile: 单文件模式
# --add-data: 添加模板文件夹 (注意 macOS/Linux 使用冒号 : 分隔)
# --name: 可执行文件名称

pyinstaller --noconfirm --onefile --name "AlphaWeights" \
    --add-data "templates:templates" \
    app.py

echo ""
echo "打包完成！"
echo ""
echo "请将 dist 文件夹下的 AlphaWeights (可执行文件) 复制到任意目录即可运行。"
echo "首次运行会自动生成 data 目录和数据库文件。"
echo ""
