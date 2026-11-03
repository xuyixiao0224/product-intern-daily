"""Minimal HTTP client for a locally running xiaohongshu-mcp.

This module deliberately has no browser/login logic: xiaohongshu-mcp owns the
browser session and cookies. We only speak JSON-RPC over HTTP.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .models import Candidate, to_int


class MCPError(RuntimeError):
    pass


class MCPClient:
    def __init__(self, url: str = "http://127.0.0.1:18060/mcp", timeout: int = 120):
        self.url = url
        self.timeout = timeout
        self._id = 0

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.URLError as exc:
            raise MCPError(f"cannot reach xiaohongshu-mcp at {self.url}: {exc}") from exc
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise MCPError(f"non-JSON response from MCP: {body[:200]}") from exc
        if "error" in data:
            raise MCPError(f"MCP error: {data['error']}")
        return data

    def call(self, name: str, arguments: dict | None = None, timeout: int | None = None) -> str:
        self._id += 1
        old = self.timeout
        if timeout:
            self.timeout = timeout
        try:
            data = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments or {}},
                }
            )
        finally:
            self.timeout = old
        result = data.get("result") or {}
        text = "\n".join(
            part.get("text", "") for part in result.get("content", []) if part.get("type") == "text"
        )
        if result.get("isError"):
            raise MCPError(text or f"{name} failed")
        return text

    def initialize(self) -> dict:
        self._id += 1
        data = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "product-intern-daily", "version": "0.1.0"},
                },
            }
        )
        return data.get("result") or {}

    def check_login(self) -> str:
        return self.call("check_login_status", {}).strip()

    def search(
        self,
        keyword: str,
        *,
        limit: int = 20,
        sort_by: str = "最新",
        publish_time: str = "一周内",
        note_type: str = "图文",
        timeout: int = 120,
    ) -> list[Candidate]:
        filters = {
            "sort_by": sort_by,
            "publish_time": publish_time,
            "note_type": note_type,
        }
        text = self.call("search_feeds", {"keyword": keyword, "filters": filters}, timeout=timeout)
        return parse_search_response(text, keyword=keyword, limit=limit)

    def detail(self, post_id: str, token: str, *, all_comments: bool = False, timeout: int = 120) -> dict:
        args: dict[str, Any] = {"feed_id": post_id, "xsec_token": token}
        if all_comments:
            args.update({"load_all_comments": True, "limit": 50, "click_more_replies": True})
        text = self.call("get_feed_detail", args, timeout=timeout)
        return json.loads(text)

    def user_profile(self, user_id: str, token: str, *, limit: int = 20, timeout: int = 120) -> list[dict]:
        text = self.call("user_profile", {"user_id": user_id, "xsec_token": token}, timeout=timeout)
        data = json.loads(text)
        feeds = data.get("feeds", []) if isinstance(data, dict) else []
        out = []
        for f in feeds[:limit]:
            card = f.get("noteCard") or {}
            out.append({"post_id": f.get("id", ""), "title": card.get("displayTitle", ""), "token": f.get("xsecToken", "")})
        return out

    def list_feeds(self, *, timeout: int = 120) -> list[dict]:
        text = self.call("list_feeds", {}, timeout=timeout)
        return json.loads(text).get("feeds", [])


def parse_search_response(text: str, keyword: str = "", limit: int = 20) -> list[Candidate]:
    """Parse the JSON text returned by xiaohongshu-mcp.search_feeds."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MCPError(f"search_feeds returned non-JSON: {text[:200]}") from exc
    feeds = data.get("feeds", []) if isinstance(data, dict) else data
    out: list[Candidate] = []
    for feed in feeds:
        post_id = feed.get("id", "")
        if not post_id:
            continue
        card = feed.get("noteCard") or {}
        user = card.get("user") or {}
        info = card.get("interactInfo") or {}
        out.append(
            Candidate(
                post_id=post_id,
                token=feed.get("xsecToken", ""),
                title=card.get("displayTitle", "") or "",
                author=user.get("nickname", "") or user.get("nickName", "") or "",
                likes=to_int(info.get("likedCount")),
                comments=to_int(info.get("commentCount")),
                keyword=keyword,
            )
        )
        if len(out) >= limit:
            break
    return out
