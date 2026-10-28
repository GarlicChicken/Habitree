"""테스트 도우미: 임시 프로젝트와 CLI 실행. / Test helpers: temp projects and CLI runs."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from habitree.cli import main  # noqa: E402


def run_cli(*args):
    """(종료 코드, 표준 출력, 표준 오류). / (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(args))
        except SystemExit as e:  # argparse
            code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class TempProject(unittest.TestCase):
    """테스트마다 새 임시 프로젝트. / A fresh temp project per test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="habitree-test-"))
        self.root = self.tmp / "프로젝트 root"
        self.root.mkdir()
        self.old_lang = os.environ.get("HABITREE_LANG")
        os.environ["HABITREE_LANG"] = "ko"

    def tearDown(self):
        if self.old_lang is None:
            os.environ.pop("HABITREE_LANG", None)
        else:
            os.environ["HABITREE_LANG"] = self.old_lang
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        return p

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    def cli(self, *args):
        return run_cli("-C", str(self.root), *args)

    def init(self, *extra):
        code, out, err = self.cli("init", *extra)
        self.assertEqual(code, 0, out + err)
        return out

    def check_json(self, *extra):
        code, out, err = self.cli("check", "--json", *extra)
        data = json.loads(out)
        return code, data["findings"]

    def ids(self, findings):
        return sorted({f["id"] for f in findings})
