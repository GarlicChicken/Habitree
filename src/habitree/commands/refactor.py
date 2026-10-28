"""refactor: 몰린 코드·중복·흩어진 코드·덜어낼 코드를 찾아 정리 계획을 제안한다. 코드는 고치지 않는다.
/ Suggest a cleanup plan for piled-up, duplicated, scattered or removable code. Changes nothing.

  habitree refactor [경로…] [--focus 낱말…] [--mode auto|mini|bold] [--top N] [--json]
후보마다 문제(숫자), 왜 비효율인지, 권하는 규모(작은 단계·큰 정리)와 이유, 순서대로 할 단계를 낸다.
기준값은 base 꾸러미의 code/structure 규칙(concentration·duplication·fragmentation)의 detect에 있다.
"""
import json

from ..core.i18n import tr
from ..guard.texts import fmt
from ..mapper import index
from ..mapper import refactor as rf

SUMMARY = {"ko": "정리 제안: 몰림·중복·흩어짐·덜어낼 곳과 작은 단계·큰 정리 계획(코드는 고치지 않음)",
           "en": "Refactoring advice: piled-up, duplicated, scattered or removable code, with a small or bold plan"}
CHECK = "habitree verify"
T = {
    "concentration": ("몰림", "Concentration"), "duplication": ("중복", "Duplication"),
    "fragmentation": ("흩어짐", "Fragmentation"), "simplify": ("덜어내기", "Simplify"),
    "mini": ("작은 단계", "small step"), "bold": ("큰 정리", "bold cleanup"), "info": ("알림", "note"),
    "p.file": ("{file}: {lines}줄(중앙값 {median}줄의 {x}배), 심볼 {symbols}개",
               "{file}: {lines} lines ({x}x the median of {median}), {symbols} symbols"),
    "p.function": ("{file}: 긴 함수 {funcs}(함수 길이 중앙값 {fmed}줄)", "{file}: long functions {funcs} (median {fmed} lines)"),
    "p.funcs": (", 긴 함수 {funcs}", ", long functions {funcs}"), "p.changes": (", 변경 {changes}번", ", {changes} changes"),
    "p.fn": ("{0} {1}줄", "{0} ({1} lines)"),
    "p.same_body": ("같은 몸통 {k}곳, 각 {lines}줄: {where}", "Same body in {k} places, {lines} lines each: {where}"),
    "p.clone": ("같은 글 {lines}줄({k}곳): {where}", "Repeated text, {lines} lines ({k} places): {where}"),
    "p.same_name": ("같은 이름 {name}이(가) {k}곳에 따로 정의됨: {where}", "{name} is defined separately in {k} places: {where}"),
    "p.coupling": ("늘 함께 바뀌는 다른 폴더의 파일 {k}개: {where}", "{k} files in different folders that change together: {where}"),
    "p.pair": ("{a} + {b}(함께 {n}번, {d}%)", "{a} + {b} ({n} together, {d}%)"),
    "p.mutual": ("다른 폴더의 파일이 서로 참조함: {where}", "Files in different folders use each other: {where}"),
    "p.unused": ("{file}: 어디서도 부르지 않는 것으로 보이는 정의 {k}개: {where}",
                 "{file}: {k} definitions nothing seems to call: {where}"),
    "p.unused_file": ("어디서도 쓰거나 언급하지 않는 파일: {file}({lines}줄)",
                      "A file nothing uses or mentions: {file} ({lines} lines)"),
    "p.wrapper": ("{file}: 한 곳에서만 쓰는 짧은 정의 {k}개: {where}", "{file}: {k} short definitions used in one place: {where}"),
    "p.tiny": ("서로만 쓰는 작은 파일 {k}개: {where}", "{k} small files that only use each other: {where}"),
    "p.lonely": ("작은 파일 {file}({lines}줄)을 {user} 한 곳만 씀", "Small file {file} ({lines} lines) is used only by {user}"),
    "r.no_verify": ("검증 명령 없음(설정 verify)", "no verify command (config verify)"),
    "r.no_tests": ("이 코드를 쓰는 시험 없음", "no test uses this code"),
    "r.many_users": ("쓰는 파일 {n}곳(기준 {max}곳 넘음)", "{n} files use it (over {max})"),
    "r.public": ("입구 파일이라 바깥에서 부를 수 있음", "an entry file others may call"),
    "r.busy": ("최근 자주 바뀜(변경 {n}번)", "changes often ({n} changes)"),
    "r.wide": ("{n}곳에 퍼졌고 안전망이 있으며 쓰는 곳이 적음", "spread over {n} places, safety net present, few users"),
    "r.local": ("{n}곳에 모여 있어 한 걸음이면 됨", "in {n} place(s), one step is enough"),
    "r.forced": ("--mode로 고름", "chosen with --mode"),
    "s.no_verify": ("안전망 먼저: 테스트·빌드 명령을 설정 verify에 등록하고 지금 상태에서 합격하는지 보기",
                    "Safety net first: register test or build commands under verify and see them pass as things are"),
    "s.no_tests": ("안전망 먼저: {files}의 지금 동작을 그대로 확인하는 시험 하나 더하기",
                   "Safety net first: add one test that pins the current behavior of {files}"),
    "s.both": ("안전망 먼저: {files}의 지금 동작을 그대로 확인하는 시험을 하나 쓰고, 그 실행 명령을 설정 verify에 등록",
               "Safety net first: write one test that pins the current behavior of {files} and register its command under verify"),
    "s.ok": ("시작 전에 지금 상태가 합격인지 확인", "Before starting, confirm the current state passes"),
    "trim.unused": ("먼저 덜어 내기: 안 쓰이는 것으로 보이는 {where}를 `git grep -n`으로 확인한 뒤 지우기",
                    "Remove first: confirm with `git grep -n` that {where} is unused, then delete it"),
    "trim.wrapper": ("먼저 덜어 내기: 한 곳에서만 쓰는 짧은 {where}를 그 쓰는 곳에 풀어 넣기",
                     "Remove first: inline the short {where}, used in one place, into its caller"),
    "m.file": ("있는 경계를 따라 한 묶음만 옮기기({seams}): 같은 폴더의 새 파일로, 옛 자리는 그것을 불러 쓰게",
               "Move one group along an existing seam ({seams}) to a new file in the same folder; the old spot calls it"),
    "m.file0": ("서로 붙어 다니는 함수 한 묶음만 같은 폴더의 새 파일로 옮기기(옛 자리는 불러 쓰게)",
                "Move one group of functions that go together to a new file in the same folder (the old spot calls it)"),
    "m.function": ("{name}에서 이름 붙일 수 있는 한 덩어리를 같은 파일 안의 함수로 빼기(새 파일·새 층 없이)",
                   "Extract one nameable chunk of {name} into a function in the same file (no new file or layer)"),
    "m.same_body": ("{keep}을(를) 남기고 {other}은(는) 그것을 부르게 바꾼 뒤 몸통 지우기(새 함수 없이)",
                    "Keep {keep}; make {other} call it and delete its body (no new function)"),
    "m.clone": ("같은 줄 묶음을 {keep} 안의 함수로 빼고 {other}가 그것을 부르게 바꾸기(새 파일 없이)",
                "Extract the repeated lines into a function inside {keep} and make {other} call it (no new file)"),
    "m.same_name": ("{name} 중 하나를 원본으로 정하고 한 곳만 그것을 부르게 바꾸기(뜻이 다르면 이름을 구분)",
                    "Pick one {name} as the original and make one other place call it (rename if they differ in meaning)"),
    "m.coupling": ("함께 바뀌는 까닭(같은 상수·형식·규칙)을 찾아 둘 중 한 파일로 옮기기",
                   "Find why they change together (a shared constant, format or rule) and move it into one of them"),
    "m.mutual": ("한쪽 방향의 참조 하나를 끊기: 서로 쓰는 부분을 한쪽 파일로 옮기기",
                 "Break one direction: move the part both use into one of the files"),
    "m.unused": ("`git grep -n <이름>`으로 문자열 호출·문서 언급까지 확인한 뒤 {where} 지우기",
                 "Check with `git grep -n <name>` for calls by string and mentions, then delete {where}"),
    "m.unused_file": ("`git grep -n {stem}`으로 진입점·설정·문서에서 부르는지 확인한 뒤 {file} 지우기",
                      "Check with `git grep -n {stem}` that no entry point, config or doc runs it, then delete {file}"),
    "m.wrapper": ("{where}: 쓰는 곳에 풀어 넣고 정의 지우기", "{where}: inline into the caller and delete the definition"),
    "m.tiny": ("작은 파일 {k}개를 하나로 합치기(둘부터)", "Merge the {k} small files into one (start with two)"),
    "m.lonely": ("{file}을(를) 쓰는 곳 {user}에 합치기", "Merge {file} into its only user, {user}"),
    "again": ("다음 걸음은 `habitree refactor --focus {focus}`로 다시 보기",
              "For the next step, run `habitree refactor --focus {focus}` again"),
    "b.outer": ("바깥 모양 고정: 쓰는 곳({fan}곳)이 부르는 이름과 인자는 그대로 두고 새 자리를 정하기: {dest}",
                "Fix the outside: keep the names and arguments its {fan} users call, and pick the new home: {dest}"),
    "b.outer0": ("바깥 모양 고정: 다른 파일에서 부르는 곳이 없으니 새 자리만 정하기: {dest}",
                 "Fix the outside: no other file calls it, so just pick the new home: {dest}"),
    "b.inner": ("안쪽 옮기기: 한 번에 한 곳씩, {places}", "Move the inside, one place at a time: {places}"),
    "b.old": ("옛 길 지우기: 옛 이름·복사본·중계 코드를 지우고 `habitree map find {name}`으로 남은 곳 확인",
              "Remove the old path: delete old names, copies and forwarding code; check with `habitree map find {name}`"),
    "d.file": ("있는 경계({seams})별 파일", "one file per existing seam ({seams})"),
    "d.file0": ("역할별 파일(경계를 먼저 목록으로)", "one file per role (list the seams first)"),
    "d.function": ("같은 파일 안의 작은 함수들", "small functions in the same file"),
    "d.same_body": ("남길 한 곳 {keep}", "the one place to keep, {keep}"),
    "d.clone": ("{keep} 안의 함수 하나", "one function in {keep}"), "d.same_name": ("원본 {name} 하나", "one original {name}"),
    "d.coupling": ("함께 바뀌는 것을 담을 한 파일", "one file for what changes together"),
    "d.mutual": ("한 방향으로만 참조하는 구조", "references in one direction only"),
    "d.other": ("합치거나 지울 자리", "where things merge or go"),
    "head": ("# 정리 제안 · 후보 {total}개 중 {shown}개 · 검증 명령: {verify} · git: {git}",
             "# Refactoring advice · {shown} of {total} candidates · verify: {verify} · git: {git}"),
    "moved": ("<옮긴 이름>", "<moved name>"), "commits": ("커밋 {n}개", "{n} commits"), "none": ("없음", "none"),
    "nogit": ("없음(변경 횟수·함께 바뀜은 건너뜀)", "none (change counts and co-changes skipped)"),
    "why": ("왜: ", "Why: "), "pick": ("권함: ", "Suggested: "), "rule": ("규칙", "rule"),
    "more": ("그 밖 {n}개({kinds}) · 더 보기 --top {top} · 좁히기 --focus <경로>",
             "{n} more ({kinds}) · see more with --top {top} · narrow with --focus <path>"),
    "empty": ("정리할 후보를 찾지 못했습니다(코드 파일 {n}개를 봤습니다).", "No candidates found ({n} code files checked)."),
    "nofocus": ("초점({focus})에 맞는 후보가 없습니다.", "No candidates match the focus ({focus})."),
    "tail": ("제안일 뿐 코드는 고치지 않았습니다. 틀린 제안이면 `habitree rules miss <규칙 id> --feedback \"…\"`.",
             "Advice only; no code was changed. If a suggestion is wrong: `habitree rules miss <rule id> --feedback \"…\"`."),
}


