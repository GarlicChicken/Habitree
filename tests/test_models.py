"""모델 배분(models)과 검증 명령(verify) 시험. / Model allocation and verify tests."""
import copy
import json
import sys
import unittest
from datetime import date

from helpers import TempProject
from habitree.core import HabitreeError
from habitree.core import vendors
from habitree.core.config import Context
from habitree.core.modelpolicy import (escalate, fm_get, fm_set, normalize_task, policy, read_events, steps_between,
                                       tune)
from habitree.core.ruledb import RuleDB, load_pack
from habitree.core.schema import load_schema, validate
from habitree.core.vendors import parse_cell

PRICE_KEYS = {"model", "vendor", "currency", "per_tokens", "input", "output", "cache_read", "cache_write",
              "cache_write_long", "cache_storage_hour", "above", "upcoming", "as_of", "checked", "source", "note"}


def pack_db():
    d = RuleDB({"scopes": {}, "aspects": {}, "contexts": {}, "rules": []})
    d.merge_pack(load_pack("base"))
    d.merge_pack(load_pack("task"))
    return d


def events(task, result, cell, n):
    return [{"task": task, "result": result, "cell": cell} for _ in range(n)]


class TestVendorTable(unittest.TestCase):
    def test_bundled_table_matches_schema(self):
        t = vendors.bundled()
        self.assertEqual(validate(t, load_schema("vendors.schema.json")), [])
        self.assertEqual(vendors.problems(t), [])
        for v in t["vendors"].values():
            self.assertEqual(v["checked"], "2026-10-28")
            for tier in ("low", "mid", "high", "top"):
                self.assertIn(tier, v["tiers"])
            for m in v["models"].values():
                self.assertTrue(m["source"].startswith("https://"))

    def test_schema_and_meaning_errors(self):
        t = vendors.bundled()
        t["vendors"]["anthropic"]["models"]["claude-opus-5-5"]["price"]["input"] = "4"
        self.assertTrue(vendors.problems(t))
        t = vendors.bundled()
        t["vendors"]["openai"]["tiers"]["mid"] = "no-such-model"
        self.assertTrue(any("no-such-model" in p for p in vendors.problems(t)))
        t = vendors.bundled()
        t["vendors"]["google"]["models"]["gemini-4-argon"]["surprise"] = 1
        self.assertTrue(vendors.problems(t))

    def test_resolve(self):
        t = vendors.bundled()
        r = vendors.resolve("mid:medium", "anthropic", t)
        self.assertEqual((r["model"], r["effort_value"], r["effort_param"]),
                         ("claude-sonnet-5-5", "medium", "output_config.effort"))
        self.assertEqual(r["aliases"], ["sonnet"])
        self.assertEqual(vendors.resolve("high:max", "anthropic", t)["effort_value"], "xhigh")
        self.assertEqual(vendors.resolve("low:low", "openai", t)["model"], "gpt-6-luna")
        self.assertEqual(vendors.resolve("top:high", "openai", t)["model"], "gpt-6-astra")
        g = vendors.resolve("top:high", "google", t)
        self.assertTrue(g["substituted"])
        self.assertEqual((g["model"], g["used_effort"], g["effort_value"]), ("gemini-4-argon", "max", "high"))
        self.assertIn("추정", g["reason"]["ko"])
        with self.assertRaises(HabitreeError):
            vendors.resolve("mid", "nobody", t)
        with self.assertRaises(HabitreeError):
            parse_cell("huge:medium")
        self.assertEqual(parse_cell("mid"), {"tier": "mid", "effort": "medium"})

    def test_effort_clamped_to_supported(self):
        t = vendors.bundled()
        t["vendors"]["anthropic"]["models"]["claude-haiku-5-5"]["efforts"] = ["low", "medium", "high"]
        r = vendors.resolve("low:max", "anthropic", t)
        self.assertEqual(r["effort_value"], "high")
        self.assertIn("xhigh", r["reason"]["en"])

    def test_price_lookup(self):
        t = vendors.bundled()
        p = vendors.price("claude-opus-5-5", t)
        self.assertEqual(set(p), PRICE_KEYS)
        self.assertEqual((p["input"], p["output"], p["cache_read"], p["cache_write"], p["cache_write_long"]),
                         (4, 20, 0.2, 5, 8))
        self.assertEqual((p["currency"], p["per_tokens"]), ("USD", 1000000))
        for name in ("opus", "anthropic/claude-opus-5-5", "anthropic.claude-opus-5-5", "Claude-Opus-5-5[1m]"):
            self.assertEqual(vendors.price(name, t)["model"], "claude-opus-5-5", name)
        self.assertIsNone(vendors.price("unknown-model", t))
        self.assertIsNone(vendors.price("gpt-5", t))  # 아는 모델이지만 가격을 확인하지 않았다
        self.assertEqual(vendors.price("haiku", t)["above"][0]["prompt_tokens"], 100000)
        self.assertEqual(vendors.price("gpt-6.1-sol", t)["above"][0]["input"], 4)

    def test_price_changes_by_date(self):
        t = vendors.bundled()
        before = vendors.price("gemini-4-argon", t, on="2026-11-30")
        self.assertEqual(before["input"], 2)
        self.assertEqual(before["upcoming"][0]["from"], "2026-12-01")
        later = vendors.price("gemini-4-argon", t, on=date(2026, 12, 1))
        self.assertEqual((later["input"], later["output"], later["cache_read"]), (4, 20, 0.2))
        self.assertEqual(later["upcoming"], [])

    def test_deprecations_and_checked_age(self):
        t = vendors.bundled()
        soon = {d["model"]: d for d in vendors.deprecations(90, t, today="2026-10-28")}
        self.assertEqual(soon["claude-sonnet-4-5-20250929"]["days_left"], 33)
        self.assertEqual(soon["claude-sonnet-4-5-20250929"]["replacement"], "claude-sonnet-5-5")
        self.assertEqual(soon["gpt-5-2025-08-07"]["days_left"], 44)
        self.assertNotIn("claude-opus-5-5", soon)
        self.assertEqual(vendors.deprecations(90, t, today="2026-10-28", models={"claude-opus-5-5"}), [])
        self.assertEqual(vendors.checked_age_days(t, "anthropic", today="2026-10-28"), 0)
        self.assertEqual(vendors.checked_age_days(t, today="2027-01-27")["openai"], 91)
        self.assertIsNone(vendors.checked_age_days(t, "nobody"))


