# 每日复盘 SOP

## 项目结构

```
data/source/YYYY-MM-DD.json       # 原始市场数据
data/analysis/YYYY-MM-DD.json     # AI 分析结果
config/positions.json             # 持仓配置（敏感，不在 git）
scripts/daily_pull.sh             # 每日一键复盘
src/pages/                        # 首页、统计、搜索、复盘详情
src/content/reviews/              # 复盘 Markdown
```

## 每日标准流程

```bash
bash scripts/daily_pull.sh [YYYY-MM-DD]
```

内部顺序：
1. `fetch_market_data.py` — 拉取指数和基金净值
2. `batch_generate_analysis.py` — 生成分析 JSON
3. `generate_review.py` — 生成 Markdown 草稿
4. `publish_review.py` — 去掉 draft，发布

## 发布

```bash
git add src/content/reviews/ data/
git commit -m "publish: 每日复盘 YYYY-MM-DD"
git push
npm run build
```

## 前端页面

| 页面 | 说明 |
|------|------|
| `/` | 首页：日历热力图、历史列表 |
| `/stats` | 统计分析：持仓趋势、基金对比、指数统计 |
| `/search` | 搜索：关键词+盈亏筛选+排序 |
| `/review/YYYY-MM-DD` | 复盘详情：指数卡、基金卡、时间线导航 |

## 批量历史回溯

```bash
python3 scripts/batch_generate_analysis.py --start DATE --end DATE
python3 scripts/batch_generate_reviews.py --start DATE --end DATE
```

## 注意事项

- 日常只需运行 `daily_pull.sh`
- 分析文本基于规则模板，关键日期建议人工复核
- 持仓配置变更后需重新拉取历史数据
- 新生成复盘默认 `draft: true`，`daily_pull.sh` 自动改为 `draft: false`
