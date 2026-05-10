#!/usr/bin/env bash
# 每日数据拉取 + 复盘草稿生成
# 用法：./daily_pull.sh [YYYY-MM-DD]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

DATE_ARG="${1:-$(date +%Y-%m-%d)}"

# 判断是否为交易日（非周末）
DOW=$(date -j -f "%Y-%m-%d" "$DATE_ARG" +%u 2>/dev/null || date -d "$DATE_ARG" +%u)
if [ "$DOW" -gt 5 ]; then
    echo "$DATE_ARG 非交易日，跳过"
    exit 0
fi

PYTHON="${PYTHON:-.venv/bin/python3}"

echo "=== 拉取 $DATE_ARG 市场数据 ==="
$PYTHON scripts/fetch_market_data.py --date "$DATE_ARG"

echo "=== 生成复盘草稿 ==="
$PYTHON scripts/generate_review.py --date "$DATE_ARG"

echo "=== 完成 ==="