class TestVendorOverride(TempProject):
    def test_project_file_merges_by_entry(self):
        self.write(".habitree/vendors.json", json.dumps({"vendors": {
            "anthropic": {"models": {"claude-opus-5-5": {"price": {"input": 3.6}}, "claude-fable-5": None}},
            "local": {"name": "Local", "checked": "2026-10-28",
                      "effort_map": {"low": "low", "medium": "medium", "high": "high", "max": "high"},
                      "tiers": {"low": "tiny"},
                      "models": {"tiny": {"tier": "low", "price": {"input": 0, "output": 0}, "source": "local"}}}}}))
        t = vendors.load(Context.load(self.root))
        p = vendors.price("claude-opus-5-5", t)
        self.assertEqual((p["input"], p["output"], p["cache_read"]), (3.6, 20, 0.2))
        self.assertNotIn("claude-fable-5", t["vendors"]["anthropic"]["models"])
        self.assertIn("claude-sonnet-5-5", t["vendors"]["anthropic"]["models"])
        self.assertEqual(vendors.resolve("low:low", "local", t)["model"], "tiny")

    def test_broken_override_is_reported(self):
        self.write(".habitree/vendors.json", '{"vendors": {"anthropic": {"tiers": {"mid": "nope"}}}}')
        with self.assertRaises(HabitreeError):
            vendors.load(Context.load(self.root))
        self.write(".habitree/vendors.json", "{broken")
        with self.assertRaises(HabitreeError):
            vendors.load(Context.load(self.root))


