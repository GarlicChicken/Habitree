"""낭비 신호: 끝난 세션에서 정해진 기준으로 찾는다(모델에게 묻지 않아 매번 같은 결과). / Waste signals.

근거가 분명하고 비용이 큰 것만 둔다. 이름은 v0.2 작업 중 감지기(guard)와 같고, 규칙 DB에 detect.signal이
같은 규칙이 있으면 그 규칙의 detect.threshold를 기준값으로 쓴다(사용자 반응으로 조정된 값이 그대로 이어진다).
기준값과 출처: docs/spec/audit.md. 결과(hit)에는 개수·토큰·도구 이름·상대 경로만 넣고 글은 넣지 않는다.
"""
import re

from ..core.i18n import tr
from ..core.ruledb import SIMILAR_THRESHOLD
from ..core.textsim import similarity
from ..core.timeutil import local_date
from .model import MAIN, category, input_hash, iso, norm_path, read_only_shell, show_path, table
from .usage import tier_of


def _t(ko, en):
    return {"ko": ko, "en": en}


SIGNALS = {  # 순서 = 보고 순서
    "big_output": {
        "severity": "warn", "scope": "work/context", "aspect": "process", "threshold": {"chars": 20000, "lines": 1000},
        "title": _t("큰 결과의 상주 비용", "Large results billed again"),
        "do": _t(["검색으로 위치를 먼저 찾는다", "필요한 범위만 읽는다", "긴 출력은 파일로 받고 요약만 본다"],
                 ["Search for the location first", "Read only the range you need", "Send long output to a file"]),
        "rule": _t("도구 결과가 2만 자를 넘거나 1,000줄 넘는 파일이면, 검색으로 위치를 찾고 필요한 범위만 읽는다.",
                   "If a tool result would exceed 20,000 characters or a file has over 1,000 lines, search first and read only the range you need."),
        "why": _t("큰 결과는 대화에 남아 뒤의 모든 요청에서 캐시 읽기로 다시 청구된다.",
                  "A large result stays in the conversation and is billed again as cache reads on every later request."),
    },
    "same_call_streak": {
        "severity": "warn", "scope": "work/loop", "aspect": "process", "threshold": {"count": 3},
        "title": _t("같은 호출 되풀이", "Same call repeated"),
        "do": _t(["마지막 결과나 오류를 다시 읽는다", "다른 방법을 고른다", "그래도 막히면 방향을 묻는다"],
                 ["Re-read the last result or error", "Pick another approach", "If still stuck, ask"]),
        "rule": _t("같은 도구를 같은 입력으로 연속 세 번 부르게 되면 멈추고 다른 방법을 찾는다.",
                   "If you are about to call the same tool with the same input a third time in a row, stop and try another way."),
        "why": _t("같은 입력이면 결과도 같아 토큰과 시간만 든다.", "The same input gives the same result."),
    },
    "same_error_streak": {
        "severity": "warn", "scope": "work/loop", "aspect": "process", "threshold": {"count": 3},
        "title": _t("같은 오류 되풀이", "Same error repeated"),
        "do": _t(["오류 문장에서 원인을 찾는다", "입력을 고치거나 다른 길로 간다", "안 되면 멈추고 보고한다"],
                 ["Find the cause in the error", "Change the input or the path", "Otherwise stop and report"]),
        "rule": _t("같은 오류가 세 번 나면 같은 방법을 다시 쓰지 않고, 원인을 찾거나 멈추고 보고한다.",
                   "When the same error appears three times, do not retry the same way; find the cause or stop and report."),
        "why": _t("같은 방법을 또 쓰면 같은 오류가 날 가능성이 크다.", "The same way is likely to fail the same way."),
    },
    "repeat_correction": {
        "severity": "warn", "scope": "work/request", "aspect": "process", "threshold": {"count": 2, "chars": 200},
        "related": ["work.cycle.feedback-to-rule"],
        "title": _t("거듭된 정정", "Repeated corrections"),
        "do": _t(["알게 된 것을 담아 요청을 새로 쓴다", "새 대화(/clear)에서 한 번 보낸다", "되풀이될 지적이면 규칙으로 남긴다"],
                 ["Rewrite the request with what you learned", "Send it once in a fresh conversation",
                  "Record recurring points as rules"]),
        "rule": _t("한 세션에서 두 번 바로잡게 되면 그 지적을 규칙으로 남기고 새 대화에서 다시 시작한다.",
                   "After two corrections in one session, record the point as a rule and restart in a fresh conversation."),
        "why": _t("실패한 시도가 대화에 남아 계속 다시 읽힌다.", "Failed attempts stay in the conversation and are re-read."),
    },
    "expensive_simple": {
        "severity": "info", "scope": "task/explore", "aspect": "process", "threshold": {"tiers": ["high", "top"]},
        "models": True,
        "title": _t("비싼 모델로 한 단순 작업", "Simple work on an expensive model"),
        "do": _t(["읽기·검색만 하는 서브에이전트는 task/explore 칸으로", "에이전트 파일을 설정 models.agents에 묶고 내보낸다"],
                 ["Run read-and-search subagents in the task/explore cell",
                  "Bind the agent file in models.agents and export"]),
        "rule": _t("읽기·검색만 하는 서브에이전트는 task/explore 칸 모델로 돌린다.",
                   "Run subagents that only read and search on the task/explore cell model."),
        "why": _t("단순한 서브에이전트 작업은 작은 모델로 충분하다.", "Simple subagent work is fine on a small model."),
    },
    "rewritten_script": {
        "severity": "info", "scope": "work/cycle", "aspect": "structure", "threshold": {"jaccard": 0.65, "tokens": 50},
        "related": ["work.cycle.repeat-to-module"],
        "title": _t("세션마다 다시 쓴 스크립트", "Script rewritten across sessions"),
        "do": _t(["되풀이되는 스크립트를 도구로 만든다", "지도(README)에 올린다", "다음에는 그 도구를 부른다"],
                 ["Make the repeated script a tool", "List it in the map (README)", "Call that tool next time"]),
        "rule": _t("비슷한 스크립트를 두 세션에서 새로 썼다면 세 번째 전에 도구로 만들어 지도에 올린다.",
                   "If a similar script was written from scratch in two sessions, make it a tool before the third time."),
        "why": _t("되풀이할 때마다 같은 코드를 다시 쓰면 토큰이 들고 결과가 조금씩 달라진다.",
                  "Rewriting the same code costs tokens and drifts each time."),
    },
}
ORDER = list(SIGNALS)


