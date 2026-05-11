#!/usr/bin/env python3
"""
拉取 A 股指数和基金净值数据，计算持仓盈亏。
用法：python fetch_market_data.py [--date YYYY-MM-DD]
不传 --date 时自动判断：21:30 前分析昨日，21:30 后分析今日。
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests


def load_positions(positions_file: str) -> list[dict]:
    """读取持仓 JSON（数组格式）"""
    path = Path(positions_file)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / path
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_trading_day(date_str: str) -> bool:
    """判断是否为交易日（简单判断：非周末）"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.weekday() < 5


def get_target_date(now=None) -> str:
    """
    根据当前时间判断应分析的目标日期。
    - 今天工作日且已过 21:30 → 分析今天
    - 否则 → 分析最近一个已结束交易日
    """
    if now is None:
        now = datetime.now()
    if now.weekday() < 5 and (now.hour > 21 or (now.hour == 21 and now.minute >= 30)):
        return now.strftime("%Y-%m-%d")
    target = now.date() - timedelta(days=1)
    while target.weekday() >= 5:
        target -= timedelta(days=1)
    return target.strftime("%Y-%m-%d")


def fetch_index_data(index_codes: list[str], date_str: str) -> list[dict]:
    """通过新浪接口拉取指数数据"""
    results = []
    name_map = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sz399006": "创业板指",
        "sh000688": "科创50",
    }
    try:
        url = f"https://hq.sinajs.cn/list={','.join(index_codes)}"
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
                "name": name_map.get(code, name),
                "date": date_str,
                "open": open_price,
                "close": close,
                "high": high,
                "low": low,
                "change_pct": change_pct,
            })
    except Exception as e:
        print(f"拉取指数数据失败：{e}", file=sys.stderr)
    return results


def fetch_fund_data_ttjj(code: str) -> dict | None:
    """天天基金接口"""
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js"
        r = requests.get(url, timeout=10)
        text = r.text
        match = re.search(r'jsonpgz\((.*?)\);', text)
        if not match or not match.group(1).strip():
            return None
        data = json.loads(match.group(1))
        return {
            "code": code,
            "name": data.get("name", code),
            "nav_date": data.get("jzrq"),
            "nav": float(data.get("dwjz", 0)) if data.get("dwjz") else None,
            "estimate_nav": float(data.get("gsz", 0)) if data.get("gsz") else None,
            "change_pct": float(data.get("gszzl", 0)) if data.get("gszzl") else None,
        }
    except Exception:
        return None


def fetch_fund_data_em(code: str) -> dict | None:
    """东方财富接口（QDII fallback）"""
    try:
        url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
        r = requests.get(url, timeout=10)
        text = r.text
        match = re.search(r'Data_netWorthTrend = (\[.*?\]);', text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(1))
        if len(data) < 2:
            return None
        latest = data[-1]
        prev = data[-2]
        nav = latest.get("y")
        prev_nav = prev.get("y")
        ts = latest.get("x")
        nav_date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else None
        change_pct = round((nav - prev_nav) / prev_nav * 100, 2) if prev_nav else None
        # 提取基金名称
        name_match = re.search(r'fS_name = "(.*?)";', text)
        name = name_match.group(1) if name_match else code
        return {
            "code": code,
            "name": name,
            "nav_date": nav_date,
            "nav": nav,
            "change_pct": change_pct,
        }
    except Exception:
        return None


def fetch_fund_data(fund_codes: list[str]) -> list[dict]:
    """获取基金净值，优先天天基金，QDII fallback 东方财富"""
    results = []
    for code in fund_codes:
        data = fetch_fund_data_ttjj(code)
        if data is None:
            data = fetch_fund_data_em(code)
        if data is None:
            print(f"拉取基金 {code} 失败", file=sys.stderr)
            continue
        results.append(data)
    return results


def calculate_fund_pnl(positions: list[dict], fund_data: list[dict]) -> tuple[list[dict], float | None]:
    """计算基金持仓盈亏"""
    nav_map = {f["code"]: f for f in fund_data}
    results = []
    total_cost = 0.0
    total_value = 0.0

    for item in positions:
        code = item["code"]
        fd = nav_map.get(code)
        if not fd or fd.get("nav") is None:
            continue

        trades = item.get("trades", [])
        is_qdii = "QDII" in item.get("name", "")

        if not trades:
            results.append({
                "code": code,
                "name": item.get("name", fd.get("name", code)),
                "nav": fd["nav"],
                "nav_date": fd.get("nav_date"),
                "change_pct": fd.get("change_pct"),
                "avg_cost": None,
                "pnl_pct": None,
                "shares": None,
                "is_qdii": is_qdii,
            })
            continue

        # 按时间正序遍历，维护加权平均成本
        sorted_trades = sorted(trades, key=lambda t: t["date"])
        total_shares = 0.0
        total_invest = 0.0

        for t in sorted_trades:
            trade_type = t.get("type", "buy")
            shares = float(t["shares"])
            nav = float(t.get("nav", 0))

            if trade_type == "buy":
                total_shares += shares
                total_invest += shares * nav
            elif trade_type == "sell":
                if total_shares > 0:
                    avg_cost = total_invest / total_shares
                    total_shares -= shares
                    total_invest -= shares * avg_cost
            elif trade_type == "dividend":
                total_shares += shares
                # 分红送份额不改变总成本

        avg_cost = total_invest / total_shares if total_shares > 0 else 0
        market_value = total_shares * fd["nav"]
        pnl_pct = round((fd["nav"] - avg_cost) / avg_cost * 100, 2) if avg_cost > 0 else 0

        total_cost += total_invest
        total_value += market_value

        results.append({
            "code": code,
            "name": item.get("name", fd.get("name", code)),
            "nav": fd["nav"],
            "nav_date": fd.get("nav_date"),
            "change_pct": fd.get("change_pct"),
            "avg_cost": round(avg_cost, 4),
            "pnl_pct": pnl_pct,
            "shares": round(total_shares, 2),
            "is_qdii": is_qdii,
        })

    total_pnl_pct = round((total_value - total_cost) / total_cost * 100, 2) if total_cost > 0 else None
    return results, total_pnl_pct


def main():
    parser = argparse.ArgumentParser(description="拉取市场数据")
    parser.add_argument("--date", type=str, help="指定日期 YYYY-MM-DD，默认自动判断")
    args = parser.parse_args()

    date_str = args.date or get_target_date()

    if not is_trading_day(date_str):
        print(f"{date_str} 非交易日，跳过")
        return

    positions_file = "config/positions.json"
    positions = load_positions(positions_file)

    index_codes = ["sh000001", "sz399001", "sz399006", "sh000688"]

    fund_codes = [p["code"] for p in positions]

    index_data = fetch_index_data(index_codes, date_str)
    fund_data = fetch_fund_data(fund_codes)
    fund_pnl, total_pnl_pct = calculate_fund_pnl(positions, fund_data)

    data_dir = Path(__file__).parent.parent / "data" / "daily"
    data_dir.mkdir(exist_ok=True)
    output = {
        "date": date_str,
        "indices": index_data,
        "funds": fund_pnl,
        "total_pnl_pct": total_pnl_pct,
    }
    output_file = data_dir / f"{date_str}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"数据已保存：{output_file}")


if __name__ == "__main__":
    main()
