"""Twitter 数据采集器"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import requests

import config


class TwitterCollector:
    """Twitter 推文采集器"""

    API_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
    BEIJING_TZ = timezone(timedelta(hours=8))

    def __init__(self):
        self.api_key = config.TWITTER_API_KEY
        self.usernames = config.TWITTER_USERNAMES
        self.check_interval = config.TWITTER_CHECK_INTERVAL_HOURS
        self.max_pages = config.TWITTER_MAX_PAGES
        self.output_dir = config.TWEETS_DIR
        self.log_dir = config.LOGS_DIR

    def log(self, message: str):
        """记录日志"""
        now = datetime.now(self.BEIJING_TZ)
        log_file = self.log_dir / f"twitter_{now.strftime('%Y-%m-%d')}.log"
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(log_msg + "\n")

    def fetch_tweets(self, since_time: str) -> Optional[List[dict]]:
        """从 API 获取推文"""
        query = " OR ".join([f"from:{user}" for user in self.usernames])
        query += f" since:{since_time}"

        self.log(f"查询语句: {query}")

        headers = {"X-API-Key": self.api_key}
        params = {"query": query, "queryType": "Latest", "cursor": ""}

        all_tweets = []
        pages = 0

        try:
            while True:
                pages += 1
                if pages > self.max_pages:
                    self.log(f"分页超过上限 {self.max_pages}，停止继续请求。")
                    break

                response = requests.get(self.API_URL, headers=headers, params=params, timeout=30)
                self.log(f"API响应状态: {response.status_code}")

                if response.status_code != 200:
                    self.log(f"API错误: {response.status_code} - {response.text}")
                    return None

                data = response.json()
                tweets = data.get("tweets", [])
                all_tweets.extend(tweets)

                if not data.get("has_next_page"):
                    break
                next_cursor = data.get("next_cursor")
                if not next_cursor:
                    self.log("API 返回 has_next_page=True 但没有 next_cursor，停止。")
                    break
                if next_cursor == params.get("cursor"):
                    self.log("检测到 cursor 未变化，可能进入循环，停止。")
                    break
                params["cursor"] = next_cursor
        except Exception as e:
            self.log(f"请求异常: {e}")
            return None

        return all_tweets

    def build_since_time(self) -> str:
        """构建查询起始时间"""
        utc_time = datetime.now(timezone.utc) - timedelta(hours=self.check_interval)
        return utc_time.strftime("%Y-%m-%d_%H:%M:%S_UTC")

    def save_tweets(self, tweets: List[dict]) -> int:
        """保存推文到文件"""
        if not tweets:
            return 0

        now = datetime.now(self.BEIJING_TZ)
        year_month = now.strftime("%Y-%m")
        year_week = now.strftime("%Y-W%W")
        date = now.strftime("%Y-%m-%d")

        monthly_file = self.output_dir / f"tweets_{year_month}.jsonl"
        weekly_file = self.output_dir / f"tweets_{year_week}.jsonl"
        daily_file = self.output_dir / f"tweets_{date}.jsonl"
        latest_file = self.output_dir / "tweets_latest.jsonl"

        existing_ids = set()
        for file in [monthly_file, weekly_file, daily_file]:
            if file.exists():
                try:
                    with file.open("r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                existing_ids.add(json.loads(line)["id"])
                except Exception as e:
                    self.log(f"读取文件 {file} 出错: {e}")

        new_tweets = [t for t in tweets if t["id"] not in existing_ids]

        if new_tweets:
            for file in [monthly_file, weekly_file, daily_file]:
                try:
                    with file.open("a", encoding="utf-8") as f:
                        for tweet in new_tweets:
                            f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
                except Exception as e:
                    self.log(f"写入文件 {file} 出错: {e}")

        try:
            with latest_file.open("w", encoding="utf-8") as f:
                for tweet in tweets:
                    f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
        except Exception as e:
            self.log(f"写入latest文件出错: {e}")

        return len(new_tweets)

    def run(self):
        """执行采集任务"""
        self.log("=" * 50)
        self.log("Twitter 采集开始")

        since_time = self.build_since_time()
        self.log(f"抓取近 {self.check_interval} 小时内（自 {since_time} 起）的推文")

        tweets = self.fetch_tweets(since_time)

        if tweets is None:
            self.log("API请求失败，程序退出")
            sys.exit(1)

        if not tweets:
            self.log("没有新推文")
            self.log("采集完成")
            return

        new_count = self.save_tweets(tweets)
        self.log(f"本次抓取 {len(tweets)} 条，新增 {new_count} 条")
        self.log("采集完成")


def main():
    """命令行入口"""
    collector = TwitterCollector()
    collector.run()


if __name__ == "__main__":
    main()
