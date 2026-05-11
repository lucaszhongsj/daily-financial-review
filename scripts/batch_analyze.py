#!/usr/bin/env python3
"""
批量复盘分析协调脚本。
不调用外部 API，而是扫描待处理日期并分组，供 Claude Code 批量处理。

用法：
    python scripts/batch_analyze.py [--batch-size N] [--start DATE] [--end DATE]

输出：打印待处理日期列表（按批次），Claude 读取后直接生成分析并保存。
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def load_existing_analysis(date_str: str) -> dict | None:
    """检查是否已有分析文件。"""
    path = Path(__file__).parent.parent / "data" / "analysis" / f"{date_str}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def get_pending_dates(start_date: str | None, end_date: str | None, reverse: bool = False) -> list[str]:
    """获取所有待处理日期（按时间顺序或倒序）。"""
    data_dir = Path(__file__).parent.parent / "data"
    all_dates = []

    for f in sorted(data_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json")):
        date_str = f.stem
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            all_dates.append(date_str)

    if start_date:
        all_dates = [d for d in all_dates if d >= start_date]
    if end_date:
        all_dates = [d for d in all_dates if d <= end_date]

    # 过滤已处理的
    pending = [d for d in all_dates if not load_existing_analysis(d)]

    if reverse:
        pending.reverse()

    return pending


def format_batch_for_claude(dates: list[str]) -> str:
    """格式化一批日期，方便 Claude 直接处理。"""
    lines = [f"  {d}" for d in dates]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="批量复盘分析协调")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="每批处理天数（默认 10）")
    parser.add_argument("--start", type=str, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--list", action="store_true",
                        help="只打印待处理日期列表，不分批")
    parser.add_argument("--count", action="store_true",
                        help="只统计待处理数量")
    parser.add_argument("--reverse", action="store_true",
                        help="从最近日期开始处理（倒序）")
    args = parser.parse_args()

    pending = get_pending_dates(args.start, args.end, reverse=args.reverse)

    if args.count:
        print(f"待处理日期：{len(pending)}")
        return

    if not pending:
        print("所有日期已完成分析。")
        return

    if args.list:
        print("待处理日期：")
        for d in pending:
            print(f"  {d}")
        return

    # 分批输出
    batch_size = args.batch_size
    total = len(pending)
    batches = (total + batch_size - 1) // batch_size

    print(f"共 {total} 个待处理日期，分 {batches} 批（每批 {batch_size} 天）")
    print()

    for i in range(0, total, batch_size):
        batch = pending[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"=== 第 {batch_num}/{batches} 批 ===")
        for date_str in batch:
            print(f"  {date_str}")
        print()

    print("使用方式：")
    print("  1. 告诉 Claude：'处理第 1 批复盘分析'")
    print("  2. Claude 读取每日数据 → 生成分析 → 保存到 data/analysis/")
    print("  3. 重复直到所有批次完成")
    print()
    print("或直接运行：")
    print("  python scripts/batch_analyze.py --list  # 查看全部日期")


if __name__ == "__main__":
    main()