class TestPolicy(unittest.TestCase):
    def test_task_pack(self):
        d = pack_db()
        self.assertEqual(d.validate(), [])
        self.assertEqual(d.duplicate_pairs(), [])
        self.assertEqual(normalize_task(d, "explore"), "task/explore")
        self.assertEqual(normalize_task(d, "task/code/clear-spec"), "task/code/clear-spec")
        with self.assertRaises(HabitreeError):
            normalize_task(d, "dance")
        for r in load_pack("task")["rules"]:
            self.assertIn("ko", r["rule"])
            self.assertIn("en", r["rule"])
            if r.get("cell"):
                self.assertIn(f"`{r['cell']['tier']}:{r['cell']['effort']}`", r["rule"]["ko"])
            if r["level"] == "must":
                self.assertIn("cell", r)

    def test_inheritance_and_floor(self):
        d = pack_db()
        p = policy(d, "task/code/clear-spec")
        self.assertEqual((p["rule"], p["floor"], p["risky"]), ("task.code.clear-spec.cell", None, False))
        d.data["scopes"]["task/risky/deploy"] = "deploy"
        p = policy(d, "task/risky/deploy")
        self.assertEqual((p["rule"], p["cell"], p["floor"], p["risky"]),
                         ("task.risky.floor", parse_cell("high:high"), parse_cell("high:high"), True))
        self.assertEqual(p["max_cell"], parse_cell("top:high"))
        self.assertEqual(p["verify"], ["*"])
        d.add("task/risky/deploy", "model", "deploy cheap", "x", "x")["cell"] = {"tier": "mid", "effort": "low"}
        p = policy(d, "task/risky/deploy")
        self.assertEqual(p["default"], parse_cell("mid:low"))
        self.assertEqual(p["cell"], parse_cell("high:high"))  # 하한이 이긴다

    def test_steps_between(self):
        self.assertEqual(steps_between(parse_cell("mid:medium"), parse_cell("mid:high")), 1)
        self.assertEqual(steps_between(parse_cell("mid:medium"), parse_cell("high:high")), 2)
        self.assertEqual(steps_between(parse_cell("mid:medium"), parse_cell("low:high")), 0)


class TestEscalate(unittest.TestCase):
    def setUp(self):
        self.db = pack_db()
        self.code = policy(self.db, "task/code")  # mid:medium, 상한 high:high

    def esc(self, pol, cur, signal, attempt=1, verified=("test",)):
        return escalate(pol, cur, signal, attempt, verified)

    def test_skipped_steps_raise_effort(self):
        r = self.esc(self.code, "mid:medium", "skipped_steps")
        self.assertEqual((r["action"], r["to"]), ("escalate", "mid:high"))

    def test_effort_at_max_moves_tier(self):
        pol = dict(self.code, default=parse_cell("mid:max"), cell=parse_cell("mid:max"))
        r = self.esc(pol, "mid:max", "skipped_steps")
        self.assertEqual((r["action"], r["to"]), ("escalate", "high:high"))  # 상한 high:high로 강도를 맞춤

    def test_confident_wrong_and_loop_raise_tier(self):
        for signal in ("confident_wrong", "loop"):
            r = self.esc(self.code, "mid:medium", signal)
            self.assertEqual((r["action"], r["to"]), ("escalate", "high:medium"), signal)
            self.assertEqual(len(r["advice"]), 2)

    def test_format_error_retries_once(self):
        r = self.esc(self.code, "mid:medium", "format_error", attempt=1)
        self.assertEqual((r["action"], r["to"]), ("retry", "mid:medium"))
        r = self.esc(self.code, "mid:medium", "format_error", attempt=2)
        self.assertEqual((r["action"], r["to"]), ("escalate", "high:medium"))
        r = self.esc(self.code, "mid:high", "format_error", attempt=2)  # 한 단계 올라온 뒤 첫 실패
        self.assertEqual(r["action"], "retry")

    def test_outages_never_raise_the_tier(self):
        for signal in ("infra", "refusal"):
            r = self.esc(self.code, "mid:medium", signal, verified=())
            self.assertEqual((r["action"], r["to"]), ("fallback", "mid:medium"), signal)
        r = self.esc(self.code, "mid:medium", "truncated")
        self.assertEqual((r["action"], r["to"]), ("retry", "mid:medium"))

    def test_step_cap(self):
        r = self.esc(self.code, "high:high", "confident_wrong", attempt=3)
        self.assertEqual(r["action"], "human")
        self.assertEqual(r["steps"], 2)

    def test_attempt_cap(self):
        for signal in ("confident_wrong", "infra"):
            r = self.esc(self.code, "mid:medium", signal, attempt=4)
            self.assertEqual(r["action"], "human", signal)

    def test_risky_goes_to_a_person(self):
        risky = policy(self.db, "task/risky")
        self.assertEqual(self.esc(risky, "high:high", "confident_wrong")["action"], "human")
        self.assertEqual(self.esc(risky, "high:high", "skipped_steps")["action"], "human")
        self.assertEqual(self.esc(risky, "high:high", "infra")["action"], "fallback")

    def test_needs_machine_verification(self):
        r = self.esc(self.code, "mid:medium", "confident_wrong", verified=())
        self.assertEqual(r["action"], "human")
        self.assertIn("기계 검증", r["reason"]["ko"])

    def test_max_cell_cap(self):
        explore = policy(self.db, "task/explore")  # low:medium, 상한 mid:medium
        r = self.esc(explore, "low:medium", "confident_wrong")
        self.assertEqual((r["action"], r["to"]), ("escalate", "mid:medium"))
        r = self.esc(explore, "mid:medium", "confident_wrong", attempt=2)
        self.assertEqual(r["action"], "human")
        self.assertIn("mid:medium", r["reason"]["en"])

    def test_unknown_signal(self):
        with self.assertRaises(HabitreeError):
            self.esc(self.code, "mid:medium", "vibes")


