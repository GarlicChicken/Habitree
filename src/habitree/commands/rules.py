"""rules: 피드백을 규칙으로 쌓고, 필요한 규칙만 뽑는다. / Grow feedback into rules; pull only what you need.

  habitree rules                                  범위·관점·상황 목록과 규칙 수
  habitree rules brief global                     작업 전에 읽을 규칙 (상위·하위 범위 포함, 글자 예산 안)
  habitree rules brief work --aspect process --when task:implement --must
  habitree rules add --scope work --aspect process --rule "…" --why "…" --feedback "…"
  habitree rules hit <id> --feedback "…"          같은 지적이 또 나옴 (권장 → 필수, 감지 규칙은 '맞았다')
  habitree rules miss <id> --feedback "…"         규칙·경고가 틀렸거나 잔소리였음 (감지 기준 완화)
  habitree rules edit <id> --rule "…" --feedback "…"
  habitree rules demote|pause|resume|retire <id> --why "…"
  habitree rules similar "글"                     같은 뜻일 수 있는 규칙 찾기
  habitree rules show <id>                        규칙 하나 전체 보기
  habitree rules doc                              RULES.md 다시 만들기
"""
import json

from ..core import HabitreeError
from ..core.i18n import t, tr
from ..core.ruledb import LEVEL_TEXT, LEVELS, RuleDB, rule_text, vote_stats

SUMMARY = {"ko": "규칙 DB: 피드백을 범위·관점·상황별 규칙으로 쌓고, 작업 전에 필요한 규칙만 뽑기",
           "en": "Rule DB: grow feedback into scoped rules and pull only the rules a task needs"}


def add_arguments(p):
    p.add_argument("--db", help="규칙 DB 경로(기본: 설정의 rules.db) / rule DB path")
    p.add_argument("--doc", help="함께 다시 만들 RULES.md 경로 / doc path to regenerate")
    sub = p.add_subparsers(dest="action", metavar="<action>")
    b = sub.add_parser("brief", help="범위의 규칙만 짧게 / short rules for scopes")
    b.add_argument("scopes", nargs="+")
    b.add_argument("--aspect", nargs="+")
    b.add_argument("--when", nargs="+")
    b.add_argument("--must", action="store_true", help="필수만 / must only")
    b.add_argument("--json", action="store_true")
    b.add_argument("--budget", type=int, help="글자 예산(0이면 제한 없음) / char budget, 0 = no limit")
    a = sub.add_parser("add", help="새 규칙 / add a rule")
    a.add_argument("--scope", required=True)
    a.add_argument("--aspect", required=True)
    a.add_argument("--when", nargs="*", default=[])
    a.add_argument("--rule", required=True)
    a.add_argument("--why", required=True)
    a.add_argument("--feedback", required=True)
    a.add_argument("--ref", default="")
    a.add_argument("--level", choices=LEVELS, default="should")
    a.add_argument("--check", help="점검 방법 / how to check")
    a.add_argument("--auto", action="store_true", help="코드·도구가 자동으로 막는 규칙 / enforced automatically")
    a.add_argument("--id")
    a.add_argument("--force", action="store_true", help="비슷한 규칙이 있어도 더함 / add despite similar rules")
    for name, helptext in (("hit", "같은 지적이 또 나옴 / same feedback again"),
                           ("miss", "규칙·경고가 틀렸음 / the rule or warning was wrong")):
        h = sub.add_parser(name, help=helptext)
        h.add_argument("id")
        h.add_argument("--feedback", required=True)
        h.add_argument("--ref", default="")
    e = sub.add_parser("edit", help="규칙 고치기(이력이 남음) / edit with history")
    e.add_argument("id")
    for k in ("rule", "why", "aspect", "check"):
        e.add_argument(f"--{k}")
    e.add_argument("--level", choices=LEVELS)
    e.add_argument("--when", nargs="*")
    e.add_argument("--auto", action="store_true")
    e.add_argument("--feedback", required=True)
    e.add_argument("--ref", default="")
    for name in ("demote", "pause", "resume", "retire"):
        s = sub.add_parser(name, help={"demote": "필수 → 권장 / must → should", "pause": "잠시 끄기 / pause",
                                       "resume": "다시 켜기 / resume", "retire": "폐기 / retire"}[name])
        s.add_argument("id")
        s.add_argument("--why", required=True)
    s = sub.add_parser("similar", help="같은 뜻일 수 있는 규칙 / possibly duplicate rules")
    s.add_argument("text")
    s.add_argument("--scope")
    s = sub.add_parser("show", help="규칙 하나 전체 / show one rule")
    s.add_argument("id")
    sub.add_parser("doc", help="RULES.md 다시 만들기 / regenerate RULES.md")


