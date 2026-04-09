"""AI 摘要分析器"""
import datetime as dt
import json
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import requests

import config
from src.aggregator.events import EventAggregator


# ============ 期数计数器 ============
ISSUE_COUNTER_FILE = config.DATA_DIR / "issue_counter.json"
ISSUE_START_NUMBER = 504  # 起始期数


def get_next_issue_number() -> int:
    """获取下一期期数并自增"""
    if ISSUE_COUNTER_FILE.exists():
        try:
            data = json.loads(ISSUE_COUNTER_FILE.read_text(encoding="utf-8"))
            current = data.get("issue_number", ISSUE_START_NUMBER - 1)
        except (json.JSONDecodeError, KeyError):
            current = ISSUE_START_NUMBER - 1
    else:
        current = ISSUE_START_NUMBER - 1

    next_number = current + 1
    ISSUE_COUNTER_FILE.write_text(
        json.dumps({"issue_number": next_number}, ensure_ascii=False),
        encoding="utf-8"
    )
    return next_number


def get_current_issue_number() -> int:
    """获取当前期数（不自增）"""
    if ISSUE_COUNTER_FILE.exists():
        try:
            data = json.loads(ISSUE_COUNTER_FILE.read_text(encoding="utf-8"))
            return data.get("issue_number", ISSUE_START_NUMBER)
        except (json.JSONDecodeError, KeyError):
            pass
    return ISSUE_START_NUMBER


