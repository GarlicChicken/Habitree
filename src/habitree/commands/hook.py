"""hook: AI 도구의 훅이 부르는 입구. 표준 입력의 JSON을 읽고 공식 형식의 JSON을 표준 출력에 쓴다.
/ Entry point called by AI tool hooks: JSON on stdin, official JSON on stdout.

  habitree hook SessionStart        작업 순환·필수 규칙 요약을 넣고 세션 상태를 새로 연다
  habitree hook UserPromptSubmit    요청 패턴(쪼개기·거듭 정정·새 주제)과 위임 신호
  habitree hook PreToolUse          같은 호출·고리·같은 오류 멈춤, 위임 중 위험한 일 확인
  habitree hook PostToolUse         잔수정·파일 커짐·복사 코드·큰 결과
  habitree hook PostToolUseFailure  같은 오류 되풀이
  habitree hook Stop                빠른 점검(오류면 한 번 더 일하게), 위임 끝 보고, 알림 모아 보이기

지키는 것:
- 내부 오류는 작업을 막지 않는다: 언제나 종료 코드 0, 오류는 .habitree/state/hook-errors.log에.
- 프로젝트에 .habitree/config.json이 없으면 아무것도 하지 않는다.
- 같은 훅이 플러그인과 프로젝트 설정에 두 번 걸려도 한 번만 처리한다.
"""
import os

from ..core import io as hio
from ..core.fast import short
from ..core import state as hstate
from ..core.config import CONFIG_REL, Context, deep_merge
from ..core.i18n import tr
from ..core.timeutil import now_iso, seconds_since
from ..guard import claude, delegate, engine
from ..guard.texts import t

SUMMARY = {"ko": "AI 도구 훅 입구(표준 입력 JSON → 표준 출력 JSON, 오류가 나도 작업을 막지 않음)",
           "en": "Hook entry for AI tools (JSON in, JSON out; never blocks work on internal errors)"}


def add_arguments(p):
    p.add_argument("event", nargs="?", default="",
                   help="SessionStart | UserPromptSubmit | PreToolUse | PostToolUse | PostToolUseFailure | Stop")


def run(args, ctx):
    return entry([args.event], root=str(ctx.root))


def entry(argv, root=None):
    """훅 입구. 무슨 일이 있어도 0을 돌려준다. / Hook entry; always returns 0."""
    event = argv[0] if argv else ""
    payload = {}
    try:
        payload = hio.read_stdin_json()
        out = handle(event, payload, root)
        if out:
            hio.emit_json(out)
    except BaseException:  # noqa: B902  알림 도구가 작업을 막으면 안 된다 / a notifier must never block work
        _record_failure(event, payload, root)
    return 0


def _start_dir(payload, root):
    return root or os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()


def _record_failure(event, payload, root):
    try:
        ctx = Context.load(_start_dir(payload, root))
        if (ctx.root / CONFIG_REL).is_file():
            import traceback  # 실패할 때만 불러온다(훅을 빠르게) / only on failure, keeps hooks fast
            hstate.log_error(ctx.state_dir, f"{event or '?'}: {traceback.format_exc()}")
    except BaseException:  # noqa: B902
        pass


def handle(event, payload, root=None):
    """훅 하나를 처리하고 출력 dict를 돌려준다(빈 dict면 출력 없음). / Handle one hook; {} means no output."""
    if event not in claude.EVENTS or not isinstance(payload, dict):
        return {}
    ctx = Context.load(_start_dir(payload, root))
    if not ctx.configured or not ctx.get("guard.enabled", True):
        return {}
    db_path = ctx.p(ctx.get("rules.db"))
    data = hio.load_json(db_path, {}) or {}
    sid = str(payload.get("session_id") or "default")
    kind = claude.EVENTS[event]
    if kind == "start":
        from ..core.ruledb import RuleDB  # 세션 시작 때만(요약을 만들 때) / only at session start
        return _session_start(ctx, RuleDB(data, db_path), sid, payload)
    db = _Rules(data)
    with hstate.session(ctx.state_dir, sid) as st:
        ev = claude.to_event(event, payload, ctx.root, lambda p: hstate.file_key(ctx.root, p, st))
        if _duplicate(st, ev):
            return {}
        run_ = engine.Run(ctx, db, st, ev)
        out = engine.Outcome()
        was_delegated = bool(delegate.active(st))
        engine.observe(run_, out)
        engine.evaluate(run_, out)
        if kind == "stop":
            _stop_extras(run_, out, was_delegated)
        return claude.render(event, out, ctx.lang, relay=ctx.get("guard.relay", "always") != "never")


class _Rules:
    """훅이 쓰는 규칙 DB의 읽기 전용 모습. 도구를 쓸 때마다 도는 길이라 검사기·비교기 없이 JSON만 읽는다.
    / Read-only view of the rule DB for hooks: plain JSON, no validator, on the hot path."""

    __slots__ = ("data", "rules")

    def __init__(self, data):
        from ..core.packs import live_rules
        self.data = data
        self.rules = list(data.get("rules") or []) + live_rules(data, ("work",))  # 훅은 감지 규칙만

    def active(self):
        return [r for r in self.rules if r.get("status", "active") == "active"]


