"""위임 예외: "알아서 해 줘"로 맡기면 그 작업에 한해 되묻기와 경고를 줄인다.
/ Delegation: "just do it" lowers questions and warnings for that one task.

- 위임은 '이 작업' 하나가 범위다. 끝: 끝 보고 뒤, 취소 표현, 새 주제, 한도, /clear.
- 함께 받은 부정·조건("지우지는 마")은 경계로 저장한다. 경계는 좁히기만 한다.
- 위임 중에도 위험한 일(지우기·배포·외부로 보내기·결제·비밀 정보·작업 폴더 밖)은 묻는다.
- 인용("'알아서 해'라고 하면?"), 질문, 남의 말("팀장님이 알아서 하래")은 위임으로 보지 않는다.
"""
import re

from ..core.paths import nfc
from ..core.fast import short
from ..core.fast import lazy_re
from ..core.textsim import tokens
from ..core.timeutil import now_iso

# 위임으로 볼 표현. 언어별 사전이고 판정 방식은 같다.
DELEGATE = [
    r"알아서\s*(?:잘\s*)?(?:해|하|처리|진행|판단|정해|골라|마무리|부탁)",
    r"(?:묻지|물어보지|질문하지)\s*(?:말고|마|않아도|않고)",
    r"확인\s*(?:안|않)\s*받아도", r"확인\s*(?:없이|안\s*하고)\s*(?:진행|해)",
    r"끝까지\s*(?:다\s*)?(?:해|진행|마무리|가|맡)", r"(?:다\s*)?맡길(?:게|께|래)", r"맡긴다",
    r"(?:네|니|너)가\s*판단", r"쭉\s*진행", r"중간에\s*(?:묻지|확인)", r"추천(?:안)?\s*대로", r"권장\s*대로",
    r"\bjust\s+do\s+it\b", r"\bdon'?t\s+ask\b", r"\bdo\s+not\s+ask\b", r"\bno\s+need\s+to\s+(?:ask|check\s+with\s+me)\b",
    r"\bwithout\s+asking\b", r"\buse\s+your\s+(?:own\s+)?judge?ment\b", r"\byou\s+decide\b", r"\byour\s+call\b",
    r"\brun\s+with\s+it\b", r"\bgo\s+ahead\s+and\s+finish\b", r"\bkeep\s+going\s+until\b", r"\bas\s+you\s+see\s+fit\b",
    r"\bwhatever\s+you\s+think\s+is\s+best\b",
]
CANCEL = [
    r"이제\s*(?:물어|확인)", r"(?:물어보고|묻고|확인\s*받고)\s*(?:해|진행)", r"(?:맡긴\s*거|위임)\s*(?:취소|끝|그만)",
    r"그만\s*맡길", r"알아서\s*하지\s*마",
    r"\bask\s+me\s+(?:first|before|again)\b", r"\bcheck\s+with\s+me\b", r"\bstop\s+delegating\b",
    r"\bcancel\s+(?:the\s+)?delegation\b", r"\bdon'?t\s+decide\s+for\s+me\b",
]
CONTINUE = lazy_re(r"^(?:계속|이어서|마저|go on|continue|keep going)", re.I)
COMMAND = lazy_re(r"^/(?:habitree:)?delegate\b\s*(.*)$", re.I | re.S)
_QUOTES = lazy_re(r"'[^'\n]*'|\"[^\"\n]*\"|‘[^’\n]*’|“[^”\n]*”|「[^」\n]*」|『[^』\n]*』|`[^`\n]*`")
_REPORTED_AFTER = lazy_re(r"^\s*(?:래|라고|라더|라네|란다|라\s*했|라고\s*했)")
_REPORTED_BEFORE = lazy_re(r"\b(?:said|says|told\s+me|told\s+us)\b[^.!?]{0,20}$", re.I)
_NEG_AFTER = lazy_re(r"^\s*(?:지\s*마|지\s*말|진\s*마)")
_SENT_END = lazy_re(r"[.!?\n。]")

# 경계: "~지는 마", "~하지 말고", "don't …". 묻기에 대한 말은 위임 그 자체라 뺀다.
_BOUND_KO = lazy_re(r"([^.,!?\n]{1,40}?(?:지는|지|진)\s*(?:마|말아|말고|마세요|말아요|마라))(?![가-힣])")
_BOUND_EN = lazy_re(r"\b(?:but\s+)?(?:don'?t|do\s+not|never)\s+([^,.;!?\n]{2,60})", re.I)
_ASKING = lazy_re(r"(묻|물어|질문|확인\s*받|확인\s*하|ask|check\s+with|confirm)", re.I)