# ============ 品牌配置（Logo 匹配）============
# 关键词匹配采用大小写不敏感
# 注意：避免使用过短或过于通用的关键词，防止误匹配
BRAND_KEYWORDS = {
    # 主流大模型
    "openai": ["openai", "chatgpt", "gpt-4", "gpt-5", "gpt4", "gpt5", "dall-e", "dalle", "openai o1", "openai o3", "gpt-o1", "gpt-o3", "codex"],
    "claude": ["claude", "anthropic", "claude 3", "claude opus", "claude sonnet"],
    "deepseek": ["deepseek", "deep seek", "深度求索", "deepseek-v", "deepseek-r1"],
    "gemini": ["gemini", "gemini pro", "gemini ultra", "google gemini"],
    "gemma": ["gemma", "google gemma", "gemma-2"],
    "meta": ["meta ai", "llama", "meta llama", "llama-2", "llama-3", "llama2", "llama3"],
    "mistral": ["mistral", "mixtral", "pixtral", "mistral ai"],
    "cohere": ["cohere", "command-r", "command r", "cohere ai"],
    "xai": ["xai", "x.ai", "grok", "grok-2", "grok-3"],

    # 国内大模型
    "qwen": ["qwen", "qwen2", "qwen3", "通义千问", "通义"],
    "alibaba": ["alibaba cloud", "阿里巴巴", "阿里云", "alibaba ai"],
    "kimi": ["kimi", "moonshot", "月之暗面", "kimi chat"],
    "minimax": ["minimax", "海螺ai", "hailuo ai", "海螺视频", "M2.1", "M2", "M2.2"],
    "zhipu": ["zhipu", "智谱", "chatglm", "glm-4", "glm-3", "智谱清言","GLM"],
    "baidu": ["baidu ai", "百度ai", "ernie", "文心一言", "文心大模型"],
    "doubao": ["doubao", "豆包", "字节豆包"],
    "bytedance": ["bytedance ai", "字节跳动ai"],
    "hunyuan": ["hunyuan", "混元", "腾讯混元", "腾讯ai"],
    "spark": ["讯飞星火", "星火大模型", "星火认知", "iflytek spark"],
    "tiangong": ["tiangong", "天工ai", "天工大模型", "昆仑万维"],

    # 图像/视频生成
    "stability": ["stability ai", "stable diffusion", "sdxl", "sd3", "stability.ai"],
    "midjourney": ["midjourney"],
    "runway": ["runway", "runwayml", "runway gen"],
    "pika": ["pika labs", "pika ai", "pika视频"],
    "flux": ["flux.1", "flux ai", "black forest labs", "flux模型"],
    "ideogram": ["ideogram", "ideogram ai"],
    "pixverse": ["pixverse"],
    "haiper": ["haiper ai", "haiper"],
    "viggle": ["viggle ai", "viggle"],
    "civitai": ["civitai"],
    "novelai": ["novelai", "novel ai"],
    "clipdrop": ["clipdrop"],
    "kling": ["kling ai", "可灵", "快手可灵"],
    "sora": ["openai sora", "sora视频", "sora ai"],

    # 音频生成
    "suno": ["suno ai", "suno音乐"],
    "udio": ["udio ai", "udio音乐"],

    # 开发工具
    "github": ["github"],
    "copilot": ["github copilot", "copilot ai"],
    "cursor": ["cursor ai", "cursor编辑器", "cursor ide"],
    "windsurf": ["windsurf", "codeium"],
    "cline": ["cline ai", "cline插件"],
    "manus": ["manus ai"],
    "devin": ["devin ai", "cognition devin"],
    "replit": ["replit", "replit ai"],

    # 平台/工具
    "huggingface": ["huggingface", "hugging face", "🤗"],
    "ollama": ["ollama"],
    "gradio": ["gradio"],
    "langchain": ["langchain"],
    "comfyui": ["comfyui", "comfy ui"],
    "openwebui": ["open webui", "openwebui"],
    "lmstudio": ["lm studio", "lmstudio"],
    "vllm": ["vllm"],
    "dify": ["dify", "dify ai"],
    "coze": ["coze", "扣子", "字节扣子"],
    "n8n": ["n8n"],
    "notion": ["notion ai"],
    "notebooklm": ["notebooklm", "notebook lm", "google notebooklm"],
    "mcp": ["model context protocol", "mcp协议", "mcp server"],

    # 云服务/硬件
    "google": ["google ai", "google deepmind", "deepmind"],
    "nvidia": ["nvidia", "英伟达", "h100", "h200", "b100", "b200", "blackwell", "geforce", "cuda"],
    "microsoft": ["microsoft ai", "微软ai", "azure ai"],
    "apple": ["apple intelligence", "apple ai", "苹果ai"],
    "azure": ["azure openai", "azure ml"],
    "cloudflare": ["cloudflare ai", "cloudflare workers ai"],
    "huawei": ["huawei ai", "华为ai", "昇腾", "盘古大模型"],
    "amd": ["amd ai", "amd mi300", "amd instinct"],
    "intel": ["intel ai", "intel gaudi"],

    # API 聚合/推理平台
    "openrouter": ["openrouter"],
    "deepinfra": ["deepinfra"],
    "fireworks": ["fireworks ai", "fireworks.ai"],
    "cerebras": ["cerebras"],
    "siliconcloud": ["siliconcloud", "硅基流动"],
    "groq": ["groq", "groq ai"],
    "together": ["together ai", "together.ai"],
    "replicate": ["replicate"],
    "modal": ["modal.com", "modal ai"],

    # 其他工具/产品
    "bilibili": ["bilibili ai", "b站ai", "哔哩哔哩ai"],
    "monica": ["monica ai"],
    "youmind": ["youmind"],
    "jina": ["jina ai"],
    "tavily": ["tavily"],
    "perplexity": ["perplexity", "perplexity ai"],
    "character": ["character.ai", "character ai"],
    "poe": ["poe ai", "quora poe"],
}

# ============ 分区配置 ============
CATEGORIES = {
    "model": {
        "name": "模型动态",
        "keywords": ["模型", "model", "发布", "release", "开源", "open source", "sota", "更新", "update",
                     "评测", "benchmark", "对比", "实测", "llm", "大模型", "参数", "训练", "微调", "fine-tune"],
    },
    "product": {
        "name": "产品工具",
        "keywords": ["产品", "工具", "tool", "app", "应用", "api", "sdk", "github", "开源项目", "star",
                     "软件", "software", "chrome", "vscode", "plugin", "插件", "extension"],
    },
    "tutorial": {
        "name": "技巧教程",
        "keywords": ["prompt", "提示词", "教程", "tutorial", "技巧", "tips", "方法", "经验", "分享"],
    },
    "hardware": {
        "name": "硬件动态",
        "keywords": ["机器人", "robot", "硬件", "hardware", "芯片", "chip", "gpu", "tpu", "npu",
                     "boston dynamics", "figure", "optimus", "树莓派", "nvidia", "英伟达"],
    },
    "industry": {
        "name": "行业资讯",
        "keywords": ["融资", "收购", "投资", "估值", "政策", "监管", "安全", "伦理", "合作", "战略"],
    },
}


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


