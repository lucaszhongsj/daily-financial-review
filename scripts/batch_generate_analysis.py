#!/usr/bin/env python3
"""
批量生成复盘分析 JSON。
基于数据特征生成有针对性的分析文本，无需外部 API。

用法：
    python scripts/batch_generate_analysis.py [--start DATE] [--end DATE]
"""
import argparse
import json
import random
import sys
from pathlib import Path

random.seed(42)


def safe(val, default=0):
    """安全取值，处理 None。"""
    return val if val is not None else default


TEMPLATES = {
    "market_up": [
        "今日市场全线收涨，上证涨{sh_change:.2f}%，创业板涨{cy_change:.2f}%。{leading_sector}领涨，市场情绪积极。",
        "今日市场强势上行，深指涨{sz_change:.2f}%，科创50涨{kc_change:.2f}%。{leading_sector}表现突出，成交活跃。",
        "今日主板与创业板齐涨，上证涨{sh_change:.2f}%，创业板涨{cy_change:.2f}%。{leading_sector}引领反弹，风险偏好回升。",
    ],
    "market_down": [
        "今日市场全线回调，上证跌{sh_change:.2f}%，创业板跌{cy_change:.2f}%。{leading_sector}领跌，市场情绪谨慎。",
        "今日市场承压下行，深指跌{sz_change:.2f}%，科创50跌{kc_change:.2f}%。{leading_sector}遭遇抛压，防御情绪升温。",
        "今日主板与创业板齐跌，上证跌{sh_change:.2f}%，创业板跌{cy_change:.2f}%。{leading_sector}拖累明显，成交萎缩。",
    ],
    "market_mixed": [
        "今日市场分化明显，上证{sh_direction}{sh_change:.2f}%，创业板{cy_direction}{cy_change:.2f}%。{leading_sector}表现突出，结构性行情特征显著。",
        "今日市场涨跌互现，深指{sz_direction}{sz_change:.2f}%，科创50{kc_direction}{kc_change:.2f}%。{leading_sector}相对强势，主板表现平淡。",
        "今日主板横盘整理，创业板{cy_direction}{cy_change:.2f}%，科创50{kc_direction}{kc_change:.2f}%。{leading_sector}活跃，整体方向不明。",
    ],
    "market_flat": [
        "今日市场窄幅震荡，上证{sh_direction}{sh_change:.2f}%，创业板{cy_direction}{cy_change:.2f}%。各板块波动不大，市场等待方向选择。",
        "今日市场波动极小，指数基本平盘。{leading_sector}略有异动，整体成交平淡，观望情绪浓厚。",
    ],
}

POSITION_TEMPLATES = {
    "loss_big": [
        "整体持仓亏损{total_pnl:.2f}%，{worst_fund}深套{worst_pnl:.2f}%是主要拖累。{best_fund}盈利{best_pnl:.2f}%是亮点，但难以抵消整体亏损。",
        "整体亏损{total_pnl:.2f}%，{worst_fund}和{worst_fund2}持续拖累。{best_fund}表现相对较好（{best_pnl:.2f}%），但仓位不足以扭转局面。",
    ],
    "loss_small": [
        "整体持仓小幅亏损{total_pnl:.2f}%，{worst_fund}跌{worst_pnl:.2f}%略有拖累。{best_fund}涨{best_pnl:.2f}%提供支撑，整体可控。",
        "整体微亏{total_pnl:.2f}%，各基金涨跌互现。{best_fund}（{best_pnl:.2f}%）和{worst_fund}（{worst_pnl:.2f}%）形成对冲，波动不大。",
    ],
    "profit": [
        "整体持仓盈利{total_pnl:.2f}%，{best_fund}大涨{best_pnl:.2f}%贡献突出。{worst_fund}虽跌{worst_pnl:.2f}%但影响有限。",
        "整体盈利{total_pnl:.2f}%，{best_fund}和{best_fund2}双双上涨。仅{worst_fund}小幅回调，组合整体健康。",
    ],
    "no_pnl": [
        "当日各基金涨跌互现，{best_fund}表现较好，{worst_fund}相对偏弱。整体波动不大，持仓结构稳定。",
    ],
}

EMOTION_TEMPLATES = [
    "市场波动时保持理性最难，但纪律是长期收益的根基。不因单日涨跌改变策略，坚持分散配置。",
    "涨跌都是市场的正常节奏，过度反应往往适得其反。保持耐心，按原计划执行。",
    "连续{streak_word}容易动摇信心，但历史表明情绪决策的胜率很低。相信纪律，相信时间。",
    "短期波动不改变长期逻辑，分散持仓的目的就是在这种时候体现价值。保持稳定心态。",
    "复盘的意义在于记录而非预测，把情绪留在纸面上，把纪律留在操作中。",
]