# 경계·위험 범주 낱말(경계 문장을 범주로 나눌 때). / Words that map a boundary to a category.
BOUND_WORDS = {
    "delete": r"지우|삭제|없애|delete|remove|\brm\b|drop",
    "deploy": r"배포|푸시|push|deploy|release|publish|공개|올리",
    "external": r"보내|전송|메일|send|email|post|upload|업로드",
    "payment": r"결제|구매|pay|purchase|charge|돈",
    "secrets": r"비밀|개인정보|키를|토큰|password|secret|token|credential",
    "outside": r"밖|다른\s*폴더|outside",
}


def clean(prompt):
    """인용 부분을 지운 글. / Prompt with quoted parts removed."""
    return _QUOTES.sub(" ", nfc(prompt or ""))


def _matches(patterns, text):
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            yield m


def find_phrase(prompt):
    """위임 표현(맞은 글) 또는 None. 질문·남의 말·부정은 뺀다. / Delegation phrase or None."""
    text = clean(prompt)
    for m in _matches(DELEGATE, text):
        after = text[m.end():m.end() + 8]
        before = text[max(0, m.start() - 40):m.start()]
        if _REPORTED_AFTER.match(after) or _REPORTED_BEFORE.search(before) or _NEG_AFTER.match(after):
            continue
        end = _SENT_END.search(text, m.end())
        if end and text[end.start()] == "?":
            continue
        if not end and text.rstrip().endswith("?"):
            continue
        return m.group(0).strip()
    return None


def is_cancel(prompt):
    text = clean(prompt)
    return any(True for _ in _matches(CANCEL, text))


def command(prompt):
    """명시 명령 '/habitree:delegate …'. (켜기·끄기, 작업 글) 또는 None. / Explicit command."""
    m = COMMAND.match((prompt or "").strip())
    if not m:
        return None
    rest = m.group(1).strip()
    if re.match(r"^(off|끄기|끝|취소|stop|cancel)\b", rest, re.I):
        return "off", ""
    return "on", re.sub(r"^(on|켜기)\b\s*", "", rest, flags=re.I)


def boundaries(prompt):
    """함께 받은 경계 문장들. / Boundary clauses that came with the delegation."""
    text = clean(prompt)
    out = []
    for m in _BOUND_KO.finditer(text):
        clause = m.group(1).strip(" ,.")
        clause = re.sub(r"^(?:다만|단|그런데|근데|하지만|그리고)\s+", "", clause)
        if clause and not _ASKING.search(clause):
            out.append(clause)
    for m in _BOUND_EN.finditer(text):
        clause = m.group(0).strip(" ,.")
        if not _ASKING.search(m.group(1)):
            out.append(clause)
    seen, uniq = set(), []
    for b in out:
        if b not in seen:
            seen.add(b)
            uniq.append(b[:80])
    return uniq[:5]


def boundary_category(text):
    for cat, rx in BOUND_WORDS.items():
        if re.search(rx, text, re.I):
            return cat
    return "custom"


def path_words(prompt):
    """요청 안의 경로처럼 보이는 낱말. / Path-like words in the prompt."""
    return [w.strip("`'\"()[]<>,") for w in re.findall(r"[\w./\\-]*[/\\.][\w./\\-]+", nfc(prompt or ""))]


def start(state, phrase, prompt, by="natural", scope_paths=None, task=None, bounds=None):
    """상태에 위임을 기록한다. / Record the delegation in the session state."""
    task = (task if task is not None else " ".join(nfc(prompt or "").split()))[:120]
    bounds = boundaries(prompt or "") if bounds is None else [b[:80] for b in bounds]
    did = short(f"{now_iso()}{task}", 8)
    state["delegation"] = {
        "id": did, "active": True, "scope": "task", "task": task, "phrase": phrase or "", "granted_by": by,
        "started": now_iso(), "paths": list(scope_paths or []),
        "boundaries": [{"text": b, "category": boundary_category(b)} for b in bounds],
        "tokens": sorted(tokens(prompt or ""))[:80], "tools": 0, "suppressed": [], "notes": [],
    }
    return state["delegation"]


