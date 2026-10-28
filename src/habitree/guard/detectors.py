"""감지기: 표준 이벤트와 세션 상태를 보고 신호를 낸다. 기준값은 규칙의 detect에서 읽는다.
/ Detectors: read the normalized event and session state, emit signals. Thresholds come from the rule.

감지기 하나 = 함수 하나 `(rule, run) -> 신호 또는 None`. 신호는
  {"n": 잰 값, "key": 같은 사건 열쇠, "dedup": 규칙 사이 겹침 열쇠, "facts": 문구 자리표시자, "stop": 멈춤 여부}
이고, 언제 누구에게 어떻게 알릴지는 engine.route가 정한다.

'고리가 아닌 것'(오탐 예외)은 판정 방식에 들어 있다: 다른 파일 대상이나 인자를 바꾼 재시도는 입력 해시가
달라 같은 호출로 세지 않고, 코드를 고친 뒤 테스트를 다시 돌리면 그 사이 수정이 연속을 끊는다.
"""
import re

from ..core.textsim import jaccard
from ..core.fast import short
from ..core.fast import lazy_re
from ..core.timeutil import seconds_since
from . import delegate
from .copyscan import find_copy
from .texts import t

POLL_TOOLS = ["BashOutput", "TaskOutput", "TaskGet", "TaskList", "Monitor", "Sleep", "ScheduleWakeup",
              "AskUserQuestion", "TodoWrite", "TodoRead"]

CORRECTION = [
    r"^\s*(?:아니|아냐|아니야|아니요|아뇨|노노)(?![가-힣])", r"그게\s*아니", r"그거\s*말고", r"말했잖", r"아직도",
    r"여전히\s*(?:안|틀|같)", r"또\s*(?:틀|안\s*돼|안돼|같은\s*(?:실수|문제|오류)|그러|이러)", r"왜\s*또",
    r"다시\s*(?:고쳐|만들어|하라고)", r"틀렸", r"잘못\s*(?:했|됐|이해|고쳤)", r"안\s*된다고", r"그렇게\s*하지\s*말",
    r"^\s*no\b", r"^\s*nope\b", r"\bthat'?s\s+not\b", r"\bnot\s+what\s+i\b", r"\bi\s+(?:said|told\s+you)\b",
    r"\bstill\s+(?:not|wrong|broken|failing)\b", r"\b(?:wrong|broken)\s+again\b", r"\bdoesn'?t\s+work\b",
    r"\bundo\s+that\b",
]
# 차분한 정정과 지켜야 할 방식을 알려 주는 말. 불만이 드러나지 않아도 바로잡는 말이다.
# / Calm corrections and stated conventions, which carry no frustration but still correct the work.
GUIDANCE = [
    r"지\s*(?:마|말고|말아)(?![가-힣])", r"말고(?![가-힣])", r"대신(?:에)?(?![가-힣])",
    r"(?:써|해|맞춰|따라|넣어|빼)야\s*(?:해|돼|지|하|한다|합니다|돼요|해요)", r"기로\s*(?:했|한|정했)",
    r"(?:이미|벌써)\s*있", r"앞으로(?:는)?(?![가-힣])", r"다음부터", r"(?:항상|늘|절대)\s",
    r"\bdon'?t\b", r"\binstead\b", r"\b(?:should|must)\s+(?:use|be|call|throw|return)\b",
    r"\bwe\s+(?:always|never|use|decided)\b", r"\bfrom\s+now\s+on\b", r"\bnext\s+time\b",
    r"\balready\s+(?:has|have|exists?)\b",
]
ACK = lazy_re(r"^(?:응|어|네|넵|예|ㅇㅇ|ㅇㅋ|오케이|좋아|좋아요|좋습니다|고마워|감사합니다|감사|계속|진행|진행해|해 줘|해줘|"
                 r"go|ok|okay|yes|yep|yeah|sure|thanks|thank you|continue|proceed|lgtm|y)[\s.!~]*$", re.I)


def D(rule):
    return rule.get("detect") or {}


def param(rule, name, default):
    p = D(rule).get("params") or {}
    return p.get(name, default)


def threshold(rule, default):
    v = D(rule).get("threshold")
    return v if isinstance(v, int) and not isinstance(v, bool) else default


def stop_at(rule):
    v = D(rule).get("stop_at")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def signal(n, key, facts=None, stop=False, dedup=None, **extra):
    s = {"n": n, "key": key, "facts": dict(facts or {}), "stop": bool(stop), "dedup": dedup}
    s["facts"].setdefault("n", n)
    s.update(extra)
    return s


def is_correction(text, rule=None):
    pats = param(rule, "markers", CORRECTION) if rule else CORRECTION
    return any(re.search(p, text or "", re.I) for p in pats)


