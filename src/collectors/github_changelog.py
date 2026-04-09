"""GitHub Changelog 采集器 - 抓取、翻译、总结 GitHub Releases"""
import json
import sys
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

import config


class GitHubChangelogCollector:
    """GitHub Releases 采集器"""

    GITHUB_API_BASE = "https://api.github.com"
    BEIJING_TZ = timezone(timedelta(hours=8))
    RECENT_IDS_FILENAME = "recent_ids.json"
    RECENT_IDS_LIMIT = 1000

    def __init__(self):
        self.repos = config.GITHUB_REPOS
        self.api_token = config.GITHUB_API_TOKEN
        self.check_interval = config.GITHUB_CHECK_INTERVAL_HOURS
        self.output_dir = config.GITHUB_DIR
        self.changelog_json_dir = config.CHANGELOG_JSON_DIR
        self.log_dir = config.LOGS_DIR
        self.recent_ids_path = self.output_dir / self.RECENT_IDS_FILENAME
        self.recent_ids = self._load_recent_ids()

        # AI 配置
        self.ai_base_url = config.OPENAI_BASE_URL
        self.ai_api_key = config.OPENAI_API_KEY
        self.ai_model = config.OPENAI_MODEL

    def _load_recent_ids(self) -> "OrderedDict[str, None]":
        """加载近期去重ID缓存"""
        if not self.recent_ids_path.exists():
            return OrderedDict()
        try:
            data = json.loads(self.recent_ids_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.log(f"recent_ids 文件损坏，忽略 {self.recent_ids_path}")
            return OrderedDict()

        if not isinstance(data, list):
            return OrderedDict()

        ids = OrderedDict()
        for item in data[-self.RECENT_IDS_LIMIT :]:
            if not item:
                continue
            ids[str(item)] = None
        return ids

    def _persist_recent_ids(self):
        """写回近期ID缓存"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        payload = list(self.recent_ids.keys())[-self.RECENT_IDS_LIMIT :]
        self.recent_ids_path.write_text(json.dumps(payload), encoding="utf-8")

    def _remember_ids(self, ordered_ids: List[str]):
        """更新缓存，保留最近的若干ID用于去重"""
        for release_id in ordered_ids:
            if not release_id:
                continue
            if release_id in self.recent_ids:
                self.recent_ids.move_to_end(release_id)
            else:
                self.recent_ids[release_id] = None
            while len(self.recent_ids) > self.RECENT_IDS_LIMIT:
                self.recent_ids.popitem(last=False)
        if ordered_ids:
            self._persist_recent_ids()

    def log(self, message: str):
        """记录日志"""
        now = datetime.now(self.BEIJING_TZ)
        log_file = self.log_dir / f"github_{now.strftime('%Y-%m-%d')}.log"
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(log_msg + "\n")

    def _get_headers(self) -> Dict[str, str]:
        """构建 GitHub API 请求头"""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def fetch_releases(self, owner: str, repo: str, since_time: datetime) -> Optional[List[dict]]:
        """获取指定仓库的 releases，支持分页获取全部历史"""
        all_releases = []
        page = 1

        try:
            while True:
                url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
                params = {"per_page": 100, "page": page}
                response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
                response.raise_for_status()
                releases = response.json()

                if not releases:
                    break  # 没有更多数据了

                # 过滤时间范围内的 releases
                found_any = False
                for release in releases:
                    published_at = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))
                    if published_at >= since_time:
                        all_releases.append(release)
                        found_any = True
                    # 如果这页最后一条已经早于 since_time，后面的页也不用翻了
                    else:
                        if not found_any:
                            return all_releases
                        break

                # 如果这页不足 100 条，说明已经是最后一页
                if len(releases) < 100:
                    break

                page += 1
                self.log(f"  翻页中... 第 {page} 页")

            return all_releases

        except requests.RequestException as e:
            self.log(f"获取 {owner}/{repo} releases 失败: {e}")
            return None

    def translate_text(self, text: str) -> str:
        """使用 AI 翻译文本"""
        if not text or not text.strip():
            return ""

        prompt = f"""请将以下英文内容翻译成中文，版本号可以不用翻译，其他需要保持原有的格式和结构，：

{text}

只返回翻译后的中文内容，不要添加任何解释。"""

        try:
            response = requests.post(
                f"{self.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.ai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            self.log(f"翻译失败: {e}")
            return text  # 翻译失败则返回原文

    def summarize_release(self, title: str, body: str) -> str:
        """使用 AI 总结 release 内容"""
        if not body or not body.strip():
            return title

        prompt = f"""请用 1-2 句话总结以下更新日志的核心内容（中文）：

标题：{title}

内容：
{body}

要求：
1. 突出最重要的新功能或改进
2. 简洁明了，不超过 100 字
3. 只返回总结内容，不要添加"总结："等前缀"""

        try:
            response = requests.post(
                f"{self.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.ai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            self.log(f"总结失败: {e}")
            return title

    def _call_ai(self, prompt: str, max_tokens: int = None, timeout: int = 180) -> str:
        """统一的 AI 调用方法"""
        import time
        start_time = time.time()
        self.log(f"  → 调用 AI ({self.ai_model})...")
        if max_tokens:
            self.log(f"  → 参数: max_tokens={max_tokens}, timeout={timeout}s")
        else:
            self.log(f"  → 参数: 无 token 限制, timeout={timeout}s")

        payload = {
            "model": self.ai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        # 只有明确指定时才加 max_tokens
        if max_tokens:
            payload["max_tokens"] = max_tokens

        # timeout 设置为 (连接超时, 读取超时)
        response = requests.post(
            f"{self.ai_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.ai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(30, timeout),  # (连接超时30秒, 读取超时使用传入的值)
        )
        response.raise_for_status()
        elapsed = time.time() - start_time
        self.log(f"  ✓ AI 响应完成 (耗时 {elapsed:.1f}s)")
        return response.json()["choices"][0]["message"]["content"].strip()

    def batch_translate_and_summarize(self, releases: List[dict]) -> List[dict]:
        """批量翻译 + 总结，一次 API 调用处理多个 release"""
        if not releases:
            return []

        BATCH_SIZE = 3  # 减少批量数量，避免超时

        results = []
        for i in range(0, len(releases), BATCH_SIZE):
            batch = releases[i: i + BATCH_SIZE]
            self.log(f"  批量处理第 {i + 1}-{i + len(batch)} 条 (共 {len(batch)} 条)...")

            # 构建批量请求
            items_text = ""
            for idx, r in enumerate(batch):
                title = r["name"] or r["tag_name"]
                body = (r["body"] or "").strip()
                items_text += f"=== ITEM_{idx} ===\n标题: {title}\n内容:\n{body}\n\n"

            prompt = f"""请对以下 {len(batch)} 个 GitHub Release 更新日志进行处理，每条需要：
1. 将标题翻译成中文
2. 将内容翻译成中文（保持原有格式）
3. 用 1-2 句话总结核心内容（不超过 100 字）

严格按照以下 JSON 格式返回，不要添加任何其他内容：
[
  {{"idx": 0, "title_cn": "中文标题", "body_cn": "中文内容", "summary": "总结"}},
  {{"idx": 1, "title_cn": "中文标题", "body_cn": "中文内容", "summary": "总结"}},
  ...
]

待处理内容：
{items_text}"""

            try:
                self.log(f"  → 发送批量请求 (约 {len(items_text)} 字符)...")
                self.log(f"  → Prompt 总长度: {len(prompt)} 字符")

                # DEBUG: 保存完整 prompt 到文件查看
                debug_file = self.output_dir / "debug_prompt.txt"
                debug_file.write_text(prompt, encoding="utf-8")  # 保存完整内容
                self.log(f"  → DEBUG: 完整 Prompt 已保存到 {debug_file}")

                # 3 条 release 预估输出 ~3000 tokens 足够
                raw = self._call_ai(prompt, max_tokens=3500, timeout=180)
                self.log(f"  → 解析 AI 返回结果...")

                # 提取 JSON 部分
                start = raw.find("[")
                end = raw.rfind("]") + 1
                if start == -1 or end == 0:
                    raise ValueError("AI 返回格式错误，未找到 JSON 数组")

                parsed = json.loads(raw[start:end])
                self.log(f"  ✓ 成功解析 {len(parsed)} 条结果")

                # 按 idx 映射回结果
                lookup = {item["idx"]: item for item in parsed}
                for idx, r in enumerate(batch):
                    item = lookup.get(idx, {})
                    results.append({
                        "title_cn": item.get("title_cn", r["name"] or r["tag_name"]),
                        "body_cn": item.get("body_cn", r["body"] or ""),
                        "summary": item.get("summary", r["name"] or r["tag_name"]),
                        "success": True  # 批量成功
                    })

            except Exception as e:
                self.log(f"  ✗ 批量处理失败: {e}")
                self.log(f"  → 降级为逐条处理...")
                # 降级：逐条处理
                for idx, r in enumerate(batch):
                    self.log(f"    处理第 {i + idx + 1} 条: {r['tag_name']}")
                    try:
                        title_cn = self._call_ai(
                            f"翻译成中文，只返回翻译结果：{r['name'] or r['tag_name']}", max_tokens=200
                        )
                        body_cn = self._call_ai(
                            f"翻译成中文，保持格式，只返回翻译结果：\n{r['body'] or ''}", max_tokens=3000
                        ) if r.get("body") else ""
                        summary = self._call_ai(
                            f"用1-2句话总结这个更新日志的核心内容（中文，不超过100字）：\n{title_cn}\n{body_cn}", max_tokens=200
                        )
                    except Exception as e2:
                        self.log(f"    ✗ 逐条处理也失败: {e2}")
                        title_cn = r["name"] or r["tag_name"]
                        body_cn = r["body"] or ""
                        summary = title_cn
                    results.append({
                        "title_cn": title_cn,
                        "body_cn": body_cn,
                        "summary": summary,
                        "success": "✗ 逐条处理也失败" not in str(e2) if 'e2' in locals() else True
                    })

        return results

    def process_and_save_one_release(self, release: dict, repo_name: str) -> bool:
        """处理单条 release：翻译 + 立即保存 + 更新 ID"""
        release_id = f"{repo_name}:{release['id']}"

        # 去重检查：只跳过已成功保存过的（检查 JSONL 里是否有 body_cn）
        if release_id in self.recent_ids:
            # 检查是否之前翻译失败（body_cn 为空但 body_en 有内容）
            if not self._needs_retry(release_id, repo_name):
                return False
            self.log(f"  {release_id} 之前翻译失败，重试...")

        tag_name = release["tag_name"]
        self.log(f"  处理 {repo_name} - {tag_name}")

        try:
            # 1. 标题保留原样，不翻译
            title_en = release["name"] or release["tag_name"]
            title_cn = title_en  # 保持原样

            # 2. 翻译内容
            body_en = release["body"] or ""
            body_cn = ""
            if body_en.strip():
                self.log(f"    → 翻译内容 (约 {len(body_en)} 字符)...")
                body_cn = self._call_ai(
                    f"将以下内容翻译成中文，保持原有格式：\n{body_en}",
                    max_tokens=None,  # 不限制，让 AI 自己决定
                    timeout=180
                )
            else:
                self.log(f"    → 无内容，跳过翻译")

            # 3. 构建数据（总结暂时用标题）
            data = {
                "id": release_id,
                "repo_name": repo_name,
                "tag_name": tag_name,
                "title_en": title_en,
                "title_cn": title_cn,
                "body_en": body_en,
                "body_cn": body_cn,
                "summary": title_cn,  # 暂时用标题，后续可单独生成总结
                "url": release["html_url"],
                "published_at": release["published_at"],
                "is_prerelease": release["prerelease"],
                "is_draft": release["draft"],
            }

            # 4. 立即保存到文件（每个仓库单独文件）
            now = datetime.now(self.BEIJING_TZ)
            date_str = now.strftime("%Y-%m-%d")
            safe_repo_name = repo_name.lower().replace(" ", "_")
            repo_file = self.output_dir / f"{safe_repo_name}_{date_str}.jsonl"

            with repo_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

            # 5. 立即更新 ID 缓存
            self._remember_ids([release_id])

            self.log(f"    ✓ 已保存并更新 ID")
            return True

        except Exception as e:
            self.log(f"    ✗ 处理失败: {e}")
            # 翻译失败也保存（body_cn 为空），下次可以重试翻译
            try:
                data = {
                    "id": release_id,
                    "repo_name": repo_name,
                    "tag_name": release["tag_name"],
                    "title_en": release["name"] or release["tag_name"],
                    "title_cn": release["name"] or release["tag_name"],
                    "body_en": release["body"] or "",
                    "body_cn": "",
                    "summary": release["name"] or release["tag_name"],
                    "url": release["html_url"],
                    "published_at": release["published_at"],
                    "is_prerelease": release["prerelease"],
                    "is_draft": release["draft"],
                }
                now = datetime.now(self.BEIJING_TZ)
                date_str = now.strftime("%Y-%m-%d")
                safe_repo_name = repo_name.lower().replace(" ", "_")
                repo_file = self.output_dir / f"{safe_repo_name}_{date_str}.jsonl"
                with repo_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
                self._remember_ids([release_id])
                self.log(f"    → 已保存未翻译版本，下次运行会重试翻译")
            except Exception:
                pass
            return False

    def _needs_retry(self, release_id: str, repo_name: str) -> bool:
        """检查某个 release 是否需要重试翻译（之前保存了但 body_cn 为空，或根本没保存）"""
        safe_repo_name = repo_name.lower().replace(" ", "_")
        found = False
        # 扫描该仓库的所有 JSONL 文件
        for jsonl_file in self.output_dir.glob(f"{safe_repo_name}_*.jsonl"):
            try:
                for line in jsonl_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    if item.get("id") == release_id:
                        found = True
                        # 有英文内容但没中文翻译 → 需要重试
                        if item.get("body_en", "").strip() and not item.get("body_cn", "").strip():
                            return True
                        return False
            except (json.JSONDecodeError, OSError):
                continue
        # ID 在缓存里但 JSONL 里找不到 → 需要重新处理
        return True

    def process_releases(self, releases: List[dict], repo_name: str) -> int:
        """逐条处理 releases，返回成功数量"""
        success_count = 0

        for release in releases:
            if self.process_and_save_one_release(release, repo_name):
                success_count += 1

        return success_count

    def save_releases(self, releases: List[dict]) -> int:
        """保存 releases 到文件"""
        if not releases:
            return 0

        now = datetime.now(self.BEIJING_TZ)
        date_str = now.strftime("%Y-%m-%d")

        # 保存原始数据到 sources/github/
        daily_file = self.output_dir / f"releases_{date_str}.jsonl"

        new_count = 0
        with daily_file.open("a", encoding="utf-8") as f:
            for release in releases:
                f.write(json.dumps(release, ensure_ascii=False) + "\n")
                new_count += 1

        # 更新去重缓存
        self._remember_ids([r["id"] for r in releases])

        # 生成 web-json 格式
        self._generate_web_json(releases)

        return new_count

    def _generate_web_json(self, releases: List[dict]):
        """生成网站用的 JSON 文件"""
        # 按仓库分组
        by_repo = {}
        for release in releases:
            repo = release["repo_name"]
            if repo not in by_repo:
                by_repo[repo] = []
            by_repo[repo].append(release)

        # 为每个仓库生成 latest.json
        for repo_name, repo_releases in by_repo.items():
            # 按时间排序，最新的在前
            repo_releases.sort(key=lambda x: x["published_at"], reverse=True)

            output = {
                "repo_name": repo_name,
                "generated_at": datetime.now(self.BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                "total": len(repo_releases),
                "releases": [
                    {
                        "tag_name": r["tag_name"],
                        "title": r["title_cn"],
                        "summary": r["summary"],
                        "body": r["body_cn"],
                        "url": r["url"],
                        "published_at": r["published_at"],
                        "is_prerelease": r["is_prerelease"],
                    }
                    for r in repo_releases[:5]  # 只保留最近 5 个
                ],
            }

            # 保存到 changelog 目录
            safe_name = repo_name.lower().replace(" ", "_")
            output_file = self.changelog_json_dir / f"{safe_name}_latest.json"
            output_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    def build_since_time(self) -> datetime:
        """构建查询起始时间"""
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=self.check_interval)
        return since

    def run(self):
        """执行采集任务"""
        self.log("=" * 50)
        self.log("GitHub Changelog 采集开始")

        since_time = self.build_since_time()
        self.log(f"抓取近 {self.check_interval} 小时内的 releases")

        total_success = 0

        for repo_config in self.repos:
            owner = repo_config["owner"]
            repo = repo_config["repo"]
            name = repo_config["name"]

            self.log(f"正在获取 {name} ({owner}/{repo})")

            releases = self.fetch_releases(owner, repo, since_time)

            if releases is None:
                self.log(f"{name} 获取失败，跳过")
                continue

            if not releases:
                self.log(f"{name} 无新 releases")
                continue

            self.log(f"{name} 找到 {len(releases)} 个新 releases")

            # 逐条处理：翻译 + 立即保存
            success = self.process_releases(releases, name)
            total_success += success
            self.log(f"{name} 完成，成功 {success} 条")

        self.log(f"全部完成，共成功处理 {total_success} 条")
        self.log("采集完成")


def main():
    """命令行入口"""
    collector = GitHubChangelogCollector()
    collector.run()


if __name__ == "__main__":
    main()
