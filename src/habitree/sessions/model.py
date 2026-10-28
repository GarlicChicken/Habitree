"""세션 기록의 공통 레코드. 도구마다 어댑터가 자기 형식을 이 모양으로 바꾼다. / Common session records.

도구 입력·결과 글·사람이 친 글은 판정할 때 메모리에서만 쓰고, 보고서(글·JSON)에는 내보내지 않는다.
보고서에 나가는 것은 개수, 토큰, 이름, 해시, 프로젝트 안의 상대 경로뿐이다.
"""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from importlib import resources

MAIN = "main"


@lru_cache(maxsize=1)
def table():
    """data/sessions.json. / Lookup tables."""
    return json.loads(resources.files("habitree.data").joinpath("sessions.json").read_text(encoding="utf-8"))


def parse_ts(value):
    """'2026-10-28T05:02:03.123Z' 같은 ISO 시각 → UTC datetime(못 읽으면 None). / Parse an ISO timestamp."""
    if not isinstance(value, str) or len(value) < 19:
        return None
    try:
        dt = datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    rest = re.sub(r"^\.\d+", "", value[19:])
    m = re.match(r"([+-])(\d\d):?(\d\d)$", rest)
    off = timedelta(hours=int(m.group(2)), minutes=int(m.group(3))) * (1 if m and m.group(1) == "+" else -1) \
        if m else timedelta(0)
    return dt.replace(tzinfo=timezone(off)).astimezone(timezone.utc)


