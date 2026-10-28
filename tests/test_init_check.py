"""init·export·check 끝에서 끝까지. / init, export and check end to end."""
import json
import unicodedata
import unittest

from helpers import TempProject


class TestInit(TempProject):
    def test_fresh_project(self):
        self.write("src/app.py", "print(1)\n")
        (self.root / "문서 폴더").mkdir()
        out = self.init()
        self.assertIn("AGENTS.md", out)
        for rel in (".habitree/config.json", ".habitree/rules.json", ".habitree/RULES.md", "README.md", "LOG.md",
                    "AGENTS.md", "CLAUDE.md", ".gitignore"):
            self.assertTrue((self.root / rel).exists(), rel)
        self.assertTrue(self.read("CLAUDE.md").startswith("<!-- habitree:begin habitree-claude -->\n@AGENTS.md"))
        self.assertIn("문서%20폴더/", self.read("README.md"))
        code, findings = self.check_json()
        self.assertEqual(code, 0, findings)
        self.assertEqual(self.ids(findings), ["map.folder-readme"])

    def test_idempotent_and_keeps_user_text(self):
        self.write("README.md", "# 내 프로젝트\n\n사람이 쓴 글\n")
        self.write("CLAUDE.md", "내 Claude 메모\n")
        self.init()
        self.init()
        claude = self.read("CLAUDE.md")
        self.assertEqual(claude.count("habitree:begin habitree-claude"), 1)
        self.assertIn("내 Claude 메모", claude)
        self.assertIn("사람이 쓴 글", self.read("README.md"))
        self.assertEqual(self.read("AGENTS.md").count("<!-- habitree:begin habitree -->"), 1)

    def test_export_keeps_hand_edit(self):
        self.init()
        text = self.read("AGENTS.md").replace("1. 찾기", "1. 내가 고친 찾기")
        self.write("AGENTS.md", text)
        code, findings = self.check_json()
        self.assertIn("generated.edited", self.ids(findings))
        code, out, _ = self.cli("export")
        self.assertIn("직접 고친", out)
        self.assertIn("내가 고친 찾기", self.read("AGENTS.md"))
        code, out, _ = self.cli("export", "--force")
        self.assertNotIn("내가 고친 찾기", self.read("AGENTS.md"))

    def test_english(self):
        code, out, err = self.cli("init", "--lang", "en")
        self.assertEqual(code, 0, err)
        self.assertIn("Habitree work cycle", self.read("AGENTS.md"))
        self.assertEqual(json.loads(self.read(".habitree/config.json"))["lang"], "en")


class TestCheck(TempProject):
    def setUp(self):
        super().setUp()
        self.init()

    def test_links_and_anchors(self):
        self.write("docs/README.md", "# 문서\n\n- 마지막 갱신: 2026-10-28\n\n## 결정 기록\n\n[ok](#결정-기록) "
                                     "[bad](#없는-앵커) [miss](없는.md) [up](../README.md#지도--map) "
                                     "[web](https://x.y) `[code](no.md)`\n")
        readme = self.read("README.md").replace("| | |", "| [docs/](docs/) | 문서 |")
        self.write("README.md", readme)
        code, findings = self.check_json()
        bad = sorted(f["message"] for f in findings if f["id"] == "docs.link")
        self.assertEqual(len(bad), 2, findings)
        self.assertTrue(any("없는-앵커" in m for m in bad))
        self.assertTrue(any("없는.md" in m for m in bad))
        self.assertEqual(code, 1)

    def test_missing_folder_and_readme(self):
        (self.root / "newdir").mkdir()
        self.write("newdir/x.txt", "x")
        code, findings = self.check_json()
        self.assertIn("map.missing-folder", self.ids(findings))
        self.assertEqual(code, 1)

    def test_hidden_unicode_and_home_path(self):
        self.write("AGENTS.md", self.read("AGENTS.md") + "\n숨은‮글자\nC:\\Users\\someone\\x\n")
        code, findings = self.check_json()
        ids = self.ids(findings)
        self.assertIn("docs.hidden-unicode", ids)
        self.assertIn("docs.home-path", ids)

    def test_auto_rule_forbid(self):
        self.write("config.py", "KEY = 'sk-" + "a" * 30 + "'\n")
        code, findings = self.check_json()
        hits = [f for f in findings if f["id"] == "rules.auto.security.no-secrets"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["path"], "config.py")
        self.assertEqual(code, 1)
        code, findings = self.check_json("--no-auto")
        self.assertNotIn("rules.auto.security.no-secrets", self.ids(findings))

    def test_auto_rule_cmd_and_max_lines(self):
        db = json.loads(self.read(".habitree/rules.json"))
        db["rules"].append({"id": "code.structure.small-files", "scope": "code/structure", "aspect": "structure",
                            "level": "should", "rule": "파일은 5줄 이하", "why": "시험",
                            "check": {"type": "auto", "how": "줄 수", "run": {"max_lines": 5, "in": ["src/**/*.py"]}},
                            "feedback": [], "history": [], "status": "active"})
        self.write(".habitree/rules.json", json.dumps(db, ensure_ascii=False))
        self.write("src/big.py", "\n".join(["x = 1"] * 10))
        code, findings = self.check_json()
        hits = [f for f in findings if f["id"] == "rules.auto.code.structure.small-files"]
        self.assertEqual([h["level"] for h in hits], ["warn"])
        self.assertIn("rules.doc-stale", self.ids(findings))

    def test_rules_doc_stale_and_invalid(self):
        db = json.loads(self.read(".habitree/rules.json"))
        db["rules"][0]["scope"] = "없는/범위"
        self.write(".habitree/rules.json", json.dumps(db, ensure_ascii=False))
        code, findings = self.check_json()
        self.assertIn("rules.invalid", self.ids(findings))
        self.assertEqual(code, 1)

    def test_nfd_name_is_found_in_nfc(self):
        name = unicodedata.normalize("NFD", "문서.md")
        (self.root / name).write_text("# t\n", encoding="utf-8")
        self.write("README.md", self.read("README.md") + "\n[문서](문서.md)\n")
        code, findings = self.check_json("--only", "docs.link")
        self.assertEqual(findings, [])

    def test_custom_check(self):
        cfg = json.loads(self.read(".habitree/config.json"))
        import sys
        cfg["checks"] = {"custom": [{"id": "fail", "cmd": [sys.executable, "-c", "import sys; sys.exit(3)"]}]}
        self.write(".habitree/config.json", json.dumps(cfg))
        code, findings = self.check_json("--only", "custom")
        self.assertEqual(self.ids(findings), ["custom.fail"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