def _paths(args, ctx):
    """(규칙 DB, RULES.md 또는 None). 문서 경로가 비어 있으면 문서를 만들지 않는다."""
    if args.db:
        db = args.db if _abs(args.db) else ctx.root / args.db
        return db, (ctx.root / args.doc if args.doc else None)
    doc = args.doc or ctx.get("rules.doc")
    return ctx.p(ctx.get("rules.db")), (ctx.p(doc) if doc else None)


def _abs(p):
    import os
    return os.path.isabs(p)


def overview(db, lang):
    rs = db.active()
    ko = lang == "ko"
    print(f"{'규칙 DB' if ko else 'Rule DB'}: {db.path}\n\n{'범위' if ko else 'Scopes'}")
    for s, depth in db.order():
        n = [r for r in rs if r["scope"] == s]
        fb = sum(len(r.get("feedback", [])) for r in n)
        print(f"  {'  ' * depth}{s:<{26 - 2 * depth}} {len(n):>3} {'규칙' if ko else 'rules'}  "
              f"{fb:>3} {'피드백' if ko else 'fb'}  {tr(db.scopes[s], lang)}")
    print(f"\n{'관점' if ko else 'Aspects'}")
    for a, desc in db.data["aspects"].items():
        print(f"  {a:<12} {sum(1 for r in rs if r['aspect'] == a):>3}  {tr(desc, lang)}")
    if db.data["contexts"]:
        print(f"\n{'상황 태그' if ko else 'Contexts'}")
        for c, desc in db.data["contexts"].items():
            print(f"  {c:<18} {sum(1 for r in rs if c in r.get('when', [])):>3}  {tr(desc, lang)}")
    off = [r for r in db.rules if r.get("status", "active") != "active"]
    if off:
        print(f"\n{'쉬거나 폐기한 규칙' if ko else 'Paused or retired'}: {len(off)}")
    print("\n" + ("작업 전: habitree rules brief global  (범위·--aspect·--when·--must로 좁힘)" if ko
                  else "Before work: habitree rules brief global  (narrow with scopes, --aspect, --when, --must)"))


