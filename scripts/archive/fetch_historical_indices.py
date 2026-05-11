#!/usr/bin/env python3
"""
拉取历史指数K线数据（新浪接口），补全已有 data/YYYY-MM-DD.json 中的 indices 字段。

用法：python fetch_historical_indices.py [--force]
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import requests


INDEX_CONFIG = {
    "sh000001": {"name": "上证指数", "sina_code": "sh000001"},
    "sz399001": {"name": "深证成指", "sina_code": "sz399001"},
    "sz399006": {"name": "创业板指", "sina_code": "sz399006"},
    "sh000688": {"name": "科创50", "sina_code": "sh000688"},
}


def fetch_index_kline(sina_code: str, datalen: int = 1500) -> list[dict]:
    """通过新浪接口获取指数历史K线"""
    url = (
        f"https://quotes.sina.cn/cn/api/jsonp.php/"
        f"var_KLine_Data=/CN_MarketDataService.getKLineData"
        f"?symbol={sina_code}&scale=240&ma=5&datalen={datalen}"
    )
    try:
        r = requests.get(url, timeout=15)
        text = r.text
        match = re.search(r'var_KLine_Data=\((.*?)\);', text, re.DOTALL)
        if not match:
            return []
        data = json.loads(match.group(1))
        if not data:
            return []
        return data
    except Exception as e:
        print(f"  拉取 {sina_code} 失败: {e}")
        return []


def transform_kline(raw: list[dict], index_code: str, index_name: str) -> list[dict]:
    """将新浪K线数据转换为标准格式，计算 change_pct"""
    result = []
    for i, item in enumerate(raw):
        date_str = item["day"]
        close = float(item["close"])
        prev_close = float(raw[i - 1]["close"]) if i > 0 else close
        change_pct = round((close - prev_close) / prev_close * 100, 2) if i > 0 else 0.0
        result.append({
            "code": index_code,
            "name": index_name,
            "date": date_str,
            "open": float(item["open"]),
            "close": close,
            "high": float(item["high"]),
            "low": float(item["low"]),
            "change_pct": change_pct,
        })
    return result


def main():
    parser = argparse.ArgumentParser(description="拉取历史指数数据")
    parser.add_argument("--force", action="store_true", help="强制重新拉取")
    args = parser.parse_args()

    data_dir = Path(__file__).parent.parent / "data" / "daily"

    # 1. 拉取所有指数数据
    all_index_records = []
    for code, cfg in INDEX_CONFIG.items():
        print(f"拉取 {cfg['name']}({code}) ...", end=" ")
        raw = fetch_index_kline(cfg["sina_code"], datalen=1500)
        if not raw:
            print("失败")
            continue
        records = transform_kline(raw, code, cfg["name"])
        print(f"{len(records)} 条 ({records[0]['date']} ~ {records[-1]['date']})")
        all_index_records.extend(records)

    if not all_index_records:
        print("未获取到任何指数数据")
        return

    # 2. 按日期聚合 {date: [indices]}
    date_indices_map = {}
    for r in all_index_records:
        date_indices_map.setdefault(r["date"], []).append(r)

    # 3. 遍历已有数据文件，补全 indices
    updated = 0
    skipped = 0
    for json_file in sorted(data_dir.glob("2*.json")):
        date_str = json_file.stem
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            continue

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("indices") and not args.force:
            skipped += 1
            continue

        indices = date_indices_map.get(date_str, [])
        if indices:
            data["indices"] = indices
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            updated += 1

    print(f"\n补全完成：更新 {updated} 个文件，跳过 {skipped} 个已有指数数据的文件")


if __name__ == "__main__":
    main()
