# 让 xiaohongshu-mcp 返回评论图片

## 问题

`xiaohongshu-mcp` 的 `get_feed_detail` 从 `window.__INITIAL_STATE__.note.noteDetailMap` 取评论，但 `Comment` 结构体没有图片字段：

```go
type Comment struct {
    ID, Content, ...
    SubComments []Comment
    ShowTags []string
}
```

纯图片置顶评论的 `content` 为空，图片字段被 Go 反序列化丢弃，所以外层拿不到图。

## 补丁

`patches/xiaohongshu-mcp-comment-pictures.patch` 给 `Comment` 加：

```go
Pictures  json.RawMessage `json:"pictures,omitempty"`
ImageList json.RawMessage `json:"imageList,omitempty"`
Images    json.RawMessage `json:"images,omitempty"`
```

用 `RawMessage` 是为了兼容不同端/版本的字段结构，字段不存在也不会让整条 comment 解析失败。

## 构建

```bash
git clone https://github.com/xpzouying/xiaohongshu-mcp.git
cd xiaohongshu-mcp
git apply /path/to/xiaohongshu-mcp-comment-pictures.patch
GOOS=darwin GOARCH=arm64 go build -o xiaohongshu-mcp .
```

## 验证

对 `6ae6e60a000000001802d294` 调 `get_feed_detail`，置顶评论会出现：

```json
{
  "content": "",
  "showTags": ["user_top"],
  "pictures": [{"urlDefault": "http://.../comment/....webp"}]
}
```

下载 `urlDefault`，本地 Apple Vision OCR（原图 + 180° + 水平/垂直翻转），得到：

```text
hr@example.com
```

## 建议

这个改动很小，建议给上游提 PR。注意评论图片可能是长图/翻转图/带贴纸，OCR 必须多方向跑。


---

# 搜索分页：从 20 条到最多 100 条

## 问题

`search_feeds` 原来只读第一页 `__INITIAL_STATE__.search.feeds`，约 20 条；没有 page/cursor 参数。

## 实现

- 监听 CDP `NetworkRequestWillBeSent` 的 `/api/sns/web/v2/search/notes`；
- 请求体里 `page=1…6`、`page_size=20`；
- 滚动搜索结果根节点，等待对应页响应完成；
- 合并多页、按 note id 去重；
- `limit` 默认 20、最大 100；`max_pages` 默认 8、最大 10；
- 页间随机延迟；遇到 461/471/401/403 停止。

补丁：`patches/xiaohongshu-mcp-search-pagination.patch`

## 构建

```bash
git apply patches/xiaohongshu-mcp-search-pagination.patch
GOCACHE=/tmp/gocache GOMODCACHE=/tmp/gomodcache go build -o xiaohongshu-mcp .
```

## 验证

```bash
# 客户端必须把 limit 传给 MCP，而不是只做本地截断
python scripts/collect_seed.py --mode daily --target 300 --per-keyword 100
```

实测（2026-11-04）：产品实习 100、产品继任 86、互联网产品 74；未遇到 461/验证码。
