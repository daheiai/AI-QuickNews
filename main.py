"""AI 信息聚合与推送系统 - 主入口"""
import argparse
import datetime as dt
import sys
from pathlib import Path

from src.collectors.twitter import TwitterCollector
from src.analyzer.digest import DigestAnalyzer
from src.notifier.feishu import FeishuNotifier


def run_quick_mode():
    """快讯模式：抓取 -> 分析 -> 推送"""
    print("=" * 50)
    print("快讯模式启动")
    print("=" * 50)

    # 1. 抓取推文
    print("\n[1/3] 抓取推文...")
    collector = TwitterCollector()
    collector.run()

    # 2. 生成快讯
    print("\n[2/3] 生成 AI 快讯...")
    analyzer = DigestAnalyzer(mode="quick")
    analyzer.run()

    # 3. 推送到飞书
    print("\n[3/3] 推送到飞书...")
    notifier = FeishuNotifier()
    notifier.send_report(mode="quick")

    print("\n快讯模式完成")


def run_daily_mode():
    """日报模式：生成日报 -> 推送"""
    print("=" * 50)
    print("日报模式启动")
    print("=" * 50)

    # 1. 生成日报（默认使用昨天的数据）
    print("\n[1/2] 生成 AI 日报...")
    yesterday = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    analyzer = DigestAnalyzer(mode="daily")
    analyzer.run(date=yesterday)

    # 2. 推送到飞书
    print("\n[2/2] 推送到飞书...")
    notifier = FeishuNotifier()
    notifier.send_report(mode="daily")

    print("\n日报模式完成")


def main():
    parser = argparse.ArgumentParser(
        description="AI 信息聚合与推送系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python main.py --mode quick   # 快讯模式（抓取+分析+推送）
  python main.py --mode daily   # 日报模式（生成日报+推送）

  # 单独运行各模块
  python -m src.collectors.twitter      # 仅抓取推文
  python -m src.analyzer.digest --mode quick   # 仅生成快讯
  python -m src.notifier.feishu --mode quick   # 仅推送快讯
        """
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "daily"],
        required=True,
        help="运行模式：quick=快讯（抓取+分析+推送），daily=日报（生成+推送）"
    )

    args = parser.parse_args()

    try:
        if args.mode == "quick":
            run_quick_mode()
        else:
            run_daily_mode()
    except Exception as e:
        print(f"\n错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
