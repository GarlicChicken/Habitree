"""guard: 작업 중 경고를 사람이 보고 다루는 명령. / See and steer the in-flight warnings.

  habitree guard status                  세션 상태와 경고 요약(기본: 가장 최근 세션)
  habitree guard explain <규칙 id>       감지 규칙이 무엇을 언제 왜 알리는지
  habitree guard off <규칙 id>           이 세션에서만 끄기('틀렸다'로 세지 않고 votes에 off로 따로 남김)
  habitree guard on <규칙 id>            다시 켜기
  habitree guard report                  끝 보고 미리 보기(대신 정한 것, 미뤄 둔 알림, 검증 실행)
  habitree guard delegate on|off|status  위임을 명령으로 켜고 끄기(--task, --boundary, --path)

세션은 --session으로 고르고, 없으면 가장 최근에 바뀐 세션을 쓴다.
"""
import json

from ..core import HabitreeError
from ..core import state as hstate
from ..core.i18n import tr
from ..core.ruledb import LEVEL_TEXT, RuleDB, rule_text, vote_stats
from ..core.timeutil import now_iso, show
from ..guard import delegate
from ..guard.detectors import DETECTORS

SUMMARY = {"ko": "작업 중 경고: 세션 상태, 규칙 설명, 세션별 끄기·켜기, 끝 보고 미리 보기, 위임",
           "en": "In-flight warnings: session status, rule explain, mute per session, report preview, delegation"}

OD_TEXT = {"skip": {"ko": "위임 중에는 알리지 않고 끝 보고에 모음", "en": "held for the end report while delegated"},
           "ask": {"ko": "위임 중에도 사용자 확인을 받음", "en": "asks the user even while delegated"},
           "nudge": {"ko": "위임 중에는 AI에게만 알림", "en": "tells only the AI while delegated"}}
AUD_TEXT = {"ai": {"ko": "AI에게 먼저(사용자는 답이 끝날 때 모아서 봄)", "en": "AI first (the user sees it at the end of the reply)"},
            "user": {"ko": "사용자에게 바로", "en": "the user, right away"},
            "both": {"ko": "AI와 사용자 둘 다", "en": "both the AI and the user"}}


def add_arguments(p):
    sub = p.add_subparsers(dest="action", metavar="<action>")

    def add(name, helptext):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("--session", help="세션 id(기본: 가장 최근) / session id (default: latest)")
        return s
    s = add("status", "세션 상태와 경고 요약 / session status")
    s.add_argument("--json", action="store_true")
    s = add("explain", "감지 규칙 설명 / explain a detection rule")
    s.add_argument("id")
    for name in ("off", "on"):
        s = add(name, "이 세션에서 끄기 / mute for this session" if name == "off" else "다시 켜기 / unmute")
        s.add_argument("id")
        s.add_argument("--why", default="")
    add("report", "끝 보고 미리 보기 / preview the end report")
    s = add("delegate", "위임 켜기·끄기·보기 / delegation on, off, status")
    s.add_argument("mode", choices=["on", "off", "status"])
    s.add_argument("--task", help="맡긴 작업 한 줄 / the delegated task in one line")
    s.add_argument("--boundary", action="append", default=[], help="지킬 경계(여러 번) / a boundary to keep")
    s.add_argument("--path", action="append", default=[], help="맡긴 범위의 경로(여러 번) / scope path")


def _say(lang, ko, en):
    print(ko if lang == "ko" else en)


def _sid(args, ctx, must=True):
    sid = getattr(args, "session", None) or hstate.latest(ctx.state_dir)
    if not sid and must:
        raise HabitreeError("세션 기록이 없습니다. 훅이 켜진 Claude Code 세션을 한 번 연 뒤 다시 실행하세요. / "
                            "No session state yet. Open a Claude Code session with the hooks on, then retry.")
    return sid


def _db(ctx):
    return RuleDB.load(ctx.p(ctx.get("rules.db")), ctx.lang)


def run(args, ctx):
    act = args.action or "status"
    if act == "status":
        return status(args, ctx)
    if act == "explain":
        return explain(args, ctx)
    if act in ("off", "on"):
        return mute(args, ctx, act)
    if act == "report":
        print(report_text(ctx, hstate.read(ctx.state_dir, _sid(args, ctx)) or {}))
        return 0
    if act == "delegate":
        return delegate_cmd(args, ctx)
    return 0


