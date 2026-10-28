"""리팩토링 후보: 이미 있는 색인·참조 그래프·중복·git 기록을 읽고 판단만 얹는다. 코드는 고치지 않는다.
/ Refactoring candidates read from the index, reference graph, duplicates and git history. Read only.

  concentration 몰림     중앙값보다 훨씬 큰 파일·함수, 심볼이 너무 많은 파일(변경 횟수로 순서)
  duplication   중복     같은 몸통, 같은 글(map dupes)
  fragmentation 흩어짐   다른 폴더의 같은 이름, 늘 함께 바뀌는 파일(git), 서로 참조하는 파일
  simplify      덜어내기 안 쓰이는 코드·파일, 한 곳에서만 쓰는 짧은 층, 서로만 쓰는 작은 파일 무리
기준값은 base 꾸러미 code/structure 규칙의 detect에서 읽는다(rules hit·miss로 조정된다).
"""
import re
from collections import Counter, defaultdict
from itertools import zip_longest
from statistics import median

from ..core import HabitreeError
from ..core import io as hio
from ..core.paths import resolve
from ..core.ruledb import RuleDB, load_pack
from . import churn, dupes, extract
from .index import is_test_path
from .rank import _path_words, parse_focus, path_hit, uses, word_hit
from .search import read_body

KINDS = ("concentration", "duplication", "fragmentation", "simplify")
RULE_OF = {"concentration": "code.structure.concentration", "duplication": "code.structure.duplication",
           "fragmentation": "code.structure.fragmentation", "simplify": "code.structure.fragmentation"}
DEFS = {"function", "class", "struct", "interface", "trait", "enum"}
# 바깥에서 부르는 입구일 수 있는 파일(진입점·패키지 입구·설정). 지우기 후보에서 빼고, 큰 정리를 막는다.
ENTRY = re.compile(r"(?:^|[._-])(?:__init__|__main__|main|index|app|cli|setup|manage|conftest|server|wsgi|asgi|"
                   r"lib|mod|config|conf|noxfile|webpack|vite|rollup|babel|jest|eslint)(?:[._-]|$)", re.I)
TOKEN = re.compile(r"[\w$]+")
CALL = re.compile(r"^(?:return\s+|await\s+)*([\w.$]+)\s*\(")
NOISE = ("#", "//", "/*", "*", '"""', "'''", "}", ")")


def _base(rel):
    return rel.rsplit("/", 1)[-1]


def _dir(rel):
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def _span(s):
    return s.get("end", s["line"]) - s.get("start", s["line"]) + 1


def _lines(p, files):
    return sum(p.code[f]["lines"] for f in files)


def criteria(ctx):
    """규칙 id → 기준값. 프로젝트 규칙 DB에 없으면 base 꾸러미 기본값. 쉬거나 폐기한 규칙은 뺀다.
    / Rule id → thresholds from detect; falls back to the bundled base pack; inactive rules are skipped."""
    pack = {r["id"]: r for r in load_pack("base")["rules"]}
    try:
        mine = {r["id"]: r for r in RuleDB.load(ctx.p(ctx.get("rules.db")), ctx.lang).rules}
    except HabitreeError:
        mine = {}
    out = {}
    for rid in set(RULE_OF.values()):
        r = mine.get(rid) or pack[rid]
        d = r.get("detect") or {}
        if r.get("status", "active") == "active" and d:
            out[rid] = dict(d.get("params") or {}, threshold=d.get("threshold", 1), level=d.get("severity", "info"),
                            rule=rid, message=r.get("message") or {})
    return out


