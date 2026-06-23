from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True, slots=True)
class ResolvedTimeRange:
    start_at: datetime
    end_at: datetime
    label: str
    source_text: str


_NUMBER_TOKEN = r"(?:\d{1,4}|[一二三四五六七八九十两]+)"
_DAY_DATE_TOKEN = rf"(?:(?:\d{{4}}年|今年|去年))?(?:{_NUMBER_TOKEN}月)?{_NUMBER_TOKEN}[日号]"
_MONTH_TOKEN = rf"(?:(?:\d{{4}}年|今年|去年))?{_NUMBER_TOKEN}月"
_RELATIVE_DATE_TOKEN = r"今天|今日|现在|目前|昨天|前天|本周[一二三四五六日天]|上周[一二三四五六日天]"
_RANGE_SEPARATOR = r"(?:到|至|~|～|—|－|-)"

_CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_WEEKDAY_OFFSETS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}


def resolve_time_range(texts: list[str], now: datetime) -> ResolvedTimeRange | None:
    current = now.astimezone()
    for text_value in texts:
        resolved = resolve_time_range_text(text_value, current)
        if resolved is not None:
            return resolved
    return None


def resolve_time_range_text(text_value: str, now: datetime) -> ResolvedTimeRange | None:
    normalized = re.sub(r"\s+", "", text_value.strip().lower())
    normalized = re.sub(r"至今(?!年)", "至今天", normalized)
    if not normalized:
        return None

    explicit_days = re.search(
        rf"(?P<start>{_DAY_DATE_TOKEN}|{_RELATIVE_DATE_TOKEN}){_RANGE_SEPARATOR}(?P<end>{_DAY_DATE_TOKEN}|{_RELATIVE_DATE_TOKEN})",
        normalized,
    )
    if explicit_days:
        return _resolve_day_range(explicit_days.group("start"), explicit_days.group("end"), now, text_value)

    explicit_months = re.search(
        rf"(?P<start>{_MONTH_TOKEN}){_RANGE_SEPARATOR}(?P<end>{_MONTH_TOKEN}|今天|今日|现在|目前)",
        normalized,
    )
    if explicit_months:
        return _resolve_month_range(explicit_months.group("start"), explicit_months.group("end"), now, text_value)

    rolling = re.search(rf"(?:最近|近|过去)(?P<count>{_NUMBER_TOKEN})(?P<unit>天|日|周|个月|月)", normalized)
    if rolling:
        count = _parse_number(rolling.group("count"))
        if count and count > 0:
            if rolling.group("unit") in {"天", "日"}:
                start_day = now.date() - timedelta(days=count - 1)
            elif rolling.group("unit") == "周":
                start_day = now.date() - timedelta(days=count * 7 - 1)
            else:
                start_day = _shift_months(now.date(), -count)
            return _build_range(start_day, now, now, text_value, f"最近 {count}{rolling.group('unit')}")

    single_date = re.search(rf"(?P<value>{_DAY_DATE_TOKEN}|{_RELATIVE_DATE_TOKEN})", normalized)
    if single_date:
        resolved_date = _resolve_date_token(single_date.group("value"), now, prefer_past=True)
        if resolved_date is not None and resolved_date <= now.date():
            return _build_range(resolved_date, _end_of_day(resolved_date, now), now, text_value, resolved_date.isoformat())

    named = _resolve_named_period(normalized, now, text_value)
    if named is not None:
        return named

    return None


def resolve_named_kind(kind: str, now: datetime, source_text: str = "") -> ResolvedTimeRange | None:
    aliases = {
        "today": "今天",
        "yesterday": "昨天",
        "this_week": "本周",
        "last_week": "上周",
        "this_month": "本月",
        "last_month": "上个月",
    }
    text_value = aliases.get(kind)
    return _resolve_named_period(text_value, now.astimezone(), source_text or text_value) if text_value else None


def _resolve_named_period(normalized: str, now: datetime, source_text: str) -> ResolvedTimeRange | None:
    current_day = now.date()
    if "本周" in normalized or "这周" in normalized:
        start = current_day - timedelta(days=current_day.weekday())
        return _build_range(start, now, now, source_text, "本周截至今天")
    if "上周" in normalized:
        this_monday = current_day - timedelta(days=current_day.weekday())
        start = this_monday - timedelta(days=7)
        end = this_monday - timedelta(days=1)
        return _build_range(start, _end_of_day(end, now), now, source_text, "上周")
    if "本月" in normalized or "这个月" in normalized:
        start = current_day.replace(day=1)
        return _build_range(start, now, now, source_text, "本月截至今天")
    if "上个月" in normalized or "上月" in normalized:
        current_month = current_day.replace(day=1)
        end = current_month - timedelta(days=1)
        start = end.replace(day=1)
        return _build_range(start, _end_of_day(end, now), now, source_text, "上个月")
    if "前天" in normalized:
        day_value = current_day - timedelta(days=2)
        return _build_range(day_value, _end_of_day(day_value, now), now, source_text, "前天")
    if "昨天" in normalized:
        day_value = current_day - timedelta(days=1)
        return _build_range(day_value, _end_of_day(day_value, now), now, source_text, "昨天")
    if "今天" in normalized or "今日" in normalized or "现在" in normalized or "目前" in normalized:
        return _build_range(current_day, now, now, source_text, "今天")
    return None


