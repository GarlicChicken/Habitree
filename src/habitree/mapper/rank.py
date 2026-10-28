"""순위와 예산: 많이 쓰이는 정의부터 글자 예산 안에 담는다. / Rank definitions and fit them in a budget.

생각은 Aider의 repo map에서 빌렸고 코드는 표준 라이브러리로 새로 썼다(NOTICE.md).
1. 파일을 점으로, '이름을 쓰는 파일 → 그 이름을 정의한 파일'을 선으로 그래프를 만든다.
2. PageRank로 파일 순위를 낸다. --focus가 있으면 그 경로·낱말 쪽에서 출발하게 무게를 준다.
3. 파일 순위를 선을 따라 정의 하나하나에 나눠 정의 순위를 만든다.
4. 상위 N개로 지도를 그려 글자 수를 재고, 예산에 맞는 가장 큰 N을 이진 탐색으로 찾는다.
"""
import math
import re
from collections import defaultdict

from ..core.paths import glob_match, nfc
from ..core.textsim import tokens
from ..core.timeutil import show as show_time
from .extract import doc_for, spec
from .index import is_test_path, totals

DAMPING = 0.85


def _short(text, limit):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _path_words(rel):
    return re.sub(r"[/._\-]+", " ", rel)


def name_tokens(name):
    return tokens(name) | {name.lower()}


def word_hit(name, words):
    if not words:
        return False
    toks = name_tokens(name)
    return any(t == w or (len(w) >= 3 and t.startswith(w)) for t in toks for w in words)


def parse_focus(index, focus):
    """초점을 경로와 낱말로 나눈다. / Split focus items into paths and words."""
    paths, words = [], set()
    files = index.get("files", {})
    for raw in focus or []:
        item = nfc(str(raw).replace("\\", "/")).strip()
        if item.startswith("./"):
            item = item[2:]
        item = item.rstrip("/")
        if not item:
            continue
        low = item.casefold()
        is_path = "/" in item or any(c in item for c in "*?") or any(
            ("/" + r.casefold()).find("/" + low) >= 0 and (r.casefold() == low or r.casefold().endswith("/" + low)
                                                         or ("/" + low + "/") in ("/" + r.casefold()))
            for r in files)
        if is_path:
            paths.append(item)
        else:
            words |= tokens(item) | {item.lower()}
    return paths, words


def path_hit(rel, paths):
    """경로 초점: 같은 파일, 그 폴더 아래, 어디든 같은 이름의 폴더·파일, 글롭. / Path focus match."""
    low = "/" + rel.casefold()
    for p in paths:
        q = p.casefold().strip("/")
        if (low == "/" + q or low.startswith("/" + q + "/") or ("/" + q + "/") in low or low.endswith("/" + q)
                or glob_match(rel, p)):
            return True
    return False


COMMON_DAMP = 0.05  # get·add·run처럼 흔한 이름은 다른 것(dict.get 등)을 부른 것일 때가 많다


def _name_weight(name, ndefs, words):
    w = 1.0
    if word_hit(name, words):
        w *= 10
    if len(name) >= 8 and ("_" in name.strip("_") or re.search(r"[a-z][A-Z]", name)):
        w *= 2
    if name.startswith("_"):
        w *= 0.2
    if ndefs > 5:
        w *= 0.1
    return w


def pagerank(nodes, edges, personal, out_total=None, damping=DAMPING, iters=60, tol=1e-7):
    """거듭제곱법 PageRank(개인화 포함). / Personalized PageRank by power iteration.

    out_total[s]가 선 무게의 합보다 크면 남는 몫은 출발점(personal)으로 돌아간다. 흔한 이름의 선을 약하게
    해도 정규화 때문에 다시 커지지 않게 하려는 것이다."""
    if not nodes:
        return {}
    idx = {n: i for i, n in enumerate(nodes)}
    total = sum(personal.get(n, 0.0) for n in nodes) or float(len(nodes))
    p = [personal.get(n, 0.0) / total if personal else 1.0 / len(nodes) for n in nodes]
    out_w = [0.0] * len(nodes)
    flat = []
    for (s, t), w in edges.items():
        if w > 0:
            out_w[idx[s]] += w
            flat.append((idx[s], idx[t], w))
    denom = [max(out_w[i], (out_total or {}).get(n, 0.0)) for i, n in enumerate(nodes)]
    keep = [out_w[i] / denom[i] if denom[i] else 0.0 for i in range(len(nodes))]
    r = list(p)
    for _ in range(iters):
        new = [(1 - damping) * x for x in p]
        leak = sum(r[i] * (1.0 - keep[i]) for i in range(len(nodes)))
        for s, t, w in flat:
            new[t] += damping * r[s] * w / denom[s]
        for i in range(len(nodes)):
            new[i] += damping * leak * p[i]
        diff = sum(abs(a - b) for a, b in zip(new, r))
        r = new
        if diff < tol:
            break
    return {n: r[idx[n]] for n in nodes}


