"""基于 AI 的推文摘要脚本。

脚本会加载 `twitter_monitor.py` 采集到的推文，根据互动度排序后，将
高优先级推文发送给兼容 OpenAI 接口的大模型进行总结，并把结果写入
Markdown 文档，方便后续查阅或手动分发。

提供两种模式：
1. `quick`（默认）读取 `tweets_latest.jsonl`，用于检测当次抓取中的重
   大 AI 动态，生成快讯。
2. `daily` 聚合 `tweets_YYYY-MM-DD.jsonl`，适合作为前一天的日报；如果
   未显式指定日期，会自动选择最新一天的数据文件。

典型用法：
    python ai_digest.py --mode quick
    python ai_digest.py --mode daily --date 2025-11-06

可以通过命令行参数指定输入文件、输出目录、时间过滤等细节；模型的
接口地址、秘钥、系统提示词使用环境变量配置，详见 `main()`。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import requests

# ---------------------------------------------------------------------------
# 基本配置：通过环境变量覆写默认值，方便接入不同的 OpenAI 兼容服务。
# ---------------------------------------------------------------------------
AI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ai.shuocier.com/v1")
AI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

DEFAULT_QUICK_PROMPT = textwrap.dedent(
    """
    你是一名 AI 速报员。请阅读最新抓取的推文，重点判断是否出现重大人工智能动态，
    包括但不限于：重量级模型或产品发布、突破性研究、行业安全/政策事件、重要融资
    或争议。如果没有重点消息，请明确说明“过去几小时暂无重大动态”。

    输出结构：
    1. 速报结论：一句话说明是否出现重要消息。
    2. 速报内容：如有重点，请列出核心内容并给出你的总结和判断，这条信息说明了什么？

    语言以中文为主，可补充重要的英文关键词。除上面要求格式外，禁止提供其他冗余信息。

    """
).strip()

DEFAULT_DAILY_PROMPT = textwrap.dedent(
    """
    你是一名AI行业观察员。
    以下是一批过去24小时内的AI相关推文摘要（JSON数组）。你需要对它们按主题归纳主要事件
    或观点（比如：新模型发布、AI绘图争议、应用工具热度）。

    要求：
    - 用“人写日报”的语气，而非AI总结的口吻。
    - 每节加上小标题与表情符号。
    - 保留关键信息，但可适当合并冗余。
    - 总字数控制在800~1200字。
    - 禁止使用markdown格式，以聊天软件易读的方式换行。

    """
).strip()

QUICK_SYSTEM_PROMPT = os.getenv("TWEET_ANALYST_PROMPT_QUICK", DEFAULT_QUICK_PROMPT)
DAILY_SYSTEM_PROMPT = os.getenv("TWEET_ANALYST_PROMPT_DAILY", DEFAULT_DAILY_PROMPT)


def _parse_env_int(name: str, default: Optional[int]) -> Optional[int]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:  # noqa: BLE001 - 明确指出配置错误
        raise ValueError(f"环境变量 {name} 需要是整数: {value}") from exc


QUICK_DEFAULT_LIMIT = int(os.getenv("QUICK_DIGEST_LIMIT", "30"))
DAILY_DEFAULT_LIMIT = int(os.getenv("DAILY_DIGEST_LIMIT", "60"))
QUICK_DEFAULT_MAX_AGE = _parse_env_int("QUICK_DIGEST_MAX_AGE_HOURS", 48)
DAILY_DEFAULT_MAX_AGE = _parse_env_int("DAILY_DIGEST_MAX_AGE_HOURS", None)


@dataclass(frozen=True)
class ModeSettings:
    key: str
    system_prompt: str
    heading: str
    output_prefix: str
    default_limit: int
    default_max_age: Optional[int]


MODE_SETTINGS = {
    "quick": ModeSettings(
        key="quick",
        system_prompt=QUICK_SYSTEM_PROMPT,
        heading="AI 快讯速览",
        output_prefix="ai_quick",
        default_limit=QUICK_DEFAULT_LIMIT,
        default_max_age=QUICK_DEFAULT_MAX_AGE,
    ),
    "daily": ModeSettings(
        key="daily",
        system_prompt=DAILY_SYSTEM_PROMPT,
        heading="AI 领域日报（{date}）",
        output_prefix="ai_daily_{date}",
        default_limit=DAILY_DEFAULT_LIMIT,
        default_max_age=DAILY_DEFAULT_MAX_AGE,
    ),
}

# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------


class Tweet:
    """对原始推文做一次轻量结构化，方便后续排序和渲染。"""

    __slots__ = (
        "id",
        "url",
        "author",
        "author_handle",
        "created_at",
        "lang",
        "text",
        "like_count",
        "retweet_count",
        "reply_count",
        "quote_count",
        "bookmark_count",
    )

    def __init__(self, raw: dict) -> None:
        self.id = raw.get("id")
        self.url = raw.get("url") or raw.get("twitterUrl")
        author = raw.get("author") or {}
        self.author = author.get("name") or author.get("userName") or "Unknown"
        self.author_handle = author.get("userName") or author.get("screen_name", "")
        self.created_at = parse_datetime(raw.get("createdAt"))
        self.lang = raw.get("lang") or ""
        self.text = (raw.get("text") or "").strip()
        self.like_count = safe_int(raw.get("likeCount"))
        self.retweet_count = safe_int(raw.get("retweetCount"))
        self.reply_count = safe_int(raw.get("replyCount"))
        self.quote_count = safe_int(raw.get("quoteCount"))
        self.bookmark_count = safe_int(raw.get("bookmarkCount"))

    @property
    def engagement(self) -> float:
        """根据互动指标计算的加权分，用于排序。"""

        # 简单的权重模型：转推比点赞更能扩散，回复说明讨论度。
        return (
            self.like_count
            + 2.5 * self.retweet_count
            + 1.5 * self.reply_count
            + 1.2 * self.quote_count
            + 0.8 * self.bookmark_count
        )

    def short_repr(self) -> str:
        created = self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""
        snippet = self.text.replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:237] + "..."
        return (
            f"[{self.author}] {created} | ❤ {self.like_count} 🔁 {self.retweet_count} 💬 {self.reply_count}\n"
            f"{snippet}\n{self.url}"
        )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def parse_datetime(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    for fmt in (
        "%a %b %d %H:%M:%S %z %Y",  # Twitter API 的默认格式
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return dt.datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def safe_int(value: Optional[int]) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def load_tweets(path: Path) -> List[Tweet]:
    tweets: List[Tweet] = []
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


def filter_tweets(
    tweets: Sequence[Tweet],
    max_age_hours: Optional[int] = None,
    min_engagement: float = 0.0,
    allow_languages: Optional[Sequence[str]] = None,
) -> List[Tweet]:
    now = dt.datetime.now(dt.timezone.utc)
    allow_set = {lang.lower() for lang in allow_languages} if allow_languages else None

    filtered: List[Tweet] = []
    for tweet in tweets:
        if max_age_hours and tweet.created_at:
            age_hours = (now - tweet.created_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                continue
        if allow_set and tweet.lang.lower() not in allow_set:
            continue
        if tweet.engagement < min_engagement:
            continue
        filtered.append(tweet)
    return filtered


def select_top_tweets(tweets: Sequence[Tweet], limit: int) -> List[Tweet]:
    return sorted(tweets, key=lambda t: t.engagement, reverse=True)[:limit]


def build_prompt_chunks(tweets: Sequence[Tweet]) -> str:
    parts = []
    for idx, tweet in enumerate(tweets, start=1):
        parts.append(f"{idx}. {tweet.short_repr()}")
    return "\n\n".join(parts)


def infer_date_from_filename(path: Path) -> Optional[str]:
    match = re.search(r"tweets_(\d{4}-\d{2}-\d{2})", path.name)
    return match.group(1) if match else None


def find_latest_daily_file(directory: Path) -> Tuple[Path, str]:
    latest_path: Optional[Path] = None
    latest_date: Optional[dt.date] = None

    for candidate in directory.glob("tweets_*.jsonl"):
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
        raise FileNotFoundError(f"未在 {directory} 找到符合命名格式的日报数据文件。")

    return latest_path, latest_date.isoformat()


LIST_HEAD_FIX = re.compile(r"(?m)^(\s*)(\d+)\.\s*\n\s*")


def normalize_numbered_blocks(text: str) -> str:
    """确保 Markdown 有序列表的编号与正文同列展示。"""

    def repl(match: re.Match[str]) -> str:
        indent, number = match.groups()
        return f"{indent}{number}. "

    return LIST_HEAD_FIX.sub(repl, text)


def call_chat_completion(
    messages: Sequence[dict],
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> str:
    if not AI_API_KEY or AI_API_KEY == "YOUR_API_KEY_HERE":
        raise RuntimeError("缺少 OPENAI_API_KEY 环境变量，运行前请先配置密钥。")

    base = AI_BASE_URL.rstrip("/")
    if not base.endswith("/v1") and "/chat/completions" not in base:
        endpoint = f"{base}/v1/chat/completions"
    elif base.endswith("/v1"):
        endpoint = f"{base}/chat/completions"
    else:
        endpoint = base  # 允许用户直接提供完整地址

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": list(messages),
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected response: {data}") from exc


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def build_digest(
    tweets: Sequence[Tweet],
    *,
    limit: int,
    model: str,
    temperature: float,
    max_tokens: int,
    system_prompt: str,
) -> Tuple[str, List[Tweet]]:
    """返回 (总结文本, 选取推文)。"""
    selected = select_top_tweets(tweets, limit=limit)

    if not selected:
        raise ValueError("No tweets left after filtering. Aborting.")

    prompt_block = build_prompt_chunks(selected)
    user_prompt = textwrap.dedent(
        f"""
        以下是最近采集的推文（已按互动度排序，序号越小越重要）。
        请依据系统提示词，输出结构化的中文洞察：

        {prompt_block}
        """
    ).strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    summary = call_chat_completion(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    return summary, selected


def _preview_snippet(text: str, limit: int = 50) -> str:
    snippet = text.replace("\n", " ").strip()
    if len(snippet) <= limit:
        return snippet
    return snippet[:limit].rstrip() + "..."


def build_appendix(tweets: Sequence[Tweet]) -> str:
    lines = []
    for idx, tweet in enumerate(tweets, start=1):
        snippet = _preview_snippet(tweet.text, 50)
        link = tweet.url or ""
        lines.append(f"{idx}. [{tweet.author}] {snippet} (❤ {tweet.like_count}) {link}".rstrip())
    return "\n".join(lines)


def save_report(
    summary: str,
    selected_tweets: Sequence[Tweet],
    output_dir: Path,
    *,
    prefix: str,
    heading: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H%M")
    path = output_dir / f"{prefix}_{timestamp}.md"

    summary = normalize_numbered_blocks(summary)
    appendix = normalize_numbered_blocks(build_appendix(selected_tweets))

    content_lines = [
        f"# {heading}",
        "",
        f"- 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        summary.strip(),
        "",
        "---",
        "",
        "## 附录：输入推文片段",
        "",
        appendix.strip(),
    ]

    content = "\n".join(content_lines).strip()

    path.write_text(content, encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="汇总并总结采集到的 AI 领域推文")
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_SETTINGS.keys()),
        default="quick",
        help="选择运行模式：quick 为快速快讯，daily 为日报",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="直接指定要处理的 .jsonl 文件路径",
    )
    parser.add_argument(
        "--date",
        help="日报模式下用于定位 tweets_YYYY-MM-DD.jsonl 的日期（格式 YYYY-MM-DD）",
    )
    parser.add_argument(
        "--tweets-dir",
        type=Path,
        default=Path("tweets_data"),
        help="查找推文数据文件的目录",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ai_reports"),
        help="摘要 Markdown 的输出目录",
    )
    parser.add_argument(
        "--output-prefix",
        help="输出文件名前缀，默认随模式变化",
    )
    parser.add_argument(
        "--heading",
        help="Markdown 顶部标题，默认随模式变化，可使用 {date} 占位符",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        help="忽略早于指定小时数的推文（默认值取决于模式，<=0 表示不限制）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="发送给模型的推文上限（默认值取决于模式）",
    )
    parser.add_argument(
        "--min-engagement",
        type=float,
        default=float(os.getenv("DIGEST_MIN_ENGAGEMENT", "0")),
        help="剔除互动度低于该阈值的推文",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(os.getenv("DIGEST_TEMPERATURE", "0.2")),
        help="模型采样温度",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("DIGEST_MAX_TOKENS", "1200")),
        help="限制模型输出的最大 token 数",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印待发送给模型的推文上下文，不实际调用模型",
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        help="仅保留给定语言代码的推文（例如 zh en）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = MODE_SETTINGS[args.mode]

    output_prefix = args.output_prefix or settings.output_prefix
    heading = args.heading or settings.heading

    # 定位输入文件
    source_file: Path
    target_date: Optional[str] = None
    if args.mode == "quick":
        if args.input:
            source_file = args.input
        else:
            source_file = args.tweets_dir / "tweets_latest.jsonl"
        target_date = infer_date_from_filename(source_file)
    else:  # daily
        if args.input:
            source_file = args.input
            target_date = infer_date_from_filename(source_file)
        else:
            if args.date:
                try:
                    dt.datetime.strptime(args.date, "%Y-%m-%d")
                except ValueError as exc:
                    raise SystemExit("--date 参数的格式应为 YYYY-MM-DD") from exc
                target_date = args.date
                source_file = args.tweets_dir / f"tweets_{target_date}.jsonl"
            else:
                source_file, target_date = find_latest_daily_file(args.tweets_dir)

    if not source_file.exists():
        raise FileNotFoundError(f"找不到指定的输入文件：{source_file}")

    if target_date and "{date}" in heading:
        heading = heading.replace("{date}", target_date)

    if args.mode == "daily" and target_date and "{date}" in output_prefix:
        output_prefix = output_prefix.replace("{date}", target_date)

    tweets = load_tweets(source_file)

    # 结合模式默认值与用户参数，得到最终过滤逻辑
    if args.limit is not None:
        limit = args.limit
    else:
        limit = settings.default_limit

    if args.max_age is None:
        max_age = settings.default_max_age
    elif args.max_age <= 0:
        max_age = None
    else:
        max_age = args.max_age

    tweets = filter_tweets(
        tweets,
        max_age_hours=max_age,
        min_engagement=args.min_engagement,
        allow_languages=args.languages,
    )

    if not tweets:
        raise SystemExit("没有符合筛选条件的推文，停止生成摘要。")

    top_count = min(limit, len(tweets))

    if args.dry_run:
        prompt_block = build_prompt_chunks(select_top_tweets(tweets, limit=top_count))
        print("[dry-run] 选取的推文上下文如下：\n")
        print(prompt_block)
        return

    summary, selected_tweets = build_digest(
        tweets,
        limit=top_count,
        model=AI_MODEL,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        system_prompt=settings.system_prompt,
    )

    report_path = save_report(
        summary,
        selected_tweets,
        args.output_dir,
        prefix=output_prefix,
        heading=heading,
    )
    print(f"[{args.mode}] 摘要已写入 {report_path}")


if __name__ == "__main__":
    main()