def is_ack(text):
    return bool(ACK.match((text or "").strip()))


def _h(parts):
    return short("\0".join(parts), 12)


# ── 작업 중(도구 호출) ──

def same_call_streak(rule, run):
    """같은 도구를 같은 입력으로 연달아(사이에 다른 호출 없이). / Identical consecutive calls."""
    ev, st = run.ev, run.state
    if ev.kind != "pre" or not ev.sig or ev.tool in param(rule, "ignore_tools", POLL_TOOLS):
        return None
    calls = st.get("calls", [])
    n = 0
    for c in reversed(calls):
        if c.get("s") != ev.sig:
            break
        n += 1
    if n < threshold(rule, 3):
        return None
    sa = stop_at(rule)
    first = calls[-n].get("c", 0)
    return signal(n, f"call:{ev.sig}:{first}", {"tool": ev.tool}, stop=bool(sa and n >= sa),
                  dedup=f"call:{ev.sig}")


def _error_chain(results, sig):
    """같은 호출의 같은 오류가 몇 번 이어졌나. 읽기만 하는 다른 호출은 사이에 끼어도 된다.
    / How many times the same call failed with the same error; read-only calls in between are allowed."""
    n, err, line, first = 0, None, "", 0
    for r in reversed(results):
        if r.get("s") == sig:
            if r.get("ok") is not False:
                break
            if err is None:
                err, line = r.get("e"), r.get("el", "")
            elif r.get("e") != err:
                break
            n += 1
            first = r.get("c", 0)
        elif r.get("ro"):
            continue
        else:
            break
    return n, line, first


def same_error_streak(rule, run):
    """같은 호출이 같은 오류로 되풀이. 결과 뒤에 경고, 다음 같은 호출 전에 멈춤.
    / Same call, same error: warn after the result, stop before the next identical call."""
    ev, st = run.ev, run.state
    if not ev.sig:
        return None
    if ev.kind == "post" and ev.ok is False:
        n, line, first = _error_chain(st.get("results", []), ev.sig)
        if n >= threshold(rule, 3):
            return signal(n, f"err:{ev.sig}:{first}", {"tool": ev.tool, "error": line}, dedup=f"call:{ev.sig}")
    if ev.kind == "pre":
        sa = stop_at(rule)
        n, line, first = _error_chain(st.get("results", []), ev.sig)
        if sa and n >= max(1, sa - 1):
            return signal(n, f"err:{ev.sig}:{first}", {"tool": ev.tool, "error": line}, stop=True,
                          dedup=f"call:{ev.sig}")
    return None


def cycle(rule, run):
    """주기 1~5짜리 묶음이 같은 순서로 몇 바퀴 되풀이됐나. / A block of 1 to 5 calls repeating in order."""
    ev, st = run.ev, run.state
    if ev.kind != "pre":
        return None
    calls = st.get("calls", [])
    sigs = [c.get("s") for c in calls]
    ignore = set(param(rule, "ignore_tools", POLL_TOOLS))
    th, sa = threshold(rule, 5), stop_at(rule)
    for k in range(max(1, param(rule, "min_period", 1)), param(rule, "max_period", 5) + 1):
        if len(sigs) < k * th:
            continue
        block = sigs[-k:]
        if k > 1 and len(set(block)) < 2:
            continue  # 한 가지 호출의 되풀이는 주기 1이 맡는다
        if all(c.get("t") in ignore for c in calls[-k:]):
            continue
        laps, i = 1, len(sigs) - 2 * k
        while i >= 0 and sigs[i:i + k] == block:
            laps += 1
            i -= k
        if laps >= th:
            rot = min(tuple(block[j:] + block[:j]) for j in range(k))
            return signal(laps, f"cyc:{_h(rot)}", {"period": k, "laps": laps}, stop=bool(sa and laps >= sa),
                          dedup=f"call:{block[0]}" if k == 1 else None)
    return None