class Project:
    """여러 판단이 함께 보는 사실(한 번만 계산). / Facts shared by every check, computed once."""

    def __init__(self, ctx, index):
        self.ctx, self.index = ctx, index
        self.files = index.get("files", {})
        self.code = {r: rec for r, rec in self.files.items()
                     if extract.is_code(rec.get("lang")) and not rec.get("skip") and rec.get("lines")}
        self.prod = sorted(r for r in self.code if not is_test_path(r))
        self.edges = uses(index)[1]
        self.users, self.by_name, self.tested = defaultdict(set), defaultdict(set), set()
        common = extract.spec()["common_names"]  # run·get 같은 흔한 이름은 쓰는 곳 수를 부풀린다
        for src, name, _, dsts in self.edges:
            for d in dsts:
                self.by_name[(d, name)].add(src)  # 지우기 판정은 보수적으로: 흔한 이름도 '쓰임'으로 본다
                if is_test_path(src):
                    self.tested.add(d)
                elif name not in common:
                    self.users[d].add(src)
        self.test_names = [_base(r).lower() for r in self.files if is_test_path(r)]
        self.log = churn.commits(ctx.root, ctx.get("map.churn_commits", 2000))
        self.changes = Counter(f for c in self.log or () for f, _ in c)
        self.verify = sorted(ctx.get("verify") or {})

    def fan_in(self, files, names=()):
        """쓰는 파일 수(시험 제외). names를 주면 그 이름을 쓰는 파일만. / Distinct non-test users."""
        if names:
            got = {u for f in files for n in names for u in self.by_name.get((f, n), ()) if not is_test_path(u)}
        else:
            got = set().union(*(self.users[f] for f in files))
        return len(got - set(files))

    def has_tests(self, files):
        """시험이 이 파일의 이름을 쓰거나, 시험 파일 이름에 이 모듈 이름이 들었나(CLI로 시험하는 경우).
        / A test uses its names, or a test file is named after the module."""
        stems = [_base(f).split(".")[0].lower() for f in files]
        return any(f in self.tested for f in files) or any(
            len(st) >= 3 and st in t for st in stems for t in self.test_names)

    def busy(self, files, top):
        """최근 자주 바뀜: 변경 횟수가 중앙값을 넘고 위에서 top% 안. 아니면 0. / Change count if in the top%."""
        vals = sorted((self.changes[r] for r in self.prod if self.changes[r]), reverse=True)
        n = max((self.changes[f] for f in files), default=0)
        if not vals or n <= median(vals):
            return 0
        return n if n >= vals[max(0, -(-len(vals) * top // 100) - 1)] else 0


def _cand(kind, sub, files, spread, stake, weight=None, **facts):
    """후보 하나. stake = 이 문제로 읽고 고쳐야 하는 줄 수, spread = 문제가 있는 곳의 수. / One candidate."""
    return {"kind": kind, "sub": sub, "files": sorted(set(files)), "spread": spread,
            "weight": stake if weight is None else weight, "facts": dict(facts, n=stake, k=spread)}


def _groups(pairs):
    """선 (a, b, …)으로 이어진 묶음. / Connected groups from pairs."""
    up = {}

    def top(x):
        while up.setdefault(x, x) != x:
            up[x] = up[up[x]]
            x = up[x]
        return x
    for a, b, *_ in pairs:
        up[top(a)] = top(b)
    comps = defaultdict(list)
    for x in list(up):
        comps[top(x)].append(x)
    return [sorted(v) for v in comps.values()]


def _seams(symbols):
    """이미 있는 경계: 맨 위 클래스(2개 이상일 때), 같은 접두어 함수 묶음. / Seams that already exist."""
    tops = [s for s in symbols if not s.get("parent")]
    classes = [s["name"] for s in tops if s["kind"] in DEFS - {"function"}]
    pre = Counter(re.split(r"_|(?<=[a-z])(?=[A-Z])", s["name"].strip("_"))[0].lower()
                  for s in tops if s["kind"] == "function")
    groups = [f"{k}_*" for k, v in pre.most_common(3) if v >= 2 and len(k) >= 2]
    return (classes[:3] if len(classes) >= 2 else []) + groups


def concentration(p, c):
    syms = {r: sorted((s for s in p.code[r].get("symbols", ()) if s["kind"] != "section"), key=lambda s: s["line"])
            for r in p.prod}
    funcs = {}
    for r, ss in syms.items():  # 끝 줄을 모르는 패턴 언어는 다음 심볼까지의 거리(대략)
        exact = p.code[r].get("extractor") == "ast"
        funcs[r] = [(_span(s) if exact or s.get("end", s["line"]) > s["line"] else
                     (ss[i + 1]["line"] if i + 1 < len(ss) else p.code[r]["lines"] + 1) - s["line"], s["name"])
                    for i, s in enumerate(ss) if s["kind"] in ("function", "method")]
    every = [ln for v in funcs.values() for ln, _ in v]
    if not p.prod:
        return []
    x = c["threshold"]
    med = (median(p.code[r]["lines"] for r in p.prod), median(len(v) for v in syms.values()), median(every or [0]))
    lim = (max(c.get("min_file_lines", 300), x * med[0]), max(c.get("min_symbols", 40), x * med[1]),
           max(c.get("min_func_lines", 50), x * med[2]))
    out = []
    for r in p.prod:
        n, k = p.code[r]["lines"], len(syms[r])
        big = sorted(((ln, nm) for ln, nm in funcs[r] if ln >= lim[2]), reverse=True)
        whole = n >= lim[0] or k >= lim[1]
        if not whole and not big:
            continue
        stake = n if whole else big[0][0]  # 핫스팟처럼 줄 수 × 변경 횟수로 순서를 정한다
        out.append(_cand("concentration", "file" if whole else "function", [r], len(big) + whole, stake,
                         stake * max(1, p.changes[r]), file=r, lines=n,
                         median=round(med[0]), x=round(n / med[0], 1) if med[0] else 0, symbols=k,
                         funcs=[[nm, ln] for ln, nm in big[:3]], fmed=round(med[2]), changes=p.changes[r],
                         seams=_seams(syms[r]) if whole else [], names=[nm for _, nm in big[:3]]))
    return out


def duplication(p, c):
    win = c["threshold"]
    res = dupes.find_dupes(p.ctx.root, p.index, win)
    out, spans = [], []

    def ok(r):
        return r in p.code and not is_test_path(r)
    for g in res["same_body"]:
        g = [(r, s) for r, s in g if ok(r)]
        ln = _span(g[0][1]) if g else 0
        if len(g) < 2 or ln < win:
            continue
        spans += [(r, s["line"], s.get("end", s["line"])) for r, s in g]
        out.append(_cand("duplication", "same_body", [r for r, _ in g], len(g), ln * (len(g) - 1),
                         lines=ln, where=[f"{r}:{s['line']} {s['name']}" for r, s in g[:4]],
                         names=[s["name"] for _, s in g], keep=f"{g[0][0]}:{g[0][1]['name']}",
                         other=f"{g[1][0]}:{g[1][1]['name']}"))
    pairs = defaultdict(list)
    for a, a1, a2, b, b1, b2, n in res["clones"]:
        inside = all(any(f == r and s <= u and v <= e for r, s, e in spans) for f, u, v in ((a, a1, a2), (b, b1, b2)))
        if ok(a) and ok(b) and not inside:  # 같은 몸통 함수 안의 같은 글은 이미 위에서 묶었다
            pairs[tuple(sorted({a, b}))].append((n, f"{a}:{a1}-{a2}", f"{b}:{b1}-{b2}"))
    for files, blocks in pairs.items():
        n = sum(b[0] for b in blocks)
        out.append(_cand("duplication", "clone", files, 2 * len(blocks), n, lines=n,
                         where=[w for b in blocks[:2] for w in b[1:]], keep=files[0], other=files[-1]))
    return out


def fragmentation(p, c):
    out, common = [], extract.spec()["common_names"]
    named = defaultdict(list)
    for r in p.prod:
        for s in p.code[r].get("symbols", ()):
            if s["kind"] in DEFS and not s.get("parent") and len(s["name"]) >= 4 and s["name"] not in common:
                named[s["name"]].append((r, s))
    for name, g in sorted(named.items()):
        files = {r for r, _ in g}
        sigs, bodies = {s.get("sig") for _, s in g}, {s.get("body") for _, s in g}
        if not 2 <= len(files) <= c.get("max_defs", 5) or (len({_dir(r) for r in files}) < 2 and len(sigs) > 1):
            continue  # 같은 폴더의 같은 이름은 시그니처까지 같을 때만(따로 만든 도우미)
        if len(bodies) == 1 and None not in bodies:
            continue  # 같은 몸통은 중복이 맡는다
        out.append(_cand("fragmentation", "same_name", files, len(files), sum(_span(s) for _, s in g),
                         name=name, where=sorted(files)[:4], names=[name]))
    if p.log:  # 늘 함께 바뀌는 다른 폴더의 파일(code-maat의 coupling 정의를 따름)
        revs, shared = Counter(), Counter()
        for commit in p.log:
            if len(commit) > c.get("max_changeset", 30):
                continue
            fs = sorted({f for f, _ in commit if f in p.code and not is_test_path(f)})
            revs.update(fs)
            shared.update((a, b) for i, a in enumerate(fs) for b in fs[i + 1:])
        links = [(a, b, n, round(200 * n / (revs[a] + revs[b]))) for (a, b), n in shared.items()
                 if n >= c["threshold"] and min(revs[a], revs[b]) >= c.get("min_revs", 5) and _dir(a) != _dir(b)]
        links = [x for x in links if x[3] >= c.get("min_coupling", 30)]
        for comp in _groups(links):
            ls = sorted((x for x in links if x[0] in comp), key=lambda x: (-x[2], x[0]))
            out.append(_cand("fragmentation", "coupling", comp, len(comp), _lines(p, comp),
                             pairs=[list(x) for x in ls[:3]]))
    one, code = defaultdict(set), set(p.code)  # 한 파일에만 정의된 이름만 본다(이름이 겹치면 거짓 고리가 생긴다)
    for src, name, _, dsts in p.edges:
        if src in code and not is_test_path(src) and len(dsts) == 1 and name not in common and len(name) >= 4:
            one[src] |= dsts & code
    mutual = sorted({tuple(sorted((a, b))) for a, bs in one.items() for b in bs
                     if a in one.get(b, ()) and _dir(a) != _dir(b)})
    for comp in _groups(mutual):
        out.append(_cand("fragmentation", "mutual", comp, len(comp), _lines(p, comp),
                         where=[f"{a} <-> {b}" for a, b in mutual if a in comp][:3]))
    return out


def _mentions(p, words):
    """{낱말: {파일: 횟수}}: 색인한 모든 글 파일에서. 덜어내기 후보가 있을 때만 한 번 읽는다(문자열 호출·문서 언급).
    / Where each word appears in any indexed text file; read once, only when there are removal candidates."""
    seen = defaultdict(Counter)
    plain = {w for w in words if re.fullmatch(r"[\w$]+", w)}
    odd = set(words) - plain  # 'build-docs'처럼 낱말로 안 나뉘는 파일 이름은 글자 그대로 찾는다
    for rel, rec in p.files.items() if words else ():
        path = resolve(p.ctx.root, rel) if rec.get("lines") and not rec.get("skip") else None
        try:
            text = hio.read_text(path) if path else ""
        except OSError:
            continue
        for w in TOKEN.findall(text):
            if w in plain:
                seen[w][rel] += 1
        for w in odd:
            if w in text:
                seen[w][rel] += text.count(w)
    return seen


def _forwards(p, r, s, defined):
    """몸통이 한 줄이고 그 줄이 프로젝트의 다른 정의를 부르기만 하는가(넘겨주기만 하는 층). / A pure forwarder?"""
    got = read_body(p.ctx.root, r, s)
    body = [x.strip() for x in (got[0] if got else [])[1:] if x.strip() and not x.strip().startswith(NOISE)]
    m = CALL.match(body[0]) if len(body) == 1 else None
    name = m.group(1).rsplit(".", 1)[-1] if m else ""
    return bool(name) and name != s["name"] and name in defined


def simplify(p, c):
    out = []
    tops = [(r, s) for r in p.prod if not ENTRY.search(_base(r)) for s in p.code[r].get("symbols", ())
            if s["kind"] in DEFS and not s.get("parent") and "start" not in s and not s["name"].startswith("__")
            and len(s["name"]) >= 3]  # 장식자가 붙은 정의는 등록되어 불릴 수 있어 뺀다
    once = Counter(s["name"] for r in p.prod for s in p.code[r].get("symbols", ()) if not s.get("parent"))
    quiet = [(r, s) for r, s in tops if not p.by_name.get((r, s["name"]))]
    thin = [(r, s, next(iter(p.by_name[(r, s["name"])]))) for r, s in tops  # 몸통 = 정의 줄·설명 줄을 뺀 줄
            if once[s["name"]] == 1 and _span(s) - 1 - bool(s.get("doc")) <= c.get("wrapper_lines", 2)
            and len(p.by_name.get((r, s["name"]), ())) == 1]
    defined = {s["name"] for r in p.prod for s in p.code[r].get("symbols", ())}
    thin = [(r, s, u) for r, s, u in thin if not is_test_path(u) and _forwards(p, r, s, defined)]
    alone = [r for r in p.prod if not p.users[r] and r not in p.tested and not ENTRY.search(_base(r))]
    stems = {r: _base(r).split(".")[0] for r in alone}
    seen = _mentions(p, {s["name"] for _, s in quiet} | {s["name"] for _, s, _ in thin} | set(stems.values()))
    dead = [r for r in alone if set(seen.get(stems[r], {})) <= {r}]
    for r in dead:
        out.append(_cand("simplify", "unused_file", [r], 1, _lines(p, [r]), file=r, lines=_lines(p, [r]), stem=stems[r],
                         names=[stems[r]]))
    per = defaultdict(list)
    for r, s in quiet:
        if r not in dead and dict(seen.get(s["name"], {})) == {r: 1}:
            per[(r, "unused")].append((s["name"], _span(s), ""))
    for r, s, u in thin:  # 제 파일 안에서는 안 쓰고, 쓰는 파일에서도 한 번(가져오기 한 줄 + 부르기 한 번)
        if seen.get(s["name"], {}).get(r, 0) <= 1 and seen.get(s["name"], {}).get(u, 0) <= 2:
            per[(r, "wrapper")].append((s["name"], _span(s), u))
    for (r, sub), items in sorted(per.items()):
        users = sorted({u for _, _, u in items if u})
        out.append(_cand("simplify", sub, [r] + users, len(items), sum(n for _, n, _ in items), file=r,
                         where=[nm + (f"(→ {u})" if u else "") for nm, _, u in items[:4]],
                         names=[nm for nm, _, _ in items], user=", ".join(users[:2])))
    tiny = {r for r in p.prod if p.code[r]["lines"] <= c.get("tiny_lines", 20) and not ENTRY.search(_base(r))}
    tiny -= set(dead)
    links = {tuple(sorted((src, d))) for src, _, _, dsts in p.edges for d in dsts
             if src in tiny and d in tiny and src != d}
    grouped = set()
    for comp in _groups(links):
        if len(comp) >= c.get("tiny_group", 3) and p.fan_in(comp) <= 1:
            grouped |= set(comp)
            out.append(_cand("simplify", "tiny", comp, len(comp), _lines(p, comp), where=comp[:4]))
    for r in sorted(tiny - grouped):
        if len(p.users[r]) == 1:
            u = next(iter(p.users[r]))
            out.append(_cand("simplify", "lonely", [r, u], 1, _lines(p, [r]), file=r, user=u, lines=_lines(p, [r])))
    return out


FINDERS = {"concentration": concentration, "duplication": duplication, "fragmentation": fragmentation,
           "simplify": simplify}


def decide(p, x, c, mode="auto"):
    """작은 단계(mini)와 큰 정리(bold) 중 무엇을 권할지와 이유. 기본은 작은 단계. / Pick mini or bold, with reasons."""
    files, why = x["files"], []
    named = x["sub"] in ("function", "same_body", "same_name", "unused", "wrapper")
    fan = p.fan_in(files, x["facts"].get("names") if named else ())
    if not p.verify:
        why.append(("no_verify", {}))
    if x["sub"] not in ("unused", "unused_file") and not p.has_tests(files):
        why.append(("no_tests", {}))
    if fan > c.get("fan_in_max", 5):
        why.append(("many_users", {"n": fan, "max": c.get("fan_in_max", 5)}))
    if any(ENTRY.search(_base(f)) for f in files):
        why.append(("public", {}))
    busy = p.busy(files, c.get("busy_top", 10))
    if busy:
        why.append(("busy", {"n": busy}))
    wide = x["spread"] >= c.get("bold_spread", 3)
    safety = [w for w, _ in why if w in ("no_verify", "no_tests")]
    if mode in ("mini", "bold"):
        pick, why = mode, [("forced", {})] + why
    else:
        pick = "bold" if wide and not why else "mini"
        why = why or [("wide" if wide else "local", {"n": x["spread"]})]
    return dict(x, mode=pick, why=why, fan_in=fan, safety=safety)


def advise(ctx, index, focus=None, mode="auto"):
    """(후보 목록, Project). 같은 파일의 덜어낼 것은 몰림 후보의 첫 단계로 붙인다. 종류마다 번갈아 늘어놓되
    한 바퀴 안에서는 경고 등급 종류가 먼저다. / (candidates, project): removals in the same file go first;
    kinds take turns, warn-level kinds first in each round."""
    p = Project(ctx, index)
    p.crit = crit = criteria(ctx)
    found = {}
    for kind in KINDS:
        c = crit.get(RULE_OF[kind])
        found[kind] = [dict(x, rule=c["rule"], level=c["level"]) for x in FINDERS[kind](p, c)] if c else []
    trim = defaultdict(list)
    for x in found["simplify"]:
        if x["sub"] in ("unused", "wrapper"):
            trim[x["facts"]["file"]].append(x)
    for x in found["concentration"]:
        x["trim"] = trim.pop(x["facts"]["file"], [])
    kept = {id(t) for v in trim.values() for t in v}
    found["simplify"] = [x for x in found["simplify"] if x["sub"] not in ("unused", "wrapper") or id(x) in kept]
    if focus:
        paths, words = parse_focus(index, focus)
        for kind in KINDS:
            found[kind] = [x for x in found[kind] if any(path_hit(f, paths) or word_hit(_path_words(f), words)
                                                         for f in x["files"])
                           or any(word_hit(n, words) for n in x["facts"].get("names", []))]
    kinds = sorted((k for k in KINDS if found[k]), key=lambda k: found[k][0]["level"] == "info")
    lists = [sorted(found[k], key=lambda x: (-x["weight"], x["files"])) for k in kinds]
    order = [x for row in zip_longest(*lists) for x in row if x]
    return [decide(p, x, crit[x["rule"]], mode) for x in order], p
