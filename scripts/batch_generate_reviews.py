#!/usr/bin/env python3
"""批量重新生成复盘 Markdown 草稿。"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="批量生成复盘草稿")
    parser.add_argument("--start", type=str, help="起始日期")
    parser.add_argument("--end", type=str, help="结束日期")
    args = parser.parse_args()

    analysis_dir = Path("data/analysis")
    review_dir = Path("src/content/reviews")
    review_dir.mkdir(parents=True, exist_ok=True)

    all_dates = sorted(
        [f.stem for f in analysis_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json")],
        reverse=True,
    )

    if args.start:
        all_dates = [d for d in all_dates if d >= args.start]
    if args.end:
        all_dates = [d for d in all_dates if d <= args.end]

    total = len(all_dates)
    print(f"待生成草稿：{total}")

    for i, date_str in enumerate(all_dates, 1):
        # 删除旧草稿（如果有）
        old = review_dir / f"{date_str}.md"
        if old.exists():
            old.unlink()

        result = subprocess.run(
            [sys.executable, "scripts/generate_review.py", "--date", date_str],
            capture_output=True, text=True,
        )

        if result.returncode != 0:
            print(f"  失败：{date_str} - {result.stderr.strip()}")

        if i % 100 == 0 or i == total:
            print(f"  进度：{i}/{total} ({i/total*100:.1f}%)")

    print(f"\n完成")


if __name__ == "__main__":
    main()