def add_arguments(p):
    p.add_argument("paths", nargs="*", help="이 경로만 / only these paths")
    p.add_argument("--focus", nargs="+", help="경로나 낱말로 좁히기 / narrow by paths or words")
    p.add_argument("--mode", choices=("auto", "mini", "bold"), default="auto",
                   help="규모: auto(상황에 맞춤), mini(작은 단계), bold(큰 정리) / scale")
    p.add_argument("--top", type=int, default=3, help="보여 줄 후보 수(기본 3) / candidates to show")
    p.add_argument("--json", action="store_true", help="AI가 따라 할 단계 구조 / steps as JSON")


def say(key, lang, **kw):
    return fmt(T[key][0 if lang == "ko" else 1], {k: ", ".join(map(str, v)) if isinstance(v, list) else v
                                                  for k, v in kw.items()})


def _q(path):
    return f'"{path}"' if " " in path else path


def problem(x, lang):
    f, sub = x["facts"], x["sub"]
    if sub == "coupling":
        f = dict(f, where=[say("p.pair", lang, a=a, b=b, n=n, d=d) for a, b, n, d in f["pairs"]])
    if "funcs" in f:
        f = dict(f, funcs=[T["p.fn"][lang != "ko"].format(*fn) for fn in f["funcs"]])
    text = say("p." + sub, lang, **f)
    if x["kind"] == "concentration":
        text += say("p.funcs", lang, **f) if f["funcs"] and sub == "file" else ""
        text += say("p.changes", lang, **f) if f["changes"] else ""
    return text


