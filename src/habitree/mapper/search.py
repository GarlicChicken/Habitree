"""찾기: 이미 있는 함수·클래스·문서 구역을 이름과 설명으로 찾는다. / Find existing symbols by name and description.

- 이름은 snake_case·camelCase를 낱말로 나눠 맞춘다(readText → read, text).
- 영어 낱말은 앞부분만 맞아도 찾는다(rul → rule, rules). 복수형처럼 끝이 조금 다른 것도 찾는다(rules → rule).
- 한국어는 두 글자 묶음으로 맞춘다. 조사가 붙어도 찾는다('인증을'로 '인증'을, '인증'으로 '인증을'을).
- 결과는 세 단계로 낸다: 1 한 줄 요약, 2 시그니처·설명, 3 몸통까지.
"""
import bisect
import math
import os
import re
from collections import defaultdict

from ..core import io as hio
from ..core.paths import resolve
from ..core.textsim import tokens
from ..core.timeutil import show as show_time
from .extract import doc_for
from .index import inside_root, is_test_path, totals

FIELD_W = {"name": 3.0, "parent": 1.0, "path": 0.8, "doc": 1.2, "sig": 0.8}
KIND_W = {"const": 0.8, "section": 0.8, "file": 0.7}
HANGUL = re.compile(r"[가-힣]")
NORM = re.compile(r"[^0-9a-z가-힣]+")
MAX_BODY_LINES = 80
MAX_PREFIX = 200


def _short(text, limit):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _path_words(rel):
    return re.sub(r"[/._\-]+", " ", rel)


def _docs(index):
    """찾을 대상: 파일 하나마다 파일 자체 + 그 안의 심볼. / Searchable entries."""
    out = []
    for rel, rec in sorted(index.get("files", {}).items()):
        name = rel.rsplit("/", 1)[-1]
        out.append((rel, {"name": name, "kind": "file", "line": 1, "end": rec.get("lines", 1) or 1,
                          "sig": rel, "doc": rec.get("doc", "")}, rec))
        for s in rec.get("symbols", ()):
            out.append((rel, s, rec))
    return out


def _fields(rel, s):
    return {"name": tokens(s["name"]) | {s["name"].lower()}, "parent": tokens(s.get("parent", "")),
            "path": tokens(_path_words(rel)), "doc": tokens(s.get("doc", "")), "sig": tokens(s.get("sig", ""))}


class Searcher:
    """색인 하나에 대한 역색인. / Inverted index over one code index."""

    def __init__(self, index):
        self.docs = _docs(index)
        self.post = defaultdict(dict)
        for i, (rel, s, _) in enumerate(self.docs):
            for field, toks in _fields(rel, s).items():
                fw = FIELD_W[field]
                for t in toks:
                    if self.post[t].get(i, 0.0) < fw:
                        self.post[t][i] = fw
        self.vocab = sorted(self.post)
        self.n = max(1, len(self.docs))

    def _idf(self, t):
        return math.log(1 + self.n / len(self.post[t]))

    def _candidates(self, q):
        """(낱말, 맞음 정도). 같음 1, 앞부분 0.6(한 글자 한글 0.4), 끝이 조금 다름 0.5."""
        out = {}
        if q in self.post:
            out[q] = 1.0
        hangul = bool(HANGUL.match(q))
        if len(q) >= 2 or hangul:
            k = bisect.bisect_left(self.vocab, q)
            got = 0
            while k < len(self.vocab) and self.vocab[k].startswith(q) and got < MAX_PREFIX:
                t = self.vocab[k]
                if t != q:
                    out.setdefault(t, 0.4 if (hangul and len(q) == 1) else 0.6)
                k += 1
                got += 1
        if not hangul:
            for cut in range(max(4, len(q) - 2), len(q)):
                t = q[:cut]
                if t in self.post:
                    out.setdefault(t, 0.5)
        return out

    def search(self, query):
        """[(점수, 파일, 심볼)] 높은 순. / Hits, best first."""
        q_tokens = tokens(query) | ({query.strip().lower()} if re.fullmatch(r"[A-Za-z_]\w*", query.strip()) else set())
        q_tokens = {q for q in q_tokens if q}
        qnorm = NORM.sub("", query.lower())
        best = defaultdict(dict)  # doc → q → 점수
        for q in q_tokens:
            for t, factor in self._candidates(q).items():
                idf = self._idf(t)
                for i, fw in self.post[t].items():
                    v = fw * factor * idf
                    if best[i].get(q, 0.0) < v:
                        best[i][q] = v
        if not q_tokens and qnorm:
            for i, (_, s, _) in enumerate(self.docs):
                if qnorm in NORM.sub("", s["name"].lower()):
                    best[i]["*"] = 1.0
        max_idf = math.log(1 + self.n)
        hits = []
        for i, per in best.items():
            rel, s, _ = self.docs[i]
            coverage = len(per) / max(1, len(q_tokens))
            score = sum(per.values()) * coverage * coverage
            name = NORM.sub("", s["name"].lower())
            if qnorm and name == qnorm:
                score += 3 * max_idf
            elif len(qnorm) >= 3 and name.startswith(qnorm):
                score += 0.5 * max_idf
            score *= KIND_W.get(s["kind"], 1.0)
            if is_test_path(rel):
                score *= 0.5
            hits.append((score, rel, s))
        hits.sort(key=lambda h: (-h[0], h[1], h[2]["line"]))
        return hits


