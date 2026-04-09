#!/usr/bin/env python3
"""
批量重译 GitHub Changelog 未翻译的记录
扫描 data/sources/github/ 下的所有 JSONL 文件，找出 body_cn 为空的记录并重新翻译
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 添加项目根目录到路径，以便导入 config
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

import config

# 配置
GITHUB_DIR = config.GITHUB_DIR  # data/sources/github/
BEIJING_TZ = timezone(timedelta(hours=8))

# AI 配置
AI_BASE_URL = config.CHANGELOG_AI_BASE_URL
AI_API_KEY = config.CHANGELOG_AI_API_KEY
AI_MODEL = config.CHANGELOG_AI_MODEL


class BatchTranslator:
    """批量翻译器"""

    def __init__(self):
        self.stats = {
            "total_files": 0,
            "total_records": 0,
            "need_translate": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

    def log(self, message: str):
        """打印日志"""
        now = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {message}")

    def translate_text(self, text: str) -> str:
        """调用 AI 翻译文本"""
        if not text or not text.strip():
            return ""

        prompt = f"""请将以下英文内容翻译成中文，版本号可以不用翻译，其他需要保持原有的格式和结构：

{text}

只返回翻译后的中文内容，不要添加任何解释。"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                import requests

                response = requests.post(
                    f"{AI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {AI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": AI_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 4000,
                    },
                    timeout=180,  # 增加到 180 秒
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()

            except Exception as e:
                if attempt < max_retries - 1:
                    self.log(f"    翻译失败，{max_retries - attempt - 1}秒后重试: {e}")
                    time.sleep(5)
                else:
                    self.log(f"    翻译失败: {e}")
                    return ""

        return ""

    def scan_and_translate(self) -> dict:
        """扫描所有 JSONL 文件，找出需要翻译的记录并处理"""
        github_dir = Path(GITHUB_DIR)

        if not github_dir.exists():
            self.log(f"目录不存在: {github_dir}")
            return self.stats

        # 获取所有 JSONL 文件
        jsonl_files = sorted(github_dir.glob("*.jsonl"))
        self.log(f"找到 {len(jsonl_files)} 个 JSONL 文件")

        for jsonl_file in jsonl_files:
            self.stats["total_files"] += 1
            self.process_file(jsonl_file)

        return self.stats

    def process_file(self, jsonl_file: Path):
        """处理单个 JSONL 文件"""
        self.log(f"\n处理文件: {jsonl_file.name}")

        # 读取所有行
        lines = []
        try:
            content = jsonl_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.splitlines() if line.strip()]
        except Exception as e:
            self.log(f"  读取文件失败: {e}")
            return

        self.stats["total_records"] += len(lines)

        # 解析并找出需要翻译的记录
        records_to_translate = []
        for idx, line in enumerate(lines):
            try:
                item = json.loads(line)
                # 检查是否需要翻译
                body_en = item.get("body_en", "").strip()
                body_cn = item.get("body_cn", "").strip()

                # 需要翻译的条件：英文内容存在，但中文为空
                if body_en and not body_cn:
                    records_to_translate.append((idx, item))
            except json.JSONDecodeError:
                continue

        if not records_to_translate:
            self.log(f"  无需翻译的记录")
            self.stats["skipped"] += len(lines)
            return

        self.log(
            f"  发现 {len(records_to_translate)} 条需要翻译（共 {len(lines)} 条记录）"
        )
        self.stats["need_translate"] += len(records_to_translate)

        # 处理需要翻译的记录
        updated_lines = list(lines)
        for idx, item in records_to_translate:
            release_id = item.get("id", "unknown")
            tag_name = item.get("tag_name", "unknown")
            body_en = item.get("body_en", "")

            self.log(f"  翻译: {tag_name} ({release_id})")

            # 翻译
            body_cn = self.translate_text(body_en)

            if body_cn:
                # 更新记录
                item["body_cn"] = body_cn

                # 如果 summary 还是英文标题，尝试翻译
                if item.get("summary") == item.get("title_en"):
                    item["summary"] = (
                        body_cn.split("\n")[0][:100] if body_cn else item["summary"]
                    )

                # 写回对应行
                updated_lines[idx] = json.dumps(item, ensure_ascii=False)
                self.stats["success"] += 1
                self.log(f"    ✓ 翻译成功")
            else:
                self.stats["failed"] += 1
                self.log(f"    ✗ 翻译失败")

            # 避免 API 过载
            time.sleep(1)

        # 写回文件
        try:
            jsonl_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
            self.log(f"  ✓ 文件已更新")
        except Exception as e:
            self.log(f"  ✗ 写回文件失败: {e}")


def main():
    print("=" * 60)
    print("批量重译 GitHub Changelog")
    print("=" * 60)

    translator = BatchTranslator()
    stats = translator.scan_and_translate()

    print("\n" + "=" * 60)
    print("处理完成!")
    print(f"  文件数: {stats['total_files']}")
    print(f"  总记录: {stats['total_records']}")
    print(f"  需翻译: {stats['need_translate']}")
    print(f"  翻译成功: {stats['success']}")
    print(f"  翻译失败: {stats['failed']}")
    print(f"  跳过(无需翻译): {stats['skipped']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
