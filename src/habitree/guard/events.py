"""표준 이벤트: 어느 AI 도구의 훅이든 이 모양으로 바꿔서 감지기에 넘긴다.
/ The normalized event every detector reads, whatever AI tool sent the hook.

감지기는 행동만 본다: 도구 이름, 입력, 결과의 성패와 길이, 파일 경로, 사용자 메시지.
프로그래밍 언어나 사람의 말(언어)에 기대지 않는다(정정·위임 표현 사전만 언어별).
"""
import hashlib
import json
import os
import re
from pathlib import Path

from ..core import io as hio
from ..core.paths import nfc
from ..core.timeutil import now_iso

KINDS = ("start", "prompt", "pre", "post", "stop")

# 읽기만 하는 도구: 같은 오류 되풀이를 셀 때 사이에 끼어도 고리를 끊지 않는다.
READ_ONLY = frozenset([
    "Read", "Grep", "Glob", "LS", "WebFetch", "WebSearch", "TodoWrite", "TodoRead", "ToolSearch", "NotebookRead",
    "BashOutput", "TaskOutput", "TaskGet", "TaskList", "Monitor",
])
# 파일을 바꾸는 도구와 경로가 든 입력 칸.
EDIT_TOOLS = frozenset(["Edit", "MultiEdit", "Write", "NotebookEdit"])
PATH_KEYS = ("file_path", "notebook_path", "path")
# 같은 호출인지 볼 때 빼는 칸(설명만 다른 같은 명령).
IGNORE_KEYS = ("description",)


class Event:
    """훅 하나가 알려 준 일. / One thing a hook reported."""

    def __init__(self, kind, name="", session="", **kw):
        self.kind = kind            # start | prompt | pre | post | stop
        self.name = name            # 원래 훅 이벤트 이름 / original hook event name
        self.session = session
        self.at = kw.get("at") or now_iso()
        self.tool = kw.get("tool", "")
        self.input = kw.get("input") or {}
        self.tool_id = kw.get("tool_id", "")
        self.ok = kw.get("ok")      # 결과 성패(post) / success (post only)
        self.error = kw.get("error", "")
        self.out_len = kw.get("out_len", 0)
        self.prompt = kw.get("prompt", "")
        self.source = kw.get("source", "")
        self.stop_active = bool(kw.get("stop_active"))
        self.last_message = kw.get("last_message", "")
        self.transcript_bytes = kw.get("transcript_bytes", 0)
        self.path = ""              # 대상 파일의 실제 경로 / target file on disk
        self.fkey = ""              # 대상 파일의 상태 키 / state key of the target file
        self.rel = ""               # 보여 줄 상대 경로 / relative path for display
        self.sig = ""
        self.error_key = ""
        self.error_line = ""

    @property
    def readonly(self):
        return self.tool in READ_ONLY

    @property
    def is_edit(self):
        return self.tool in EDIT_TOOLS

    @property
    def shell(self):
        """셸 명령 글(Bash·PowerShell 등 'command' 칸이 글인 도구). / Shell command text, if any."""
        cmd = self.input.get("command") if isinstance(self.input, dict) else None
        return cmd if isinstance(cmd, str) and not self.is_edit else ""


def signature(tool, tool_input, keyfn=None, ignore=IGNORE_KEYS):
    """도구 이름 + 키를 정렬한 입력의 해시. 경로 칸은 파일 키로 맞춘다.
    / Hash of the tool name and the key-sorted input; path fields use file keys."""
    data = dict(tool_input) if isinstance(tool_input, dict) else {"_": tool_input}
    for k in ignore:
        data.pop(k, None)
    if keyfn:
        for k in PATH_KEYS:
            if isinstance(data.get(k), str) and data[k]:
                data[k] = keyfn(data[k])
    body = json.dumps([tool, data], ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(nfc(body).encode("utf-8")).hexdigest()[:16]


def target_path(tool, tool_input):
    """수정·읽기 도구가 다루는 파일 경로. / File path a tool works on."""
    if not isinstance(tool_input, dict):
        return ""
    for k in ("file_path", "notebook_path"):
        v = tool_input.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def output_length(value, limit=10_000_000):
    """도구 결과에 든 글자 수(안쪽까지). / Characters inside a tool result."""
    total, stack = 0, [value]
    while stack and total < limit:
        v = stack.pop()
        if isinstance(v, str):
            total += len(v)
        elif isinstance(v, dict):
            stack.extend(v.values())
        elif isinstance(v, (list, tuple)):
            stack.extend(v)
    return total


_VOLATILE = re.compile(r"0x[0-9a-fA-F]+|\d{4,}|\d+\.\d+s\b")


def error_parts(error):
    """(오류 열쇠, 보여 줄 한 줄). 시각·주소 같은 바뀌는 숫자는 지운다.
    / (error key, display line). Volatile numbers such as times and addresses are dropped."""
    text = nfc(str(error or "")).replace("\r\n", "\n")
    norm = _VOLATILE.sub("#", " ".join(text.lower().split()))[:2000]
    key = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12] if norm else ""
    line = ""
    for ln in text.split("\n"):
        ln = ln.strip()
        if ln and not re.match(r"^exit code \d+$", ln, re.I):
            line = ln
            break
    if not line:
        line = text.strip().split("\n", 1)[0]
    return key, (line[:117] + "..." if len(line) > 120 else line)


def count_lines(path, max_bytes=4_000_000):
    """파일 줄 수(줄 끝 종류와 무관). 없거나 너무 크면 None. / Line count, or None."""
    try:
        if os.path.getsize(path) > max_bytes:
            return None
        data = Path(path).read_bytes()
    except OSError:
        return None
    if not data:
        return 0
    data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def read_text_small(path, max_bytes=1_000_000):
    try:
        if os.path.getsize(path) > max_bytes:
            return None
        data = Path(path).read_bytes()
    except OSError:
        return None
    if b"\0" in data[:4096]:
        return None
    return hio.read_bytes_text(data).replace("\r\n", "\n").replace("\r", "\n")
