"""audit: 끝난 세션 기록에서 토큰·비용·도구 호출과 낭비 신호를 본다. 부를 때만 돈다. / Analyze finished sessions.

  habitree audit                       최근 10개 세션 요약
  habitree audit --last 3 | --since 2026-10-01 | --session 0cb25a02
  habitree audit --detail              세션별·모델별·신호별 자세히
  habitree audit --suggest             신호 → 고정 처방 → 규칙 명령 초안(실행하지 않음), 자동 메모리 받은편지함
  habitree audit --json                전부(시각은 UTC)

레코드의 cwd가 이 루트(또는 그 아래)인 세션만 본다. 기록은 이 컴퓨터 안에서만 읽고, 대화 글·도구 입력·
결과 글은 보고서에 넣지 않는다. 토큰은 응답 하나를 한 번만 센다. 자세히: docs/spec/audit.md
"""
import json
from datetime import datetime

from .. import sessions
from ..core import HabitreeError, vendors
from ..core.i18n import tr
from ..core.ruledb import RuleDB, load_pack
from ..core.timeutil import now_iso, show
from ..sessions import signals
from ..sessions.claude import feedback_memories
from ..sessions.usage import Pricer, summarize

SUMMARY = {"ko": "끝난 세션 기록 분석: 토큰·비용, 낭비 신호, 규칙 후보(--suggest)",
           "en": "Analyze finished sessions: tokens, cost, waste signals, rule candidates (--suggest)"}
DEFAULT_LAST = 10
LEVEL = {"warn": {"ko": "경고", "en": "warn"}, "info": {"ko": "알림", "en": "info"}}


def add_arguments(p):
    p.add_argument("--session", help="세션 id(앞부분) / session id or prefix")
    p.add_argument("--last", type=int, help=f"최근 N개(기본 {DEFAULT_LAST}) / most recent N")
    p.add_argument("--since", help="이 지역 날짜(YYYY-MM-DD)부터 / from this local date")
    p.add_argument("--detail", action="store_true", help="세션별·모델별·신호별 자세히 / full breakdown")
    p.add_argument("--suggest", action="store_true", help="처방과 규칙 후보 / prescriptions and rule candidates")
    p.add_argument("--json", action="store_true", help="JSON(시각은 UTC) / JSON output (UTC)")
    p.add_argument("--tool", default="claude", choices=sorted(sessions.ADAPTERS), help="기록을 남긴 도구 / source")
    p.add_argument("--claude-dir", help="Claude Code 설정 폴더(기본 CLAUDE_CONFIG_DIR 또는 ~/.claude) / config dir")


def select(found, args, lang):
    rows = sorted(found, key=lambda s: s.started.isoformat() if s.started else "")
    if args.session:
        rows = [s for s in rows if s.id.startswith(args.session)]
        if not rows:
            raise HabitreeError((f"이 프로젝트에 없는 세션: {args.session}" if lang == "ko"
                                 else f"No such session in this project: {args.session}"))
    if args.since:
        try:
            start = datetime.strptime(args.since, "%Y-%m-%d").astimezone()
        except ValueError:
            raise HabitreeError("--since: YYYY-MM-DD")
        rows = [s for s in rows if s.started and s.started >= start]
    last = args.last if args.last is not None else (None if args.session or args.since else DEFAULT_LAST)
    return rows[-last:] if last else rows


def _explore(ctx, db, table):
    """task/explore 칸과 그 칸의 모델(설정 models.vendor). 규칙 DB에 없으면 기본 꾸러미로. / Explore cell."""
    from ..core.modelpolicy import policy
    if db is None or "task/explore" not in db.scopes:
        db = RuleDB({"scopes": {}, "aspects": {}, "contexts": {}, "rules": []})
        db.merge_pack(load_pack("base"))
        db.merge_pack(load_pack("task"))
    try:
        cell = policy(db, "task/explore")["cell"]
        return vendors.cell_str(cell), vendors.resolve(cell, ctx.get("models.vendor") or "anthropic", table)["model"]
    except HabitreeError:
        return None, None


