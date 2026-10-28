"""규칙 DB: 피드백이 규칙으로 자라는 곳. / The rule DB where feedback grows into rules.

규칙은 세 축으로 찾는다.
  범위(scope)  무엇에 대한 규칙인가. 'work/loop'처럼 계층이고 상위 범위의 규칙을 물려받는다.
  관점(aspect) 어떤 종류의 규칙인가(절차, 구조, 품질 …).
  상황(when)   특정 상황에서만 맞는 규칙의 조건 태그. 비어 있으면 늘 적용된다.

규칙 사다리: 말로 한 피드백 → 권장(should) → 필수(must) → 자동 검사(check.auto) → 코드에서 막기.
- 사람이 말한 피드백은 빠르게 오른다: 같은 지적이 또 나오면(hit) 권장이 필수가 된다.
- 감지 규칙(detect가 있는 규칙)은 사용자 반응(votes)으로 천천히 조정한다(Google Tricorder 방식):
  최근 반응 중 '틀렸다' 비율이 10% 이상이면 기준값을 한 단계 완화, 25%를 넘으면 끄기를 제안한다.
  멈춤(stop) 등급으로는 자동으로 올리지 않는다.
"""
import copy
import json
import re
from pathlib import Path

from . import HabitreeError
from . import io as hio
from . import packs as _packs
from .i18n import t, tr
from .timeutil import local_date, now_iso

LEVELS = ("must", "should")
LEVEL_TEXT = {"must": {"ko": "필수", "en": "must"}, "should": {"ko": "권장", "en": "should"}}
CHECK_TEXT = {"auto": {"ko": "자동", "en": "auto"}, "review": {"ko": "눈으로", "en": "review"}}
SEVERITIES = ("info", "warn", "stop")
VOTE_WINDOW = 20
PROBATION = 0.10
PAUSE_SUGGEST = 0.25
MIN_VOTES = 5
SIMILAR_THRESHOLD = 0.45


def rule_text(r, key="rule", lang="ko"):
    return tr(r.get(key, ""), lang)


def all_text(value):
    """두 언어를 모두 이어 붙인 글(비슷함 비교용). / All languages joined."""
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values())
    return str(value or "")