class Env:
    """판정에 함께 쓰는 것. / Shared inputs for detectors."""

    def __init__(self, root, pricer, db=None, explore_cell=None, explore_model=None):
        self.root, self.pricer, self.db = str(root), pricer, db
        self.explore_cell, self.explore_model = explore_cell, explore_model

    def th(self, name):
        """기준값. 규칙 DB에 같은 신호의 감지 규칙이 있으면 그 threshold를 count로 쓴다. / Thresholds."""
        out = dict(SIGNALS[name]["threshold"])
        rule = _detect_rule(self.db, name)
        if rule and isinstance(rule["detect"].get("threshold"), int) and "count" in out:
            out["count"] = rule["detect"]["threshold"]
        return out

    def costs(self, reqs):
        vals = [self.pricer.request(r) for r in reqs]
        return sum(v for v in vals if v is not None) if any(v is not None for v in vals) else None


def _hit(name, ses, ctx, count, at=None, tokens=None, cost=None, saving=None, **evidence):
    return {"signal": name, "severity": SIGNALS[name]["severity"], "session": ses.id, "ctx": ctx, "count": count,
            "tokens": tokens, "cost_usd": cost, "saving_usd": saving, "at": iso(at),
            "evidence": {k: v for k, v in evidence.items() if v not in (None, "", [])}}


