# Product Intern Daily · 产品实习日报

> **每天 5 分钟，看完还在招的产品实习。**  
> 公开网页 / RSS / 邮件，零登录；只收产品实习，带 Base、投递方式、在招证据和原帖链接。

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/xuyixiao0224/product-intern-daily/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![Pages](https://img.shields.io/badge/site-GitHub%20Pages-0969da)](docs/index.html)

![产品实习日报截图](docs/screenshot.png)

---

## 为什么做这个

找产品实习，最痛的不是“没有岗位”，而是**信息太散、太脏、太费时间**。

### 1. 小红书是组内直招，流程真的更快

很多帖子来自组内成员/即将离职的实习生，直接留邮箱或私信，绕过官网的初筛和流程。  
相比 Boss 直聘、官网投递，响应更快，也更容易拿到“人”的反馈。

### 2. 但“最新”不等于“相关”

- 首页推荐有时效，但刷多了全是岗位，想看别的都刷不到；
- 搜索按时间排序的精度低，旧帖、面经、引流、已截止混在一起；
- 我们抽样 100 条：**只有 10 条能拿到投递邮箱，12 条明确在招，4 条既在招又有邮箱**。

### 3. 提取成本高

一条帖子里的关键信息散落在：标题、正文、评论区、图片 OCR、置顶评论。  
要汇总成“公司 / 岗位 / Base / 邮箱 / 是否在招”，人工一天看 20 条就到极限。

### 4. 每天刷，真的会忘

今天刷到一条，明天就沉底；没有记录、没有去重、没有提醒。

### 5. 所以做了这个

> **不是另一个爬虫，是一个每天更新、可验证、可订阅的产品实习情报站。**

---

## 我们怎么做

```text
搜索（最新 + 一天内/一周内）
  → 详情（正文/图片/评论/置顶评论）
  → 本地 OCR（原图 + 旋转 + 翻转）
  → 结构化（公司/岗位/Base/邮箱/内推码/状态）
  → 过滤（面经/求助/购买表格/多公司引流）
  → 邮箱去重
  → 网页 / RSS / 邮件
```

**三条原则：**

1. **只收产品实习**：产品经理/产品运营/产品策划/策略产品/AI 产品。
2. **每条都有证据**：状态写作者回复或正文“二编”原话，不猜。
3. **公开、可删除**：来源链接可追溯；作者要求删除就删；不卖数据。

---

## 数据说话（100 条抽样）

| 指标 | 数量 |
|---|---:|
| 抓取详情 | 100 |
| 判定为招聘帖 | 66 |
| 产品相关（去重后） | 24 |
| 有投递邮箱 | 10 |
| 明确在招 | 12 |
| 既在招又有邮箱 | 4 |

> 这就是“搜索按时间排序”的真实体感：100 条里，真正可投的只有个位数到十几条。

---


## 功能

- **时间过滤**：`sort_by=最新` + `publish_time=一天内/一周内/半年内`，再用 `note.time` 精确排序。
- **过滤**：购买/同款表格评论、求助/职业咨询帖、作者多公司引流。
- **字段**：Base 地、内推码、邮箱来源、评论邮箱、置顶评论、是否已截止、**是否可转正**。
- **详情**：标题、正文、作者、发布时间、图片、评论/子评论。
- **OCR（可选）**：macOS Vision（`ocrmac`）读图片里的 JD/邮箱/内推码。
- **Agent 抽取**：DSH/Codex 直接读详情，输出严格 JSON；**不需要额外大模型 API Key**。
- **邮箱优先去重**：email → company+position → note_id。
- **在招判断**：标题/正文“已招到/已截止/二编”、作者回复、发布时间。
- **转正标签**：出现“可转正/转正HC/留用”等 → 可转正；出现“无转正/无HC” → 日常；否则默认日常实习。
- **证据链**：每条状态都保存原话，不黑箱。
- **增量**：SQLite + `seen` + 详情文件缓存；`content_hash` 预留给后续变更检测。
- **导出**：CSV + 可浏览 HTML。

---

## 不做什么（Non-goals）

- ❌ 不做 Web UI / SaaS / 账号系统；
- ❌ 不做自动投递、自动私信、自动评论；
- ❌ 不做多平台（先把小红书跑稳）；
- ❌ 不自己实现浏览器/登录/反爬（继续用 `xiaohongshu-mcp`）；
- ❌ 不把 cookies、真实邮箱、抓取数据提交到仓库；
- ❌ 不绑定某一家 LLM（Agent 抽 / API 抽都可）。

---

## 安装

```bash
# Python 3.10+
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

# 可选：图片 OCR（macOS）
pip install -e ".[ocr]"
```

前置：本地已启动 `xiaohongshu-mcp`，并完成扫码登录。

```bash
# 检查
product-intern-daily doctor
```

---

## 快速开始

```bash
# 1) 搜索：最新 + 一天内 + 图文
product-intern-daily search \
  --role AI产品 --base 北京 \
  --sort 最新 --publish-time 一天内 --note-type 图文 \
  --out candidates.json

# 每日默认关键词 = 产品实习 / 产品继任 / 互联网产品
# 也可以显式 --keyword "AI产品实习" --keyword "AI产品经理实习"

# 2) 拉详情（--ocr 可选）
product-intern-daily fetch candidates.json --out details --ocr

# 3) 给 Agent 准备抽取任务
product-intern-daily extract --details details --out tasks.json --prepare

# 4) Agent 读 tasks.json + prompts/extract.md，写 extractions.json
#    然后导入
product-intern-daily extract --import-file extractions.json --details details

# 5) 导出
product-intern-daily export --format csv,html --out exports --since 7d
```

没有安装时，也可以用仓库根目录的 `run.py`：

```bash
python run.py doctor
python run.py search --keyword "AI产品实习" --out candidates.json
```

---

## 命令

| 命令 | 作用 |
|---|---|
| `doctor` | 检查 MCP、登录态、OCR、DB |
| `search` | 多关键词搜索 + note 去重，输出 candidates.json |
| `fetch` | 拉详情/评论/图片，可选 OCR |
| `extract --prepare` | 生成 Agent 抽取任务（tasks.json） |
| `extract --import-file` | 校验并写入 SQLite |
| `export` | 按邮箱去重，导出 CSV/HTML |
| `status` | 查看 DB 统计 |

---

## 时间过滤

> `sort_by=最新` 会牺牲相关性：越新越可能混入无关帖。建议多关键词 + Agent 过滤，不要只靠一个词。

`search_feeds` 支持小红书站内筛选：

```json
{"sort_by":"最新","publish_time":"一天内","note_type":"图文"}
```

- `publish_time` 只有 `不限 / 一天内 / 一周内 / 半年内`，没有自定义区间；
- 搜索结果**不带发布时间**，`fetch` 后用 `data.note.time` 精确排序；
- 一次搜索约 20 条（第一页），没有 page/cursor；多关键词轮换是必须的。

---

## Agent 抽取（DSH / Codex）

`extract --prepare` 生成的任务包含：

- `title`、`description`、`published_at`、`comments`、`ocr_text`、`images`、`source_url`；
- `schema` 和 `instructions`。

把 `tasks.json` 交给 DSH/Codex，让它按 `prompts/extract.md` 输出：

```json
{
  "post_id": "...",
  "is_job_post": true,
  "company": "字节跳动",
  "position": "AI产品经理实习生",
  "email": ["hr@example.com"],
  "contact": "",
  "location": "北京",
  "employment_type": "实习",
  "salary": "500/天",
  "still_hiring": "在招",
  "status_evidence": "作者 11-02 回复：没删就是在招",
  "confidence": 0.9,
  "reason": "有具体 JD、邮箱和作者回复"
}
```

**不需要额外 API Key**：Agent 自己就是抽取模型。若要用 API 批量抽取，也可以自己接，但本项目不绑定。

---

## 去重规则

1. 有邮箱：`email:<first-email>`；
2. 无邮箱但有公司+岗位：`role:<company>|<position>`；
3. 都没有：`note:<post_id>`。

导出时同一 `dedup_key` 只保留一条，优先“有邮箱 → 更新 → 置信度高”。

---

## 在招判断

状态只有两个：**在招 / 无法确认**。

1. 标题/正文有“已招到 / 已截止 / 不收了 / 简历已筛完 / 先不投” → `closed=true`，状态 `无法确认`；
2. 作者最新回复有“还在 / 没删就还在 / 招 / 可以投 / 有” → `在招`；
3. 其他 → `无法确认`。

状态必须带 `status_evidence`（原话 + 日期），否则不要写“在招”。`closed=true` 的帖子默认不进入导出。

## 过滤规则

- 评论区出现 `购买 / 同款表格 / 买同款 / 付费 / 岗位表` → 判为引流，排除；
- 标题/正文是“收到终面/offer，请问这个岗位怎么样/职业发展/有没有同岗” → 求助帖，排除；
- 笔记没有邮箱，且作者主页简介含 `岗位表/表格/购买/群/每日更新/校招/内推`，且其他笔记出现 >2 家公司 → 判为多公司引流，排除；
- 有内推码但无邮箱 → 保留，写 `referral_code`；
- 评论/图片 OCR 有邮箱而正文没有 → 保留，写 `comment_email` / `email_source`。

---

## OCR（可选）

> 不加 `--ocr` 时，HTML 封面直接引用小红书 CDN 签名 URL，可能过期；加 `--ocr` 会把图片下载到本地 `images/<post_id>/`。

```bash
product-intern-daily fetch candidates.json --out details --ocr
```

- macOS：`sips` 转 JPEG + `ocrmac`（Apple Vision）OCR；
- `--ocr` 需要 `ocrmac`，没装会报错并提示安装；**不会静默跳过**；
- OCR **全部图片**，默认原图 + 180° 旋转 + 水平/垂直翻转，避免翻转图漏邮箱；
- 评论图片有 `pictures/imageList/images` 字段时也会 OCR；
- **纯图片置顶评论需要 patched `xiaohongshu-mcp`**：原版 `Comment` 结构体没有图片字段。补丁见 [`patches/xiaohongshu-mcp-comment-pictures.patch`](patches/xiaohongshu-mcp-comment-pictures.patch)，说明见 [`docs/XHS_MCP_PATCH.md`](docs/XHS_MCP_PATCH.md)；
- 图片只本地保存，不上传。

---

## 调度

```bash
# 每天 9:00 搜索 + 拉详情（示例，macOS launchd/cron 均可）
0 9 * * * cd /path/to/product-intern-daily && \
  python run.py search --keyword "AI产品实习" --sort 最新 --publish-time 一天内 --out candidates.json && \
  python run.py fetch candidates.json --out details --ocr
```

抽取步骤需要 Agent 参与；可以用 DSH/Codex 的定时任务，或自己接 API。**OpenClaw 不是必需。**

---

## 数据

默认 SQLite：`./data/jobs.sqlite3`。

表：

- `jobs`：岗位 + 证据 + 原始详情；
- `seen`：已抓过的 note；
- `runs`：每次命令的运行记录。

---

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

测试不联网，使用合成 fixture。

---

## 风险与合规

- 仅用于个人求职研究；遵守小红书用户协议；
- 使用**小号**采集，控制频率（2–5 秒/次）；出现验证码/登录失效立即停止；
- Cookie 只在本地，不进入仓库；
- 邮箱/微信属于个人信息，投递前核实对方身份；
- 本项目不是小红书官方产品，与小红书无隶属关系。

---

## License

MIT。依赖 [`xiaohongshu-mcp`](https://github.com/xpzouying/xiaohongshu-mcp)（Apache-2.0），本项目不包含其代码。

---

## 借鉴 Swelist / SimplifyJobs 的地方

- **一条岗位一条稳定记录**：`jobs.json` 作为机器可读数据源，CSV/HTML 只是视图；方便做站点、RSS、订阅。
- **状态 + 最后验证时间**：`still_hiring`、`status_evidence`、`extracted_at`；后续可加 `last_verified_at` 与“超过 N 天自动降级为无法确认”。
- **公开数据 + 贡献入口**：README 表格 + `jobs.json`；外部用户用 Issue 表单提交帖子 URL，维护者跑一遍管线后合并。
- **日/周摘要**：Swelist 用“daily/weekly + 邮箱”做订阅；我们可以用 `jobs.json` 生成邮件/RSS/飞书摘要，不依赖付费服务。
- **不要把 Cookie 放进公开 CI**：小红书登录态不能进 GitHub Actions；用本地 cron/自托管 runner 更新，公开仓库只放脱敏后的 `jobs.json`。

当前已支持：

```bash
product-intern-daily export --format csv,html,json --out exports
# exports/jobs.json 可直接给静态站点/RSS/邮件脚本用
```

---

## 开源工程结构

```text
product-intern-daily/
├── src/product_intern_daily/        # CLI + 数据层 + 抽取 + OCR + 导出
├── scripts/
│   ├── validate_data.py      # 校验 jobs.json
│   ├── generate_readme.py    # 生成 docs/JOBS.md
│   └── build_site.py         # 生成 docs/index.html（GitHub Pages）
├── schema/job.schema.json
├── data/jobs.example.json    # 脱敏示例；真实 jobs.json 不提交
├── docs/                     # 架构/数据模型/岗位列表/Pages
├── patches/                  # xiaohongshu-mcp 评论图片补丁
├── .github/ISSUE_TEMPLATE/   # 新增/修正/批量失效
├── .github/workflows/        # CI + Pages
└── tests/                    # 24 个离线测试
```

常用命令：

```bash
make test
make validate
make site
make readme
```

- 发布数据：`product-intern-daily export --format json --out exports` → `exports/jobs.json`
- 生成页面：`python scripts/build_site.py exports/jobs.json docs/index.html`
- 生成岗位列表：`python scripts/generate_readme.py exports/jobs.json docs/JOBS.md`

贡献流程：Issue 模板提交原帖 → 维护者本地跑管线 → 校验 → 合并 → 重新生成 `docs/`。

**不要把 Cookie 放进 GitHub Actions**。公开仓库只放代码和脱敏示例；真实数据本地生成。

---

## 每日发布

自动化与 GitHub 更新方案：[docs/SCHEDULE.md](docs/SCHEDULE.md)。 / 订阅

维护者本地跑完管线后：

```bash
# 生成公开静态页、RSS、岗位列表
python scripts/build_site.py exports/jobs.json docs/index.html
python scripts/build_feed.py exports/jobs.json docs/feed.xml "https://xuyixiao0224.github.io/product-intern-daily/"
python scripts/generate_readme.py exports/jobs.json docs/JOBS.md

# 渲染每日邮件（默认 dry-run，不发送）
python scripts/send_digest.py --jobs exports/jobs.json --since 1d --dry-run

# 发送：用事务邮件服务/Newsletter，不用私人邮箱
# 见 docs/SUBSCRIBE.md（Buttondown / Resend / Listmonk）
```

- 消费者：打开 GitHub Pages / RSS，零登录。
- Pages 只部署已提交的 `docs/`；维护者本地生成 `docs/index.html`、`docs/feed.xml`、`docs/JOBS.md` 后再提交，CI 不用 Cookie、不覆盖真实数据。
- 维护者：本地跑 MCP + OCR + 管线，提交 `docs/` 静态产物；`data/jobs.json` 不公开。
- 邮件：Buttondown（推荐起步）/ Resend / 自托管 Listmonk；**不要用私人 Gmail/QQ 群发**。

---

## 如果这个项目帮你省了时间

- 点个 **Star**，让更多找产品实习的人看到；
- 订阅 [RSS](docs/feed.xml) 或 [邮件](docs/subscribe.html)；
- 发现好帖子/错误信息，用 [Issue 模板](.github/ISSUE_TEMPLATE/new-job.yml) 提交；
- 只想自己跑：clone + 自己的 `xiaohongshu-mcp` + 自己的 Cookie，不需要把账号给我们。

## Roadmap

- [x] 产品实习字段：公司/岗位/Base/邮箱/内推码/状态/证据
- [x] 多图 OCR + 翻转 + 评论邮箱 + 置顶评论
- [x] 静态站 + RSS + 邮件 dry-run
- [x] Issue 模板 + CI + Pages
- [ ] 300–500 条种子数据 + 人工复核
- [ ] 每周产品实习报告
- [ ] 第二数据源（公众号/官网/牛客）
- [ ] 订阅者增长到 1000 后换 Resend/Listmonk

---

## “自托管 CLI”是什么意思

它不是另一个网站，也不是 SaaS，而是**装在你本机的一个命令行工具** `product-intern-daily`：

- 负责确定性的活：搜索、拉详情、OCR、写 SQLite、导入抽取结果、导出 JSON/CSV/HTML；
- 不负责“理解帖子”：抽取由 Codex/DSH 这个 Agent 做；
- Codex/DSH 通过 shell 调它，所以叫“Agent 的手”；
- 普通读者不需要装它：他们只看网页/RSS/邮件；
- 自托管用户用自己的 MCP、自己的小红书账号、自己的 Cookie，数据不经过我们。

```text
Codex / DSH（大脑）
   └── 调 product-intern-daily（手）
          ├── search / fetch / ocr
          ├── SQLite / jobs.json
          └── export → 网页 / RSS / 邮件
```

---

## 向导式开始（借鉴 Swelist）

```bash
python run.py init
```

一次只问一个问题：

```text
方向（产品/AI产品/产品运营） [产品]:
时间范围（一天内/一周内/半年内） [一周内]:
启用本地 OCR（yes/no） [yes]:
```

生成：

- `run.sh`：可直接执行的搜索 → 详情 → 抽取任务；
- `config.yaml`：关键词/时间/OCR 配置；
- `.env.example`：邮件服务占位，不含任何真实 Key。

非交互：

```bash
python run.py init --yes --dir my-job
```

## Evaluation

- 对比方法与指标：[docs/BENCHMARK.md](docs/BENCHMARK.md)（pending 真实 LLM + 同批语料）

## Inspiration

- [Swelist](https://swelist.com/)：one-question-at-a-time onboarding、daily/weekly 邮件订阅；
- [SimplifyJobs](https://github.com/SimplifyJobs/Summer2027-Internships)：公开岗位列表、Issue 贡献、README/站点生成。

只借鉴交互与数据组织方式，不复制品牌、文案或数据；与上述项目无隶属关系。