class RuleDB:
    def __init__(self, data, path=None):
        self.data = data
        self.path = Path(path) if path else None
        self._file_keys = None   # 파일에 원래 있던 범위·관점·상황 이름(살아 있는 꾸러미를 얹은 뒤에만)
        self._virtual = set()    # 메모리에만 얹은(아직 손대지 않은) 꾸러미 규칙 id
        self.data.setdefault("scopes", {"global": {"ko": "모든 작업", "en": "All work"}})
        self.data.setdefault("parents", {})
        self.data.setdefault("aspects", {})
        self.data.setdefault("contexts", {})
        self.data.setdefault("rules", [])

    # ── 불러오기·저장 ──
    @classmethod
    def load(cls, path, lang="ko", live=True):
        """규칙 DB를 읽는다. live면 살아 있는 꾸러미(work, task) 규칙을 메모리에만 얹는다.
        / Load the DB; with live=True, live pack rules are added in memory only."""
        path = Path(path)
        if not path.is_file():
            raise HabitreeError(t("no_db", lang, path=path))
        try:
            data = hio.load_json(path)
        except json.JSONDecodeError as e:
            raise HabitreeError(f"규칙 DB JSON이 깨졌습니다 / Broken JSON: {path}: {e}")
        db = cls(data, path)
        if live:
            db.add_live_packs()
        return db

    def add_live_packs(self, names=_packs.LIVE):
        """프로젝트 DB에 옮겨 적지 않은 꾸러미 규칙을 메모리에만 얹는다(저장할 때 손대지 않은 것은 빠진다).
        / Overlay live pack rules in memory; untouched ones are left out on save."""
        if self._file_keys is None:
            self._file_keys = {k: set(self.data[k]) for k in ("scopes", "aspects", "contexts", "parents")}
        copied = self.data.get("packs") or {}
        have = {r["id"] for r in self.rules}
        for name in names:
            if name in copied:
                continue
            try:
                pack = _packs.load_pack(name)
            except (OSError, ValueError):
                continue
            for key in ("scopes", "aspects", "contexts", "parents"):
                for k, v in pack.get(key, {}).items():
                    self.data[key].setdefault(k, v)
            for pr in pack["rules"]:
                if pr["id"] in have:
                    continue
                r = _pack_copy(pr, pack)
                self.rules.append(r)
                self._virtual.add(r["id"])
        return self

    def untouched_virtual(self, r):
        """메모리에만 얹었고 아직 아무도 손대지 않은 규칙인가. / Overlaid and still untouched?"""
        return (r["id"] in self._virtual and pack_rule_hash(r) == r.get("origin_hash") and not r.get("feedback")
                and not r.get("votes") and not r.get("history") and r.get("status", "active") == "active")

    def persisted(self):
        return [r for r in self.rules if not self.untouched_virtual(r)]

    def file_data(self):
        """파일에 쓸 모습: 손대지 않은 살아 있는 꾸러미 규칙과, 그것들만 쓰던 범위·관점·상황은 뺀다.
        / What goes to disk: untouched live rules and names only they used are left out."""
        if self._file_keys is None:
            return self.data
        rules = self.persisted()
        used = {"scopes": set(), "aspects": set(), "contexts": set()}
        for r in rules:
            used["scopes"].update(self.chain(r["scope"]))
            used["aspects"].add(r["aspect"])
            used["contexts"].update(r.get("when", []))
        out = dict(self.data)
        out["rules"] = rules
        for key in ("scopes", "aspects", "contexts"):
            keep = self._file_keys[key] | used[key]
            out[key] = {k: v for k, v in self.data[key].items() if k in keep}
        keep = self._file_keys["parents"] | used["scopes"]
        out["parents"] = {k: v for k, v in self.data["parents"].items() if k in keep}
        return out

    @property
    def rules(self):
        return self.data["rules"]

    @property
    def scopes(self):
        return self.data["scopes"]

    def save(self, doc_path=None, lang="ko"):
        problems = self.validate()
        if problems:
            raise HabitreeError(t("db_invalid", lang) + "\n  " + "\n  ".join(problems))
        hio.save_json(self.path, self.file_data())
        if doc_path:
            hio.write_text(doc_path, self.render_md(Path(doc_path).parent, self.path, lang))

    # ── 범위 트리 ──
    def parent(self, scope):
        if scope == "global":
            return None
        if "/" in scope:
            return scope.rsplit("/", 1)[0]
        return self.data["parents"].get(scope, "global")

    def chain(self, scope):
        out = []
        while scope:
            out.append(scope)
            scope = self.parent(scope)
        return out

    def order(self):
        """(범위, 깊이) 트리 순서. / Scopes in tree order."""
        children = {}
        for s in self.scopes:
            children.setdefault(self.parent(s), []).append(s)
        out, seen = [], set()

        def walk(s, depth):
            if s in seen:
                return
            seen.add(s)
            out.append((s, depth))
            for c in children.get(s, []):
                walk(c, depth + 1)
        walk("global", 0)
        for s in self.scopes:  # 고아 범위도 빠뜨리지 않는다
            walk(s, 0)
        return out

    def active(self):
        return [r for r in self.rules if r.get("status", "active") == "active"]

    def find(self, rid, lang="ko"):
        for r in self.rules:
            if r["id"] == rid:
                return r
        raise HabitreeError(t("unknown_rule", lang, id=rid))

    def rules_for(self, scopes, aspects=None, when=None):
        """범위들의 규칙: 상위 범위(물려받는 규칙)와 하위 범위까지.
        when을 주면 상황 조건이 없는 규칙 + 그 상황 규칙만, 안 주면 상황 규칙도 모두."""
        order = [s for s, _ in self.order()]
        wanted = set()
        for s in scopes:
            wanted.update(self.chain(s))
            wanted.update(o for o in order if s in self.chain(o))
        out = []
        for s in order:
            if s not in wanted:
                continue
            for r in self.active():
                if r["scope"] != s or (aspects and r["aspect"] not in aspects):
                    continue
                if when is not None and r.get("when") and not set(r["when"]) & set(when):
                    continue
                out.append(r)
        return out

    def unknown_names(self, scopes=(), aspects=(), when=()):
        bad = [s for s in scopes if s not in self.scopes]
        bad += [a for a in aspects or () if a not in self.data["aspects"]]
        bad += [w for w in when or () if w not in self.data["contexts"]]
        return bad

    # ── 검사 ──
    def validate(self):
        from .schema import load_schema, validate  # 검사할 때만 / only when validating
        problems = validate(self.data, load_schema("rules.schema.json"))
        ids = set()
        for s in self.scopes:
            p = self.parent(s)
            if p is not None and p not in self.scopes:
                problems.append(f"범위의 상위가 없음 / missing parent scope: {s} → {p}")
        for r in self.rules:
            rid = r.get("id", "?")
            if rid in ids:
                problems.append(f"규칙 id 중복 / duplicate id: {rid}")
            ids.add(rid)
            if r.get("scope") not in self.scopes:
                problems.append(f"없는 범위 / unknown scope: {rid} → {r.get('scope')}")
            if r.get("aspect") not in self.data["aspects"]:
                problems.append(f"없는 관점 / unknown aspect: {rid} → {r.get('aspect')}")
            for w in r.get("when", []):
                if w not in self.data["contexts"]:
                    problems.append(f"없는 상황 태그 / unknown context: {rid} → {w}")
        return problems

    # ── 찾기 ──
    def similar(self, text, scope=None, exclude=None, threshold=SIMILAR_THRESHOLD):
        """같은 뜻일 수 있는 규칙(점수 높은 순). / Possibly duplicate rules."""
        out = []
        for r in self.active():
            if r["id"] == exclude:
                continue
            score = max_similarity(text, r.get("rule"))
            if scope and r["scope"] in self.chain(scope):
                score += 0.05
            if score >= threshold:
                out.append((round(min(score, 1.0), 2), r))
        return sorted(out, key=lambda x: -x[0])

    def duplicate_pairs(self, threshold=0.6):
        rs = self.active()
        pairs = []
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                s = max(max_similarity(v, b.get("rule")) for v in _variants(a.get("rule")))
                if s >= threshold:
                    pairs.append((round(s, 2), a["id"], b["id"]))
        return pairs

    # ── 바꾸기 ──
    def make_id(self, scope, text):
        base = scope.replace("/", ".")
        text = all_text(text)
        ascii_words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]+", text)]
        if len(ascii_words) >= 2:
            words = ascii_words[:3]
        else:
            words = [w for w in re.findall(r"[\w]+", text) if not w.isdigit()][:3]
        slug = "-".join(words) or "rule"
        ids = {r["id"] for r in self.rules}
        rid, n = f"{base}.{slug}", 2
        while rid in ids:
            rid, n = f"{base}.{slug}-{n}", n + 1
        return rid

    def add(self, scope, aspect, rule, why, feedback, ref="", level="should", when=None, check_how=None,
            auto=False, rid=None):
        r = {
            "id": rid or self.make_id(scope, rule), "scope": scope, "aspect": aspect, "when": list(when or []),
            "level": level, "rule": rule, "why": why,
            "check": {"type": "auto" if auto else "review", "how": check_how or "결과물에서 눈으로 확인한다."},
            "feedback": [{"date": local_date(), "note": feedback, "ref": ref}],
            "history": [], "status": "active",
        }
        self.rules.append(r)
        return r

    def log_change(self, r, change):
        r.setdefault("history", []).append({"date": local_date(), "change": change})

    def hit(self, rid, feedback, ref="", lang="ko"):
        """같은 지적이 또 나옴. 사람 피드백은 권장 → 필수, 감지 규칙은 '맞았다' 반응. / Same feedback again."""
        r = self.find(rid, lang)
        r.setdefault("feedback", []).append({"date": local_date(), "note": feedback, "ref": ref})
        notes = []
        if r.get("detect"):
            r.setdefault("votes", []).append({"at": now_iso(), "kind": "useful", "note": feedback})
            stats = vote_stats(r)
            sev = r["detect"].get("severity", "info")
            if sev == "info" and stats["useful"] >= 2 and stats["miss"] == 0:
                r["detect"]["severity"] = "warn"
                self.log_change(r, "detect.severity: info → warn (맞았다는 반응 2회 / 2 useful votes)")
                notes.append("severity info → warn")
        elif r.get("level") == "should":
            r["level"] = "must"
            self.log_change(r, "level: should → must (같은 지적 반복 / repeated feedback)")
            notes.append("should → must")
        return r, notes

    def miss(self, rid, feedback, ref="", lang="ko"):
        """이 규칙(경고)이 틀렸거나 잔소리였다. / The rule or warning was wrong or noisy."""
        r = self.find(rid, lang)
        r.setdefault("feedback", []).append({"date": local_date(), "note": f"(miss) {feedback}", "ref": ref})
        notes = []
        if not r.get("detect"):
            notes.append("suggest:edit-or-retire")
            return r, notes
        r.setdefault("votes", []).append({"at": now_iso(), "kind": "miss", "note": feedback})
        stats = vote_stats(r)
        if stats["total"] >= MIN_VOTES and stats["useless"] >= PROBATION:
            th = r["detect"].get("threshold")
            if isinstance(th, int):
                r["detect"]["threshold"] = th + 1
                if isinstance(r["detect"].get("stop_at"), int) and r["detect"]["stop_at"] <= th + 1:
                    r["detect"]["stop_at"] = th + 2
                self.log_change(r, f"detect.threshold: {th} → {th + 1} (쓸모없음 {stats['useless']:.0%} / "
                                   f"useless ratio, 보호관찰 / probation)")
                notes.append(f"threshold {th} → {th + 1}")
        if stats["total"] >= MIN_VOTES and stats["useless"] > PAUSE_SUGGEST:
            notes.append("suggest:pause")
        return r, notes

    def set_status(self, rid, status, why, lang="ko"):
        r = self.find(rid, lang)
        old = r.get("status", "active")
        if old == status:
            raise HabitreeError(t("nothing_changed", lang))
        r["status"] = status
        self.log_change(r, f"status: {old} → {status}: {why}")
        return r

    def demote(self, rid, why, lang="ko"):
        r = self.find(rid, lang)
        if r.get("level") != "must":
            raise HabitreeError(t("nothing_changed", lang))
        r["level"] = "should"
        self.log_change(r, f"level: must → should: {why}")
        return r

    # ── 묶음(pack): 기본 규칙 꾸러미 ──
    def merge_pack(self, pack, force=False):
        """꾸러미의 범위·관점·상황·규칙을 더한다. 사용자가 고친 규칙은 덮어쓰지 않는다.
        / Merge a bundled pack without clobbering user-edited rules."""
        name, version = pack["pack"], pack["version"]
        report = {"added": [], "updated": [], "kept": []}
        for key in ("scopes", "aspects", "contexts", "parents"):
            for k, v in pack.get(key, {}).items():
                self.data[key].setdefault(k, v)
        by_id = {r["id"]: r for r in self.rules}
        for pr in pack["rules"]:
            self._virtual.discard(pr["id"])  # 꾸러미를 옮겨 적으면 메모리 전용이 아니다
            new = copy.deepcopy(pr)
            new.setdefault("when", [])
            new.setdefault("feedback", [])
            new.setdefault("history", [])
            new.setdefault("status", "active")
            new["origin"] = f"pack:{name}@{version}"
            new["origin_hash"] = pack_rule_hash(pr)
            cur = by_id.get(pr["id"])
            if cur is None:
                self.rules.append(new)
                report["added"].append(pr["id"])
                continue
            if not str(cur.get("origin", "")).startswith(f"pack:{name}@"):
                report["kept"].append(pr["id"])
                continue
            if cur.get("origin_hash") == new["origin_hash"]:
                continue
            untouched = pack_rule_hash(cur) == cur.get("origin_hash")
            if untouched or force:
                for k in ("feedback", "history", "votes", "status"):
                    if cur.get(k):
                        new[k] = cur[k]
                cur.clear()
                cur.update(new)
                report["updated"].append(pr["id"])
            else:
                report["kept"].append(pr["id"])
        self.data.setdefault("packs", {})[name] = version
        return report

    # ── 문서 ──
    def render_md(self, doc_dir=None, db_path=None, lang="ko"):
        """RULES.md(사람이 읽는 규칙 문서). 설정 언어 한 벌로, 프로젝트 DB에 있는 규칙만 싣는다.
        같은 입력이면 늘 같은 결과. / Human-readable rule doc in one language, persisted rules only."""
        ko = lang == "ko"
        rules = [r for r in self.persisted() if r.get("status", "active") == "active"]
        dates = [f["date"] for r in rules for f in r.get("feedback", [])]
        link = "rules.json"
        if doc_dir and db_path:
            try:
                link = Path(db_path).resolve().relative_to(Path(doc_dir).resolve()).as_posix()
            except ValueError:
                link = Path(db_path).name
        L = ["# 규칙" if ko else "# Rules", "",
             (f"> [{Path(link).name}]({link})에서 만든 문서입니다. 고칠 때는 `habitree rules`를 쓰세요." if ko else
              f"> Generated from [{Path(link).name}]({link}). Use `habitree rules` to change it."), ""]
        fb = sum(len(r.get("feedback", [])) for r in rules)
        L.append(f"- 규칙 {len(rules)}개 · 피드백 {fb}건 · 마지막 피드백 {max(dates) if dates else '-'}" if ko else
                 f"- {len(rules)} rules · {fb} feedback entries · last feedback {max(dates) if dates else '-'}")
        live = sorted({r["origin"].split(":", 1)[1].split("@")[0] for r in self.rules
                       if self.untouched_virtual(r) and r.get("origin")})
        if live:
            L.append(("- 패키지에서 바로 읽는 꾸러미: " if ko else "- Packs read straight from the package: ")
                     + ", ".join(f"`{n}`" for n in live)
                     + (" (보기: `habitree rules brief <범위>`, 반응하거나 고친 규칙만 여기에 남습니다)" if ko else
                        " (see `habitree rules brief <scope>`; only rules you react to or edit are kept here)"))
        L.append("")
        aspect_order = list(self.data["aspects"])
        for s, _ in self.order():
            rs = [r for r in rules if r["scope"] == s]
            if not rs:
                continue
            L += [f"## `{s}` · {tr(self.scopes[s], lang)}", ""]
            for r in sorted(rs, key=lambda r: (aspect_order.index(r["aspect"]) if r["aspect"] in aspect_order else 99,
                                               r["id"])):
                lv = tr(LEVEL_TEXT[r.get("level", "should")], lang)
                L.append(f"- **[{lv} · {r['aspect']}] {tr(r['rule'], lang)}**")
                L.append(("  - 이유: " if ko else "  - Why: ") + tr(r["why"], lang))
                chk = r.get("check", {})
                L.append(("  - 점검" if ko else "  - Check") + f" ({tr(CHECK_TEXT.get(chk.get('type', 'review'), {}), lang)}): "
                         + tr(chk.get("how", ""), lang))
                extra = []
                if r.get("when"):
                    extra.append(", ".join(f"`{w}`" for w in r["when"]))
                if r.get("history"):
                    extra.append((f"고침 {len(r['history'])}" if ko else f"edits {len(r['history'])}"))
                L.append(("  - 피드백 " if ko else "  - feedback ") + str(len(r.get("feedback", [])))
                         + "".join(f" · {e}" for e in extra) + f" · `{r['id']}`")
            L.append("")
        off = [r for r in self.persisted() if r.get("status", "active") != "active"]
        if off:
            L += ["## 쉬거나 폐기한 규칙" if ko else "## Paused or retired", ""]
            for r in off:
                last = r["history"][-1]["change"] if r.get("history") else ""
                L.append(f"- ~~{tr(r['rule'], lang)}~~ · `{r['id']}` · {r.get('status')} · {last}")
            L.append("")
        events = [(f["date"], r["id"], tr(f.get("note", ""), lang)) for r in self.persisted() for f in r.get("feedback", [])]
        events += [(h["date"], r["id"], h["change"]) for r in self.persisted() for h in r.get("history", [])]
        if events:
            L += ["## 피드백과 변경 기록" if ko else "## Feedback and changes", "",
                  "| 날짜 | 규칙 | 내용 |" if ko else "| Date | Rule | Note |", "|---|---|---|"]
            for d, rid, note in sorted(events, key=lambda e: (e[0], e[1], e[2]), reverse=True):
                L.append(f"| {d} | `{rid}` | {str(note).replace('|', '/')} |")
        return "\n".join(L).rstrip("\n") + "\n"

    def brief(self, scopes, aspects=None, when=None, must_only=False, budget=0, lang="ko", compact=False,
              skip_scopes=()):
        """AI가 읽을 짧은 규칙 목록(설정 언어 한 벌, 글자 예산). / Short rule list for an AI, within budget."""
        rs = [r for r in self.rules_for(scopes, aspects, when) if not must_only or r.get("level") == "must"]
        rs = [r for r in rs if not any(r["scope"] == s or r["scope"].startswith(s + "/") for s in skip_scopes)]
        lines_by_rule = []
        for r in rs:
            n = len(r.get("feedback", []))
            tags = [r["aspect"]] + r.get("when", [])
            mark = (f" (지적 {n}회)" if lang == "ko" else f" (raised {n}x)") if n > 1 else ""
            lv = tr(LEVEL_TEXT[r.get("level", "should")], lang)
            text = f"- [{lv}·{'·'.join(tags)}] {rule_text(r, 'rule', lang)}{mark}"
            chk = r.get("check", {})
            if chk.get("type") == "review" and chk.get("how") and not compact:
                text += ("\n    점검: " if lang == "ko" else "\n    check: ") + tr(chk["how"], lang)
            lines_by_rule.append((r, text))
        kept = lines_by_rule
        dropped = 0
        if budget and sum(len(x[1]) + 1 for x in lines_by_rule) > budget:
            # 예산이 넘치면 필수를 먼저 담고, 남는 자리에 권장을 담는다(지적 많은 순)
            ranked = sorted(lines_by_rule, key=lambda x: (x[0].get("level") != "must", -len(x[0].get("feedback", []))))
            chosen, used = set(), 0
            for r, text in ranked:
                if used + len(text) + 1 > budget:
                    continue
                chosen.add(r["id"])
                used += len(text) + 1
            kept = [x for x in lines_by_rule if x[0]["id"] in chosen]
            dropped = len(lines_by_rule) - len(kept)
        head = (f"# 규칙 ({', '.join(scopes)} · 상위·하위 범위 포함 {len(kept)}개)" if lang == "ko"
                else f"# Rules ({', '.join(scopes)} · incl. parent and child scopes, {len(kept)})")
        out, current = [head], None
        for r, text in kept:
            if r["scope"] != current:
                current = r["scope"]
                out.append(f"\n[{current}] {tr(self.scopes.get(current, ''), lang)}")
            out.append(text)
        if dropped:
            out.append(f"\n(글자 예산 {budget}자 때문에 {dropped}개를 뺐습니다. 전부 보려면 --budget 0)" if lang == "ko"
                       else f"\n({dropped} rules left out to fit {budget} chars. Use --budget 0 for all.)")
        return "\n".join(out)

    def brief_json(self, scopes, aspects=None, when=None, must_only=False, lang="ko"):
        rs = [r for r in self.rules_for(scopes, aspects, when) if not must_only or r.get("level") == "must"]
        return [{"id": r["id"], "scope": r["scope"], "aspect": r["aspect"], "when": r.get("when", []),
                 "level": r.get("level"), "rule": rule_text(r, "rule", lang),
                 "check": tr(r.get("check", {}).get("how", ""), lang),
                 "feedbackCount": len(r.get("feedback", []))} for r in rs]


