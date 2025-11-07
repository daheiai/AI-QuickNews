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


@dataclass
class DigestOutput:
    """运行结果产物"""
    report_path: Path
    primary_text: str
    appendix_text: str


DEFAULT_QUICK_PROMPT = textwrap.dedent("""
# 角色设定
你是一名 AI 行业速报编辑，AI行业每天都有爆炸式的信息，而你擅长从中抓取到真正的价值。
你的核心目标是输出「是否有重要动态」+「核心内容摘要」+「价值判断」。

---

# 判断逻辑（按优先级）
1、新开源模型（关键词：release, Open source, 开源, 发布, SOTA ,Qwen,GLM 等开源模型发布或更新）
2、商业大模型更新（关键词：ChatGPT, Claude, Gemini, Grok, Kimi, MiniMax等闭源模型动态）
3、模型实测结论（关键词：对比, 跑测试, 实测, 差距, ）
3、AI产品/工具发布与更新（关键词：API，推出，试玩, YouMind, Sora, Codex ，等AI工具动态）
4、github开源项目（关键词：star, 工具, 开源, 分享, 爆火 ,含有github.com链接）
5、提示词创新（出现prompt，实用性工具性的提示词模板）
6、机器人/硬件相关（关键词：Boston Dynamics, Figure, Optimus ,树莓派 等）
7、重大软件的更新（关键词：Chrome、Vscode等）
                                

只有推文中**直接提及或隐含这些事件行为**（发布、上线、开放、更新、宣布、推出）时，才视为“有动态”。
额外信息：JustinLin610是Qwen团队的成员，他会说一些谜语，比如要有新东西来了。Hx1u0是Kimi团队的成员，会爆料一些有趣的开发故事。
                                       

---

# 输出要求
## 第一部分
用一句话说明整体结论：
- 如果没有检测到符合条件的内容，输出：“暂无重大动态。”
- 如果检测到，输出：“有 X 条重要动态。”

## 第二部分
逐条总结：
- 每条最多 5 行。
- 信息量小的，用一句话概括，越精简越好不必换行。
- 信息量大的，再用以下格式：

一、事件标题（用一句话抓住主干）
· 细节1：
· 细节2：

## 第三部分
AI总结：针对以上内容做总结。 
---

# 语言要求
- 全中文输出，但可保留必要的英文关键词。
- 严禁出现“以下是结果”“我认为”等AI自述语。
- 不得输出任何格式说明、推理过程或无关评论。
- 再次精简，                            

---

# 示例输出
有3条重要动态：
一、Sora APP 安卓版正式上线，已在加、美、日等地区开放下载。

二、Google 推出 File Search Tool 
    ·产品形态：完全托管的 RAG 系统，内置于 Gemini API 
    ·核心价值：将 RAG 简化为一行 API 调用，自动完成索引、向量嵌入与语义检索 
    ·计费模式：仅首次建立索引收费（$0.15/100万tokens），后续查询免费 ·支持格式：PDF、Word、TXT、JSON、源代码等主流格式

三、苹果新版 Siri 将由 Gemini 提供后台支持，预计 2026 年 3 月上线。

AI总结：谷歌推出的工具会大幅降低企业级知识库部署门槛，RAG技术平民化。Sora朝着更广泛的用户群体进军，Siri抛弃OpenAI转向Gemini。
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
                parsed = dt.datetime.strptime(value, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt.timezone.utc)
                return parsed
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

    def save_report(self, summary: str, selected_tweets: Sequence[Tweet], heading: str) -> DigestOutput:
        """生成并保存报告，同时返回飞书友好的文本"""
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
            appendix_lines.append(
                f"{idx}. [{tweet.author}] {snippet} (❤ {tweet.like_count}) {tweet.url}".rstrip()
            )

        content = f"""# {heading}

- 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}

---

{summary.strip()}

---

## 附录：输入推文片段

