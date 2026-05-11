#!/usr/bin/env python3
"""
生成复盘 Markdown 草稿。
用法：python generate_review.py [--date YYYY-MM-DD]
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_target_date(now=None) -> str:
    if now is None:
        now = datetime.now()
    if now.weekday() < 5 and (now.hour > 21 or (now.hour == 21 and now.minute >= 30)):
        return now.strftime("%Y-%m-%d")
    target = now.date() - timedelta(days=1)
    while target.weekday() >= 5:
        target -= timedelta(days=1)
    return target.strftime("%Y-%m-%d")


def load_data(date_str: str) -> dict:
    data_dir = Path(__file__).parent.parent / "data"
    data_file = data_dir / "source" / f"{date_str}.json"
    if not data_file.exists():
        print(f"数据文件不存在：{data_file}", file=sys.stderr)
        sys.exit(1)
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def format_indices(indices: list[dict]) -> str:
    lines = ["| 指数 | 收盘 | 涨跌幅 |", "|------|------|--------|"]
    for idx in indices:
        change = f"{idx['change_pct']:+.2f}%"
        lines.append(f"| {idx['name']} | {idx['close']:.2f} | {change} |")
    return "\n".join(lines)


def format_funds(funds: list[dict], total_pnl_pct: float | None) -> str:
    if not funds:
        return "暂无基金数据。"
    lines = ["| 基金 | 净值 | 净值日期 | 当日涨跌 | 持仓盈亏 |", "|------|------|----------|----------|----------|"]
    for f in funds:
        name = f["name"]
        if f.get("is_qdii"):
            name += " (QDII)"
        nav = f"{f['nav']:.4f}" if f.get("nav") is not None else "-"
        nav_date = f.get("nav_date", "-")
        change = f"{f['change_pct']:+.2f}%" if f.get("change_pct") is not None else "-"
        if f.get("pnl_pct") is not None:
            pnl = f"{f['pnl_pct']:+.2f}%"
        else:
            pnl = "-"
        lines.append(f"| {name} | {nav} | {nav_date} | {change} | {pnl} |")
    if total_pnl_pct is not None:
        lines.append(f"\n**整体持仓盈亏：{total_pnl_pct:+.2f}%**")
    return "\n".join(lines)


def generate_review(data: dict) -> str:
    template_path = Path(__file__).parent / "review_template.md"
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    date_str = data["date"]
    title = f"每日理财复盘 {date_str}"

    template = template.replace("<!-- DATE_PLACEHOLDER -->", f'"{date_str}"')
    template = template.replace("<!-- TITLE_PLACEHOLDER -->", title)
    template = template.replace("<!-- INDICES_PLACEHOLDER -->", format_indices(data.get("indices", [])))
    template = template.replace("<!-- POSITIONS_PLACEHOLDER -->", format_funds(data.get("funds", []), data.get("total_pnl_pct")))

    # 若 data 中存在 analysis 字段，直接嵌入分析内容
    analysis = data.get("analysis", {})
    # fallback：从 data/analysis/ 目录读取
    if not analysis:
        analysis_path = Path(__file__).parent.parent / "data" / "analysis" / f"{date_str}.json"
        if analysis_path.exists():
            with open(analysis_path, "r", encoding="utf-8") as f:
                analysis = json.load(f)
    if analysis:
        template = template.replace("<!-- TODAY_FOCUS_PLACEHOLDER -->", analysis.get("today_focus", "<!-- TODAY_FOCUS_PLACEHOLDER -->"))
        template = template.replace("<!-- MARKET_COMMENT_PLACEHOLDER -->", analysis.get("market_comment", "<!-- MARKET_COMMENT_PLACEHOLDER -->"))
        template = template.replace("<!-- POSITION_ANALYSIS_PLACEHOLDER -->", analysis.get("position_analysis", "<!-- POSITION_ANALYSIS_PLACEHOLDER -->"))
        template = template.replace("<!-- EMOTION_DISCIPLINE_PLACEHOLDER -->", analysis.get("emotion_discipline", "<!-- EMOTION_DISCIPLINE_PLACEHOLDER -->"))
        template = template.replace("<!-- TOMORROW_PLAN_PLACEHOLDER -->", analysis.get("tomorrow_plan", "<!-- TOMORROW_PLAN_PLACEHOLDER -->"))

    return template


def main():
    parser = argparse.ArgumentParser(description="生成复盘 Markdown 草稿")
    parser.add_argument("--date", type=str, default=get_target_date(),
                        help="指定日期，格式 YYYY-MM-DD")
    args = parser.parse_args()
    date_str = args.date

    data = load_data(date_str)
    content = generate_review(data)

    review_dir = Path(__file__).parent.parent / "src" / "content" / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    output_file = review_dir / f"{date_str}.md"

    if output_file.exists():
        print(f"草稿已存在，跳过：{output_file}")
        return

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"复盘草稿已生成：{output_file}")


if __name__ == "__main__":
    main()