def steps(x, lang):
    """순서대로 할 단계: 안전망 → 덜어 내기 → (작은 단계 하나 | 바깥 고정 → 안쪽 옮기기 → 옛 길 지우기).
    / Ordered steps: safety net, removals, then one small step or the staged bold plan."""
    f, files, sub = x["facts"], x["files"], x["sub"]
    if sub == "file" and not f["seams"]:
        sub = "file0"
    moved = say("moved", lang) if x["kind"] == "concentration" else (f.get("names") or [files[0]])[0]
    kw = dict(f, name=(f.get("names") or [files[0]])[0], files=files[:2], moved=moved)
    safe = "both" if len(x["safety"]) == 2 else (x["safety"] or [""])[0]
    out = [{"do": say("s." + safe, lang, **kw), "files": files, "check": CHECK}] if safe else []
    if not out and x["mode"] == "bold":
        out.append({"do": say("s.ok", lang), "files": [], "check": CHECK})
    for t in x.get("trim", []):
        out.append({"do": say("trim." + t["sub"], lang, **t["facts"]), "files": t["files"], "check": CHECK})
    if x["mode"] == "mini":
        out.append({"do": say("m." + sub, lang, **kw), "files": files, "check": CHECK})
        out.append({"do": say("again", lang, focus=_q(f.get("file") or files[0])), "files": [], "check": ""})
        return out
    dest = say("d." + sub if "d." + sub in T else "d.other", lang, **kw)
    outer = "b.outer" if x["fan_in"] else "b.outer0"
    out.append({"do": say(outer, lang, fan=x["fan_in"], dest=dest), "files": files, "check": CHECK})
    out.append({"do": say("b.inner", lang, places=(f.get("where") or f.get("seams") or files)[:4]), "files": files,
                "check": CHECK})
    out.append({"do": say("b.old", lang, name=moved), "files": files, "check": CHECK})
    return out


