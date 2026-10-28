"""규칙 DB와 rules 명령 시험. / Rule DB and rules command tests."""
import json
import unittest

from helpers import TempProject
from habitree.core.ruledb import RuleDB, load_pack, vote_stats


def detect_rule(rid="work.loop.same-call"):
    return {"id": rid, "scope": "work", "aspect": "process", "level": "should", "rule": "같은 호출을 되풀이하지 않는다",
            "why": "토큰", "check": {"type": "auto", "how": "guard"}, "feedback": [], "history": [],
            "detect": {"signal": "same_call", "threshold": 3, "stop_at": 5, "severity": "info"}}


class TestRuleDB(TempProject):
    def db(self):
        d = RuleDB({"scopes": {}, "aspects": {}, "contexts": {}, "rules": []}, self.root / "r.json")
        d.merge_pack(load_pack("base"))
        return d

    def test_pack_valid_and_tree(self):
        d = self.db()
        self.assertEqual(d.validate(), [])
        self.assertEqual(d.chain("work/cycle"), ["work/cycle", "work", "global"])
        ids = [r["id"] for r in d.rules_for(["work/cycle"])]
        self.assertIn("work.cycle.find-first", ids)
        self.assertNotIn("docs.single-source", ids)
        self.assertIn("work.verify.define-check", [r["id"] for r in d.rules_for(["work"])])

    def test_make_id_korean(self):
        d = self.db()
        rid = d.make_id("work", "같은 파일 조금씩 고치기")
        self.assertEqual(rid, "work.같은-파일-조금씩")
        self.assertEqual(d.make_id("work", "Batch small edits together"), "work.batch-small-edits")

    def test_hit_promotes_human_rule(self):
        d = self.db()
        r = d.add("work", "process", "새 규칙", "이유", "첫 지적")
        self.assertEqual(r["level"], "should")
        d.hit(r["id"], "또 지적")
        self.assertEqual(r["level"], "must")
        d.demote(r["id"], "너무 셌다")
        self.assertEqual(r["level"], "should")
        self.assertEqual(len(r["history"]), 2)

    def test_detect_votes(self):
        d = self.db()
        d.data["scopes"].setdefault("work", "w")
        r = detect_rule()
        d.rules.append(r)
        d.hit(r["id"], "맞았다")
        self.assertEqual(r["detect"]["severity"], "info")
        d.hit(r["id"], "또 맞았다")
        self.assertEqual(r["detect"]["severity"], "warn")  # info → warn, 절대 stop으로는 자동 승격하지 않음
        self.assertEqual(r["level"], "should")
        for _ in range(3):
            d.useful = d.hit(r["id"], "맞음")
        _, notes = d.miss(r["id"], "잔소리")
        st = vote_stats(r)
        self.assertEqual(st["miss"], 1)
        self.assertGreaterEqual(st["total"], 5)
        self.assertIn("threshold 3 → 4", notes)
        self.assertEqual(r["detect"]["threshold"], 4)
        for _ in range(3):
            _, notes = d.miss(r["id"], "또 잔소리")
        self.assertIn("suggest:pause", notes)
        self.assertNotEqual(r["detect"]["severity"], "stop")

    def test_brief_budget_keeps_must(self):
        d = self.db()
        full = d.brief(["global"], budget=0)
        cut = d.brief(["global"], budget=600)
        self.assertLess(len(cut), len(full))
        self.assertIn("--budget 0", cut)
        self.assertIn("[필수", cut)

    def test_similar(self):
        d = self.db()
        sims = d.similar("같은 파일을 여러 번 조금씩 고치지 않는다")
        self.assertTrue(sims and sims[0][1]["id"] == "work.cycle.batch-edits")

    def test_merge_pack_keeps_user_edits(self):
        d = self.db()
        r = d.find("docs.single-source")
        r["rule"] = "내가 고친 문장"
        pack = load_pack("base")
        pack["version"] = "9.9.9"
        for pr in pack["rules"]:
            if pr["id"] == "docs.single-source":
                pr["why"] = {"ko": "새 이유", "en": "new why"}
        rep = d.merge_pack(pack)
        self.assertIn("docs.single-source", rep["kept"])
        self.assertEqual(d.find("docs.single-source")["rule"], "내가 고친 문장")


class TestRulesCommand(TempProject):
    def test_add_hit_similar_doc(self):
        self.init()
        code, out, err = self.cli("rules", "add", "--scope", "work", "--aspect", "process",
                                  "--rule", "같은 파일을 여러 번 조금씩 고치지 않는다", "--why", "토큰", "--feedback", "지적")
        self.assertEqual(code, 2)
        self.assertIn("work.cycle.batch-edits", err)
        code, out, err = self.cli("rules", "add", "--scope", "work", "--aspect", "process",
                                  "--rule", "커밋 메시지는 한국어로 쓴다", "--why", "팀 규칙", "--feedback", "지적")
        self.assertEqual(code, 0, err)
        db = json.loads(self.read(".habitree/rules.json"))
        rid = [r["id"] for r in db["rules"] if r["rule"] == "커밋 메시지는 한국어로 쓴다"][0]
        code, out, err = self.cli("rules", "hit", rid, "--feedback", "또")
        self.assertEqual(code, 0, err)
        self.assertIn("필수", out)
        self.assertIn("커밋 메시지는 한국어로 쓴다", self.read(".habitree/RULES.md"))
        code, out, _ = self.cli("rules", "brief", "work", "--json")
        self.assertIn(rid, out)
        code, _, err = self.cli("rules", "brief", "없는범위")
        self.assertEqual(code, 2)

    def test_external_db(self):
        """다른 형식의 기존 규칙 DB(v1)도 --db로 그대로 다룬다. / Works on an existing v1 DB."""
        self.write("rules.json", json.dumps({
            "about": "x", "version": 1, "scopes": {"global": "모든", "story": "이야기", "story/person": "사람"},
            "parents": {"story": "global"}, "aspects": {"look": "모양"}, "contexts": {"beat:problem": "문제"},
            "rules": [{"id": "a", "scope": "story/person", "aspect": "look", "when": [], "level": "must",
                       "rule": "손은 둥글게", "why": "어색함", "check": {"type": "review", "how": "본다"},
                       "feedback": [{"date": "2026-10-25", "note": "n", "ref": ""}], "history": [], "status": "active"}]},
            ensure_ascii=False))
        code, out, err = self.cli("rules", "--db", "rules.json", "brief", "story")
        self.assertEqual(code, 0, err)
        self.assertIn("손은 둥글게", out)


if __name__ == "__main__":
    unittest.main()
