"""
health_score.py — Device health score and PM-status calculation.

Health score (0-100, higher = healthier):
  100
  - risk_penalty   (risk_score × 0.3, capped at 30)
  - status_penalty (online=0, warning=15, critical=30, offline=50)
  - pm_penalty     (due_soon=5; overdue: min(25, 5 + days_overdue × 2))
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def compute_pm_status(
    next_pm_date: Optional[str],
    now: Optional[datetime] = None,
) -> str:
    """
    Return 'overdue', 'due_soon', or 'ok' based on next_pm_date.

    due_soon threshold: within 7 days.
    """
    if not next_pm_date:
        return "ok"
    if now is None:
        now = datetime.now(timezone.utc)
    try:
        nxt = datetime.fromisoformat(next_pm_date.replace("Z", "+00:00"))
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
        delta_days = (nxt - now).days
        if delta_days < 0:
            return "overdue"
        if delta_days <= 7:
            return "due_soon"
        return "ok"
    except (ValueError, TypeError):
        return "ok"


def compute_health_score(
    risk_score: int,
    status: str,
    pm_status: str,
    next_pm_date: Optional[str] = None,
    now: Optional[datetime] = None,
) -> int:
    """
    Composite device health score (0-100, higher = healthier).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    score = 100.0

    # Risk penalty: 0–30 pts
    score -= min(30.0, float(risk_score) * 0.3)

    # Operational-status penalty
    _status_penalty = {"online": 0, "warning": 15, "critical": 30, "offline": 50}
    score -= _status_penalty.get(status, 0)

    # PM penalty
    if pm_status == "due_soon":
        score -= 5.0
    elif pm_status == "overdue" and next_pm_date:
        try:
            nxt = datetime.fromisoformat(next_pm_date.replace("Z", "+00:00"))
            if nxt.tzinfo is None:
                nxt = nxt.replace(tzinfo=timezone.utc)
            days_overdue = max(0, (now - nxt).days)
            score -= min(25.0, 5.0 + days_overdue * 2.0)
        except (ValueError, TypeError):
            score -= 10.0

    return max(0, min(100, round(score)))
