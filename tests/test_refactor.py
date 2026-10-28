"""리팩토링 제안(refactor) 시험: 몰림·중복·흩어짐·덜어내기, 규모 판단, JSON 단계, 규칙 기준값, git 유무.
/ Refactoring advice tests: detection kinds, scale choice, JSON steps, rule thresholds, with and without git."""
import json
import os
import shutil
import subprocess
import unittest

from helpers import TempProject

HAS_GIT = shutil.which("git") is not None
EM_DASH = chr(0x2014)  # 문서·문구에 쓰지 않는 글자 / a character the texts never use


def git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, env=dict(os.environ))


def calc_part(i):
    return (f"def calc_part_{i}(x):\n    \"\"\"조각 {i}.\"\"\"\n    total = x + {i}\n    total = total * 2\n"
            f"    total = total - 1\n    if total > 10:\n        total = total // 2\n    return total\n\n\n")


def total_fn(name):
    return (f"def {name}(items):\n    \"\"\"합계.\"\"\"\n    total = 0\n    for item in items:\n        if item > 0:\n"
            f"            total += item * 2\n        else:\n            total -= item\n    return total\n")


CLONE = ("  const x = a.map(v => v * 2);\n  const y = x.filter(v => v > 3);\n  const z = y.reduce((s, v) => s + v, 0);\n"
         "  console.log(\"sum\", z);\n  const w = z * 10;\n  console.log(\"ten\", w);\n  const q = w - 7;\n"
         "  console.log(\"q\", q);\n")


class Base(TempProject):
    def advise(self, *args):
        code, out, err = self.cli("refactor", "--json", "--top", "50", *args)
        self.assertEqual(code, 0, out + err)
        return json.loads(out)

    def of(self, data, kind, sub=None):
        return [c for c in data["candidates"] if c["kind"] == kind and (sub is None or c["sub"] == sub)]

    def verify_cfg(self):
        self.write(".habitree/config.json", json.dumps({"version": 1, "lang": "ko",
                                                       "verify": {"test": ["python", "-c", "pass"]}}))


class TestConcentration(Base):
    def setUp(self):
        super().setUp()
        for i in range(6):
            self.write(f"한글 폴더/작은_{i}.py", f"from big import calc_part_{i}\n\n\ndef small_{i}(x):\n"
                                              f"    return calc_part_{i}(x) + 1\n")
        big = "".join(calc_part(i) for i in range(36))
        big += "def orphan_helper(y):\n    value = y\n    value += 1\n    return value\n\n\n"
        big += "PARTS = [" + ", ".join(f"calc_part_{i}" for i in range(36)) + "]\n"
        self.write("src/big file.py", big)
        body = "".join(f"  out.push(items[{i}]);\n" for i in range(60))
        self.write("web/app.js", "// 화면을 그린다\nexport function render(items) {\n  let out = [];\n" + body +
                   "  return out;\n}\n\nexport function small(a) {\n  return a + 1;\n}\n")

    def test_big_file_long_function_and_trim_first(self):
        data = self.advise()
        self.assertTrue((self.root / ".habitree/state/map.json").exists())     # 색인이 없으면 먼저 만든다
        big = [c for c in self.of(data, "concentration", "file") if c["files"] == ["src/big file.py"]][0]
        self.assertGreaterEqual(big["facts"]["lines"], 300)
        self.assertIn("calc_*", big["facts"]["seams"])                        # 있는 경계
        js = [c for c in self.of(data, "concentration", "function") if c["files"] == ["web/app.js"]][0]
        self.assertEqual(js["facts"]["funcs"][0][0], "render")                # 패턴 언어도 함수 길이(대략)
        self.assertGreaterEqual(js["facts"]["funcs"][0][1], 60)
        steps = [s["do"] for s in big["steps"]]
        self.assertIn("안전망", steps[0])                                       # 검증 수단이 없으면 첫 단계
        self.assertIn("orphan_helper", steps[1])                              # 덜어내기가 나누기보다 먼저
        self.assertIn("calc_*", steps[2])
        self.assertEqual(big["mode"], "mini")
        self.assertEqual(set(big["reasons"]), {"no_verify", "no_tests", "many_users"})  # 작은 파일 6곳이 씀
        self.assertFalse(self.of(data, "simplify", "unused"))                 # 몰림 후보에 붙었으니 따로 내지 않는다

    def test_thresholds_come_from_rules(self):
        self.init()
        self.assertTrue(self.of(self.advise(), "concentration"))
        from habitree.core.ruledb import RuleDB  # 꾸러미 규칙은 패키지에서 읽고, 고치면 프로젝트 DB에 남는다
        db = RuleDB.load(self.root / ".habitree/rules.json")
        db.find("code.structure.concentration")["detect"]["params"].update(
            min_file_lines=5000, min_func_lines=500, min_symbols=500)
        db.save()
        self.assertIn("code.structure.concentration", self.read(".habitree/rules.json"))
        self.assertFalse(self.of(self.advise(), "concentration"))
        code, out, err = self.cli("rules", "pause", "code.structure.fragmentation", "--why", "시험")
        self.assertEqual(code, 0, out + err)
        data = self.advise()
        self.assertFalse(self.of(data, "fragmentation") + self.of(data, "simplify"))

    def test_focus_and_text_output(self):
        data = self.advise("--focus", "web/app.js")
        self.assertEqual({tuple(c["files"]) for c in data["candidates"]}, {("web/app.js",)})
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file() and ".habitree" not in p.parts}
        code, out, _ = self.cli("refactor")
        self.assertEqual(code, 0)
        self.assertLessEqual(sum(1 for line in out.splitlines() if line[:1].isdigit()), 3)  # 기본 3개
        self.assertIn("[몰림]", out)
        self.assertIn("→ habitree verify", out)
        self.assertNotIn(EM_DASH, out)
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file() and ".habitree" not in p.parts}
        self.assertEqual(before, after)                                       # 제안만 하고 고치지 않는다
        code, out, _ = self.cli("--lang", "en", "refactor", "--top", "1")
        self.assertIn("[Concentration]", out)
        self.assertIn("Suggested: ", out)
        self.assertNotIn("권함", out)


