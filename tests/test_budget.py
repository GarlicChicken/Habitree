"""무게 예산: Habitree가 쓰는 프로젝트에 지우는 무게와, AI가 매번 읽는 분량에 상한을 둔다.
기능이 늘어도 이 시험을 넘지 못하면 들어오지 않는다.
/ Weight budgets: limits on what Habitree adds to a project and on what the agent reads every session."""
import json
import os
import subprocess
import sys
import unittest

from helpers import SRC, TempProject
from habitree.core.packs import LIVE, load_pack

# 예산(바이트·글자). 늘려야 한다면 왜 늘어나는지 먼저 따진다.
FRESH_RULES_JSON = 32_000      # init 직후 .habitree/rules.json
FRESH_RULES_MD = 12_000        # init 직후 .habitree/RULES.md
AGENTS_MD = 3_000              # AGENTS.md 전체(생성 구역 포함)
CLAUDE_MD = 600                # CLAUDE.md 전체
SESSION_START = 2_000          # 세션 시작 때 AI에게 넣는 글
WARNING_TEXT = 300             # 경고 한 건(언어별)
SUGGEST_ITEM = 140             # 제안 한 줄
HEAVY_ON_HOOK = ("argparse", "tempfile", "hashlib", "difflib", "subprocess", "habitree.core.ruledb",
                 "habitree.core.schema", "importlib.resources", "habitree.mapper", "habitree.sessions")


class TestFootprint(TempProject):
    def test_fresh_init_is_small(self):
        self.write("src/app.py", "print(1)\n")
        self.init()
        sizes = {rel: (self.root / rel).stat().st_size for rel in
                 (".habitree/rules.json", ".habitree/RULES.md", "AGENTS.md", "CLAUDE.md")}
        self.assertLessEqual(sizes[".habitree/rules.json"], FRESH_RULES_JSON, sizes)
        self.assertLessEqual(sizes[".habitree/RULES.md"], FRESH_RULES_MD, sizes)
        self.assertLessEqual(sizes["AGENTS.md"], AGENTS_MD, sizes)
        self.assertLessEqual(sizes["CLAUDE.md"], CLAUDE_MD, sizes)
        db = json.loads(self.read(".habitree/rules.json"))
        for name in LIVE:  # 쓰지 않는 기능의 규칙은 옮겨 적지 않는다
            self.assertNotIn(name, db.get("packs", {}))

    def test_agents_md_stays_small_with_every_pack(self):
        self.init("--packs", "base", *LIVE)
        self.assertLessEqual((self.root / "AGENTS.md").stat().st_size, AGENTS_MD + 1_000)

    def test_session_start_text(self):
        self.init()
        from habitree.commands import hook
        out = hook.handle("SessionStart", {"session_id": "budget", "source": "startup", "cwd": str(self.root)},
                          str(self.root))
        text = ((out or {}).get("hookSpecificOutput") or {}).get("additionalContext", "")
        self.assertLessEqual(len(text), SESSION_START)


class TestTexts(unittest.TestCase):
    def test_warning_and_suggest_lengths(self):
        for name in LIVE:
            for r in load_pack(name)["rules"]:
                msg = r.get("message") or {}
                for key in ("user", "ai"):
                    for lang, text in (msg.get(key) or {}).items():
                        with self.subTest(rule=r["id"], key=key, lang=lang):
                            self.assertLessEqual(len(text), WARNING_TEXT)
                for item in msg.get("suggest") or []:
                    for lang, text in (item.items() if isinstance(item, dict) else [("", item)]):
                        with self.subTest(rule=r["id"], suggest=lang):
                            self.assertLessEqual(len(text), SUGGEST_ITEM)


class TestHookPath(unittest.TestCase):
    def test_hook_path_loads_no_heavy_modules(self):
        code = ("import sys, json; from habitree.cli import main; from habitree.commands import hook; "
                f"print(json.dumps([m for m in {list(HEAVY_ON_HOOK)!r} if any(k == m or k.startswith(m + '.') "
                "for k in sys.modules)]))")
        env = dict(os.environ, PYTHONPATH=str(SRC))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        self.assertEqual(json.loads(r.stdout.decode("utf-8")), [])


if __name__ == "__main__":
    unittest.main()
