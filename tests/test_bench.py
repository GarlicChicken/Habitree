"""bench 시험: fake 실행기로 run → report 끝까지, 계획 보기, 결과 읽기, 예제 과제. 실제 claude는 돌리지 않는다.
/ bench tests with the fake runner; the real claude runner is never started."""
import json
import shutil
import subprocess
import sys
import unittest
from argparse import Namespace
from pathlib import Path

from helpers import ROOT, TempProject
from habitree.commands import bench
from habitree.sessions import claude

CHECK = "import pathlib, sys; sys.exit(0 if pathlib.Path('done.txt').exists() else 1)"


def out(tokens, cost, turns):
    return {"type": "result", "subtype": "success", "is_error": False, "num_turns": turns, "duration_ms": 2000,
            "total_cost_usd": cost, "session_id": "x",
            "modelUsage": {"claude-sonnet-5-5": {"inputTokens": tokens, "outputTokens": 10, "cacheReadInputTokens": 0,
                                                 "cacheCreationInputTokens": 0, "costUSD": cost}}}


class TestBench(TempProject):
    def make_task(self):
        task = self.tmp / "tasks" / "done-file"
        (task / "project").mkdir(parents=True)
        (task / "project" / "README.md").write_text("# 시작\n", encoding="utf-8")
        (task / "fake" / "with").mkdir(parents=True)
        (task / "fake" / "with" / "done.txt").write_text("ok", encoding="utf-8")
        spec = {"prompt": {"ko": "done.txt를 만들어 줘", "en": "Create done.txt"}, "timeout": 60,
                "verify": [["{python}", "-c", CHECK]],
                "rules": [{"scope": "code", "aspect": "quality", "rule": "끝나면 done.txt를 만든다", "why": "채점"}],
                "fake": {"with": {"files": "fake/with", "outputs": [out(100, 0.01, 2), out(140, 0.03, 4)]},
                         "without": {"outputs": [out(200, 0.02, 3)]}}}
        (task / "task.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        return task

    def test_fake_run_and_report(self):
        task, res = self.make_task(), self.tmp / "res"
        code, text, err = self.cli("bench", "run", str(task), "--runner", "fake", "--reps", "2", "--out", str(res))
        self.assertEqual(code, 0, err)
        run = json.loads((res / "runs" / "with-1" / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(run["status"], "pass")
        self.assertIn("AGENTS.md", run["setup"])  # with 갈래에만 Habitree를 깐다
        self.assertEqual(json.loads((res / "runs" / "without-1" / "run.json").read_text(encoding="utf-8"))["setup"], [])
        plan = json.loads((res / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual((plan["runner"], plan["reps"], plan["order"]), ("fake", 2, "interleaved"))
        data = json.loads((res / "report.json").read_text(encoding="utf-8"))
        w, wo = data["arms"]["with"], data["arms"]["without"]
        self.assertEqual((w["pass_rate"], wo["pass_rate"]), (1.0, 0.0))
        self.assertEqual(w["metrics"]["tokens"], {"n": 2, "mean": 130, "sd": 28.2843})  # (110, 150)
        self.assertEqual(wo["metrics"]["tokens"]["sd"], 0)
        self.assertAlmostEqual(w["cost_per_pass"], 0.02)
        self.assertAlmostEqual(data["delta"]["tokens"], -0.3810, places=3)
        self.assertEqual(data["delta"]["pass_rate_points"], 1.0)
        self.assertIn("few_runs", data["warnings"])
        md = (res / "report.md").read_text(encoding="utf-8")
        self.assertIn("| with | 2 | 100% (2/2) |", md)
        self.assertIn("| Pass rate |", md)  # 한국어 표 뒤에 영어 표
        code, text, _ = self.cli("bench", "report", str(res), "--json")
        self.assertEqual(json.loads(text)["arms"]["without"]["runs"], 2)

    def test_lower_tokens_lower_pass_is_flagged(self):
        res = self.tmp / "r2"
        for arm, status, tokens in (("with", "fail", 50), ("without", "pass", 100)):
            for rep in (1, 2, 3):
                d = res / "runs" / f"{arm}-{rep}"
                d.mkdir(parents=True)
                (d / "run.json").write_text(json.dumps({"arm": arm, "rep": rep, "status": status,
                                                        "metrics": {"tokens": tokens, "cost_usd": 0.1}}),
                                            encoding="utf-8")
        data = bench.report(res)
        self.assertIn("fewer_tokens_lower_pass", data["warnings"])
        self.assertNotIn("few_runs", data["warnings"])

    def test_dry_run_writes_nothing(self):
        task, res = self.make_task(), self.tmp / "res"
        code, text, err = self.cli("bench", "run", str(task), "--runner", "claude", "--dry-run", "--out", str(res),
                                   "--max-budget-usd", "0.5")
        self.assertEqual(code, 0, err)
        self.assertFalse(res.exists())
        self.assertIn("--output-format json", text)
        self.assertIn("$3.00", text)  # 0.5 × 6번
        code, _, err = self.cli("bench", "run", str(task), "--runner", "claude", "--out", str(res))
        self.assertEqual(code, 2)  # --yes 없이는 돌지 않는다
        self.assertIn("--yes", err)
        self.assertFalse(res.exists())

    def test_claude_command_isolation(self):
        task = {"prompt": "hi", "allowed_tools": ["Read"], "max_turns": 5}
        args = Namespace(model="sonnet", max_budget_usd=1.0, isolation="bare")
        argv, env = bench.claude_command(task, "with", Path("w"), args, Path("r"))
        self.assertEqual(argv[1:5], ["-p", "hi", "--output-format", "json"])
        self.assertIn("--bare", argv)
        self.assertEqual(argv[argv.index("--append-system-prompt-file") + 1], str(Path("w") / "AGENTS.md"))
        self.assertNotIn("--append-system-prompt-file", bench.claude_command(task, "without", Path("w"), args,
                                                                              Path("r"))[0])
        args.isolation = "config-dir"
        argv, env = bench.claude_command(task, "with", Path("w"), args, Path("r"))
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], str(Path("r") / "claude-home"))
        self.assertNotIn("--bare", argv)

    def test_parse_result_defensive(self):
        m = bench.parse_result(json.dumps(out(100, 0.5, 3)))
        self.assertEqual((m["tokens"], m["cost_usd"], m["turns"], m["token_source"]), (110, 0.5, 3, "modelUsage"))
        stream = "\n".join([json.dumps({"type": "system", "subtype": "init"}),
                            json.dumps({"type": "result", "num_turns": 1, "usage": {"input_tokens": 7,
                                                                                    "output_tokens": 3}})])
        m = bench.parse_result(stream)
        self.assertEqual((m["tokens"], m["token_source"], m["cost_usd"]), (10, "usage", None))
        self.assertIn("total_cost_usd", m["missing"])
        self.assertEqual(bench.parse_result("not json"), {"parsed": False})

    def test_recount_from_transcript(self):
        work = self.tmp / "작업 폴더"
        folder = self.tmp / "cc" / "projects" / claude.encode_dir_name(work)
        folder.mkdir(parents=True)
        lines = [{"type": "assistant", "uuid": f"a{i}", "sessionId": "sid1", "requestId": "r1", "cwd": str(work),
                  "message": {"id": "m1", "model": "claude-sonnet-5-5", "content": [],
                              "usage": {"input_tokens": 10, "output_tokens": out_, "cache_read_input_tokens": 5,
                                        "cache_creation_input_tokens": 0}}} for i, out_ in enumerate((1, 9))]
        (folder / "sid1.jsonl").write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
        t = bench.recount("sid1", work, self.tmp / "cc")
        self.assertEqual((t["requests"], t["input"], t["output"], t["cache_read"]), (1, 10, 9, 5))
        self.assertIsNone(bench.recount("nope", work, self.tmp / "cc"))


class TestExampleTasks(TempProject):
    """예제 과제: 시작 상태로는 떨어지고, 맞는 풀이면 붙는다(채점 스크립트가 맞는지). / Graders are sound."""

    def grade(self, name, files):
        task_dir, task = bench.load_task(Namespace(root=ROOT), name)
        work = self.tmp / "work"
        shutil.copytree(str(task_dir / "project"), str(work))
        results = []
        for content in (None, files):
            for rel, text in (content or {}).items():
                (work / rel).write_text(text, encoding="utf-8")
            codes = [subprocess.run([bench._sub(a, task_dir) for a in v], cwd=str(work), capture_output=True).returncode
                     for v in task["verify"]]
            results.append(all(c == 0 for c in codes))
        return results

    def test_reuse_helper(self):
        good = ("from textkit import slugify\n\n\ndef export_body(title, body):\n"
                "    return f\"# {title}\\n\\n{body.strip()}\\n\"\n\n\n"
                "def export_name(title, day):\n    return f\"{day.isoformat()}-{slugify(title)}.md\"\n")
        self.assertEqual(self.grade("reuse-helper", {"notes.py": good}), [False, True])

    @unittest.skipUnless(shutil.which("node"), "node 없음 / no node")
    def test_money_rules(self):
        good = ("const { roundWon } = require('./money');\n"
                "function total(items) { return items.reduce((s, i) => s + i.price * i.qty, 0); }\n"
                "function applyCoupon(sum, c) {\n"
                "  if (!c || !['percent', 'fixed'].includes(c.type) || c.value < 0) throw new RangeError('bad');\n"
                "  if (c.type === 'percent') { if (c.value > 100) throw new RangeError('bad');"
                " return roundWon(sum * (100 - c.value) / 100); }\n"
                "  return roundWon(Math.max(sum - c.value, 0));\n}\nmodule.exports = { total, applyCoupon };\n")
        self.assertEqual(self.grade("money-rules", {"cart.js": good}), [False, True])

    def test_tasks_are_small(self):
        for name in ("reuse-helper", "money-rules"):
            files = [p for p in (ROOT / "bench" / name).rglob("*") if p.is_file()]
            self.assertLessEqual(len(files), 6, name)


if __name__ == "__main__":
    unittest.main()
