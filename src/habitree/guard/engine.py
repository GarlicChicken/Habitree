"""guard 엔진: 이벤트를 세션 상태에 적고(observe), 감지기를 돌리고(evaluate), 누구에게 어떻게 알릴지 정한다(route).
/ The guard engine: record the event (observe), run detectors (evaluate), decide who hears what (route).

잔소리가 되지 않게 하는 장치:
- 규칙마다 repeat(once_per_session·once_per_streak·always)와 max_per_session.
- 같은 사건을 두 규칙이 겹쳐 알리지 않게 dedup 열쇠.
- 이 세션에서 끈 규칙(guard off)은 건너뜀. 쉬거나 폐기한 규칙도 건너뜀.
- 정보(info) 등급은 바로 말하지 않고 답이 끝날 때 한 번에 모아 보인다.
- 위임 중이면 규칙의 on_delegate(skip·ask·nudge)를 따른다.
"""
import json
import re
import time
from pathlib import Path

from ..core import io as hio
from ..core.fast import lazy_re
from ..core.i18n import tr
from ..core.paths import iter_files
from ..core.state import file_key, push
from ..core.textsim import tokens
from ..core.timeutil import now_iso
from . import delegate
from .copyscan import inserted_text, line_delta, new_windows
from .detectors import DETECTORS, is_ack, is_correction, param
from .events import count_lines, read_text_small
from .texts import fmt, numbered, t

EVENT_KIND = {"SessionStart": "start", "UserPromptSubmit": "prompt", "PreToolUse": "pre", "PostToolUse": "post",
              "PostToolUseFailure": "post", "Stop": "stop"}
HISTORY = 40          # 기본으로 남기는 최근 호출·결과 수 / default number of recent calls and results kept
DEDUP_SPAN = 20       # 규칙 사이 겹침을 보는 호출 거리 / call distance for the cross-rule duplicate guard
FILES_CACHE = "cache/files.json"
FILES_CACHE_AGE = 3600
FILES_CACHE_MAX = 20000
MUTATING = lazy_re(
    r"(?:>|\bmv\b|\bcp\b|\brm\b|\bmkdir\b|\btouch\b|\bsed\s+-i|\bgit\s+(?:add|commit|mv|rm|checkout|apply|merge|"
    r"rebase|reset|restore|stash|switch)\b|\bhabitree\s+(?:init|export|rules\s+(?:add|hit|miss|edit|retire|pause|"
    r"resume|demote|doc))\b|\b(?:npm|pnpm|yarn)\s+(?:install|i|add)\b|\bpip\s+install\b|\buv\s+(?:add|sync)\b|"
    r"Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Move-Item|Copy-Item|Rename-Item)", re.I)


def rule_kinds(rule):
    names = re.split(r"[|,\s]+", str((rule.get("detect") or {}).get("event", "")))
    return {EVENT_KIND[n] for n in names if n in EVENT_KIND}


class Outcome:
    """한 이벤트에서 나갈 것. / What one event sends out."""

    def __init__(self):
        self.ai = []           # AI 맥락 / AI context lines
        self.user = []         # 사용자 화면 / user-visible lines
        self.relay = []        # AI가 사용자에게 전할 줄 / lines the AI should relay
        self.permission = None  # None | "ask" | "deny"
        self.reasons = []
        self.block = []        # Stop을 막는 이유 / reasons to keep going at Stop
        self.notes = []        # 정보 등급 / info notes

    def ask(self, level, reason):
        rank = {None: 0, "ask": 1, "deny": 2}
        if rank[level] > rank[self.permission]:
            self.permission = level
        if reason:
            self.reasons.append(reason)

    @property
    def empty(self):
        return not (self.ai or self.user or self.permission or self.block)


class Run:
    """이벤트 하나를 처리하는 동안의 맥락. / Context while handling one event."""

    def __init__(self, ctx, db, state, ev):
        self.ctx, self.db, self.state, self.ev = ctx, db, state, ev
        self.lang = ctx.lang
        self.root = ctx.root
        self.started = None    # 이번 요청으로 시작한 위임 / delegation started by this prompt
        self.extra = {}
        self._files = None

    def key(self, path):
        return file_key(self.root, path, self.state)

    def detect_of(self, signal_name):
        if self.db is None:
            return None
        for r in self.db.active():
            d = r.get("detect")
            if d and d.get("signal") == signal_name and r["id"] not in self.state.get("off", []):
                return r
        return None

    def inside_root(self, path):
        try:
            Path(path).resolve().relative_to(Path(self.root).resolve())
            return True
        except (ValueError, OSError):
            return False

    def file_list(self):
        """복사 코드 탐색용 파일 목록(세션 시작 때 캐시). / File list cached at session start."""
        if self._files is None:
            self._files = load_files(self.ctx)
        return self._files