{chr(10).join(appendix_lines)}
"""
        path.write_text(content.strip(), encoding="utf-8")

        primary_text = self._format_primary_text(summary, now)
        appendix_text = self._format_appendix_text(appendix_lines, now)
        return DigestOutput(report_path=path, primary_text=primary_text, appendix_text=appendix_text)

    def _format_primary_text(self, summary: str, generated_at: dt.datetime) -> str:
        header_label = "大黑4小时AI速报" if self.mode == "quick" else "大黑AI日报"
        header = f"【{header_label}  时间：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}】"

        conclusion_section = self._extract_section(summary, "1. 速报结论")
        if conclusion_section:
            conclusion_lines = [ln.strip() for ln in conclusion_section.splitlines() if ln.strip()]
            conclusion_raw = " ".join(conclusion_lines)
        else:
            conclusion_raw = summary.strip().split("\n", 1)[0]
        conclusion_text = self._normalize_inline(conclusion_raw).strip()
        if conclusion_text and "有重要动态" in conclusion_text and "：" not in conclusion_text.split("有重要动态", 1)[1][:2]:
            conclusion_text = conclusion_text.replace("有重要动态", "有重要动态：", 1)
        content_section = self._extract_section(summary, "2. 速报内容") or summary
        content_text = self._convert_content_section(content_section)
        content_lines = content_text.splitlines()
        for idx, raw_line in enumerate(content_lines):
            stripped_line = raw_line.strip()
            if not stripped_line:
                continue
            if stripped_line == conclusion_text.strip():
                content_text = "\n".join(content_lines[idx + 1:]).lstrip()
            break

        ending = "本时段速报完毕，请等待下一个4小时速报~" if self.mode == "quick" else "本期日报结束，感谢关注~"

        parts = [header, conclusion_text, "", content_text.strip(), "", ending]
        return "\n".join(part for part in parts if part is not None)

    def _extract_section(self, markdown: str, title: str) -> str:
        pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$", re.MULTILINE)
        match = pattern.search(markdown)
        if not match:
            return ""
        start = match.end()
        remainder = markdown[start:]
        next_heading = re.search(r"^##\s+", remainder, re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(markdown)
        return markdown[start:end].strip()

    def _convert_content_section(self, markdown: str) -> str:
        lines: List[str] = []
        section_index = 0
        for raw_line in markdown.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                lines.append("")
                continue
            if stripped.startswith("###"):
                section_index += 1
                numeral = self._section_index_to_cn(section_index)
                title = stripped.lstrip("# ")
                lines.append(f"{numeral}、{self._normalize_inline(title)}")
                continue

            indent = "  " if raw_line.startswith("  ") else ""
            bullet_match = re.match(r"^([*-]|\d+\.)\s+", stripped)
            prefix = None
            if bullet_match:
                stripped = stripped[len(bullet_match.group(0)) :]
                prefix = f"{indent}· "
            if stripped.startswith("**判断**"):
                stripped = stripped.replace("**判断**", "AI判断", 1)

            normalized = self._normalize_inline(stripped)
            lines.append(f"{prefix}{normalized}" if prefix else normalized)

        return "\n".join(self._collapse_blank_lines(lines))

    @staticmethod
    def _collapse_blank_lines(lines: Sequence[str]) -> List[str]:
        cleaned: List[str] = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            cleaned.append(line)
            prev_blank = is_blank
        return cleaned

    @staticmethod
    def _section_index_to_cn(index: int) -> str:
        numerals = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"]
        if 1 <= index <= len(numerals):
            return numerals[index - 1]
        return str(index)

    @staticmethod
    def _normalize_inline(text: str) -> str:
        text = text.replace("**", "")
        text = re.sub(r"`(.+?)`", r"\\1", text)
        text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\\1（\\2）", text)
        text = text.replace("#", "")
        return text.strip()

    def _format_appendix_text(self, appendix_lines: Sequence[str], generated_at: dt.datetime) -> str:
        header = f"【速报附录  时间：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}】"
        intro = "以下为本次摘要引用的原始内容片段："
        body = []
        for line in appendix_lines:
            normalized = self._normalize_inline(line)
            normalized = normalized.replace("[", "").replace("]", "")
            body.append(normalized)
        return "\n".join([header, intro, "", *body])

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

        # 保存报告并生成消息文本
        output = self.save_report(summary, selected, heading)
        print(f"[{self.mode}] 摘要已写入 {output.report_path}")
        return output


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
