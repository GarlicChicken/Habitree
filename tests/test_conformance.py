"""적합성 시험: conformance/<명령>/<사례>/project를 돌려 expected.json과 맞춘다.
다른 언어로 만든 엔진도 같은 사례를 통과해야 호환된다(docs/spec/conformance.md).
/ Conformance: run each case and compare with expected.json. Any implementation must pass these."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, run_cli

CASES = ROOT / "conformance"


def findings_key(items):
    return sorted({(f["id"], f["path"]) for f in items})


class TestConformance(unittest.TestCase):
    def test_check_cases(self):
        cases = sorted(p for p in (CASES / "check").iterdir() if p.is_dir())
        self.assertGreater(len(cases), 0)
        for case in cases:
            with self.subTest(case=case.name):
                expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
                tmp = Path(tempfile.mkdtemp(prefix="habitree-conf-"))
                try:
                    proj = tmp / "project"
                    shutil.copytree(case / "project", proj)
                    code, out, err = run_cli("-C", str(proj), "--lang", "en", "check", "--json")
                    data = json.loads(out)
                    self.assertEqual(findings_key(data["findings"]), findings_key(expected["findings"]),
                                     json.dumps(data["findings"], ensure_ascii=False, indent=1))
                    self.assertEqual(code, expected["exit"])
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