只有推文中**直接提及或隐含这些事件行为**（发布、上线、开放、更新、宣布、推出）时，才视为"有动态"。
额外信息：JustinLin610是Qwen团队的成员，他会说一些谜语，比如要有新东西来了。Hx1u0是Kimi团队的成员，会爆料一些有趣的开发故事。


---

# 输出要求
## 第一部分
用一句话说明整体结论：
- 如果没有检测到符合条件的内容，输出："暂无重大动态。"
- 如果检测到，输出："有 X 条重要动态。"

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
- 严禁出现"以下是结果""我认为"等AI自述语。
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

# 新版快讯 Prompt - 输出 JSON 格式
QUICK_JSON_PROMPT = textwrap.dedent("""
# 角色设定
你是一名 AI 行业速报编辑，擅长从海量信息中抓取有价值的内容并归类整理。

# 内容分类
1、model（模型动态）：模型发布、更新、评测、训练方法、性能对比
2、product（产品工具）：AI产品、工具、GitHub项目、软件更新、新功能、API
3、tutorial（技巧教程）：提示词、使用技巧、教程分享
4、hardware（硬件动态）：机器人、芯片、硬件设备、GPU
5、industry（行业资讯）：研究论文、安全报告、融资、政策、公司动态、合作

# 判断标准
- 有实质信息内容的推文都应该被收录
- 多条相关推文可以合并为一条快讯（如同一主题的连续推文）
- 过滤掉纯闲聊、表情回复、无实质内容的推文
- 研究论文、安全报告属于 industry 分类

额外信息：JustinLin610是Qwen团队成员，Hx1u0是Kimi团队成员。

# 输出要求
请严格按照以下 JSON 格式输出，不要输出任何其他内容：

{
  "summary": "2-3句话的整体总结，用【】标记重点词汇",
  "total": 3,
  "items": [
    {
      "category": "model",
      "title": "事件标题（一句话概括）",
      "content": "详细内容，用【】标记核心亮点词汇。",
      "source_ids": [1, 3, 5]
    }
  ]
}

# 字段说明
- summary: 整体总结，用2-3句话概括本期速报最重要的几个动态
- category: 必须是 model、product、tutorial、hardware、industry 之一
- title: 事件标题，一句话概括
- content: 详细内容，完整描述，不要省略
- source_ids: 引用的原始推文编号列表

# 重点标记规则
在 summary 和 content 中，用中文方括号【】标记需要强调的重点词汇，例如：
- 产品/模型名称：【Rodin Gen-2】、【Qwen3-Max】
- 核心能力/特性：【局部和增量修改】、【自然语言编辑】
- 重要数据/指标：【排名第一】、【提升50%】
- 关键动作：【正式发布】、【开源】

每条内容标记2-4个重点词即可，不要过度标记。标题不需要标记。

# 链接保留规则
- 如果原文中包含 GitHub 项目链接、产品官网、论文链接等有价值的 URL，必须在 content 中保留完整链接
- 链接格式：在描述后附上链接，如"项目地址：https://github.com/xxx/xxx"
- 不要省略或简化链接，保持原始完整 URL

# 重要规则
- 直接输出 JSON，不要有 ```json 标记或其他任何文字
- 将相关的多条推文合并为一条快讯
- 全中文输出，可保留必要的英文关键词
- summary 要精炼有力，突出最重要的1-2个事件
""").strip()