class TestDuplicationAndScale(Base):
    def setUp(self):
        super().setUp()
        self.write("가 폴더/a.py", total_fn("alpha_total"))
        self.write("b/b.py", total_fn("beta_total"))
        self.write("c d/c.py", total_fn("gamma_total"))
        self.write("web 1/first.js", "function first(a) {\n" + CLONE + "  return q;\n}\n")
        self.write("web 2/second.js", "function second(b) {\n  const a = b + 1;\n" + CLONE + "  return q + 1;\n}\n")

    def safety_net(self):
        self.verify_cfg()
        self.write("tests/test_totals.py", "from a import alpha_total\nfrom b import beta_total\n"
                                           "from c import gamma_total\n\n\ndef test_all():\n"
                                           "    assert alpha_total([1]) == beta_total([1]) == gamma_total([1])\n")

    def test_same_body_and_clone(self):
        data = self.advise()
        same = self.of(data, "duplication", "same_body")
        self.assertEqual(len(same), 1)
        self.assertEqual(same[0]["files"], ["b/b.py", "c d/c.py", "가 폴더/a.py"])
        self.assertEqual(same[0]["facts"]["k"], 3)
        clone = self.of(data, "duplication", "clone")
        self.assertEqual(clone[0]["files"], ["web 1/first.js", "web 2/second.js"])
        self.assertGreaterEqual(clone[0]["facts"]["lines"], 6)
        self.assertIn("새 함수 없이", " ".join(s["do"] for s in same[0]["steps"]))  # 남길 곳을 부르게(더하지 않기)

    def test_no_safety_net_is_mini_and_starts_with_it(self):
        same = self.of(self.advise(), "duplication", "same_body")[0]
        self.assertEqual(same["mode"], "mini")
        self.assertIn("no_verify", same["reasons"])
        self.assertIn("verify", same["steps"][0]["do"])

    def test_safety_net_and_few_users_is_bold(self):
        self.safety_net()
        same = self.of(self.advise(), "duplication", "same_body")[0]
        self.assertEqual(same["mode"], "bold")
        self.assertEqual(same["reasons"], ["wide"])
        self.assertEqual(len(same["steps"]), 4)                               # 확인 → 바깥 고정 → 안쪽 → 옛 길
        self.assertTrue(all(s["check"] == "habitree verify" for s in same["steps"]))
        self.assertIn("바깥 모양", same["steps"][1]["do"])
        self.assertIn("옛 길", same["steps"][3]["do"])

    def test_many_users_turns_bold_into_mini(self):
        self.safety_net()
        for i in range(6):
            self.write(f"users/u{i}.py", f"from a import alpha_total\n\nVALUE_{i} = alpha_total([{i}])\n")
        same = self.of(self.advise(), "duplication", "same_body")[0]
        self.assertEqual(same["mode"], "mini")
        self.assertIn("many_users", same["reasons"])

    def test_mode_flag(self):
        same = self.of(self.advise("--mode", "bold"), "duplication", "same_body")[0]
        self.assertEqual(same["mode"], "bold")
        self.assertEqual(same["reasons"][0], "forced")
        self.assertIn("안전망", same["steps"][0]["do"])                       # 강제해도 안전망이 먼저