def big_output(ses, env):
    """큰 결과 × 그 뒤 남은 요청 수 = 다시 청구되는 비용(캐시 쓰기 1번 + 캐시 읽기). / Resident cost."""
    th, hits, pricer = env.th("big_output"), [], env.pricer
    for ctx in ses.contexts():
        reqs = ses.ordered_requests(ctx)
        cuts = sorted(o for cx, o in ses.compactions if cx == ctx)
        for c in ses.ordered_calls(ctx):
            whole = category(c.name) == "read" and c.info.get("totalLines", 0) > th["lines"] and \
                c.info.get("numLines") == c.info.get("totalLines") and c.info.get("startLine") in (None, 1)
            issued = ses.requests.get(c.request)
            if not c.has_result or issued is None or (c.chars < th["chars"] and not whole):
                continue
            stop = next((o for o in cuts if o > issued.order), None)
            later = [r for r in reqs if r.order > issued.order and (stop is None or r.order < stop)]
            tokens, measured = c.chars // 4, False  # 추정: 글자 수 ÷ 4(영어 기준)
            if later:
                sib = sum(ses.calls[t].chars for t in issued.tool_ids if t in ses.calls) or c.chars
                delta = later[0].prompt - issued.prompt - issued.output  # 다음 요청에서 새로 늘어난 프롬프트
                if delta > 0:
                    tokens, measured = int(delta * c.chars / sib), True
            parts = []
            for i, r in enumerate(later):
                rate = pricer.rates(r.model, r.ts.date() if r.ts else None, r.prompt)
                key = "cache_write" if i == 0 else "cache_read"
                if rate and rate.get(key) is not None:
                    parts.append(tokens * rate[key] / 1e6)
            hits.append(_hit("big_output", ses, ctx, 1, at=c.ts, tokens=tokens, cost=sum(parts) if parts else None,
                             tool=c.name, path=show_path(c.path(), env.root), chars=c.chars, later=len(later),
                             measured=measured, whole_file=whole or None))
    return hits


def _runs_to_hits(name, ses, ctx, env, runs):
    """반복분(두 번째부터)을 낸 요청의 비용을 매긴다. / Cost of the requests that issued the repeats."""
    out = []
    for run in runs:
        if len(run) >= env.th(name)["count"]:
            reqs = {c.request for c in run[1:]} - {run[0].request}
            out.append(_hit(name, ses, ctx, len(run), at=run[0].ts, tool=run[0].name,
                            cost=env.costs([ses.requests[k] for k in reqs if k in ses.requests])))
    return out


def same_call_streak(ses, env):
    """같은 도구·같은 입력(키를 정렬한 JSON 해시)이 연속으로. / Same tool and input in a row."""
    hits, skip = [], set(table()["repeat_ok_tools"])
    for ctx in ses.contexts():
        runs, prev = [], None
        for c in ses.ordered_calls(ctx):
            if c.name in skip:
                continue
            k = input_hash(c.name, c.input)
            if k != prev:
                runs.append([])
            runs[-1].append(c)
            prev = k
        hits += _runs_to_hits("same_call_streak", ses, ctx, env, runs)
    return hits


def same_error_streak(ses, env):
    """같은 도구가 같은 오류(첫 줄 해시)로, 그 도구의 성공 없이 되풀이. / Same tool, same error, no success between."""
    hits = []
    for ctx in ses.contexts():
        open_runs, done = {}, []
        for c in ses.ordered_calls(ctx):
            if not c.has_result:
                continue
            if c.error and c.err_sig:
                open_runs.setdefault((c.name, c.err_sig), []).append(c)
            else:
                done += [open_runs.pop(k) for k in [k for k in open_runs if k[0] == c.name]]
        hits += _runs_to_hits("same_error_streak", ses, ctx, env, done + list(open_runs.values()))
    return hits


def correction_markers(text, max_chars=200):
    """정정 표현이면 걸린 표지(우리 목록의 낱말), 아니면 []. 사용자 글은 돌려주지 않는다. / Matched markers."""
    t = (text or "").strip().casefold()
    data = table()["correction"]
    if not t or len(t) > max_chars or t.startswith(tuple(x.casefold() for x in data["not"])):
        return []
    found = {m.strip() for lang in ("ko", "en") for m in data[lang]["start"] if t.startswith(m.casefold())}
    found |= {m.strip() for lang in ("ko", "en") for m in data[lang]["contains"] if m.casefold() in t}
    return sorted(found)


def repeat_correction(ses, env):
    th = env.th("repeat_correction")
    reqs = ses.ordered_requests(MAIN)
    if not reqs:
        return []
    got = [(ts, correction_markers(text, th["chars"])) for ts, text, order in ses.human if order > reqs[0].order]
    got = [(ts, m) for ts, m in got if m]
    if len(got) < th["count"]:
        return []
    return [_hit("repeat_correction", ses, MAIN, len(got), at=got[0][0],
                 markers=sorted({x for _, m in got for x in m})[:6])]