PLAN_TEMPLATES = [
    "关注明日{focus_index}能否{direction}，{focus_sector}是否持续{sector_trend}。暂无操作计划，继续观察。",
    "明日关注{focus_sector}的持续性，以及{focus_index}的{direction}信号。保持现有仓位，不做追涨杀跌。",
    "短期内关注{focus_index}的支撑位和{focus_sector}的资金流向。按原计划定投，不临时加仓。",
    "明日无明确操作计划，重点观察{focus_index}和{focus_sector}的联动关系。保持纪律。",
]


def classify_market(indices):
    changes = [safe(i.get("change_pct"), 0) for i in indices]
    sh = next((i for i in indices if i["code"] == "sh000001"), None)
    sz = next((i for i in indices if i["code"] == "sz399001"), None)
    cy = next((i for i in indices if i["code"] == "sz399006"), None)
    kc = next((i for i in indices if i["code"] == "sh000688"), None)

    up_count = sum(1 for c in changes if c > 0)
    down_count = sum(1 for c in changes if c < 0)
    avg_change = sum(changes) / len(changes) if changes else 0

    if abs(avg_change) < 0.3:
        return "market_flat", sh, sz, cy, kc
    elif up_count >= 3:
        return "market_up", sh, sz, cy, kc
    elif down_count >= 3:
        return "market_down", sh, sz, cy, kc
    else:
        return "market_mixed", sh, sz, cy, kc


def get_sector(name):
    sectors = {
        "医疗": "医药板块", "健康": "医药板块",
        "光伏": "光伏/新能源", "能源": "新能源",
        "军工": "军工板块", "国防": "军工板块",
        "白酒": "消费/白酒", "消费": "消费板块",
        "亚洲": "QDII/海外市场", "QDII": "QDII/海外市场",
    }
    for key, sector in sectors.items():
        if key in name:
            return sector
    return "相关板块"


def find_leading(funds, market_type):
    if not funds:
        return "市场"
    if market_type in ("market_up", "market_mixed"):
        best = max(funds, key=lambda f: safe(f.get("change_pct"), -999))
        return get_sector(best["name"])
    else:
        worst = min(funds, key=lambda f: safe(f.get("change_pct"), 999))
        return get_sector(worst["name"])


def generate_market_comment(data, market_type, sh, sz, cy, kc):
    funds = data.get("funds", [])
    leading = find_leading(funds, market_type)

    ctx = {
        "sh_change": abs(safe(sh["change_pct"], 0)) if sh else 0,
        "sz_change": abs(safe(sz["change_pct"], 0)) if sz else 0,
        "cy_change": abs(safe(cy["change_pct"], 0)) if cy else 0,
        "kc_change": abs(safe(kc["change_pct"], 0)) if kc else 0,
        "sh_direction": "涨" if (sh and safe(sh["change_pct"], 0) >= 0) else "跌",
        "sz_direction": "涨" if (sz and safe(sz["change_pct"], 0) >= 0) else "跌",
        "cy_direction": "涨" if (cy and safe(cy["change_pct"], 0) >= 0) else "跌",
        "kc_direction": "涨" if (kc and safe(kc["change_pct"], 0) >= 0) else "跌",
        "leading_sector": leading,
    }

    tmpl = random.choice(TEMPLATES[market_type])
    return tmpl.format(**ctx)


def generate_position_analysis(data):
    funds = data.get("funds", [])
    total_pnl = data.get("total_pnl_pct")

    if not funds:
        return "暂无持仓数据。"

    has_pnl = any(f.get("pnl_pct") is not None for f in funds)

    sorted_funds = sorted(funds, key=lambda f: safe(f.get("pnl_pct"), -999))
    worst = sorted_funds[0]
    best = sorted_funds[-1]

    worst_pnl = worst.get("pnl_pct")
    best_pnl = best.get("pnl_pct")

    ctx = {
        "total_pnl": abs(safe(total_pnl, 0)),
        "worst_fund": worst["name"].split("(")[0],
        "worst_pnl": abs(safe(worst_pnl, 0)),
        "best_fund": best["name"].split("(")[0],
        "best_pnl": abs(safe(best_pnl, 0)),
        "worst_fund2": sorted_funds[1]["name"].split("(")[0] if len(sorted_funds) > 1 else worst["name"].split("(")[0],
        "best_fund2": sorted_funds[-2]["name"].split("(")[0] if len(sorted_funds) > 1 else best["name"].split("(")[0],
    }

    if not has_pnl:
        tmpl = random.choice(POSITION_TEMPLATES["no_pnl"])
    elif total_pnl is not None and total_pnl <= -10:
        tmpl = random.choice(POSITION_TEMPLATES["loss_big"])
    elif total_pnl is not None and total_pnl < 0:
        tmpl = random.choice(POSITION_TEMPLATES["loss_small"])
    else:
        tmpl = random.choice(POSITION_TEMPLATES["profit"])

    return tmpl.format(**ctx)


