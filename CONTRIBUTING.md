# Contributing

欢迎提交岗位、修正字段、修 bug。请先看 [docs/DATA_MODEL.md](docs/DATA_MODEL.md) 和 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 提交岗位

1. 用 Issue 模板「新增岗位」，贴原帖链接、公司、岗位、Base、邮箱/内推码、状态证据。
2. 维护者用本地管线跑一遍，确认：
   - 不是面经/体验/求助/购买表格帖；
   - 邮箱/内推码来自正文、评论或图片 OCR；
   - 状态有作者回复或正文“二编”证据。
3. 合并到 `data/jobs.json`，再生成 `docs/JOBS.md` / `docs/index.html`。

## 本地开发

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[ocr]"
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/validate_data.py data/jobs.example.json
```

## 隐私红线

- **不要提交** cookies、账号密码、简历、真实邮箱列表、抓取原始 JSON。
- `data/jobs.json` 默认被 `.gitignore`；公开仓库只提交 `data/jobs.example.json` 和脱敏后的示例。
- 图片只本地保存；不要把带个人信息的原图提交到仓库。

## Pull Request

- 一个 PR 只做一件事；
- 附上验证方式（跑了哪条命令、哪个帖子）；
- 不修改 `xiaohongshu-mcp` 的登录/风控逻辑；
- 不加入自动投递、自动私信、批量爬取功能。
