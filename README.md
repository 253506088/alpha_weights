# 中国基金实时监控 Web 应用

## 项目概述

一个轻量级的 Web 应用程序，供个人用户实时监控中国大陆公募基金的预估涨跌幅。通过追踪基金持仓的即时股价，计算并呈现基金股票部分的预估走势。

## 技术架构

- **后端框架**: Flask (Python Web 框架)
- **数据库**: SQLite (轻量级本地数据库)
- **任务调度**: APScheduler (定时任务)
- **前端**: HTML + JavaScript + Chart.js
- **数据源**: 新浪财经 API、东方财富 API

## 功能特性

1. **基金管理**
   - 输入 6 位基金代码自动获取持仓信息
   - 从东方财富获取前十大重仓股票及持仓占比
   - 支持多基金同时监控

2. **实时数据获取**
   - 从新浪财经 API 获取股票实时行情
   - 自动去重合并多个基金的持仓股票
   - 批量请求减少网络开销

3. **核心算法**
   - 计算每只股票的涨跌幅
   - 通过加权平均计算基金预估涨跌幅

4. **定时任务**
   - 每 5 分钟自动更新数据
   - 结果持久化到本地数据库
   - 生成历史数据点用于绘制曲线

5. **用户界面**
   - 无需登录，打开即用
   - 展示基金今日分时走势图
   - 基于 Chart.js 绘制折线图

## 目录结构

```
alpha_weights/
├── app.py                 # Flask 应用主程序
├── requirements.txt       # Python 依赖
├── run.bat               # Windows 启动脚本
├── run.sh                # Linux/Mac 启动脚本
├── README.md             # 项目说明
├── DEPLOY.md             # 部署说明
├── models.py             # 数据库模型
├── api.py                # 数据获取 API
├── scheduler.py          # 定时任务
├── static/               # 静态文件目录
│   └── css/
│       └── style.css
├── templates/            # HTML 模板目录
│   ├── index.html        # 主页面
│   └── chart.html        # 图表页面
└── data/                 # 数据目录（自动生成）
    └── fund_monitor.db   # SQLite 数据库
```

## 快速开始

```BASH
# 使用 Conda 创建环境
conda create -n alpha_weights python=3.10 -y
conda activate alpha_weights

# 安装依赖
cd D:\code\my\1\alpha_weights\alpha_weights
pip install -r requirements.txt
python app.py
```

### Windows 用户

**方式一：一键启动**
1. 双击运行 `run.bat` 脚本
2. 脚本会自动安装依赖并启动应用

**方式二：手动安装依赖**
1. 双击运行 `install.bat` 安装依赖
2. 双击运行 `run.bat` 启动应用

应用启动后，在浏览器访问: `http://localhost:5000`

### Linux/Mac 用户

**方式一：一键启动**
```bash
bash run.sh
```

**方式二：手动安装依赖**
```bash
# 安装依赖
pip3 install -r requirements.txt

# 启动应用
python3 app.py
```

应用启动后，在浏览器访问: `http://localhost:5000`

## 数据源说明

- **基金持仓数据**: 东方财富 API (eastmoney.com)
- **股票实时行情**: 新浪财经 API (hq.sinajs.cn)

## 注意事项

- 本应用仅计算基金股票部分的预估涨跌幅，不代表最终净值
- 数据更新频率为 5 分钟，符合 API 使用规范
- 债券、现金等其他资产部分被忽略

## 许可证

Apache License 2.0