def run(args, ctx):
    lang = ctx.lang
    db_path, doc_path = _paths(args, ctx)
    db = RuleDB.load(db_path, lang)
    act = args.action

    def save():
        db.save(doc_path, lang)

    if act is None:
        overview(db, lang)
    elif act == "brief":
        bad = db.unknown_names(args.scopes, args.aspect, args.when)
        if bad:
            raise HabitreeError(t("unknown_names", lang, names=", ".join(bad)))
        if args.json:
            print(json.dumps(db.brief_json(args.scopes, args.aspect, args.when, args.must, lang),
                             ensure_ascii=False, indent=1))
        else:
            budget = ctx.get("rules.brief_budget", 0) if args.budget is None else args.budget
            print(db.brief(args.scopes, args.aspect, args.when, args.must, budget, lang))
    elif act == "add":
        bad = db.unknown_names([args.scope], [args.aspect], args.when)
        if bad:
            raise HabitreeError(t("unknown_names", lang, names=", ".join(bad)))
        sims = db.similar(args.rule, args.scope)
        if sims and not args.force:
            lines = [t("similar_found", lang)]
            lines += [f"  {score:.2f}  {r['id']}  {rule_text(r, 'rule', lang)}" for score, r in sims[:5]]
            raise HabitreeError("\n".join(lines))
        r = db.add(args.scope, args.aspect, args.rule, args.why, args.feedback, args.ref, args.level, args.when,
                   args.check, args.auto, args.id)
        save()
        print(("규칙을 더했습니다" if lang == "ko" else "Added rule") +
              f": {r['id']} ({args.scope} · {args.aspect} · {tr(LEVEL_TEXT[args.level], lang)})")
    elif act == "hit":
        r, notes = db.hit(args.id, args.feedback, args.ref, lang)
        save()
        print(("기록했습니다" if lang == "ko" else "Recorded") +
              f": {r['id']} ({'지적' if lang == 'ko' else 'feedback'} {len(r['feedback'])}, "
              f"{tr(LEVEL_TEXT[r['level']], lang)}{', ' + ', '.join(notes) if notes else ''})")
    elif act == "miss":
        r, notes = db.miss(args.id, args.feedback, args.ref, lang)
        save()
        st = vote_stats(r)
        print(("기록했습니다" if lang == "ko" else "Recorded") + f": {r['id']} (miss {st['miss']}/{st['total']})")
        for n in notes:
            if n == "suggest:pause":
                print("  " + ("최근 반응의 25% 넘게 '틀렸다'입니다. 끄려면: habitree rules pause " if lang == "ko"
                              else "Over 25% of recent votes say 'wrong'. To pause: habitree rules pause ")
                      + f"{r['id']} --why \"…\"")
            elif n == "suggest:edit-or-retire":
                print("  " + ("규칙이 맞지 않으면 rules edit로 고치거나 rules retire로 폐기하세요." if lang == "ko"
                              else "If the rule no longer fits, fix it with rules edit or retire it."))
            else:
                print("  " + n)
    elif act == "edit":
        r = db.find(args.id, lang)
        changes = []
        for key in ("rule", "why", "level", "aspect", "when"):
            v = getattr(args, key)
            if v is not None and v != r.get(key):
                changes.append(f"{key}: {tr(r.get(key), lang)} → {v}")
                r[key] = v
        if args.check:
            changes.append(f"check: {tr(r['check'].get('how'), lang)} → {args.check}")
            r["check"]["how"] = args.check
        if args.auto and r["check"].get("type") != "auto":
            changes.append("check.type: review → auto")
            r["check"]["type"] = "auto"
        if not changes:
            raise HabitreeError(t("nothing_changed", lang))
        db.log_change(r, "; ".join(changes))
        r.setdefault("feedback", []).append({"date": r["history"][-1]["date"], "note": args.feedback, "ref": args.ref})
        save()
        print(("고쳤습니다" if lang == "ko" else "Edited") + f": {r['id']} ({len(changes)})")
    elif act in ("demote", "pause", "resume", "retire"):
        if act == "demote":
            r = db.demote(args.id, args.why, lang)
        else:
            r = db.set_status(args.id, {"pause": "paused", "resume": "active", "retire": "retired"}[act], args.why, lang)
        save()
        print(f"{act}: {r['id']}")
    elif act == "similar":
        sims = db.similar(args.text, args.scope, threshold=0.2)
        if not sims:
            print("비슷한 규칙이 없습니다." if lang == "ko" else "No similar rules.")
        for score, r in sims[:10]:
            print(f"{score:.2f}  {r['id']}  {rule_text(r, 'rule', lang)}")
    elif act == "show":
        print(json.dumps(db.find(args.id, lang), ensure_ascii=False, indent=2))
    elif act == "doc":
        save()
        print(("다시 만들었습니다" if lang == "ko" else "Regenerated") + f": {doc_path}")
    return 0
