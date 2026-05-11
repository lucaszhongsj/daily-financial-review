#!/usr/bin/env python3
"""
将 data/historical_nav/ 中每只基金的单独文件，按日期聚合为统一格式。
输出与 data/YYYY-MM-DD.json 结构一致的历史数据文件。

用法：python transform_historical_nav.py [--output FILE]
"""
import argparse
import json
from datetime import datetime
from pathlib import Path


def load_fund_info() -> dict[str, dict]:
    """读取持仓配置，返回 {code: {name, is_qdii}}"""
    path = Path(__file__).parent.parent / "config" / "positions.json"
    with open(path, "r", encoding="utf-8") as f:
        positions = json.load(f)
    return {
        p["code"]: {
            "name": p["name"],
            "is_qdii": "QDII" in p.get("name", ""),
        }
        for p in positions
    }


def load_fund_records(code: str) -> list[dict]:
    """读取单只基金的历史净值文件"""
    path = Path(__file__).parent.parent / "data" / "historical_nav" / f"{code}.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("records", [])


def calc_change_pct(records: list[dict]) -> list[dict]:
    """为每条记录计算 change_pct"""
    result = []
    for i, r in enumerate(records):
        nav = r["nav"]
        if i > 0:
            prev_nav = records[i - 1]["nav"]
            change_pct = round((nav - prev_nav) / prev_nav * 100, 2) if prev_nav else 0.0
        else:
            change_pct = None
        result.append({
            "date": r["date"],
            "nav": nav,
            "change_pct": change_pct,
        })
    return result


def main():
    parser = argparse.ArgumentParser(description="聚合历史净值数据为统一格式")
    parser.add_argument("--output", type=str, default="data/historical_nav/history.json",
                        help="输出文件路径")
    args = parser.parse_args()

    fund_info = load_fund_info()
    all_dates = set()
    fund_records = {}

    # 加载并处理每只基金
    for code, info in fund_info.items():
        records = load_fund_records(code)
        if not records:
            print(f"警告：{code} 无历史数据")
            continue
        processed = calc_change_pct(records)
        fund_records[code] = processed
        for r in processed:
            all_dates.add(r["date"])

    # 按日期聚合
    history = []
    for date in sorted(all_dates):
        day_funds = []
        for code, info in fund_info.items():
            records = fund_records.get(code, [])
            record_map = {r["date"]: r for r in records}
            r = record_map.get(date)
            if r:
                day_funds.append({
                    "code": code,
                    "name": info["name"],
                    "nav": r["nav"],
                    "nav_date": r["date"],
                    "change_pct": r["change_pct"],
                    "is_qdii": info["is_qdii"],
                })
        history.append({
            "date": date,
            "funds": day_funds,
        })

    output_path = Path(__file__).parent.parent / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"历史数据已聚合：{output_path}")
    print(f"共 {len(history)} 个交易日，{len(fund_info)} 只基金")

    # 同时更新单只基金的文件格式，增加 change_pct
    for code, records in fund_records.items():
        info = fund_info[code]
        output_file = Path(__file__).parent.parent / "data" / "historical_nav" / f"{code}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "code": code,
                "name": info["name"],
                "is_qdii": info["is_qdii"],
                "records": records,
            }, f, ensure_ascii=False, indent=2)
    print(f"单只基金文件已更新 change_pct 字段")


if __name__ == "__main__":
    main()
