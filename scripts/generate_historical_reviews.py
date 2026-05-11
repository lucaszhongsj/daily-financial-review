#!/usr/bin/env python3
"""
将 data/historical_nav/history.json 转换为每日视角的复盘数据文件。
为每个交易日生成 data/YYYY-MM-DD.json，包含指数、基金持仓盈亏、整体盈亏。

用法：python generate_historical_reviews.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--dry-run]
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def load_positions() -> list[dict]:
    path = Path(__file__).parent.parent / "config" / "positions.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history() -> list[dict]:
    path = Path(__file__).parent.parent / "data" / "historical_nav" / "history.json"
    if not path.exists():
        print(f"错误：{path} 不存在。请先运行：python scripts/transform_historical_nav.py", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_existing_daily(date_str: str) -> dict | None:
    path = Path(__file__).parent.parent / "data" / f"{date_str}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def is_trading_day(date_str: str) -> bool:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.weekday() < 5


def calc_fund_state(trades: list[dict], target_date: str, nav: float | None) -> dict:
    """计算截至 target_date 的基金持仓状态"""
    sorted_trades = sorted(trades, key=lambda t: t["date"])
    total_shares = 0.0
    total_invest = 0.0

    for t in sorted_trades:
        trade_date = t["date"][:10]
        if trade_date > target_date:
            break
        trade_type = t.get("type", "buy")
        shares = float(t["shares"])
        trade_nav = float(t.get("nav", 0))

        if trade_type == "buy":
            total_shares += shares
            total_invest += shares * trade_nav
        elif trade_type == "sell":
            if total_shares > 0:
                avg_cost = total_invest / total_shares
                total_shares -= shares
                total_invest -= shares * avg_cost
        elif trade_type == "dividend":
            total_shares += shares

    # 浮点精度修正：shares 接近 0 时清零成本
    if abs(total_shares) < 0.001:
        total_shares = 0.0
        total_invest = 0.0

    avg_cost = total_invest / total_shares if total_shares > 0 else 0
    pnl_pct = round((nav - avg_cost) / avg_cost * 100, 2) if avg_cost > 0 and nav is not None else None

    return {
        "total_shares": total_shares,
        "total_invest": total_invest,
        "avg_cost": round(avg_cost, 4) if avg_cost > 0 else 0,
        "pnl_pct": pnl_pct,
    }


def main():
    parser = argparse.ArgumentParser(description="生成历史每日复盘数据")
    parser.add_argument("--start", type=str, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="只打印不写入")
    parser.add_argument("--force", action="store_true", help="覆盖已有文件")
    args = parser.parse_args()

    positions = load_positions()
    history = load_history()

    # 构建日期 -> {code: fund_data} 的映射
    date_funds_map = {}
    for day in history:
        date_funds_map[day["date"]] = {f["code"]: f for f in day.get("funds", [])}

    # 确定日期范围
    all_dates = sorted(date_funds_map.keys())
    start_date = args.start or all_dates[0]
    end_date = args.end or all_dates[-1]

    target_dates = [d for d in all_dates if start_date <= d <= end_date and is_trading_day(d)]

    print(f"日期范围：{start_date} ~ {end_date}")
    print(f"共 {len(target_dates)} 个交易日")

    data_dir = Path(__file__).parent.parent / "data" / "daily"
    data_dir.mkdir(exist_ok=True)

    generated = 0
    skipped = 0

    for date_str in target_dates:
        output_file = data_dir / f"{date_str}.json"

        if not args.force and output_file.exists():
            skipped += 1
            continue

        fund_map = date_funds_map.get(date_str, {})

        funds = []
        total_cost = 0.0
        total_value = 0.0

        for item in positions:
            code = item["code"]
            fd = fund_map.get(code)
            if not fd:
                continue

            nav = fd.get("nav")
            if nav is None:
                continue

            is_qdii = fd.get("is_qdii", "QDII" in item.get("name", ""))
            trades = item.get("trades", [])

            if not trades:
                funds.append({
                    "code": code,
                    "name": item.get("name", fd.get("name", code)),
                    "nav": nav,
                    "nav_date": fd.get("nav_date", date_str),
                    "change_pct": fd.get("change_pct"),
                    "avg_cost": None,
                    "pnl_pct": None,
                    "shares": None,
                    "is_qdii": is_qdii,
                })
                continue

            state = calc_fund_state(trades, date_str, nav)
            market_value = state["total_shares"] * nav

            total_cost += state["total_invest"]
            total_value += market_value

            funds.append({
                "code": code,
                "name": item.get("name", fd.get("name", code)),
                "nav": nav,
                "nav_date": fd.get("nav_date", date_str),
                "change_pct": fd.get("change_pct"),
                "avg_cost": state["avg_cost"] if state["total_shares"] > 0 else None,
                "pnl_pct": state["pnl_pct"],
                "shares": round(state["total_shares"], 2) if state["total_shares"] > 0 else None,
                "is_qdii": is_qdii,
            })

        total_pnl_pct = round((total_value - total_cost) / total_cost * 100, 2) if total_cost > 0 else None

        # 尝试复用已有文件中的指数数据
        existing = load_existing_daily(date_str)
        indices = existing.get("indices", []) if existing else []

        output = {
            "date": date_str,
            "indices": indices,
            "funds": funds,
            "total_pnl_pct": total_pnl_pct,
        }

        if args.dry_run:
            print(f"[DRY-RUN] {date_str}: {len(funds)} 只基金, total_pnl={total_pnl_pct}%")
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            generated += 1

    if args.dry_run:
        print(f"\n干运行完成，共 {len(target_dates)} 天")
    else:
        print(f"\n生成 {generated} 个文件，跳过 {skipped} 个已有文件")


if __name__ == "__main__":
    main()
