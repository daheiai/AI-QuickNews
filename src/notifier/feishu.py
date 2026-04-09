"""飞书通知器"""
import json
import time
from pathlib import Path
from typing import Optional

import requests

import config


class FeishuNotifier:
    """飞书机器人通知器"""

    def __init__(self):
        self.app_id = config.FEISHU_APP_ID
        self.app_secret = config.FEISHU_APP_SECRET
        self.chat_id = config.FEISHU_CHAT_ID
        self.token_cache_path = config.FEISHU_TOKEN_CACHE
        self.reports_dir = config.REPORTS_DIR

    def _load_cached_token(self) -> Optional[str]:
        """加载缓存的 token"""
        if not self.token_cache_path.exists():
            return None
        try:
            data = json.loads(self.token_cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        token = data.get("token")
        expires_at = data.get("expires_at", 0)
        if not token or expires_at <= time.time() + 120:
            return None
        return token

    def _store_cached_token(self, token: str, expires_in: int):
        """存储 token 到缓存"""
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "token": token,
            "expires_at": time.time() + max(expires_in - 120, 300),
        }
        self.token_cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def get_access_token(self) -> str:
        """获取访问令牌"""
        if not self.app_id or not self.app_secret:
            raise RuntimeError("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET")

        cached = self._load_cached_token()
        if cached:
            return cached

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise RuntimeError(f"获取 tenant_access_token 失败：{data}")

        token = data.get("tenant_access_token")
        expires_in = int(data.get("expire") or data.get("expire_in") or 7200)
        if not token:
            raise RuntimeError(f"响应缺少 tenant_access_token：{data}")

        self._store_cached_token(token, expires_in)
        return token

    def send_message(self, text: str, chat_id: Optional[str] = None):
        """发送文本消息"""
        if not text.strip():
            raise ValueError("文本内容为空")

        target_chat = chat_id or self.chat_id
        if not target_chat:
            raise RuntimeError("缺少目标 chat_id")

        # 截断过长的文本
        if len(text) > 3500:
            text = text[:3497] + "..."

        token = self.get_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload = {
            "receive_id": target_chat,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }
        params = {"receive_id_type": "chat_id"}

        response = requests.post(url, params=params, headers=headers, json=payload, timeout=15)
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.status_code != 200 or data.get("code") not in (None, 0):
            raise RuntimeError(f"飞书发送失败：status={response.status_code}, response={data}")

    def find_latest_report(self, prefix: str) -> Path:
        """查找最新的报告文件"""
        if not self.reports_dir.exists():
            raise FileNotFoundError(f"报告目录不存在：{self.reports_dir}")

        candidates = [p for p in self.reports_dir.glob(f"{prefix}_*.md") if p.is_file()]
        if not candidates:
            raise FileNotFoundError(f"未在 {self.reports_dir} 找到匹配 {prefix}_*.md 的文件")

        return max(candidates, key=lambda p: p.stat().st_mtime)

    def send_report(self, mode: str, chat_id: Optional[str] = None):
        """发送报告"""
        prefix = "ai_quick" if mode == "quick" else "ai_daily"
        latest_path = self.find_latest_report(prefix)
        content = latest_path.read_text(encoding="utf-8")
        self.send_message(content, chat_id=chat_id)
        print(f"飞书消息发送成功，来源文件：{latest_path}")


def main():
    """命令行入口"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="飞书消息推送")
    parser.add_argument("--text", help="直接发送文本内容")
    parser.add_argument("--file", help="发送文件内容")
    parser.add_argument("--mode", choices=["quick", "daily"], help="发送最新报告")
    parser.add_argument("--chat-id", help="指定接收消息的 chat_id")
    args = parser.parse_args()

    notifier = FeishuNotifier()

    try:
        if args.text:
            notifier.send_message(args.text, chat_id=args.chat_id)
            print("飞书消息发送成功")
        elif args.file:
            content = Path(args.file).read_text(encoding="utf-8")
            notifier.send_message(content, chat_id=args.chat_id)
            print(f"飞书消息发送成功，来源文件：{args.file}")
        elif args.mode:
            notifier.send_report(args.mode, chat_id=args.chat_id)
        else:
            print("必须提供 --text、--file 或 --mode", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"发送失败：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
