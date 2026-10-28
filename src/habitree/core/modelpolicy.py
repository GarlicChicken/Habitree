"""모델 배분 정책: 규칙 DB의 task 범위에서 칸을 읽고, 승격·조정·점검을 정한다. / Model allocation policy.

정책은 규칙 DB 안에 있다. task 범위 트리의 규칙 중 cell이 있는 것이 그 작업의 칸이다.
  권장(should) 규칙의 cell   기본 칸. 통계(models tune)로 한 단계씩 오른다.
  필수(must) 규칙의 cell     하한. 통계로 바꾸지 않고, 내보내기도 이보다 낮게 쓰지 않는다.
  max_cell                   자동 승격이 갈 수 있는 끝.
  verify                     그 작업의 기계 검증(설정 verify의 이름, "*"는 전부).
하위 범위는 가까운 상위 범위의 칸·상한·검증을 물려받고, 하한은 사슬 전체에서 가장 높은 것을 쓴다.

승격 규칙(E 조사 4-2):
  장애(infra)·거절(refusal)  등급을 올리지 않고 같은 등급의 다른 모델로
  잘림(truncated)            같은 칸으로 다시(출력 한도를 늘리거나 강도를 낮춤)
  형식 오류(format_error)    같은 칸 1번 더, 그다음은 등급 +1
  건너뜀(skipped_steps)      강도 +1(강도가 최대면 등급 +1)
  자신 있게 틀림·맴돌기       등급 +1
  작업당 자동 승격 2단계, 시도 4번. 하한이 있는 작업, 기계 검증이 없는 작업, 상한을 넘는 승격은 사람에게.
"""
import json
import re

from . import HabitreeError
from . import io as hio
from . import vendors
from .config import CONFIG_REL
from .paths import rel
from .ruledb import RuleDB
from .timeutil import now_iso
from .vendors import EFFORTS, TIERS, cell_key, cell_str, parse_cell

TASK_ROOT = "task"
SIGNALS = ("skipped_steps", "confident_wrong", "loop", "format_error", "infra", "refusal", "truncated")
QUALITY_SIGNALS = ("skipped_steps", "confident_wrong", "loop", "format_error")
RESULTS = ("pass", "quality_fail", "infra_fail")
EVENTS_FILE = "models-events.jsonl"
AGENTS_DIR = ".claude/agents"
TOP = {"tier": "top", "effort": "max"}


def setting(ctx, dotted):
    """설정 models.<이름>. 기본값은 core/config.py의 DEFAULTS에 있다. / A models.* setting."""
    return ctx.get("models." + dotted)


def configured(ctx):
    """프로젝트 설정 파일에 models 절이 있는가. 없으면 check가 조용히 넘어간다. / Is models configured?"""
    raw = hio.load_json(ctx.p(CONFIG_REL), {}) or {}
    return isinstance(raw, dict) and "models" in raw


# ── 칸 계산 · Cell arithmetic ──

def effort_up(cell):
    i = EFFORTS.index(cell["effort"])
    return {"tier": cell["tier"], "effort": EFFORTS[i + 1]} if i + 1 < len(EFFORTS) else None


def effort_down(cell):
    i = EFFORTS.index(cell["effort"])
    return {"tier": cell["tier"], "effort": EFFORTS[i - 1]} if i > 0 else None


def tier_up(cell):
    i = TIERS.index(cell["tier"])
    return {"tier": TIERS[i + 1], "effort": cell["effort"]} if i + 1 < len(TIERS) else None


def tier_down(cell):
    i = TIERS.index(cell["tier"])
    return {"tier": TIERS[i - 1], "effort": cell["effort"]} if i > 0 else None


def higher(a, b):
    return a if cell_key(a) >= cell_key(b) else b


def steps_between(start, cur):
    """start에서 cur까지 올라온 단계 수(낮아졌으면 0). / Steps climbed from start to cur."""
    dt = TIERS.index(cur["tier"]) - TIERS.index(start["tier"])
    de = EFFORTS.index(cur["effort"]) - EFFORTS.index(start["effort"])
    if dt < 0 or (dt == 0 and de <= 0):
        return 0
    return max(dt, 0) + max(de, 0)


