"""심볼 추출: Python은 ast(정확), 그 밖의 언어는 패턴표(대략). / Symbol extraction: ast for Python, patterns elsewhere.

어느 추출기를 쓰든 같은 레코드를 낸다.
  name, kind, line, end, sig(시그니처), doc(첫 줄 설명), parent, start(장식자 포함 시작 줄), body(몸통 해시)
패턴은 data/symbols.json에 있다. 언어를 더할 때는 그 파일에 묶음 하나를 더한다.
"""
import ast
import hashlib
import json
import re
from collections import Counter
from functools import lru_cache
from importlib import resources

from . import langs

EXTRACT_VERSION = 1
MAX_SIG = 160
MAX_DOC = 160
MIN_BODY_LINES = 3  # 몸통 해시는 의미 있는 줄이 이만큼 있을 때만(중복 찾기용)
MAX_LINE = 1000  # 이보다 긴 줄은 압축된 코드로 보고 패턴을 맞추지 않는다
CONTAINERS = {"class", "struct", "interface", "trait", "impl", "module", "namespace", "object", "enum", "protocol",
              "extension", "actor", "record", "union", "mixin"}
METHOD_PARENTS = CONTAINERS - {"module", "namespace"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
HANGUL = re.compile(r"[가-힣]")
STRINGS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')
FENCE = re.compile(r"^\s*(```|~~~)")
DOC_MARK = re.compile(r"^(?:/\*\*+|/\*+|\*+/|\*+|///?|//!|#+|--+|;+|%+|')\s?")
TRIVIAL_DOC = re.compile(r"(?i)copyright|licen[cs]e|spdx|^-\*-|^!|^@")


@lru_cache(maxsize=1)
def _raw():
    return resources.files("habitree.data").joinpath("symbols.json").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def spec():
    """패턴표를 읽고 정규식을 미리 엮는다. / Load and compile the pattern table."""
    data = json.loads(_raw())
    by_lang = {}
    for gname, g in data["groups"].items():
        compiled = []
        for p in g["patterns"]:
            flags = re.IGNORECASE if "i" in p.get("flags", "") else 0
            compiled.append(dict(p, rx=re.compile(p["re"], flags)))
        group = dict(g, name=gname, compiled=compiled)
        for lang in g["languages"]:
            by_lang[lang] = group
    return {"by_lang": by_lang, "text_only": set(data.get("text_only", [])),
            "not_names": set(data.get("not_names", [])), "ref_stop": set(data.get("ref_stop", [])),
            "common_names": set(data.get("common_names", []))}


def engine_id():
    """패턴표·언어표·추출기 판이 바뀌면 달라지는 값(바뀌면 색인을 새로 만든다). / Changes force a full rebuild."""
    h = hashlib.sha256(_raw().encode("utf-8")).hexdigest()[:12]
    return f"x{EXTRACT_VERSION}-{h}-{langs.digest()}"


def is_code(lang):
    """코드로 볼 언어인가(문서·데이터 형식은 아님). / Is this a programming language (not prose or data)?"""
    return bool(lang) and lang not in spec()["text_only"]


def has_patterns(lang):
    return lang in spec()["by_lang"]


# ── 공용 ──

def _short(text, limit):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def doc_for(doc, lang):
    """'한국어 / English'처럼 두 언어로 쓴 설명이면 설정 언어 쪽만(토큰 절약). / Pick one side of a bilingual doc."""
    parts = [p.strip() for p in str(doc or "").rsplit(" / ", 1)]
    if len(parts) == 2 and all(parts):
        ko_side = [p for p in parts if HANGUL.search(p)]
        other = [p for p in parts if not HANGUL.search(p)]
        if len(ko_side) == 1 and len(other) == 1:
            return ko_side[0] if lang == "ko" else other[0]
    return doc or ""


def norm_line(line, marks):
    """중복 비교용 한 줄(공백 정리, 주석만 있는 줄은 빈 글). / Normalized line for duplicate checks."""
    s = line.strip()
    if not s or (marks and s.startswith(marks)):
        return ""
    return " ".join(s.split())


def body_hash(lines, marks):
    norm = [x for x in (norm_line(x, marks) for x in lines) if x]
    if len(norm) < MIN_BODY_LINES:
        return None
    return hashlib.sha256("\n".join(norm).encode("utf-8")).hexdigest()[:16]


def _indent(line):
    return len(line) - len(line.lstrip(" \t"))


# ── Python: ast ──

def _py_sig(node):
    deco = ""
    for d in node.decorator_list:
        name = ast.unparse(d)
        if name in ("property", "staticmethod", "classmethod") or name.endswith((".setter", ".getter")):
            deco += f"@{name} "
    if isinstance(node, ast.ClassDef):
        bases = [ast.unparse(b) for b in node.bases] + [f"{k.arg}={ast.unparse(k.value)}" for k in node.keywords]
        return f"{deco}class {node.name}({', '.join(bases)})" if bases else f"{deco}class {node.name}"
    head = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{deco}{head} {node.name}({ast.unparse(node.args)}){ret}"


def _py_doc(node):
    try:
        doc = ast.get_docstring(node, clean=True)
    except (TypeError, ValueError):
        return ""
    if not doc:
        return ""
    first = next((x.strip() for x in doc.split("\n") if x.strip()), "")
    return _short(first, MAX_DOC)


def _py_record(node, kind, lines, marks, parent=None):
    rec = {"name": node.name, "kind": kind, "line": node.lineno, "end": getattr(node, "end_lineno", node.lineno),
           "sig": _short(_py_sig(node), MAX_SIG)}
    doc = _py_doc(node)
    if doc:
        rec["doc"] = doc
    if parent:
        rec["parent"] = parent
    start = min([d.lineno for d in node.decorator_list] + [node.lineno])
    if start != node.lineno:
        rec["start"] = start
    if kind in ("function", "method"):
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]
        if body:
            h = body_hash(lines[body[0].lineno - 1:rec["end"]], marks)
            if h:
                rec["body"] = h
    return rec