class TestFragmentation(Base):
    def setUp(self):
        super().setUp()
        self.write("api 폴더/money.py", "def format_price(value):\n    return f\"{value:,} 원\"\n")
        self.write("web/money.js", "function format_price(v) {\n  return v.toFixed(2) + \" KRW\";\n}\n")
        self.write("core/one.py", "from util.two import two_helper\n\n\ndef one_helper(x):\n    return x + 1\n\n\n"
                                  "def one_main(x):\n    return two_helper(x) * 2\n")
        self.write("util/two.py", "from core.one import one_helper\n\n\ndef two_helper(x):\n"
                                  "    return one_helper(x) - 1\n")
        self.write("front/view.js", "function draw() {\n  return 1;\n}\n")
        self.write("back/api.py", "def serve():\n    return 1\n")

    def test_same_name_and_mutual_without_git(self):
        data = self.advise()
        self.assertFalse(data["git"])
        same = self.of(data, "fragmentation", "same_name")
        self.assertEqual(same[0]["files"], ["api 폴더/money.py", "web/money.js"])
        self.assertEqual(same[0]["level"], "info")                            # 근거가 약해 정보 등급
        mutual = self.of(data, "fragmentation", "mutual")
        self.assertEqual(mutual[0]["files"], ["core/one.py", "util/two.py"])
        self.assertFalse(self.of(data, "fragmentation", "coupling"))
        code, out, _ = self.cli("refactor", "--top", "10")
        self.assertIn("흩어짐 · 알림", out)
        self.assertIn("git: 없음", out)

    @unittest.skipUnless(HAS_GIT, "git이 없음 / git not available")
    def test_coupling_with_git(self):
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "start")
        for i in range(5):
            self.write("front/view.js", self.read("front/view.js") + f"// {i}\n")
            self.write("back/api.py", self.read("back/api.py") + f"# {i}\n")
            git(self.root, "add", "-A")
            git(self.root, "commit", "-q", "-m", f"change {i}")
        data = self.advise()
        self.assertTrue(data["git"])
        pair = self.of(data, "fragmentation", "coupling")[0]
        self.assertEqual(pair["files"], ["back/api.py", "front/view.js"])
        self.assertEqual(pair["facts"]["pairs"][0][2:], [6, 100])              # 함께 6번, 100%
        self.assertIn("busy", pair["reasons"])                                # 최근 자주 바뀜 → 작은 단계
        self.assertEqual(pair["mode"], "mini")