def clamp_to(cell, cap):
    """상한 안으로. 등급이 상한을 넘으면 None, 같은 등급이면 강도를 상한에 맞춘다. / Fit under the cap."""
    if cell is None:
        return None
    if TIERS.index(cell["tier"]) > TIERS.index(cap["tier"]):
        return None
    if cell["tier"] == cap["tier"] and EFFORTS.index(cell["effort"]) > EFFORTS.index(cap["effort"]):
        return {"tier": cell["tier"], "effort": cap["effort"]}
    return cell


# ── 정책 읽기 · Reading the policy ──

def load_db(ctx):
    return RuleDB.load(ctx.p(ctx.get("rules.db")), ctx.lang)


def task_scopes(db):
    return [s for s, _ in db.order() if s == TASK_ROOT or s.startswith(TASK_ROOT + "/")]


def normalize_task(db, name, lang="ko"):
    """'explore' → 'task/explore'. 규칙 DB에 없는 작업이면 오류. / Normalize and validate a task name."""
    n = str(name or "").strip().strip("/")
    if n != TASK_ROOT and not n.startswith(TASK_ROOT + "/"):
        n = f"{TASK_ROOT}/{n}" if n else TASK_ROOT
    if n not in db.scopes or TASK_ROOT not in db.chain(n):
        known = ", ".join(task_scopes(db)) or "-"
        if TASK_ROOT not in db.scopes:
            raise HabitreeError("규칙 DB에 task 범위가 없습니다. `habitree init`을 다시 실행하면 task 꾸러미가 들어옵니다."
                                if lang == "ko" else
                                "The rule DB has no task scope. Run `habitree init` again to add the task pack.")
        raise HabitreeError((f"없는 작업 유형: {name} (있는 것: {known})" if lang == "ko"
                             else f"Unknown task type: {name} (available: {known})"))
    return n


def policy(db, task):
    """작업 하나의 정책. / The policy for one task.

    돌려주는 칸: task, rule(기본 칸을 정한 규칙 id), level, default(그 규칙의 칸), cell(하한을 반영한 칸),
    floor, floor_rule, max_cell, verify(이름 목록), risky(하한이 있나), why, text(규칙 글).
    """
    chain = db.chain(task)
    governing = floor = floor_rule = max_cell = verify = None
    for scope in chain:
        rs = [r for r in db.active() if r["scope"] == scope and r.get("cell")]
        for r in rs:
            if r.get("level") == "must":
                c = parse_cell(r["cell"])
                if floor is None or cell_key(c) > cell_key(floor):
                    floor, floor_rule = c, r["id"]
        if governing is None and rs:
            governing = sorted(rs, key=lambda r: r.get("level") == "must")[0]
        if max_cell is None:
            caps = [r["max_cell"] for r in rs if r.get("max_cell")]
            if caps:
                max_cell = parse_cell(caps[0])
        if verify is None:
            vs = [r["verify"] for r in rs if "verify" in r]
            if vs:
                verify = list(vs[0])
    if governing is None:
        raise HabitreeError(f"이 작업에 칸 규칙이 없습니다 / no cell rule for this task: {task}")
    default = parse_cell(governing["cell"])
    cell = higher(default, floor) if floor else default
    cap = max_cell or dict(TOP)
    if cell_key(cap) < cell_key(cell):
        cap = cell
    return {"task": task, "rule": governing["id"], "level": governing.get("level", "should"), "default": default,
            "cell": cell, "floor": floor, "floor_rule": floor_rule, "max_cell": cap, "verify": verify or [],
            "risky": floor is not None, "why": governing.get("why", ""), "text": governing.get("rule", "")}


def verify_spec(entry):
    """설정 verify의 항목 하나 → (명령 배열, 시간 한도 초 또는 None).
    항목은 ["pytest", "-q"] 또는 {"cmd": [...], "timeout": 900}. / One verify entry."""
    cmd, timeout = entry, None
    if isinstance(entry, dict):
        cmd, timeout = entry.get("cmd") or entry.get("run"), entry.get("timeout")
    if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) for x in cmd):
        raise HabitreeError(f"verify 명령은 글자 배열이어야 합니다 / verify commands must be string arrays: {entry!r}")
    return list(cmd), (int(timeout) if timeout else None)