def analyze(ctx, args):
    """보고 자료(dict). / Build the report data."""
    mod = sessions.ADAPTERS[args.tool]
    if not mod.SUPPORTED:
        raise HabitreeError(tr(mod.REASON, ctx.lang))
    scan = mod.scan(str(ctx.root), claude_dir=args.claude_dir)
    chosen = select(scan.sessions.values(), args, ctx.lang)
    table = vendors.load(ctx)
    pricer = Pricer(table)
    db_path = ctx.p(ctx.get("rules.db"))
    try:
        db = RuleDB.load(db_path, ctx.lang) if db_path.is_file() else None
    except HabitreeError:
        db = None
    cell, model = _explore(ctx, db, table)
    hits = signals.detect(chosen, signals.Env(ctx.root, pricer, db, cell, model))
    rows, models, total = summarize(chosen, pricer)
    data = {"generated_at": now_iso(), "root": str(ctx.root), "tool": args.tool,
            "source": {"dir": str(mod.config_dir(args.claude_dir)), "folders": len(scan.folders), "files": scan.files,
                       "sessions": len(scan.sessions), "other_cwd_sessions": scan.other_cwd,
                       "unknown_types": scan.unknown_types, "bad_lines": scan.bad_lines,
                       "duplicate_lines": scan.duplicate_lines},
            "sessions": rows, "models": models, "totals": total, "signals": hits,
            "unpriced_models": sorted(pricer.unpriced), "partial_models": sorted(m for m in pricer.partial if m),
            "prices_checked": {v: d.get("checked") for v, d in table["vendors"].items()}}
    if args.suggest:
        data["suggest"] = signals.suggestions(hits, db, ctx.lang)
        data["inbox"] = signals.inbox(feedback_memories(scan.memory_dirs), db, ctx.lang)
        data["rule_db"] = db is not None
    return data


def run(args, ctx):
    data = analyze(ctx, args)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        render(data, ctx.lang, args.detail)
    return 0


def _n(v):
    return f"{int(v or 0):,}"


def _usd(v):
    return "-" if v is None else (f"${v:,.4f}" if abs(v) < 1 else f"${v:,.2f}")


def _tok(t, ko):
    return (f"입력 {_n(t.get('input'))} · 출력 {_n(t.get('output'))} · 캐시 읽기 {_n(t.get('cache_read'))} · "
            f"캐시 쓰기 {_n(t.get('cache_write'))}" if ko else
            f"in {_n(t.get('input'))} · out {_n(t.get('output'))} · cache read {_n(t.get('cache_read'))} · "
            f"cache write {_n(t.get('cache_write'))}")


def _line(h, ko):
    e, bits = h["evidence"], [h["session"][:8]]
    bits += [str(e[k]) for k in ("tool", "agent_type", "path") if e.get(k)]
    if h["signal"] == "big_output":
        how = ("기록으로 잼" if ko else "measured") if e.get("measured") else ("추정" if ko else "estimate")
        bits.append(f"~{_n(h['tokens'])} tok ({how}) × {e.get('later')}")
    elif h["signal"] == "rewritten_script":
        bits.append(", ".join(e.get("names", [])))
    elif h["signal"] == "repeat_correction":
        bits.append(", ".join(e.get("markers", [])))
    elif h["signal"] == "expensive_simple":
        bits.append(", ".join(e.get("models", [])))
    if h["count"] > 1:
        bits.append(f"{h['count']}x")
    if h.get("saving_usd") is not None:
        bits.append((f"{e.get('target')}이면 약 {_usd(h['saving_usd'])} 적음(추정)" if ko else
                     f"~{_usd(h['saving_usd'])} less on {e.get('target')} (estimate)"))
    elif h.get("cost_usd") is not None:
        bits.append(_usd(h["cost_usd"]))
    return " · ".join(bits)


