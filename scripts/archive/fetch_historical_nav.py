#!/usr/bin/env python3
"""
分批拉取基金历史净值（东方财富接口）。
用法：python fetch_historical_nav.py [--start YYYY-MM-DD] [--output DIR]
默认 start 为最早交易日期，end 为今日。
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests


def load_positions() -> list[dict]:
    """读取持仓配置，返回基金列表"""
    path = Path(__file__).parent.parent / "config" / "positions.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_nav_history(code: str) -> list[dict]:
    """通过东方财富接口获取基金历史净值"""
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    try:
        r = requests.get(url, timeout=15)
        r.encoding = "utf-8"
        text = r.text

        match = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', text, re.DOTALL)
        if not match:
            print(f"  {code}: 未找到净值数据", file=sys.stderr)
            return []

        raw = json.loads(match.group(1))
        records = []
        for item in raw:
            ts = item.get("x")
            nav = item.get("y")
            if ts is None or nav is None:
                continue
            date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            records.append({
                "date": date_str,
                "nav": round(float(nav), 4),
            })
        return records
    except Exception as e:
        print(f"  {code}: 请求失败 {e}", file=sys.stderr)
        return []


def filter_by_date(records: list[dict], start_date: str, end_date: str) -> list[dict]:
    """按日期范围过滤"""
    return [
        r for r in records
        if start_date <= r["date"] <= end_date
    ]


def main():
    parser = argparse.ArgumentParser(description="拉取基金历史净值")
    parser.add_argument("--start", type=str, help="起始日期 YYYY-MM-DD，默认从最早交易推算")
    parser.add_argument("--output", type=str, default="data/historical_nav", help="输出目录")
    args = parser.parse_args()

    positions = load_positions()

    # 确定日期范围
    today = datetime.now().strftime("%Y-%m-%d")
    if args.start:
        start_date = args.start
    else:
        # 从所有 trade 中找最早日期
        all_dates = []
        for p in positions:
            for t in p.get("trades", []):
                d = t["date"][:10]
                all_dates.append(d)
        start_date = min(all_dates) if all_dates else "2020-01-01"

    print(f"日期范围：{start_date} ~ {today}")
    print(f"共 {len(positions)} 只基金")

    output_dir = Path(__file__).parent.parent / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, item in enumerate(positions):
        code = item["code"]
        name = item["name"]
        print(f"[{i+1}/{len(positions)}] 拉取 {code} {name} ...", end=" ")

        records = fetch_nav_history(code)
        if not records:
            print("失败")
            continue

        filtered = filter_by_date(records, start_date, today)
        print(f"原始 {len(records)} 条，过滤后 {len(filtered)} 条")

        output_file = output_dir / f"{code}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "code": code,
                "name": name,
                "start_date": start_date,
                "end_date": today,
                "records": filtered,
            }, f, ensure_ascii=False, indent=2)

        # 分批延迟，避免限流
        if i < len(positions) - 1:
            time.sleep(1)

    print(f"\n历史净值已保存至：{output_dir}")


if __name__ == "__main__":
    main()
