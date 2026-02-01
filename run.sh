#!/bin/bash

echo "========================================"
echo "  中国基金实时监控 Web 应用"
echo "========================================"
echo ""

# 检查 Python 环境
echo "[1/3] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python 3.8 或更高版本"
    exit 1
fi
python3 --version
echo "✓ Python 环境正常"
echo ""

# 安装依赖
echo "[2/3] 安装/更新依赖包..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误: 依赖包安装失败"
    exit 1
fi
echo "✓ 依赖包安装完成"
echo ""

# 启动应用
echo "[3/3] 启动应用..."
echo ""
echo "========================================"
echo "应用已启动！"
echo "请在浏览器中访问: http://localhost:5000"
echo "按 Ctrl+C 停止应用"
echo "========================================"
echo ""

python3 app.py