def verify_names(ctx, pol):
    """이 작업에 쓸 수 있는 검증 명령 이름(설정 verify에 있는 것만). / Usable verify names."""
    cfg = ctx.get("verify") or {}
    names = pol.get("verify") or []
    if "*" in names:
        return list(cfg)
    return [n for n in names if n in cfg]


# ── 승격 · Escalation ──

def _txt(ko, en):
    return {"ko": ko, "en": en}


def escalate(pol, cur, signal, attempt=1, verified=(), max_steps=2, max_attempts=4):
    """실패 신호 → 다음 할 일. action: retry(같은 칸) | fallback(같은 등급 대체) | escalate(올림) | human.
    / Next step after a failure signal."""
    cur = parse_cell(cur)
    if signal not in SIGNALS:
        raise HabitreeError(f"없는 신호 / unknown signal: {signal} ({', '.join(SIGNALS)})")
    attempt = max(1, int(attempt or 1))
    steps = steps_between(pol["default"], cur)
    out = {"task": pol["task"], "from": cell_str(cur), "signal": signal, "attempt": attempt,
           "next_attempt": attempt + 1, "steps": steps, "action": "human", "to": None, "reason": {}, "advice": []}

    def done(action, to, ko, en, advice=()):
        out["action"], out["to"] = action, (cell_str(to) if to else None)
        out["reason"] = _txt(ko, en)
        out["advice"] = list(advice)
        return out

    upstream = _txt("모델을 바꾸기 전에 지시문·맥락·도구·검증 명령이 빠지지 않았는지 먼저 본다.",
                    "Before changing the model, check that instructions, context, tools and verify commands are complete.")
    fresh = _txt("새 서브에이전트(새 대화)에서 실패 요약만 넘겨 다시 한다.",
                 "Retry in a fresh subagent (new conversation) with only a failure summary.")
    if attempt >= max_attempts:
        return done("human", None, f"시도 {max_attempts}번을 다 썼다. 실패 기록과 함께 사람에게 넘긴다.",
                    f"All {max_attempts} attempts are used. Hand over to a person with the failure log.")
    if signal == "infra":
        return done("fallback", cur, "장애(429·5xx·과부하·컨텍스트 초과)는 품질 문제가 아니다. 등급을 올리지 않고 같은 등급의 다른 배포·회사로 돌린다.",
                    "Outages (429, 5xx, overload, context overflow) are not quality problems. Keep the tier and switch "
                    "to another deployment or vendor at the same tier.")
    if signal == "refusal":
        return done("fallback", cur, "거절은 등급을 올려 풀 일이 아니다. 같은 등급의 다른 모델이나 회사로 돌린다.",
                    "A refusal is not solved by a higher tier. Switch to another model or vendor at the same tier.")
    if signal == "truncated":
        return done("retry", cur, "출력이 잘렸다. 등급과 무관하다. 출력 한도를 늘리거나 강도를 한 단계 낮춰 같은 등급으로 다시 한다.",
                    "Output was truncated; this is unrelated to the tier. Raise the output limit or lower effort one "
                    "step and retry at the same tier.")
    if signal == "format_error":
        retries_used = attempt - 1 - steps
        if retries_used <= 0:
            return done("retry", cur, "형식 오류는 같은 칸에서 1번 더 한다(실패 출력을 붙여서).",
                        "On a format error, retry once in the same cell (with the failing output attached).")
    if pol.get("risky"):
        return done("human", None, f"하한이 있는 위험 작업({cell_str(pol['floor'])} 하한)은 자동으로 올리지 않고 사람에게 넘긴다.",
                    f"Risky tasks with a floor ({cell_str(pol['floor'])}) are not escalated automatically; hand over "
                    "to a person.", [upstream])
    if not verified:
        return done("human", None, "이 작업에는 기계 검증(설정 verify)이 없어 자동으로 올리지 않는다. 사람이나 다른 회사 모델이 결과를 본다.",
                    "This task has no machine verification (verify in the config), so it is not escalated "
                    "automatically. A person or a model from another vendor reviews the result.", [upstream])
    if steps >= max_steps:
        return done("human", None, f"작업당 자동 승격 {max_steps}단계를 다 썼다. 사람에게 넘긴다.",
                    f"The {max_steps} automatic steps for this task are used. Hand over to a person.", [upstream])
    if signal == "skipped_steps":
        nxt = effort_up(cur)
        why = _txt("단계를 건너뛰면(파일을 안 읽음, 테스트를 안 돌림) 강도를 한 단계 올린다.",
                   "Skipped steps (unread files, tests not run) raise effort one step.")
        if nxt is None:
            nxt = tier_up(cur)
            why = _txt("강도가 이미 최대라 등급을 한 단계 올린다.", "Effort is already at max, so the tier goes up one step.")
    else:
        nxt = tier_up(cur)
        why = {"confident_wrong": _txt("맥락이 충분한데도 자신 있게 틀리면 등급을 한 단계 올린다.",
                                       "Confidently wrong with enough context: raise the tier one step."),
               "loop": _txt("같은 자리를 맴돌면 멈추고 등급을 한 단계 올린다.",
                            "Looping: stop and raise the tier one step."),
               "format_error": _txt("같은 칸 재시도에도 형식 오류가 나서 등급을 한 단계 올린다.",
                                    "The format error repeated after the same-cell retry, so the tier goes up one step.")
               }[signal]
    capped = clamp_to(nxt, pol["max_cell"])
    if capped is None or cell_key(capped) <= cell_key(cur):
        return done("human", None, f"자동 승격 상한({cell_str(pol['max_cell'])})에 닿았다. 사람에게 넘긴다.",
                    f"Reached the escalation cap ({cell_str(pol['max_cell'])}). Hand over to a person.", [upstream])
    return done("escalate", capped, why["ko"], why["en"], [upstream, fresh])


