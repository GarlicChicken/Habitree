"""중복: 새로 만들기 전에 이미 비슷한 코드가 있는지. / Duplicates: is there similar code already?

두 가지를 본다.
1. 같은 몸통: 함수·메서드 몸통(공백·주석을 지운 줄)의 해시가 같음. 이름이 달라도 잡는다.
2. 글 중복: 공백·주석·빈 줄·뜻 없는 줄(괄호만, import 등)을 지운 줄을 창(기본 6줄)으로 묶어 같은 묶음을 찾는다.
   문법을 모르므로 어떤 언어에도 같게 돈다. 생각은 jscpd에서 빌렸다(NOTICE.md).
"""
import hashlib
import os
import re
from collections import defaultdict

from ..core import io as hio
from ..core.paths import resolve
from . import extract, langs
from .index import inside_root

TRIVIAL = re.compile(r"^(?:import|from|#\s*include|using|require|use|package)\b|^export\s*\{|^[^0-9A-Za-z가-힣]*$")
TRIVIAL_WORDS = {"end", "else", "else:", "pass", "break", "continue", "return", "return;", "fi", "done", "esac",
                 "try:", "finally:", "do", "then", "begin", "}", "};", "});", "})", "]", "];", ")", ");"}
MAX_CLONES = 50


def same_bodies(index):
    """[[(파일, 심볼), …]] 몸통 해시가 같은 무리. / Groups of symbols with the same body hash."""
    groups = defaultdict(list)
    for rel, rec in sorted(index.get("files", {}).items()):
        for s in rec.get("symbols", ()):
            if s.get("body"):
                groups[s["body"]].append((rel, s))
    out = [g for g in groups.values() if len(g) > 1]
    out.sort(key=lambda g: (-(g[0][1].get("end", 0) - g[0][1]["line"]), g[0][0]))
    return out


def _norm_lines(text, lang):
    marks = tuple(langs.comments(lang))
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        s = extract.norm_line(line, marks)
        if not s or s in TRIVIAL_WORDS or TRIVIAL.search(s):
            continue
        out.append((i, s))
    return out


def text_clones(root, index, window=6):
    """[(파일 A, 시작, 끝, 파일 B, 시작, 끝, 줄 수)] 창 크기 이상 같은 글. / Repeated text blocks."""
    root_real = os.path.realpath(str(root))
    seen, clones, cache = {}, [], {}
    for rel, rec in sorted(index.get("files", {}).items()):
        lang = rec.get("lang")
        if not extract.is_code(lang) or rec.get("skip") or not rec.get("lines"):
            continue
        p = resolve(root, rel)
        if p is None or not inside_root(root_real, p):
            continue
        try:
            lines = _norm_lines(hio.read_text(p), lang)
        except OSError:
            continue
        cache[rel] = lines
        texts = [s for _, s in lines]
        i = 0
        while i + window <= len(texts):
            h = hashlib.sha1("\n".join(texts[i:i + window]).encode("utf-8")).digest()
            prev = seen.get(h)
            if prev and not (prev[0] == rel and prev[1] + window > i):
                g, j = prev
                other = cache[g]
                n = window
                while (i + n < len(texts) and j + n < len(other) and texts[i + n] == other[j + n][1]
                       and not (g == rel and j + n >= i)):
                    n += 1
                clones.append((g, other[j][0], other[j + n - 1][0], rel, lines[i][0], lines[i + n - 1][0], n))
                i += n
                continue
            seen.setdefault(h, (rel, i))
            i += 1
    clones.sort(key=lambda c: (-c[6], c[0], c[1]))
    return clones


def find_dupes(root, index, window=6):
    return {"same_body": same_bodies(index), "clones": text_clones(root, index, window)}


def render(result, lang, window=6, limit=MAX_CLONES):
    ko = lang == "ko"
    sb, cl = result["same_body"], result["clones"]
    if not sb and not cl:
        return ("중복 없음: 같은 몸통의 함수도, {w}줄 넘게 같은 글도 찾지 못했습니다.".format(w=window) if ko
                else f"No duplicates: no functions with the same body and no text repeated over {window} lines.")
    out = []
    if sb:
        out.append(f"# 같은 몸통 {len(sb)}무리 (이름이 달라도 몸통이 같음)" if ko
                   else f"# Same body: {len(sb)} groups (bodies match even if names differ)")
        for g in sb[:limit]:
            out.append("  " + "  =  ".join(f"{rel}:{s['line']} {s['name']}" for rel, s in g))
    if cl:
        out.append(f"# 같은 글 {len(cl)}곳 ({window}줄 이상, 공백·주석 무시)" if ko
                   else f"# Repeated text: {len(cl)} places ({window}+ lines, ignoring spaces and comments)")
        for a, a1, a2, b, b1, b2, n in cl[:limit]:
            out.append(f"  {a}:{a1}-{a2}  =  {b}:{b1}-{b2}  ({n}{'줄' if ko else ' lines'})")
    shown = max(len(sb), len(cl))
    if shown > limit:
        out.append(f"(위 {limit}개만 보여 줌. --json으로 전부)" if ko else f"(showing the top {limit}; use --json for all)")
    out.append("하나로 합칠 수 있으면 공용 모듈로 옮기고, 일부러 둔 것이면 그대로 둡니다." if ko
               else "Merge into a shared module where you can; leave intentional copies as they are.")
    return "\n".join(out)
