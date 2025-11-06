import requests
import json
from datetime import datetime, timedelta, timezone
import os
import sys

# ========== 配置区域 ==========
API_KEY = os.getenv("TWITTER_API_KEY", "")
USERNAMES = ["karminski3", "lijigang_com", "op7418"]
CHECK_INTERVAL_HOURS = 2
OUTPUT_DIR = "tweets_data"
LOG_DIR = "logs"
LAST_CHECK_FILE = ".last_check_time"
# ==============================

API_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
BEIJING_TZ = timezone(timedelta(hours=8))

def log(message):
    os.makedirs(LOG_DIR, exist_ok=True)
    now = datetime.now(BEIJING_TZ)
    log_file = f"{LOG_DIR}/log_{now.strftime('%Y-%m-%d')}.log"
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(log_file, "a", encoding="utf-8") as f:
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
    try:
        while True:
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
            params["cursor"] = data.get("next_cursor", "")
    except Exception as e:
        log(f"请求异常: {e}")
        return None

    return all_tweets

def get_last_check_time():
    if os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, "r") as f:
            return f.read().strip()
    utc_time = datetime.now(timezone.utc) - timedelta(hours=CHECK_INTERVAL_HOURS)
    return utc_time.strftime("%Y-%m-%d_%H:%M:%S_UTC")

def save_last_check_time():
    utc_time = datetime.now(timezone.utc)
    with open(LAST_CHECK_FILE, "w") as f:
        f.write(utc_time.strftime("%Y-%m-%d_%H:%M:%S_UTC"))

def save_tweets(tweets):
    if not tweets:
        return 0

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    now = datetime.now(BEIJING_TZ)
    year_month = now.strftime("%Y-%m")
    year_week = now.strftime("%Y-W%W")
    date = now.strftime("%Y-%m-%d")

    monthly_file = f"{OUTPUT_DIR}/tweets_{year_month}.jsonl"
    weekly_file = f"{OUTPUT_DIR}/tweets_{year_week}.jsonl"
    daily_file = f"{OUTPUT_DIR}/tweets_{date}.jsonl"
    latest_file = f"{OUTPUT_DIR}/tweets_latest.jsonl"

    existing_ids = set()
    for file in [monthly_file, weekly_file, daily_file]:
        if os.path.exists(file):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            existing_ids.add(json.loads(line)["id"])
            except Exception as e:
                log(f"读取文件 {file} 出错: {e}")

    new_tweets = [t for t in tweets if t["id"] not in existing_ids]

    if new_tweets:
        for file in [monthly_file, weekly_file, daily_file]:
            try:
                with open(file, "a", encoding="utf-8") as f:
                    for tweet in new_tweets:
                        f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
            except Exception as e:
                log(f"写入文件 {file} 出错: {e}")

    try:
        with open(latest_file, "w", encoding="utf-8") as f:
            for tweet in tweets:
                f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
    except Exception as e:
        log(f"写入latest文件出错: {e}")

    return len(new_tweets)

def main():
    log("=" * 50)
    log("程序开始运行")

    since_time = get_last_check_time()
    log(f"抓取 {since_time} 之后的推文")

    tweets = fetch_tweets(since_time)

    if tweets is None:
        log("API请求失败，程序退出")
        sys.exit(1)

    if not tweets:
        log("没有新推文")
        save_last_check_time()
        log("程序完成")
        return

    new_count = save_tweets(tweets)
    log(f"本次抓取 {len(tweets)} 条，新增 {new_count} 条")

    save_last_check_time()
    log("程序完成")

if __name__ == "__main__":
    main()
