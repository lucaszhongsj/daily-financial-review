# 重命名 data/daily 为 data/source

## 目标

将 `data/daily/` 重命名为 `data/source/`，表达"原始源数据"含义，与 `data/analysis/`（派生分析）形成更清晰的语义对比。

## 变更范围

1. `git mv data/daily/ data/source/`
2. 更新 `.gitignore`：`data/daily/*.json` → `data/source/*.json`
3. 更新所有脚本中 `data/daily/` 路径引用为 `data/source/`
4. 涉及脚本：batch_analyze.py, batch_generate_analysis.py, fetch_historical_indices.py, fetch_market_data.py, generate_historical_reviews.py, generate_historical_reviews_md.py, generate_review.py