def _duplicate(st, ev):
    """플러그인과 프로젝트 설정에 같은 훅이 둘 다 있을 때 두 번째 부름을 건너뛴다. / Skip a doubled hook call."""
    seen = st.setdefault("seen", {})
    if ev.kind in ("pre", "post") and ev.tool_id:
        ids = seen.setdefault(ev.kind, [])
        if ev.tool_id in ids:
            return True
        ids.append(ev.tool_id)
        del ids[:-60]
        return False
    body = f"{ev.kind}\0{ev.prompt or ev.last_message}\0{ev.source}\0{ev.stop_active}"
    key = short(body, 12)
    items = seen.setdefault(ev.kind, [])
    if any(k == key and (seconds_since(at) or 99) < 5 for k, at in items):
        return True
    items.append([key, now_iso()])
    del items[:-10]
    return False


def _session_start(ctx, db, sid, payload):
    source = str(payload.get("source") or "startup")
    sdir = ctx.state_dir
    old = hstate.read(sdir, sid)
    body = short(f"start\0{source}", 12)
    if old and any(k == body and (seconds_since(at) or 99) < 5 for k, at in old.get("seen", {}).get("start", [])):
        return {}
    hstate.cleanup(sdir, ctx.get("guard.state_days", 7) or 7)
    fresh = source in ("startup", "clear") or old is None
    with hstate.session(sdir, sid, fresh=fresh) as st:
        st["source"] = source
        st.setdefault("seen", {}).setdefault("start", []).append([body, now_iso()])
        text = session_text(ctx, db, st)
    try:
        engine.build_files(ctx)
    except OSError:
        pass
    if not text:
        return {}
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": claude._cut(text)}}


def _agents_loaded(ctx):
    """AGENTS.md(작업 순환·필수 규칙)가 CLAUDE.md의 @AGENTS.md로 이미 실리는가. / Already loaded via CLAUDE.md?"""
    from ..core.markdown import get_block
    try:
        claude_md, agents_md = ctx.p("CLAUDE.md"), ctx.p("AGENTS.md")
        if not (claude_md.is_file() and agents_md.is_file()):
            return False
        return get_block(hio.read_text(claude_md), "habitree-claude") is not None and \
            get_block(hio.read_text(agents_md), "habitree") is not None
    except OSError:
        return False


def session_text(ctx, db, st):
    """세션 시작 때 AI에게 넣는 글(설정 언어 한 벌, 짧게). / Context injected at session start."""
    mode = ctx.get("guard.session_start", "auto")
    if mode == "off":
        return ""
    lang = ctx.lang
    parts = []
    if mode == "full" or (mode == "auto" and not _agents_loaded(ctx)):
        parts.append(t("start.full", lang, map=ctx.get("docs.map"), log=ctx.get("docs.log")))
        brief = db.brief(["global"], must_only=True, budget=ctx.get("guard.session_budget", 1500), lang=lang,
                         compact=True, skip_scopes=("work/cycle",))
        body = brief.split("\n", 1)[1].strip() if "\n" in brief else ""
        if body:
            parts.append(t("start.must", lang) + "\n" + body)
    else:
        parts.append(t("start.short", lang))
    parts.append(t("start.react", lang))
    d = delegate.active(st)
    if d:
        parts.append(t("start.delegated", lang, task=d.get("task", "")))
    return "\n\n".join(parts)


def quick_check(ctx):
    """Stop 때 빠른 점검: check.collect를 자동 검사·사용자 명령 없이. 오류만. / Fast check without auto/custom runs."""
    from . import check  # 문서로 정한 도우미: check.collect / documented helper
    qctx = Context(ctx.root, deep_merge(ctx.cfg, {"checks": {"custom": []}}), ctx.lang)
    findings = check.collect(qctx, no_auto=True)[0]
    return sorted((f for f in findings if f.level == "error"), key=lambda f: (f.id, f.path, f.line))


def _stop_extras(run, out, was_delegated):
    st, ctx, lang = run.state, run.ctx, run.lang
    stop = st.setdefault("stop", {"check_fp": "", "check_blocks": 0})
    if ctx.get("guard.stop_check", True) and not run.ev.stop_active and st.get("edits_since_check", 0) > 0:
        errors = quick_check(ctx)
        st["edits_since_check"] = 0
        if errors:
            fp = short("\n".join(f"{f.id}\0{f.path}" for f in errors), 12)
            if fp != stop.get("check_fp") and stop.get("check_blocks", 0) < (ctx.get("guard.stop_check_max", 3) or 3):
                stop["check_fp"] = fp
                stop["check_blocks"] = stop.get("check_blocks", 0) + 1
                items = "\n".join(f"- {f.id} {f.path}{':' + str(f.line) if f.line else ''}: {tr(f.msg, lang)}"
                                  for f in errors[:8])
                out.block.insert(0, t("check.block", lang, n=len(errors), items=items))
                out.user.append(t("check.user", lang, n=len(errors)))
        else:
            stop["check_fp"] = ""
    items = st.get("turn", [])
    st["turn"] = []
    if items and not was_delegated:
        lines = [t("summary.head", lang, n=len(items))]
        lines += [f"· {x.get('text', '')} ({x.get('rule')})" for x in items[:5]]
        lines.append(t("summary.tail", lang))
        out.user.append("\n".join(lines))