class TestTune(unittest.TestCase):
    def item(self, rep, task):
        return next(x for x in rep if x["task"] == task)

    def test_raise_when_quality_failures_reach_ratio(self):
        db = pack_db()
        evs = events("task/code", "pass", "mid:medium", 7) + events("task/code", "quality_fail", "mid:medium", 3)
        x = self.item(tune(db, evs), "task/code")
        self.assertEqual((x["action"], x["to"], x["runs"], x["fails"]), ("raised", "mid:high", 10, 3))
        r = db.find("task.code.cell")
        self.assertEqual(r["cell"], {"tier": "mid", "effort": "high"})
        self.assertIn("`mid:high`", r["rule"]["ko"])
        self.assertIn("`mid:high`", r["rule"]["en"])
        self.assertIn("tune", r["history"][-1]["change"])
        x = self.item(tune(db, evs), "task/code")  # 새 칸의 기록이 아직 없다
        self.assertEqual(x["action"], "few")
        self.assertEqual(r["cell"], {"tier": "mid", "effort": "high"})

    def test_below_ratio_or_too_few_runs_keep(self):
        db = pack_db()
        x = self.item(tune(db, events("task/code", "quality_fail", "mid:medium", 9)), "task/code")
        self.assertEqual(x["action"], "few")
        evs = events("task/code", "pass", "mid:medium", 9) + events("task/code", "quality_fail", "mid:medium", 1)
        evs += events("task/code", "infra_fail", "mid:medium", 10)  # 장애는 세지 않는다
        x = self.item(tune(db, evs), "task/code")
        self.assertEqual((x["action"], x["runs"]), ("keep", 10))
        self.assertEqual(db.find("task.code.cell")["cell"], {"tier": "mid", "effort": "medium"})

    def test_window_uses_recent_twenty(self):
        db = pack_db()
        evs = events("task/code", "quality_fail", "mid:medium", 10) + events("task/code", "pass", "mid:medium", 20)
        x = self.item(tune(db, evs, apply=False), "task/code")
        self.assertEqual((x["runs"], x["fails"]), (20, 0))

    def test_lowering_is_only_suggested(self):
        db = pack_db()
        x = self.item(tune(db, events("task/explore", "pass", "low:medium", 20)), "task/explore")
        self.assertEqual((x["action"], x["to"]), ("suggest_down", "low:low"))
        self.assertEqual(db.find("task.explore.cell")["cell"], {"tier": "low", "effort": "medium"})

    def test_floor_is_protected(self):
        db = pack_db()
        before = copy.deepcopy(db.find("task.risky.floor"))
        x = self.item(tune(db, events("task/risky", "quality_fail", "high:high", 15)), "task/risky")
        self.assertEqual(x["action"], "floor")
        x = self.item(tune(db, events("task/risky", "pass", "high:high", 25)), "task/risky")
        self.assertEqual(x["action"], "floor")
        self.assertEqual(db.find("task.risky.floor"), before)

    def test_cap_and_dry_run(self):
        db = pack_db()
        x = self.item(tune(db, events("task/long-autonomous", "quality_fail", "top:high", 10)), "task/long-autonomous")
        self.assertEqual(x["action"], "cap")
        evs = events("task/code", "quality_fail", "mid:medium", 10)
        x = self.item(tune(db, evs, apply=False), "task/code")
        self.assertEqual(x["action"], "raised")
        self.assertEqual(db.find("task.code.cell")["cell"], {"tier": "mid", "effort": "medium"})


