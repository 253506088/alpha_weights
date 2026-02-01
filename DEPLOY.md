# 中国基金实时监控 Web 应用 - 部署说明

## 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows、Linux 或 macOS
- **内存**: 最小 512MB
- **磁盘空间**: 最小 100MB

## 安装步骤

### Windows 用户

1. **安装 Python**
   - 访问 https://www.python.org/downloads/
   - 下载并安装 Python 3.8 或更高版本
   - 安装时勾选 "Add Python to PATH"

2. **克隆或下载项目**
   ```bash
   git clone https://github.com/253506088/alpha_weights.git
   cd alpha_weights
   ```

3. **启动应用**
   - 双击 `run.bat` 文件
   - 脚本会自动安装依赖并启动应用

4. **访问应用**
   - 在浏览器中打开: http://localhost:5000

### Linux/macOS 用户

1. **安装 Python**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install python3 python3-pip

   # macOS (使用 Homebrew)
   brew install python3
   ```

2. **克隆或下载项目**
   ```bash
   git clone https://github.com/253506088/alpha_weights.git
   cd alpha_weights
   ```

3. **启动应用**
   ```bash
   bash run.sh
   ```

   或手动执行：
   ```bash
   pip3 install -r requirements.txt
   python3 app.py
   ```

4. **访问应用**
   - 在浏览器中打开: http://localhost:5000

## 手动安装依赖

如果启动脚本无法自动安装依赖，可以手动安装：

```bash
# Windows
pip install Flask==3.0.0 APScheduler==3.10.4 requests==2.31.0 SQLAlchemy==2.0.23 lxml==4.9.3

# Linux/macOS
pip3 install Flask==3.0.0 APScheduler==3.10.4 requests==2.31.0 SQLAlchemy==2.0.23 lxml==4.9.3
```

## 目录结构

```
alpha_weights/
├── app.py                 # Flask 应用主程序
├── requirements.txt       # Python 依赖列表
├── run.bat               # Windows 启动脚本
├── run.sh                # Linux/macOS 启动脚本
├── README.md             # 项目说明
├── DEPLOY.md             # 本文档（部署说明）
├── models.py             # 数据库模型
├── api.py                # 数据获取 API
├── scheduler.py          # 定时任务
├── static/               # 静态文件目录
│   └── css/
│       └── style.css     # 样式表
├── templates/            # HTML 模板目录
│   └── index.html        # 主页面
├── data/                 # 数据目录（首次运行后自动创建）
│   └── fund_monitor.db   # SQLite 数据库
└── LICENSE               # 许可证
```

## 使用说明

### 1. 添加基金

1. 在主页面顶部的输入框中输入 6 位基金代码（如 `000001`）
2. 点击"添加基金"按钮
3. 系统会自动从东方财富获取该基金的前十大重仓股信息
4. 基金将添加到监控列表中

### 2. 查看实时数据

- **预估涨跌幅**: 显示基金股票部分的预估涨跌幅
- **更新时间**: 显示最近一次数据更新的时间
- **自动更新**: 系统每 5 分钟自动更新一次数据

### 3. 查看走势图

点击基金卡片上的"查看走势"按钮，会打开新窗口显示该基金今日的分时走势图。

### 4. 查看持仓详情

点击"查看持仓"按钮，可以查看该基金的前十大重仓股列表及其持仓占比。

### 5. 删除基金

点击"删除"按钮可以移除该基金，相关的历史数据也会被删除。

## 常见问题

### Q: 数据更新不准确？

A: 本应用仅计算基金股票部分的预估涨跌幅，不包括债券、现金等其他资产。这代表股票资产的波动，不等于最终净值波动。

### Q: 首次添加基金后显示"等待数据..."？

A: 这是正常的。系统需要等待下一个 5 分钟定时任务执行后才会生成数据。你也可以手动重启应用来立即触发一次更新。

### Q: 无法获取基金信息？

A: 请检查：
1. 基金代码是否正确（6 位数字）
2. 网络连接是否正常
3. 东方财富网站是否可以访问

### Q: 无法获取股票行情？

A: 请检查：
1. 网络连接是否正常
2. 新浪财经 API 是否可以访问
3. 是否因频繁请求被限流（建议不要手动刷新过快）

### Q: 应用无法启动？

A: 请检查：
1. Python 版本是否为 3.8 或更高
2. 依赖包是否已正确安装
3. 端口 5000 是否被其他程序占用

### Q: 如何修改端口？

A: 编辑 `app.py` 文件，修改最后一行：
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```
将 `port=5000` 改为你想要的端口号。

## 数据说明

### 数据来源

- **基金持仓数据**: 东方财富 (eastmoney.com)
- **股票实时行情**: 新浪财经 (finance.sina.com.cn)

### 数据频率

- 数据更新频率：每 5 分钟一次
- 历史数据保留：数据库中永久保存

### 数据准确性

- 股票行情为实时数据，但可能有几秒到几分钟的延迟
- 基金持仓数据为最新披露的季报/半年报数据
- 预估涨跌幅仅基于前十大重仓股计算，未考虑其他持仓

## 安全与隐私

- 本应用为本地运行，无需上传任何数据
- 所有数据存储在本地 SQLite 数据库中
- 仅使用公开的免费 API，无需任何注册或密钥

## 许可证

Apache License 2.0

## 联系方式

如有问题或建议，欢迎提交 Issue 到 GitHub 项目仓库。