DEFAULT_DAILY_PROMPT = textwrap.dedent("""
# 角色

你是一位在科技圈备受推崇的专栏主笔和思想者。对待大量的AI科技新闻有着独特的见解，更加擅长将复杂的技术概念和产业趋势，用平实睿智、循循善诱的语言解读给广大的科技爱好者。

# 任务

以下是一批过去24小时内的AI相关推文摘要（JSON数组）。请你据此撰写一篇完整、可直接发布的AI日报。日报必须具有清晰的主题线、信息逻辑与思考温度，像一个真正的人在说话，而不是AI在汇报。
你需要对它们按主题归纳主要事件或观点（比如：新模型发布、AI绘图争议、应用工具热度）。

# 目标读者与风格

- **目标读者**：普通中文科技爱好者，对科技领域有热情和好奇心。
- **核心风格**：平实睿智、有启发性、发人深省、吸引人。语言有独立的逻辑和美感，避免生硬地转述原文。

# 判断逻辑（按优先级）
1、新开源模型（关键词：release, Open source, 开源, 发布, SOTA ,Qwen,GLM 等开源模型发布或更新）
2、商业大模型更新（关键词：ChatGPT, Claude, Gemini, Grok, Kimi, MiniMax等闭源模型动态）
3、模型实测结论（关键词：对比, 跑测试, 实测, 差距, ）
3、AI产品/工具发布与更新（关键词：API，推出，试玩, YouMind, Sora, Codex ，等AI工具动态）
4、github开源项目（关键词：star, 工具, 开源, 分享, 爆火 ,含有github.com链接）
5、提示词创新（出现prompt，实用性工具性的提示词模板）
6、机器人/硬件相关（关键词：Boston Dynamics, Figure, Optimus ,树莓派 等）
7、重大软件的更新（关键词：Chrome、Vscode等）
                                       

# 具体要求：
- 通读提供的所有信源消息，精准识别重要的内容，并内化其核心论点、关键洞察、整体基调。不重要的水文大胆剔除，只留最重要的部分。
- 构思钩子： 基于你对AI领域的理解，设计一个引人入胜的开篇。
- 精准概括描述今日AI界发生的要点，要点之间构建逻辑不生硬。
- 总字数控制在600~1000字。
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
    "quick_json": ModeSettings(
        key="quick_json",
        system_prompt=QUICK_JSON_PROMPT,
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


# ============ JSON 解析和品牌匹配辅助函数 ============

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """从 AI 输出中提取 JSON，处理各种格式问题"""
    text = text.strip()

    # 尝试移除 markdown 代码块标记
    if text.startswith("```"):
        lines = text.split("\n")
        # 移除第一行（```json 或 ```）
        lines = lines[1:]
        # 移除最后的 ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试找到 JSON 对象的边界
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    # 尝试修复常见问题
    # 1. 单引号替换为双引号
    fixed = text.replace("'", '"')
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 2. 处理尾部逗号
    fixed = re.sub(r',\s*}', '}', text)
    fixed = re.sub(r',\s*]', ']', fixed)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    return None


def match_brands(text: str, title: str = "") -> List[str]:
    """从文本中匹配品牌（大小写不敏感）

    Args:
        text: 完整文本（标题+内容）
        title: 标题文本，用于优先排序

    Returns:
        品牌列表，标题中出现的品牌排在前面
    """
    text_lower = text.lower()
    title_lower = title.lower() if title else ""

    title_brands = []  # 标题中匹配到的品牌
    content_brands = []  # 仅在内容中匹配到的品牌

    for brand, keywords in BRAND_KEYWORDS.items():
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                # 检查是否在标题中出现
                if title_lower and keyword_lower in title_lower:
                    if brand not in title_brands:
                        title_brands.append(brand)
                else:
                    if brand not in content_brands and brand not in title_brands:
                        content_brands.append(brand)
                break

    # 标题中的品牌优先
    return title_brands + content_brands


def detect_category(text: str) -> str:
    """根据文本内容检测分类"""
    text_lower = text.lower()
    scores = {}

    for cat_key, cat_info in CATEGORIES.items():
        score = 0
        for keyword in cat_info["keywords"]:
            if keyword.lower() in text_lower:
                score += 1
        scores[cat_key] = score

    # 返回得分最高的分类，如果都是0则返回 industry
    if max(scores.values()) == 0:
        return "industry"
    return max(scores, key=scores.get)


def get_category_name(cat_key: str) -> str:
    """获取分类的中文名称"""
    if cat_key in CATEGORIES:
        return CATEGORIES[cat_key]["name"]
    return "行业资讯"


class Event:
    """通用信源事件"""

    __slots__ = (
        "id",
        "source",
        "source_name",
        "author",
        "title",
        "summary",
        "content",
        "url",
        "published_at",
        "score",
    )

    def __init__(self, raw: dict):
        self.id = raw.get("id")
        self.source = raw.get("source") or "unknown"
        self.source_name = raw.get("source_name") or self.source
        self.author = raw.get("author") or self.source_name
        self.title = (raw.get("title") or raw.get("summary") or "").strip()
        self.summary = (raw.get("summary") or raw.get("content") or "").strip()
        self.content = (raw.get("content") or self.summary).strip()
        self.url = raw.get("url")
        self.published_at = self._parse_datetime(raw.get("published_at"))
        try:
            self.score = float(raw.get("score") or 0)
        except (TypeError, ValueError):
            self.score = 0.0

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[dt.datetime]:
        if not value:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%a %b %d %H:%M:%S %z %Y",
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

    def short_repr(self) -> str:
        """构造 LLM 输入片段"""
        timestamp = self.published_at.strftime("%Y-%m-%d %H:%M") if self.published_at else ""
        snippet = self.content.replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:237] + "..."
        return (
            f"[{self.source_name}] {self.title or self.summary}\n"
            f"时间：{timestamp}\n"
            f"内容：{snippet}\n"
            f"链接：{self.url}"
        )


class DigestAnalyzer:
    """AI 摘要分析器"""

    def __init__(self, mode: str = "quick"):
        self.mode = mode
        self.settings = MODE_SETTINGS[mode]
        self.reports_dir = config.REPORTS_DIR
        self.aggregator = EventAggregator()

    def filter_events(self, events: Sequence[Event], max_age_hours: Optional[int] = None,
                      min_score: float = 0.0) -> List[Event]:
        """过滤事件"""
        now = dt.datetime.now(dt.timezone.utc)
        filtered = []
        for event in events:
            if max_age_hours and event.published_at:
                age_hours = (now - event.published_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    continue
            if event.score < min_score:
                continue
            filtered.append(event)
        return filtered

    def select_top_events(self, events: Sequence[Event], limit: int) -> List[Event]:
        """按照重要度排序"""
        return sorted(events, key=lambda event: event.score, reverse=True)[:limit]

    def build_prompt(self, events: Sequence[Event]) -> str:
        """构建提示词"""
        parts = []
        for idx, event in enumerate(events, start=1):
            parts.append(
                f"{idx}. 来源：{event.source_name}\n"
                f"标题：{event.title}\n"
                f"摘要：{event.summary}\n"
                f"链接：{event.url}\n"
            )
        return "\n".join(parts)

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

    def save_report(self, summary: str, selected_events: Sequence[Event], heading: str) -> DigestOutput:
        """生成并保存报告，同时返回飞书友好的文本"""
        now = dt.datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H%M")

        prefix = self.settings.output_prefix
        if "{date}" in prefix:
            prefix = prefix.replace("{date}", now.strftime("%Y-%m-%d"))

        path = self.reports_dir / f"{prefix}_{timestamp}.md"

        appendix_entries = []
        for idx, event in enumerate(selected_events, start=1):
            snippet = (event.summary or event.content).replace("\n", " ").strip()
            if len(snippet) > 60:
                snippet = snippet[:60].rstrip() + "..."
            appendix_entries.append(
                {
                    "line": f"{idx}. [{event.source_name}] {snippet} {event.url}".rstrip(),
                    "source": event.source,
                }
            )

        content = f"""# {heading}

- 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}

