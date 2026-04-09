"""任务调度脚本：串联推特抓取、AI 摘要与飞书推送。

使用方式：
    python orchestrator.py --mode quick  # 刷新数据、生成快讯、发送飞书
    python orchestrator.py --mode daily  # 生成上一日日报、发送飞书

环境要求：
- 已配置 twitter_monitor.py、ai_digest.py、feishu_client.py 所需的环境变量。
- 飞书应用必须开启机器人能力并确保 FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_CHAT_ID 可用。
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import List

BASEROOT = Path(__file__).resolve().parent

PYTHON = sys.executable or "python"

QUICK_COMMANDS = [
    [PYTHON, "twitter_monitor.py"],
    [PYTHON, "ai_digest.py", "--mode", "quick"],
    [PYTHON, "feishu_client.py", "--mode", "quick"],
]

DAILY_SUMMARY_COMMAND = [PYTHON, "ai_digest.py", "--mode", "daily"]
DAILY_PUSH_COMMAND = [PYTHON, "feishu_client.py", "--mode", "daily"]

REPORT_DIR = BASEROOT / "ai_reports"


def run_command(cmd: List[str]) -> None:
    print(f"[orchestrator] 运行命令: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, text=True, cwd=BASEROOT)
    if result.returncode != 0:
        raise RuntimeError(f"命令执行失败 (exit={result.returncode}): {' '.join(cmd)}")


def ensure_yesterday_digest() -> None:
    # 每天 7 点运行日报时，确保目标文件名包含昨日日期
    yesterday = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    expected_prefix = f"ai_daily_{yesterday}"
    matches = sorted(REPORT_DIR.glob(f"{expected_prefix}*.md"))
    if matches:
        print(f"[orchestrator] 已发现现成日报：{matches[-1]}")
        return

    print("[orchestrator] 未找到昨日日报，开始生成...")
    tweets_file = Path("tweets_data") / f"tweets_{yesterday}.jsonl"
    if tweets_file.exists():
        cmd = DAILY_SUMMARY_COMMAND + ["--date", yesterday]
    else:
        print(f"[orchestrator] 警告：{tweets_file} 不存在，将使用 ai_digest 默认逻辑生成最新日报。")
        cmd = DAILY_SUMMARY_COMMAND

    run_command(cmd)

    matches = sorted(REPORT_DIR.glob(f"{expected_prefix}*.md"))
    if matches:
        print(f"[orchestrator] 新生成日报：{matches[-1]}")
    else:
        raise RuntimeError("生成日报后仍未找到目标文件，请检查数据源是否完整。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="推特快讯/日报自动化脚本")
    parser.add_argument(
        "--mode",
        choices=["quick", "daily"],
        required=True,
        help="选择运行模式：quick 为即时快讯，daily 为昨日日报",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        if args.mode == "quick":
            for cmd in QUICK_COMMANDS:
                run_command(cmd)
        else:
            ensure_yesterday_digest()
            run_command(DAILY_PUSH_COMMAND)
    except Exception as exc:  # noqa: BLE001
        print(f"[orchestrator] 任务失败：{exc}", file=sys.stderr)
        sys.exit(1)
    else:
        print("[orchestrator] 任务完成")


if __name__ == "__main__":
    main()