class TestFrontMatter(unittest.TestCase):
    def test_get_and_set(self):
        text = "---\nname: a\ndescription: |\n  여러 줄\n  설명\nmodel: \"sonnet\"\n---\nmodel: body\n"
        self.assertEqual(fm_get(text, "model"), "sonnet")
        new = fm_set(text, {"model": "claude-haiku-5-5", "effort": "medium"})
        self.assertEqual(new, "---\nname: a\ndescription: |\n  여러 줄\n  설명\nmodel: claude-haiku-5-5\n"
                              "effort: medium\n---\nmodel: body\n")
        self.assertIsNone(fm_set("no front matter\n", {"model": "x"}))
        self.assertIsNone(fm_get("no front matter\n", "model"))


class ModelsProject(TempProject):
    def setUp(self):
        super().setUp()
        self.init()

    def config(self, **updates):
        cfg = json.loads(self.read(".habitree/config.json"))
        cfg.update(updates)
        self.write(".habitree/config.json", json.dumps(cfg, ensure_ascii=False))

    def json_cli(self, *args):
        code, out, err = self.cli(*args)
        return code, json.loads(out)


class TestModelsCommand(ModelsProject):
    def test_init_adds_task_pack_and_stays_clean(self):
        db = json.loads(self.read(".habitree/rules.json"))
        self.assertEqual(db["packs"]["task"], "0.3.0")
        self.assertIn("task.risky.floor", self.read(".habitree/RULES.md"))
        code, findings = self.check_json()
        self.assertEqual(self.ids(findings), [])  # models 절이 없으면 모델 점검을 건너뛴다
        self.assertIn("high:high", self.read("AGENTS.md"))  # 하한(필수 규칙)이 AI 지침 요약에 들어간다

    def test_show_and_pick(self):
        code, out, err = self.cli("models")
        self.assertEqual(code, 0, err)
        self.assertIn("task/review/security", out)
        self.assertIn("gemini-4-argon", out)
        code, out, err = self.cli("models", "show", "debug")
        self.assertEqual(code, 0, err)
        self.assertIn("claude-opus-5-5", out)
        code, data = self.json_cli("models", "pick", "explore", "--json")
        self.assertEqual((data["model"], data["effort_value"], data["cell"]), ("claude-haiku-5-5", "medium", "low:medium"))
        self.assertFalse(data["auto_escalate"])
        code, data = self.json_cli("models", "pick", "code", "--vendor", "openai", "--json")
        self.assertEqual(data["model"], "gpt-6.1-terra")
        self.assertEqual(data["price"]["input"], 1)
        code, out, err = self.cli("models", "pick", "dance")
        self.assertEqual(code, 2)

    def test_escalate_exit_codes(self):
        self.config(verify={"test": [sys.executable, "-c", "pass"]})
        code, data = self.json_cli("models", "escalate", "code", "--signal", "confident_wrong", "--json")
        self.assertEqual((code, data["action"], data["to"], data["model"]), (0, "escalate", "high:medium",
                                                                             "claude-opus-5-5"))
        code, data = self.json_cli("models", "escalate", "code", "--signal", "infra", "--json")
        self.assertEqual((code, data["action"]), (0, "fallback"))
        self.assertEqual({a["vendor"] for a in data["alternatives"]}, {"openai", "google"})
        code, data = self.json_cli("models", "escalate", "risky", "--signal", "loop", "--json")
        self.assertEqual((code, data["action"]), (3, "human"))
        code, out, err = self.cli("models", "escalate", "code", "--from", "high:high", "--signal", "loop")
        self.assertEqual(code, 3)

    def test_record_tune_set(self):
        for i in range(10):
            self.cli("models", "record", "code", "--result", "quality_fail" if i < 2 else "pass")
        self.assertEqual(len(read_events(Context.load(self.root))), 10)
        code, out, err = self.cli("models", "tune")
        self.assertEqual(code, 0, err)
        rule = next(r for r in json.loads(self.read(".habitree/rules.json"))["rules"] if r["id"] == "task.code.cell")
        self.assertEqual(rule["cell"], {"tier": "mid", "effort": "high"})
        code, findings = self.check_json()
        self.assertNotIn("rules.doc-stale", self.ids(findings))
        code, out, err = self.cli("models", "set", "risky", "--cell", "mid:low", "--why", "시험")
        self.assertEqual(code, 0, err)  # 하한 규칙 자신은 사람이 바꿀 수 있다
        self.cli("models", "set", "risky", "--cell", "high:high", "--why", "되돌림")
        db = json.loads(self.read(".habitree/rules.json"))
        db["scopes"]["task/risky/deploy"] = "deploy"
        self.write(".habitree/rules.json", json.dumps(db, ensure_ascii=False))
        code, out, err = self.cli("models", "set", "risky/deploy", "--cell", "mid:low", "--why", "싸게")
        self.assertEqual(code, 2)  # 상위 하한보다 낮게 둘 수 없다
        self.assertIn("high:high", err)

    def test_export_claude_touches_front_matter_only(self):
        body = "\n# 역할\n\n탐색만 한다.\nmodel: 본문 속 글은 그대로\n"
        head = "---\nname: scout\ndescription: 찾기 전담\ntools: Read, Grep\nmodel: opus\n---\n"
        self.write(".claude/agents/scout.md", head + body)
        self.write(".claude/agents/other.md", "---\nname: guard\nmodel: haiku\n---\nbody\n")
        self.config(models={"agents": {"scout": "task/explore", "guard": "task/risky", "ghost": "task/code"}})
        code, out, err = self.cli("models", "export", "claude")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.read(".claude/agents/scout.md"), head + body)  # 미리 보기는 쓰지 않는다
        self.assertIn("--write", out)
        self.assertIn("ghost", out)
        code, out, err = self.cli("models", "export", "claude", "--write")
        self.assertEqual(code, 0, err)
        after = self.read(".claude/agents/scout.md")
        self.assertTrue(after.endswith(body))
        self.assertEqual(after, "---\nname: scout\ndescription: 찾기 전담\ntools: Read, Grep\nmodel: claude-haiku-5-5\n"
                                "effort: medium\n---\n" + body)
        self.assertIn("model: claude-opus-5-5\neffort: high\n", self.read(".claude/agents/other.md"))
        code, out, err = self.cli("models", "export", "claude")
        self.assertNotIn("--write", out)
        self.config(models={"agents": {"scout": "task/explore"}, "claude_model": "alias"})
        self.cli("models", "export", "claude", "--write")
        self.assertIn("model: haiku\n", self.read(".claude/agents/scout.md"))

    def test_export_other_tools(self):
        self.config(verify={"test": [sys.executable, "-m", "unittest"], "lint": ["ruff", "check", "."]},
                    models={"agents": {"scout": "task/explore"}})
        code, out, _ = self.cli("models", "export", "codex")
        self.assertIn('model = "gpt-6-luna"', out)
        self.assertIn("review_model = ", out)
        self.assertIn("~/.codex/ht-high-high.config.toml", out)
        code, out, _ = self.cli("models", "export", "aider")
        self.assertIn('weak-model: "anthropic/claude-haiku-5-5"', out)
        self.assertIn("test-cmd: ", out)
        self.assertIn('lint-cmd: "ruff check ."', out)
        code, out, _ = self.cli("models", "export", "litellm")
        self.assertIn("model_list:", out)
        self.assertIn('api_key: "os.environ/ANTHROPIC_API_KEY"', out)
        self.assertIn('"ht-mid-medium": ["ht-mid-medium-openai", "ht-mid-medium-google"]', out)
        code, out, _ = self.cli("models", "export", "opencode", "--vendor", "openai")
        data = json.loads("\n".join(line for line in out.splitlines() if not line.startswith("#")))
        self.assertEqual((data["model"], data["small_model"]), ("openai/gpt-6.1-terra", "openai/gpt-6-luna"))
        self.assertEqual(data["agent"]["scout"]["model"], "openai/gpt-6-luna")
        for target in ("codex", "aider", "litellm", "opencode"):
            code, out, _ = self.cli("--lang", "en", "models", "export", target)
            self.assertEqual(code, 0)
            self.assertIn("# Not verified: ", out)  # 확인하지 못한 형식은 주석으로 밝힌다