def expensive_simple(ses, env):
    """상·최상 등급 모델로 돈 서브에이전트가 읽기·검색만 했다(E 노트 4-4, 추정). / Expensive read-only subagent."""
    th, hits, pricer = env.th("expensive_simple"), [], env.pricer
    for ctx in ses.contexts():
        reqs, calls = ses.ordered_requests(ctx), ses.ordered_calls(ctx)
        if ctx == MAIN or not reqs or not calls:
            continue
        if not {tier_of(pricer.table, r.model) for r in reqs} <= set(th["tiers"]):
            continue
        if not all(category(c.name) in ("read", "search", "web") or
                   (category(c.name) == "shell" and read_only_shell(c.command())) for c in calls):
            continue
        cost, saving = env.costs(reqs), None
        if env.explore_model and cost is not None:
            alt = [pricer.cost(r.tokens(), env.explore_model, r.ts.date() if r.ts else None) for r in reqs]
            saving = max(cost - sum(alt), 0.0) if None not in alt else None
        hits.append(_hit("expensive_simple", ses, ctx, len(calls), at=reqs[0].ts, cost=cost, saving=saving,
                         agent_type=ses.agents.get(ctx, {}).get("type"), models=sorted({r.model for r in reqs}),
                         target=f"{env.explore_cell} {env.explore_model}" if env.explore_model else None))
    return hits


def rewritten_script(sessions, env):
    """다른 세션에서 새로 쓴 비슷한 스크립트(낱말 3개 묶음의 자카드 유사도). / Similar scripts across sessions."""
    th, exts, inline = env.th("rewritten_script"), tuple(table()["script_extensions"]), table()["inline_script"]
    items = []
    for ses in sessions:
        for c in ses.ordered_calls():
            text, name, key = None, None, ""
            if c.name == "Write" and c.path().lower().endswith(exts):
                text, name, key = c.input.get("content"), show_path(c.path(), env.root), norm_path(c.path())
            elif category(c.name) == "shell" and any(m in c.command() for m in inline):
                text, name = c.command(), f"({c.name})"
            toks = re.findall(r"[A-Za-z_]\w*|\d+|[^\sA-Za-z0-9_]", text) if isinstance(text, str) else []
            if len(toks) >= th["tokens"]:
                items.append((ses, name, key, {hash(tuple(toks[i:i + 3])) for i in range(len(toks) - 2)}, c.ts))
    items.sort(key=lambda x: len(x[3]))
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i
    for i, a in enumerate(items):
        for j in range(i + 1, len(items)):
            b = items[j]
            if len(b[3]) * th["jaccard"] > len(a[3]):
                break  # 크기 차이가 커서 유사도 기준을 넘을 수 없다
            if a[0] is not b[0] and not (a[2] and a[2] == b[2]):
                inter = len(a[3] & b[3])
                if inter / (len(a[3]) + len(b[3]) - inter) >= th["jaccard"]:
                    parent[find(j)] = find(i)
    groups = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)
    hits = []
    for members in groups.values():
        ids = sorted({m[0].id for m in members})
        if len(ids) >= 2:
            last = max(members, key=lambda m: (m[4] is not None, m[4].isoformat() if m[4] else ""))
            hits.append(_hit("rewritten_script", last[0], MAIN, len(ids), at=last[4],
                             names=sorted({m[1] for m in members})[:5], sessions=[s[:8] for s in ids][:8]))
    return hits


def detect(sessions, env):
    hits = []
    for ses in sessions:
        for fn in (big_output, same_call_streak, same_error_streak, repeat_correction, expensive_simple):
            hits.extend(fn(ses, env))
    hits.extend(rewritten_script(sessions, env))
    return sorted(hits, key=lambda h: (ORDER.index(h["signal"]), h["at"] or "", h["session"]))


# ── 처방과 규칙 후보 · Prescriptions and rule candidates ──

def _q(text):
    return '"' + str(text).replace('"', "'").replace("\n", " ") + '"'


def _detect_rule(db, name):
    if db is None:
        return None
    return next((r for r in db.active() if (r.get("detect") or {}).get("signal") == name), None)


def _scope_in(db, scope):
    while db is not None and scope and scope not in db.scopes:
        scope = db.parent(scope)
    return scope or "global"


