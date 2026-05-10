#!/usr/bin/env bash
# 每日数据拉取 + 复盘草稿生成
# 用法：./daily_pull.sh [YYYY-MM-DD]
# 不传日期时自动判断：21:30 前分析昨日，21:30 后分析今日

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

DATE_ARG="${1:-}"

echo "=== 拉取市场数据 ==="
if [ -n "$DATE_ARG" ]; then
    .venv/bin/python3 scripts/fetch_market_data.py --date "$DATE_ARG"
    TARGET_DATE="$DATE_ARG"
else
    .venv/bin/python3 scripts/fetch_market_data.py
    # 从最新生成的 json 文件名获取日期
    TARGET_DATE=$(ls -t data/*.json 2>/dev/null | head -1 | sed 's|data/||;s|\.json||')
fi

echo "=== 生成复盘草稿 ==="
.venv/bin/python3 scripts/generate_review.py --date "$TARGET_DATE"

echo "=== 完成 ==="