class TestModelsCheck(ModelsProject):
    def test_floor_deprecated_and_stale(self):
        self.write(".claude/agents/guard.md", "---\nname: guard\nmodel: haiku\n---\nbody\n")
        self.config(models={"agents": {"guard": "task/risky"}})
        code, findings = self.check_json()
        floor = [f for f in findings if f["id"] == "models.floor"]
        self.assertEqual([(f["level"], f["path"]) for f in floor], [("error", ".claude/agents/guard.md")])
        self.assertEqual(code, 1)
        self.write(".claude/agents/guard.md", "---\nname: guard\nmodel: claude-opus-5-5\neffort: medium\n---\nbody\n")
        code, findings = self.check_json()
        self.assertIn("models.floor", self.ids(findings))  # 같은 등급이라도 강도가 하한보다 낮다
        self.write(".claude/agents/guard.md", "---\nname: guard\nmodel: claude-opus-5-5\neffort: high\n---\nbody\n")
        code, findings = self.check_json()
        self.assertNotIn("models.floor", self.ids(findings))
        self.write(".claude/agents/guard.md", "---\nname: guard\nmodel: claude-sonnet-4-5-20250929\n---\nbody\n")
        code, findings = self.check_json()
        dep = [f for f in findings if f["id"] == "models.deprecated"]
        self.assertEqual([(f["level"], f["path"]) for f in dep], [("warn", ".claude/agents/guard.md")])
        self.write(".habitree/vendors.json", json.dumps({"vendors": {"anthropic": {"checked": "2020-01-01"}}}))
        code, findings = self.check_json()
        stale = [f for f in findings if f["id"] == "models.price-stale"]
        self.assertEqual([(f["level"], f["path"]) for f in stale], [("info", ".habitree/vendors.json")])
        self.write(".habitree/vendors.json", "{broken")
        code, findings = self.check_json()
        self.assertIn(("models.floor", ".habitree/vendors.json"), {(f["id"], f["path"]) for f in findings})
        code, out, err = self.cli("models", "check")
        self.assertEqual(code, 2)  # 대응표가 깨지면 명령은 오류로 멈춘다

    def test_models_check_command(self):
        code, out, err = self.cli("models", "check")
        self.assertEqual(code, 0, err)
        self.assertIn("claude-sonnet-4-5-20250929", out)


