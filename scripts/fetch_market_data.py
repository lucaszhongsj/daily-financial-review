#!/usr/bin/env python3
"""
拉取 A 股市场数据，计算持仓盈亏。
用法：python fetch_market_data.py [--date YYYY-MM-DD]
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests


def parse_positions(env_value: str) -> list[dict]:
    """解析持仓字符串，格式：代码:名称:数量:成本价,代码:名称:数量:成本价"""
    positions = []
    if not env_value:
        return positions
    for item in env_value.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) != 4:
            print(f"持仓格式错误，跳过：{item}", file=sys.stderr)
            continue
        code, name, quantity, cost = parts
        positions.append({
            "code": code.strip(),
            "name": name.strip(),
            "quantity": int(quantity.strip()),
            "cost": float(cost.strip()),
        })
    return positions


def is_trading_day(date_str: str) -> bool:
    """判断是否为交易日（简单判断：非周末）"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.weekday() < 5


def fetch_sina_data(codes: list[str], date_str: str) -> list[dict]:
    """通过新浪接口批量拉取行情数据"""
    results = []
    if not codes:
        return results
    try:
        url = f"https://hq.sinajs.cn/list={','.join(codes)}"
        headers = {"Referer": "https://finance.sina.com.cn"}
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = "gb2312"
        for line in r.text.strip().split(";"):
            line = line.strip()
            if not line.startswith("var hq_str_"):
                continue
            code = line.split("=")[0].replace("var hq_str_", "")
            data_str = line.split('="')[1].rstrip('"')
            parts = data_str.split(",")
            if len(parts) < 5:
                continue
            name = parts[0]
            open_price = float(parts[1])
            prev_close = float(parts[2])
            close = float(parts[3])
            high = float(parts[4])
            low = float(parts[5])
            change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0.0
            results.append({
                "code": code,
                "name": name,
                "date": date_str,
                "open": open_price,
                "close": close,
                "high": high,
                "low": low,
                "change_pct": change_pct,
            })
    except Exception as e:
        print(f"拉取行情数据失败：{e}", file=sys.stderr)
    return results


def calculate_position_pnl(positions: list[dict], stock_data: list[dict]) -> tuple[list[dict], float]:
    """计算持仓盈亏"""
    price_map = {s["code"]: s for s in stock_data}
    results = []
    total_cost = 0.0
    total_value = 0.0
    for p in positions:
        sd = price_map.get(p["code"])
        if not sd:
            continue
        cost_value = p["quantity"] * p["cost"]
        market_value = p["quantity"] * sd["close"]
        pnl_pct = (sd["close"] - p["cost"]) / p["cost"] * 100 if p["cost"] else 0
        total_cost += cost_value
        total_value += market_value
        results.append({
            "code": p["code"],
            "name": p["name"],
            "close": sd["close"],
            "change_pct": sd["change_pct"],
            "cost": p["cost"],
            "pnl_pct": round(pnl_pct, 2),
        })
    total_pnl_pct = round((total_value - total_cost) / total_cost * 100, 2) if total_cost else 0
    return results, total_pnl_pct


def main():
    parser = argparse.ArgumentParser(description="拉取 A 股市场数据")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"),
                        help="指定日期，格式 YYYY-MM-DD")
    args = parser.parse_args()
    date_str = args.date

    if not is_trading_day(date_str):
        print(f"{date_str} 非交易日，跳过")
        return

    # 加载环境变量
    env_path = Path(__file__).parent.parent / ".env.local"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

    positions = parse_positions(os.environ.get("POSITIONS", ""))
    indices_env = os.environ.get("INDICES", "sh000001,sz399001,sz399006,sh000688")
    index_codes = [c.strip() for c in indices_env.split(",") if c.strip()]

    # 个股代码加交易所前缀
    stock_codes = []
    for p in positions:
        code = p["code"]
        prefix = "sh" if code.startswith("6") else "sz"
        stock_codes.append(f"{prefix}{code}")

    # 统一拉取
    all_codes = index_codes + stock_codes
    all_data = fetch_sina_data(all_codes, date_str)

    index_data = [d for d in all_data if d["code"] in index_codes]
    stock_data = [d for d in all_data if d["code"] in stock_codes]

    # 个股 code 去掉前缀以便匹配持仓
    for s in stock_data:
        s["code"] = s["code"].replace("sh", "").replace("sz", "")

    position_pnl, total_pnl_pct = calculate_position_pnl(positions, stock_data)

    # 保存数据
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    output = {
        "date": date_str,
        "indices": index_data,
        "stocks": stock_data,
        "positions": position_pnl,
        "total_pnl_pct": total_pnl_pct,
    }
    output_file = data_dir / f"{date_str}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"数据已保存：{output_file}")


if __name__ == "__main__":
    main()
