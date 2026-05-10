# 批量历史数据复盘分析

## 背景

项目已有 `daily-review` 单日分析工作流：读取当日 `data/YYYY-MM-DD.json`，生成 `data/analysis/YYYY-MM-DD.json` 分析文本，再产出 `src/content/reviews/YYYY-MM-DD.md` 复盘草稿。

现需对历史存量数据做批量回溯分析，覆盖从最早交易日到最近交易日的完整区间。

## 目标

为 2020-11-23 至 2026-05-08 之间所有已有数据文件的交易日，逐一生成复盘分析文件和 Markdown 草稿。

已有分析文件的日期自动跳过，不重复生成。

## 数据范围

- 数据文件位置：`data/YYYY-MM-DD.json`
- 已有分析文件位置：`data/analysis/YYYY-MM-DD.json`
- 总数据文件：1321 个
- 已有分析：50 个
- 待处理日期：1271 个

## 批次策略

- 批次大小：**5 天/批**（小批）
- 处理方向：**倒序**（从最近日期 2026-05-08 向最早日期 2020-11-23）
- 总批数：约 255 批
- 已完成的日期自动跳过

## 分析内容（每日期）

基于当日 `data/YYYY-MM-DD.json` 中的指数和基金数据，生成以下 5 个字段：

| 字段 | 说明 | 字数限制 |
|------|------|----------|
| `today_focus` | 今日关注：市场关键事件、异动板块、重要数据 | 100 字以内 |
| `market_comment` | 大盘点评：主要指数表现、市场风格、成交量 | 200 字以内 |
| `position_analysis` | 持仓分析：各基金当日表现、盈亏归因、整体评估 | 200 字以内 |
| `emotion_discipline` | 情绪与纪律：当日心态、纪律遵守、反思 | 150 字以内 |
| `tomorrow_plan` | 明日计划：关注方向、可能的操作、策略调整 | 150 字以内 |

`operations`（操作记录）留空 `"无"`，由用户后续按需补充。

## 输出格式

### 1. 分析 JSON

路径：`data/analysis/YYYY-MM-DD.json`

```json
{
  "date": "YYYY-MM-DD",
  "today_focus": "...",
  "market_comment": "...",
  "position_analysis": "...",
  "emotion_discipline": "...",
  "tomorrow_plan": "..."
}
```

### 2. 复盘 Markdown

路径：`src/content/reviews/YYYY-MM-DD.md`

基于 `scripts/review_template.md` 模板生成，包含：
- Frontmatter（title, date, draft: true）
- 大盘指数表格
- 基金持仓概览表格
- 今日关注、大盘点评、持仓分析、情绪与纪律、操作记录、明日计划

使用 `scripts/generate_review.py` 生成，该脚本会自动读取 `data/YYYY-MM-DD.json` 中的 `analysis` 字段嵌入模板。

## 执行流程

```
batch_analyze.py --batch-size 5 --reverse --start 2020-11-23 --end 2026-05-08
  ↓
逐批读取 5 个日期的 data/YYYY-MM-DD.json
  ↓
Claude 为每个日期生成分析文本（大盘点评、持仓分析等）
  ↓
保存 analysis JSON 到 data/analysis/
  ↓
运行 generate_review.py 生成 Markdown 草稿
  ↓
重复直到所有批次完成
```

## 质量要求

1. 分析文本必须基于当日真实数据，不编造不存在的市场事件
2. 分析应结合持仓盈亏百分比和当日涨跌幅，给出有意义的洞察
3. QDII 基金标注"净值滞后"，分析时注明实际反映日期
4. 不同日期的分析应有区分度，反映当日市场真实差异
5. 情绪与纪律和明日计划应体现连续交易日的思考延续性

## 跳过规则

- 已有 `data/analysis/YYYY-MM-DD.json` 的日期跳过
- 缺失 `data/YYYY-MM-DD.json` 的日期跳过
- 用户可随时说"跳过此批"进入下一批