# ── 사건 기록 · Event log ──

def events_path(ctx):
    return ctx.state_dir / EVENTS_FILE


def read_events(ctx):
    p = events_path(ctx)
    if not p.is_file():
        return []
    out = []
    for line in hio.read_text(p).split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict):
            out.append(e)
    return out


def record(ctx, task, result, cell, note="", source="record"):
    """사건 한 줄을 더한다(UTC 시각). / Append one event (UTC timestamp)."""
    if result not in RESULTS:
        raise HabitreeError(f"없는 결과 / unknown result: {result} ({', '.join(RESULTS)})")
    event = {"at": now_iso(), "task": task, "result": result, "cell": cell_str(parse_cell(cell)), "source": source}
    if note:
        event["note"] = note
    p = events_path(ctx)
    old = hio.read_text(p) if p.is_file() else ""
    if old and not old.endswith("\n"):
        old += "\n"
    hio.write_text(p, old + json.dumps(event, ensure_ascii=False) + "\n")
    return event


# ── 통계로 조정 · Tuning ──

def replace_cell_text(rule, old, new):
    """규칙 글 속 칸 표기(`low:medium`)를 새 칸으로(처음 나오는 하나만). / Keep rule text in step with the cell."""
    o, n = f"`{cell_str(old)}`", f"`{cell_str(new)}`"
    text = rule.get("rule")
    if isinstance(text, dict):
        rule["rule"] = {k: (v.replace(o, n, 1) if isinstance(v, str) else v) for k, v in text.items()}
    elif isinstance(text, str):
        rule["rule"] = text.replace(o, n, 1)


def set_cell(db, rule, new, change):
    old = parse_cell(rule["cell"])
    rule["cell"] = dict(new)
    replace_cell_text(rule, old, new)
    db.log_change(rule, f"cell: {cell_str(old)} → {cell_str(new)} ({change})")


