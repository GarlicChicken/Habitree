"""models: 작업 유형별 모델 칸(등급·강도)을 보고, 고르고, 올리고, 기록하고, 내보낸다. / Model allocation.

  habitree models                                   작업별 칸과 회사별 대응표
  habitree models show task/code                    작업 하나: 회사별 모델·강도·가격
  habitree models pick explore [--vendor openai] [--json]
  habitree models escalate task/code --from mid:medium --signal confident_wrong [--attempt 2]
  habitree models record task/code --result quality_fail [--cell mid:medium] [--note "…"]
  habitree models tune [--dry-run]                  최근 기록으로 기본 칸 올림(내림은 제안만)
  habitree models set task/explore --cell low:low --why "…"
  habitree models export claude|codex|aider|litellm|opencode [--write]
  habitree models check                             단종 예정·하한·가격 확인일

정책은 규칙 DB의 task 범위(꾸러미 task)에, 회사별 실제 모델은 대응표(core/vendors.py)에 있다.
라우터를 직접 만들지 않고, 각 도구의 설정을 정책 하나에서 만들어 준다(docs/spec/models.md).
"""
import json
import os
import shlex
import subprocess
import sys
import unicodedata

from ..core import HabitreeError
from ..core import io as hio
from ..core import vendors
from ..core.i18n import tr
from ..core.modelpolicy import (AGENTS_DIR, RESULTS, SIGNALS, agent_file, agent_model_value, escalate, findings,
                                fm_get, fm_set, load_db, normalize_task, policy, read_events, record, set_cell,
                                setting, task_scopes, tune, verify_names, verify_spec)
from ..core.paths import rel
from ..core.timeutil import local_date
from ..core.vendors import TIERS, cell_key, cell_str, parse_cell

SUMMARY = {"ko": "모델 배분: 작업 유형별 (등급, 강도) 칸, 회사별 모델·가격, 승격 규칙, 도구 설정 내보내기",
           "en": "Model allocation: (tier, effort) cells per task type, vendor models and prices, escalation, exports"}

TARGETS = ("claude", "codex", "aider", "litellm", "opencode")
LEVEL_TEXT = {"error": {"ko": "오류", "en": "error"}, "warn": {"ko": "경고", "en": "warning"},
              "info": {"ko": "알림", "en": "notice"}}


def add_arguments(p):
    sub = p.add_subparsers(dest="action", metavar="<action>")
    s = sub.add_parser("show", help="작업별 칸과 회사별 모델·가격 / cells, vendor models and prices")
    s.add_argument("task", nargs="?")
    k = sub.add_parser("pick", help="쓸 모델 ID와 강도 / model ID and effort to use")
    k.add_argument("task")
    k.add_argument("--vendor")
    k.add_argument("--json", action="store_true")
    e = sub.add_parser("escalate", help="실패 신호 → 다음 칸 / next cell after a failure signal")
    e.add_argument("task")
    e.add_argument("--from", dest="from_cell", help="실패한 칸 tier:effort(기본: 그 작업의 칸) / failed cell")
    e.add_argument("--signal", required=True, choices=SIGNALS)
    e.add_argument("--attempt", type=int, default=1, help="방금 실패한 시도 번호(1부터) / attempt number that failed")
    e.add_argument("--vendor")
    e.add_argument("--json", action="store_true")
    r = sub.add_parser("record", help="결과 한 줄 기록 / record one outcome")
    r.add_argument("task")
    r.add_argument("--result", required=True, choices=RESULTS)
    r.add_argument("--cell", help="쓴 칸 tier:effort(기본: 그 작업의 칸) / cell used")
    r.add_argument("--note", default="")
    t = sub.add_parser("tune", help="기록으로 기본 칸 조정(올림만 바로, 내림은 제안) / tune default cells")
    t.add_argument("--dry-run", action="store_true")
    st = sub.add_parser("set", help="사람이 칸을 정함(이력이 남음) / set a cell by hand, with history")
    st.add_argument("task")
    st.add_argument("--cell", required=True)
    st.add_argument("--why", required=True)
    x = sub.add_parser("export", help="도구 설정 만들기 / generate tool settings")
    x.add_argument("target", choices=TARGETS)
    x.add_argument("--vendor")
    x.add_argument("--write", action="store_true", help="claude: 에이전트 파일에 쓴다(없으면 미리 보기) / write agent files")
    sub.add_parser("check", help="단종 예정·하한·가격 확인일 / deprecations, floors, price dates")


# ── 출력 도우미 · Output helpers ──

