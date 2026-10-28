"""Claude Code 세션 기록 어댑터. / Claude Code transcript adapter.

위치(공식 문서 sessions.md): ~/.claude/projects/<프로젝트>/<세션 ID>.jsonl. <프로젝트>는 작업 폴더 경로에서
영문자·숫자가 아닌 글자를 모두 '-'로 바꾼 이름이고, 200자를 넘으면 자르고 해시를 붙인다.
CLAUDE_CONFIG_DIR가 있으면 ~/.claude 대신 그 폴더다. 서브에이전트는 <세션 ID>/subagents/agent-<id>.jsonl.

이름 바꾸기는 되돌릴 수 없어서(한글·NFD 자모는 글자마다 '-') 폴더 이름은 후보를 고르는 데만 쓰고,
이 프로젝트의 세션인지는 레코드의 cwd로 정한다. 줄 구조는 공식 계약이 아니라서(#53516 not_planned):
  - 사용량은 assistant 줄만 보고 (message.id, requestId)로 묶어 한 번만 센다. 한 응답이 내용 블록마다
    한 줄씩 기록되고 같은 usage가 되풀이된다. 칸마다 가장 큰 값을 남긴다(출력은 뒤 줄로 갈수록 커진다).
  - 도구 호출은 tool_use.id 단위. api-request-blob 줄의 tool_use는 사본이라 보지 않는다.
  - 같은 uuid가 다시 붙은 줄(#56196)은 한 번만, 모르는 type은 개수만 센다(형식이 바뀌면 보이게).
"""
import json
import os
import re
import unicodedata
from pathlib import Path

from ..core import io as hio
from .model import MAIN, Request, Scan, Session, ToolCall, error_signature, parse_ts, table, text_of, within

NAME = "claude"
SUPPORTED = True