def _resolve_day_range(start_token: str, end_token: str, now: datetime, source_text: str) -> ResolvedTimeRange | None:
    start = _resolve_date_token(start_token, now, prefer_past=True)
    if start is None:
        return None
    end = _resolve_date_token(end_token, now, inherited=start, prefer_past=False)
    if end is None:
        return None
    if end < start and not _token_has_month_or_year(end_token):
        end = _shift_months(end, 1)
    if start > now.date() or end > now.date() or end < start:
        return None
    end_at = now if end == now.date() and end_token in {"今天", "今日", "现在", "目前"} else _end_of_day(end, now)
    return _build_range(start, end_at, now, source_text, f"{start.isoformat()} 至 {end.isoformat()}")


def _resolve_month_range(start_token: str, end_token: str, now: datetime, source_text: str) -> ResolvedTimeRange | None:
    start_month = _resolve_month_token(start_token, now, prefer_past=True)
    if start_month is None:
        return None
    if end_token in {"今天", "今日", "现在", "目前"}:
        end_at = now
    else:
        end_month = _resolve_month_token(end_token, now, inherited=start_month, prefer_past=False)
        if end_month is None:
            return None
        if end_month < start_month and not _token_has_year(end_token):
            end_month = end_month.replace(year=end_month.year + 1)
        end_day = date(end_month.year, end_month.month, calendar.monthrange(end_month.year, end_month.month)[1])
        if end_day > now.date():
            if end_month.year == now.year and end_month.month == now.month:
                end_at = now
            else:
                return None
        else:
            end_at = _end_of_day(end_day, now)
    if start_month > end_at.date() or start_month > now.date():
        return None
    return _build_range(start_month, end_at, now, source_text, f"{start_month:%Y-%m} 至 {end_at:%Y-%m}")


def _resolve_date_token(
    token: str,
    now: datetime,
    *,
    inherited: date | None = None,
    prefer_past: bool,
) -> date | None:
    if token in {"今天", "今日", "现在", "目前"}:
        return now.date()
    if token == "昨天":
        return now.date() - timedelta(days=1)
    if token == "前天":
        return now.date() - timedelta(days=2)
    weekday = re.fullmatch(r"(?P<week>本周|上周)(?P<day>[一二三四五六日天])", token)
    if weekday:
        monday = now.date() - timedelta(days=now.date().weekday())
        if weekday.group("week") == "上周":
            monday -= timedelta(days=7)
        return monday + timedelta(days=_WEEKDAY_OFFSETS[weekday.group("day")])

    match = re.fullmatch(
        rf"(?:(?P<year>\d{{4}})年|(?P<relative_year>今年|去年))?(?:(?P<month>{_NUMBER_TOKEN})月)?(?P<day>{_NUMBER_TOKEN})[日号]",
        token,
    )
    if not match:
        return None
    day_value = _parse_number(match.group("day"))
    month_value = _parse_number(match.group("month")) if match.group("month") else inherited.month if inherited else now.month
    if not day_value or not month_value:
        return None
    year_value = _resolve_year(match.group("year"), match.group("relative_year"), now.year)
    if not match.group("year") and not match.group("relative_year") and inherited:
        year_value = inherited.year
    try:
        result = date(year_value, month_value, day_value)
    except ValueError:
        return None
    if prefer_past and not _token_has_month_or_year(token) and result > now.date():
        result = _shift_months(result, -1)
    elif prefer_past and not _token_has_year(token) and month_value > now.month and result > now.date():
        result = result.replace(year=result.year - 1)
    return result


def _resolve_month_token(
    token: str,
    now: datetime,
    *,
    inherited: date | None = None,
    prefer_past: bool,
) -> date | None:
    match = re.fullmatch(
        rf"(?:(?P<year>\d{{4}})年|(?P<relative_year>今年|去年))?(?P<month>{_NUMBER_TOKEN})月",
        token,
    )
    if not match:
        return None
    month_value = _parse_number(match.group("month"))
    if not month_value:
        return None
    year_value = _resolve_year(match.group("year"), match.group("relative_year"), now.year)
    if not match.group("year") and not match.group("relative_year") and inherited:
        year_value = inherited.year
    try:
        result = date(year_value, month_value, 1)
    except ValueError:
        return None
    if prefer_past and not _token_has_year(token) and result > now.date().replace(day=1):
        result = result.replace(year=result.year - 1)
    return result


def _resolve_year(year: str | None, relative_year: str | None, current_year: int) -> int:
    if year:
        return int(year)
    if relative_year == "去年":
        return current_year - 1
    return current_year


def _parse_number(value: str | None) -> int | None:
    if not value:
        return None
    if value.isdigit():
        return int(value)
    if value == "十":
        return 10
    if "十" in value:
        tens, ones = value.split("十", 1)
        return (_CHINESE_DIGITS.get(tens, 1) * 10) + _CHINESE_DIGITS.get(ones, 0)
    result = 0
    for char in value:
        if char not in _CHINESE_DIGITS:
            return None
        result = result * 10 + _CHINESE_DIGITS[char]
    return result


def _shift_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _end_of_day(day_value: date, now: datetime) -> datetime:
    if day_value == now.date():
        return now
    return datetime.combine(day_value, time.max, now.tzinfo)


def _build_range(start: date, end_at: datetime, now: datetime, source_text: str, label: str) -> ResolvedTimeRange:
    return ResolvedTimeRange(
        start_at=datetime.combine(start, time.min, now.tzinfo),
        end_at=end_at,
        label=label,
        source_text=source_text,
    )


def _token_has_year(token: str) -> bool:
    return bool(re.search(r"(?:\d{4}年|今年|去年)", token))


def _token_has_month_or_year(token: str) -> bool:
    return "月" in token or _token_has_year(token)
