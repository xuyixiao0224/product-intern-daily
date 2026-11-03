# 每日更新与 GitHub 自动发布

## 结论先说

**不要让 GitHub-hosted Actions 直接登录小红书。**  
GitHub 的 runner 没有你的 Cookie，也不应该把 Cookie 放进 Secrets；正确做法是：

> **本地/自托管机器跑采集 → 提交 `jobs.json` + 生成 `docs/` → GitHub Actions 只做 CI 校验（Pages 已关闭）。**

## 推荐架构

```text
每天 09:00（本地 launchd / cron / VPS）
  ├─ 3 个关键词，只搜“一天内”
  ├─ 40–60 条详情，2 并发，3–8 秒 jitter
  ├─ OCR → 抽取 → 过滤 → 去重 → 合并 jobs.json
  ├─ 生成 docs/index.html / JOBS.md / feed.xml
  ├─ git add data/jobs.json docs/
  ├─ git commit -m "chore: daily YYYY-MM-DD"
  ├─ git push
  └─ send_digest.py（可选）
        ↓
GitHub Actions: CI validate
```

## 每日命令

```bash
# 1. 只搜 3 个关键词，不做 Base × 时间矩阵
python scripts/collect_seed.py --mode daily --target 60 --out data/daily/candidates.json

# 2. 低并发抓详情（2 并发，脚本内已有间隔）
python scripts/fetch_parallel.py data/daily/candidates.json data/daily/details 60 2

# 3. OCR + 规则抽取
python scripts/ocr_covers.py --details data/daily/details --out data/daily/ocr --covers data/daily/covers_raw
OCR_DIR=data/daily/ocr python scripts/heuristic_extract.py data/daily/details data/daily/extractions.json

# 4. 产品过滤 + 可转正标签
python scripts/build_seed_report.py --details data/daily/details --extractions data/daily/extractions.json --out data/daily/jobs.json --covers data/daily/covers

# 5. 合并进累计数据（按 email → 公司+岗位 → post_id 去重）
python scripts/merge_jobs.py --base data/jobs.json --new data/daily/jobs.json --out data/jobs.json
python scripts/build_site.py data/jobs.json docs/index.html --images-dir data/covers
python scripts/generate_readme.py data/jobs.json docs/JOBS.md
python scripts/build_feed.py data/jobs.json docs/feed.xml

# 6. 发布
git add data/jobs.json docs/
git commit -m "chore: daily $(date +%F)" || true
git push
```

## launchd（macOS）

`~/Library/LaunchAgents/com.product-intern-daily.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.product-intern-daily</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>/path/to/product-intern-daily/scripts/daily.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/product-intern-daily.log</string>
  <key>StandardErrorPath</key><string>/tmp/product-intern-daily.err</string>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.product-intern-daily.plist
```

## 怎么“保证”

- **幂等**：按 note_id/email 去重，重复跑不会重复插入；
- **失败即停**：`set -euo pipefail`，出现 `cannot reach` / 461 立即退出；
- **健康检查**：成功后 ping healthchecks.io 或发 Telegram；24h 没 ping 就告警；
- **保留最后成功时间**：`data/.last_success`；
- **Git 失败重试**：push 失败重试 3 次；冲突时先 pull --rebase；
- **不把 Cookie 放 GitHub**：Actions 只校验 `jobs.json` 和部署 `docs/`；
- **无新增也提交**：写 `last_run`/healthcheck，避免“看起来每天都没更新”。

> “保证”只能做到工程上的可观测、可重试、可告警；小红书风控/账号异常无法 100% 保证。
