"""export: 규칙 DB에서 AI 도구가 읽는 지침 파일을 만든다. / Generate agent instruction files from the rule DB.

- AGENTS.md: 모든 도구 공용(Codex·Cursor·Copilot·Gemini 등). 생성 구역만 고친다.
- CLAUDE.md: 맨 위에 `@AGENTS.md` 한 줄과 Claude 전용 안내만.
- 생성 구역의 해시를 .habitree/manifest.json에 남겨, 사용자가 구역을 직접 고쳤으면 덮어쓰지 않는다(--force로 덮음).
- AI가 읽는 파일이므로 설정 언어 한 벌만 쓴다(토큰 절약).
"""
from ..core import io as hio
from ..core.i18n import tr
from ..core.markdown import digest, get_block, put_block
from ..core.ruledb import RuleDB

SUMMARY = {"ko": "규칙 DB에서 AGENTS.md·CLAUDE.md 생성 구역을 다시 만들기",
           "en": "Regenerate the managed blocks in AGENTS.md and CLAUDE.md from the rule DB"}

MANIFEST_REL = ".habitree/manifest.json"
TARGETS = {"agents": ("AGENTS.md", "habitree", "end"), "claude": ("CLAUDE.md", "habitree-claude", "start")}

CYCLE = {
    "ko": """## Habitree 작업 순환

이 프로젝트는 Habitree로 작업 습관을 관리한다. 모든 작업은 이 순서를 따른다.

1. 찾기: [지도]({map})와 `habitree rules brief <범위>`로 관련 문서·도구·규칙을 먼저 본다.
2. 있으면 쓰기: 있는 것을 쓰고, 낡았거나 틀린 곳은 그 자리에서 고친다.
3. 없으면 만들기: 되풀이할 일이면 도구·모듈·양식으로 만든다.
4. 기록하기: 바꾼 것을 폴더 README, 지도, [변경 기록]({log})에 함께 반영한다.
5. 고치기: 지금 못 고친 문제는 변경 기록의 '손볼 것'에 적는다.
6. 점검하기: 끝내기 전에 `habitree check`와 검증 명령을 실행하고 나온 문제를 고친다.

사용자 피드백은 고치는 것과 동시에 규칙으로 남긴다. 같은 뜻 규칙이 있으면 `habitree rules hit <id> --feedback "…"`, 없으면 `habitree rules add --scope … --aspect … --rule "…" --why "…" --feedback "…"`. 전체 규칙: [{doc}]({doc}).""",
    "en": """## Habitree work cycle

This project manages its working habits with Habitree. Every task follows this order.

1. Find: check the [map]({map}) and `habitree rules brief <scope>` for related docs, tools and rules first.
2. Reuse: use what exists; fix stale or wrong parts on the spot.
3. Build: if the work will repeat, make it a tool, module or template.
4. Record: reflect changes in the folder README, the map and the [change log]({log}).
5. Fix later: write problems you cannot fix now under 'To fix' in the change log.
6. Check: before finishing, run `habitree check` and the verify commands, and fix what they report.

Record user feedback as a rule while fixing it: `habitree rules hit <id> --feedback "…"` when a rule with the same meaning exists, otherwise `habitree rules add --scope … --aspect … --rule "…" --why "…" --feedback "…"`. All rules: [{doc}]({doc}).""",
}
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
    text = CYCLE[lang].format(map=ctx.get("docs.map"), log=ctx.get("docs.log"), doc=ctx.get("rules.doc"))
    brief = db.brief(["global"], must_only=True, budget=ctx.get("export.brief_budget", 3000), lang=lang,
                     compact=True, skip_scopes=("work/cycle",))
    body = brief.split("\n", 1)[1].strip() if "\n" in brief else ""
    return text + ("\n\n" + MUST_HEAD[lang] + "\n" + body if body else "")


def claude_block(ctx, db):
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