def tune(db, events, window=20, min_runs=10, up_ratio=0.2, down_ratio=0.05, apply=True):
    """최근 기록으로 기본 칸을 조정한다. 올림은 바로(apply), 내림은 제안만, 하한(must)은 그대로.
    / Raise default cells from recent outcomes; only suggest lowering; never touch floors.

    돌려주는 목록의 칸: task, rule, action(raised|suggest_down|floor|few|cap|keep), from, to, runs, fails, ratio."""
    by_rule = {}
    for e in events:
        task = e.get("task")
        if task not in db.scopes or TASK_ROOT not in db.chain(task):
            continue
        try:
            pol = policy(db, task)
        except HabitreeError:
            continue
        by_rule.setdefault(pol["rule"], []).append(e)
    report = []
    for rid, evs in by_rule.items():
        r = db.find(rid)
        cur = parse_cell(r["cell"])
        pol = policy(db, r["scope"])
        rows = [e for e in evs if e.get("cell") == cell_str(cur) and e.get("result") in ("pass", "quality_fail")]
        rows = rows[-window:]
        n = len(rows)
        fails = sum(1 for e in rows if e["result"] == "quality_fail")
        ratio = fails / n if n else 0.0
        item = {"task": r["scope"], "rule": rid, "action": "keep", "from": cell_str(cur), "to": None, "runs": n,
                "fails": fails, "ratio": round(ratio, 3)}
        if r.get("level") == "must":
            item["action"] = "floor"
        elif n < min_runs:
            item["action"] = "few"
        elif ratio >= up_ratio:
            nxt = effort_up(cur) or tier_up(cur)
            capped = clamp_to(nxt, pol["max_cell"])
            if capped is None or cell_key(capped) <= cell_key(cur):
                item["action"] = "cap"
            else:
                item["action"], item["to"] = "raised", cell_str(capped)
                if apply:
                    set_cell(db, r, capped, f"tune: 품질 실패 {fails}/{n} = {ratio:.0%} ≥ {up_ratio:.0%} / "
                                            f"quality failures")
        elif n >= window and ratio <= down_ratio:
            prv = effort_down(cur) or tier_down(cur)
            if prv is not None and (pol["floor"] is None or cell_key(prv) >= cell_key(pol["floor"])):
                item["action"], item["to"] = "suggest_down", cell_str(prv)
        report.append(item)
    return sorted(report, key=lambda x: x["task"])


# ── 에이전트 파일 · Agent files ──

FM_LINE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$")