def end(state, reason):
    d = state.get("delegation")
    if not d or not d.get("active"):
        return None
    d["active"] = False
    d["ended"] = now_iso()
    d["end_reason"] = reason
    hist = state.setdefault("delegations", [])
    hist.append(d)
    del hist[:-5]
    state["delegation"] = None
    return d


def active(state):
    d = state.get("delegation")
    return d if d and d.get("active") else None


# ── 위험한 일 ──
DEFAULT_RISK = {
    "delete": [r"\brm\s", r"\brmdir\b", r"\bdel\s", r"\bRemove-Item\b", r"\bgit\s+clean\b", r"\bgit\s+reset\s+--hard\b",
               r"\bgit\s+branch\s+-D\b", r"\bgit\s+push\b[^\n]*--delete\b", r"\bshutil\.rmtree\b", r"\bunlink\b",
               r"\bDROP\s+(?:TABLE|DATABASE)\b", r"\bTRUNCATE\b"],
    "deploy": [r"\bgit\s+push\b", r"\bnpm\s+publish\b", r"\btwine\s+upload\b", r"\buv\s+publish\b",
               r"\bcargo\s+publish\b", r"\bgh\s+release\s+create\b", r"\bgh\s+pr\s+merge\b", r"--visibility\s+public",
               r"\bdocker\s+push\b", r"\bkubectl\s+apply\b", r"\bterraform\s+(?:apply|destroy)\b",
               r"\b(?:vercel|netlify|firebase|fly|flyctl)\b[^\n]*\bdeploy\b", r"\bnpm\s+run\s+deploy\b"],
    "external": [r"\bcurl\b[^\n]*(?:\s-X\s*(?:POST|PUT|PATCH|DELETE)|\s--data|\s-d\s|\s-F\s|--upload-file|\s-T\s)",
                 r"\bwget\b[^\n]*--post", r"\bscp\s", r"\brsync\b[^\n]*\S+:\S*", r"\bsendmail\b",
                 r"\bInvoke-(?:WebRequest|RestMethod)\b[^\n]*-Method\s+(?:Post|Put|Patch|Delete)"],
    "payment": [r"(?i)\b(?:stripe|paypal|checkout|purchase|billing)\b"],
    "secrets": [r"\bgit\s+add\b[^\n]*\.env\b", r"(?i)\bcat\b[^\n]*(?:\.ssh/|id_rsa|\.env\b)"],
}
DEFAULT_TOOL_RISK = {"external": r"(?i)(send|post|publish|upload|forward|reply|share|create_draft)",
                     "delete": r"(?i)(delete|trash|remove|drop)", "payment": r"(?i)(pay|charge|purchase|checkout)"}
DEFAULT_SECRET_PATH = r"(?i)(^|/)(\.env(\.|$)|id_rsa|id_ed25519|[^/]*\.pem$|credentials?(\.|$)|secrets?\.)"


def risky(ev, params, root_key_fn, inside_root, delegation):
    """위험한 일의 (범주, 무엇) 목록. / (category, what) pairs for a risky action."""
    found = []
    cats = params.get("categories") or DEFAULT_RISK
    cmd = ev.shell
    if cmd:
        for cat, pats in cats.items():
            if any(re.search(p, cmd, re.I) for p in pats):
                found.append((cat, " ".join(cmd.split())[:80]))
    if ev.tool.startswith("mcp__"):
        name = ev.tool.split("__")[-1]
        for cat, rx in (params.get("tool_categories") or DEFAULT_TOOL_RISK).items():
            if re.search(rx, name):
                found.append((cat, ev.tool))
    if ev.is_edit and ev.path:
        if not inside_root(ev.path):
            found.append(("outside", ev.path))
        elif re.search(params.get("secret_paths") or DEFAULT_SECRET_PATH, ev.rel or ""):
            found.append(("secrets", ev.rel))
        elif delegation and delegation.get("paths"):
            keys = [root_key_fn(p) for p in delegation["paths"]]
            if not any(ev.fkey == k or ev.fkey.startswith(k.rstrip("/") + "/") for k in keys):
                found.append(("outside_scope", ev.rel))
    seen, out = set(), []
    for cat, what in found:
        if cat not in seen:
            seen.add(cat)
            out.append((cat, what))
    return out
