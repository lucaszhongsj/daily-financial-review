#!/usr/bin/env python3
"""
批量生成历史每日复盘 Markdown。
基于 data/YYYY-MM-DD.json 自动生成分析内容。

用法：python generate_historical_reviews_md.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--force]
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def load_daily_data(date_str: str) -> dict | None:
    path = Path(__file__).parent.parent / "data" / f"{date_str}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_indices(indices: list[dict]) -> str:
    if not indices:
        return "暂无指数数据。"
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


def generate_market_comment(indices: list[dict]) -> str:
    """基于指数数据自动生成大盘点评"""
    if not indices:
        return "暂无指数数据。"

    sh = next((i for i in indices if i["code"] == "sh000001"), None)
    cy = next((i for i in indices if i["code"] == "sz399006"), None)
    kc = next((i for i in indices if i["code"] == "sh000688"), None)

    parts = []

    # 整体方向
    if sh:
        if sh["change_pct"] > 1:
            parts.append(f"上证指数大涨 +{sh['change_pct']:.2f}%，市场情绪积极。")
        elif sh["change_pct"] > 0:
            parts.append(f"上证微涨 +{sh['change_pct']:.2f}%，市场整体偏暖。")
        elif sh["change_pct"] > -1:
            parts.append(f"上证微跌 {sh['change_pct']:.2f}%，市场窄幅震荡。")
        else:
            parts.append(f"上证下跌 {sh['change_pct']:.2f}%，市场情绪偏弱。")

    # 风格判断
    if cy and sh:
        diff = cy["change_pct"] - sh["change_pct"]
        if diff > 1:
            parts.append(f"创业板指 (+{cy['change_pct']:.2f}%) 明显强于主板，成长风格占优。")
        elif diff < -1:
            parts.append(f"创业板指 ({cy['change_pct']:.2f}%) 弱于主板，成长板块承压。")

    # 科创50
    if kc:
        if kc["change_pct"] > 2:
            parts.append(f"科创50 大涨 +{kc['change_pct']:.2f}%，科技板块情绪高涨。")
        elif kc["change_pct"] < -2:
            parts.append(f"科创50 大跌 {kc['change_pct']:.2f}%，科技成长遭遇抛压。")
        elif kc["change_pct"] < -1:
            parts.append(f"科创50 下跌 {kc['change_pct']:.2f}%，科技股表现偏弱。")

    return " ".join(parts) if parts else "市场平稳运行。"


def generate_position_analysis(funds: list[dict], total_pnl_pct: float | None, indices: list[dict]) -> str:
    """基于基金数据自动生成持仓分析"""
    if not funds:
        return "暂无持仓数据。"

    parts = []

    # 整体盈亏状态
    if total_pnl_pct is not None:
        if total_pnl_pct > 10:
            parts.append(f"整体持仓盈利 +{total_pnl_pct:.2f}%，表现较好。")
        elif total_pnl_pct > 0:
            parts.append(f"整体持仓微盈 +{total_pnl_pct:.2f}%。")
        elif total_pnl_pct > -10:
            parts.append(f"整体持仓微亏 {total_pnl_pct:.2f}%。")
        else:
            parts.append(f"整体持仓亏损 {total_pnl_pct:.2f}%，压力较大。")

    # 当日涨跌分布
    changes = [f["change_pct"] for f in funds if f.get("change_pct") is not None]
    if changes:
        up = sum(1 for c in changes if c > 0)
        down = sum(1 for c in changes if c < 0)
        flat = len(changes) - up - down
        parts.append(f"当日 {len(changes)} 只基金中，{up} 只上涨、{down} 只下跌、{flat} 只平盘。")

    # 最大涨跌基金
    funds_with_change = [f for f in funds if f.get("change_pct") is not None]
    if funds_with_change:
        best = max(funds_with_change, key=lambda f: f["change_pct"])
        worst = min(funds_with_change, key=lambda f: f["change_pct"])
        if best["change_pct"] > 0:
            parts.append(f"表现最好：{best['name']} (+{best['change_pct']:.2f}%)。")
        if worst["change_pct"] < 0:
            parts.append(f"表现最差：{worst['name']} ({worst['change_pct']:.2f}%)。")

    # 持仓盈亏分布
    pnls = [(f["name"], f["pnl_pct"]) for f in funds if f.get("pnl_pct") is not None]
    if pnls:
        profit = [(n, p) for n, p in pnls if p > 0]
        loss = [(n, p) for n, p in pnls if p <= 0]
        if profit:
            names = "、".join([n for n, _ in profit])
            parts.append(f"盈利持仓：{names}。")
        if loss:
            names = "、".join([n for n, _ in loss])
            parts.append(f"亏损持仓：{names}。")

    return "\n\n".join(parts)


def generate_today_focus(funds: list[dict], indices: list[dict]) -> str:
    """自动生成今日关注要点"""
    focuses = []

    # 指数异动
    for idx in indices:
        if abs(idx["change_pct"]) >= 2:
            direction = "大涨" if idx["change_pct"] > 0 else "大跌"
            focuses.append(f"{idx['name']} {direction} {idx['change_pct']:+.2f}%，市场波动加大。")

    # 基金异动（当日涨跌超 2%）
    for f in funds:
        if f.get("change_pct") is not None and abs(f["change_pct"]) >= 2:
            direction = "大涨" if f["change_pct"] > 0 else "大跌"
            focuses.append(f"{f['name']} {direction} {f['change_pct']:+.2f}%。")

    # QDII 滞后提醒
    qdii = [f for f in funds if f.get("is_qdii")]
    if qdii:
        focuses.append(f"QDII 基金 ({'、'.join([f['name'] for f in qdii])}) 净值滞后一天（T-1）。")

    return "\n".join(f"- {f}" for f in focuses) if focuses else "- 市场运行平稳，无显著异动。"


def generate_review(data: dict) -> str:
    date_str = data["date"]
    indices = data.get("indices", [])
    funds = data.get("funds", [])
    total_pnl_pct = data.get("total_pnl_pct")

    title = f"每日理财复盘 {date_str}"

    # 自动生成分析内容
    market_comment = generate_market_comment(indices)
    position_analysis = generate_position_analysis(funds, total_pnl_pct, indices)
    today_focus = generate_today_focus(funds, indices)

    template = f"""---
