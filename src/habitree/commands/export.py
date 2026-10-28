"""export: 규칙 DB에서 AI 도구가 읽는 지침 파일을 만든다. / Generate agent instruction files from the rule DB.

- AGENTS.md: 모든 도구 공용(Codex·Cursor·Copilot·Gemini 등). 생성 구역만 고친다.
- CLAUDE.md: 맨 위에 `@AGENTS.md` 한 줄과 Claude 전용 안내만.
- 생성 구역의 해시를 .habitree/manifest.json에 남겨, 사용자가 구역을 직접 고쳤으면 덮어쓰지 않는다(--force로 덮음).
- AI가 읽는 파일이므로 설정 언어 한 벌만 쓴다(토큰 절약).
"""
from ..core import io as hio
from ..core.i18n import tr
from ..core.markdown import digest, get_block, put_block
from ..core.paths import iter_files
from ..core.ruledb import RuleDB

SUMMARY = {"ko": "규칙 DB에서 AGENTS.md·CLAUDE.md 생성 구역을 다시 만들기",
           "en": "Regenerate the managed blocks in AGENTS.md and CLAUDE.md from the rule DB"}

MANIFEST_REL = ".habitree/manifest.json"
TARGETS = {"agents": ("AGENTS.md", "habitree", "end"), "claude": ("CLAUDE.md", "habitree-claude", "start")}

CYCLE = {
    "ko": """## Habitree 작업 순환

이 프로젝트는 Habitree로 작업 습관을 관리한다. 모든 작업은 이 순서를 따르되, 절차는 일의 크기에 맞춘다.

1. 찾기: [지도]({map})와 `habitree rules brief <범위>`로 관련 문서·도구·규칙을 먼저 본다. 코드는 `habitree map find <말>`로 위치부터 찾고 필요한 부분만 연다.
2. 있으면 쓰기: 있는 것을 쓰고, 낡았거나 틀린 곳은 그 자리에서 고친다.
3. 없으면 만들기: 되풀이가 실제로 보일 때만 도구·모듈·양식으로 만든다. 한 번 쓰고 마는 것은 만들지 않는다.
4. 기록하기: 구조나 쓰는 법이 바뀌었을 때만 폴더 README, 지도, [변경 기록]({log})에 반영한다. 작은 수정은 기록하지 않는다.
5. 고치기: 지금 못 고친 문제는 변경 기록의 '손볼 것'에 적는다. 쌓는 만큼 덜어낸다: 겹치거나 안 쓰이는 규칙·도구·코드는 합치거나 지운다.
6. 점검하기: 끝내기 전에 검증 명령(테스트·빌드)을 돌린다. 문서·구조를 바꿨으면 `habitree check`도 돌린다.

사용자 피드백은 고치는 것과 동시에 규칙으로 남긴다. 같은 뜻 규칙이 있으면 `habitree rules hit <id> --feedback "…"`, 없으면 `habitree rules add --scope … --aspect … --rule "…" --why "…" --feedback "…"`. 전체 규칙: [{doc}]({doc}).""",
    "en": """## Habitree work cycle

This project manages its working habits with Habitree. Every task follows this order, scaled to the size of the task.

1. Find: check the [map]({map}) and `habitree rules brief <scope>` for related docs, tools and rules first. For code, locate it with `habitree map find <word>` and open only what you need.
2. Reuse: use what exists; fix stale or wrong parts on the spot.
3. Build: make a tool, module or template only when the work actually repeats; nothing used just once.
4. Record: update the folder README, the map and the [change log]({log}) only when structure or usage changed. Small fixes need no record.
5. Fix later: write problems you cannot fix now under 'To fix' in the change log. Trim as much as you grow: merge or remove overlapping or unused rules, tools and code.
6. Check: before finishing, run the verify commands (tests, build). Run `habitree check` too if you changed docs or structure.

Record user feedback as a rule while fixing it: `habitree rules hit <id> --feedback "…"` when a rule with the same meaning exists, otherwise `habitree rules add --scope … --aspect … --rule "…" --why "…" --feedback "…"`. All rules: [{doc}]({doc}).""",
}
LEAN = {
    "find": {"ko": "- 만들기 전에 이미 있는 것을 찾아 쓴다.", "en": "- Before building, look for what already exists and reuse it."},
    "map": {"ko": " 코드 위치는 `habitree map find <말>`로 먼저 찾는다.", "en": " Locate code with `habitree map find <word>` first."},
    "verify": {"ko": "- 끝내기 전에 {cmds}를 돌린다.", "en": "- Before finishing, run {cmds}."},
    "feedback": {"ko": "- 사용자가 결과를 바로잡으면, 같은 지적을 다시 받지 않도록 그 내용을 규칙으로 남긴다(방법은 `.habitree/RULES.md` 맨 위).",
                 "en": "- When the user corrects your work, record it as a rule so the same correction is never needed again (how: top of `.habitree/RULES.md`)."},
}
PROJECT_HEAD = {"ko": "### 이 프로젝트의 규칙", "en": "### Rules of this project"}
MUST_HEAD = {"ko": "### 필수 규칙 (요약)", "en": "### Must rules (summary)"}
CLAUDE_NOTE = {
    "ko": "@AGENTS.md\n\nClaude Code 전용: Habitree 플러그인을 설치하면 훅이 작업 중 비효율을 먼저 알려 준다. 경고가 틀렸으면 `habitree rules miss <id>`로 남긴다.",
    "en": "@AGENTS.md\n\nClaude Code only: with the Habitree plugin installed, hooks warn about inefficient work early. If a warning was wrong, record it with `habitree rules miss <id>`.",
}


