"""check: 지도·문서·규칙이 실제와 맞는지 AI 없이 점검한다. / Deterministic checks, no AI involved.

점검 항목(id 앞부분으로 고르거나 뺄 수 있다):
  map.missing-folder     최상위 폴더가 지도(README)에 없음
  map.folder-readme      최상위 폴더에 README.md가 없음
  docs.updated           지도·폴더 README에 '마지막 갱신' 날짜가 없거나 오래됨
  docs.link              깨진 상대 링크·앵커
  docs.log               변경 기록 파일이 없음
  docs.instructions-size AGENTS.md 32KiB 초과, CLAUDE.md 줄 수 초과
  docs.import            CLAUDE.md·AGENTS.md의 @import 대상이 없음
  docs.hidden-unicode    지침·규칙 파일 안의 보이지 않는 제어 문자
  docs.home-path         지침 파일에 박힌 개인 폴더 경로
  rules.invalid          규칙 DB 형식·뜻 오류
  rules.doc-stale        RULES.md가 규칙 DB와 다름
  rules.auto             규칙의 자동 검사(check.run) 실패
  rules.duplicate        같은 뜻으로 보이는 규칙 쌍
  rules.noisy            '틀렸다' 반응이 많은 감지 규칙
  generated.edited       생성 구역을 사람이 직접 고침
  paths.collision        NFC·NFD나 대소문자만 다른 파일 이름
  git.precompose         macOS에서 git core.precomposeUnicode가 꺼짐
  custom.<id>            설정 checks.custom의 명령
종료 코드: 오류가 있으면 1. / Exit code 1 when any error is found.
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from urllib.parse import unquote

from ..core import HabitreeError
from ..core import io as hio
from ..core.i18n import tr
from ..core.markdown import anchors, digest, get_block, links
from ..core.paths import git, glob_match, iter_files, nfc, resolve, top_dirs
from ..core.ruledb import PAUSE_SUGGEST, PROBATION, MIN_VOTES, RuleDB, vote_stats
from ..core.timeutil import now_utc
from . import export

SUMMARY = {"ko": "지도·문서·규칙이 실제와 맞는지 점검(오류가 있으면 종료 코드 1)",
           "en": "Check that map, docs and rules match reality (exit 1 on errors)"}

LEVEL_ORDER = {"error": 0, "warn": 1, "info": 2}
LEVEL_TEXT = {"error": {"ko": "오류", "en": "error"}, "warn": {"ko": "경고", "en": "warning"},
              "info": {"ko": "알림", "en": "notice"}}
HIDDEN = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿]")
HOME = re.compile(r"(?:[A-Za-z]:\\Users\\[^\\\s\"'`<>|]+|/Users/[^/\s\"'`<>]+|/home/[^/\s\"'`<>]+)")
IMPORT = re.compile(r"(?<![\w@`])@((?:\.{1,2}/|/)?[\w\-.]+(?:/[\w\-.]+)*)")
MAX_SCAN_BYTES = 1_000_000


class Finding:
    __slots__ = ("id", "level", "path", "line", "msg")

    def __init__(self, cid, level, msg, path="", line=0):
        self.id, self.level, self.msg, self.path, self.line = cid, level, msg, path, line

    def to_json(self, lang):
        return {"id": self.id, "level": self.level, "path": self.path, "line": self.line, "message": tr(self.msg, lang)}


def add_arguments(p):
    p.add_argument("--json", action="store_true", help="결과를 JSON으로 / JSON output")
    p.add_argument("--only", nargs="+", help="이 id(앞부분)만 / only these check ids (prefix)")
    p.add_argument("--skip", nargs="+", help="이 id(앞부분)는 뺌 / skip these check ids (prefix)")
    p.add_argument("--no-auto", action="store_true", help="규칙의 자동 검사를 돌리지 않음 / skip rules.auto")


# ── 개별 점검 ──

def check_map(ctx, files, out):
    map_rel = ctx.get("docs.map")
    path = ctx.p(map_rel)
    if not path.exists():
        out.append(Finding("map.missing-folder", "error",
                           {"ko": f"지도 파일이 없습니다: {map_rel}", "en": f"Map file missing: {map_rel}"}, map_rel))
        return
    text = hio.read_text(path)
    targets = set()
    for _, tgt in links(text):
        tgt = nfc(unquote(tgt.split("#")[0])).strip("./").rstrip("/")
        if tgt:
            targets.add(tgt.split("/")[0])
    for d in top_dirs(ctx.root, ctx.get("exclude")):
        if d not in targets:
            out.append(Finding("map.missing-folder", "error",
                               {"ko": f"지도({map_rel})에 없는 폴더: {d}/ (지도 표에 한 줄 더하기)",
                                "en": f"Folder not in the map ({map_rel}): {d}/ (add a row)"}, map_rel))
        fr = ctx.get("docs.folder_readme")
        if fr and not (ctx.root / d / "README.md").exists():
            out.append(Finding("map.folder-readme", "error" if fr == "error" else "warn",
                               {"ko": f"폴더에 README.md가 없음: {d}/ (목적·구조·마지막 갱신)",
                                "en": f"Folder has no README.md: {d}/ (purpose, layout, last updated)"}, f"{d}/"))


def check_updated(ctx, out):
    labels = ctx.get("docs.updated_labels") or []
    rx = re.compile("(?:" + "|".join(re.escape(x) for x in labels) + r")[^0-9\n]*(\d{4}-\d{2}-\d{2})") if labels else None
    stale = ctx.get("docs.stale_days", 60)
    docs = [ctx.get("docs.map")] + [f"{d}/README.md" for d in top_dirs(ctx.root, ctx.get("exclude"))]
    for rel in docs:
        p = ctx.p(rel)
        if not p.exists() or rx is None:
            continue
        m = rx.search(hio.read_text(p))
        if not m:
            out.append(Finding("docs.updated", "warn",
                               {"ko": f"'{labels[0]}' 날짜가 없음: {rel}", "en": f"No '{labels[-1]}' date: {rel}"}, rel))
            continue
        try:
            age = (now_utc().date() - datetime.strptime(m.group(1), "%Y-%m-%d").date()).days
        except ValueError:
            continue
        if stale and age > stale:
            out.append(Finding("docs.updated", "info",
                               {"ko": f"{age}일 동안 갱신되지 않음: {rel} (내용이 맞는지 확인)",
                                "en": f"Not updated for {age} days: {rel} (check it is still right)"}, rel))


def check_links(ctx, files, out):
    md_files = [f for f in files if f.lower().endswith(".md")]
    anchor_cache = {}

    def anchors_of(rel):
        if rel not in anchor_cache:
            p = resolve(ctx.root, rel)
            anchor_cache[rel] = anchors(hio.read_text(p)) if p and p.is_file() else set()
        return anchor_cache[rel]

    existing = set(files)
    for rel in md_files:
        src = resolve(ctx.root, rel)
        if src is None:
            continue
        text = hio.read_text(src)
        base = rel.rsplit("/", 1)[0] if "/" in rel else ""
        for line, target in links(text):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("//"):
                continue
            if any(c in target for c in "{}<>") or target.startswith("@"):
                continue
            raw_path, _, frag = target.partition("#")
            path_part = nfc(unquote(raw_path))
            frag = nfc(unquote(frag))
            if not path_part:
                tgt_rel = rel
            else:
                joined = path_part.lstrip("/") if path_part.startswith("/") else (base + "/" + path_part if base else path_part)
                parts = []
                for seg in joined.split("/"):
                    if seg in ("", "."):
                        continue
                    if seg == "..":
                        if parts:
                            parts.pop()
                        continue
                    parts.append(seg)
                tgt_rel = "/".join(parts)
                if tgt_rel not in existing and resolve(ctx.root, tgt_rel) is None:
                    out.append(Finding("docs.link", "error",
                                       {"ko": f"깨진 링크: {target}", "en": f"Broken link: {target}"}, rel, line))
                    continue
            if frag and tgt_rel.lower().endswith(".md") and (tgt_rel in existing or resolve(ctx.root, tgt_rel)):
                if frag not in anchors_of(tgt_rel) and not re.match(r"^L\d+(-L\d+)?$", frag):
                    out.append(Finding("docs.link", "error",
                                       {"ko": f"없는 제목 앵커: {target}", "en": f"Missing heading anchor: {target}"},
                                       rel, line))


def check_log(ctx, out):
    rel = ctx.get("docs.log")
    if rel and not ctx.p(rel).exists():
        out.append(Finding("docs.log", "warn",
                           {"ko": f"변경 기록 파일이 없음: {rel}", "en": f"Change log missing: {rel}"}, rel))


def check_instructions(ctx, files, out):
    names = set(ctx.get("docs.instructions") or [])
    max_bytes = ctx.get("docs.agents_md_max_bytes", 32768)
    max_lines = ctx.get("docs.claude_md_max_lines", 200)
    for rel in files:
        name = rel.rsplit("/", 1)[-1]
        if name not in names:
            continue
        p = resolve(ctx.root, rel)
        if p is None:
            continue
        data = p.read_bytes()
        text = hio.read_bytes_text(data)
        if name == "AGENTS.md" and len(data) > max_bytes:
            out.append(Finding("docs.instructions-size", "error",
                               {"ko": f"AGENTS.md가 {len(data)}바이트로 한도 {max_bytes}를 넘음(넘친 부분은 도구가 읽지 않을 수 있음)",
                                "en": f"AGENTS.md is {len(data)} bytes, over the {max_bytes} limit (tools may cut it)"}, rel))
        n_lines = text.count("\n") + 1
        if name == "CLAUDE.md" and n_lines > max_lines:
            out.append(Finding("docs.instructions-size", "warn",
                               {"ko": f"CLAUDE.md가 {n_lines}줄(권장 {max_lines}줄 이하). 매 대화에 실려 토큰이 든다",
                                "en": f"CLAUDE.md has {n_lines} lines (recommended ≤ {max_lines}); it loads into every session"},
                               rel))
        base = rel.rsplit("/", 1)[0] if "/" in rel else ""
        for i, line in enumerate(text.split("\n"), 1):
            for m in IMPORT.finditer(line):
                target = m.group(1)
                if "." not in target and "/" not in target:
                    continue
                tgt = (ctx.root / target.lstrip("/")) if target.startswith("/") else ctx.p((base + "/" if base else "") + target)
                if not tgt.exists():
                    out.append(Finding("docs.import", "error",
                                       {"ko": f"@import 대상이 없음: @{target}", "en": f"@import target missing: @{target}"},
                                       rel, i))
            if HOME.search(line):
                out.append(Finding("docs.home-path", "warn",
                                   {"ko": "개인 폴더 경로가 박혀 있음(다른 사람·컴퓨터에서 틀림)",
                                    "en": "Hard-coded personal home path (wrong on other machines)"}, rel, i))
    scan = [r for r in files if r.rsplit("/", 1)[-1] in names] + [ctx.get("rules.db")]
    for rel in scan:
        p = resolve(ctx.root, rel)
        if p is None or not p.is_file():
            continue
        text = hio.read_text(p)
        for i, line in enumerate(text.split("\n"), 1):
            if HIDDEN.search(line.lstrip("﻿") if i == 1 else line):
                out.append(Finding("docs.hidden-unicode", "error",
                                   {"ko": "보이지 않는 제어 문자(방향 바꿈·폭 없는 공백)가 있음",
                                    "en": "Invisible control characters (bidi or zero-width)"}, rel, i))


def _text_files(ctx, files, globs):
    for rel in files:
        if not any(glob_match(rel, g) for g in globs):
            continue
        p = resolve(ctx.root, rel)
        try:
            if p is None or p.stat().st_size > MAX_SCAN_BYTES:
                continue
            data = p.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:4096]:
            continue
        yield rel, hio.read_bytes_text(data)


def run_auto(ctx, db, files, out):
    for r in db.active():
        chk = r.get("check", {})
        run = chk.get("run")
        if chk.get("type") != "auto" or not run:
            continue
        level = "error" if r.get("level") == "must" else "warn"
        cid = f"rules.auto.{r['id']}"
        globs = run.get("in") or ["**/*"]
        if run.get("cmd"):
            exe = run["cmd"]
            try:
                res = subprocess.run(exe, cwd=str(ctx.root), capture_output=True, timeout=run.get("timeout", 120))
                ok = res.returncode == 0
                tail = hio.read_bytes_text((res.stdout or b"") + (res.stderr or b"")).strip().splitlines()[-3:]
            except (OSError, subprocess.SubprocessError) as e:
                ok, tail = False, [str(e)]
            if not ok:
                out.append(Finding(cid, level, {"ko": f"자동 검사 실패: {' '.join(exe)} · {' / '.join(tail)}",
                                                "en": f"Auto check failed: {' '.join(exe)} · {' / '.join(tail)}"},
                                   ctx.get("rules.db")))
        if run.get("forbid"):
            rx = re.compile(run["forbid"])
            for rel, text in _text_files(ctx, files, globs):
                for i, line in enumerate(text.split("\n"), 1):
                    if rx.search(line):
                        out.append(Finding(cid, level, {"ko": f"규칙 위반({r['id']}): 금지한 형식이 있음",
                                                        "en": f"Rule violated ({r['id']}): forbidden pattern found"},
                                           rel, i))
        if run.get("require"):
            rx = re.compile(run["require"])
            if not any(rx.search(text) for _, text in _text_files(ctx, files, globs)):
                out.append(Finding(cid, level, {"ko": f"규칙 위반({r['id']}): 있어야 할 내용이 없음",
                                                "en": f"Rule violated ({r['id']}): required pattern missing"},
                                   ctx.get("rules.db")))
        if run.get("max_lines"):
            for rel, text in _text_files(ctx, files, globs):
                n = text.count("\n") + 1
                if n > run["max_lines"]:
                    out.append(Finding(cid, level, {"ko": f"규칙 위반({r['id']}): {n}줄로 한도 {run['max_lines']}줄 초과",
                                                    "en": f"Rule violated ({r['id']}): {n} lines, over {run['max_lines']}"},
                                       rel))


def check_rules(ctx, files, out, no_auto=False):
    rel = ctx.get("rules.db")
    p = ctx.p(rel)
    if not p.exists():
        return None
    try:
        db = RuleDB.load(p, ctx.lang)
    except HabitreeError as e:
        out.append(Finding("rules.invalid", "error", str(e), rel))
        return None
    for prob in db.validate():
        out.append(Finding("rules.invalid", "error", prob, rel))
    doc_rel = ctx.get("rules.doc")
    if doc_rel:
        doc = ctx.p(doc_rel)
        want = db.render_md(doc.parent, p)
        if not doc.exists() or hio.read_text(doc) != want:
            out.append(Finding("rules.doc-stale", "warn",
                               {"ko": f"{doc_rel}가 규칙 DB와 다름 (habitree rules doc)",
                                "en": f"{doc_rel} differs from the rule DB (habitree rules doc)"}, doc_rel))
    for score, a, b in db.duplicate_pairs():
        out.append(Finding("rules.duplicate", "warn",
                           {"ko": f"같은 뜻으로 보이는 규칙({score:.2f}): {a} · {b} (하나로 합치면 지적 횟수가 모인다)",
                            "en": f"Rules look the same ({score:.2f}): {a} · {b} (merge so feedback counts add up)"}, rel))
    for r in db.active():
        if not r.get("detect"):
            continue
        st = vote_stats(r)
        if st["total"] >= MIN_VOTES and st["useless"] > PAUSE_SUGGEST:
            out.append(Finding("rules.noisy", "warn",
                               {"ko": f"'틀렸다' 반응 {st['useless']:.0%}: {r['id']} (끄기 제안: habitree rules pause)",
                                "en": f"{st['useless']:.0%} 'wrong' votes: {r['id']} (consider habitree rules pause)"}, rel))
        elif st["total"] >= MIN_VOTES and st["useless"] >= PROBATION:
            out.append(Finding("rules.noisy", "info",
                               {"ko": f"보호관찰 중({st['useless']:.0%}): {r['id']}",
                                "en": f"On probation ({st['useless']:.0%}): {r['id']}"}, rel))
    if not no_auto:
        run_auto(ctx, db, files, out)
    return db


def check_generated(ctx, out):
    manifest = hio.load_json(ctx.p(export.MANIFEST_REL), {}) or {}
    for rel, blocks in (manifest.get("files") or {}).items():
        p = ctx.p(rel)
        if not p.exists():
            continue
        text = hio.read_text(p)
        for name, dig in blocks.items():
            cur = get_block(text, name)
            if cur is not None and digest(cur) != dig:
                out.append(Finding("generated.edited", "info",
                                   {"ko": f"생성 구역 [{name}]을 직접 고쳤음(다음 export가 두고 감. 원본을 고친 뒤 export --force)",
                                    "en": f"Managed block [{name}] was edited by hand (export keeps it; fix the source, then export --force)"},
                                   rel))


def check_paths(ctx, files, out):
    groups = defaultdict(list)
    for rel in files:
        groups[nfc(rel).casefold()].append(rel)
    raw = git(ctx.root, "ls-files", "-z")
    if raw:
        import unicodedata
        for item in raw.split(b"\0"):
            s = item.decode("utf-8", errors="replace")
            if s and s != unicodedata.normalize("NFC", s):
                out.append(Finding("paths.collision", "warn",
                                   {"ko": f"git에 NFD(자모 분리)로 등록된 이름: {nfc(s)}",
                                    "en": f"Name stored in git as NFD (decomposed): {nfc(s)}"}, nfc(s)))
    for key, items in groups.items():
        if len(set(items)) > 1:
            out.append(Finding("paths.collision", "error",
                               {"ko": f"대소문자·정규화만 다른 파일 이름: {', '.join(sorted(set(items)))}",
                                "en": f"File names differ only by case or normalization: {', '.join(sorted(set(items)))}"},
                               items[0]))
    if sys.platform == "darwin":
        v = git(ctx.root, "config", "--get", "core.precomposeunicode")
        if v is not None and v.strip().lower() == b"false":
            out.append(Finding("git.precompose", "warn",
                               {"ko": "git core.precomposeUnicode가 꺼져 있어 한글 파일 이름이 NFD로 등록될 수 있음",
                                "en": "git core.precomposeUnicode is off; Korean names may be stored as NFD"}))


def check_custom(ctx, out):
    for c in ctx.get("checks.custom") or []:
        cid = f"custom.{c.get('id', 'check')}"
        cmd = c.get("cmd")
        if not cmd:
            continue
        try:
            res = subprocess.run(cmd, cwd=str(ctx.root), capture_output=True, timeout=c.get("timeout", 120))
            ok = res.returncode == 0
            tail = hio.read_bytes_text((res.stdout or b"") + (res.stderr or b"")).strip().splitlines()[-3:]
        except (OSError, subprocess.SubprocessError) as e:
            ok, tail = False, [str(e)]
        if not ok:
            msg = c.get("message") or {"ko": f"명령 실패: {' '.join(cmd)}", "en": f"Command failed: {' '.join(cmd)}"}
            if tail:
                msg = {k: f"{tr(msg, k)} · {' / '.join(tail)}" for k in ("ko", "en")}
            out.append(Finding(cid, c.get("level", "error"), msg))


def check_models(ctx, out):
    """모델 배분(v0.3): models.deprecated·models.floor·models.price-stale. 설정에 models 절이 없으면 넘어간다."""
    from ..core.modelpolicy import findings
    for f in findings(ctx):
        out.append(Finding(f["id"], f["level"], f["msg"], f.get("path", "")))


def collect(ctx, no_auto=False):
    files = iter_files(ctx.root, ctx.get("exclude"))
    out = []
    check_map(ctx, files, out)
    check_updated(ctx, out)
    check_links(ctx, files, out)
    check_log(ctx, out)
    check_instructions(ctx, files, out)
    check_rules(ctx, files, out, no_auto)
    check_generated(ctx, out)
    check_paths(ctx, files, out)
    check_custom(ctx, out)
    check_models(ctx, out)
    disabled = ctx.get("checks.disable") or []
    out = [f for f in out if not any(f.id == d or f.id.startswith(d + ".") for d in disabled)]
    return out, files


def _match(fid, prefixes):
    return any(fid == p or fid.startswith(p.rstrip(".") + ".") or fid.startswith(p) for p in prefixes)


def run(args, ctx):
    findings, files = collect(ctx, args.no_auto)
    if args.only:
        findings = [f for f in findings if _match(f.id, args.only)]
    if args.skip:
        findings = [f for f in findings if not _match(f.id, args.skip)]
    findings.sort(key=lambda f: (LEVEL_ORDER[f.level], f.id, f.path, f.line))
    errors = sum(1 for f in findings if f.level == "error")
    lang = ctx.lang
    if args.json:
        print(json.dumps({"root": str(ctx.root), "files": len(files), "errors": errors,
                          "findings": [f.to_json(lang) for f in findings]}, ensure_ascii=False, indent=1))
        return 1 if errors else 0
    ko = lang == "ko"
    print(("Habitree 점검" if ko else "Habitree check") + f": {ctx.root}")
    print(f"  {'파일' if ko else 'files'} {len(files)}")
    if not findings:
        print("  " + ("문제 없음" if ko else "No problems"))
        return 0
    for f in findings:
        loc = f"{f.path}:{f.line}" if f.line else f.path
        print(f"  [{tr(LEVEL_TEXT[f.level], lang)}] {f.id}  {loc}\n      {tr(f.msg, lang)}")
    warns = sum(1 for f in findings if f.level == "warn")
    print(("\n  오류 {e} · 경고 {w} · 알림 {i}" if ko else "\n  errors {e} · warnings {w} · notices {i}").format(
        e=errors, w=warns, i=len(findings) - errors - warns))
    return 1 if errors else 0