def config_dir(explicit=None):
    """인자 → CLAUDE_CONFIG_DIR → ~/.claude. / The Claude Code config directory."""
    return Path(explicit or os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def encode_dir_name(path):
    """작업 폴더 경로 → projects/ 아래 폴더 이름(공식 규칙). / Folder name derived from a path."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def _encodings(root):
    s = str(root).rstrip("/\\") or str(root)
    forms = {s, unicodedata.normalize("NFC", s), unicodedata.normalize("NFD", s)}
    return {encode_dir_name(f).casefold() for f in forms}


def candidate_dirs(projects, root):
    """root나 그 아래에서 시작한 세션이 있을 수 있는 폴더(최종 판정은 cwd). / Candidate folders."""
    projects = Path(projects)
    if not projects.is_dir():
        return []
    encs = _encodings(root)
    return [d for d in sorted(projects.iterdir()) if d.is_dir() and any(
        d.name.casefold() == e or d.name.casefold().startswith(e + "-") or
        (len(e) > 200 and d.name.casefold().startswith(e[:200])) for e in encs)]


def _human_text(rec, content):
    """사람이 친 글이면 그 글. / The text if a person typed it."""
    origin = rec.get("origin")
    if rec.get("isMeta") or rec.get("isSidechain") or (isinstance(origin, dict) and origin.get("kind") != "human"):
        return None
    if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    text = text_of(content).strip()
    if not text or (origin is None and text.startswith(tuple(table()["claude"]["system_tags"]))):
        return None
    return text


def _usage_into(req, u):
    def num(v):
        return v if isinstance(v, int) and not isinstance(v, bool) else 0
    req.input = max(req.input, num(u.get("input_tokens")))
    req.output = max(req.output, num(u.get("output_tokens")))
    req.cache_read = max(req.cache_read, num(u.get("cache_read_input_tokens")))
    split = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else {}
    w1 = num(split.get("ephemeral_1h_input_tokens"))
    w5 = max(num(u.get("cache_creation_input_tokens")) - w1, num(split.get("ephemeral_5m_input_tokens")))
    req.cache_write_5m, req.cache_write_1h = max(req.cache_write_5m, w5), max(req.cache_write_1h, w1)


def _attach(call, block, tur):
    call.has_result = True
    text = text_of(block.get("content"))
    call.chars = max(call.chars, len(text))
    if block.get("is_error"):
        call.error, call.err_sig = True, error_signature(text)
    f = tur.get("file") if isinstance(tur, dict) else None
    if isinstance(f, dict):
        call.info.update({k: f[k] for k in ("totalLines", "numLines", "startLine") if f.get(k) is not None})


def _read(path, folder, res, sessions, seen_uuid, counter):
    sub = "subagents" in path.relative_to(folder).parts
    agent_id = path.stem[len("agent-"):] if sub and path.stem.startswith("agent-") else None
    meta = {}
    if sub:
        try:
            m = hio.load_json(path.with_name(path.stem + ".meta.json")) or {}
            meta = {"type": m.get("agentType")}  # 설명 글(description)은 읽지 않는다
        except (ValueError, OSError):
            pass
    ignored = set(table()["claude"]["ignored_types"])
    pending = {}
    for line in hio.read_text(path).split("\n"):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            rec = None
        if not isinstance(rec, dict):
            res.bad_lines += 1
            continue
        rtype = rec.get("type")
        if rtype not in ("user", "assistant", "system"):
            if rtype not in ignored:
                res.unknown_types[str(rtype)] = res.unknown_types.get(str(rtype), 0) + 1
            continue
        uid = rec.get("uuid")
        if uid in seen_uuid:
            res.duplicate_lines += 1
            continue
        if uid:
            seen_uuid.add(uid)
        sid = rec.get("sessionId") or (path.parent.parent.name if sub else path.stem)
        ses = sessions.setdefault(sid, Session(sid, NAME))
        ses.files.add(str(path))
        if rec.get("version"):
            ses.versions.add(str(rec["version"]))
        if ses.cwd is None and not sub and isinstance(rec.get("cwd"), str):
            ses.cwd = rec["cwd"]
        ts = parse_ts(rec.get("timestamp"))
        ses.touch(ts)
        ctx = "agent:" + str(rec.get("agentId") or agent_id or "?") if sub or rec.get("isSidechain") else MAIN
        if ctx != MAIN:
            ses.agents.setdefault(ctx, dict(meta))
        counter[0] += 1
        if rtype == "system":
            if rec.get("subtype") == "compact_boundary":
                ses.compactions.append((ctx, counter[0]))
            continue
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        content = msg.get("content")
        if rtype == "assistant":
            key = (msg.get("id") or uid, rec.get("requestId") or sid)
            req = ses.requests.get(key)
            if req is None:
                req = ses.requests[key] = Request(key, ctx, msg.get("model") or "", ts, counter[0])
            req.lines += 1
            if isinstance(msg.get("usage"), dict):
                _usage_into(req, msg["usage"])
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") and b["id"] not in ses.calls:
                    counter[0] += 1
                    call = ses.calls[b["id"]] = ToolCall(b["id"], b.get("name") or "", b.get("input"), ctx,
                                                         counter[0], ts, key)
                    req.tool_ids.append(call.id)
                    if call.id in pending:
                        _attach(call, *pending.pop(call.id))
            continue
        results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"] \
            if isinstance(content, list) else []
        for i, b in enumerate(results):
            tur = rec.get("toolUseResult") if i == 0 else None
            if b.get("tool_use_id") in ses.calls:
                _attach(ses.calls[b["tool_use_id"]], b, tur)
            elif b.get("tool_use_id"):
                pending[b["tool_use_id"]] = (b, tur)
        text = None if results or ctx != MAIN else _human_text(rec, content)
        if text:
            ses.human.append((ts, text, counter[0]))


def scan(root, claude_dir=None, folders=None):
    """이 루트의 세션을 읽는다. folders를 주면 그 폴더만. / Read the sessions of one project."""
    res = Scan(NAME)
    folders = [Path(f) for f in folders] if folders is not None else \
        candidate_dirs(config_dir(claude_dir) / "projects", root)
    res.folders = [str(f) for f in folders]
    sessions, seen_uuid, counter = {}, set(), [0]
    for folder in folders:
        for path in sorted(folder.rglob("*.jsonl")):
            if path.relative_to(folder).parts[0] in ("memory", "tool-results"):
                continue
            res.files += 1
            try:
                _read(path, folder, res, sessions, seen_uuid, counter)
            except OSError:
                continue
    for sid, ses in sessions.items():
        if ses.cwd and within(ses.cwd, root):
            res.sessions[sid] = ses
        else:
            res.other_cwd += 1
    own = _encodings(root)
    used = {str(Path(f).parent) for s in res.sessions.values() for f in s.files}
    res.memory_dirs = [str(f / "memory") for f in folders if (f / "memory").is_dir() and
                       (f.name.casefold() in own or str(f) in used)]
    return res


def transcript_dir(session_id, workdir, claude_dir=None):
    """bench 교차 확인: 그 작업 폴더에서 돈 세션의 기록 폴더(없으면 None). / Folder holding one session."""
    for d in candidate_dirs(config_dir(claude_dir) / "projects", workdir):
        if (d / f"{session_id}.jsonl").is_file():
            return d
    return None


def feedback_memories(memory_dirs):
    """자동 메모리 중 머리말 type이 feedback인 것의 이름과 한 줄 설명(본문은 옮기지 않는다).
    type은 최상위나 metadata 아래 어느 쪽이든 읽는다. / Name and description of feedback-type memories."""
    out = []
    for d in memory_dirs:
        for p in sorted(Path(d).glob("*.md")):
            if p.name.upper() == "MEMORY.MD":
                continue
            lines = hio.read_text(p).split("\n")
            if not lines or lines[0].strip() != "---":
                continue
            fm = {}
            for line in lines[1:]:
                if line.strip() in ("---", "..."):
                    break
                m = re.match(r"^(\s*)([A-Za-z_]\w*)\s*:\s*(.*?)\s*$", line)
                if m and (m.group(2) == "type" or not m.group(1)):
                    v = m.group(3)
                    if len(v) > 1 and v[0] == v[-1] == '"':
                        v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                    fm.setdefault(m.group(2), v.strip("'"))
            if fm.get("type") == "feedback":
                out.append({"file": p.name, "name": fm.get("name") or p.stem, "description": fm.get("description", "")})
    return out
