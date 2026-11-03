# 数据模型

一条岗位 = `post_id` 唯一。

| 字段 | 说明 |
|---|---|
| `post_id` | 小红书 note id |
| `source_url` | 原帖链接（带 xsec_token） |
| `company` / `position` | 公司 / 岗位 |
| `base_location` | Base 地 |
| `email` / `email_source` | 邮箱 / 来源（正文/评论/图片OCR） |
| `comment_email` | 只出现在评论里的邮箱 |
| `referral_code` | 内推码 |
| `published_at` | 发帖时间 |
| `still_hiring` | 只有 `在招` / `无法确认` |
| `status_evidence` | 作者回复/正文二编原话 |
| `closed` | 已截止/已招到；默认不导出 |
| `convertible` | 是否可转正（可转正/转正HC/留用） |
| `conversion_evidence` | 转正/无转正原话 |
| `excluded_reason` | 购买表格/求助帖/引流等排除原因 |
| `confidence` | 0–1 |
| `dedup_key` | email → company+position → note_id |

## 过滤规则

1. 评论区 `购买/同款表格/付费/岗位表` → 排除。
2. 求助/职业咨询帖 → 排除。
3. 无邮箱 + 作者简介含岗位表/购买等 + 其他笔记 >2 家公司 → 排除。
4. 已截止/已招到 → `closed=true`，默认不导出。
5. 有内推码无邮箱 → 保留。

## 状态

- `在招`：作者最新回复明确“还在/没删就还在/招/可以投/有”。
- `无法确认`：其他；如已知截止，`closed=true` + evidence。
