#!/usr/bin/env python3
"""
生成复盘 Markdown 草稿。
用法：python generate_review.py [--date YYYY-MM-DD]
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def load_data(date_str: str) -> dict:
    data_dir = Path(__file__).parent.parent / "data"
    data_file = data_dir / f"{date_str}.json"
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


def format_positions(positions: list[dict], total_pnl_pct: float) -> str:
    if not positions:
        return "暂无持仓数据。"
    lines = ["| 标的 | 收盘价 | 当日涨跌 | 持仓盈亏 |", "|------|--------|----------|----------|"]
    for p in positions:
        change = f"{p['change_pct']:+.2f}%"
        pnl = f"{p['pnl_pct']:+.2f}%"
        lines.append(f"| {p['name']} | {p['close']:.2f} | {change} | {pnl} |")
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
    template = template.replace("<!-- POSITIONS_PLACEHOLDER -->", format_positions(data.get("positions", []), data.get("total_pnl_pct", 0)))

    return template


def main():
    parser = argparse.ArgumentParser(description="生成复盘 Markdown 草稿")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"),
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