def render(data, lang, detail=False):
    ko, src, t = lang == "ko", data["source"], data["totals"]
    print(("세션 기록 분석: " if ko else "Session audit: ") + data["root"])
    if not data["sessions"]:
        print("  " + (f"이 프로젝트의 세션 기록이 없습니다({src['dir']}). 다른 위치면 --claude-dir." if ko else
                      f"No session records for this project ({src['dir']}). Use --claude-dir if elsewhere."))
        return
    first, last = data["sessions"][0]["started"], data["sessions"][-1]["ended"]
    cost = _usd(t["cost_usd"]) + ("" if t["complete"] else ("(가격 아는 모델만)" if ko else " (priced models only)"))
    print(("  세션 {s}개 ({a} ~ {b}) · 요청 {r} · 도구 호출 {c} · {cost}" if ko else
           "  {s} sessions ({a} to {b}) · {r} requests · {c} tool calls · {cost}").format(
        s=len(data["sessions"]), a=show(first)[:16], b=show(last)[:16], r=_n(t["requests"]), c=_n(t["tool_calls"]),
        cost=cost))
    print("  " + _tok(t["tokens"], ko))
    print("  " + " · ".join(f"{m} {_usd(v['cost_usd']) if v['cost_usd'] is not None else ('가격 모름' if ko else 'no price')}"
                            for m, v in list(data["models"].items())[:3]))
    if src["unknown_types"]:
        print(("  [알림] 모르는 레코드 형식(세지 않음): " if ko else "  [info] unknown record types (not counted): ")
              + ", ".join(f"{k} {v}" for k, v in src["unknown_types"].items()))
    if detail:
        print()
        for s in data["sessions"]:
            print(f"  {s['id'][:8]} {show(s['started'])} · " + (
                f"요청 {_n(s['requests'])}(기록 줄 {_n(s['lines'])}) · 도구 {_n(s['tool_calls'])} · "
                f"서브에이전트 {s['subagents']} · {_usd(s['cost_usd'])}" if ko else
                f"{_n(s['requests'])} requests ({_n(s['lines'])} lines) · {_n(s['tool_calls'])} tools · "
                f"{s['subagents']} subagents · {_usd(s['cost_usd'])}"))
        print()
        for m, v in data["models"].items():
            print(f"  {m}: {_tok(v, ko)} · {_usd(v['cost_usd'])}")
        print("  " + " · ".join(f"{k} {v}" for k, v in list(t["tools"].items())[:10]))
    by = {}
    for h in data["signals"]:
        by.setdefault(h["signal"], []).append(h)
    print()
    print("낭비 신호" if ko else "Waste signals")
    if not by:
        print("  " + ("찾은 신호가 없습니다." if ko else "None found."))
    for name in signals.ORDER:
        hs = sorted(by.get(name, []), key=lambda h: -(h.get("cost_usd") or h.get("saving_usd") or 0))
        if not hs:
            continue
        meta, total_cost = signals.SIGNALS[name], sum(h.get("cost_usd") or 0 for h in hs)
        money = f" · {_usd(total_cost)}" if total_cost and name != "expensive_simple" else ""
        print(f"  [{tr(LEVEL[meta['severity']], lang)}] {tr(meta['title'], lang)} ({name}) "
              + (f"{len(hs)}건" if ko else f"{len(hs)} hits") + money)
        for h in hs[:(5 if detail else 1)]:
            print("      " + _line(h, ko))
    print()
    print(("비용은 기록의 토큰 × 대응표 단가(확인일 {c})로 낸 추정이며 청구서가 아닙니다." if ko else
           "Costs are recorded tokens × vendor table prices (checked {c}); an estimate, not a bill.").format(
        c=", ".join(sorted(set(data["prices_checked"].values())))))
    if "suggest" in data:
        render_suggest(data, ko)
    elif data["signals"]:
        print(("자세히: --detail · 처방과 규칙 후보: --suggest · 전부: --json" if ko else
               "More: --detail · prescriptions and rule candidates: --suggest · everything: --json"))


def render_suggest(data, ko):
    print()
    print("처방과 규칙 후보 (반복된 것부터 · 실행하지 않음)" if ko else "Prescriptions and rule candidates (most repeated first; not run)")
    if not data["rule_db"]:
        print("  " + ("규칙 DB가 없어 모두 새 규칙 초안입니다(habitree init)." if ko else "No rule DB; all drafts are new rules (habitree init)."))
    for i, s in enumerate(data["suggest"], 1):
        print(f"  {i}. {s['title']} · " + (f"세션 {s['sessions']}개 · {s['count']}건" if ko else
                                           f"{s['sessions']} sessions · {s['count']} hits"))
        print("     " + " → ".join(s["do"]))
        if s["rule"]:
            print(("     기존 규칙 " if ko else "     existing rule ") + f"{s['rule']} ({s['match']})")
        for cmd in s["commands"]:
            print("     $ " + cmd)
    inbox = data["inbox"]
    print()
    print((f"규칙 후보 받은편지함 (자동 메모리 feedback {sum(g['count'] for g in inbox)}개, 보여 주기만 함)" if ko else
           f"Rule candidate inbox (auto memory, {sum(g['count'] for g in inbox)} feedback notes, shown only)"))
    for g in inbox:
        for m in g["memories"]:
            print(f"  - {m['name']}: {m['description']}")
        for cmd in g["commands"]:
            print("     $ " + cmd)
