"""统一配置管理模块"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 项目根目录 - 使用绝对路径确保在任何位置运行都能正确找到文件
BASE_DIR = Path(__file__).resolve().parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
TWEETS_DIR = DATA_DIR / "tweets"
REPORTS_DIR = DATA_DIR / "reports"
LOGS_DIR = DATA_DIR / "logs"

# 确保目录存在
TWEETS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Twitter 配置
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_USERNAMES = os.getenv(
    "TWITTER_USERNAMES",
    "Alibaba_Qwen,deepseek_ai"
).split(",")    
TWITTER_CHECK_INTERVAL_HOURS = int(os.getenv("TWITTER_CHECK_INTERVAL_HOURS", "4"))
TWITTER_MAX_PAGES = int(os.getenv("TWITTER_MAX_PAGES", "10"))

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
DIGEST_MAX_TOKENS = int(os.getenv("DIGEST_MAX_TOKENS", "1200"))
