"""RSS 数据采集器（并行抓取 + AI 预处理评分）"""
import datetime as dt
import json
import re
import textwrap
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

import feedparser
import requests

import config


# AI 预处理 Prompt
RSS_AI_SYSTEM_PROMPT = textwrap.dedent("""
你是AI行业新闻评估助手。请评估以下RSS文章对AI从业者的新闻价值。

评分标准(1-100):
- 90-100: 重大发布/突破（新模型发布、重要产品上线、突破性研究）
- 70-89: 重要更新（模型升级、新功能、重要论文、行业重大事件）
- 50-69: 有价值（教程、工具推荐、一般行业新闻）
- 30-49: 一般（讨论、评论、旧闻）
- 1-29: 低价值（无关内容、广告）

请严格按JSON格式输出，不要输出任何其他内容：
{"items": [{"id": 1, "score": 85, "summary": "2-3句中文摘要", "category": "model"}]}

字段说明：
- id: 对应输入的编号
- score: 重要性评分(1-100)
- summary: 2-3句中文摘要，精炼概括核心内容
- category: 必须是 model, product, tutorial, hardware, industry 之一
""").strip()


class RSSCollector:
    """根据 JSON 配置批量并行抓取 RSS 内容，并通过 AI 预处理评分"""

    BEIJING_TZ = dt.timezone(dt.timedelta(hours=8))
    RECENT_IDS_FILENAME = "recent_ids.json"
    RECENT_IDS_LIMIT = 5000

    def __init__(self):
        self.feeds_path = config.RSS_FEEDS_PATH
        self.lookback_hours = config.RSS_LOOKBACK_HOURS
        self.max_items_per_feed = config.RSS_MAX_ITEMS_PER_FEED
        self.max_workers = config.RSS_MAX_WORKERS
        self.output_dir = config.RSS_DIR
        self.log_dir = config.LOGS_DIR
        self.recent_ids_path = self.output_dir / self.RECENT_IDS_FILENAME
        self.recent_ids = self._load_recent_ids()

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def run(self):
        feeds = self._load_feeds()
        if not feeds:
            self.log("未找到任何 RSS 信源，跳过采集。")
            return

        self.log("=" * 50)
        self.log(f"RSS 采集开始，共 {len(feeds)} 个信源，最大并行数 {self.max_workers}")

        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=self.lookback_hours)

        # 1. 并行抓取所有 feed
        collected = self._fetch_all_feeds(feeds, cutoff)
        self.log(f"并行抓取完成，共收集 {len(collected)} 条条目")

        # 2. 去重：过滤掉已处理过的条目，只保留新内容
        new_entries = []
        skipped = 0
        seen_batch = set()
        for entry in collected:
            entry_id = entry.get("id")
            if not entry_id or entry_id in seen_batch:
                continue
            seen_batch.add(entry_id)
            if entry_id in self.recent_ids:
                skipped += 1
            else:
                new_entries.append(entry)

        if skipped:
            self.log(f"跳过 {skipped} 条已处理条目，{len(new_entries)} 条为新内容")

        # 3. 只对新条目进行 AI 预处理评分
        if new_entries:
            new_entries = self._ai_preprocess(new_entries)
            self.log(f"AI 预处理完成，{len(new_entries)} 条新条目已评分")

        # 4. 保存（只保存新条目，避免旧内容重复进入日报）
        new_count = self._save_entries(new_entries)
        self.log(f"RSS 采集完成，本次新增 {new_count} 条（跳过 {skipped} 条已处理）")

    # ------------------------------------------------------------------
    # 加载 RSS 源列表（JSON 格式）
    # ------------------------------------------------------------------
    def _load_feeds(self) -> List[Dict[str, Any]]:
        """从 JSON 文件加载 RSS 源列表"""
        if not self.feeds_path.exists():
            self.log(f"RSS 配置文件不存在：{self.feeds_path}")
            return []
        try:
            data = json.loads(self.feeds_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            self.log(f"解析 RSS 配置失败：{exc}")
            return []

        feeds = []
        for item in data:
            url = item.get("url")
            if not url:
                continue
            feeds.append({
                "name": item.get("name") or url,
                "url": url,
                "weight": float(item.get("weight", 1.0)),
            })
        return feeds

    # ------------------------------------------------------------------
    # 并行抓取
    # ------------------------------------------------------------------
    def _fetch_all_feeds(self, feeds: List[Dict], cutoff: dt.datetime) -> List[dict]:
        """使用线程池并行抓取所有 feed"""
        session = requests.Session()
        session.headers["User-Agent"] = "AI-Digest-RSS/1.0"

        collected: List[dict] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._fetch_feed, feed, cutoff, session): feed
                for feed in feeds
            }
            for future in as_completed(futures):
                feed = futures[future]
                try:
                    entries = future.result()
                    if entries:
                        collected.extend(entries)
                        self.log(f"[{feed['name']}] 收集 {len(entries)} 条")
                    else:
                        self.log(f"[{feed['name']}] 无新内容")
                except Exception as exc:
                    self.log(f"[{feed['name']}] 抓取异常: {exc}")

        return collected

    def _fetch_feed(self, feed: Dict, cutoff: dt.datetime,
                    session: requests.Session) -> List[dict]:
        """抓取单个 feed 的内容"""
        try:
            response = session.get(
                feed["url"],
                timeout=config.RSS_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except Exception as exc:
            self.log(f"[{feed['name']}] HTTP 失败：{exc}")
            return []

        try:
            parsed = feedparser.parse(response.content)
        except Exception as exc:
            self.log(f"[{feed['name']}] 解析失败：{exc}")
            return []

        if getattr(parsed, "bozo", False):
            self.log(f"[{feed['name']}] 解析警告：{getattr(parsed, 'bozo_exception', '未知错误')}")

        items: List[dict] = []
        for entry in parsed.entries[:self.max_items_per_feed]:
            normalized = self._normalize_entry(feed, entry)
            if not normalized:
                continue
            published_at = normalized.get("published_at")
            published_dt = self._parse_datetime(published_at)
            if published_dt and published_dt < cutoff:
                continue
            items.append(normalized)
        return items

    def _normalize_entry(self, feed: Dict, entry) -> Optional[dict]:
        """将 feedparser 条目转换为标准格式"""
        entry_id = entry.get("id") or entry.get("guid") or entry.get("link")
        if not entry_id:
            return None

        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or entry.get("description") or title).strip()
        content = summary
        if entry.get("content"):
            content = "\n".join(
                c.get("value", "") for c in entry["content"] if c.get("value")
            ) or summary

        author = entry.get("author") or feed.get("name")
        published_at = self._format_datetime_entry(entry)

        return {
            "type": "rss_entry",
            "id": entry_id,
            "title": title or summary[:120],
            "summary": summary,
            "content": content,
            "url": entry.get("link"),
            "author": author,
            "published_at": published_at,
            "feed": {"title": feed.get("name"), "url": feed.get("url")},
            "score": 10,  # 默认分数，AI 预处理后会覆盖
            "_feed_weight": feed.get("weight", 1.0),
        }

    # ------------------------------------------------------------------
    # AI 预处理评分
    # ------------------------------------------------------------------
    def _ai_preprocess(self, entries: List[dict]) -> List[dict]:
        """用 AI 模型对 RSS 条目进行重要性评估和摘要生成"""
        if not entries:
            return entries

        # 检查 AI 配置是否可用
        if not config.RSS_AI_BASE_URL or not config.RSS_AI_API_KEY:
            self.log("AI 预处理配置不完整，使用静态评分")
            return self._static_scoring(entries)

        batch_size = config.RSS_AI_BATCH_SIZE
        batches = [entries[i:i + batch_size] for i in range(0, len(entries), batch_size)]

        self.log(f"AI 预处理：{len(entries)} 条分为 {len(batches)} 批")

        scored_entries: List[dict] = []
        for batch_idx, batch in enumerate(batches, start=1):
            self.log(f"AI 预处理批次 {batch_idx}/{len(batches)}（{len(batch)} 条）")
            try:
                ai_results = self._call_ai_scoring(batch)
                for entry, ai_result in zip(batch, ai_results):
                    weight = entry.get("_feed_weight", 1.0)
                    ai_score = ai_result.get("score", 50)
                    # 最终分数 = AI 评分 × 源权重
                    entry["score"] = round(ai_score * weight, 1)
                    # 用 AI 摘要替换原始摘要
                    if ai_result.get("summary"):
                        entry["summary"] = ai_result["summary"]
                    if ai_result.get("category"):
                        entry["ai_category"] = ai_result["category"]
                    scored_entries.append(entry)
            except Exception as exc:
                self.log(f"AI 预处理批次 {batch_idx} 失败：{exc}，使用静态评分")
                scored_entries.extend(self._static_scoring(batch))

        return scored_entries

    def _call_ai_scoring(self, batch: List[dict]) -> List[Dict[str, Any]]:
        """调用 AI 模型评估一批 RSS 条目"""
        # 构建输入文本
        parts = []
        for idx, entry in enumerate(batch, start=1):
            title = entry.get("title", "")
            # 取内容前300字
            content = (entry.get("content") or entry.get("summary") or "").strip()
            content = re.sub(r"<[^>]+>", "", content)  # 去除 HTML 标签
            if len(content) > 300:
                content = content[:300] + "..."
            feed_name = entry.get("feed", {}).get("title", "")
            parts.append(f"{idx}. [{feed_name}] 标题：{title}\n内容：{content}")

        user_content = "\n\n".join(parts)

        # 调用 API
        base = config.RSS_AI_BASE_URL.rstrip("/")
        if not base.endswith("/v1") and "/chat/completions" not in base:
            endpoint = f"{base}/v1/chat/completions"
        elif base.endswith("/v1"):
            endpoint = f"{base}/chat/completions"
        else:
            endpoint = base

        headers = {
            "Authorization": f"Bearer {config.RSS_AI_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": config.RSS_AI_MODEL,
            "messages": [
                {"role": "system", "content": RSS_AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "max_tokens": config.RSS_AI_MAX_TOKENS,
        }

        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        ai_text = data["choices"][0]["message"]["content"].strip()

        # 解析 AI 响应
        return self._parse_ai_response(ai_text, len(batch))

    def _parse_ai_response(self, ai_text: str, expected_count: int) -> List[Dict[str, Any]]:
        """解析 AI 返回的 JSON 评分结果"""
        # 尝试提取 JSON
        text = ai_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        parsed = None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # 尝试找 JSON 边界
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    parsed = json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

        if parsed is None:
            self.log(f"AI 响应解析失败，使用默认评分。响应前200字: {ai_text[:200]}")
            return [{"score": 50, "summary": "", "category": "industry"}] * expected_count

        items = parsed.get("items", [])

        # 按 id 建立索引
        result_map = {}
        for item in items:
            item_id = item.get("id")
            if item_id is not None:
                result_map[int(item_id)] = item

        # 按顺序返回，缺失的用默认值填充
        results = []
        for idx in range(1, expected_count + 1):
            if idx in result_map:
                results.append(result_map[idx])
            else:
                results.append({"score": 50, "summary": "", "category": "industry"})

        return results

    def _static_scoring(self, entries: List[dict]) -> List[dict]:
        """静态评分（AI 不可用时的降级方案）"""
        for entry in entries:
            weight = entry.get("_feed_weight", 1.0)
            summary = entry.get("summary", "")
            base_score = 10 + min(len(summary) // 200, 10)
            entry["score"] = round(base_score * weight, 1)
        return entries

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------
    def _save_entries(self, entries: List[dict]) -> int:
        now = dt.datetime.now(self.BEIJING_TZ)
        date_str = now.strftime("%Y-%m-%d")
        daily_file = self.output_dir / f"rss_{date_str}.jsonl"
        latest_file = self.output_dir / "rss_latest.jsonl"

        # 保存前清理内部字段
        for entry in entries:
            entry.pop("_feed_weight", None)

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

        if batch_unique:
            self._remember_ids([item.get("id") for item in batch_unique if item.get("id")])

            if new_entries:
                with daily_file.open("a", encoding="utf-8") as handle:
                    for item in new_entries:
                        handle.write(json.dumps(item, ensure_ascii=False) + "\n")

            with latest_file.open("w", encoding="utf-8") as handle:
                for item in batch_unique:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        else:
            latest_file.parent.mkdir(parents=True, exist_ok=True)
            latest_file.write_text("", encoding="utf-8")

        return len(new_entries)

    # ------------------------------------------------------------------
    # 工具方法
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
            return dt.datetime.fromtimestamp(
                time.mktime(struct_time), tz=dt.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S%z")
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