class TestVerify(ModelsProject):
    def setUp(self):
        super().setUp()
        self.config(verify={"ok": [sys.executable, "-c", "print('fine')"],
                            "bad": [sys.executable, "-c", "import sys; print('broken'); sys.exit(3)"]})

    def test_pass_and_fail(self):
        code, out, err = self.cli("verify", "ok")
        self.assertEqual(code, 0, out + err)
        self.assertIn("[합격] ok", out)
        code, data = self.json_cli("verify", "--json")
        self.assertEqual(code, 1)
        self.assertEqual([r["status"] for r in data["results"]], ["pass", "fail"])
        self.assertEqual((data["passed"], data["failed"], data["results"][1]["exit"]), (1, 1, 3))
        self.assertIn("broken", data["results"][1]["tail"])
        self.assertIsNone(data["recorded"])

    def test_task_records_outcome(self):
        self.cli("verify", "ok", "--task", "code")
        self.cli("verify", "bad", "--task", "code", "--cell", "high:medium")
        evs = read_events(Context.load(self.root))
        self.assertEqual([(e["result"], e["cell"], e["source"]) for e in evs],
                         [("pass", "mid:medium", "verify"), ("quality_fail", "high:medium", "verify")])
        self.assertTrue(all(e["at"].endswith("Z") for e in evs))

    def test_missing_program_and_timeout(self):
        self.config(verify={"ghost": ["habitree-no-such-program-xyz"],
                            "slow": {"cmd": [sys.executable, "-c", "import time; time.sleep(5)"], "timeout": 1}})
        code, data = self.json_cli("verify", "--json", "--task", "code")
        self.assertEqual(code, 1)
        self.assertEqual([r["status"] for r in data["results"]], ["error", "timeout"])
        self.assertIsNone(data["recorded"])  # 못 돌린 명령은 모델 품질이 아니다
        self.assertEqual(read_events(Context.load(self.root)), [])

    def test_errors(self):
        code, out, err = self.cli("verify", "nope")
        self.assertEqual(code, 2)
        self.config(verify={})
        code, out, err = self.cli("verify")
        self.assertEqual(code, 2)
        self.assertIn("verify", err)


if __name__ == "__main__":
    unittest.main()
