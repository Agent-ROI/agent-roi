"""Tests for budget tracking: period boundaries and spend-vs-limit status."""

from __future__ import annotations

from datetime import datetime, timezone

from agent_roi.core.config import BudgetConfig, Config
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.service import Service
from agent_roi.core.timeframe import period_start


def test_period_start_day_week_month():
    # Wednesday 2026-06-10 12:34 UTC
    now = datetime(2026, 6, 10, 12, 34, tzinfo=timezone.utc)
    assert period_start("day", now=now) == datetime(2026, 6, 10, tzinfo=timezone.utc)
    # Monday of that week is 2026-06-08
    assert period_start("week", now=now) == datetime(2026, 6, 8, tzinfo=timezone.utc)
    assert period_start("month", now=now) == datetime(2026, 6, 1, tzinfo=timezone.utc)


def _service(tmp_path, budget: BudgetConfig) -> Service:
    config = Config(budget=budget, db_path=tmp_path / "roi.db")
    return Service(config=config)


def _interaction(when: datetime) -> Interaction:
    # claude-opus-4-8: input $15/1M -> 1M input tokens = $15.00
    return Interaction(
        id=f"x:{when.isoformat()}",
        tool=Tool.CLAUDE_CODE,
        session_id="s1",
        timestamp=when,
        model="claude-opus-4-8",
        input_tokens=1_000_000,
    )


def test_budget_status_flags_over_and_reports_spend(tmp_path):
    svc = _service(tmp_path, BudgetConfig(daily_usd=10.0, monthly_usd=100.0))
    now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    # Two interactions today = $30 of spend.
    svc.db.upsert_many([_interaction(now), _interaction(now.replace(hour=9))])

    status = svc.budget_status(now=now)
    by_period = {p.period: p for p in status.periods}

    day = by_period["day"]
    assert round(day.spent_usd, 2) == 30.00
    assert day.limit_usd == 10.0
    assert day.over is True  # $30 > $10
    assert day.pct == 300.0
    assert day.remaining_usd == 10.0 - 30.0

    month = by_period["month"]
    assert round(month.spent_usd, 2) == 30.00
    assert month.over is False  # $30 < $100

    # week has no configured limit
    week = by_period["week"]
    assert week.limit_usd is None
    assert week.pct is None
    assert week.over is False

    assert status.any_over is True


def test_budget_status_excludes_prior_periods(tmp_path):
    svc = _service(tmp_path, BudgetConfig(daily_usd=10.0))
    now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    # Spend from yesterday should not count toward today's budget.
    svc.db.upsert_many([_interaction(now.replace(day=9))])

    day = next(p for p in svc.budget_status(now=now).periods if p.period == "day")
    assert day.spent_usd == 0.0
    assert day.over is False


def test_update_config_persists_budget(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setenv("AGENT_ROI_CONFIG", str(cfg_path))
    svc = _service(tmp_path, BudgetConfig())

    svc.update_config(budget={"daily_usd": 5.0, "monthly_usd": 120.0})

    reloaded = Config.load()
    assert reloaded.budget.daily_usd == 5.0
    assert reloaded.budget.monthly_usd == 120.0
    assert reloaded.budget.weekly_usd is None