def _py_const(node):
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    out = []
    for t in targets:
        if isinstance(t, ast.Name) and re.match(r"^_?[A-Z][A-Z0-9_]+$", t.id):
            sig = t.id
            if isinstance(node, ast.AnnAssign) and node.annotation is not None:
                sig += f": {ast.unparse(node.annotation)}"
            out.append({"name": t.id, "kind": "const", "line": node.lineno,
                        "end": getattr(node, "end_lineno", node.lineno), "sig": _short(sig, MAX_SIG)})
    return out


def _py_walk_top(body):
    """맨 위 문장(if·try 안 한 단계 포함). / Top-level statements, one level into if/try."""
    for node in body:
        yield node
        if isinstance(node, (ast.If, ast.Try)):
            for part in (node.body, node.orelse, getattr(node, "finalbody", []),
                         *[h.body for h in getattr(node, "handlers", [])]):
                for sub in part:
                    yield sub


def _py_refs(tree):
    """다른 파일의 정의를 썼을 수 있는 이름: 속성(mod.f, obj.m), from-import한 이름과 그 이름을 읽은 곳.
    지역 변수·매개변수 이름(ctx, path …)은 세지 않는다. ast.walk보다 빠르게 직접 돈다.
    / Names that may use other files' definitions: attributes and from-imported names (not locals)."""
    refs, names = Counter(), Counter()
    name_t, attr_t, imp_t, load_t, AST = ast.Name, ast.Attribute, ast.ImportFrom, ast.Load, ast.AST
    imported = {}
    stack = [tree]
    pop, push = stack.pop, stack.append
    while stack:
        node = pop()
        t = type(node)
        if t is name_t:
            if type(node.ctx) is load_t:
                names[node.id] += 1
            continue
        if t is attr_t:
            refs[node.attr] += 1
        elif t is imp_t:
            for a in node.names:
                refs[a.name] += 1
                imported[a.asname or a.name] = a.name  # 별칭으로 읽은 곳은 원래 이름으로 센다
        for field in node._fields:
            v = getattr(node, field, None)
            if type(v) is list:
                for x in v:
                    if isinstance(x, AST):
                        push(x)
            elif isinstance(v, AST):
                push(v)
    for local, original in imported.items():
        if names.get(local):
            refs[original] += names[local]
    return refs


def python_ast(text):
    tree = ast.parse(text)
    lines = text.split("\n")
    marks = ("#",)
    symbols = []
    for node in _py_walk_top(tree.body):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(_py_record(node, "function", lines, marks))
        elif isinstance(node, ast.ClassDef):
            symbols.append(_py_record(node, "class", lines, marks))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(_py_record(sub, "method", lines, marks, node.name))
                elif isinstance(sub, ast.ClassDef):
                    symbols.append(_py_record(sub, "class", lines, marks, node.name))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            symbols.extend(_py_const(node))
    refs = _py_refs(tree)
    symbols.sort(key=lambda s: s["line"])
    return {"extractor": "ast", "symbols": symbols, "refs": refs, "doc": _py_doc(tree)}