def run(args, ctx):
    lang, top = ctx.lang, max(1, args.top)
    idx = index.ensure(ctx)  # map 색인이 없으면 만들고, 있으면 바뀐 파일만 다시 읽는다
    focus = list(args.paths or []) + list(args.focus or [])
    found, proj = rf.advise(ctx, idx, focus, args.mode)
    shown = found[:top]
    for x in shown:
        x["steps"] = steps(x, lang)
        msg = proj.crit[x["rule"]]["message"]
        x["why_text"] = fmt(tr(msg.get("ai" if args.json else "user"), lang), x["facts"])
    if args.json:
        keys = ("kind", "sub", "level", "rule", "files", "facts", "mode", "steps")
        print(json.dumps({"verify": proj.verify, "git": proj.log is not None, "total": len(found),
                          "candidates": [dict({k: x[k] for k in keys}, why=x["why_text"],
                                              reasons=[w for w, _ in x["why"]]) for x in shown]},
                         ensure_ascii=False, indent=1))
        return 0
    verify = ", ".join(proj.verify) or say("none", lang)
    git = say("commits", lang, n=len(proj.log)) if proj.log is not None else say("nogit", lang)
    print(say("head", lang, total=len(found), shown=len(shown), verify=verify, git=git))
    if not found:
        print(say("nofocus", lang, focus=", ".join(focus)) if focus else say("empty", lang, n=len(proj.code)))
        return 0
    marks = "①②③④⑤⑥⑦⑧⑨" if lang == "ko" else ""
    for i, x in enumerate(shown, 1):
        label = say(x["kind"], lang) + (f" · {say('info', lang)}" if x["level"] == "info" else "")
        print(f"{i}. [{label}] {problem(x, lang)}")
        print("   " + say("why", lang) + x["why_text"])
        reasons = ", ".join(say("r." + w, lang, **kw) for w, kw in x["why"])
        print(f"   {say('pick', lang)}{say(x['mode'], lang)} · {reasons} · {say('rule', lang)} {x['rule']}")
        for j, s in enumerate(x["steps"]):
            mark = marks[j] if j < len(marks) else f"{j + 1})"
            print(f"   {mark} {s['do']}" + (f" → {s['check']}" if s["check"] else ""))
    rest = found[top:]
    if rest:
        kinds = ", ".join(f"{say(k, lang)} {n}" for k in rf.KINDS for n in [sum(1 for x in rest if x["kind"] == k)] if n)
        print(say("more", lang, n=len(rest), kinds=kinds, top=min(len(found), top + 5)))
    print(say("tail", lang))
    return 0
