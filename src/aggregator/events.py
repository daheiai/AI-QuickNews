"""事件聚合器：将不同信源的数据统一为分析可用格式"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import config


class EventAggregator:
    """聚合 Twitter、RSS 等多信源事件"""

    def __init__(self):
        self.twitter_dir = config.TWEETS_DIR
        self.rss_dir = config.RSS_DIR
        self.events_dir = config.EVENTS_DIR
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def gather(self, date: Optional[str] = None) -> Tuple[List[dict], Path]:
        """聚合指定日期（或最新）的所有事件，并写入统一文件"""
        events: List[dict] = []
        events.extend(self._load_twitter_events(date))
        events.extend(self._load_rss_events(date))

        seen_ids = set()
        deduped: List[dict] = []
        for event in events:
            event_id = event.get("id")
            if not event_id or event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            deduped.append(event)

        deduped.sort(key=lambda item: item.get("score", 0), reverse=True)

        target = self.events_dir / ("events_latest.jsonl" if date is None else f"events_{date}.jsonl")
        self._write_jsonl(target, deduped)
        return deduped, target

    # ------------------------------------------------------------------
    # Twitter 数据
    def _load_twitter_events(self, date: Optional[str]) -> List[dict]:
        path = self._resolve_twitter_path(date)
        if not path or not path.exists():
            return []
        events = []
        for raw in self._read_jsonl(path):
            if raw.get("type") != "tweet":
                continue
            converted = self._tweet_to_event(raw)
            if converted:
                events.append(converted)
        return events

    def _resolve_twitter_path(self, date: Optional[str]) -> Optional[Path]:
        if date:
            candidate = self.twitter_dir / f"tweets_{date}.jsonl"
        else:
            candidate = self.twitter_dir / "tweets_latest.jsonl"
        return candidate

    def _tweet_to_event(self, raw: dict) -> Optional[dict]:
        tweet_id = raw.get("id")
        if not tweet_id:
            return None
        author = raw.get("author") or {}
        text = (raw.get("text") or "").strip()
        url = raw.get("url") or raw.get("twitterUrl")
        published_iso = self._normalize_datetime(raw.get("createdAt"))
        title = text.splitlines()[0][:120] if text else "Twitter 更新"
        score = self._tweet_engagement(raw)
        return {
            "id": f"twitter:{tweet_id}",
            "source": "twitter",
            "source_name": author.get("name") or author.get("userName") or "Twitter",
            "author": author.get("name") or author.get("userName") or "",
            "title": title,
            "summary": text,
            "content": text,
            "url": url,
            "published_at": published_iso,
            "score": score,
            "metadata": {
                "likes": raw.get("likeCount", 0),
                "retweets": raw.get("retweetCount", 0),
                "replies": raw.get("replyCount", 0),
                "quotes": raw.get("quoteCount", 0),
                "bookmarks": raw.get("bookmarkCount", 0),
            },
        }

    @staticmethod
    def _tweet_engagement(raw: dict) -> float:
        return (
            (raw.get("likeCount") or 0)
            + 2.5 * (raw.get("retweetCount") or 0)
            + 1.5 * (raw.get("replyCount") or 0)
            + 1.2 * (raw.get("quoteCount") or 0)
            + 0.8 * (raw.get("bookmarkCount") or 0)
        )

    # ------------------------------------------------------------------
    # RSS 数据
    def _load_rss_events(self, date: Optional[str]) -> List[dict]:
        path = self._resolve_rss_path(date)
        if not path or not path.exists():
            return []
        events = []
        for raw in self._read_jsonl(path):
            if raw.get("type") != "rss_entry":
                continue
            converted = self._rss_to_event(raw)
            if converted:
                events.append(converted)
        return events

    def _resolve_rss_path(self, date: Optional[str]) -> Optional[Path]:
        if date:
            candidate = self.rss_dir / f"rss_{date}.jsonl"
        else:
            candidate = self.rss_dir / "rss_latest.jsonl"
        return candidate

    def _rss_to_event(self, raw: dict) -> Optional[dict]:
        entry_id = raw.get("id") or raw.get("url")
        if not entry_id:
            return None
        summary = (raw.get("summary") or raw.get("title") or "").strip()
        content = raw.get("content") or summary
        published_iso = self._normalize_datetime(raw.get("published_at"))
        feed = raw.get("feed") or {}
        score = raw.get("score") or 5
        return {
            "id": f"rss:{entry_id}",
            "source": "rss",
            "source_name": feed.get("title") or raw.get("author") or "RSS",
            "author": raw.get("author") or feed.get("title") or "",
            "title": raw.get("title") or summary[:120],
            "summary": summary,
            "content": content,
            "url": raw.get("url"),
            "published_at": published_iso,
            "score": score,
            "metadata": {
                "feed_title": feed.get("title"),
                "feed_url": feed.get("url"),
            },
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _read_jsonl(path: Path) -> Iterable[dict]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    @staticmethod
    def _write_jsonl(path: Path, items: Sequence[dict]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    @staticmethod
    def _normalize_datetime(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        parsed = EventAggregator._parse_datetime(value)
        if not parsed:
            return None
        return parsed.strftime("%Y-%m-%dT%H:%M:%S%z")

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[dt.datetime]:
        if not value:
            return None
        for fmt in (
            "%a %b %d %H:%M:%S %z %Y",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                parsed = dt.datetime.strptime(value, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt.timezone.utc)
                return parsed
            except (ValueError, TypeError):
                continue
        # 兜底：尝试从时间戳
        try:
            timestamp = float(value)
            return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
        except (ValueError, TypeError):
            return None