# ── 패턴: 그 밖의 언어 ──

def _brace_info(lines, marks, pairs):
    """줄마다 (시작 깊이, 끝 깊이, 여는 괄호가 있나, 코드 부분). 글자열·주석은 지우고 센다(대략)."""
    starts, ends, opens, codes = [], [], [], []
    depth, closing = 0, None
    for line in lines:
        starts.append(depth)
        s = line if len(line) <= MAX_LINE else ""
        if closing:
            k = s.find(closing)
            if k < 0:
                ends.append(depth)
                opens.append(False)
                codes.append("")
                continue
            s = s[k + len(closing):]
            closing = None
        s = STRINGS.sub('""', s)
        changed = True
        while changed:
            changed = False
            for a, b in pairs:
                k = s.find(a)
                if k < 0:
                    continue
                e = s.find(b, k + len(a))
                if e < 0:
                    s, closing = s[:k], b
                else:
                    s = s[:k] + " " + s[e + len(b):]
                    changed = True
                break
        for m in marks:
            k = s.find(m)
            while k >= 0 and k > 0 and not s[k - 1].isspace():
                k = s.find(m, k + 1)
            if k >= 0:
                s = s[:k]
        op, cl = s.count("{"), s.count("}")
        depth += op - cl
        ends.append(depth)
        opens.append(op > 0)
        codes.append(s)
    return starts, ends, opens, codes


def _brace_end(i, info, n):
    starts, ends, opens, codes = info
    base, opened = starts[i], False
    for j in range(i, n):
        if opens[j] or ends[j] > base:
            opened = True
        if opened and ends[j] <= base:
            return j
        if not opened and (";" in codes[j] or j - i >= 10):
            return j if ";" in codes[j] else i
    return n - 1 if opened else i


def _indent_end(lines, i):
    ind, last = _indent(lines[i]), i
    for j in range(i + 1, len(lines)):
        if not lines[j].strip():
            continue
        if _indent(lines[j]) <= ind:
            break
        last = j
    return last


def _end_end(lines, i):
    ind, last = _indent(lines[i]), i
    for j in range(i + 1, len(lines)):
        st = lines[j].strip()
        if not st:
            continue
        if _indent(lines[j]) == ind and re.match(r"end\b", st):
            return j
        if _indent(lines[j]) <= ind:
            return last
        last = j
    return last


def _doc_above(lines, i, marks):
    j = i - 1
    while j >= 0 and lines[j].strip().startswith(("@", "#[", "[")):  # 장식자·속성 줄은 건너뛴다
        j -= 1
    got = []
    while j >= 0:
        st = lines[j].strip()
        if not st:
            break
        if st.startswith(("/*", "*", "///", "//!")) or (marks and st.startswith(marks)):
            got.append(st)
            j -= 1
            continue
        break
    for st in reversed(got):
        t = DOC_MARK.sub("", st)
        t = re.sub(r"\s*\*+/\s*$", "", t).strip()
        if t and not TRIVIAL_DOC.search(t):
            return _short(t, MAX_DOC)
    return ""


def _sig(lines, i, kind):
    s = lines[i].strip()
    k = i + 1
    while s.count("(") > s.count(")") and k < len(lines) and k <= i + 5:
        s += " " + lines[k].strip()
        k += 1
    if kind in ("const", "type"):
        s = re.split(r"(?<![=!<>:])=(?![=>])", s, maxsplit=1)[0]
    depth = 0
    for pos, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "{" and depth <= 0 and pos > 0:
            s = s[:pos]
            break
    s = s.rstrip().rstrip(":{").rstrip()
    return _short(s, MAX_SIG)


def _clean_name(name, kind):
    name = name.strip()
    if kind == "section":
        return _short(name.replace("`", "").strip("# "), 120)
    return name.strip("\"'`[]")