_CACHE = {}


def searcher(index):
    """같은 색인이면 만든 역색인을 다시 쓴다(MCP 서버처럼 오래 도는 곳에서). / Reuse the inverted index."""
    key = (id(index), index.get("built"), len(index.get("files", {})))
    if _CACHE.get("key") != key:
        _CACHE.clear()
        _CACHE.update(key=key, value=Searcher(index))
    return _CACHE["value"]


def read_body(root, rel, s, max_lines=MAX_BODY_LINES):
    """심볼 몸통(지금 파일에서). 루트 밖이면 None. / Current body lines, or None outside the root."""
    p = resolve(root, rel)
    if p is None or not p.is_file() or not inside_root(os.path.realpath(str(root)), p):
        return None
    try:
        lines = hio.read_text(p).split("\n")
    except OSError:
        return None
    start = s.get("start", s["line"])
    end = s.get("end", s["line"])
    if s["kind"] == "file":
        start, end = 1, min(len(lines), 40)
    seg = lines[start - 1:end]
    cut = len(seg) - max_lines if len(seg) > max_lines else 0
    return seg[:max_lines], cut


def _qual(s):
    return f"{s['parent']}.{s['name']}" if s.get("parent") and s["kind"] != "section" else s["name"]


def hit_json(root, rel, s, rec, score, level):
    out = {"path": rel, "line": s["line"], "end": s.get("end", s["line"]), "kind": s["kind"], "name": s["name"],
           "sig": s.get("sig", ""), "score": round(score, 3)}
    if s.get("parent"):
        out["parent"] = s["parent"]
    if s.get("doc"):
        out["doc"] = s["doc"]
    out["precision"] = "exact" if rec.get("extractor") == "ast" else "approx"
    if level >= 3:
        got = read_body(root, rel, s)
        if got is not None:
            out["body"] = "\n".join(got[0])
            if got[1]:
                out["body_cut"] = got[1]
    return out


def _render_hit(root, rel, s, rec, level, lang):
    ko = lang == "ko"
    if level <= 1:
        if s["kind"] == "file":
            line = rel
        else:
            line = f"{rel}:{s['line']}  {_short(s.get('sig') or s['name'], 90)}"
        if s.get("doc"):
            line += f"  · {_short(doc_for(s['doc'], lang), 50)}"
        return line
    approx = "" if rec.get("extractor") == "ast" or s["kind"] == "file" else (" [대략]" if ko else " [approx]")
    kind = s["kind"]
    out = [f"{rel}:{s['line']}-{s.get('end', s['line'])}  {kind} {_qual(s)}{approx}"]
    if s.get("sig") and kind != "file":
        out.append(f"    {s['sig']}")
    if s.get("doc"):
        out.append(f"    {s['doc']}")
    if level >= 3:
        got = read_body(root, rel, s)
        if got is None:
            out.append("    (몸통을 읽지 못함)" if ko else "    (could not read the body)")
        else:
            seg, cut = got
            out.append("```")
            out.extend(seg)
            if cut:
                out.append(f"… ({cut}줄 더)" if ko else f"… ({cut} more lines)")
            out.append("```")
    return "\n".join(out)


