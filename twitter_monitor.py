import requests
import json
from datetime import datetime, timedelta, timezone
import os
import sys
from pathlib import Path

# ========== 配置区域 ==========
API_KEY = os.getenv("TWITTER_API_KEY", "")
USERNAMES = ["karminski3","op7418", "Alibaba_Qwen", "dotey", "arena", "MiniMax__AI", "KwaiAICoder","Zai_org","JustinLin610","lmstudio","oran_ge","deepseek_ai","OpenRouterAI","imxiaohu","AnthropicAI","OpenAI","huggingface"]
CHECK_INTERVAL_HOURS = 4
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "tweets_data"
LOG_DIR = BASE_DIR / "logs"
# ==============================

API_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
BEIJING_TZ = timezone(timedelta(hours=8))
MAX_PAGES = int(os.getenv("TWITTER_MAX_PAGES", "10"))

def log(message):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(BEIJING_TZ)
    log_file = LOG_DIR / f"log_{now.strftime('%Y-%m-%d')}.log"
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def fetch_tweets(since_time):
    if not API_KEY:
        raise RuntimeError("缺少 TWITTER_API_KEY 环境变量，无法请求 Twitter API。")

    query = " OR ".join([f"from:{user}" for user in USERNAMES])
    query += f" since:{since_time}"

    log(f"查询语句: {query}")

    headers = {"X-API-Key": API_KEY}
    params = {"query": query, "queryType": "Latest", "cursor": ""}

    all_tweets = []
    pages = 0
    try:
        while True:
            pages += 1
            if pages > MAX_PAGES:
                log(f"分页超过上限 {MAX_PAGES}，停止继续请求。")
                break

            response = requests.get(API_URL, headers=headers, params=params, timeout=30)
            log(f"API响应状态: {response.status_code}")

            if response.status_code != 200:
                log(f"API错误: {response.status_code} - {response.text}")
                return None

            data = response.json()
            tweets = data.get("tweets", [])
            all_tweets.extend(tweets)

            if not data.get("has_next_page"):
                break
            next_cursor = data.get("next_cursor")
            if not next_cursor:
                log("API 返回 has_next_page=True 但没有 next_cursor，停止。")
                break
            if next_cursor == params.get("cursor"):
                log("检测到 cursor 未变化，可能进入循环，停止。")
                break
            params["cursor"] = next_cursor
    except Exception as e:
        log(f"请求异常: {e}")
        return None

    return all_tweets

def build_since_time() -> str:
    utc_time = datetime.now(timezone.utc) - timedelta(hours=CHECK_INTERVAL_HOURS)
    return utc_time.strftime("%Y-%m-%d_%H:%M:%S_UTC")

def save_tweets(tweets):
    if not tweets:
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(BEIJING_TZ)
    year_month = now.strftime("%Y-%m")
    year_week = now.strftime("%Y-W%W")
    date = now.strftime("%Y-%m-%d")

    monthly_file = OUTPUT_DIR / f"tweets_{year_month}.jsonl"
    weekly_file = OUTPUT_DIR / f"tweets_{year_week}.jsonl"
    daily_file = OUTPUT_DIR / f"tweets_{date}.jsonl"
    latest_file = OUTPUT_DIR / "tweets_latest.jsonl"

    existing_ids = set()
    for file in [monthly_file, weekly_file, daily_file]:
        if file.exists():
            try:
                with file.open("r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            existing_ids.add(json.loads(line)["id"])
            except Exception as e:
                log(f"读取文件 {file} 出错: {e}")

    new_tweets = [t for t in tweets if t["id"] not in existing_ids]

    if new_tweets:
        for file in [monthly_file, weekly_file, daily_file]:
            try:
                with file.open("a", encoding="utf-8") as f:
                    for tweet in new_tweets:
                        f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
            except Exception as e:
                log(f"写入文件 {file} 出错: {e}")

    try:
        with latest_file.open("w", encoding="utf-8") as f:
            for tweet in tweets:
                f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
    except Exception as e:
        log(f"写入latest文件出错: {e}")

    return len(new_tweets)

def main():
    log("=" * 50)
    log("程序开始运行")

    since_time = build_since_time()
    log(f"抓取近 {CHECK_INTERVAL_HOURS} 小时内（自 {since_time} 起）的推文")

    tweets = fetch_tweets(since_time)

    if tweets is None:
        log("API请求失败，程序退出")
        sys.exit(1)

    if not tweets:
        log("没有新推文")
        log("程序完成")
        return

    new_count = save_tweets(tweets)
    log(f"本次抓取 {len(tweets)} 条，新增 {new_count} 条")

    log("程序完成")

if __name__ == "__main__":
    main()