title: {title}
date: "{date_str}"
draft: true
---

## 大盘指数

{format_indices(indices)}

## 基金持仓概览

{format_funds(funds, total_pnl_pct)}

## 今日关注

{today_focus}

## 大盘点评

{market_comment}

## 持仓分析

{position_analysis}

## 情绪与纪律

<!-- EMOTION_DISCIPLINE_PLACEHOLDER -->

## 操作记录

<!-- OPERATIONS_PLACEHOLDER -->

## 明日计划

<!-- TOMORROW_PLAN_PLACEHOLDER -->
"""
    return template


def main():
    parser = argparse.ArgumentParser(description="批量生成历史复盘 Markdown")
    parser.add_argument("--start", type=str, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="覆盖已有复盘")
    args = parser.parse_args()

    data_dir = Path(__file__).parent.parent / "data" / "daily"
    review_dir = Path(__file__).parent.parent / "src" / "content" / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)

    # 收集所有日期
    all_dates = []
    for f in sorted(data_dir.glob("2*.json")):
        date_str = f.stem
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            all_dates.append(date_str)

    start_date = args.start or all_dates[0]
    end_date = args.end or all_dates[-1]

    target_dates = [d for d in all_dates if start_date <= d <= end_date]

    print(f"日期范围：{start_date} ~ {end_date}")
    print(f"共 {len(target_dates)} 个交易日")

    generated = 0
    skipped = 0

    for date_str in target_dates:
        output_file = review_dir / f"{date_str}.md"

        if not args.force and output_file.exists():
            skipped += 1
            continue

        data = load_daily_data(date_str)
        if not data:
            print(f"  跳过 {date_str}：无数据")
            continue

        content = generate_review(data)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        generated += 1

        if generated % 100 == 0:
            print(f"  已生成 {generated} / {len(target_dates)}")

    print(f"\n生成 {generated} 个复盘文件，跳过 {skipped} 个已有文件")


if __name__ == "__main__":
    main()