class TestSimplify(Base):
    def setUp(self):
        super().setUp()
        self.write("lib 폴더/tools.py", "def used_one(x):\n    return x * 3\n\n\ndef never_called(y):\n"
                                       "    total = y\n    total += 1\n    return total\n")
        self.write("main.py", "from tools import used_one\n\nprint(used_one(2))\n")
        self.write("scripts/old_job.py", "import sys\n\nprint(sys.argv)\n")
        self.write("scripts/new_job.py", "import sys\n\nprint(len(sys.argv))\n")
        self.write("README.md", "# 시험\n\n`python scripts/new_job.py`로 돌린다.\n")
        self.write("svc/store.py", "def load_user_record(uid):\n    \"\"\"사용자를 읽는다.\"\"\"\n"
                                   "    record = {\"id\": uid}\n    record[\"name\"] = \"n\"\n    return record\n")
        self.write("svc/wrap.py", "from svc.store import load_user_record\n\n\ndef fetch_user(uid):\n"
                                  "    return load_user_record(uid)\n\n\ndef is_ready(x):\n    return bool(x)\n")
        self.write("app/view.py", "from svc.wrap import fetch_user, is_ready\nfrom svc.store import load_user_record\n"
                                  "from bits.a1 import aye_one\n\n\n"
                                  "def show_user(uid):\n    if is_ready(uid):\n        return fetch_user(uid)\n"
                                  "    return load_user_record(aye_one())\n")
        self.write("bits/a1.py", "from b2 import bee_two\n\n\ndef aye_one():\n    return bee_two() + 1\n")
        self.write("bits/b2.py", "from c3 import cee_three\n\n\ndef bee_two():\n    return cee_three() + 2\n")
        self.write("bits/c3.py", "def cee_three():\n    return 3\n")

    def test_removals(self):
        data = self.advise()
        simp = self.of(data, "simplify")
        self.assertTrue(simp and all(c["level"] == "info" for c in simp))
        unused = {c["facts"]["file"]: c["facts"]["names"] for c in self.of(data, "simplify", "unused")}
        self.assertEqual(unused["lib 폴더/tools.py"], ["never_called"])
        files = [c["files"] for c in self.of(data, "simplify", "unused_file")]
        self.assertIn(["scripts/old_job.py"], files)
        self.assertNotIn(["scripts/new_job.py"], files)                       # 문서가 부르는 스크립트는 남긴다
        self.assertNotIn(["main.py"], files)                                  # 진입점은 지우기 후보가 아니다
        wrap = [c for c in self.of(data, "simplify", "wrapper") if c["facts"]["file"] == "svc/wrap.py"][0]
        self.assertEqual(wrap["facts"]["names"], ["fetch_user"])               # 내장 함수만 부르는 is_ready는 아님
        tiny = self.of(data, "simplify", "tiny")[0]
        self.assertEqual(tiny["files"], ["bits/a1.py", "bits/b2.py", "bits/c3.py"])
        dead = [c for c in self.of(data, "simplify", "unused_file") if c["files"] == ["scripts/old_job.py"]][0]
        self.assertIn("git grep", dead["steps"][-2]["do"])
        self.assertNotIn("no_tests", dead["reasons"])                         # 지울 코드에 시험을 쓰라고 하지 않는다

    def test_json_steps_shape(self):
        data = self.advise()
        self.assertEqual(set(data), {"verify", "git", "total", "candidates"})
        for c in data["candidates"]:
            self.assertEqual(set(c), {"kind", "sub", "level", "rule", "files", "facts", "mode", "steps", "why", "reasons"})
            self.assertIn(c["mode"], ("mini", "bold"))
            self.assertTrue(c["rule"].startswith("code.structure."))
            for s in c["steps"]:
                self.assertEqual(set(s), {"do", "files", "check"})
            if c["mode"] == "mini":
                self.assertIn("habitree refactor --focus", c["steps"][-1]["do"])


class TestPacks(unittest.TestCase):
    def test_base_rules_and_work_links(self):
        from habitree.core.ruledb import load_pack
        base = load_pack("base")
        rules = {r["id"]: r for r in base["rules"] if r["id"].startswith("code.structure.") and r.get("detect")}
        self.assertEqual(set(rules), {"code.structure.concentration", "code.structure.duplication",
                                      "code.structure.fragmentation"})
        for r in rules.values():
            self.assertEqual(r["detect"]["event"], "refactor")                # 훅에서는 돌지 않는다
            self.assertIsInstance(r["detect"]["threshold"], int)
            for key in ("rule", "why"):
                self.assertEqual(set(r[key]), {"ko", "en"})
            for key in ("ai", "user"):
                self.assertEqual(set(r["message"][key]), {"ko", "en"})
            self.assertNotIn(EM_DASH, json.dumps(r, ensure_ascii=False))
        self.assertEqual(rules["code.structure.fragmentation"]["detect"]["severity"], "info")
        work = {r["id"]: r for r in load_pack("work")["rules"]}
        for rid in ("code.structure.file-growth", "code.structure.copy-block", "work.loop.small-edits"):
            self.assertIn("habitree refactor --focus", work[rid]["message"]["suggest"][-1]["ko"])


if __name__ == "__main__":
    unittest.main()