def small_edits_same_file(rule, run):
    """한 파일에 작은 수정이 시간 창 안에 여러 번(검증 실행이 없던 사이). / Many small edits to one file."""
    ev, st = run.ev, run.state
    if ev.kind != "post" or not ev.ok or not ev.is_edit or not ev.fkey:
        return None
    f = st.get("files", {}).get(ev.fkey)
    if not f:
        return None
    window = param(rule, "window_sec", 900)
    times = [x for x in f.get("small", []) if (seconds_since(x) or 0) <= window]
    n = len(times)
    if n < threshold(rule, 6):
        return None
    return signal(n, f"small:{ev.fkey}", {"file": f.get("p", ev.rel), "minutes": max(1, window // 60)})


def file_growth(rule, run):
    """세션 안에서 파일이 크게 늘었고 거의 더하기만 했다(덧대기). / File grew a lot, almost only additions."""
    ev, st = run.ev, run.state
    if ev.kind != "post" or not ev.ok or not ev.is_edit or not ev.fkey:
        return None
    f = st.get("files", {}).get(ev.fkey) or {}
    start, now = f.get("start"), f.get("now")
    if not isinstance(start, int) or not isinstance(now, int) or start < param(rule, "min_lines", 150):
        return None
    pct = (now - start) * 100.0 / start
    if pct < threshold(rule, 30):
        return None
    added, removed = f.get("added", 0), f.get("removed", 0)
    if added <= 0 or (removed > 0 and added / removed < param(rule, "ratio", 10)):
        return None
    return signal(int(pct), f"grow:{ev.fkey}", {"file": f.get("p", ev.rel), "from": start, "to": now,
                                                "added": added, "removed": removed, "pct": int(pct)})


def copy_block(rule, run):
    """새로 쓴 줄 묶음이 다른 파일에 이미 있다. / Newly written lines already exist in another file."""
    ev = run.ev
    if ev.kind != "post" or not ev.ok or not ev.is_edit:
        return None
    wanted = run.extra.get("win") or {}
    if not wanted:
        return None
    k = threshold(rule, 6)
    ext = ("." + ev.rel.rsplit(".", 1)[-1].lower()) if "." in ev.rel.rsplit("/", 1)[-1] else ""
    found = find_copy(run.root, run.file_list(), wanted, k, ev.fkey, run.key,
                      max_files=param(rule, "max_files", 400), max_file_bytes=param(rule, "max_file_bytes", 262144),
                      max_total_bytes=param(rule, "max_total_bytes", 8 * 1024 * 1024), prefer_ext=ext)
    if not found:
        return None
    other, line = found
    return signal(k, f"copy:{ev.fkey}:{other}", {"file": ev.rel, "other": other, "line": line})


def big_output(rule, run):
    """도구 결과가 아주 길다. / A very long tool result."""
    ev = run.ev
    if ev.kind != "post" or not ev.ok or ev.out_len < threshold(rule, 20000):
        return None
    return signal(ev.out_len, f"big:{ev.tool}:{ev.fkey or ev.sig}", {"tool": ev.tool, "chars": ev.out_len})


# ── 요청(사용자 메시지) ──

def request_split(rule, run):
    """짧은 요청이 짧은 시간 안에 잇달아. / Several short requests in a short time."""
    st = run.state
    if run.ev.kind != "prompt":
        return None
    max_chars, window = param(rule, "max_chars", 40), param(rule, "window_sec", 300)
    tail = []
    for p in reversed(st.get("prompts", [])):
        if p.get("ack") or p.get("cmd"):
            continue  # 대답 한 마디와 / 명령은 세지도 끊지도 않는다
        if p.get("len", 0) > max_chars:
            break
        tail.append(p)
    tail.reverse()
    tail = [p for p in tail if (seconds_since(p.get("at")) or 0) <= window]
    n = len(tail)
    if n < threshold(rule, 3):
        return None
    return signal(n, f"split:{tail[0].get('i')}", {"minutes": max(1, window // 60)})


def repeat_correction(rule, run):
    """같은 주제를 바로잡는 정정이 거듭. / Repeated corrections on the same topic."""
    st = run.state
    prompts = st.get("prompts", [])
    if run.ev.kind != "prompt" or not prompts or not prompts[-1].get("corr"):
        return None
    cur = prompts[-1]
    base = set(cur.get("tok", []))
    min_overlap = param(rule, "min_overlap", 0.1)
    n, first, adjacent = 1, cur.get("i"), True
    for p in reversed(prompts[:-1][-param(rule, "lookback", 10):]):
        if not p.get("corr"):
            if not p.get("ack"):
                adjacent = False
            continue
        if adjacent or jaccard(base, set(p.get("tok", []))) >= min_overlap:
            n += 1
            first = p.get("i")
            adjacent = True
    if n < threshold(rule, 2):
        return None
    return signal(n, f"corr:{first}", {})


def correction_to_rule(rule, run):
    """세션 첫 요청이 아닌데 바로잡는 말이 왔다: 규칙으로 남길 때. / A correction after earlier work: time to record it."""
    ev, st = run.ev, run.state
    prompts = st.get("prompts", [])
    if ev.kind != "prompt" or not prompts:
        return None
    cur = prompts[-1]
    if cur.get("ack") or cur.get("cmd"):
        return None
    if len(prompts) < 2 and ev.transcript_bytes < param(rule, "transcript_bytes", 4000):
        return None  # 세션의 첫 요청은 바로잡는 말이 아니다 / a session's first request corrects nothing
    text = ev.prompt or ""
    n = int(bool(cur.get("corr"))) + sum(1 for p in param(rule, "markers", GUIDANCE) if re.search(p, text, re.I))
    if n < threshold(rule, 1):  # 반응으로 기준이 오르면 표현이 더 많이 걸려야 알린다 / tuned by votes
        return None
    return signal(n, f"rec:{cur.get('i')}", {})


def topic_mix(rule, run):
    """긴 세션에 앞 요청들과 거의 안 겹치는 새 요청. / An unrelated new request in a long session."""
    ev, st = run.ev, run.state
    prompts = st.get("prompts", [])
    if ev.kind != "prompt" or len(prompts) < 2:
        return None
    long_session = st.get("turns", 0) >= threshold(rule, 30) or \
        ev.transcript_bytes >= param(rule, "transcript_bytes", 1_000_000)
    cur = prompts[-1]
    if not long_session or cur.get("len", 0) < param(rule, "min_chars", 20) or cur.get("ack") or cur.get("cmd"):
        return None
    tok = set(cur.get("tok", []))
    if len(tok) < 4:
        return None
    seen = set()
    for p in prompts[:-1]:
        seen.update(p.get("tok", []))
    share = len(tok & seen) / len(tok)
    if share >= param(rule, "max_overlap", 0.1):
        return None
    return signal(st.get("turns", 0), f"topic:{cur.get('i')}", {"turns": st.get("turns", 0)})


# ── 끝(Stop) ──

def no_verify(rule, run):
    """수정은 있었는데 설정한 검증 명령을 한 번도 안 돌렸다. / Edits but no verify command run."""
    st = run.state
    verify = run.ctx.get("verify") or {}
    if run.ev.kind != "stop" or not verify or st.get("verify_runs", 0) > 0:
        return None
    if st.get("edits", 0) < threshold(rule, 1):
        return None
    return signal(st.get("edits", 0), "noverify", {"names": ", ".join(sorted(verify))})


# ── 위임 ──

def delegation(rule, run):
    """이번 요청으로 위임이 시작됐다(맥락 주입용). / Delegation started with this prompt."""
    d = run.started
    if run.ev.kind != "prompt" or not d:
        return None
    items = ", ".join(f"\"{b['text']}\"" for b in d.get("boundaries", []))
    bounds = t("delegate.boundaries", run.lang, items=items) if items else ""
    return signal(1, f"del:{d['id']}", {"phrase": d.get("phrase") or d.get("task", ""), "task": d.get("task", ""),
                                        "boundaries": bounds})


def risky_action(rule, run):
    """위임 중에도 확인을 받아야 할 위험한 일. / Risky actions that need confirmation even when delegated."""
    ev, st = run.ev, run.state
    if ev.kind != "pre":
        return None
    d = delegate.active(st)
    if not d and not param(rule, "always", False):
        return None
    found = delegate.risky(ev, D(rule).get("params") or {}, run.key, run.inside_root, d)
    if not found:
        return None
    cats = [c for c, _ in found]
    bound = [b["text"] for b in (d or {}).get("boundaries", []) if b.get("category") in cats]
    label = ", ".join(t(f"category.{c}", run.lang) for c in cats)
    what = found[0][1]
    if bound:
        label += f" · {t('category.boundary', run.lang)}: \"{bound[0]}\""
    return signal(1, f"risk:{ev.tool_id or ev.sig}", {"category": label, "what": what})


def delegate_report(rule, run):
    """맡긴 작업이 끝날 때 끝 보고를 받는다(한 번). / Ask for the end report once when delegated work ends."""
    st = run.state
    d = delegate.active(st)
    if run.ev.kind != "stop" or not d:
        return None
    held = d.get("suppressed", [])
    if held:
        items = "; ".join(f"{x.get('text', '')} ({x.get('rule')})" for x in held[:8])
        sup = t("delegate.suppressed", run.lang, n=len(held), items=items)
    else:
        sup = t("delegate.none", run.lang)
    return signal(1, f"report:{d['id']}", {"task": d.get("task", ""), "suppressed": sup}, end_delegation=True)


DETECTORS = {
    "same_call_streak": same_call_streak,
    "same_error_streak": same_error_streak,
    "cycle": cycle,
    "small_edits_same_file": small_edits_same_file,
    "file_growth": file_growth,
    "copy_block": copy_block,
    "big_output": big_output,
    "request_split": request_split,
    "repeat_correction": repeat_correction,
    "correction_to_rule": correction_to_rule,
    "topic_mix": topic_mix,
    "no_verify": no_verify,
    "delegation": delegation,
    "risky_action": risky_action,
    "delegate_report": delegate_report,
}
