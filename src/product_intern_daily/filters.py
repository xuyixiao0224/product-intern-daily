"""Post-level filters: lead-gen ads, help-seeking posts, buy-comments, closure."""
from __future__ import annotations

import re

BUY_WORDS = ("购买", "同款表格", "买同款", "付费", "课程", "训练营", "岗位表", "表格")
HELP_RE = re.compile(
    r"收到.{0,8}(终面|面试|offer)|请问.{0,12}(岗位|职业发展|前景|方向)|"
    r"有没有同岗|求建议|该不该|值不值得|怎么样|求问|求助",
    re.I,
)
CLOSE_WORDS = ("先不投", "已招到", "已招满", "不收了", "不收啦", "停止招聘", "招满", "简历已筛完", "已截止")
REFERRAL_RE = re.compile(r"内推码[:：]?\s*([A-Za-z0-9_-]{4,})")


def buy_flags(text: str) -> list[str]:
    return [w for w in BUY_WORDS if w in (text or "")]


def is_help_seeking(text: str) -> bool:
    return bool(HELP_RE.search(text or ""))


def closed_flags(text: str) -> list[str]:
    return [w for w in CLOSE_WORDS if w in (text or "")]


def referral_code(text: str) -> str:
    m = REFERRAL_RE.search(text or "")
    return m.group(1) if m else ""


AGGR_WORDS = ("岗位表", "表格", "购买", "群", "每日更新", "校招", "内推")


def is_aggregator_profile(desc: str, titles: list[str], *, max_companies: int = 2) -> bool:
    """Heuristic: profile advertises a paid job table / many companies."""
    if len(titles) <= max_companies:
        return False
    return any(w in (desc or "") for w in AGGR_WORDS)
