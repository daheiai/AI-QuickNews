"""RSS 数据采集器"""
import datetime as dt
import json
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

import feedparser
import requests

import config


class RSSCollector:
    """根据 OPML 列表批量抓取 RSS 内容"""

    BEIJING_TZ = dt.timezone(dt.timedelta(hours=8))
    RECENT_IDS_FILENAME = "recent_ids.json"
    RECENT_IDS_LIMIT = 5000

    def __init__(self):
        self.opml_path = config.RSS_OPML_PATH
        self.lookback_hours = config.RSS_LOOKBACK_HOURS
        self.max_items_per_feed = config.RSS_MAX_ITEMS_PER_FEED
        self.output_dir = config.RSS_DIR
        self.log_dir = config.LOGS_DIR
        self.recent_ids_path = self.output_dir / self.RECENT_IDS_FILENAME
        self.recent_ids = self._load_recent_ids()

    # ------------------------------------------------------------------
    def run(self):
        feeds = self._load_feeds()
        if not feeds:
            self.log("未在 OPML 中找到任何 RSS 信源，跳过采集。")
            return

        self.log("=" * 50)
        self.log(f"RSS 采集开始，共 {len(feeds)} 个信源")

        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=self.lookback_hours)
        collected: List[dict] = []
        for index, feed in enumerate(feeds, start=1):
            self.log(f"[{index}/{len(feeds)}] 抓取 {feed['title']}")
            entries = self._fetch_feed(feed, cutoff)
            if entries:
                collected.extend(entries)
                self.log(f"[{feed['title']}] 收集 {len(entries)} 条")

        new_count = self._save_entries(collected)
        self.log(f"RSS 采集完成，抓取 {len(collected)} 条，新增 {new_count} 条")

    # ------------------------------------------------------------------
    def _load_feeds(self) -> List[Dict[str, str]]:
        if not self.opml_path.exists():
            self.log(f"OPML 文件不存在：{self.opml_path}")
            return []
        try:
            tree = ET.parse(self.opml_path)
        except ET.ParseError as exc:
            self.log(f"解析 OPML 失败：{exc}")
            return []
        feeds = []
        for node in tree.findall('.//outline[@type="rss"]'):
            url = node.attrib.get("xmlUrl")
            title = node.attrib.get("title") or node.attrib.get("text") or url
            if not url:
                continue
            feeds.append({"title": title or "RSS", "url": url})
        return feeds

    def _fetch_feed(self, feed: Dict[str, str], cutoff: dt.datetime) -> List[dict]:
        try:
            response = requests.get(
                feed["url"],
                headers={"User-Agent": "AI-Digest-RSS/1.0"},
                timeout=config.RSS_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except Exception as exc:
            self.log(f"[{feed['title']}] 抓取失败：{exc}")
            return []

        try:
            parsed = feedparser.parse(response.content)
        except Exception as exc:
            self.log(f"[{feed['title']}] 抓取失败：{exc}")
            return []

        if getattr(parsed, "bozo", False):
            self.log(f"[{feed['title']}] 解析警告：{getattr(parsed, 'bozo_exception', '未知错误')}")

        items: List[dict] = []
        for entry in parsed.entries[: self.max_items_per_feed]:
            normalized = self._normalize_entry(feed, entry)
            if not normalized:
                continue
            published_at = normalized.get("published_at")
            published_dt = self._parse_datetime(published_at)
            if published_dt and published_dt < cutoff:
                continue
            items.append(normalized)
        return items

    def _normalize_entry(self, feed: Dict[str, str], entry) -> Optional[dict]:
        entry_id = entry.get("id") or entry.get("guid") or entry.get("link")
        if not entry_id:
            return None
        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or entry.get("description") or title).strip()
        content = summary
        if entry.get("content"):
            content = "\n".join(c.get("value", "") for c in entry["content"] if c.get("value")) or summary
        author = entry.get("author") or feed.get("title")
        published_at = self._format_datetime_entry(entry)
        score = 10 + min(len(summary) // 200, 10)
        return {
            "type": "rss_entry",
            "id": entry_id,
            "title": title or summary[:120],
            "summary": summary,
            "content": content,
            "url": entry.get("link"),
            "author": author,
            "published_at": published_at,
            "feed": {"title": feed.get("title"), "url": feed.get("url")},
            "score": score,
        }

    def _save_entries(self, entries: List[dict]) -> int:
        if not entries:
            return 0
        now = dt.datetime.now(self.BEIJING_TZ)
        date_str = now.strftime("%Y-%m-%d")
        daily_file = self.output_dir / f"rss_{date_str}.jsonl"
        latest_file = self.output_dir / "rss_latest.jsonl"

        batch_unique: List[dict] = []
        new_entries: List[dict] = []
        seen_batch = set()
        for entry in entries:
            entry_id = entry.get("id")
            if not entry_id or entry_id in seen_batch:
                continue
            seen_batch.add(entry_id)
            batch_unique.append(entry)
            if entry_id in self.recent_ids:
                continue
            new_entries.append(entry)

        self._remember_ids([item.get("id") for item in batch_unique if item.get("id")])

        if new_entries:
            with daily_file.open("a", encoding="utf-8") as handle:
                for item in new_entries:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")

        with latest_file.open("w", encoding="utf-8") as handle:
            for item in batch_unique:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

        return len(new_entries)

    # ------------------------------------------------------------------
    def log(self, message: str):
        now = dt.datetime.now(self.BEIJING_TZ)
        log_file = self.log_dir / f"rss_{now.strftime('%Y-%m-%d')}.log"
        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(line)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _load_recent_ids(self) -> "OrderedDict[str, None]":
        if not self.recent_ids_path.exists():
            return OrderedDict()
        try:
            data = json.loads(self.recent_ids_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return OrderedDict()
        ids = OrderedDict()
        if isinstance(data, list):
            for entry_id in data[-self.RECENT_IDS_LIMIT:]:
                ids[str(entry_id)] = None
        return ids

    def _remember_ids(self, ids: List[str]):
        changed = False
        for entry_id in ids:
            if not entry_id:
                continue
            if entry_id in self.recent_ids:
                self.recent_ids.move_to_end(entry_id)
            else:
                self.recent_ids[entry_id] = None
            changed = True
            while len(self.recent_ids) > self.RECENT_IDS_LIMIT:
                self.recent_ids.popitem(last=False)
        if changed:
            payload = list(self.recent_ids.keys())[-self.RECENT_IDS_LIMIT:]
            self.recent_ids_path.write_text(json.dumps(payload), encoding="utf-8")

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[dt.datetime]:
        if not value:
            return None
        for fmt in (
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
        return None

    @staticmethod
    def _format_datetime_entry(entry) -> Optional[str]:
        struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
        if struct_time:
            return dt.datetime.fromtimestamp(time.mktime(struct_time), tz=dt.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S%z"
            )
        # Fallback to string fields
        text_value = entry.get("published") or entry.get("updated")
        if text_value:
            for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
                try:
                    parsed = dt.datetime.strptime(text_value, fmt)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=dt.timezone.utc)
                    return parsed.strftime("%Y-%m-%dT%H:%M:%S%z")
                except (ValueError, TypeError):
                    continue
        return None


def main():
    collector = RSSCollector()
    collector.run()


if __name__ == "__main__":
    main()
