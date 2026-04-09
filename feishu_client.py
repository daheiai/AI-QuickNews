"""飞书机器人发送工具。

默认使用用户提供的应用信息，可通过环境变量覆盖：
- FEISHU_APP_ID
- FEISHU_APP_SECRET
- FEISHU_CHAT_ID
- FEISHU_TOKEN_CACHE (可选，默认为 ~/.cache/feishu_token.json)

示例：
    python feishu_client.py --text "测试内容"
    python feishu_client.py --file ai_reports/ai_quick_2025-11-06_1816.md
    python feishu_client.py --mode quick  # 自动发送最新快讯
    python feishu_client.py --mode daily  # 自动发送最新日报
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
DEFAULT_CHAT_ID = os.getenv("FEISHU_CHAT_ID", "")
TOKEN_CACHE_PATH = Path(os.getenv("FEISHU_TOKEN_CACHE", "~/.cache/feishu_token.json")).expanduser()
DEFAULT_REPORTS_DIR = Path(os.getenv("AI_REPORTS_DIR", "ai_reports"))


def _load_cached_token() -> Optional[str]:
    if not TOKEN_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    token = data.get("token")
    expires_at = data.get("expires_at", 0)
    if not token or expires_at <= time.time() + 120:  # 预留 2 分钟
        return None
    return token


def _store_cached_token(token: str, expires_in: int) -> None:
    TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "token": token,
        "expires_at": time.time() + max(expires_in - 120, 300),
    }
    TOKEN_CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")


def get_tenant_access_token() -> str:
    if not APP_ID or not APP_SECRET:
        raise RuntimeError("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET，无法获取凭证。")

    cached = _load_cached_token()
    if cached:
        return cached

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败：{data}")

    token = data.get("tenant_access_token")
    expires_in = int(data.get("expire") or data.get("expire_in") or 7200)
    if not token:
        raise RuntimeError(f"响应缺少 tenant_access_token：{data}")

    _store_cached_token(token, expires_in)
    return token


def _truncate(text: str, limit: int = 3500) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _find_latest_report(prefix: str, reports_dir: Path) -> Path:
    reports_dir = reports_dir.expanduser()
    if not reports_dir.exists():
        raise FileNotFoundError(f"报告目录不存在：{reports_dir}")

    candidates = [p for p in reports_dir.glob(f"{prefix}_*.md") if p.is_file()]
    if not candidates:
        raise FileNotFoundError(f"未在 {reports_dir} 找到匹配 {prefix}_*.md 的文件")

    return max(candidates, key=lambda p: p.stat().st_mtime)


def send_text_message(text: str, *, chat_id: Optional[str] = None) -> None:
    if not text.strip():
        raise ValueError("文本内容为空，无法发送。")

    target_chat = chat_id or DEFAULT_CHAT_ID
    if not target_chat:
        raise RuntimeError("缺少目标 chat_id，可通过参数 --chat-id 或环境变量 FEISHU_CHAT_ID 指定。")

    token = get_tenant_access_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "receive_id": target_chat,
        "msg_type": "text",
        "content": json.dumps({"text": _truncate(text)}),
    }
    params = {"receive_id_type": "chat_id"}

    response = requests.post(url, params=params, headers=headers, json=payload, timeout=15)
    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text}

    if response.status_code != 200 or data.get("code") not in (None, 0):
        raise RuntimeError(
            "飞书发送失败："
            f"status={response.status_code}, "
            f"response={data}"
        )


def _read_input(args: argparse.Namespace) -> tuple[str, Optional[Path]]:
    if args.text:
        return args.text, None
    if args.file:
        file_path = Path(args.file)
        content = file_path.read_text(encoding="utf-8")
        return content, file_path
    if args.mode:
        prefix = "ai_quick" if args.mode == "quick" else "ai_daily"
        reports_dir = args.reports_dir
        latest_path = _find_latest_report(prefix, reports_dir)
        content = latest_path.read_text(encoding="utf-8")
        return content, latest_path
    raise ValueError("必须提供 --text、--file 或 --mode。")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通过飞书机器人发送文本消息")
    parser.add_argument("--text", help="要发送的文本内容")
    parser.add_argument("--file", help="读取文件内容后发送")
    parser.add_argument(
        "--mode",
        choices=["quick", "daily"],
        help="按模式选择 ai_reports 目录下最新的摘要文件",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help="摘要文件目录，默认 ai_reports",
    )
    parser.add_argument(
        "--chat-id",
        help="指定接收消息的 chat_id，默认使用配置的 FEISHU_CHAT_ID",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    try:
        content, source_file = _read_input(args)
        send_text_message(content, chat_id=args.chat_id)
    except Exception as exc:  # noqa: BLE001
        print(f"发送失败：{exc}", file=sys.stderr)
        sys.exit(1)
    else:
        if source_file:
            print(f"飞书消息发送成功，来源文件：{source_file}")
        else:
            print("飞书消息发送成功。")


if __name__ == "__main__":
    main()
