# AI 信息聚合与推送系统

自动抓取 Twitter AI 领域推文，通过 AI 生成摘要，并推送到飞书群聊的自动化系统。

## 功能特性

- 🐦 **多源采集**：支持 Twitter（可扩展 RSS 等其他信源）
- 🤖 **AI 分析**：使用大模型生成快讯和日报
- 📱 **飞书推送**：自动推送到飞书群聊
- ⏰ **定时任务**：支持 cron 定时执行
- 📊 **数据归档**：按日/周/月自动归档推文

## 目录结构

```
.
├── main.py              # 主入口
├── config.py            # 配置管理
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
├── src/                 # 源代码
│   ├── collectors/      # 数据采集模块
│   │   └── twitter.py   # Twitter 采集器
│   ├── analyzer/        # AI 分析模块
│   │   └── digest.py    # 摘要分析器
│   └── notifier/        # 通知模块
│       └── feishu.py    # 飞书通知器
├── data/                # 数据目录
│   ├── tweets/          # 推文数据
│   ├── reports/         # AI 报告
│   └── logs/            # 日志文件
└── scripts/             # 部署脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的 API 密钥：

```bash
# Twitter API
TWITTER_API_KEY=your_twitter_api_key

# AI 模型
OPENAI_API_KEY=your_openai_api_key

# 飞书
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_CHAT_ID=your_chat_id
```

### 3. 运行程序

**快讯模式**（抓取最新推文 + 生成快讯 + 推送）：
```bash
python main.py --mode quick
```

**日报模式**（生成昨日日报 + 推送）：
```bash
python main.py --mode daily
```

### 4. 单独运行各模块

```bash
# 仅抓取推文
python -m src.collectors.twitter

# 仅生成快讯
python -m src.analyzer.digest --mode quick

# 仅推送到飞书
python -m src.notifier.feishu --mode quick
```

## 定时任务配置

### 宝塔面板

1. 进入「计划任务」
2. 添加 Shell 脚本任务
3. 执行周期：每 4 小时
4. 脚本内容：

```bash
#!/bin/bash
cd /path/to/推特每日更新-claude
source .env
/usr/bin/python3 main.py --mode quick >> data/logs/cron.log 2>&1
```

### Linux Crontab

```bash
# 每 4 小时执行快讯
0 */4 * * * cd /path/to/推特每日更新-claude && /usr/bin/python3 main.py --mode quick

# 每天早上 7 点生成日报
0 7 * * * cd /path/to/推特每日更新-claude && /usr/bin/python3 main.py --mode daily
```

## 配置说明

### Twitter 配置

- `TWITTER_API_KEY`：Twitter API 密钥
- `TWITTER_USERNAMES`：监控的用户列表（逗号分隔）
- `TWITTER_CHECK_INTERVAL_HOURS`：抓取时间间隔（默认 4 小时）
- `TWITTER_MAX_PAGES`：最大分页数（默认 10）

### AI 模型配置

- `OPENAI_BASE_URL`：API 端点
- `OPENAI_API_KEY`：API 密钥
- `OPENAI_MODEL`：模型名称
- `DIGEST_TEMPERATURE`：采样温度（默认 0.2）
- `DIGEST_MAX_TOKENS`：最大输出 token（默认 1200）

### 飞书配置

- `FEISHU_APP_ID`：飞书应用 ID
- `FEISHU_APP_SECRET`：飞书应用密钥
- `FEISHU_CHAT_ID`：目标群聊 ID

## 扩展其他信源

系统已预留扩展接口，添加新的信息源只需：

1. 在 `src/collectors/` 下创建新的采集器（如 `rss.py`）
2. 实现 `run()` 方法，保存数据到 `data/tweets/` 目录
3. 在 `main.py` 中调用新的采集器

示例：

```python
# src/collectors/rss.py
class RSSCollector:
    def run(self):
        # 采集 RSS 数据
        # 保存到 data/tweets/ 目录
        pass
```

## 常见问题

### 1. 路径问题导致写入失败

确保使用绝对路径。`config.py` 已自动处理路径问题，所有数据都会写入 `data/` 目录。

### 2. 环境变量未生效

在服务器上运行时，需要在脚本中显式加载 `.env`：

```bash
export $(cat .env | xargs) && python main.py --mode quick
```

或使用 `python-dotenv`：

```python
from dotenv import load_dotenv
load_dotenv()
```

### 3. 飞书推送失败

检查：
- 飞书应用是否开启了机器人能力
- `FEISHU_CHAT_ID` 是否正确
- 应用是否已添加到目标群聊

## 许可证

MIT License