def _variants(text):
    if isinstance(text, dict):
        return [v for v in text.values() if v] or [""]
    return [str(text or "")]


def max_similarity(text, rule_value):
    """언어별 글과 따로 비교해 가장 높은 점수. / Best score across languages."""
    from .textsim import similarity
    return max(similarity(text, v) for v in _variants(rule_value))


def vote_stats(r, window=VOTE_WINDOW):
    votes = [v for v in r.get("votes", []) if v.get("kind") in ("useful", "miss")][-window:]
    useful = sum(1 for v in votes if v["kind"] == "useful")
    miss = sum(1 for v in votes if v["kind"] == "miss")
    total = useful + miss
    return {"useful": useful, "miss": miss, "total": total, "useless": (miss / total) if total else 0.0}


def pack_rule_hash(r):
    keys = ("scope", "aspect", "when", "level", "rule", "why", "check", "detect", "message", "cell", "max_cell",
            "on_delegate", "retire_when")
    # 빈 칸은 없는 칸과 같게 본다(when 없음 = when []) / an empty field equals a missing one
    body = json.dumps({k: (r.get(k) or None) for k in keys}, ensure_ascii=False, sort_keys=True)
    import hashlib
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def load_pack(name):
    return _packs.load_pack(name)


def available_packs():
    return _packs.available()


def _pack_copy(pr, pack):
    """꾸러미 규칙을 DB에 넣을 모양으로. / A pack rule shaped for the DB."""
    r = copy.deepcopy(pr)
    r.setdefault("when", [])
    r.setdefault("feedback", [])
    r.setdefault("history", [])
    r.setdefault("status", "active")
    r["origin"] = f"pack:{pack['pack']}@{pack['version']}"
    r["origin_hash"] = pack_rule_hash(pr)
    return r
