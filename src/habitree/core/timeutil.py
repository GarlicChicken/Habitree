"""시각: 저장은 UTC, 보여 줄 때는 이 컴퓨터의 시간대. / Store UTC, display local time."""
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


def now_iso():
    """저장용 UTC 시각 문자열. / UTC timestamp for storage."""
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def local_date():
    """규칙 기록에 남기는 날짜(이 컴퓨터 시간대 기준). / Local calendar date."""
    return now_utc().astimezone().strftime("%Y-%m-%d")


def show(s):
    """UTC 문자열을 이 컴퓨터 시간대로 보여 준다. / Display a UTC string in local time."""
    dt = parse_iso(s)
    if dt is None:
        return s or ""
    local = dt.astimezone()
    return local.strftime("%Y-%m-%d %H:%M ") + (local.tzname() or "")


def seconds_since(s):
    dt = parse_iso(s)
    return None if dt is None else (now_utc() - dt).total_seconds()
