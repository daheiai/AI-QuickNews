"""AI 摘要分析器"""
import datetime as dt
import json
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import requests

import config


@dataclass(frozen=True)
class ModeSettings:
    """模式配置"""
    key: str
    system_prompt: str
    heading: str
    output_prefix: str
    default_limit: int
    default_max_age: Optional[int]


DEFAULT_QUICK_PROMPT = textwrap.dedent("""
你是一名 AI 速报员。请阅读最新抓取的推文，重点判断是否出现重大人工智能动态，
包括但不限于：重量级模型或产品发布、突破性研究、行业安全/政策事件、重要融资
或争议。如果没有重点消息，请明确说明"过去几小时暂无重大动态"。

输出结构：
1. 速报结论：一句话说明是否出现重要消息。
2. 速报内容：如有重点，请列出核心内容并给出你的总结和判断，这条信息说明了什么？

语言以中文为主，可补充重要的英文关键词。除上面要求格式外，禁止提供其他冗余信息。
""").strip()

DEFAULT_DAILY_PROMPT = textwrap.dedent("""
你是一名AI行业观察员。
以下是一批过去24小时内的AI相关推文摘要（JSON数组）。你需要对它们按主题归纳主要事件
或观点（比如：新模型发布、AI绘图争议、应用工具热度）。

要求：
- 用"人写日报"的语气，而非AI总结的口吻。
- 每节加上小标题与表情符号。
- 保留关键信息，但可适当合并冗余。
- 总字数控制在800~1200字。
- 禁止使用markdown格式，以聊天软件易读的方式换行。
""").strip()

MODE_SETTINGS = {
    "quick": ModeSettings(
        key="quick",
        system_prompt=DEFAULT_QUICK_PROMPT,
        heading="AI 快讯速览",
        output_prefix="ai_quick",
        default_limit=config.QUICK_DIGEST_LIMIT,
        default_max_age=config.QUICK_DIGEST_MAX_AGE_HOURS,
    ),
    "daily": ModeSettings(
        key="daily",
        system_prompt=DEFAULT_DAILY_PROMPT,
        heading="AI 领域日报（{date}）",
        output_prefix="ai_daily_{date}",
        default_limit=config.DAILY_DIGEST_LIMIT,
        default_max_age=None,
    ),
}


class Tweet:
    """推文数据结构"""
    __slots__ = ("id", "url", "author", "author_handle", "created_at", "lang", "text",
                 "like_count", "retweet_count", "reply_count", "quote_count", "bookmark_count")

    def __init__(self, raw: dict):
        self.id = raw.get("id")
        self.url = raw.get("url") or raw.get("twitterUrl")
        author = raw.get("author") or {}
        self.author = author.get("name") or author.get("userName") or "Unknown"
        self.author_handle = author.get("userName") or author.get("screen_name", "")
        self.created_at = self._parse_datetime(raw.get("createdAt"))
        self.lang = raw.get("lang") or ""
        self.text = (raw.get("text") or "").strip()
        self.like_count = self._safe_int(raw.get("likeCount"))
        self.retweet_count = self._safe_int(raw.get("retweetCount"))
        self.reply_count = self._safe_int(raw.get("replyCount"))
        self.quote_count = self._safe_int(raw.get("quoteCount"))
        self.bookmark_count = self._safe_int(raw.get("bookmarkCount"))

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[dt.datetime]:
        if not value:
            return None
        for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
            try:
                return dt.datetime.strptime(value, fmt)
            except (ValueError, TypeError):
                continue
        return None

    @staticmethod
    def _safe_int(value: Optional[int]) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def engagement(self) -> float:
        """互动度评分"""
        return (self.like_count + 2.5 * self.retweet_count + 1.5 * self.reply_count +
                1.2 * self.quote_count + 0.8 * self.bookmark_count)

    def short_repr(self) -> str:
        """简短表示"""
        created = self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""
        snippet = self.text.replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:237] + "..."
        return (f"[{self.author}] {created} | ❤ {self.like_count} 🔁 {self.retweet_count} 💬 {self.reply_count}\n"
                f"{snippet}\n{self.url}")


