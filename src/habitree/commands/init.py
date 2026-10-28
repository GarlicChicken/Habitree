"""init: 프로젝트에 Habitree 뼈대를 깐다. 다시 실행하면 새 꾸러미 규칙만 더하는 업그레이드가 된다.
/ Install the Habitree skeleton. Running it again upgrades: only new pack rules are added.

만드는 것(없을 때만): .habitree/config.json, .habitree/rules.json(+RULES.md), AGENTS.md·CLAUDE.md 생성 구역,
README 지도(없으면 새로, 있으면 지도 절만 더함), LOG.md, .gitignore의 .habitree/state/.
--hooks: 플러그인 없이 쓸 때 프로젝트 .claude/settings.json에 훅을 더한다(사용자 전역 설정은 건드리지 않음).
사람이 쓴 내용은 지우지 않는다.
"""
import shutil

from ..core import io as hio
from ..core.config import CONFIG_REL, Context
from ..core.i18n import LANGS, tr
from ..core.markdown import links
from ..core.paths import top_dirs
from ..core import packs as _packs
from ..core.ruledb import RuleDB, available_packs, load_pack
from ..core.timeutil import local_date
from ..guard import install as hooks_install
from . import export

SUMMARY = {"ko": "프로젝트에 Habitree 뼈대 깔기(다시 실행하면 업그레이드)",
           "en": "Install the Habitree skeleton (run again to upgrade)"}

DEFAULT_PACKS = list(_packs.INSTALLED)  # 나머지 꾸러미(work, task)는 패키지에서 바로 읽는다

README_NEW = """# {name}

{{한 줄로 이 프로젝트가 하는 일을 쓰세요.}}
{{Describe in one line what this project does.}}

- 마지막 갱신 · Last updated: {date}

{map}

## 무엇이 어디에 · Where things are

| 찾는 것 · Looking for | 위치 · Location |
|---|---|
| AI 작업 지침 · Agent instructions | [AGENTS.md](AGENTS.md) |
| 규칙 · Rules | [{doc}]({doc}) |
| 변경 기록과 손볼 것 · Change log and to-do | [{log}]({log}) |
"""

MAP_SECTION = """## 지도 · Map

| 폴더 · Folder | 하는 일 · Purpose |
|---|---|
{rows}
"""

LOG_NEW = """# 변경 기록 · Change log

무엇이 언제 바뀌었는지와 다음에 손볼 것을 적는다. 새 기록을 위에 쓴다.
What changed and when, and what to fix next. Newest first.

## 손볼 것 · To fix

작업하다 발견했지만 그 자리에서 고치지 못한 것. / Found while working but not fixed yet.

## 기록 · Log

### {date}

- Habitree를 설치했다(`habitree init`). / Installed Habitree (`habitree init`).
"""


def add_arguments(p):
    p.add_argument("--lang", dest="init_lang", choices=LANGS, help="AI 지침 언어 / language for agent files")
    p.add_argument("--packs", nargs="+", help=f"넣을 규칙 꾸러미(기본: {' '.join(DEFAULT_PACKS)})")
    p.add_argument("--no-readme", action="store_true", help="README를 만들거나 고치지 않음")
    p.add_argument("--force", action="store_true", help="직접 고친 생성 구역·꾸러미 규칙도 새것으로")
    p.add_argument("--dry-run", action="store_true", help="쓰지 않고 할 일만 보기")
    p.add_argument("--hooks", action="store_true",
                   help="프로젝트 .claude/settings.json에 Claude Code 훅 연결(플러그인 없이 쓸 때) / "
                        "wire Claude Code hooks into the project settings (without the plugin)")


def _say(ctx, ko, en):
    print("  " + (ko if ctx.lang == "ko" else en))


def md_href(path):
    """Markdown 링크 주소: 공백·괄호만 바꾼다(한글은 그대로). / Escape spaces and parens only."""
    return path.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def map_rows(root):
    rows = [f"| [{d}/]({md_href(d)}/) | |" for d in top_dirs(root)]
    return "\n".join(rows) if rows else "| | |"