def build_files(ctx):
    excludes = list(ctx.get("exclude") or []) + [".habitree"]
    out = []
    for rel in iter_files(ctx.root, excludes)[:FILES_CACHE_MAX]:
        try:
            out.append([rel, (ctx.root / rel).stat().st_size])
        except OSError:
            continue
    hio.write_text(ctx.state_dir / FILES_CACHE,
                   json.dumps({"built": time.time(), "files": out}, ensure_ascii=False, separators=(",", ":")))
    return [tuple(x) for x in out]


def load_files(ctx):
    path = ctx.state_dir / FILES_CACHE
    try:
        data = hio.load_json(path)
        if data and time.time() - data.get("built", 0) < FILES_CACHE_AGE:
            return [tuple(x) for x in data.get("files", [])]
    except (ValueError, OSError):
        pass
    return build_files(ctx)


# ── 적기 ──

def _shell_is_verify(cmd, verify):
    """명령이 설정의 검증 명령(verify)을 돌리는가: 낱말이 같은 차례로 다 들어 있으면. / Does the command run a verify?"""
    words = cmd.replace('"', " ").replace("'", " ").split()
    for argv in (verify or {}).values():
        if not isinstance(argv, list) or not argv:
            continue
        it = iter(words)
        if all(any(_same_word(w, a, i == 0) for w in it) for i, a in enumerate(argv)):
            return True
    return bool(re.search(r"\bhabitree\s+verify\b", cmd))


def _same_word(word, want, program):
    """명령 낱말이 같은가. 실행 파일은 경로·.exe·뒤 숫자(python3)를 무시한다. / Compare one argument."""
    if word == want:
        return True
    if not program:
        return False
    base = re.split(r"[\\/]", word)[-1].lower()
    base = re.sub(r"\.exe$", "", base)
    return base == want.lower() or re.sub(r"[\d.]+$", "", base) == want.lower()


def _edit_texts(ev):
    """(옛 글, 새 글) 쌍 목록. / (old, new) pairs for an edit tool."""
    inp = ev.input if isinstance(ev.input, dict) else {}
    if ev.tool == "Edit":
        return [(str(inp.get("old_string") or ""), str(inp.get("new_string") or ""))]
    if ev.tool == "MultiEdit":
        return [(str(e.get("old_string") or ""), str(e.get("new_string") or ""))
                for e in inp.get("edits") or [] if isinstance(e, dict)]
    if ev.tool == "Write":
        old = read_text_small(ev.path) if ev.path else None
        return [(old or "", str(inp.get("content") or ""))]
    return []


def observe(run, out):
    """이벤트를 세션 상태에 적는다(감지기보다 먼저). / Record the event before detectors run."""
    ev, st = run.ev, run.state
    hist = run.ctx.get("guard.history", HISTORY) or HISTORY
    if ev.kind == "pre":
        st["counter"] = st.get("counter", 0) + 1
        push(st, "calls", {"s": ev.sig, "t": ev.tool, "c": st["counter"], "ro": ev.readonly, "at": ev.at}, hist)
        if ev.is_edit and ev.path and ev.fkey:
            _pre_edit(run)
        d = delegate.active(st)
        if d:
            d["tools"] = d.get("tools", 0) + 1
            limit = run.ctx.get("guard.delegate.max_tools", 200)
            if limit and d["tools"] > limit:
                delegate.end(st, "limit")
                out.ai.append(t("delegate.limit", run.lang, n=limit))
    elif ev.kind == "post":
        pid = ev.tool_id or ev.sig
        pend = st.get("pending", {}).pop(pid, None)
        push(st, "results", {"s": ev.sig, "t": ev.tool, "ok": ev.ok, "e": ev.error_key, "el": ev.error_line,
                             "c": st.get("counter", 0), "ro": ev.readonly, "len": ev.out_len}, hist)
        if ev.ok and ev.is_edit and pend:
            f = st["files"].get(pend["f"])
            if f is not None:
                f["added"] = f.get("added", 0) + pend.get("a", 0)
                f["removed"] = f.get("removed", 0) + pend.get("r", 0)
                now = count_lines(ev.path) if ev.path else None
                f["now"] = now if now is not None else f.get("now")
                if pend.get("small"):
                    f.setdefault("small", []).append(ev.at)
                    del f["small"][:-50]
            st["edits"] = st.get("edits", 0) + 1
            st["edits_since_verify"] = st.get("edits_since_verify", 0) + 1
            st["edits_since_check"] = st.get("edits_since_check", 0) + 1
            run.extra["win"] = pend.get("win") or {}
        cmd = ev.shell
        if cmd and ev.ok is not None:
            if _shell_is_verify(cmd, run.ctx.get("verify")):
                st["verify_runs"] = st.get("verify_runs", 0) + 1
                st["edits_since_verify"] = 0
                for f in st.get("files", {}).values():
                    f["small"] = []
            elif re.search(r"\bhabitree\s+check\b", cmd) and ev.ok:
                st["edits_since_check"] = 0
            elif MUTATING.search(cmd):
                st["edits_since_check"] = st.get("edits_since_check", 0) + 1
    elif ev.kind == "prompt":
        _observe_prompt(run, out)


