# 架构

```text
xiaohongshu-mcp (browser + login)
        │  HTTP JSON-RPC :18060
        ▼
product-intern-daily CLI
  search → fetch → extract --prepare → Agent → extract --import → export
        │
        ├── SQLite: jobs / seen / runs
        ├── 本地 OCR: sips + ocrmac (Apple Vision)
        └── jobs.json / CSV / HTML
```

## 分层

- **采集层**：`xiaohongshu-mcp` 负责浏览器、登录、反爬；本项目不碰 Cookie。
- **数据层**：`store.py` SQLite；`jobs.json` 是公开数据源。
- **抽取层**：`extract.py` 准备任务；Codex/Claude Code 输出严格 JSON；`--import` 校验入库。
- **展示层**：`export.py` / `build_site.py` / `generate_readme.py`。

## 为什么不做全自动 LLM API

- 默认让当前 Agent 抽取，避免 API Key 和费用；
- 需要批量时，用户可自己接 API，但项目不绑定供应商。

## 评论图片

原版 `xiaohongshu-mcp` 的 `Comment` 结构体没有图片字段。补丁：

- `patches/xiaohongshu-mcp-comment-pictures.patch`
- `docs/XHS_MCP_PATCH.md`

打完补丁后 `get_feed_detail` 会返回 `pictures`，本项目再下载 + 多方向 OCR。