def _t(ctx, ko, en):
    return ko if ctx.lang == "ko" else en


def _width(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def _pad(s, n):
    s = str(s)
    return s + " " * max(1, n - _width(s))


def _usd(x):
    return "?" if x is None else f"{x:g}"


def _price3(p):
    return f"{_usd(p['input'])} / {_usd(p['output'])} / {_usd(p['cache_read'])}" if p else "?"


def _verify_text(ctx, pol, names):
    if not pol["verify"]:
        return _t(ctx, "없음(자동 승격 안 함)", "none (no automatic escalation)")
    if not names:
        return _t(ctx, f"{', '.join(pol['verify'])} · 설정 verify에 명령이 없음(자동 승격 안 함)",
                  f"{', '.join(pol['verify'])} · no matching verify command in the config (no automatic escalation)")
    return ", ".join(names)


def _context(ctx):
    db = load_db(ctx)
    table = vendors.load(ctx)
    return db, table


# ── show ──

def show_all(ctx, db, table):
    lang = ctx.lang
    print(_t(ctx, "작업별 모델 칸 (등급:강도)", "Model cells per task (tier:effort)"))
    print("  " + _pad(_t(ctx, "작업", "task"), 28) + _pad(_t(ctx, "기본 칸", "default"), 14)
          + _pad(_t(ctx, "하한", "floor"), 14) + _pad(_t(ctx, "승격 상한", "cap"), 14) + _t(ctx, "검증", "verify"))
    for s in task_scopes(db):
        try:
            pol = policy(db, s)
        except HabitreeError:
            continue
        print("  " + _pad(s, 28) + _pad(cell_str(pol["cell"]), 14) + _pad(cell_str(pol["floor"]), 14)
              + _pad(cell_str(pol["max_cell"]), 14) + (", ".join(pol["verify"]) or "-"))
    print("\n" + _t(ctx, "회사별 대응표 (USD / 100만 토큰: 입력 / 출력 / 캐시 읽기)",
                    "Vendor table (USD per million tokens: input / output / cache read)"))
    for vname, v in table["vendors"].items():
        print(f"  {vname} ({v['name']}, {_t(ctx, '확인일', 'checked')} {v['checked']})")
        for tier in reversed(TIERS):
            slot = v["tiers"].get(tier)
            if isinstance(slot, dict):
                print("    " + _pad(tier, 6) + f"→ {slot['tier']}:{slot.get('effort', '')}  {tr(slot.get('note', ''), lang)}")
            elif slot:
                print("    " + _pad(tier, 6) + _pad(slot, 26) + _price3(vendors.price(slot, table)))
            else:
                print("    " + _pad(tier, 6) + "-")
    print("\n" + _t(ctx, "작업 하나 자세히: habitree models show <작업> · 고르기: habitree models pick <작업>",
                    "One task in detail: habitree models show <task> · choose: habitree models pick <task>"))


def show_task(ctx, db, table, name):
    lang = ctx.lang
    task = normalize_task(db, name, lang)
    pol = policy(db, task)
    lv = _t(ctx, "필수(하한)", "must (floor)") if pol["level"] == "must" else _t(ctx, "권장", "should")
    print(f"{task} · {_t(ctx, '칸', 'cell')} {cell_str(pol['cell'])} ({pol['rule']}, {lv})")
    print(f"  {_t(ctx, '규칙', 'rule')}: {tr(pol['text'], lang)}")
    print(f"  {_t(ctx, '근거', 'why')}: {tr(pol['why'], lang)}")
    print(f"  {_t(ctx, '하한', 'floor')}: {cell_str(pol['floor'])} · {_t(ctx, '자동 승격 상한', 'escalation cap')}: "
          f"{cell_str(pol['max_cell'])} · {_t(ctx, '검증', 'verify')}: {_verify_text(ctx, pol, verify_names(ctx, pol))}")
    print("  " + _t(ctx, "회사별 (강도 값 · USD/100만 토큰 입력/출력/캐시 읽기)",
                    "per vendor (effort value · USD per million tokens input/output/cache read)"))
    for vname in table["vendors"]:
        try:
            r = vendors.resolve(pol["cell"], vname, table)
        except HabitreeError as e:
            print("    " + _pad(vname, 11) + str(e))
            continue
        print("    " + _pad(vname, 11) + _pad(r["model"], 24) + _pad(r["effort_value"], 9) + _price3(r["price"]))


# ── pick ──

def pick_data(ctx, db, table, name, vendor):
    task = normalize_task(db, name, ctx.lang)
    pol = policy(db, task)
    r = vendors.resolve(pol["cell"], vendor, table)
    names = verify_names(ctx, pol)
    return {"task": task, "cell": cell_str(pol["cell"]), "vendor": vendor, "model": r["model"],
            "model_name": r["model_name"], "aliases": r["aliases"], "pinned": r["pinned"],
            "effort": pol["cell"]["effort"], "effort_param": r["effort_param"], "effort_value": r["effort_value"],
            "reason": r["reason"], "rule": pol["rule"], "level": pol["level"], "why": pol["why"],
            "floor": cell_str(pol["floor"]) if pol["floor"] else None, "max_cell": cell_str(pol["max_cell"]),
            "verify": names, "auto_escalate": bool(names) and not pol["risky"], "price": r["price"],
            "checked": r["checked"]}


def cmd_pick(args, ctx, db, table):
    lang = ctx.lang
    vendor = args.vendor or setting(ctx, "vendor")
    d = pick_data(ctx, db, table, args.task, vendor)
    if args.json:
        out = dict(d)
        out["reason"] = tr(d["reason"], lang)
        out["why"] = tr(d["why"], lang)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    print(f"{d['task']} → {d['cell']}")
    print(f"  {_t(ctx, '모델', 'model')}: {d['model']} ({d['model_name']}, {vendor})")
    print(f"  {_t(ctx, '강도', 'effort')}: {d['effort_param']} = {d['effort_value']}")
    print(f"  {_t(ctx, '이유', 'reason')}: {tr(d['reason'], lang)}")
    print(f"  {_t(ctx, '근거', 'why')}: {tr(d['why'], lang)} ({d['rule']})")
    pol = policy(db, d["task"])
    print(f"  {_t(ctx, '하한', 'floor')}: {d['floor'] or '-'} · {_t(ctx, '자동 승격 상한', 'escalation cap')}: "
          f"{d['max_cell']} · {_t(ctx, '검증', 'verify')}: {_verify_text(ctx, pol, d['verify'])}")
    print(f"  {_t(ctx, '가격(USD/100만 토큰, 입력/출력/캐시 읽기)', 'price (USD per million tokens, input/output/cache read)')}: "
          f"{_price3(d['price'])} ({_t(ctx, '확인일', 'checked')} {d['checked']})")
    return 0


# ── escalate ──

def cmd_escalate(args, ctx, db, table):
    lang = ctx.lang
    task = normalize_task(db, args.task, lang)
    pol = policy(db, task)
    cur = parse_cell(args.from_cell, lang) if args.from_cell else pol["cell"]
    names = verify_names(ctx, pol)
    res = escalate(pol, cur, args.signal, args.attempt, names, max_steps=setting(ctx, "escalate.max_steps") or 2,
                   max_attempts=setting(ctx, "escalate.max_attempts") or 4)
    vendor = args.vendor or setting(ctx, "vendor")
    res["vendor"] = vendor
    res["verify"] = names
    if res["to"]:
        r = vendors.resolve(res["to"], vendor, table)
        res["model"], res["effort_value"] = r["model"], r["effort_value"]
    if res["action"] == "fallback":
        res["alternatives"] = [{"vendor": a["vendor"], "model": a["model"], "effort_value": a["effort_value"]}
                               for a in vendors.same_tier_alternatives(table, res["to"], vendor)]
    code = 3 if res["action"] == "human" else 0
    if args.json:
        out = dict(res)
        out["reason"] = tr(res["reason"], lang)
        out["advice"] = [tr(a, lang) for a in res["advice"]]
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return code
    label = {"retry": _t(ctx, "같은 칸으로 다시", "retry in the same cell"),
             "fallback": _t(ctx, "같은 등급의 다른 모델로", "switch to another model at the same tier"),
             "escalate": _t(ctx, "올림", "escalate"), "human": _t(ctx, "사람에게 넘김", "hand over to a person")}
    head = f"{task} · {res['from']} · {args.signal} · {_t(ctx, '시도', 'attempt')} {res['attempt']}"
    print(head)
    line = f"  → {label[res['action']]}"
    if res["to"]:
        line += f": {res['to']} ({res['model']}, {res['effort_value']})"
    print(line)
    print(f"  {tr(res['reason'], lang)}")
    for a in res.get("alternatives", []):
        print(f"    {a['vendor']}: {a['model']} ({a['effort_value']})")
    for a in res["advice"]:
        print(f"  - {tr(a, lang)}")
    if res["action"] != "human":
        print("  " + _t(ctx, f"결과를 남기기: habitree models record {task} --result pass|quality_fail|infra_fail "
                             f"--cell {res['to'] or res['from']}",
                        f"Record the outcome: habitree models record {task} --result pass|quality_fail|infra_fail "
                        f"--cell {res['to'] or res['from']}"))
    return code


# ── record · tune · set ──

def cmd_record(args, ctx, db):
    task = normalize_task(db, args.task, ctx.lang)
    pol = policy(db, task)
    cell = parse_cell(args.cell, ctx.lang) if args.cell else pol["cell"]
    e = record(ctx, task, args.result, cell, args.note, "record")
    print(_t(ctx, "기록했습니다", "Recorded") + f": {task} {e['result']} ({e['cell']})")
    return 0


def _doc_path(ctx):
    doc = ctx.get("rules.doc")
    return ctx.p(doc) if doc else None


def cmd_tune(args, ctx, db):
    t = setting(ctx, "tune") or {}
    rep = tune(db, read_events(ctx), window=t.get("window", 20), min_runs=t.get("min_runs", 10),
               up_ratio=t.get("up_ratio", 0.2), down_ratio=t.get("down_ratio", 0.05), apply=not args.dry_run)
    if not rep:
        print(_t(ctx, "기록이 없습니다. habitree models record 또는 habitree verify --task로 결과를 남기세요.",
                 "No records yet. Record outcomes with habitree models record or habitree verify --task."))
        return 0
    raised = [x for x in rep if x["action"] == "raised"]
    if raised and not args.dry_run:
        db.save(_doc_path(ctx), ctx.lang)
    for x in rep:
        stat = f"{x['fails']}/{x['runs']}"
        if x["action"] == "raised":
            msg = _t(ctx, f"올림{'(미리 보기)' if args.dry_run else ''}: {x['task']} {x['from']} → {x['to']} "
                          f"(품질 실패 {stat} = {x['ratio']:.0%})",
                     f"raised{' (dry run)' if args.dry_run else ''}: {x['task']} {x['from']} → {x['to']} "
                     f"(quality failures {stat} = {x['ratio']:.0%})")
        elif x["action"] == "suggest_down":
            msg = _t(ctx, f"내려 볼 만함(제안만): {x['task']} {x['from']} → {x['to']} (품질 실패 {stat}). 바꾸려면 "
                          f"habitree models set {x['task']} --cell {x['to']} --why \"…\"",
                     f"could go lower (suggestion only): {x['task']} {x['from']} → {x['to']} (quality failures "
                     f"{stat}). To apply: habitree models set {x['task']} --cell {x['to']} --why \"…\"")
        elif x["action"] == "floor":
            msg = _t(ctx, f"하한이라 통계로 바꾸지 않음: {x['task']} {x['from']} (품질 실패 {stat})",
                     f"floor, not changed by statistics: {x['task']} {x['from']} (quality failures {stat})")
        elif x["action"] == "few":
            msg = _t(ctx, f"관측이 모자람: {x['task']} {x['from']} ({x['runs']}회, 조정은 "
                          f"{(setting(ctx, 'tune') or {}).get('min_runs', 10)}회부터)",
                     f"not enough runs: {x['task']} {x['from']} ({x['runs']}, tuning starts at "
                     f"{(setting(ctx, 'tune') or {}).get('min_runs', 10)})")
        elif x["action"] == "cap":
            msg = _t(ctx, f"상한이라 올리지 않음: {x['task']} {x['from']} (품질 실패 {stat}). 사람이 작업을 나누거나 칸을 정한다",
                     f"at the cap, not raised: {x['task']} {x['from']} (quality failures {stat}). A person should "
                     "split the task or set the cell")
        else:
            msg = _t(ctx, f"그대로: {x['task']} {x['from']} (품질 실패 {stat})",
                     f"kept: {x['task']} {x['from']} (quality failures {stat})")
        print("  " + msg)
    return 0


def cmd_set(args, ctx, db):
    lang = ctx.lang
    task = normalize_task(db, args.task, lang)
    new = parse_cell(args.cell, lang)
    rs = [r for r in db.active() if r["scope"] == task and r.get("cell")]
    pol = policy(db, task)
    rule = next((r for r in rs if r.get("level") != "must"), None) or (rs[0] if rs else None)
    if rule is None or rule.get("level") != "must":
        if pol["floor"] and cell_key(new) < cell_key(pol["floor"]):
            raise HabitreeError(_t(ctx, f"하한 {cell_str(pol['floor'])}({pol['floor_rule']})보다 낮게 둘 수 없습니다. "
                                        f"하한을 바꾸려면 그 범위에서 models set을 실행하세요.",
                                   f"Cannot go below the floor {cell_str(pol['floor'])} ({pol['floor_rule']}). "
                                   "Run models set on that scope to change the floor."))
    if rule is None:
        text = (f"{task} 작업은 `{cell_str(new)}` 칸(등급:강도)에서 시작한다." if lang == "ko"
                else f"{task} work starts at the `{cell_str(new)}` cell (tier:effort).")
        rule = db.add(task, "model", text, args.why, args.why, check_how=None, auto=True)
        rule["cell"] = dict(new)
        db.log_change(rule, f"cell: - → {cell_str(new)} (set: {args.why})")
    else:
        if cell_key(parse_cell(rule["cell"])) == cell_key(new):
            raise HabitreeError(_t(ctx, "바뀐 것이 없습니다.", "Nothing changed."))
        set_cell(db, rule, new, f"set: {args.why}")
        rule.setdefault("feedback", []).append({"date": local_date(), "note": args.why, "ref": "models set"})
    db.save(_doc_path(ctx), lang)
    print(_t(ctx, "정했습니다", "Set") + f": {task} → {cell_str(new)} ({rule['id']})")
    return 0


# ── export ──

def _cells_by_task(db):
    out = {}
    for s in task_scopes(db):
        try:
            pol = policy(db, s)
        except HabitreeError:
            continue
        out.setdefault(cell_str(pol["cell"]), []).append(s)
    return sorted(out.items(), key=lambda kv: cell_key(parse_cell(kv[0])))


def _q(s):
    """TOML·YAML 겹따옴표 글자. / Double-quoted string for TOML and YAML."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _res(db, table, task, vendor):
    if task not in db.scopes:
        task = "task"
    return policy(db, task), vendors.resolve(policy(db, task)["cell"], vendor, table)


def _named(table, vendor, tool, model):
    prefix = (table["vendors"][vendor].get("prefix") or {}).get(tool)
    return f"{prefix}/{model}" if prefix else model


def export_claude(args, ctx, db, table):
    agents = setting(ctx, "agents") or {}
    if not agents:
        print(_t(ctx, "설정 models.agents가 비어 있습니다. 예: \"models\": {\"agents\": {\"explorer\": \"task/explore\"}}",
                 "models.agents is empty in the config. Example: \"models\": {\"agents\": {\"explorer\": \"task/explore\"}}"))
        return 0
    if args.vendor and args.vendor != "anthropic":
        print(_t(ctx, "claude 대상은 anthropic 대응표만 씁니다.", "The claude target always uses the anthropic table."),
              file=sys.stderr)
    print(_t(ctx, "Claude Code 에이전트 파일(머리말의 model·effort만 고친다)",
             "Claude Code agent files (only model and effort in the front matter change)")
          + ("" if args.write else _t(ctx, ": 미리 보기", ": preview")))
    pending = 0
    for name, task_name in agents.items():
        try:
            task = normalize_task(db, task_name, ctx.lang)
        except HabitreeError as e:
            print(f"  {name}: {e}")
            continue
        pol = policy(db, task)
        r = vendors.resolve(pol["cell"], "anthropic", table)
        model, effort = agent_model_value(ctx, r), r["effort_value"]
        path = agent_file(ctx, name)
        if path is None:
            print(f"  {name}: " + _t(ctx, f"에이전트 파일이 없음({AGENTS_DIR}/{name}.md). 만들지 않는다",
                                     f"no agent file ({AGENTS_DIR}/{name}.md); not created"))
            continue
        relp = rel(ctx.root, path)
        text = hio.read_text(path)
        new = fm_set(text, {"model": model, "effort": effort})
        if new is None:
            print(f"  {relp}: " + _t(ctx, "머리말(---)이 없어 고치지 않음", "no front matter (---); left alone"))
            continue
        tag = f"[{task} → {cell_str(pol['cell'])}]"
        if new == text:
            print(f"  {relp} {tag}: " + _t(ctx, "그대로", "unchanged"))
            continue
        pending += 1
        none = _t(ctx, "(없음)", "(none)")
        diffs = [f"{k} {fm_get(text, k) or none} → {v}" for k, v in (("model", model), ("effort", effort))
                 if fm_get(text, k) != v]
        print(f"  {relp} {tag}: " + (" · ".join(diffs) or _t(ctx, "표기만 고침", "formatting only")))
        if args.write:
            hio.write_text(path, new)
    if pending and not args.write:
        print(_t(ctx, "쓰려면 --write", "Add --write to apply"))
    return 0


def _header(ctx, tool, vendor, table, ok, unknown):
    v = table["vendors"][vendor]
    lines = [f"# Habitree: models export {tool} · {vendor} ({_t(ctx, '대응표 확인일', 'table checked')} {v['checked']})",
             "# " + _t(ctx, "habitree가 만든 조각이다. 정책을 바꾸려면 규칙 DB(task 범위)를 고치고 다시 만든다.",
                       "Generated by habitree. To change the policy, edit the rule DB (task scopes) and regenerate.")]
    lines.append("# " + _t(ctx, "공식 문서로 확인한 형식(2026-10-28): ", "Format checked in official docs (2026-10-28): ") + ok)
    for u in unknown:
        lines.append("# " + _t(ctx, "확인하지 못함: ", "Not verified: ") + u)
    return lines


def export_codex(args, ctx, db, table):
    vendor = args.vendor or "openai"
    lines = _header(ctx, "codex", vendor, table,
                    _t(ctx, "프로필은 ~/.codex/<이름>.config.toml 파일 하나씩, 최상위 키로 쓰고 `codex --profile <이름>`으로 고른다. "
                            "review_model은 /review 전용 모델, plan_mode_reasoning_effort는 계획 모드 강도(설정 참조).",
                       "one file per profile at ~/.codex/<name>.config.toml with top-level keys, chosen with "
                       "`codex --profile <name>`; review_model is the /review model and plan_mode_reasoning_effort "
                       "the plan-mode effort (config reference)."),
                    [_t(ctx, "model_reasoning_effort가 받는 값은 모델과 클라이언트에 따라 다르다(설정 참조 문서).",
                        "accepted model_reasoning_effort values depend on the model and client (config reference)."),
                     _t(ctx, "review_model·plan_mode_reasoning_effort를 프로필 파일에서도 읽는지는 확인하지 못해 config.toml에 둔다.",
                        "whether profile files read review_model and plan_mode_reasoning_effort is unverified, so "
                        "they go in config.toml.")]
                    + ([] if vendor == "openai" else
                       [_t(ctx, "OpenAI가 아닌 회사는 config.toml의 model_provider 설정이 따로 필요하다.",
                           "vendors other than OpenAI need a model_provider entry in config.toml.")]))
    for c, tasks in _cells_by_task(db):
        r = vendors.resolve(c, vendor, table)
        name = "ht-" + c.replace(":", "-")
        lines += ["", f"# ---- ~/.codex/{name}.config.toml ----",
                  f"# {_t(ctx, '작업', 'tasks')}: {', '.join(tasks)}",
                  f"model = {_q(r['model'])}", f"model_reasoning_effort = {_q(r['effort_value'])}"]
    _, review = _res(db, table, "task/review", vendor)
    _, plan = _res(db, table, "task/plan", vendor)
    lines += ["", "# ---- ~/.codex/config.toml ----",
              f"# {_t(ctx, '/review 전용 모델', '/review model')} (task/review)", f"review_model = {_q(review['model'])}",
              f"# {_t(ctx, '계획 모드 강도(세션 모델은 그대로)', 'plan-mode effort (session model unchanged)')} (task/plan)",
              f"plan_mode_reasoning_effort = {_q(plan['effort_value'])}"]
    print("\n".join(lines))
    return 0


def _join_cmd(cmd):
    """셸 한 줄로 잇기(aider는 명령을 글 한 줄로 받는다). 이 컴퓨터의 셸 규칙을 따른다. / One shell line."""
    if os.name == "nt":
        return subprocess.list2cmdline(cmd)
    return " ".join(shlex.quote(c) for c in cmd)


def _verify_strings(ctx):
    out = {}
    for name, entry in (ctx.get("verify") or {}).items():
        try:
            cmd, _ = verify_spec(entry)
        except HabitreeError:
            continue
        out[name] = _join_cmd(cmd)
    return out


def export_aider(args, ctx, db, table):
    vendor = args.vendor or setting(ctx, "vendor")
    lines = _header(ctx, "aider", vendor, table,
                    _t(ctx, ".aider.conf.yml 키 model, weak-model, editor-model, reasoning-effort, test-cmd, lint-cmd, "
                            "auto-test. 파일은 홈, git 루트, 현재 폴더 순서로 읽는다(aider 설정 문서).",
                       ".aider.conf.yml keys model, weak-model, editor-model, reasoning-effort, test-cmd, lint-cmd, "
                       "auto-test; read from home, git root, then current folder (aider config docs)."),
                    [_t(ctx, "모델 이름의 회사 접두어(예: anthropic/…) 형식은 aider 문서로 확인하지 않았다.",
                        "the provider prefix in model names (e.g. anthropic/…) was not checked in aider docs."),
                     _t(ctx, "reasoning-effort 값이 회사 API로 그대로 넘어가는지 확인하지 못했다.",
                        "whether reasoning-effort passes through to the vendor API unchanged is unverified.")])
    main_pol, main = _res(db, table, "task/code", vendor)
    weak_pol, weak = _res(db, table, "task/commit-message", vendor)
    edit_pol, edit = _res(db, table, "task/code/clear-spec", vendor)
    lines += [f"model: {_q(_named(table, vendor, 'aider', main['model']))}  # task/code {cell_str(main_pol['cell'])}",
              f"weak-model: {_q(_named(table, vendor, 'aider', weak['model']))}  # task/commit-message "
              f"{cell_str(weak_pol['cell'])}",
              f"editor-model: {_q(_named(table, vendor, 'aider', edit['model']))}  # task/code/clear-spec "
              f"{cell_str(edit_pol['cell'])} ({_t(ctx, '--architect 모드에서만', '--architect mode only')})",
              f"reasoning-effort: {_q(main['effort_value'])}  # task/code"]
    cmds = _verify_strings(ctx)
    test = cmds.get("test") or (next(iter(cmds.values())) if cmds else None)
    shell = "Windows cmd" if os.name == "nt" else "POSIX sh"
    if test:
        lines += [f"test-cmd: {_q(test)}  # {_t(ctx, '설정 verify, 이은 방식', 'config verify, joined for')} {shell}",
                  "auto-test: true"]
    if cmds.get("lint"):
        lines.append(f"lint-cmd: {_q(cmds['lint'])}  # {_t(ctx, '설정 verify', 'config verify')}.lint")
    rest = [n for n in cmds if cmds[n] not in (test, cmds.get("lint"))]
    if rest:
        lines.append("# " + _t(ctx, "aider로 옮기지 않은 verify: ", "verify entries not carried over: ") + ", ".join(rest))
    if not cmds:
        lines.append("# " + _t(ctx, "설정 verify가 비어 있어 test-cmd를 쓰지 않았다.", "config verify is empty, so no test-cmd."))
    print("\n".join(lines))
    return 0


def export_opencode(args, ctx, db, table):
    vendor = args.vendor or setting(ctx, "vendor")
    unknown = [_t(ctx, "강도는 이 형식으로 내보내지 않는다(문서에서 확인하지 못함).",
                  "effort is not exported in this format (not found in the docs).")]
    if vendor == "google":
        unknown.append(_t(ctx, "회사 이름 google이 opencode에서 맞는지 확인하지 못했다.",
                          "the provider name google for opencode is unverified."))
    lines = _header(ctx, "opencode", vendor, table,
                    _t(ctx, "프로젝트 루트의 opencode.json, 모델은 \"회사/모델-id\", small_model은 제목 생성 같은 가벼운 일, "
                            "agent.<이름>.model(opencode 설정 문서). 아래 JSON만 파일에 넣는다.",
                       "opencode.json in the project root, models as \"provider/model-id\", small_model for light work "
                       "such as titles, agent.<name>.model (opencode config docs). Put only the JSON below in the file."),
                    unknown)
    _, main = _res(db, table, "task/code", vendor)
    _, small = _res(db, table, "task/commit-message", vendor)
    data = {"$schema": "https://opencode.ai/config.json",
            "model": _named(table, vendor, "opencode", main["model"]),
            "small_model": _named(table, vendor, "opencode", small["model"])}
    agents = {}
    for name, task_name in (setting(ctx, "agents") or {}).items():
        try:
            task = normalize_task(db, task_name, ctx.lang)
        except HabitreeError:
            continue
        r = vendors.resolve(policy(db, task)["cell"], vendor, table)
        agents[name] = {"model": _named(table, vendor, "opencode", r["model"])}
    if agents:
        data["agent"] = agents
    print("\n".join(lines))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def export_litellm(args, ctx, db, table):
    primary = args.vendor or setting(ctx, "vendor")
    others = [v for v in table["vendors"] if v != primary]
    lines = _header(ctx, "litellm", primary, table,
                    _t(ctx, "config.yaml의 model_list(model_name, litellm_params의 model·api_key \"os.environ/이름\"·"
                            "reasoning_effort), 장애 대체 fallbacks(LiteLLM 설정·안정성·추론 문서).",
                       "config.yaml model_list (model_name; litellm_params model, api_key \"os.environ/NAME\", "
                       "reasoning_effort) and outage fallbacks (LiteLLM config, reliability and reasoning docs)."),
                    [_t(ctx, "fallbacks는 문서에 router_settings와 litellm_settings 두 자리가 모두 나온다. 여기서는 router_settings에 둔다.",
                        "the docs show fallbacks under both router_settings and litellm_settings; this uses router_settings."),
                     _t(ctx, "OPENAI_API_KEY 환경 변수 이름은 이번에 읽은 문서에서 확인하지 못했다.",
                        "the OPENAI_API_KEY variable name was not seen in the pages read.")])
    lines.append("# " + _t(ctx, f"같은 칸의 다른 회사 모델을 장애 대체로 둔다(장애는 등급을 올리지 않는다): {', '.join(others) or '-'}",
                           f"other vendors at the same cell are outage fallbacks (outages never raise the tier): "
                           f"{', '.join(others) or '-'}"))
    lines += ["model_list:"]
    fallbacks = []
    for c, tasks in _cells_by_task(db):
        base = "ht-" + c.replace(":", "-")
        alts = []
        for v in [primary] + others:
            try:
                r = vendors.resolve(c, v, table)
            except HabitreeError:
                continue
            mname = base if v == primary else f"{base}-{v}"
            if v != primary:
                alts.append(mname)
            lines.append(f"  - model_name: {mname}" + (f"  # {', '.join(tasks)}" if v == primary else ""))
            lines.append("    litellm_params:")
            lines.append(f"      model: {_named(table, v, 'litellm', r['model'])}")
            env = table["vendors"][v].get("env_key")
            if env:
                lines.append(f"      api_key: {_q('os.environ/' + env)}")
            lines.append(f"      reasoning_effort: {_q(r['effort_value'])}")
        if alts:
            fallbacks.append({base: alts})
    if fallbacks:
        lines += ["", "router_settings:", "  fallbacks:"]
        lines += [f"    - {json.dumps(fb, ensure_ascii=False)}" for fb in fallbacks]
    print("\n".join(lines))
    return 0


def cmd_export(args, ctx, db, table):
    if args.write and args.target != "claude":
        print(_t(ctx, "이 대상은 표준 출력으로만 냅니다(--write는 claude 전용).",
                 "This target prints to standard output only (--write is for claude)."), file=sys.stderr)
    fn = {"claude": export_claude, "codex": export_codex, "aider": export_aider, "litellm": export_litellm,
          "opencode": export_opencode}[args.target]
    return fn(args, ctx, db, table)


# ── check ──

def cmd_check(args, ctx, table):
    lang = ctx.lang
    fs = findings(ctx, force=True)
    print(_t(ctx, "모델 점검", "Model check") + f": {ctx.root}")
    for f in fs:
        loc = f" {f['path']}" if f.get("path") else ""
        print(f"  [{tr(LEVEL_TEXT[f['level']], lang)}] {f['id']}{loc}\n      {tr(f['msg'], lang)}")
    if not fs:
        print("  " + _t(ctx, "쓰는 모델에 문제 없음", "No problems with the models in use"))
    days = setting(ctx, "deprecation_days")
    allm = vendors.deprecations(days, table)
    if allm:
        print("\n" + _t(ctx, f"대응표 전체에서 단종 예정·예고({days}일 안 또는 예고됨)",
                        f"Retiring or deprecated across the table (within {days} days or announced)"))
        for d in allm:
            left = "" if d["days_left"] is None else (f" ({d['days_left']}{_t(ctx, '일', ' days')})")
            print(f"  {d['vendor']:<10} {d['model']:<28} {d['retire'] or '-'}{left} → {d.get('replacement') or '-'}")
    return 1 if any(f["level"] == "error" for f in fs) else 0


def run(args, ctx):
    act = args.action or "show"
    if act == "check":
        return cmd_check(args, ctx, vendors.load(ctx))
    db, table = _context(ctx)
    normalize_task(db, "task", ctx.lang)  # task 꾸러미가 없으면 init 안내와 함께 멈춘다
    if act == "show":
        if getattr(args, "task", None):
            show_task(ctx, db, table, args.task)
        else:
            show_all(ctx, db, table)
        return 0
    if act == "pick":
        return cmd_pick(args, ctx, db, table)
    if act == "escalate":
        return cmd_escalate(args, ctx, db, table)
    if act == "record":
        return cmd_record(args, ctx, db)
    if act == "tune":
        return cmd_tune(args, ctx, db)
    if act == "set":
        return cmd_set(args, ctx, db)
    if act == "export":
        return cmd_export(args, ctx, db, table)
    return 0