def _pre_edit(run):
    ev, st = run.ev, run.state
    files = st.setdefault("files", {})
    f = files.get(ev.fkey)
    if f is None:
        start = count_lines(ev.path)
        f = files[ev.fkey] = {"p": ev.rel, "start": start if start is not None else 0, "now": start,
                              "added": 0, "removed": 0, "small": []}
    pairs = _edit_texts(ev)
    added = removed = 0
    changed = 0
    for old, new in pairs:
        a, r = line_delta(old, new)
        added += a
        removed += r
        changed = max(changed, len(old.split("\n")) if old else 0, len(new.split("\n")) if new else 0)
    small_rule = run.detect_of("small_edits_same_file")
    small_lines = param(small_rule, "small_lines", 3) if small_rule else 3
    win = {}
    copy_rule = run.detect_of("copy_block")
    if copy_rule:
        k = copy_rule["detect"].get("threshold", 6) or 6
        min_chars = param(copy_rule, "min_chars", 80)
        runs = []
        for old, new in pairs:
            runs += inserted_text(old, new) if old else [new]
        win = new_windows(runs, k, min_chars)
    pending = st.setdefault("pending", {})
    pending[ev.tool_id or ev.sig] = {"f": ev.fkey, "a": added, "r": removed, "win": win,
                                     "small": ev.tool in ("Edit", "MultiEdit") and 0 < changed <= small_lines}
    for k in list(pending)[:-30]:
        pending.pop(k, None)


def _observe_prompt(run, out):
    ev, st = run.ev, run.state
    st["turns"] = st.get("turns", 0) + 1
    prompt = ev.prompt or ""
    toks = tokens(prompt)
    d = delegate.active(st)
    cmd = delegate.command(prompt)
    if cmd and cmd[0] == "off":
        if delegate.end(st, "command"):
            out.ai.append(t("delegate.cancel", run.lang))
    elif cmd:
        delegate.end(st, "replaced")
        run.started = delegate.start(st, "", cmd[1] or prompt, by="command", task=cmd[1] or None)
    elif d and delegate.is_cancel(prompt):
        delegate.end(st, "cancel")
        out.ai.append(t("delegate.cancel", run.lang))
    elif d and _new_topic(prompt, toks, d):
        delegate.end(st, "new_topic")
        out.ai.append(t("delegate.topic", run.lang))
    elif not d and run.ctx.get("guard.delegate.natural", True) and run.detect_of("delegation"):
        phrase = delegate.find_phrase(prompt)
        if phrase:
            paths = [p for p in delegate.path_words(prompt) if (run.root / p).exists()]
            run.started = delegate.start(st, phrase, prompt, scope_paths=paths)
    push(st, "prompts", {"i": st["turns"], "at": ev.at, "len": len(prompt.strip()), "tok": sorted(toks)[:60],
                         "corr": is_correction(prompt, run.detect_of("repeat_correction")),
                         "ack": is_ack(prompt), "cmd": prompt.strip().startswith("/")}, 30)


def _new_topic(prompt, toks, d):
    text = (prompt or "").strip()
    if len(text) < 20 or is_ack(text) or delegate.CONTINUE.match(text) or len(toks) < 4:
        return False
    base = set(d.get("tokens", []))
    return bool(base) and len(toks & base) / len(toks) < 0.1


# ── 판정과 전달 ──

def evaluate(run, out):
    if run.db is None:
        return out
    for rule in run.db.active():
        if not rule.get("detect") or run.ev.kind not in rule_kinds(rule):
            continue
        if rule["id"] in run.state.get("off", []):
            continue
        fn = DETECTORS.get(rule["detect"].get("signal"))
        if fn is None:
            continue
        sig = fn(rule, run)
        if sig:
            route(rule, sig, run, out)
            if sig.get("end_delegation"):
                delegate.end(run.state, "report")
    return out


def _texts(rule, sig, lang):
    msg = rule.get("message") or {}
    facts = sig.get("facts", {})
    ai = fmt(tr(msg.get("ai"), lang), facts) if msg.get("ai") else ""
    user = fmt(tr(msg.get("user"), lang), facts) if msg.get("user") else ""
    sugg = [fmt(tr(s, lang), facts) for s in msg.get("suggest") or []]
    return ai, user, sugg