def rank(index, focus=None):
    """(정의 목록[(점수, 파일, 심볼)], 파일 순위, 초점이 맞은 파일 수). / Ranked definitions."""
    files = index.get("files", {})
    paths, words = parse_focus(index, focus)
    defs = defaultdict(set)
    for rel, rec in files.items():
        for s in rec.get("symbols", ()):
            if s["kind"] != "section" and len(s["name"]) >= 3:
                defs[s["name"]].add(rel)
    nodes = sorted(rel for rel, rec in files.items()
                   if any(s["kind"] != "section" for s in rec.get("symbols", ())) or rec.get("refs"))
    edges, by_edge, out_total = defaultdict(float), defaultdict(dict), defaultdict(float)
    common = spec()["common_names"]
    for src in nodes:
        for name, cnt in files[src].get("refs", {}).items():
            dsts = defs.get(name)
            if not dsts or src in dsts:  # 제 파일에 같은 이름이 있으면 그것을 쓴 것으로 본다
                continue
            if not is_test_path(src):  # 제품 코드는 시험 코드를 부르지 않는다
                dsts = {d for d in dsts if not is_test_path(d)}
                if not dsts:
                    continue
            raw = _name_weight(name, len(dsts), words) * math.sqrt(cnt)
            w = raw * (COMMON_DAMP if name in common and not word_hit(name, words) else 1.0)
            for dst in dsts:
                if dst != src:
                    out_total[src] += raw
                    edges[(src, dst)] += w
                    by_edge[(src, dst)][name] = by_edge[(src, dst)].get(name, 0.0) + w
    hits = 0
    personal = {}
    for rel in nodes:
        v = 1.0
        if paths and path_hit(rel, paths):
            v += 100.0
        if words and (word_hit(_path_words(rel), words) or any(
                word_hit(s["name"], words) or word_hit(s.get("doc", ""), words)
                for s in files[rel].get("symbols", ()))):
            v += 20.0
        if v > 1.0:
            hits += 1
        personal[rel] = v
    pr = pagerank(nodes, edges, personal, out_total)
    def_rank = defaultdict(float)
    for (src, dst), names in by_edge.items():
        share = pr[src] / out_total[src] if out_total[src] else 0.0
        for name, w in names.items():
            def_rank[(dst, name)] += share * w
    entries = []
    for rel in nodes:
        syms = [s for s in files[rel].get("symbols", ()) if s["kind"] != "section"]
        for s in syms:
            score = def_rank.get((rel, s["name"]), 0.0) + 0.1 * pr[rel] / len(syms)
            if s["name"].startswith("_"):
                score *= 0.5
            if is_test_path(rel):
                score *= 0.3
            if word_hit(s["name"], words):
                score *= 10
            elif word_hit(s.get("doc", ""), words):
                score *= 5
            if (paths and path_hit(rel, paths)) or (words and word_hit(_path_words(rel), words)):
                score *= 3
            entries.append((score, rel, s))
    entries.sort(key=lambda e: (-e[0], e[1], e[2]["line"]))
    return entries, pr, hits


def _render(index, entries, n, budget, lang, focus, focus_missed):
    files = index.get("files", {})
    ko = lang == "ko"
    chosen = entries[:n]
    order, groups = [], defaultdict(list)
    for _, rel, s in chosen:
        if rel not in groups:
            order.append(rel)
        groups[rel].append(s)
    tot = totals(index)
    built = show_time(index.get("built", ""))
    head = (f"# 코드 지도 · 파일 {len(order)}/{tot['files']}개, 심볼 {n}/{len(entries)}개, 예산 {budget}자, 색인 {built}"
            if ko else f"# Code map · files {len(order)}/{tot['files']}, symbols {n}/{len(entries)}, "
                       f"budget {budget} chars, indexed {built}")
    out = [head]
    if focus:
        out.append((f"초점: {', '.join(focus)}" + (" (맞는 파일이 없어 전체 순위로 보여 줌)" if focus_missed else ""))
                   if ko else (f"Focus: {', '.join(focus)}" + (" (nothing matched; showing the overall ranking)"
                                                                if focus_missed else "")))
    for rel in order:
        rec = files[rel]
        size = f"{rec.get('lines', 0)}{'줄' if ko else ' lines'}"
        approx = "" if rec.get("extractor") != "regex" else (", 대략" if ko else ", approx")
        out.append(f"{rel} ({rec.get('lang', '?')}, {size}{approx})")
        names = {s["name"] for s in groups[rel]}
        for s in sorted(groups[rel], key=lambda x: x["line"]):
            parent = s.get("parent")
            if parent and parent in names:
                text = f"    {s['line']}: {_short(s['sig'], 100)}"
            elif parent:
                text = f"  {s['line']}: {parent} › {_short(s['sig'], 100)}"
            else:
                text = f"  {s['line']}: {_short(s['sig'], 100)}"
            if s.get("doc"):
                text += f"  · {_short(doc_for(s['doc'], lang), 60)}"
            out.append(text)
    if n < len(entries):
        out.append(f"(예산 때문에 심볼 {len(entries) - n}개를 뺐습니다. 더 보려면 예산을 늘리거나 초점(focus)으로 좁히세요)"
                   if ko else f"({len(entries) - n} symbols left out to fit the budget. "
                              f"Raise the budget or narrow it with a focus.)")
    return "\n".join(out)


def show(index, focus=None, budget=4000, lang="ko"):
    """예산 안에 드는 코드 지도(글). / The code map that fits the character budget."""
    entries, _, hits = rank(index, focus)
    focus = [str(f) for f in (focus or []) if str(f).strip()]
    missed = bool(focus) and hits == 0
    if not entries:
        tot = totals(index)
        return (f"# 코드 지도 · 심볼을 찾은 파일이 없습니다(파일 {tot['files']}개). 이 언어에 패턴이 없으면 "
                f"data/symbols.json에 묶음을 더할 수 있습니다." if lang == "ko"
                else f"# Code map · no symbols found ({tot['files']} files). If the language has no patterns, "
                     f"add a group to data/symbols.json.")
    if budget <= 0:  # 0이면 제한 없음
        return _render(index, entries, len(entries), budget, lang, focus, missed)
    lo, hi = 0, len(entries)
    best = _render(index, entries, 0, budget, lang, focus, missed)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        text = _render(index, entries, mid, budget, lang, focus, missed)
        if len(text) <= budget:
            lo, best = mid, text
        else:
            hi = mid - 1
    return best if len(best) <= budget else best[:max(0, budget - 1)] + "…"