def _similar(db, texts):
    """같은 뜻 규칙(모델 칸 규칙은 빼고: hit하면 하한이 되어 버린다). / Same-meaning rule, skipping cell rules."""
    best = None
    for text in texts:
        for score, r in db.similar(text) if db is not None else []:
            if not (r.get("cell") or r.get("max_cell")) and (best is None or score > best[0]):
                best = (score, r)
    return best if best and best[0] >= SIMILAR_THRESHOLD else None


def find_rule(db, name):
    """detect.signal이 같은 규칙 → 이 신호에 묶어 둔 규칙 → 같은 뜻 규칙. (규칙, 근거) / Existing rule."""
    r = _detect_rule(db, name)
    if r:
        return r, "detect"
    active = {x["id"]: x for x in db.active()} if db is not None else {}
    for rid in SIGNALS[name].get("related", []):
        if rid in active:
            return active[rid], "related"
    best = _similar(db, SIGNALS[name]["rule"].values())
    return (best[1], f"similar {best[0]:.2f}") if best else (None, None)


def suggestions(hits, db=None, lang="ko"):
    """신호를 묶어 반복된 것부터 고정 처방과 명령 초안. 실행하지 않는다. / Grouped candidates; nothing is run."""
    groups = {}
    for h in hits:
        g = groups.setdefault(h["signal"], {"sessions": set(), "count": 0, "cost": 0.0})
        g["sessions"].add(h["session"])
        g["count"] += 1
        g["cost"] += h.get("cost_usd") or h.get("saving_usd") or 0.0
    out = []
    for name, g in sorted(groups.items(), key=lambda x: (-len(x[1]["sessions"]), -x[1]["count"], -x[1]["cost"])):
        meta, n = SIGNALS[name], len(g["sessions"])
        title = tr(meta["title"], lang)
        note = (f"audit {local_date()}: {title}, 세션 {n}개에서 {g['count']}건" if lang == "ko" else
                f"audit {local_date()}: {title}, {g['count']} hits in {n} sessions")
        item = {"signal": name, "title": title, "sessions": n, "count": g["count"], "cost_usd": round(g["cost"], 4),
                "do": tr(meta["do"], lang), "rule": None, "match": None}
        if meta.get("models"):
            item["commands"] = ["habitree models show explore", "habitree models export claude"]
        else:
            rule, how = find_rule(db, name)
            if rule:
                item.update(rule=rule["id"], match=how)
                item["commands"] = [f"habitree rules hit {rule['id']} --feedback {_q(note)}"]
            else:
                item["commands"] = [f"habitree rules add --scope {_scope_in(db, meta['scope'])} --aspect "
                                    f"{meta['aspect']} --rule {_q(tr(meta['rule'], lang))} "
                                    f"--why {_q(tr(meta['why'], lang))} --feedback {_q(note)}"]
        out.append(item)
    return out


def inbox(memories, db=None, lang="ko"):
    """자동 메모리의 feedback 메모를 같은 뜻끼리 묶고(많은 묶음부터), 같은 뜻 규칙이 있으면 hit, 없으면 add 초안.
    / Group feedback memories and draft hit or add commands."""
    texts = [f"{m['name']} {m['description']}" for m in memories]
    groups = []
    for i, m in enumerate(memories):
        g = next((g for g in groups if similarity(texts[g[0]], texts[i]) >= SIMILAR_THRESHOLD), None)
        g.append(i) if g else groups.append([i])
    out = []
    for g in sorted(groups, key=lambda g: -len(g)):
        head = memories[g[0]]
        note = (f"자동 메모리에서: {head['name']}" if lang == "ko" else f"from auto memory: {head['name']}")
        best = _similar(db, [texts[i] for i in g])
        item = {"memories": [memories[i] for i in g], "count": len(g), "rule": best[1]["id"] if best else None}
        if best:
            item["commands"] = [f"habitree rules hit {best[1]['id']} --feedback {_q(note)}"]
        else:
            why = "사용자가 직접 바로잡은 것" if lang == "ko" else "A correction the user made"
            item["commands"] = [f"habitree rules add --scope {_scope_in(db, 'global')} --aspect process --rule "
                                f"{_q(head['description'] or head['name'])} --why {_q(why)} --feedback {_q(note)}"]
        out.append(item)
    return out