class DigestAnalyzer:
    """AI 摘要分析器"""

    def __init__(self, mode: str = "quick"):
        self.mode = mode
        self.settings = MODE_SETTINGS[mode]
        self.tweets_dir = config.TWEETS_DIR
        self.reports_dir = config.REPORTS_DIR

    def load_tweets(self, path: Path) -> List[Tweet]:
        """加载推文"""
        tweets = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if raw.get("type") != "tweet":
                    continue
                tweets.append(Tweet(raw))
        return tweets

    def filter_tweets(self, tweets: Sequence[Tweet], max_age_hours: Optional[int] = None,
                     min_engagement: float = 0.0) -> List[Tweet]:
        """过滤推文"""
        now = dt.datetime.now(dt.timezone.utc)
        filtered = []
        for tweet in tweets:
            if max_age_hours and tweet.created_at:
                age_hours = (now - tweet.created_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    continue
            if tweet.engagement < min_engagement:
                continue
            filtered.append(tweet)
        return filtered

    def select_top_tweets(self, tweets: Sequence[Tweet], limit: int) -> List[Tweet]:
        """选择热度最高的推文"""
        return sorted(tweets, key=lambda t: t.engagement, reverse=True)[:limit]

    def build_prompt(self, tweets: Sequence[Tweet]) -> str:
        """构建提示词"""
        parts = []
        for idx, tweet in enumerate(tweets, start=1):
            parts.append(f"{idx}. {tweet.short_repr()}")
        return "\n\n".join(parts)

    def call_ai(self, prompt: str) -> str:
        """调用 AI 模型"""
        base = config.OPENAI_BASE_URL.rstrip("/")
        if not base.endswith("/v1") and "/chat/completions" not in base:
            endpoint = f"{base}/v1/chat/completions"
        elif base.endswith("/v1"):
            endpoint = f"{base}/chat/completions"
        else:
            endpoint = base

        headers = {
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "system", "content": self.settings.system_prompt},
            {"role": "user", "content": f"以下是最近采集的推文（已按互动度排序）：\n\n{prompt}"},
        ]

        payload = {
            "model": config.OPENAI_MODEL,
            "messages": messages,
            "temperature": config.DIGEST_TEMPERATURE,
            "max_tokens": config.DIGEST_MAX_TOKENS,
        }

        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    def save_report(self, summary: str, selected_tweets: Sequence[Tweet], heading: str) -> Path:
        """保存报告"""
        now = dt.datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H%M")

        prefix = self.settings.output_prefix
        if "{date}" in prefix:
            prefix = prefix.replace("{date}", now.strftime("%Y-%m-%d"))

        path = self.reports_dir / f"{prefix}_{timestamp}.md"

        appendix_lines = []
        for idx, tweet in enumerate(selected_tweets, start=1):
            snippet = tweet.text.replace("\n", " ").strip()
            if len(snippet) > 50:
                snippet = snippet[:50].rstrip() + "..."
            appendix_lines.append(f"{idx}. [{tweet.author}] {snippet} (❤ {tweet.like_count}) {tweet.url}".rstrip())

        content = f"""# {heading}

- 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}

---

{summary.strip()}

---

## 附录：输入推文片段

{chr(10).join(appendix_lines)}
"""
        path.write_text(content.strip(), encoding="utf-8")
        return path

    def find_latest_daily_file(self) -> Tuple[Path, str]:
        """查找最新的日报文件"""
        latest_path = None
        latest_date = None

        for candidate in self.tweets_dir.glob("tweets_*.jsonl"):
            match = re.match(r"tweets_(\d{4}-\d{2}-\d{2})\.jsonl$", candidate.name)
            if not match:
                continue
            try:
                current_date = dt.datetime.strptime(match.group(1), "%Y-%m-%d").date()
            except ValueError:
                continue
            if latest_date is None or current_date > latest_date:
                latest_date = current_date
                latest_path = candidate

        if not latest_path or latest_date is None:
            raise FileNotFoundError(f"未在 {self.tweets_dir} 找到符合命名格式的日报数据文件。")

        return latest_path, latest_date.isoformat()

    def run(self, date: Optional[str] = None, limit: Optional[int] = None,
            max_age: Optional[int] = None):
        """执行分析任务"""
        # 定位输入文件
        if self.mode == "quick":
            source_file = self.tweets_dir / "tweets_latest.jsonl"
            target_date = None
        else:  # daily
            if date:
                target_date = date
                source_file = self.tweets_dir / f"tweets_{target_date}.jsonl"
            else:
                source_file, target_date = self.find_latest_daily_file()

        if not source_file.exists():
            raise FileNotFoundError(f"找不到指定的输入文件：{source_file}")

        # 准备标题
        heading = self.settings.heading
        if target_date and "{date}" in heading:
            heading = heading.replace("{date}", target_date)

        # 加载和过滤推文
        tweets = self.load_tweets(source_file)

        if max_age is None:
            max_age = self.settings.default_max_age

        tweets = self.filter_tweets(tweets, max_age_hours=max_age)

        if not tweets:
            raise ValueError("没有符合筛选条件的推文，停止生成摘要。")

        # 选择推文
        limit = limit or self.settings.default_limit
        selected = self.select_top_tweets(tweets, limit=min(limit, len(tweets)))

        # 生成摘要
        prompt = self.build_prompt(selected)
        summary = self.call_ai(prompt)

        # 保存报告
        report_path = self.save_report(summary, selected, heading)
        print(f"[{self.mode}] 摘要已写入 {report_path}")
        return report_path


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="AI 推文摘要分析")
    parser.add_argument("--mode", choices=["quick", "daily"], default="quick")
    parser.add_argument("--date", help="日报日期 (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, help="推文数量限制")
    parser.add_argument("--max-age", type=int, help="最大时间范围（小时）")
    args = parser.parse_args()

    analyzer = DigestAnalyzer(mode=args.mode)
    analyzer.run(date=args.date, limit=args.limit, max_age=args.max_age)


if __name__ == "__main__":
    main()