def regex_extract(group, text, lang):
    lines = text.split("\n")
    n = len(lines)
    marks = tuple(langs.comments(lang))
    pairs = langs.blocks(lang)
    mode = group.get("block", "line")
    not_names = spec()["not_names"]
    info = _brace_info(lines, marks, pairs) if mode == "brace" else None
    fences, in_fence = group.get("fences"), False
    stack, symbols = [], []
    for i, line in enumerate(lines):
        if fences and FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or len(line) > MAX_LINE:
            continue
        st = line.strip()
        if not st or (marks and st.startswith(marks) and mode != "heading"):
            continue
        while stack and stack[-1][1] < i:
            stack.pop()
        top = stack[-1] if stack else None
        for p in group["compiled"]:
            if p.get("top") and top:
                continue
            if p.get("inside") and (not top or top[0]["kind"] not in p["inside"]):
                continue
            if p.get("member") and info is not None and info[0][i] != (top[2] if top else 0):
                continue
            m = p["rx"].match(line)
            if not m:
                continue
            gd = m.groupdict()
            kind = gd.get("kind") or p.get("kind", "function")
            kind = p.get("kinds", {}).get(kind, kind)
            name = _clean_name(gd.get("name") or "", kind)
            if not name or (kind != "section" and name.lower() in not_names):
                continue
            if kind == "function" and top and top[0]["kind"] in METHOD_PARENTS:
                kind = "method"
            pmode = p.get("block", mode)
            if pmode == "brace" and info is not None:
                end = _brace_end(i, info, n)
            elif pmode == "indent":
                end = _indent_end(lines, i)
            elif pmode == "end":
                end = _end_end(lines, i)
            else:
                end = i
            rec = {"name": name, "kind": kind, "line": i + 1, "end": end + 1,
                   "sig": _short(st, MAX_SIG) if kind == "section" else _sig(lines, i, kind)}
            parent = gd.get("parent") or (top[0]["name"] if top else None)
            if parent:
                rec["parent"] = parent
            if kind == "section":
                rec["level"] = len(gd.get("level") or "#")
            else:
                doc = _doc_above(lines, i, marks)
                if doc:
                    rec["doc"] = doc
                if kind in ("function", "method") and end > i:
                    h = body_hash(lines[i + 1:end + 1], marks)
                    if h:
                        rec["body"] = h
            symbols.append(rec)
            if kind in CONTAINERS and end > i:
                stack.append((rec, end, (info[0][i] + 1) if info is not None else 0))
            break
    if mode == "heading":
        _section_ends(symbols, lines)
    refs = Counter()
    if group.get("refs", True):
        stop = spec()["ref_stop"]
        for line in lines:
            s = line.strip()
            if not s or len(line) > MAX_LINE or (marks and s.startswith(marks)):
                continue
            for w in IDENT.findall(line):
                if len(w) >= 3 and w not in stop:
                    refs[w] += 1
    doc = ""
    if mode == "heading":
        doc = next((s["name"] for s in symbols), "")
    else:
        doc = _file_doc(lines, marks)
    return {"extractor": "regex", "symbols": symbols, "refs": refs, "doc": doc}


def _section_ends(symbols, lines):
    """제목 구역의 끝: 같거나 높은 단계의 다음 제목 바로 앞. 설명은 첫 문단 첫 줄."""
    secs = [s for s in symbols if s["kind"] == "section"]
    for k, s in enumerate(secs):
        nxt = next((t for t in secs[k + 1:] if t["level"] <= s["level"]), None)
        end = (nxt["line"] - 1) if nxt else len(lines)
        while end > s["line"] and not lines[end - 1].strip():
            end -= 1
        s["end"] = end
        stop = secs[k + 1]["line"] - 1 if k + 1 < len(secs) else len(lines)
        for j in range(s["line"], stop):
            t = lines[j].strip()
            if t and not t.startswith(("#", "```", "~~~", "|", "<!--", "---")):
                s["doc"] = _short(t, MAX_DOC)
                break


def _file_doc(lines, marks):
    for line in lines[:30]:
        s = line.strip()
        if not s or s.startswith("#!"):
            continue
        if s.startswith(("/*", "*", "///", "//!")) or (marks and s.startswith(marks)):
            t = re.sub(r"\s*\*+/\s*$", "", DOC_MARK.sub("", s)).strip()
            if t and not TRIVIAL_DOC.search(t):
                return _short(t, MAX_DOC)
            continue
        break
    return ""


def extract(lang, text):
    """{extractor, symbols, refs, doc}. 패턴이 없는 언어는 빈 결과. / Extract symbols for one file."""
    group = spec()["by_lang"].get(lang)
    if group is None:
        return {"extractor": "", "symbols": [], "refs": Counter(), "doc": ""}
    if group.get("extractor") == "ast":
        try:
            return python_ast(text)
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            pass  # 이 Python이 못 읽는 문법이면 패턴으로 물러선다
    return regex_extract(group, text, lang)
