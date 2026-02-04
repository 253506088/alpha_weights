import os
import sys
import shutil
import platform
import subprocess

def main():
    # 确保在脚本所在目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("正在安装/根据需要更新打包工具 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])

    print("\n正在清理旧的构建文件...")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # 清理 spec 文件
    for f in os.listdir("."):
        if f.endswith(".spec"):
            os.remove(f)

    print("\n开始打包 AlphaWeights...")
    
    # 根据系统判断分隔符
    system_platform = platform.system()
    separator = ";" if system_platform == "Windows" else ":"
    
    print(f"当前系统: {system_platform}, 使用分隔符: '{separator}'")

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--name", "AlphaWeights",
        "--add-data", f"templates{separator}templates",
        "app.py"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    print("\n打包完成！")
    print("请将 dist 文件夹下的可执行文件复制到任意目录即可运行。")
    print("首次运行会自动生成 data 目录和数据库文件。")

if __name__ == "__main__":
    main()
