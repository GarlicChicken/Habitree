"""세션 상태: 훅이 작업 중에 본 것을 세션마다 적어 둔다. / Per-session state written by hooks.

- 위치: .habitree/state/sessions/<session_id>.json (git에 올리지 않는다).
- 쓰기는 core/io.py의 원자적 쓰기. 훅은 동시에 여러 개 돌 수 있어(도구를 나란히 부를 때)
  짧은 잠금 파일로 차례를 지킨다. 잠금을 못 잡으면 기다리지 않고 포기한다(작업을 막지 않기 위해).
- 기록은 최근 것만 남기고, 오래된 세션 파일은 세션을 시작할 때 지운다.
- 파일 키는 core/paths.path_key(NFC, 대소문자 무시 파일 시스템이면 casefold)를 쓴다.
- 사용자 요청 원문은 남기지 않는다. 낱말 묶음(토큰)과 길이만 남긴다.
"""
import json
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path

from . import io as hio
from .fast import short
from .paths import case_insensitive, path_key
from .timeutil import now_iso

SESSIONS = "sessions"
ERROR_LOG = "hook-errors.log"
ERROR_LOG_MAX = 256 * 1024
STATE_VERSION = 1


class StateBusy(Exception):
    """잠금을 제때 못 잡음. / Could not take the lock in time."""


def safe_id(session_id):
    """파일 이름으로 쓸 수 있는 세션 id. / Session id safe for a file name."""
    raw = str(session_id or "").strip()
    sid = re.sub(r"[^A-Za-z0-9_.-]", "_", raw)[:80].strip(".")
    if not raw:
        return "default"
    if sid != raw:  # 바꾼 글자가 있으면 원래 id의 해시를 붙여 서로 겹치지 않게 한다
        sid = f"{sid[:60]}-{short(raw, 8)}".lstrip("-.")
    return sid


def sessions_dir(state_dir):
    return Path(state_dir) / SESSIONS


def session_path(state_dir, session_id):
    return sessions_dir(state_dir) / f"{safe_id(session_id)}.json"


def new_state(session_id):
    now = now_iso()
    return {
        "v": STATE_VERSION, "session": str(session_id or ""), "started": now, "updated": now, "source": "",
        "counter": 0,          # 도구 호출 번호(PreToolUse마다 1씩) / tool call counter
        "calls": [],           # 최근 도구 호출 / recent tool calls
        "results": [],         # 최근 도구 결과 / recent tool results
        "pending": {},         # 호출 전에 잰 수정 정보(tool_use_id별) / edit facts measured before the call
        "files": {},           # 이번 세션에 고친 파일 / files changed in this session
        "prompts": [],         # 최근 요청(토큰만) / recent prompts (tokens only)
        "turns": 0, "edits": 0, "edits_since_verify": 0, "edits_since_check": 0, "verify_runs": 0,
        "warned": {},          # 규칙별 경고 횟수와 이미 알린 열쇠 / per-rule warning counts and keys
        "dedup": {},           # 규칙 사이 같은 사건 겹침 막기 / cross-rule duplicate guard
        "off": [],             # 이 세션에서 끈 규칙 / rules muted for this session
        "signals": [],         # 최근 신호 기록 / recent signal log
        "turn": [],            # 이번 답에서 사용자에게 아직 안 보인 알림 / items for the end-of-turn summary
        "delegation": None, "delegations": [],
        "stop": {"check_fp": "", "check_blocks": 0},
        "seen": {},            # 같은 훅이 두 번 설치돼 두 번 불릴 때 막기 / duplicate install guard
        "cache": {},
    }


def _load(path, session_id):
    try:
        data = hio.load_json(path)
    except (ValueError, OSError):
        data = None
    if not isinstance(data, dict) or data.get("v") != STATE_VERSION:
        return new_state(session_id)
    base = new_state(session_id)
    for k, v in base.items():
        data.setdefault(k, v)
    return data


@contextmanager
def _lock(path, timeout=1.5, stale=10.0):
    lock = Path(str(path) + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    fd = None
    while fd is None:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            try:
                if time.time() - lock.stat().st_mtime > stale:
                    os.remove(str(lock))
                    continue
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise StateBusy(str(lock))
            time.sleep(0.02)
    try:
        yield
    finally:
        os.close(fd)
        try:
            os.remove(str(lock))
        except OSError:
            pass


@contextmanager
def session(state_dir, session_id, fresh=False, timeout=1.5):
    """세션 상태를 잠그고 읽어서 넘기고, 블록이 끝나면 저장한다(예외가 나면 저장하지 않음).
    / Lock, load, yield and save the session state (not saved when the block raises)."""
    path = session_path(state_dir, session_id)
    with _lock(path, timeout):
        data = new_state(session_id) if fresh else _load(path, session_id)
        yield data
        data["updated"] = now_iso()
        hio.write_text(path, json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")


def read(state_dir, session_id):
    """잠그지 않고 읽기(보기용). 없으면 None. / Read without locking, for display."""
    path = session_path(state_dir, session_id)
    if not path.is_file():
        return None
    return _load(path, session_id)


def write(state_dir, session_id, data):
    """보기용 명령이 고친 상태를 저장. / Save state changed by a command."""
    with _lock(session_path(state_dir, session_id)):
        data["updated"] = now_iso()
        hio.write_text(session_path(state_dir, session_id),
                       json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")


def latest(state_dir):
    """가장 최근에 바뀐 세션의 id. 없으면 None. / Id of the most recently updated session."""
    folder = sessions_dir(state_dir)
    if not folder.is_dir():
        return None
    best, best_t = None, -1.0
    for p in folder.glob("*.json"):
        try:
            t = p.stat().st_mtime
        except OSError:
            continue
        if t > best_t:
            best, best_t = p.stem, t
    return best


def cleanup(state_dir, days=7):
    """며칠 지난 세션 파일과 남은 잠금 파일을 지운다. / Remove old session files."""
    folder = sessions_dir(state_dir)
    if not folder.is_dir():
        return 0
    limit = time.time() - days * 86400
    removed = 0
    for p in list(folder.iterdir()):
        try:
            if p.suffix in (".json", ".lock") and p.stat().st_mtime < limit:
                p.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def push(data, key, item, limit):
    """목록 끝에 더하고 최근 limit개만 남긴다. / Append and keep the last `limit` items."""
    items = data.setdefault(key, [])
    items.append(item)
    if len(items) > limit:
        del items[:len(items) - limit]
    return items


def file_key(root, path, data=None):
    """세션 상태의 파일 키. 대소문자 판정은 세션 캐시에 둔다. / File key with a cached case probe."""
    ci = None
    if data is not None:
        ci = data.setdefault("cache", {}).get("ci")
        if ci is None:
            ci = case_insensitive(str(Path(root).resolve()))
            data["cache"]["ci"] = ci
    return path_key(root, path, ci)


def log_error(state_dir, text):
    """훅 내부 오류를 남긴다(작업은 막지 않는다). / Record an internal hook error."""
    try:
        path = Path(state_dir) / ERROR_LOG
        old = hio.read_text(path) if path.is_file() else ""
        if len(old.encode("utf-8")) > ERROR_LOG_MAX:
            old = old[-ERROR_LOG_MAX // 2:]
        hio.write_text(path, old + f"[{now_iso()}] {text.rstrip()}\n")
    except OSError:
        pass
