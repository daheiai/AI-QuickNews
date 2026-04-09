"""AI 信息聚合与推送系统 - 主入口"""
import argparse
import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import config
from src.collectors import RSSCollector, TwitterCollector, GitHubChangelogCollector
from src.analyzer.digest import DigestAnalyzer
from src.notifier.feishu import FeishuNotifier


def _collect_sources():
    """并行抓取 Twitter 和 RSS 数据"""
    print("  并行启动 Twitter + RSS 采集...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        twitter_future = executor.submit(TwitterCollector().run)
        rss_future = executor.submit(RSSCollector().run)
        # 等待两个采集器都完成，收集异常
        errors = []
        for name, future in [("Twitter", twitter_future), ("RSS", rss_future)]:
            try:
                future.result()
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                print(f"  [警告] {name} 采集异常: {exc}")
        if errors:
            print(f"  采集完成（{len(errors)} 个源有异常）")
        else:
            print("  采集完成")


def run_quick_mode():
    """快讯模式：抓取 -> 分析 -> 推送（纯文字版，从 JSON 派生）"""
    print("=" * 50)
    print("快讯模式启动")
    print("=" * 50)

    # 1. 抓取多信源数据（并行）
    print("\n[1/3] 抓取多信源数据...")
    _collect_sources()

    # 2. 生成 JSON 格式的快讯
    print("\n[2/3] 生成 AI 快讯 (JSON)...")
    analyzer = DigestAnalyzer(mode="quick_json")
    result = analyzer.run_json()
    print(f"生成了 {result['total']} 条快讯")

    # 3. 推送到飞书（从 JSON 格式化为文字）
    print("\n[3/3] 推送到飞书...")
    notifier = FeishuNotifier()
    primary_text = _format_primary_from_json(result)
    appendix_text = _format_appendix_from_json(result)
    notifier.send_digest_messages(primary_text, appendix_text, mode="quick")

    print("\n快讯模式完成")


def run_quick_image_mode(page_url: str = None, skip_collect: bool = False):
    """快讯图片模式：抓取 -> 分析生成JSON -> 截图 -> 推送图片+附录"""
    print("=" * 50)
    print("快讯图片模式启动")
    print("=" * 50)

    # 1. 抓取多信源数据（可选跳过，并行）
    if not skip_collect:
        print("\n[1/4] 抓取多信源数据...")
        _collect_sources()
    else:
        print("\n[1/4] 跳过数据抓取（使用现有数据）")

    # 2. 生成 JSON 格式的快讯
    print("\n[2/4] 生成 AI 快讯 (JSON)...")
    analyzer = DigestAnalyzer(mode="quick_json")
    result = analyzer.run_json()
    print(f"生成了 {result['total']} 条快讯")

    # 3. 截图
    print("\n[3/4] 生成网页截图...")
    if page_url:
        # 使用指定的 URL
        from src.renderer.screenshot import ScreenshotRenderer
        with ScreenshotRenderer(width=390, device_scale_factor=2) as renderer:
            screenshot_path = renderer.capture(page_url, format="png")
    else:
        # 提示用户需要配置 URL
        print("提示：需要配置网页服务才能截图")
        print("请设置 PHP 服务并通过 --page-url 参数指定 URL")
        print(f"JSON 数据已保存到：{config.WEB_JSON_DIR / 'quick_latest.json'}")
        screenshot_path = None

    # 4. 推送到飞书
    print("\n[4/4] 推送到飞书...")
    notifier = FeishuNotifier()

    if screenshot_path and screenshot_path.exists():
        # 发送图片
        print(f"发送截图：{screenshot_path}")
        notifier.send_image(screenshot_path)

    # 发送附录文本
    appendix_text = _format_appendix_from_json(result)
    notifier.send_message(appendix_text)

    print("\n快讯图片模式完成")


def _format_primary_from_json(result: dict) -> str:
    """从 JSON 结果格式化主文本（用于飞书推送）"""
    now_str = result.get("generated_at", dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    header = f"【大黑4小时AI速报  时间：{now_str}】"

    # 总结
    summary = result.get("summary", "")

    # 条目列表
    items = result.get("items", [])
    numerals = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

    lines = [header, ""]
    if summary:
        lines.append(summary.replace("【", "").replace("】", ""))
        lines.append("")

    lines.append(f"有 {len(items)} 条重要动态：")
    lines.append("")

    for idx, item in enumerate(items):
        numeral = numerals[idx] if idx < len(numerals) else str(idx + 1)
        title = item.get("title", "")
        content = item.get("content", "").replace("【", "").replace("】", "")

        lines.append(f"{numeral}、{title}")
        if content and content != title:
            # 简化内容，避免过长
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"   {content}")
        lines.append("")

    lines.append("本时段速报完毕，请等待下一个4小时速报~")
    return "\n".join(lines)


def _format_appendix_from_json(result: dict) -> str:
    """从 JSON 结果格式化附录文本"""
    now_str = result.get("generated_at", dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    header = f"【速报附录  时间：{now_str}】"
    intro = "以下为本次摘要引用的原始内容片段："

    grouped = {"twitter": [], "rss": [], "other": []}

    for source in result.get("all_sources", []):
        source_type = source.get("source_type", "other")
        line = f"{source['index']}. [{source['author']}] {source['snippet']} {source['url']}"

        if source_type == "twitter":
            grouped["twitter"].append(line)
        elif source_type == "rss":
            grouped["rss"].append(line)
        else:
            grouped["other"].append(line)

    sections = [header, intro, ""]
    if grouped["twitter"]:
        sections.extend(["【Twitter】", *grouped["twitter"], ""])
    if grouped["rss"]:
        sections.extend(["【RSS】", *grouped["rss"], ""])
    if grouped["other"]:
        sections.extend(["【其他来源】", *grouped["other"], ""])

    return "\n".join(sections).rstrip()


def run_daily_mode():
    """日报模式：生成日报 -> 推送"""
    print("=" * 50)
    print("日报模式启动")
    print("=" * 50)

    # 1. 生成日报（默认使用昨天的数据）
    print("\n[1/2] 生成 AI 日报...")
    yesterday = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    analyzer = DigestAnalyzer(mode="daily")
    digest_output = analyzer.run(date=yesterday)

    # 2. 推送到飞书
    print("\n[2/2] 推送到飞书...")
    notifier = FeishuNotifier()
    notifier.send_digest_messages(
        digest_output.primary_text,
        digest_output.appendix_text,
        mode="daily",
    )

    print("\n日报模式完成")


def run_github_changelog_mode():
    """GitHub Changelog 模式：抓取 -> 翻译 -> 汇总 JSON -> 生成趋势"""
    print("=" * 50)
    print("GitHub Changelog 模式启动")
    print("=" * 50)

    # 1. 抓取、翻译
    print("\n[1/3] 抓取并翻译 GitHub Releases...")
    collector = GitHubChangelogCollector()
    collector.run()

    # 2. 汇总生成 changelog_all.json
    print("\n[2/3] 汇总生成 changelog_all.json...")
    from src.generators.changelog_json import generate as generate_json
    generate_json()

    # 3. 生成趋势总结
    print("\n[3/3] 生成更新趋势总结...")
    from src.generators.changelog_trend import generate as generate_trend
    generate_trend()

    print("\nGitHub Changelog 模式完成")


def main():
    parser = argparse.ArgumentParser(
        description="AI 信息聚合与推送系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python main.py --mode quick        # 快讯模式（抓取+分析+推送文字到飞书）
  python main.py --mode quick_image  # 快讯图片模式（抓取+分析+截图+推送图片到飞书）
  python main.py --mode quick_image --page-url http://localhost/ai-digest/
  python main.py --mode quick_image --skip-collect  # 跳过数据抓取
  python main.py --mode daily        # 日报模式（生成日报+推送）

  # 单独运行各模块
  python -m src.collectors.twitter             # 仅抓取推文
  python -m src.analyzer.digest --mode quick_json  # 生成快讯 JSON
  python -m src.notifier.feishu --mode quick   # 仅推送快讯
  python -m src.renderer.screenshot <url>      # 单独截图
        """
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "quick_image", "daily", "github"],
        required=True,
        help="运行模式：quick=快讯文字版，quick_image=快讯图片版，daily=日报，github=GitHub Changelog"
    )
    parser.add_argument(
        "--page-url",
        help="快讯网页 URL（用于 quick_image 模式截图）"
    )
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="跳过数据抓取，直接使用现有数据"
    )

    args = parser.parse_args()

    try:
        if args.mode == "quick":
            run_quick_mode()
        elif args.mode == "quick_image":
            run_quick_image_mode(
                page_url=args.page_url,
                skip_collect=args.skip_collect
            )
        elif args.mode == "github":
            run_github_changelog_mode()
        else:
            run_daily_mode()
    except Exception as e:
        print(f"\n错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