def run(args, ctx):
    root = ctx.root
    dry = args.dry_run
    lang = args.init_lang or ctx.lang
    ctx = Context(root, ctx.cfg, lang)
    print(("Habitree 설치: " if lang == "ko" else "Installing Habitree: ") + str(root))

    # 1. 설정
    cfg_path = root / CONFIG_REL
    if not cfg_path.exists():
        cfg = {"version": 1, "lang": lang, "verify": {}}
        if not dry:
            hio.save_json(cfg_path, cfg)
        _say(ctx, f"만듦: {CONFIG_REL}", f"created: {CONFIG_REL}")
    ctx = Context.load(root, lang) if not dry else ctx

    # 2. 규칙 DB와 꾸러미
    db_path = ctx.p(ctx.get("rules.db"))
    if db_path.exists():
        db = RuleDB.load(db_path, lang)
        fresh = False
    else:
        db = RuleDB({"version": 2, "about": {"ko": "이 프로젝트의 규칙", "en": "Rules of this project"},
                     "scopes": {}, "aspects": {}, "contexts": {}, "rules": []}, db_path).add_live_packs()
        fresh = True
    packs = args.packs or sorted(set(DEFAULT_PACKS) | set(db.data.get("packs", {})))
    unknown = [p for p in packs if p not in available_packs()]
    if unknown:
        raise SystemExit(f"없는 꾸러미 / unknown pack: {', '.join(unknown)} (있는 것 / available: {', '.join(available_packs())})")
    for name in packs:
        rep = db.merge_pack(load_pack(name), force=args.force)
        if rep["added"] or rep["updated"] or rep["kept"]:
            _say(ctx, f"꾸러미 {name}: 더함 {len(rep['added'])} · 고침 {len(rep['updated'])} · 둠 {len(rep['kept'])}",
                 f"pack {name}: added {len(rep['added'])} · updated {len(rep['updated'])} · kept {len(rep['kept'])}")
    if not dry:
        doc = ctx.get("rules.doc")
        db.save(ctx.p(doc) if doc else None, lang)
    if fresh:
        _say(ctx, f"만듦: {ctx.get('rules.db')}, {ctx.get('rules.doc')}",
             f"created: {ctx.get('rules.db')}, {ctx.get('rules.doc')}")

    # 3. README 지도
    map_rel = ctx.get("docs.map")
    readme = ctx.p(map_rel)
    if not args.no_readme:
        section = MAP_SECTION.format(rows=map_rows(root)).strip()
        if not readme.exists():
            text = README_NEW.format(name=root.name, date=local_date(), map=section, doc=ctx.get("rules.doc"),
                                     log=ctx.get("docs.log"))
            if not dry:
                hio.write_text(readme, text)
            _say(ctx, f"만듦: {map_rel} (지도 초안. '하는 일' 칸을 채우세요)",
                 f"created: {map_rel} (draft map; fill in the Purpose column)")
        else:
            text = hio.read_text(readme)
            targets = {tgt.split("#")[0].rstrip("/") for _, tgt in links(text)}
            dirs = top_dirs(root)
            if dirs and not any(d in targets for d in dirs):
                if not dry:
                    hio.write_text(readme, text.rstrip("\n") + "\n\n" + section + "\n")
                _say(ctx, f"고침: {map_rel}에 지도 절을 더함('하는 일' 칸을 채우세요)",
                     f"updated: added a Map section to {map_rel} (fill in the Purpose column)")

    # 4. 변경 기록
    log = ctx.p(ctx.get("docs.log"))
    if not log.exists():
        if not dry:
            hio.write_text(log, LOG_NEW.format(date=local_date()))
        _say(ctx, f"만듦: {ctx.get('docs.log')}", f"created: {ctx.get('docs.log')}")

    # 5. .gitignore
    gi = root / ".gitignore"
    gtext = hio.read_text(gi) if gi.exists() else ""
    if ".habitree/state" not in gtext:
        if not dry:
            hio.write_text(gi, gtext.rstrip("\n") + ("\n\n" if gtext.strip() else "") +
                           "# Habitree 세션 상태(커밋하지 않음) / Habitree session state (not committed)\n.habitree/state/\n")
        _say(ctx, "고침: .gitignore에 .habitree/state/", "updated: .gitignore += .habitree/state/")

    # 6. AI 지침 파일
    steps = export.plan(ctx, db, args.force)
    for rel, name, _w, _c, action in steps:
        print(f"  {rel} [{name}]: {tr(export.LABEL[action], lang)}")
    if not dry:
        export.apply(ctx, steps)

    # 7. Claude Code 훅(선택). 사용자 전역 설정은 건드리지 않는다.
    if args.hooks:
        added = hooks_install.merge_settings(root, dry)
        rel = hooks_install.SETTINGS_REL
        if added:
            _say(ctx, f"고침: {rel}에 훅 {len(added)}개 ({', '.join(added)})",
                 f"updated: {rel} += {len(added)} hooks ({', '.join(added)})")
        else:
            _say(ctx, f"그대로: {rel}에 Habitree 훅이 이미 있음", f"unchanged: {rel} already has the Habitree hooks")
        if not shutil.which(hooks_install.COMMAND):
            _say(ctx, "주의: habitree 명령이 PATH에 없어 훅이 돌지 않을 수 있습니다. "
                      "`uv tool install git+https://github.com/GarlicChicken/habitree`로 설치하세요.",
                 "Note: habitree is not on PATH, so the hooks may not run. "
                 "Install it with `uv tool install git+https://github.com/GarlicChicken/habitree`.")

    print("\n" + ("다음: README 지도의 '하는 일' 칸을 채우고, 설정 verify에 테스트·빌드 명령을 등록한 뒤 `habitree check`."
                  if lang == "ko" else
                  "Next: fill in the map's Purpose column, register test/build commands under verify in the config, "
                  "then run `habitree check`."))
    return 0