def iso(dt):
    """저장용 UTC 문자열. / UTC string for storage."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def norm_path(path):
    """비교용 경로 키(어느 OS의 경로든): NFC, '/', 끝 '/' 없음, Windows 꼴이면 대소문자 무시. / Path key."""
    p = unicodedata.normalize("NFC", str(path or "")).replace("\\", "/")
    unc = p.startswith("//")
    p = ("/" if unc else "") + re.sub(r"/+", "/", p)
    p = p.rstrip("/") if len(p) > 1 else p
    return p.casefold() if unc or re.match(r"^[A-Za-z]:(/|$)", p) else p


def within(path, root):
    """path가 root이거나 그 아래인가. / Is path equal to or under root?"""
    a, b = norm_path(path), norm_path(root)
    return bool(a and b) and (a == b or a.startswith(b.rstrip("/") + "/"))


def show_path(path, root):
    """보고서용: 프로젝트 안이면 상대 경로, 밖이면 파일 이름만. / Relative path, or only the name if outside."""
    if not path:
        return ""
    if within(path, root):
        def slashed(p):
            return re.sub(r"/+", "/", unicodedata.normalize("NFC", str(p)).replace("\\", "/")).rstrip("/")
        return slashed(path)[len(slashed(root)):].lstrip("/") or "."
    return "<out>/" + unicodedata.normalize("NFC", re.split(r"[\\/]", str(path))[-1])


class Request:
    """응답 하나(같은 message.id·requestId 묶음). 사용량은 한 번만 센다. / One API response, counted once."""
    __slots__ = ("key", "ctx", "model", "ts", "order", "input", "output", "cache_read", "cache_write_5m",
                 "cache_write_1h", "lines", "tool_ids")

    def __init__(self, key, ctx, model, ts, order):
        self.key, self.ctx, self.model, self.ts, self.order = key, ctx, model, ts, order
        self.input = self.output = self.cache_read = self.cache_write_5m = self.cache_write_1h = self.lines = 0
        self.tool_ids = []

    @property
    def prompt(self):
        """이 요청의 프롬프트 전체(캐시 포함). / Whole prompt size."""
        return self.input + self.cache_read + self.cache_write_5m + self.cache_write_1h

    def tokens(self):
        return {"input": self.input, "output": self.output, "cache_read": self.cache_read,
                "cache_write_5m": self.cache_write_5m, "cache_write_1h": self.cache_write_1h}


class ToolCall:
    """도구 호출 하나(tool_use.id 단위). / One tool call, keyed by tool_use.id."""
    __slots__ = ("id", "name", "input", "ctx", "order", "ts", "request", "error", "chars", "err_sig", "info",
                 "has_result")

    def __init__(self, cid, name, inp, ctx, order, ts, request):
        self.id, self.name, self.ctx, self.order, self.ts, self.request = cid, name, ctx, order, ts, request
        self.input = inp if isinstance(inp, dict) else {}
        self.error, self.chars, self.err_sig, self.info, self.has_result = False, 0, None, {}, False

    def path(self):
        for k in ("file_path", "path", "notebook_path"):
            if isinstance(self.input.get(k), str) and self.input[k]:
                return self.input[k]
        return ""

    def command(self):
        return self.input.get("command") if isinstance(self.input.get("command"), str) else ""


class Session:
    __slots__ = ("id", "tool", "cwd", "files", "started", "ended", "requests", "calls", "human", "agents",
                 "compactions", "versions")

    def __init__(self, sid, tool):
        self.id, self.tool, self.cwd = sid, tool, None
        self.files, self.versions = set(), set()
        self.started = self.ended = None
        self.requests, self.calls, self.agents = {}, {}, {}  # key → Request, id → ToolCall, ctx → {"type"}
        self.human = []        # (시각, 글, 순서): 사람이 친 글, 메모리에만
        self.compactions = []  # (ctx, 순서)

    def touch(self, ts):
        if ts is not None:
            self.started = ts if self.started is None or ts < self.started else self.started
            self.ended = ts if self.ended is None or ts > self.ended else self.ended

    def contexts(self):
        seen = []
        for x in list(self.requests.values()) + list(self.calls.values()):
            if x.ctx not in seen:
                seen.append(x.ctx)
        return seen

    def ordered_requests(self, ctx=None):
        return sorted((r for r in self.requests.values() if ctx is None or r.ctx == ctx), key=lambda r: r.order)

    def ordered_calls(self, ctx=None):
        return sorted((c for c in self.calls.values() if ctx is None or c.ctx == ctx), key=lambda c: c.order)


class Scan:
    """읽은 결과: 세션과, 형식이 바뀌었는지 알 수 있는 숫자. / Sessions plus format-drift counters."""

    def __init__(self, tool):
        self.tool = tool
        self.folders, self.memory_dirs = [], []
        self.files = self.bad_lines = self.duplicate_lines = self.other_cwd = 0
        self.sessions = {}
        self.unknown_types = {}  # 모르는 type → 줄 수(형식이 바뀌면 여기에 보인다)


def category(tool_name):
    """도구 이름 → 행동 범주(read·search·write·shell·delegate·web·mcp·other). / Tool behavior category."""
    for cat, names in table()["tool_categories"].items():
        if tool_name in names:
            return cat
    return "mcp" if str(tool_name).startswith("mcp__") else "other"


def read_only_shell(command):
    """읽기만 하는 셸 명령인가(보수적으로: 모르면 아니다). / Is this shell command read-only?"""
    bare = re.sub(r"'[^']*'|\"[^\"]*\"", "''", (command or "").strip())
    bare = re.sub(r"\d?>&\d|2>\s*(/dev/null|\$null|nul)", " ", bare, flags=re.I)
    if not bare or ">" in bare or "<<" in bare or re.search(r"-delete\b|-exec\b", bare):
        return False
    prefixes = table()["read_only_shell"]
    for part in re.split(r"&&|\|\||;|\|", bare):
        words = part.split()
        if words and words[0] not in ("cd", "Set-Location") and \
                not any(" ".join(words[:len(p.split())]) == p for p in prefixes):
            return False
    return True


def text_of(content):
    """tool_result 내용의 글(글자 블록만). / Text of a tool_result content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str))
    return ""


def error_signature(text):
    """오류 첫 줄을 숫자·경로를 지운 해시로. 원문은 남기지 않는다. / Hash of the first error line."""
    line = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    line = re.sub(r"[A-Za-z]:\\[^\s'\"]+|/[^\s'\"]+", "<path>", line)
    return hashlib.sha256(re.sub(r"\d+", "0", line.lower())[:160].encode("utf-8")).hexdigest()[:12]


def input_hash(name, inp):
    """도구 이름 + 키를 정렬한 입력 JSON의 해시(v0.2 guard와 같은 방식). / Hash of tool name and sorted input."""
    body = json.dumps(inp if isinstance(inp, dict) else {}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(f"{name}\0{body}".encode("utf-8")).hexdigest()[:16]
