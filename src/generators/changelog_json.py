"""将 JSONL 源数据汇总为网页用的 changelog_all.json"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
import config


BEIJING_TZ = timezone(timedelta(hours=8))

# 仓库元信息
REPO_META = {r["name"]: {"owner": r["owner"], "repo": r["repo"]} for r in config.GITHUB_REPOS}
REPO_ORDER = [r["name"] for r in config.GITHUB_REPOS]


def load_all_releases() -> dict:
    """扫描所有 JSONL 文件，按仓库汇总并去重"""
    github_dir = config.GITHUB_DIR
    seen_ids: set[str] = set()
    by_repo: dict[str, list] = {}

    for jsonl_file in sorted(github_dir.glob("*.jsonl")):
        if jsonl_file.name == "recent_ids.json":
            continue
        # releases_*.jsonl 是早期混合格式，也需要读取

        with jsonl_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                rid = item.get("id", "")
                if not rid or rid in seen_ids:
                    continue
                seen_ids.add(rid)

                repo_name = item.get("repo_name", "")
                if repo_name not in by_repo:
                    by_repo[repo_name] = []

                by_repo[repo_name].append({
                    "id": rid,
                    "tag_name": item.get("tag_name", ""),
                    "title_en": item.get("title_en", ""),
                    "body_en": item.get("body_en", ""),
                    "body_cn": item.get("body_cn", ""),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", ""),
                    "published_at": item.get("published_at", ""),
                    "is_prerelease": item.get("is_prerelease", False),
                })

    # 按发布时间降序
    for releases in by_repo.values():
        releases.sort(key=lambda r: r["published_at"], reverse=True)

    return by_repo


def generate():
    """生成 changelog_all.json"""
    by_repo = load_all_releases()

    repos = {}
    for name in REPO_ORDER:
        meta = REPO_META.get(name, {})
        releases = by_repo.get(name, [])
        repos[name] = {
            "repo_name": name,
            "owner": meta.get("owner", ""),
            "repo": meta.get("repo", ""),
            "releases": releases,
            "total": len(releases),
        }

    # 补充未在 REPO_ORDER 中但数据里存在的仓库
    for name, releases in by_repo.items():
        if name not in repos:
            repos[name] = {
                "repo_name": name,
                "owner": "",
                "repo": "",
                "releases": releases,
                "total": len(releases),
            }

    output = {
        "generated_at": datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "repos": repos,
    }

    out_path = config.CHANGELOG_JSON_DIR / "changelog_all.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # 统计
    total = sum(r["total"] for r in repos.values())
    print(f"已生成 {out_path}")
    print(f"共 {len(repos)} 个仓库, {total} 条 release")
    for name in REPO_ORDER:
        if name in repos:
            print(f"  {name}: {repos[name]['total']} 条")


if __name__ == "__main__":
    generate()