def _ai_line(rule, level, text, sugg, lang):
    head = t("head.delegate" if rule["scope"].startswith("work/delegate") else f"head.{level}", lang)
    line = f"{head} {text}"
    if sugg:
        line += f" {t('suggest', lang)} {numbered(sugg, lang)}"
    return f"{line} {t('rule_tail_ai', lang, id=rule['id'])}"


def _user_line(rule, text, sugg, lang):
    line = t("user_prefix", lang) + text
    if sugg:
        line += " " + numbered(sugg, lang)
    return f"{line}\n{t('rule_tail_user', lang, id=rule['id'])}"


def route(rule, sig, run, out):
    """신호를 등급·반복 제한·위임 상태에 따라 내보낸다. / Deliver a signal by level, limits and delegation."""
    st, ev, lang = run.state, run.ev, run.lang
    det = rule.get("detect") or {}
    rid = rule["id"]
    level = "stop" if sig.get("stop") else det.get("severity", "info")
    rec = st.setdefault("warned", {}).setdefault(rid, {"count": 0, "keys": {}})
    kl = f"{sig['key']}|{level}"
    repeat = det.get("repeat", "once_per_streak")
    if repeat == "once_per_session" and rec["count"] >= 1:
        return False
    if repeat == "once_per_streak" and kl in rec["keys"]:
        return False
    mx = det.get("max_per_session")
    if mx and rec["count"] >= mx and level != "stop":
        return False
    counter = st.get("counter", 0)
    dk = f"{sig['dedup']}|{level}" if sig.get("dedup") else None
    if dk:
        prev = st.setdefault("dedup", {}).get(dk)
        if prev and prev.get("rule") != rid and counter - prev.get("c", 0) <= DEDUP_SPAN:
            rec["keys"][kl] = counter  # 같은 사건은 이미 알렸다
            return False
    rec["count"] += 1
    rec["keys"][kl] = counter
    if len(rec["keys"]) > 60:
        for k in list(rec["keys"])[:-60]:
            rec["keys"].pop(k, None)
    if dk:
        st["dedup"][dk] = {"rule": rid, "c": counter}
        if len(st["dedup"]) > 100:
            for k in list(st["dedup"])[:-100]:
                st["dedup"].pop(k, None)
    ai, user, sugg = _texts(rule, sig, lang)
    short = user or ai
    push(st, "signals", {"at": now_iso(), "rule": rid, "level": level, "n": sig.get("n"), "text": short[:200]}, 50)
    d = delegate.active(st)
    od = rule.get("on_delegate", "nudge")
    audience = det.get("audience", "ai")

    if level == "info":
        out.notes.append((rid, short))
        st.setdefault("turn", []).append({"rule": rid, "text": short})
        if d:
            d.setdefault("suppressed", []).append({"rule": rid, "text": short, "level": level})
        return True
    ai_line = _ai_line(rule, level, ai or user, sugg, lang)
    if d:
        if od == "skip":
            d.setdefault("suppressed", []).append({"rule": rid, "text": short, "level": level})
            return True
        if od == "ask" and ev.kind == "pre":
            out.ask("ask", t("user_prefix", lang) + (user or ai) + f" ({rid})")
            out.ai.append(ai_line)
            return True
        if level == "stop" and ev.kind == "pre":
            out.ask("deny", f"{ai or user} {t('stop.deny', lang)} ({rid})")
            return True
        if ev.kind == "stop":
            out.block.append(ai_line)
            return True
        out.ai.append(ai_line)
        if not rule["scope"].startswith("work/delegate"):
            d.setdefault("suppressed", []).append({"rule": rid, "text": short, "level": level, "to": "ai"})
        return True
    if ev.kind == "stop":
        if audience in ("user", "both") and level != "stop":
            out.user.append(_user_line(rule, user or ai, sugg, lang))
        else:
            out.block.append(ai_line)
        return True
    if level == "stop":
        out.ai.append(f"{ai_line} {t('stop.ask', lang)}")
        if ev.kind == "pre":
            out.ask("ask", f"{t('user_prefix', lang)}{user or ai} {t('stop.user', lang)} ({rid})")
        else:
            line = _user_line(rule, user or ai, sugg, lang)
            out.user.append(line)
            out.relay.append(line)
        return True
    if audience in ("user", "both"):
        line = _user_line(rule, user or ai, sugg, lang)
        out.user.append(line)
        out.relay.append(line)
        if ai:
            out.ai.append(ai_line)
        return True
    out.ai.append(ai_line)
    st.setdefault("turn", []).append({"rule": rid, "text": short})
    return True
