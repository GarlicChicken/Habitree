"""코드 색인(map): 새로 만들기 전에 이미 있는 모듈·함수·도구를 적은 토큰으로 찾게 한다.
/ Code index: find existing modules, functions and tools with few tokens before building new ones.

  langs    언어표(확장자·파일 이름·shebang → 언어, 주석 표시)
  extract  심볼 추출(Python ast, 그 밖의 언어는 data/symbols.json 패턴)
  index    색인 만들기·읽기(.habitree/state/map.json, 바뀐 파일만 다시 읽음)
  rank     참조 그래프 + PageRank + 글자 예산 이진 탐색
  search   이름·설명 찾기(낱말 나눔, 앞부분 일치, 한국어 두 글자 묶음), 세 단계 결과
  dupes    같은 몸통, 창 단위 글 중복
  churn    git 기록: 핫스팟, 커밋별 파일, 파일별 마지막 커밋 시각
  refactor 위 결과를 읽어 몰림·중복·흩어짐·덜어낼 곳과 정리 규모를 판단(habitree refactor)
"""
from collections import defaultdict

from ..core.timeutil import show as show_time
from .index import totals


def stats(index):
    """언어별 파일·줄·심볼 수. / Files, lines and symbols per language."""
    per = defaultdict(lambda: {"files": 0, "lines": 0, "code": 0, "symbols": 0, "approx": 0})
    skipped = defaultdict(int)
    for rec in index.get("files", {}).values():
        row = per[rec.get("lang") or "?"]
        row["files"] += 1
        row["lines"] += rec.get("lines", 0)
        row["code"] += rec.get("code", 0)
        n = len(rec.get("symbols", ()))
        row["symbols"] += n
        if rec.get("extractor") == "regex":
            row["approx"] += n
        if rec.get("skip"):
            skipped[rec["skip"]] += 1
    langs = sorted(per.items(), key=lambda kv: (-kv[1]["code"], -kv[1]["files"], kv[0]))
    return {"totals": totals(index), "built": index.get("built", ""), "languages": dict(langs),
            "skipped": dict(skipped), "excluded": index.get("excluded", {})}


def render_stats(data, lang, path=""):
    ko = lang == "ko"
    t = data["totals"]
    out = [(f"# 코드 색인 · 파일 {t['files']}개, 심볼 {t['symbols']}개, 색인 {show_time(data['built'])}"
            if ko else f"# Code index · {t['files']} files, {t['symbols']} symbols, indexed {show_time(data['built'])}")]
    if path:
        out.append(("  위치: " if ko else "  at: ") + path)
    out.append(f"  {'언어' if ko else 'language':<16} {'파일' if ko else 'files':>6} {'줄' if ko else 'lines':>8} "
               f"{'코드 줄' if ko else 'code':>8} {'심볼' if ko else 'symbols':>8}")
    for name, row in data["languages"].items():
        mark = "*" if row["approx"] else ""
        out.append(f"  {name[:16]:<16} {row['files']:>6} {row['lines']:>8} {row['code']:>8} {row['symbols']:>7}{mark or ' '}")
    out.append("  * 패턴으로 뽑은 대략 결과가 섞임" if ko else "  * includes approximate (pattern) results")
    sk = data["skipped"]
    if sk:
        names = {"binary": ("바이너리", "binary"), "large": ("큰 파일", "large"), "minified": ("압축 코드", "minified")}
        parts = [f"{names.get(k, (k, k))[0 if ko else 1]} {v}" for k, v in sorted(sk.items())]
        out.append(("  안 읽은 파일: " if ko else "  not parsed: ") + ", ".join(parts))
    ex = data["excluded"]
    if ex:
        names = {"secret": ("비밀일 수 있어 뺌", "possible secrets"), "outside": ("루트 밖 링크", "links outside the root"),
                 "unreadable": ("못 읽음", "unreadable")}
        parts = [f"{names.get(k, (k, k))[0 if ko else 1]} {v}" for k, v in sorted(ex.items())]
        out.append(("  뺀 파일: " if ko else "  excluded: ") + ", ".join(parts))
    return "\n".join(out)
