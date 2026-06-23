from __future__ import annotations

from datetime import datetime

from app.services.time_range import resolve_time_range_text


NOW = datetime.fromisoformat("2026-06-23T16:30:00+08:00")


def test_explicit_day_to_today_beats_today_keyword() -> None:
    result = resolve_time_range_text("帮我生成15号到今天的工作日志", NOW)

    assert result is not None
    assert result.start_at.isoformat() == "2026-06-15T00:00:00+08:00"
    assert result.end_at == NOW


def test_day_to_present_alias_is_supported() -> None:
    result = resolve_time_range_text("从15号至今", NOW)

    assert result is not None
    assert result.start_at.date().isoformat() == "2026-06-15"
    assert result.end_at == NOW


def test_day_without_month_uses_nearest_non_future_date() -> None:
    now = datetime.fromisoformat("2026-06-02T10:00:00+08:00")
    result = resolve_time_range_text("15号到今天", now)

    assert result is not None
    assert result.start_at.date().isoformat() == "2026-05-15"


def test_cross_month_range_inherits_and_advances_month() -> None:
    result = resolve_time_range_text("5月28日至6月3日", NOW)

    assert result is not None
    assert result.start_at.date().isoformat() == "2026-05-28"
    assert result.end_at.date().isoformat() == "2026-06-03"


def test_range_end_without_month_advances_when_needed() -> None:
    now = datetime.fromisoformat("2026-07-10T10:00:00+08:00")
    result = resolve_time_range_text("6月28日至3日", now)

    assert result is not None
    assert result.end_at.date().isoformat() == "2026-07-03"


def test_last_week_is_a_complete_calendar_week() -> None:
    result = resolve_time_range_text("生成上周工作日志", NOW)

    assert result is not None
    assert result.start_at.date().isoformat() == "2026-06-15"
    assert result.end_at.date().isoformat() == "2026-06-21"


def test_weekday_range_is_more_specific_than_named_week() -> None:
    result = resolve_time_range_text("上周三到本周一", NOW)

    assert result is not None
    assert result.start_at.date().isoformat() == "2026-06-17"
    assert result.end_at.date().isoformat() == "2026-06-22"


def test_recent_days_is_a_rolling_calendar_range() -> None:
    result = resolve_time_range_text("最近3天", NOW)

    assert result is not None
    assert result.start_at.date().isoformat() == "2026-06-21"
    assert result.end_at == NOW


def test_relative_year_month_range() -> None:
    result = resolve_time_range_text("去年12月至今年1月", NOW)

    assert result is not None
    assert result.start_at.date().isoformat() == "2025-12-01"
    assert result.end_at.date().isoformat() == "2026-01-31"


def test_future_range_is_rejected() -> None:
    result = resolve_time_range_text("6月24日到6月25日", NOW)

    assert result is None
