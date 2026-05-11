# 重构 data 目录结构

## 现状

`data/` 目录下直接存放 1321 个日期命名 JSON（`YYYY-MM-DD.json`），与 `analysis/` 子目录并列。数据类型混杂，不利于扩展和维护。

## 目标

将原始每日数据与派生分析数据分离，建立清晰的目录层级。

## 新目录结构

```
data/
  daily/          # 原始每日市场+持仓数据（从 data/*.json 移入）
    2020-11-23.json
    ...
  analysis/       # 复盘分析结果（保持不动）
    2020-11-23.json
    ...
  historical_nav/ # 历史净值原始数据（保持不动）
```

## 影响范围

需修改路径引用的脚本：
- `scripts/batch_analyze.py`
- `scripts/fetch_historical_indices.py`
- `scripts/fetch_market_data.py`
- `scripts/generate_historical_reviews_md.py`
- `scripts/generate_historical_reviews.py`
- `scripts/generate_review.py`
- `scripts/transform_historical_nav.py`
- `scripts/batch_generate_analysis.py`
- `scripts/batch_generate_reviews.py`

## 变更规则

- 所有 `data/YYYY-MM-DD.json` 路径改为 `data/daily/YYYY-MM-DD.json`
- `data_dir.glob("[0-9][0-9][0-9][0-9]-*.json")` 类模式改为 `data_dir / "daily"`
- `.gitignore` 中 `data/*.json` 改为 `data/daily/*.json`（保留 analysis/ 和 historical_nav/ 的追踪）
- 文件移动使用 `git mv`，保留历史记录

## 边界

- `data/analysis/` 不动
- `data/historical_nav/` 不动
- `config/positions.json` 和 `config/positions.example.json` 不动
