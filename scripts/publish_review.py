#!/usr/bin/env python3
"""
复盘 publish 辅助脚本：替换占位符、生成标题、去掉 draft。
用法（由 Claude 内部调用，非手动）：
    python3 scripts/publish_review.py --date YYYY-MM-DD \
        --title "xxx" \
        --today-focus "xxx" \
        --market-comment "xxx" \
        --position-analysis "xxx" \
        --emotion-discipline "xxx" \
        --operations "xxx" \
        --tomorrow-plan "xxx"

或从 AI 分析 JSON 文件读取：
    python3 scripts/publish_review.py --date YYYY-MM-DD --ai-input data/analysis/YYYY-MM-DD.json
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PLACEHOLDERS = {
    "today_focus": "<!-- TODAY_FOCUS_PLACEHOLDER -->",
    "market_comment": "<!-- MARKET_COMMENT_PLACEHOLDER -->",
    "position_analysis": "<!-- POSITION_ANALYSIS_PLACEHOLDER -->",
    "emotion_discipline": "<!-- EMOTION_DISCIPLINE_PLACEHOLDER -->",
    "operations": "<!-- OPERATIONS_PLACEHOLDER -->",
    "tomorrow_plan": "<!-- TOMORROW_PLAN_PLACEHOLDER -->",
}


def main():
    parser = argparse.ArgumentParser(description="Publish 复盘草稿")
    parser.add_argument("--date", required=True)
    parser.add_argument("--title")
    parser.add_argument("--today-focus", default="暂无")
    parser.add_argument("--market-comment", default="暂无")
    parser.add_argument("--position-analysis", default="暂无")
    parser.add_argument("--emotion-discipline", default="暂无")
    parser.add_argument("--operations", default="无")
    parser.add_argument("--tomorrow-plan", default="暂无")
    parser.add_argument("--ai-input", type=str, help="从 AI 分析 JSON 文件读取占位符内容")
    args = parser.parse_args()

    # 若指定了 --ai-input，从 JSON 读取分析内容
    if args.ai_input:
        ai_path = Path(args.ai_input)
        if not ai_path.exists():
            print(f"AI 分析文件不存在：{ai_path}", file=sys.stderr)
            sys.exit(1)
        with open(ai_path, "r", encoding="utf-8") as f:
            ai_data = json.load(f)
        args.today_focus = ai_data.get("today_focus", args.today_focus)
        args.market_comment = ai_data.get("market_comment", args.market_comment)
        args.position_analysis = ai_data.get("position_analysis", args.position_analysis)
        args.emotion_discipline = ai_data.get("emotion_discipline", args.emotion_discipline)
        args.tomorrow_plan = ai_data.get("tomorrow_plan", args.tomorrow_plan)

    # 标题默认使用日期格式
    if not args.title:
        args.title = f"每日理财复盘 {args.date}"

    review_file = Path("src/content/reviews") / f"{args.date}.md"
    if not review_file.exists():
        print(f"草稿不存在：{review_file}", file=sys.stderr)
        sys.exit(1)

    content = review_file.read_text(encoding="utf-8")

    # 处理命令行传入的转义换行
    def unescape(val: str) -> str:
        return val.replace("\\n", "\n")

    # 替换标题
    content = content.replace(f"title: 每日理财复盘 {args.date}", f'title: "{args.title}"')

    # 替换占位符
    content = content.replace(PLACEHOLDERS["today_focus"], unescape(args.today_focus))
    content = content.replace(PLACEHOLDERS["market_comment"], unescape(args.market_comment))
    content = content.replace(PLACEHOLDERS["position_analysis"], unescape(args.position_analysis))
    content = content.replace(PLACEHOLDERS["emotion_discipline"], unescape(args.emotion_discipline))
    content = content.replace(PLACEHOLDERS["operations"], unescape(args.operations))
    content = content.replace(PLACEHOLDERS["tomorrow_plan"], unescape(args.tomorrow_plan))

    # 去掉 draft
    content = content.replace("draft: true", "draft: false")

    review_file.write_text(content, encoding="utf-8")
    print(f"已发布：{review_file}")


if __name__ == "__main__":
    main()
