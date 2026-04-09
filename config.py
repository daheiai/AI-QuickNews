"""统一配置管理模块"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 项目根目录 - 使用绝对路径确保在任何位置运行都能正确找到文件
BASE_DIR = Path(__file__).resolve().parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
SOURCES_DIR = DATA_DIR / "sources"
EVENTS_DIR = DATA_DIR / "events"
TWITTER_DIR = SOURCES_DIR / "twitter"
RSS_DIR = SOURCES_DIR / "rss"
TWEETS_DIR = TWITTER_DIR  # 向后兼容旧路径
REPORTS_DIR = DATA_DIR / "reports"
LOGS_DIR = DATA_DIR / "logs"
WEB_JSON_DIR = DATA_DIR / "web-json"  # Web 渲染用的 JSON 数据
SCREENSHOTS_DIR = DATA_DIR / "screenshots"  # 截图输出目录

# Web 目录
WEB_DIR = BASE_DIR / "web"

# GitHub Changelog 配置
GITHUB_DIR = SOURCES_DIR / "github"
CHANGELOG_JSON_DIR = WEB_JSON_DIR / "changelog"
GITHUB_CHECK_INTERVAL_HOURS = int(os.getenv("GITHUB_CHECK_INTERVAL_HOURS", "12"))
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN", "")  # 可选，提高 API 限额

# GitHub 仓库列表
GITHUB_REPOS = [
    {"owner": "anthropics", "repo": "claude-code", "name": "Claude Code"},
    {"owner": "anomalyco", "repo": "opencode", "name": "OpenCode"},
    {"owner": "openclaw", "repo": "openclaw", "name": "OpenClaw"},
    {"owner": "google-gemini", "repo": "gemini-cli", "name": "Gemini CLI"},
    {"owner": "openai", "repo": "codex", "name": "Codex"},
]

# 确保目录存在
for path in (SOURCES_DIR, EVENTS_DIR, TWITTER_DIR, RSS_DIR, GITHUB_DIR, REPORTS_DIR, LOGS_DIR, WEB_JSON_DIR, CHANGELOG_JSON_DIR, SCREENSHOTS_DIR):
    path.mkdir(parents=True, exist_ok=True)

# Twitter 配置
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_USERNAMES = os.getenv(
    "TWITTER_USERNAMES",
    "Alibaba_Qwen,deepseek_ai"
).split(",")    
TWITTER_CHECK_INTERVAL_HOURS = int(os.getenv("TWITTER_CHECK_INTERVAL_HOURS", "4"))
TWITTER_MAX_PAGES = int(os.getenv("TWITTER_MAX_PAGES", "10"))

# RSS 配置
_rss_feeds_path = Path(os.getenv("RSS_FEEDS_PATH", "resources/rss_feeds.json"))
RSS_FEEDS_PATH = _rss_feeds_path if _rss_feeds_path.is_absolute() else BASE_DIR / _rss_feeds_path
RSS_LOOKBACK_HOURS = int(os.getenv("RSS_LOOKBACK_HOURS", "4"))
RSS_MAX_ITEMS_PER_FEED = int(os.getenv("RSS_MAX_ITEMS_PER_FEED", "50"))
RSS_REQUEST_TIMEOUT = int(os.getenv("RSS_REQUEST_TIMEOUT", "10"))
RSS_MAX_WORKERS = int(os.getenv("RSS_MAX_WORKERS", "20"))

# RSS AI 预处理配置（默认复用主模型）
RSS_AI_MODEL = os.getenv("RSS_AI_MODEL", "") or os.getenv("OPENAI_MODEL", "deepseek-chat")
RSS_AI_BASE_URL = os.getenv("RSS_AI_BASE_URL", "") or os.getenv("OPENAI_BASE_URL", "")
RSS_AI_API_KEY = os.getenv("RSS_AI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
RSS_AI_BATCH_SIZE = int(os.getenv("RSS_AI_BATCH_SIZE", "20"))
RSS_AI_MAX_TOKENS = int(os.getenv("RSS_AI_MAX_TOKENS", "2000"))

# AI 模型配置
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

# 飞书配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_CHAT_ID = os.getenv("FEISHU_CHAT_ID", "")
FEISHU_TOKEN_CACHE = Path(os.getenv("FEISHU_TOKEN_CACHE", "~/.cache/feishu_token.json")).expanduser()

# 摘要配置
QUICK_DIGEST_LIMIT = int(os.getenv("QUICK_DIGEST_LIMIT", "30"))
DAILY_DIGEST_LIMIT = int(os.getenv("DAILY_DIGEST_LIMIT", "60"))
QUICK_DIGEST_MAX_AGE_HOURS = int(os.getenv("QUICK_DIGEST_MAX_AGE_HOURS", "48"))
DIGEST_TEMPERATURE = float(os.getenv("DIGEST_TEMPERATURE", "0.2"))
DIGEST_MAX_TOKENS = int(os.getenv("DIGEST_MAX_TOKENS", "4000"))

# GitHub Changelog 配置
GITHUB_DIR = SOURCES_DIR / "github"
CHANGELOG_JSON_DIR = WEB_JSON_DIR / "changelog"
GITHUB_CHECK_INTERVAL_HOURS = int(os.getenv("GITHUB_CHECK_INTERVAL_HOURS", "12"))
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN", "")  # 可选，提高 API 限额

# GitHub 仓库列表
GITHUB_REPOS = [
    {"owner": "anthropics", "repo": "claude-code", "name": "Claude Code"},
    {"owner": "anomalyco", "repo": "opencode", "name": "OpenCode"},
    {"owner": "openclaw", "repo": "openclaw", "name": "OpenClaw"},
    {"owner": "google-gemini", "repo": "gemini-cli", "name": "Gemini CLI"},
    {"owner": "openai", "repo": "codex", "name": "Codex"},
]
