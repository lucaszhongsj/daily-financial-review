# macOS crontab 配置说明

## 1. 编辑 crontab

```bash
crontab -e
```

## 2. 添加定时任务

工作日 16:30 自动执行数据拉取：

```
30 16 * * 1-5 /bin/bash scripts/daily_pull.sh >> /tmp/daily_finance.log 2>&1
```

注意：请将路径替换为实际项目路径。

## 3. 补拉历史数据

```bash
for date in 2026-05-06 2026-05-07 2026-05-08; do
    bash scripts/daily_pull.sh "$date"
done
```

## 4. 查看日志

```bash
tail -f /tmp/daily_finance.log
```