def frontmatter_bounds(lines):
    """머리말 줄 범위 [start, end). 없으면 None. / Front matter line range."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return 1, i
    return None


def _clean_value(v):
    v = v.split(" #", 1)[0].strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    return v


def fm_get(text, key):
    lines = text.split("\n")
    b = frontmatter_bounds(lines)
    if not b:
        return None
    for line in lines[b[0]:b[1]]:
        m = FM_LINE.match(line)
        if m and m.group(1) == key:
            return _clean_value(m.group(2))
    return None


def fm_set(text, updates):
    """머리말의 키 값만 바꾸거나 더한다. 머리말이 없으면 None. 본문은 그대로. / Edit front matter keys only."""
    lines = text.split("\n")
    b = frontmatter_bounds(lines)
    if not b:
        return None
    start, end = b
    for key, value in updates.items():
        hit = None
        for i in range(start, end):
            m = FM_LINE.match(lines[i])
            if m and m.group(1) == key:
                hit = i
                break
        if hit is not None:
            lines[hit] = f"{key}: {value}"
        else:
            lines.insert(end, f"{key}: {value}")
            end += 1
    return "\n".join(lines)


def agent_file(ctx, name):
    """에이전트 정의 파일: .claude/agents/<이름>.md, 없으면 머리말 name이 같은 파일. / Find an agent file."""
    folder = ctx.p(AGENTS_DIR)
    direct = folder / f"{name}.md"
    if direct.is_file():
        return direct
    if folder.is_dir():
        for p in sorted(folder.glob("*.md")):
            try:
                if fm_get(hio.read_text(p), "name") == name:
                    return p
            except OSError:
                continue
    return None


def agent_model_value(ctx, res):
    """에이전트 파일에 쓸 model 값: 고정 ID(기본) 또는 Claude Code 별칭. / Pinned ID or alias."""
    if setting(ctx, "claude_model") == "alias" and res.get("aliases"):
        return res["aliases"][0]
    return res["model"]


# ── 점검 · Findings (check 연동) ──

def _f(cid, level, ko, en, path=""):
    return {"id": cid, "level": level, "msg": {"ko": ko, "en": en}, "path": path}


def findings(ctx, today=None, force=False):
    """check가 쓰는 결과: models.deprecated(경고), models.floor(오류), models.price-stale(알림).
    설정에 models 절이 없으면 빈 목록(force면 기본값으로 점검). / Findings for check."""
    if not force and not configured(ctx):
        return []
    over_rel = vendors.OVERRIDE_REL
    try:
        table = vendors.load(ctx)
    except HabitreeError as e:
        return [_f("models.floor", "error", f"대응표를 읽지 못해 하한을 확인하지 못함: {e}",
                   f"Could not read the vendor table, so floors were not checked: {e}", over_rel)]
    out = []
    vendor = setting(ctx, "vendor")
    in_use = {}
    for mid in vendors.tier_models(table, vendor).values():
        in_use.setdefault(mid, "")
    try:
        db = load_db(ctx)
    except HabitreeError:
        db = None  # rules.invalid가 따로 알린다
    for name, task in (setting(ctx, "agents") or {}).items():
        path = agent_file(ctx, name)
        if path is None:
            continue
        text = hio.read_text(path)
        model, effort = fm_get(text, "model"), fm_get(text, "effort")
        relp = rel(ctx.root, path)
        if not model or model == "inherit":
            continue
        found = vendors.find_model(table, model)
        if not found:
            continue
        vname, mid, entry = found
        in_use[mid] = relp
        if db is None or not entry.get("tier"):
            continue
        try:
            pol = policy(db, normalize_task(db, task, ctx.lang))
        except HabitreeError:
            continue
        floor = pol["floor"]
        if not floor:
            continue
        mt, ft = TIERS.index(entry["tier"]), TIERS.index(floor["tier"])
        ne = vendors.neutral_effort(table, vname, effort) if effort else None
        low = mt < ft or (mt == ft and ne is not None and EFFORTS.index(ne) < EFFORTS.index(floor["effort"]))
        if low:
            shown = f"{model} ({entry['tier']}" + (f":{ne}" if ne else "") + ")"
            out.append(_f("models.floor", "error",
                          f"에이전트 {name}의 model {shown}이 작업 {pol['task']}의 하한 {cell_str(floor)}보다 낮음 "
                          f"(habitree models export claude --write)",
                          f"Agent {name} uses {shown}, below the floor {cell_str(floor)} of {pol['task']} "
                          f"(habitree models export claude --write)", relp))
    days = setting(ctx, "deprecation_days")
    for d in vendors.deprecations(days, table, today, models=set(in_use)):
        path = in_use.get(d["model"], "")
        repl = d.get("replacement") or "-"
        if d["days_left"] is not None and d["days_left"] < 0:
            ko, en = (f"단종일이 지난 모델: {d['model']} ({d['retire']}), 대체 {repl}",
                      f"Model past its retirement date: {d['model']} ({d['retire']}), replacement {repl}")
        elif d["days_left"] is not None:
            ko, en = (f"단종 예정: {d['model']} {d['retire']}({d['days_left']}일 남음), 대체 {repl}",
                      f"Retiring: {d['model']} on {d['retire']} ({d['days_left']} days left), replacement {repl}")
        else:
            ko, en = (f"단종 예고된 모델: {d['model']} (상태 {d['status']}), 대체 {repl}",
                      f"Deprecated model: {d['model']} (status {d['status']}), replacement {repl}")
        out.append(_f("models.deprecated", "warn", ko, en, path))
    stale = setting(ctx, "price_stale_days")
    used_vendors = {vendor} | {vendors.find_model(table, m)[0] for m in in_use if vendors.find_model(table, m)}
    for vname in sorted(v for v in used_vendors if v in table["vendors"]):
        age = vendors.checked_age_days(table, vname, today)
        if age is not None and stale and age > stale:
            name = table["vendors"][vname]["name"]
            out.append(_f("models.price-stale", "info",
                          f"{name} 가격·모델 확인일이 {age}일 지남(기준 {stale}일). 공식 페이지로 다시 확인하고 "
                          f"{over_rel}의 checked를 고친다",
                          f"{name} prices and models were checked {age} days ago (limit {stale}). Re-check the "
                          f"official pages and update checked in {over_rel}",
                          over_rel if ctx.p(over_rel).is_file() else ""))
    return out
