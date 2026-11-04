---
name: product-intern-daily
description: 用本地 xiaohongshu-mcp 搜索小红书招聘帖，拉正文/全部图片/评论/置顶评论，由当前 Agent 自己抽取公司、岗位、Base、邮箱、内推码、发布时间和在招状态，并按邮箱去重导出 CSV/HTML。手动模式由当前 Agent 抽取，不强制 API Key；自动任务可走 CLI + OpenAI-compatible API。
---

# product-intern-daily（Codex / Claude Code / API）

## 前置

- 本地 `xiaohongshu-mcp` 已启动（默认 `http://127.0.0.1:18060/mcp`）并扫码登录。
- Python 3.10+。
- 本地 OCR：macOS `ocrmac` + `sips`（Apple Vision，不收费）；`--ocr` 时必须安装，未安装会报错并提示 `pip install -e ".[ocr]"`。

## 流程

```bash
# 1. 搜索（最新 + 一天内，多关键词）
python run.py search \
  --keyword "AI产品实习" --keyword "AI产品经理实习" \
  --sort 最新 --publish-time 一天内 --note-type 图文 \
  --out candidates.json

# 2. 详情 + 全部图片 OCR（含翻转/旋转）
python run.py fetch candidates.json --out details --ocr

# 3. 生成抽取任务
python run.py extract --details details --out tasks.json --prepare

# 4. 当前 Agent 读 tasks.json，按 prompts/extract.md 输出 extractions.json

# 5. 导入 + 导出
python run.py extract --import-file extractions.json --details details
python run.py export --format csv,html --out exports --since 7d
```

## 规则

- 状态只有 `在招` / `无法确认`；已截止/已招到用 `closed=true` + `status_evidence` 记录，默认不导出。
- Base 地写到 `base_location`，同时保留 `location`。
- 有内推码但无邮箱：保留，写 `referral_code`。
- 邮箱来源写到 `email_source`（正文/评论/图片OCR）；只出现在评论的写 `comment_email`。
- 评论区出现 `购买/同款表格/付费/岗位表` → 排除（引流）。
- 求助帖（“收到终面，请问岗位怎么样/职业发展…”）→ 排除。
- 无邮箱 + 作者主页含岗位表/购买等 + 其他笔记 >2 家公司 → 判为多公司引流，排除。
- 只读：不要调用 `publish_content`、`post_comment_to_feed`、`like_feed`。
- 控制频率：2–5 秒/次；验证码/登录失效立即停。

## 已知限制

- 原版 `xiaohongshu-mcp` 的 `Comment` 结构体没有图片字段，纯图片置顶评论只返回 `showTags:["user_top"]` + 空 `content`。
- 本仓库提供补丁 `patches/xiaohongshu-mcp-comment-pictures.patch`，给 `Comment` 加 `pictures/imageList/images`；构建后 `get_feed_detail` 会返回评论图片，OCR 就能读到。
- 不打补丁时，代码仍支持接口已返回的评论图片字段，但这类纯图片评论会拿不到。

## 输出

`exports/jobs.csv` + `exports/jobs.html`（含 Base、邮箱来源、内推码、封面、正文、评论证据、原帖链接）。
