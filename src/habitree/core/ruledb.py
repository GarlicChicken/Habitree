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
from importlib import resources
from pathlib import Path

from . import HabitreeError
from . import io as hio
from .i18n import t, tr
from .schema import load_schema, validate
from .textsim import similarity
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
        self.data.setdefault("scopes", {"global": {"ko": "모든 작업", "en": "All work"}})
        self.data.setdefault("parents", {})
        self.data.setdefault("aspects", {})
        self.data.setdefault("contexts", {})
        self.data.setdefault("rules", [])

    # ── 불러오기·저장 ──
    @classmethod
    def load(cls, path, lang="ko"):
        path = Path(path)
        if not path.is_file():
            raise HabitreeError(t("no_db", lang, path=path))
        try:
            data = hio.load_json(path)
        except json.JSONDecodeError as e:
            raise HabitreeError(f"규칙 DB JSON이 깨졌습니다 / Broken JSON: {path}: {e}")
        return cls(data, path)

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
        hio.save_json(self.path, self.data)
        if doc_path:
            hio.write_text(doc_path, self.render_md(Path(doc_path).parent, self.path))

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
    def render_md(self, doc_dir=None, db_path=None):
        """RULES.md(사람용, 두 언어). 같은 입력이면 항상 같은 결과. / Deterministic bilingual doc."""
        rules = self.active()
        dates = [f["date"] for r in self.rules for f in r.get("feedback", [])]
        link = "rules.json"
        if doc_dir and db_path:
            try:
                link = Path(db_path).resolve().relative_to(Path(doc_dir).resolve()).as_posix()
            except ValueError:
                link = Path(db_path).name
        L = [
            "# 규칙 · Rules",
            "",
            f"> 이 문서는 [{Path(link).name}]({link})에서 자동으로 만든다. 직접 고치지 말고 `habitree rules`로 고친다.",
            f"> Generated from [{Path(link).name}]({link}). Do not edit by hand; use `habitree rules`.",
            "",
            f"- 규칙 {len(rules)}개 · 피드백 {sum(len(r.get('feedback', [])) for r in rules)}건 · "
            f"마지막 피드백 {max(dates) if dates else '-'}",
            f"- {len(rules)} rules · {sum(len(r.get('feedback', [])) for r in rules)} feedback entries · "
            f"last feedback {max(dates) if dates else '-'}",
            "",
            "## 범위 · Scopes",
            "",
            "| 범위 · Scope | 뜻 · Meaning | 규칙 · Rules |",
            "|---|---|---|",
        ]
        for s, depth in self.order():
            n = sum(1 for r in rules if r["scope"] == s)
            L.append(f"| {'　' * depth}`{s}` | {_cell(self.scopes[s])} | {n} |")
        L += ["", "## 관점 · Aspects", "", "| 관점 · Aspect | 뜻 · Meaning | 규칙 · Rules |", "|---|---|---|"]
        for a, desc in self.data["aspects"].items():
            L.append(f"| `{a}` | {_cell(desc)} | {sum(1 for r in rules if r['aspect'] == a)} |")
        if self.data["contexts"]:
            L += ["", "## 상황 태그 · Contexts", "", "| 태그 · Tag | 뜻 · Meaning | 규칙 · Rules |", "|---|---|---|"]
            for c, desc in self.data["contexts"].items():
                L.append(f"| `{c}` | {_cell(desc)} | {sum(1 for r in rules if c in r.get('when', []))} |")
        L += ["", "## 규칙 · Rules", ""]
        aspect_order = list(self.data["aspects"])
        for s, _ in self.order():
            rs = [r for r in rules if r["scope"] == s]
            if not rs:
                continue
            L += [f"### `{s}` · {_cell(self.scopes[s])}", ""]
            for r in sorted(rs, key=lambda r: (aspect_order.index(r["aspect"]) if r["aspect"] in aspect_order else 99,
                                               r["id"])):
                lv = r.get("level", "should")
                L.append(f"- **[{LEVEL_TEXT[lv]['ko']} · {lv} · {r['aspect']}] {_inline(r['rule'])}**")
                L.append(f"  - 이유 · Why: {_inline(r['why'])}")
                chk = r.get("check", {})
                ctype = chk.get("type", "review")
                L.append(f"  - 점검 · Check ({CHECK_TEXT.get(ctype, {}).get('ko', ctype)} · {ctype}): "
                         f"{_inline(chk.get('how', ''))}")
                if r.get("detect"):
                    d = r["detect"]
                    L.append(f"  - 감지 · Detect: `{d.get('signal')}` · {d.get('event', '')} · "
                             f"threshold {d.get('threshold', '-')} · {d.get('severity', 'info')}")
                extra = []
                if r.get("when"):
                    extra.append("상황 · when: " + ", ".join(f"`{w}`" for w in r["when"]))
                if r.get("history"):
                    extra.append(f"고침 · edits {len(r['history'])}")
                if r.get("origin"):
                    extra.append(f"`{r['origin']}`")
                L.append(f"  - 피드백 · feedback {len(r.get('feedback', []))}"
                         + "".join(f" · {e}" for e in extra) + f" · `{r['id']}`")
            L.append("")
        off = [r for r in self.rules if r.get("status", "active") != "active"]
        if off:
            L += ["## 쉬거나 폐기한 규칙 · Paused or retired", ""]
            for r in off:
                last = r["history"][-1]["change"] if r.get("history") else ""
                L.append(f"- ~~{_inline(r['rule'])}~~ · `{r['id']}` · {r.get('status')} · {_inline(last)}")
            L.append("")
        events = [(f["date"], r["id"], f.get("note", "")) for r in self.rules for f in r.get("feedback", [])]
        events += [(h["date"], r["id"], f"(고침 · edit) {h['change']}") for r in self.rules for h in r.get("history", [])]
        if events:
            L += ["## 피드백·변경 기록 · Feedback and changes", "", "| 날짜 · Date | 규칙 · Rule | 내용 · Note |",
                  "|---|---|---|"]
            for d, rid, note in sorted(events, key=lambda e: (e[0], e[1], e[2]), reverse=True):
                L.append(f"| {d} | `{rid}` | {_inline(note).replace('|', '/')} |")
        return "\n".join(L) + "\n"

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
    body = json.dumps({k: r.get(k) for k in keys}, ensure_ascii=False, sort_keys=True)
    import hashlib
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def load_pack(name):
    text = resources.files("habitree.data").joinpath("packs", f"{name}.json").read_text(encoding="utf-8")
    return json.loads(text)


def available_packs():
    folder = resources.files("habitree.data").joinpath("packs")
    return sorted(p.name[:-5] for p in folder.iterdir() if p.name.endswith(".json"))


def _cell(text):
    if isinstance(text, dict):
        ko, en = text.get("ko", ""), text.get("en", "")
        return f"{ko} · {en}" if ko and en and ko != en else (ko or en)
    return str(text or "")


def _inline(text):
    if isinstance(text, dict):
        ko, en = text.get("ko", ""), text.get("en", "")
        if ko and en and ko != en:
            return f"{ko} / {en}"
        return ko or en
    return str(text or "")
