"""为每个仓库生成近 10 期更新趋势总结"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
import config

BEIJING_TZ = timezone(timedelta(hours=8))
REPO_ORDER = [r["name"] for r in config.GITHUB_REPOS]


def load_changelog_all() -> dict:
    path = config.CHANGELOG_JSON_DIR / "changelog_all.json"
    if not path.exists():
        print(f"错误: {path} 不存在，请先运行 changelog_json.py")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def call_ai(prompt: str) -> str:
    """调用 AI 生成总结"""
    start = time.time()
    response = requests.post(
        f"{config.OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        },
        timeout=(30, 120),
    )
    response.raise_for_status()
    elapsed = time.time() - start
    print(f"  AI 响应完成 ({elapsed:.1f}s)")
    return response.json()["choices"][0]["message"]["content"].strip()


def generate_trend(repo_name: str, releases: list) -> str:
    """为单个仓库生成趋势总结"""
    recent = releases[:10]
    if not recent:
        return ""

    # 检查是否有实质内容（不只是版本号）
    has_content = False
    items = ""
    for r in recent:
        tag = r["tag_name"]
        date = r["published_at"][:10]
        body = r.get("body_cn") or r.get("body_en") or ""
        items += f"### {tag} ({date})\n{body}\n\n"
        if body.strip():
            has_content = True

    if not has_content:
        return f"近 {len(recent)} 个版本均无详细更新说明。"

    prompt = f"""以下是 {repo_name} 最近 {len(recent)} 个版本的更新日志。

请直接总结这段时间的更新趋势。

要求：
1. 2-3 句话，不超过 150 字
2. 直说结论，不要铺垫（禁止"从更新日志来看"、"从近期版本来看"这类开头）
3. 说具体的事，不说空话套话
4. 如果某些版本没有实质内容（只有版本号），直接忽略，不要编造更新内容
5. 只返回总结，不加标题或前缀

更新日志：
{items}"""

    return call_ai(prompt)


def generate():
    data = load_changelog_all()
    repos = data.get("repos", {})

    trends = {}
    for name in REPO_ORDER:
        repo = repos.get(name)
        releases = repo["releases"] if repo else []
        if not releases:
            print(f"{name}: 无数据，跳过")
            trends[name] = ""
            continue

        print(f"{name}: 分析近 {min(10, len(releases))} 期趋势...")
        try:
            trends[name] = generate_trend(name, releases)
            print(f"  完成")
        except Exception as e:
            print(f"  失败: {e}")
            trends[name] = ""

    output = {
        "generated_at": datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "trends": trends,
    }

    out_path = config.CHANGELOG_JSON_DIR / "changelog_trend.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已生成 {out_path}")


if __name__ == "__main__":
    generate()