def status(args, ctx):
    lang = ctx.lang
    sid = _sid(args, ctx, must=False)
    data = hstate.read(ctx.state_dir, sid) if sid else None
    db = _db(ctx)
    detect_rules = [r for r in db.active() if r.get("detect")]
    if args.json:
        print(json.dumps({"session": sid, "state": data, "detect_rules": [r["id"] for r in detect_rules]},
                         ensure_ascii=False, indent=1))
        return 0
    if not detect_rules:
        _say(lang, "감지 규칙이 없습니다. `habitree init`을 다시 실행하면 work 꾸러미가 더해집니다.",
             "No detection rules. Run `habitree init` again to add the work pack.")
    if not data:
        _say(lang, "세션 기록이 아직 없습니다.", "No session state yet.")
        return 0
    ko = lang == "ko"
    print(("세션" if ko else "Session") + f": {sid}")
    print(("  시작 " if ko else "  started ") + show(data.get("started")) +
          (" · 마지막 " if ko else " · last ") + show(data.get("updated")))
    print(("  도구 호출 {c} · 수정 {e} · 검증 실행 {v} · 요청 {p}" if ko else
           "  tool calls {c} · edits {e} · verify runs {v} · prompts {p}").format(
        c=data.get("counter", 0), e=data.get("edits", 0), v=data.get("verify_runs", 0), p=data.get("turns", 0)))
    warned = {k: v.get("count", 0) for k, v in data.get("warned", {}).items() if v.get("count")}
    if warned:
        print(("  알림 " if ko else "  notes ") + ", ".join(f"{k} {n}" for k, n in sorted(warned.items())))
    for s in data.get("signals", [])[-5:]:
        print(f"    {show(s.get('at'))} [{s.get('level')}] {s.get('rule')}: {s.get('text', '')[:90]}")
    if data.get("off"):
        print(("  이 세션에서 끈 규칙: " if ko else "  muted this session: ") + ", ".join(data["off"]))
    d = delegate.active(data)
    if d:
        print(("  위임 중: " if ko else "  delegated: ") + f"\"{d.get('task', '')}\" · " +
              (f"도구 {d.get('tools', 0)}번 · 미뤄 둔 알림 {len(d.get('suppressed', []))}개" if ko else
               f"{d.get('tools', 0)} tool calls · {len(d.get('suppressed', []))} held notes"))
    return 0


def explain(args, ctx):
    lang = ctx.lang
    ko = lang == "ko"
    r = _db(ctx).find(args.id, lang)
    det = r.get("detect")
    print(f"{r['id']}  [{tr(LEVEL_TEXT[r.get('level', 'should')], lang)} · {r['scope']} · {r['aspect']}]")
    print("  " + rule_text(r, "rule", lang))
    print(("  이유: " if ko else "  why: ") + tr(r.get("why"), lang))
    if not det:
        _say(lang, "  감지 규칙이 아닙니다(작업 중에 알리지 않음).", "  Not a detection rule (no in-flight notes).")
        return 0
    # 훅이 아닌 명령이 쓰는 규칙(예: refactor)의 감지 이름은 훅 감지기 목록에 없어도 정상이다
    known = det.get("signal") in DETECTORS or det.get("event") not in (None, "", "SessionStart", "UserPromptSubmit",
                                                                        "PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop")
    print(("  감지: " if ko else "  detect: ") + f"{det.get('signal')}{'' if known else ' (?)'} · "
          f"{det.get('event', '')} · threshold {det.get('threshold', '-')} · stop_at {det.get('stop_at', '-')} · "
          f"{det.get('severity', 'info')} · {det.get('repeat', 'once_per_streak')}"
          + (f" · max {det['max_per_session']}" if det.get("max_per_session") else ""))
    if det.get("params"):
        print("  params: " + json.dumps(det["params"], ensure_ascii=False)[:300])
    print(("  누구에게: " if ko else "  audience: ") + tr(AUD_TEXT.get(det.get("audience", "ai"), AUD_TEXT["ai"]), lang))
    print(("  위임 중: " if ko else "  when delegated: ") +
          tr(OD_TEXT.get(r.get("on_delegate", "nudge"), OD_TEXT["nudge"]), lang))
    msg = r.get("message") or {}
    if msg.get("user"):
        print(("  사용자 문구: " if ko else "  user text: ") + tr(msg["user"], lang))
    if msg.get("ai"):
        print(("  AI 문구: " if ko else "  AI text: ") + tr(msg["ai"], lang))
    for i, s in enumerate(msg.get("suggest") or [], 1):
        print(f"    {i}. {tr(s, lang)}")
    st = vote_stats(r)
    offs = sum(1 for v in r.get("votes", []) if v.get("kind") == "off")
    print(("  반응: 맞았다 {u} · 틀렸다 {m} · 세션 끄기 {o}" if ko else "  votes: useful {u} · miss {m} · muted {o}").format(
        u=st["useful"], m=st["miss"], o=offs))
    _say(lang, f"  맞았으면 habitree rules hit {r['id']} --feedback \"…\" · 틀렸으면 habitree rules miss {r['id']} "
               f"--feedback \"…\" · 이 세션만 끄기 habitree guard off {r['id']}",
         f"  Useful: habitree rules hit {r['id']} --feedback \"…\" · wrong: habitree rules miss {r['id']} "
         f"--feedback \"…\" · mute: habitree guard off {r['id']}")
    return 0


