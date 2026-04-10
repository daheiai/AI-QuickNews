<div align="center">

# AI-QuickNews

> *把 AI 圈每天最值得看的信息，自动抓下来，整理好，再稳定发出去。*

[在线效果](https://news.daheiai.com) · [我的主页](https://daheiai.com/) · [加入交流](https://my.feishu.cn/wiki/MB6FwO9GyiGebykfeamcv4H3n5b)

</div>

---

这是我自己长期在跑的一套 AI 热点日报系统。

它会持续抓取 Twitter、RSS、GitHub Changelog 等信源，把零散信息聚合起来，再交给 AI 做快讯、日报、更新日志整理，最后输出到网页和消息渠道。`news.daheiai.com` 上现在展示的，就是这套系统真实运行后的效果，不是单纯做出来摆着的 Demo。

这个仓库不只是“某一版代码”，而是我把项目从最早期脚本、过渡阶段到后期完整版本，按时间点整理出来的一条历史链。你既可以直接拿最新版本部署，也可以回看我整个系统是怎么一步一步长出来的。

## 在线效果

- 项目运行效果：<https://news.daheiai.com>
- 个人主页：<https://daheiai.com/>
- 社群入口：<https://my.feishu.cn/wiki/MB6FwO9GyiGebykfeamcv4H3n5b>

如果你平时也在关注 AI 资讯、做信息聚合、日报系统、AI 工作流，或者只是想看看一个真实跑起来的独立项目长什么样，这个仓库应该会对你有点参考价值。

## 这个项目能做什么

- 抓取多类 AI 信源：Twitter、RSS、GitHub Changelog
- 把不同来源的信息统一整理成事件流
- 用大模型生成快讯、日报、更新日志摘要
- 输出网页展示页、历史页、RSS 等阅读入口
- 支持飞书推送
- 保留完整历史版本，方便回退和研究演进过程

## 适合谁看

- 想做 AI 日报、资讯聚合、自动化内容系统的人
- 想看一个真实项目如何从脚本演化成完整系统的人
- 想参考 Twitter/RSS/Changelog 多源聚合实现方式的人
- 想把 AI 总结、网页展示、消息推送串起来的人

## 仓库里有什么

```text
.
├── main.py                 # 主入口
├── config.py               # 配置管理
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── retranslate_changelog.py
├── src/                    # 核心源码
│   ├── collectors/         # 信源采集
│   ├── aggregator/         # 事件聚合
│   ├── analyzer/           # AI 摘要生成
│   ├── generators/         # Changelog 相关生成逻辑
│   ├── notifier/           # 消息推送
│   └── renderer/           # 截图与渲染
├── resources/              # RSS 等资源文件
└── web/                    # 网页展示层
```

注意，这个公开仓库已经去掉了真实 `.env`、运行数据、截图、缓存和敏感信息。  
所以你直接下载可以看源码、改逻辑、部署自己的版本，但要自己补环境变量配置。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

然后在 `.env` 里填好你自己的配置。

最基本需要这些：

```bash
TWITTER_API_KEY=your_twitter_api_key
OPENAI_API_KEY=your_openai_api_key
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_CHAT_ID=your_feishu_chat_id
```

### 3. 运行

快讯模式：

```bash
python main.py --mode quick
```

日报模式：

```bash
python main.py --mode daily
```

GitHub Changelog 模式：

```bash
python main.py --mode github
```

## 主要能力说明

### Twitter / RSS / GitHub Changelog 多源采集

项目不是只抓一个来源，而是把不同信息源放在同一条流水线里处理。这样做的好处是，你最后拿到的不是碎片信息，而是更接近“今天 AI 圈发生了什么”的统一视角。

### AI 摘要生成

采集完原始信息后，系统会做筛选、排序、聚合，再交给大模型生成更适合人读的快讯、日报或 changelog 摘要。  
这一步不是简单拼接文本，而是尽量把信息从“抓到了什么”变成“今天值得看什么”。

### 网页展示

后期版本里，项目已经不只是命令行工具，而是带完整网页展示层：

- 主页
- 实时页
- 历史页
- RSS 页面
- Changelog 页面

这也是为什么你可以直接在 `news.daheiai.com` 上看到最终运行效果。

## 历史版本

这个仓库保留了完整的项目演化历史，不是只传了最后一版。

你可以直接看：

```bash
git log --oneline --decorate --graph
git tag
```

每个关键阶段我都打了 tag，例如：

- `v0001-initial-twitter-monitor`
- `v0007-add-rss-prototype`
- `v004-add-rss`
- `v009-add-history-page`
- `v012-add-tool-monitoring`
- `v014-add-reddit-monitoring`

如果你想回到某个历史时间点：

```bash
git checkout v009-add-history-page
```

## 部署提醒

公开仓库里已经移除了：

- 真实 `.env`
- 日志
- 运行数据
- 截图
- 缓存
- 个人敏感资源

所以如果你要部署自己的版本，需要自己准备：

- 各类 API key
- 推送渠道配置
- 定时任务环境
- 网页部署环境

## 如果你对这个项目感兴趣

如果你是从网页那边点进来的，或者你本身就在做 AI 信息流、日报系统、自动化内容产品，也欢迎继续看我别的项目和内容。

- 我的主页：<https://daheiai.com/>
- 这个日报系统在线效果：<https://news.daheiai.com>
- 加群交流：<https://my.feishu.cn/wiki/MB6FwO9GyiGebykfeamcv4H3n5b>

## License

MIT
