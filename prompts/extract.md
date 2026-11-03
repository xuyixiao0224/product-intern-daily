# 抽取契约

输入：`tasks.json` 中的每个 task（title/description/comments/ocr_text/images/source_url）。

输出：JSON 列表，每个 task 一个对象。**只输出 JSON，不要 Markdown。**

```json
{
  "post_id": "string",
  "is_job_post": true,
  "company": "string",
  "position": "string",
  "email": ["string"],
  "contact": "string",
  "location": "string",
  "employment_type": "实习/日常实习/校招/正职/未知",
  "salary": "string",
  "still_hiring": "在招|无法确认",
  "status_evidence": "引用作者回复/正文二编/标题原话",
  "base_location": "北京/上海/深圳/远程/待确认",
  "referral_code": "内推码，没有写空字符串",
  "email_source": "正文/评论/图片OCR，多个用 / 分隔",
  "comment_email": "只出现在评论里的邮箱",
  "pinned_comment": "置顶评论文本；纯图片写“见置顶评论图片”",
  "closed": false,
  "convertible": false,
  "conversion_evidence": "可转正/无转正的原话；没有写未出现",
  "excluded_reason": "如果排除，写原因",
  "author_companies": 0,
  "confidence": 0.0,
  "reason": "string"
}
```

## 规则

1. **is_job_post**
   - true：有公司/团队、具体职责或 JD、投递方式（邮箱/私信/官网/扫码）之一。
   - false：面经、实习体验、行业讨论、教程、个人求职帖、只有标签没有 JD 的引流帖。

2. **company**
   - 从正文、图片 OCR、评论、作者名推断；不能确定写“未披露”。

3. **position**
   - 清洗成岗位名，不要公司名、动词、地点。

4. **email**
   - 正文 + 评论 + OCR 都看；小写、去空格、去重；多个用 `;` 分隔。
   - 图片里的邮箱如果被遮挡/模糊，降低 confidence，并在 reason 里说明。

5. **still_hiring / closed**
   - 状态只有两个：`在招` / `无法确认`。
   - 标题/正文有“已招到 / 已截止 / 不收了 / 简历已筛完 / 先不投” → `still_hiring=无法确认`，`closed=true`。
   - 作者最新回复有“还在 / 没删就还在 / 招 / 可以投 / 有” → `在招`。
   - 其他 → `无法确认`，不要猜。

6. **convertible**
   - 正文/标题/评论/OCR 出现“可转正 / 转正HC / 有转正 / 留用 / 表现优秀可转正” → `true`；
   - 出现“无转正 / 没有转正 / 不提供转正 / 无HC” → `false`；
   - 都没有 → `false`，默认按日常实习。

7. **过滤**
   - 评论区有“购买 / 同款表格 / 买同款 / 付费 / 岗位表” → `is_job_post=false`，`excluded_reason` 写“评论区售卖表格”。
   - 标题/正文是“收到终面/offer，请问岗位怎么样/职业发展/有没有同岗” → 求助帖，`is_job_post=false`。
   - 无邮箱，且作者主页简介含“岗位表/表格/购买/群/每日更新/校招/内推”，其他笔记出现 >2 家公司 → 多公司引流，`is_job_post=false`。
   - 有内推码但无邮箱 → 保留，写 `referral_code`。
   - 评论/图片 OCR 有邮箱而正文没有 → 保留，写 `comment_email` 和 `email_source`。

8. **status_evidence**
   - 必须能回溯：作者名 + 日期 + 原话，或正文“二编”原话。

9. **confidence**
   - 0–1；邮箱/状态是推断而不是明示时，≤0.6。

## 示例

```json
[
  {
    "post_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
    "is_job_post": true,
    "company": "示例科技",
    "position": "AI产品实习生",
    "email": ["hr@example.com"],
    "contact": "",
    "location": "北京",
    "employment_type": "实习",
    "salary": "",
    "still_hiring": "在招",
    "status_evidence": "作者 11-02 回复：没删就是在招",
    "confidence": 0.85,
    "reason": "有具体 JD、邮箱和作者回复"
  }
]
```
