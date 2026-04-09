# 迁移指南

从旧版本迁移到重构后的新版本。

## 主要变化

### 1. 目录结构变化

**旧版本：**
```
推特每日更新-claude/
├── twitter_monitor.py
├── ai_digest.py
├── feishu_client.py
├── orchestrator.py
├── tweets_data/
├── ai_reports/
└── logs/
```

**新版本：**
```
推特每日更新-claude/
├── main.py              # 统一入口
├── config.py            # 配置管理
├── .env                 # 环境变量（敏感信息）
├── src/                 # 模块化代码
│   ├── collectors/
│   ├── analyzer/
│   └── notifier/
└── data/                # 数据目录
    ├── tweets/
    ├── reports/
    └── logs/
```

### 2. 命令变化

| 旧命令 | 新命令 |
|--------|--------|
| `python orchestrator.py --mode quick` | `python main.py --mode quick` |
| `python orchestrator.py --mode daily` | `python main.py --mode daily` |
| `python twitter_monitor.py` | `python -m src.collectors.twitter` |
| `python ai_digest.py --mode quick` | `python -m src.analyzer.digest --mode quick` |
| `python feishu_client.py --mode quick` | `python -m src.notifier.feishu --mode quick` |

### 3. 配置方式变化

**旧版本：** 配置硬编码在各个 Python 文件中

**新版本：** 统一使用 `.env` 文件管理配置

## 迁移步骤

### 步骤 1：备份旧数据

```bash
# 备份推文数据
cp -r tweets_data data/tweets/

# 备份报告
cp -r ai_reports data/reports/

# 备份日志
cp -r logs data/logs/
```

### 步骤 2：安装新依赖

```bash
pip3 install python-dotenv
```

### 步骤 3：更新宝塔计划任务

找到你的计划任务，将脚本内容从：

```bash
cd /path/to/推特每日更新-claude
python3 orchestrator.py --mode quick
```

改为：

```bash
cd /path/to/推特每日更新-claude
python3 main.py --mode quick
```

### 步骤 4：测试新版本

```bash
# 测试配置加载
python3 -c "import config; print('配置加载成功')"

# 测试模块导入
python3 -c "from src.collectors.twitter import TwitterCollector; print('模块导入成功')"

# 查看帮助信息
python3 main.py --help
```

### 步骤 5：试运行

```bash
# 试运行快讯模式（不会重复抓取，因为会检查已有数据）
python3 main.py --mode quick
```

## 兼容性说明

### 数据文件兼容

新版本**完全兼容**旧版本的数据文件格式：

- ✅ `tweets_YYYY-MM-DD.jsonl` 格式不变
- ✅ `tweets_latest.jsonl` 格式不变
- ✅ `ai_quick_*.md` 和 `ai_daily_*.md` 格式不变

### 路径处理改进

新版本使用**绝对路径**，解决了之前在服务器上运行时的路径问题：

```python
# config.py 中
BASE_DIR = Path(__file__).resolve().parent  # 自动获取项目根目录
TWEETS_DIR = BASE_DIR / "data/tweets"       # 绝对路径
```

这意味着无论从哪个目录运行程序，都能正确找到数据文件。

## 旧文件处理

迁移完成并确认新版本运行正常后，可以删除旧文件：

```bash
# 可以删除的旧文件
rm twitter_monitor.py
rm ai_digest.py
rm feishu_client.py
rm orchestrator.py

# 如果数据已迁移到 data/ 目录，可以删除旧目录
rm -rf tweets_data/
rm -rf ai_reports/
rm -rf logs/
```

**注意：** 删除前请确保数据已备份！

## 常见问题

### Q: 新版本会丢失旧数据吗？

A: 不会。新版本读取的数据目录是 `data/tweets/`，只要把旧数据复制过去即可。

### Q: 宝塔计划任务需要修改什么？

A: 只需要把命令从 `python3 orchestrator.py --mode quick` 改为 `python3 main.py --mode quick`。

### Q: 环境变量在服务器上如何生效？

A: `.env` 文件会自动加载（通过 `python-dotenv`），无需手动 export。

### Q: 如何验证迁移成功？

A: 运行 `python3 main.py --mode quick`，如果能正常抓取、分析、推送，说明迁移成功。

## 回滚方案

如果新版本有问题，可以立即回滚：

1. 旧文件还在，直接使用旧命令即可
2. 宝塔计划任务改回 `python3 orchestrator.py --mode quick`
3. 数据文件互相兼容，不影响回滚

## 技术支持

如有问题，请检查：

1. `.env` 文件是否正确配置
2. `python-dotenv` 是否已安装
3. 数据目录 `data/tweets/` 是否存在
4. 日志文件 `data/logs/` 查看详细错误信息
