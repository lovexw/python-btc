# 加密货币资金流动监控预警系统

这是一个实时监控加密货币资金流动的系统，重点关注比特币和稳定币的大额转账动态。

## 功能特性

- 实时监控 https://rss.xiaowuleyi.com/telegram/channel/misttrack_alert RSS数据源
- 每5分钟同步获取数据，避免429限制
- 只获取包含 #BTC、#USDT、#USDC 关键词的信息
- 数据存储在本地SQLite数据库
- Web前端界面展示过滤后的消息
- 每日总量变动统计面板
- 分别统计BTC、USDT、USDC的流动量数据

## 技术架构

- Python 3.x
- Flask Web框架
- SQLite本地数据库
- feedparser RSS解析库
- Chart.js 数据可视化

## 安装与运行

1. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

2. 运行程序:
   ```
   python main.py
   ```

3. 访问Web界面:
   打开浏览器访问 http://localhost:5000

## 目录结构

```
.
├── main.py                 # 主程序文件
├── requirements.txt        # 依赖包列表
├── README.md              # 说明文档
├── data/                  # 数据库文件目录
├── templates/             # HTML模板目录
│   └── index.html         # 主页模板
└── static/                # 静态资源目录
    ├── css/               # 样式文件
    │   └── style.css
    └── js/                # JavaScript文件
        └── script.js
```

## 数据库结构

### crypto_alerts 表
存储所有符合条件的警报信息

| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | INTEGER | 主键 |
| title | TEXT | 标题 |
| summary | TEXT | 摘要 |
| link | TEXT | 链接 |
| published | TEXT | 发布时间 |
| btc_amount | REAL | BTC金额 |
| usdt_amount | REAL | USDT金额 |
| usdc_amount | REAL | USDC金额 |
| timestamp | DATETIME | 本地时间戳 |

### daily_stats 表
存储每日统计数据

| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | INTEGER | 主键 |
| date | TEXT | 日期 |
| btc_total | REAL | 当日BTC总金额 |
| usdt_total | REAL | 当日USDT总金额 |
| usdc_total | REAL | 当日USDC总金额 |
| transaction_count | INTEGER | 当日交易笔数 |
| timestamp | DATETIME | 时间戳 |

## API接口

### 获取最新警报
```
GET /api/alerts
```

### 获取统计数据
```
GET /api/stats
```

## 配置说明

系统默认每5分钟抓取一次数据，可以通过修改 [main.py](file:///Users/xw/Documents/code/buy-btc-test-ali/main.py) 中的 `time.sleep(300)` 来调整频率。

## 注意事项

1. 程序启动后会立即开始监控并获取最新数据
2. 数据库文件会自动创建在 `data/crypto_monitor.db`
3. 系统只获取最新的数据，不会获取历史演示数据
4. 前端页面会自动刷新显示最新数据