def not_found(index, query, lang, via="cli"):
    tot = totals(index)
    ko = lang == "ko"
    unread = (f", 읽지 못한 파일 {tot['unread']}개" if ko else f", {tot['unread']} files unread") if tot["unread"] else ""
    if via == "mcp":
        nxt = ("다음에 할 일: (1) 다른 낱말로 다시 찾기(영어 이름의 앞부분, 한국어는 두 글자 이상), "
               "(2) map_show에 focus를 주어 주변 보기, (3) 그래도 없으면 새로 만들기 전에 글 전체 검색(grep)으로 한 번 더 확인."
               if ko else "Next: (1) try other words (the start of an English name, or two or more Korean characters), "
                          "(2) call map_show with a focus to look around, (3) if still nothing, run a full-text search "
                          "(grep) once before building something new.")
    else:
        nxt = ("다음에 할 일: (1) 다른 낱말로 다시 찾기(영어 이름의 앞부분, 한국어는 두 글자 이상), "
               "(2) `habitree map show --focus <낱말>`로 주변 보기, (3) 그래도 없으면 새로 만들기 전에 `git grep -n <낱말>`로 확인."
               if ko else "Next: (1) try other words (the start of an English name, or two or more Korean characters), "
                          "(2) look around with `habitree map show --focus <word>`, (3) if still nothing, check with "
                          "`git grep -n <word>` before building something new.")
    head = (f"못 찾음: '{query}'. 색인한 파일 {tot['files']}개·심볼 {tot['symbols']}개를 다 봤습니다{unread}."
            if ko else f"Not found: '{query}'. Searched all {tot['files']} indexed files and {tot['symbols']} "
                       f"symbols{unread}.")
    return head + "\n" + nxt


def find(root, index, query, level=1, limit=10, budget=4000, lang="ko", via="cli"):
    """(JSON용 결과, 글). 예산을 넘기 전까지 담는다. / (data, text) within the budget."""
    hits = searcher(index).search(query)
    tot = totals(index)
    ko = lang == "ko"
    data = {"query": query, "level": level, "total": len(hits),
            "index": {"files": tot["files"], "symbols": tot["symbols"], "unread": tot["unread"],
                      "built": index.get("built", "")}, "hits": []}
    if not hits:
        data["status"] = "absent"
        return data, not_found(index, query, lang, via)
    data["status"] = "ok"
    head = (f"# 찾기 '{query}' · {len(hits)}개 중 위에서부터 (단계 {level}, 색인 {show_time(index.get('built', ''))})"
            if ko else f"# Find '{query}' · top of {len(hits)} (level {level}, indexed {show_time(index.get('built', ''))})")
    out, used, shown = [head], len(head), 0
    files = index.get("files", {})
    for score, rel, s in hits[:max(1, limit)]:
        rec = files.get(rel, {})
        block = _render_hit(root, rel, s, rec, level, lang)
        if budget and shown and used + len(block) + 1 > budget:
            break
        if budget and used + len(block) + 1 > budget:
            block = block[:max(0, budget - used - 2)] + "…"
        out.append(block)
        used += len(block) + 1
        shown += 1
        data["hits"].append(hit_json(root, rel, s, rec, score, level))
    rest = len(hits) - shown
    if rest > 0:
        out.append(f"(결과 {rest}개 더 있음. 낱말을 더해 좁히거나 개수·예산을 늘리세요)" if ko
                   else f"({rest} more results. Add words to narrow, or raise the limit or budget.)")
    return data, "\n".join(out)