def generate_today_focus(data, market_type):
    funds = data.get("funds", [])
    indices = data.get("indices", [])

    lines = []

    big_moves = [i for i in indices if abs(safe(i.get("change_pct"), 0)) >= 1.5]
    for idx in sorted(big_moves, key=lambda x: abs(safe(x.get("change_pct"), 0)), reverse=True)[:2]:
        direction = "大涨" if safe(idx.get("change_pct"), 0) > 0 else "大跌"
        lines.append(f"{idx['name']}{direction}{abs(safe(idx.get('change_pct'), 0)):.2f}%")

    if funds:
        fund_moves = sorted(funds, key=lambda f: abs(safe(f.get("change_pct"), 0)), reverse=True)
        top = fund_moves[0]
        direction = "领涨" if safe(top.get("change_pct"), 0) > 0 else "领跌"
        lines.append(f"{top['name'].split('(')[0]}{direction}{abs(safe(top.get('change_pct'), 0)):.2f}%")

        qdii = [f for f in funds if f.get("is_qdii")]
        for q in qdii:
            lines.append(f"{q['name'].split('(')[0]}(QDII)净值滞后一天")

    if not lines:
        lines.append("市场波动不大，各板块表现平稳。")

    return "。".join(lines[:3]) + "。"


def generate_emotion_discipline(data):
    indices = data.get("indices", [])
    changes = [safe(i.get("change_pct"), 0) for i in indices]
    avg_change = sum(changes) / len(changes) if changes else 0

    if abs(avg_change) >= 1.5:
        streak_word = "大涨" if avg_change > 0 else "大跌"
    elif abs(avg_change) >= 0.5:
        streak_word = "上涨" if avg_change > 0 else "下跌"
    else:
        streak_word = "震荡"

    tmpl = random.choice(EMOTION_TEMPLATES)
    return tmpl.format(streak_word=streak_word)


def generate_tomorrow_plan(data, market_type):
    indices = data.get("indices", [])
    funds = data.get("funds", [])

    focus_idx = next((i for i in indices if i["code"] in ("sz399006", "sh000688")), indices[0] if indices else None)
    focus_index = focus_idx["name"] if focus_idx else "创业板"

    if funds:
        focus_fund = max(funds, key=lambda f: abs(safe(f.get("change_pct"), 0)))
        focus_sector = get_sector(focus_fund["name"])
        sector_trend = "走强" if safe(focus_fund.get("change_pct"), 0) > 0 else "调整"
    else:
        focus_sector = "主要板块"
        sector_trend = "企稳"

    direction = "企稳" if market_type in ("market_down", "market_flat") else "延续"

    tmpl = random.choice(PLAN_TEMPLATES)
    return tmpl.format(
        focus_index=focus_index,
        direction=direction,
        focus_sector=focus_sector,
        sector_trend=sector_trend,
    )


def analyze_date(date_str: str) -> dict | None:
    data_file = Path("data") / f"{date_str}.json"
    if not data_file.exists():
        return None

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    analysis_file = Path("data/analysis") / f"{date_str}.json"
    if analysis_file.exists():
        return None

    market_type, sh, sz, cy, kc = classify_market(data.get("indices", []))

    return {
        "date": date_str,
        "today_focus": generate_today_focus(data, market_type),
        "market_comment": generate_market_comment(data, market_type, sh, sz, cy, kc),
        "position_analysis": generate_position_analysis(data),
        "emotion_discipline": generate_emotion_discipline(data),
        "tomorrow_plan": generate_tomorrow_plan(data, market_type),
    }


def main():
    parser = argparse.ArgumentParser(description="批量生成复盘分析")
    parser.add_argument("--start", type=str, help="起始日期")
    parser.add_argument("--end", type=str, help="结束日期")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date", type=str, help="单个日期")
    args = parser.parse_args()

    analysis_dir = Path("data/analysis")
    analysis_dir.mkdir(exist_ok=True)

    if args.date:
        dates = [args.date]
    else:
        data_dir = Path("data")
        all_dates = sorted(
            [f.stem for f in data_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json")
             if len(f.stem) == 10],
            reverse=True,
        )
        if args.start:
            all_dates = [d for d in all_dates if d >= args.start]
        if args.end:
            all_dates = [d for d in all_dates if d <= args.end]
        dates = [d for d in all_dates if not (analysis_dir / f"{d}.json").exists()]

    if not dates:
        print("所有日期已完成分析。")
        return

    total = len(dates)
    print(f"待处理日期：{total}")

    processed = 0
    for i, date_str in enumerate(dates, 1):
        analysis = analyze_date(date_str)
        if not analysis:
            continue

        if args.dry_run:
            print(f"\n=== {date_str} ===")
            for k, v in analysis.items():
                print(f"  {k}: {v}")
        else:
            path = analysis_dir / f"{date_str}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)

        processed += 1
        if i % 50 == 0 or i == total:
            print(f"  进度：{i}/{total} ({i/total*100:.1f}%)")

    print(f"\n完成：{processed} 个日期")


if __name__ == "__main__":
    main()
