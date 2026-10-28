"""Claude Code 플러그인 파일, init --hooks, work 꾸러미 시험. / Plugin files, init --hooks and the work pack."""
import json
import os
import re
import unittest

from helpers import ROOT, TempProject
from habitree.core.ruledb import RuleDB, load_pack
from habitree.guard import install
from habitree.guard.detectors import DETECTORS

PLACEHOLDER = re.compile(r"\{(\w+)\}")
EM_DASH = chr(0x2014)  # 문서·문구에 쓰지 않는 글자 / a character the texts never use


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out = {}
    for line in (m.group(1) if m else "").split("\n"):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


class TestPluginFiles(unittest.TestCase):
    def test_manifest_and_marketplace(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], "habitree")
        self.assertRegex(plugin["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertTrue(market["name"] and market["owner"]["name"])
        self.assertEqual(market["plugins"][0]["name"], plugin["name"])
        self.assertEqual(market["plugins"][0]["source"], "./")

    def test_hooks_file_matches_install_definition(self):
        hooks = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(hooks, install.plugin_hooks_file())       # 원본은 install.py 하나
        for event, groups in hooks["hooks"].items():
            h = groups[0]["hooks"][0]
            self.assertEqual((h["type"], h["command"], h["args"]), ("command", "habitree", ["hook", event]))

    def test_skills(self):
        folder = ROOT / "skills"
        names = sorted(p.name for p in folder.iterdir() if p.is_dir())
        self.assertGreaterEqual(len(names), 2)
        for name in names:
            text = (folder / name / "SKILL.md").read_text(encoding="utf-8")
            fm = frontmatter(text)
            self.assertEqual(fm.get("name"), name)
            self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
            self.assertLessEqual(len(name), 64)
            self.assertTrue(0 < len(fm.get("description", "")) <= 1024, name)
            self.assertRegex(fm["description"], r"[가-힣]")          # 한국어로도 불리게
            self.assertRegex(fm["description"], r"\bUse when\b")    # 영어로도 불리게
            self.assertLessEqual(set(fm), {"name", "description", "license", "compatibility", "metadata",
                                           "allowed-tools"})          # 공용 필드만
            self.assertLess(text.count("\n"), 500)
            self.assertNotIn(EM_DASH, text)


class TestWorkPack(unittest.TestCase):
    def test_pack_rules(self):
        pack = load_pack("work")
        self.assertEqual(pack["version"], "0.6.0")
        db = RuleDB({"scopes": {}, "aspects": {}, "contexts": {}, "rules": []})
        db.merge_pack(load_pack("base"))
        db.merge_pack(pack)
        self.assertEqual(db.validate(), [])
        self.assertEqual(db.duplicate_pairs(), [])               # 기본 규칙과 같은 뜻으로 겹치지 않는다
        for r in pack["rules"]:
            d = r["detect"]
            self.assertIn(d["signal"], DETECTORS, r["id"])
            self.assertEqual(r["check"]["type"], "auto")
            self.assertIn(r.get("on_delegate"), ("skip", "ask", "nudge"))
            msg = r["message"]
            for key in ("ai", "user"):
                if key in msg:
                    self.assertEqual(set(msg[key]), {"ko", "en"}, r["id"])
                    self.assertEqual(set(PLACEHOLDER.findall(msg[key]["ko"])),
                                     set(PLACEHOLDER.findall(msg[key]["en"])), r["id"])
            for s in msg.get("suggest", []):
                self.assertEqual(set(s), {"ko", "en"})
            text = json.dumps(r, ensure_ascii=False)
            self.assertNotIn(EM_DASH, text)

    def test_one_rule_per_pattern(self):
        signals = [r["detect"]["signal"] for r in load_pack("work")["rules"]]
        self.assertEqual(len(signals), len(set(signals)))
        self.assertEqual(set(signals), set(DETECTORS))


class TestInitHooks(TempProject):
    def setUp(self):
        super().setUp()
        self.old_home = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}

    def tearDown(self):
        for k, v in self.old_home.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        super().tearDown()

    def test_merge_keeps_existing_and_is_idempotent(self):
        self.write(".claude/settings.json", json.dumps({
            "permissions": {"allow": ["Bash(npm test)"]},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "my-check"}]}]},
        }))
        out = self.init("--hooks")
        self.assertIn(".claude/settings.json", out)
        data = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(data["permissions"], {"allow": ["Bash(npm test)"]})
        pre = data["hooks"]["PreToolUse"]
        self.assertEqual(pre[0]["hooks"][0]["command"], "my-check")
        self.assertEqual(pre[1]["hooks"][0], install.handler("PreToolUse", 10))
        self.assertEqual(set(data["hooks"]), {e for e, _ in install.EVENTS})
        self.init("--hooks")
        again = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(again, data)                            # 두 번 넣지 않는다

    def test_without_flag_no_settings(self):
        self.init()
        self.assertFalse((self.root / ".claude/settings.json").exists())

    def test_refuses_user_global_settings(self):
        os.environ["HOME"] = str(self.root)
        os.environ["USERPROFILE"] = str(self.root)
        code, out, err = self.cli("init", "--hooks")
        self.assertEqual(code, 2)
        self.assertIn("전역", err)
        self.assertFalse((self.root / ".claude/settings.json").exists())

    def test_init_adds_work_pack(self):
        self.init()
        db = json.loads(self.read(".habitree/rules.json"))
        self.assertIn("work", db["packs"])
        self.assertIn("work.loop.same-call", self.read(".habitree/RULES.md"))


if __name__ == "__main__":
    unittest.main()