---

{summary.strip()}

---

## 附录：输入推文片段

{chr(10).join(entry['line'] for entry in appendix_entries)}
"""
        path.write_text(content.strip(), encoding="utf-8")

        primary_text = self._format_primary_text(summary, now)
        appendix_text = self._format_appendix_text(appendix_entries, now)
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

    def _format_appendix_text(self, appendix_entries: Sequence[Union[dict, str]],
                              generated_at: dt.datetime) -> str:
        header = f"【速报附录  时间：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}】"
        intro = "以下为本次摘要引用的原始内容片段："
        grouped = {"twitter": [], "rss": [], "other": []}
        for entry in appendix_entries:
            if isinstance(entry, dict):
                source_key = entry.get("source") or "other"
                line = entry.get("line", "")
            else:
                line = str(entry)
                lower_line = line.lower()
                if "twitter.com" in lower_line or "x.com" in lower_line:
                    source_key = "twitter"
                elif lower_line.startswith("http") or "http" in lower_line:
                    source_key = "rss"
                else:
                    source_key = "other"
                line = str(entry)
            if source_key not in grouped:
                grouped[source_key] = []
            normalized = self._normalize_inline(line)
            normalized = normalized.replace("[", "").replace("]", "")
            grouped[source_key].append(normalized)

        sections = [header, intro, ""]
        if grouped.get("twitter"):
            sections.extend(["【Twitter】", *grouped["twitter"], ""])
        if grouped.get("rss"):
            sections.extend(["【RSS】", *grouped["rss"], ""])
        if grouped.get("other"):
            sections.extend(["【其他来源】", *grouped["other"], ""])
        return "\n".join(sections).rstrip()

    def _resolve_daily_date(self, explicit_date: Optional[str]) -> str:
        if explicit_date:
            return explicit_date

        yesterday = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
        if self._has_any_source_for_date(yesterday):
            return yesterday
        raise FileNotFoundError(
            f"未找到昨天({yesterday})的 Twitter/RSS 数据，请先运行采集任务。"
        )

    def _has_any_source_for_date(self, date_str: str) -> bool:
        twitter_file = config.TWEETS_DIR / f"tweets_{date_str}.jsonl"
        rss_file = config.RSS_DIR / f"rss_{date_str}.jsonl"
        return twitter_file.exists() or rss_file.exists()

    def run(self, date: Optional[str] = None, limit: Optional[int] = None,
            max_age: Optional[int] = None):
        """执行分析任务"""
        if self.mode == "quick":
            target_date = None
        else:
            target_date = self._resolve_daily_date(date)

        raw_events, aggregated_path = self.aggregator.gather(date=target_date)

        # 准备标题
        heading = self.settings.heading
        if target_date and "{date}" in heading:
            heading = heading.replace("{date}", target_date)

        events = [Event(item) for item in raw_events]

        if max_age is None:
            max_age = self.settings.default_max_age

        events = self.filter_events(events, max_age_hours=max_age)

        if not events:
            raise ValueError("没有符合筛选条件的事件，停止生成摘要。")

        limit = limit or self.settings.default_limit
        selected = self.select_top_events(events, limit=min(limit, len(events)))

        prompt = self.build_prompt(selected)
        summary = self.call_ai(prompt)

        output = self.save_report(summary, selected, heading)
        print(f"[{self.mode}] 汇总数据来源：{aggregated_path}")
        print(f"[{self.mode}] 摘要已写入 {output.report_path}")
        return output

    def run_json(self, date: Optional[str] = None, limit: Optional[int] = None,
                 max_age: Optional[int] = None) -> Dict[str, Any]:
        """执行分析任务并输出 JSON 格式（用于网页渲染）"""
        target_date = None  # 快讯模式不需要日期

        raw_events, aggregated_path = self.aggregator.gather(date=target_date)
        events = [Event(item) for item in raw_events]

        # 统计信源数量（采集的总数，按来源类型分组）
        source_stats = {"twitter": 0, "rss": 0}
        for event in events:
            source_type = event.source.lower() if event.source else "other"
            if "twitter" in source_type:
                source_stats["twitter"] += 1
            elif "rss" in source_type:
                source_stats["rss"] += 1

        if max_age is None:
            max_age = self.settings.default_max_age

        events = self.filter_events(events, max_age_hours=max_age)

        if not events:
            raise ValueError("没有符合筛选条件的事件，停止生成摘要。")

        limit = limit or self.settings.default_limit
        selected = self.select_top_events(events, limit=min(limit, len(events)))

        # 构建 prompt 并调用 AI
        prompt = self.build_prompt(selected)
        ai_response = self.call_ai(prompt)

        # 调试输出：便于了解运行状态和排查问题
        print(f"[quick_json] 发送给 AI 的事件数量: {len(selected)}")
        print(f"[quick_json] AI 响应长度: {len(ai_response)} 字符")

        # 解析 AI 的 JSON 响应
        parsed = extract_json_from_text(ai_response)

        if parsed is None:
            print(f"[警告] AI 未返回有效 JSON，尝试使用备用解析")
            print(f"[警告] AI 原始响应: {ai_response[:500]}")
            # 备用方案：将 AI 响应作为纯文本处理
            parsed = self._fallback_parse(ai_response, selected)

        # 获取期数
        issue_number = get_next_issue_number()
        print(f"[quick_json] 本期期数: 第{issue_number}期")

        # 处理并补充品牌信息
        result = self._process_json_result(parsed, selected, issue_number, source_stats)

        # 保存 JSON 文件
        json_path = self._save_web_json(result)
        print(f"[quick_json] 汇总数据来源：{aggregated_path}")
        print(f"[quick_json] JSON 已写入 {json_path}")

        return result

    def _fallback_parse(self, ai_response: str, selected: Sequence[Event]) -> Dict[str, Any]:
        """备用解析：当 AI 未返回有效 JSON 时，从文本中提取信息"""
        items = []
        lines = ai_response.strip().split("\n")

        current_item = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测新条目开始（一、二、三...）
            match = re.match(r'^[一二三四五六七八九十]+[、.]\s*(.+)$', line)
            if match:
                if current_item:
                    items.append(current_item)
                title = match.group(1).strip()
                current_item = {
                    "category": detect_category(title),
                    "title": title[:50],  # 限制标题长度
                    "content": "",
                    "source_ids": []
                }
            elif current_item and line.startswith("·"):
                # 详情行
                current_item["content"] += line[1:].strip() + " "
            elif current_item and not line.startswith("AI总结"):
                # 其他内容行
                if not current_item["content"]:
                    current_item["content"] = line

        if current_item:
            items.append(current_item)

        return {
            "total": len(items),
            "items": items
        }

    def _process_json_result(self, parsed: Dict[str, Any],
                              selected: Sequence[Event],
                              issue_number: int = 0,
                              source_stats: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """处理 AI 返回的 JSON，补充品牌信息和来源详情"""
        now = dt.datetime.now()
        if source_stats is None:
            source_stats = {"twitter": 0, "rss": 0}

        # 构建事件索引映射
        event_map = {idx + 1: event for idx, event in enumerate(selected)}

        processed_items = []
        for item in parsed.get("items", []):
            title = item.get('title', '')
            content = item.get('content', '')
            # 合并标题和内容用于品牌匹配
            full_text = f"{title} {content}"

            # 匹配品牌（标题中的品牌优先）
            brands = match_brands(full_text, title=title)

            # 确保分类有效
            category = item.get("category", "industry")
            if category not in CATEGORIES:
                category = detect_category(full_text)

            # 获取来源详情
            source_ids = item.get("source_ids", [])
            sources = []
            for sid in source_ids:
                if sid in event_map:
                    event = event_map[sid]
                    sources.append({
                        "author": event.author or event.source_name,
                        "url": event.url,
                        "source_type": event.source
                    })

            # 如果没有指定来源，尝试从所有事件中匹配
            if not sources:
                for event in selected:
                    event_text = f"{event.title} {event.content}"
                    # 简单匹配：检查标题关键词是否在事件中出现
                    title_words = item.get("title", "").split()[:3]
                    if any(word in event_text for word in title_words if len(word) > 2):
                        sources.append({
                            "author": event.author or event.source_name,
                            "url": event.url,
                            "source_type": event.source
                        })
                        if len(sources) >= 3:  # 最多关联3个来源
                            break

            processed_items.append({
                "category": category,
                "category_name": get_category_name(category),
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "brands": brands,
                "sources": sources
            })

        # 构建完整的附录（所有来源）
        all_sources = []
        for idx, event in enumerate(selected, start=1):
            snippet = (event.summary or event.content).replace("\n", " ").strip()
            if len(snippet) > 60:
                snippet = snippet[:60].rstrip() + "..."
            all_sources.append({
                "index": idx,
                "author": event.author or event.source_name,
                "snippet": snippet,
                "url": event.url,
                "source_type": event.source
            })

        return {
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "generated_time": now.strftime("%H:%M"),
            "date_display": now.strftime("%Y-%m-%d"),
            "issue_number": issue_number,
            "source_stats": source_stats,
            "summary": parsed.get("summary", ""),  # AI 生成的整体总结
            "total": len(processed_items),
            "items": processed_items,
            "all_sources": all_sources
        }

    def _save_web_json(self, result: Dict[str, Any]) -> Path:
        """保存 JSON 到 web-json 目录"""
        now = dt.datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H%M")

        # 保存带时间戳的版本
        json_path = config.WEB_JSON_DIR / f"quick_{timestamp}.json"
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        # 同时保存 latest 版本（方便 PHP 读取）
        latest_path = config.WEB_JSON_DIR / "quick_latest.json"
        latest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        return json_path


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="AI 推文摘要分析")
    parser.add_argument("--mode", choices=["quick", "quick_json", "daily"], default="quick")
    parser.add_argument("--date", help="日报日期 (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, help="推文数量限制")
    parser.add_argument("--max-age", type=int, help="最大时间范围（小时）")
    args = parser.parse_args()

    analyzer = DigestAnalyzer(mode=args.mode)

    if args.mode == "quick_json":
        result = analyzer.run_json(date=args.date, limit=args.limit, max_age=args.max_age)
        print(f"生成了 {result['total']} 条快讯")
    else:
        analyzer.run(date=args.date, limit=args.limit, max_age=args.max_age)


if __name__ == "__main__":
    main()
