"""map: 코드 색인. 새로 만들기 전에 이미 있는 것을 적은 토큰으로 찾는다. / Code index: find what already exists.

  habitree map build [--full]                     색인 만들기(바뀐 파일만 다시 읽음)
  habitree map show [--budget N] [--focus …]      많이 쓰이는 정의부터 예산 안의 지도
  habitree map find <말> [--level 1|2|3] [--json] 이름·설명으로 찾기(한국어 조사도 됨)
  habitree map dupes                              같은 몸통, 6줄 넘게 같은 글
  habitree map churn                              자주 바뀌는 곳(git 기록)
  habitree map stats                              언어별 파일·줄·심볼 수
색인은 .habitree/state/map.json에 있고 커밋하지 않는다. show·find·dupes·churn·stats는 부를 때마다
바뀐 파일만 다시 읽어 색인을 최신으로 맞춘다.
"""
import json

from ..core.i18n import tr
from ..mapper import churn, dupes, index, rank, render_stats, search, stats

SUMMARY = {"ko": "코드 색인: 이미 있는 함수·모듈을 찾기(build·show·find·dupes·churn·stats)",
           "en": "Code index: find existing functions and modules (build, show, find, dupes, churn, stats)"}

MSG = {
    "built": {"ko": "색인을 만들었습니다: 파일 {files}개 (새로 읽음 {read}, 그대로 {same}, 내용 같음 {touched}, 지움 {removed}) "
                    "· 심볼 {symbols}개 · {seconds}초",
              "en": "Index built: {files} files (read {read}, unchanged {same}, same content {touched}, removed {removed}) "
                    "· {symbols} symbols · {seconds}s"},
    "excluded": {"ko": "  뺀 파일: {parts}", "en": "  excluded: {parts}"},
    "where": {"ko": "  위치: {path} (커밋하지 않음)", "en": "  at: {path} (not committed)"},
    "next": {"ko": "다음: habitree map show --budget 2000 · habitree map find <말>",
             "en": "Next: habitree map show --budget 2000 · habitree map find <words>"},
    "usage": {"ko": "할 일을 고르세요: build, show, find, dupes, churn, stats (habitree map -h)",
              "en": "Pick an action: build, show, find, dupes, churn, stats (habitree map -h)"},
}
EXCLUDED = {"secret": {"ko": "비밀일 수 있음", "en": "possible secrets"},
            "outside": {"ko": "루트 밖 링크", "en": "links outside the root"},
            "unreadable": {"ko": "못 읽음", "en": "unreadable"}}


def add_arguments(p):
    sub = p.add_subparsers(dest="action", metavar="<action>")
    b = sub.add_parser("build", help="색인 만들기 / build the index")
    b.add_argument("--full", action="store_true", help="처음부터 다시 / rebuild from scratch")
    s = sub.add_parser("show", help="예산 안의 코드 지도 / ranked map within a budget")
    s.add_argument("--budget", type=int, help="글자 예산(0이면 제한 없음) / character budget, 0 = no limit")
    s.add_argument("--focus", nargs="+", help="경로나 낱말 쪽에 무게 / weight toward paths or words")
    f = sub.add_parser("find", help="이름·설명으로 찾기 / find by name or description")
    f.add_argument("words", nargs="+")
    f.add_argument("--level", type=int, choices=(1, 2, 3), default=1,
                   help="1 한 줄, 2 시그니처·설명, 3 몸통까지 / 1 one line, 2 signature and doc, 3 with body")
    f.add_argument("--limit", type=int, help="결과 수 / number of results")
    f.add_argument("--budget", type=int, help="글자 예산(0이면 제한 없음) / character budget, 0 = no limit")
    f.add_argument("--json", action="store_true")
    d = sub.add_parser("dupes", help="같은 몸통·같은 글 / duplicate bodies and text")
    d.add_argument("--window", type=int, help="글 중복 창(줄) / window in lines")
    d.add_argument("--json", action="store_true")
    c = sub.add_parser("churn", help="자주 바뀌는 곳(git) / hotspots from git history")
    c.add_argument("--top", type=int)
    c.add_argument("--json", action="store_true")
    t = sub.add_parser("stats", help="언어별 통계 / per-language stats")
    t.add_argument("--json", action="store_true")


def _excluded_text(ex, lang):
    return ", ".join(f"{tr(EXCLUDED.get(k, {'ko': k, 'en': k}), lang)} {v}" for k, v in sorted(ex.items()))


def run(args, ctx):
    lang = ctx.lang
    act = args.action
    if act is None:
        print(tr(MSG["usage"], lang))
        return 0
    if act == "build":
        idx, st = index.build(ctx, full=args.full)
        print(tr(MSG["built"], lang).format(symbols=index.totals(idx)["symbols"], **st))
        if st["excluded"]:
            print(tr(MSG["excluded"], lang).format(parts=_excluded_text(st["excluded"], lang)))
        print(tr(MSG["where"], lang).format(path=index.INDEX_REL))
        print(tr(MSG["next"], lang))
        return 0
    idx = index.ensure(ctx)
    if act == "show":
        budget = ctx.get("map.show_budget", 4000) if args.budget is None else args.budget
        print(rank.show(idx, args.focus, budget, lang))
    elif act == "find":
        query = " ".join(args.words)
        limit = args.limit or (3 if args.level == 3 else ctx.get("map.find_limit", 10))
        budget = ctx.get("map.find_budget", 4000) if args.budget is None else args.budget
        data, text = search.find(ctx.root, idx, query, args.level, limit, budget, lang)
        print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else text)
    elif act == "dupes":
        window = args.window or ctx.get("map.dupe_window", 6)
        result = dupes.find_dupes(ctx.root, idx, window)
        if args.json:
            print(json.dumps({"same_body": [[{"path": r, "line": s["line"], "name": s["name"]} for r, s in g]
                                            for g in result["same_body"]],
                              "clones": [{"a": a, "a_lines": [a1, a2], "b": b, "b_lines": [b1, b2], "lines": n}
                                         for a, a1, a2, b, b1, b2, n in result["clones"]]},
                             ensure_ascii=False, indent=1))
        else:
            print(dupes.render(result, lang, window))
    elif act == "churn":
        top = args.top or ctx.get("map.churn_top", 15)
        rows = churn.hotspots(ctx.root, idx, ctx.get("map.churn_commits", 2000), top)
        if args.json:
            print(json.dumps(None if rows is None else [
                {"path": r, "score": sc, "changes": n, "lines": ln, "churn": ch} for sc, r, n, ln, ch in rows],
                ensure_ascii=False, indent=1))
        else:
            print(churn.render(rows, lang))
    elif act == "stats":
        data = stats(idx)
        print(json.dumps(data, ensure_ascii=False, indent=1) if args.json
              else render_stats(data, lang, index.INDEX_REL))
    return 0