def mute(args, ctx, act):
    lang = ctx.lang
    db = _db(ctx)
    r = db.find(args.id, lang)
    sid = _sid(args, ctx)
    with hstate.session(ctx.state_dir, sid) as st:
        off = st.setdefault("off", [])
        if act == "off" and r["id"] not in off:
            off.append(r["id"])
        elif act == "on" and r["id"] in off:
            off.remove(r["id"])
    if act == "off":
        # 세션 끄기는 '틀렸다'(miss)로 세지 않는다. 바빠서 끈 것과 틀려서 끈 것을 나누려고 따로 남긴다.
        r.setdefault("votes", []).append({"at": now_iso(), "kind": "off", "note": args.why or f"session {sid}"})
        doc = ctx.get("rules.doc")
        db.save(ctx.p(doc) if doc else None, lang)
    _say(lang, f"{'끔' if act == 'off' else '켬'}: {r['id']} (세션 {sid})", f"{act}: {r['id']} (session {sid})")
    return 0


def report_text(ctx, data):
    """끝 보고 미리 보기. / Preview of the end report."""
    lang = ctx.lang
    ko = lang == "ko"
    lines = []
    d = delegate.active(data) or (data.get("delegations") or [None])[-1]
    if d:
        state = ("진행 중" if ko else "active") if d.get("active") else \
            (f"끝남({d.get('end_reason', '')})" if ko else f"ended ({d.get('end_reason', '')})")
        lines.append(("맡긴 작업: " if ko else "Delegated task: ") + f"\"{d.get('task', '')}\" · {state}")
        for b in d.get("boundaries", []):
            lines.append(("  경계: " if ko else "  boundary: ") + b.get("text", ""))
        held = d.get("suppressed", [])
        lines.append((f"  미뤄 둔 알림 {len(held)}개" if ko else f"  held notes: {len(held)}"))
        for x in held[:10]:
            lines.append(f"    · {x.get('text', '')} ({x.get('rule')})")
    else:
        lines.append("맡긴 작업이 없습니다." if ko else "No delegated task.")
    sigs = data.get("signals", [])
    lines.append((f"이번 세션 알림 {len(sigs)}개" if ko else f"Notes this session: {len(sigs)}"))
    for s in sigs[-8:]:
        lines.append(f"  · [{s.get('level')}] {s.get('text', '')[:100]} ({s.get('rule')})")
    verify = ctx.get("verify") or {}
    lines.append((f"검증 실행 {data.get('verify_runs', 0)}번 (등록: {', '.join(verify) or '없음'})" if ko else
                  f"Verify runs: {data.get('verify_runs', 0)} (registered: {', '.join(verify) or 'none'})"))
    lines.append(("끝 보고에 넣을 것: 대신 정한 것마다 무엇·왜·다른 안·되돌리는 법, 실행한 검사와 결과, 확인이 필요한 것." if ko else
                  "The end report covers: each decision made (what, why, alternative, how to undo), checks run "
                  "with results, and anything that needs confirmation."))
    return "\n".join(lines)


def delegate_cmd(args, ctx):
    lang = ctx.lang
    if args.mode == "status":
        data = hstate.read(ctx.state_dir, _sid(args, ctx)) or {}
        d = delegate.active(data)
        if not d:
            _say(lang, "위임 중이 아닙니다.", "Not delegated.")
            return 0
        print(json.dumps({k: d.get(k) for k in ("task", "granted_by", "started", "paths", "boundaries", "tools")},
                         ensure_ascii=False, indent=1))
        return 0
    sid = _sid(args, ctx)
    with hstate.session(ctx.state_dir, sid) as st:
        if args.mode == "off":
            ended = delegate.end(st, "command")
            _say(lang, "위임을 끝냈습니다." if ended else "위임 중이 아니었습니다.",
                 "Delegation ended." if ended else "Was not delegated.")
            return 0
        delegate.end(st, "replaced")
        d = delegate.start(st, "", args.task or "", by="command", scope_paths=args.path, task=args.task or "",
                           bounds=args.boundary)
    _say(lang, f"위임을 켰습니다(세션 {sid}): \"{d['task']}\". 위험한 일은 위임 중에도 확인을 받습니다.",
         f"Delegation on (session {sid}): \"{d['task']}\". Risky actions still ask for confirmation.")
    return 0