def add_arguments(p):
    p.add_argument("--force", action="store_true", help="직접 고친 생성 구역도 덮어씀 / overwrite edited blocks")
    p.add_argument("--dry-run", action="store_true", help="쓰지 않고 할 일만 보기 / show without writing")


def agents_block(ctx, db):
    lang = ctx.lang
    if ctx.get("export.style", "lean") == "lean":
        return lean_block(ctx, db)
    text = CYCLE[lang].format(map=ctx.get("docs.map"), log=ctx.get("docs.log"), doc=ctx.get("rules.doc"))
    db = RuleDB(db.file_data(), db.path)  # 프로젝트에 있는 규칙만 / persisted rules only
    brief = db.brief(["global"], must_only=True, budget=ctx.get("export.brief_budget", 3000), lang=lang,
                     compact=True, skip_scopes=("work/cycle",))
    body = brief.split("\n", 1)[1].strip() if "\n" in brief else ""
    return text + ("\n\n" + MUST_HEAD[lang] + "\n" + body if body else "")


def lean_block(ctx, db):
    """걷어낸 판: 핵심 세 줄 + 이 프로젝트에서 쌓인 규칙만(꾸러미의 일반 규칙은 빼고 기계 점검·훅이 지킨다).
    / Lean: three lines plus only the rules this project grew; generic pack rules are left to checks and hooks."""
    lang = ctx.lang
    data = db.file_data()
    own = [r for r in data.get("rules", []) if not r.get("origin") and r.get("status", "active") == "active"]
    # 상황에 맞을 때만 싣는다: 측정에서 작은 프로젝트의 색인 안내와 등록 안 된 검증 안내는 턴만 늘렸다
    line = tr(LEAN["find"], lang)
    big = ctx.get("export.map_hint_files", 150)
    if not big or len(iter_files(ctx.root, ctx.get("exclude"))) >= big:  # 0이면 늘 싣는다
        line += tr(LEAN["map"], lang)
    lines = ["## Habitree", "", line]
    verify = ctx.get("verify") or {}
    if verify:
        cmds = ", ".join("`" + " ".join(c) + "`" for c in verify.values() if c)
        lines.append(tr(LEAN["verify"], lang).format(cmds=cmds))
    lines.append(tr(LEAN["feedback"], lang))
    text = chr(10).join(lines)
    if not own:
        return text
    view = RuleDB(dict(data, rules=own), db.path)
    brief = view.brief(["global"], budget=ctx.get("export.brief_budget", 3000), lang=lang, compact=True)
    body = brief.split("\n", 1)[1].strip() if "\n" in brief else ""
    return text + ("\n\n" + PROJECT_HEAD[lang] + "\n" + body if body else "")


def claude_block(ctx, db):
    if ctx.get("export.style", "lean") == "lean":
        return "@AGENTS.md"
    return CLAUDE_NOTE[ctx.lang]


def plan(ctx, db, force=False):
    """(경로, 구역, 내용, 동작) 목록. 동작: create|update|same|kept. / What export would do."""
    manifest = hio.load_json(ctx.p(MANIFEST_REL), {}) or {}
    files = manifest.get("files", {})
    builders = {"agents": agents_block, "claude": claude_block}
    out = []
    for target in ctx.get("export.targets", []):
        if target not in TARGETS:
            continue
        rel, name, where = TARGETS[target]
        content = builders[target](ctx, db)
        path = ctx.p(rel)
        text = hio.read_text(path) if path.exists() else ""
        cur = get_block(text, name)
        recorded = files.get(rel, {}).get(name)
        if cur is None:
            action = "create"
        elif digest(cur) == digest(content):
            action = "same"
        elif recorded and digest(cur) != recorded and not force:
            action = "kept"  # 사용자가 생성 구역을 직접 고쳤다
        else:
            action = "update"
        out.append((rel, name, where, content, action))
    return out


def apply(ctx, steps):
    manifest = hio.load_json(ctx.p(MANIFEST_REL), {}) or {}
    files = manifest.setdefault("files", {})
    for rel, name, where, content, action in steps:
        if action in ("create", "update"):
            path = ctx.p(rel)
            text = hio.read_text(path) if path.exists() else ""
            hio.write_text(path, put_block(text, name, content, where))
            files.setdefault(rel, {})[name] = digest(content)
        elif action == "same":
            files.setdefault(rel, {})[name] = digest(content)
    from .. import __version__
    manifest["version"] = __version__
    hio.save_json(ctx.p(MANIFEST_REL), manifest)


LABEL = {"create": {"ko": "만듦", "en": "created"}, "update": {"ko": "고침", "en": "updated"},
         "same": {"ko": "그대로", "en": "unchanged"},
         "kept": {"ko": "직접 고친 구역이라 두었음(--force로 덮어씀)", "en": "kept: edited by hand (use --force)"}}


def run(args, ctx):
    db = RuleDB.load(ctx.p(ctx.get("rules.db")), ctx.lang)
    steps = plan(ctx, db, args.force)
    for rel, name, _w, _c, action in steps:
        print(f"  {rel} [{name}]: {tr(LABEL[action], ctx.lang)}")
    if not args.dry_run:
        apply(ctx, steps)
    return 0
