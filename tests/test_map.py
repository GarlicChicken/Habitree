"""코드 색인(map) 시험: 여러 언어 심볼, 증분 색인, 예산, 한국어 찾기, 중복, git 기록. / Code index tests."""
import json
import os
import shutil
import subprocess
import time
import unittest

from helpers import TempProject
from habitree.core.config import Context
from habitree.mapper import extract, index, langs, rank, search
from habitree.mapper.dupes import find_dupes

HAS_GIT = shutil.which("git") is not None


def syms(lang, text):
    return extract.extract(lang, text)["symbols"]


def by_name(items):
    """이름 → 처음 나온 심볼(struct와 impl처럼 이름이 겹치면 앞의 것). / First symbol per name."""
    out = {}
    for s in items:
        out.setdefault(s["name"], s)
    return out


PY = '''"""모듈 설명. / Module doc."""
import os

MAX_SIZE = 10


class Store:
    """저장소. / A store."""

    def load(self, path: str) -> dict:
        """파일을 읽는다."""
        return {}


def authenticate_user(name, token=None):
    """사용자 인증을 처리한다."""
    check = name.strip()
    if not token:
        return False
    return check == token
'''

TS = '''/** 설정을 읽는다. */
export function readConfig(path: string): Config {
  return JSON.parse(path);
}

export interface Config {
  name: string;
}

export const parseItem = async (raw: string) => {
  return raw.trim();
};

export const API_URL = "https://example.com";

// 사용자 서비스
export class UserService {
  private cache = new Map();

  constructor(db: Db) {
    this.db = db;
  }

  async findUser(id: number): Promise<User> {
    const found = lookup(id);
    if (found) {
      return found;
    }
    return null;
  }
}
'''

GO = '''package main

// Server serves requests.
type Server struct {
	addr string
}

// Start runs the server.
func (s *Server) Start(port int) error {
	return nil
}

func NewServer(addr string) *Server {
	return &Server{addr: addr}
}
'''

RUST = '''/// A point in space.
pub struct Point {
    x: f64,
}

pub trait Shape {
    fn area(&self) -> f64;
}

impl Point {
    pub fn new(x: f64) -> Self {
        Point { x }
    }
}

pub fn distance(a: &Point, b: &Point) -> f64 {
    (a.x - b.x).abs()
}
'''

JAVA = '''package com.example;

/** Billing logic. */
public class Billing {
    private final int rate = compute(3);

    public Billing(int rate) {
        this.rate = rate;
    }

    /** Total price. */
    public int total(int qty) {
        int x = helper(qty);
        return x * rate;
    }

    private static List<String> names() {
        return List.of();
    }
}
'''

RUBY = '''# Greets people.
class Greeter
  def initialize(name)
    @name = name
  end

  def greet?
    puts "hi"
  end
end
'''

SHELL = '''#!/bin/bash
# Deploy the app.
deploy() {
  echo "deploy"
}

function cleanup {
  rm -rf build
}
'''

C = '''#include <stdio.h>
#define MAX(a, b) ((a) > (b) ? (a) : (b))

struct node {
    int value;
};

/* Add two numbers. */
static int add_numbers(int a, int b) {
    if (a > b) {
        return a;
    }
    return a + b;
}
'''

MD = '''# 프로젝트

설명 문단.

## 설치 · Install

설치하는 법.

```bash
# 코드 안 제목은 제목이 아님
pip install x
```

## 쓰는 법

쓰는 법 문단.
'''


class TestLangs(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(langs.detect("src/a.py"), "Python")
        self.assertEqual(langs.detect("web/App.TSX"), "TypeScript")
        self.assertEqual(langs.detect("infra/main.tf.json"), "Terraform")
        self.assertEqual(langs.detect("Makefile"), "Makefile")
        self.assertEqual(langs.detect("x/Dockerfile"), "Dockerfile")
        self.assertEqual(langs.detect("bin/tool", b"#!/usr/bin/env python3\nprint(1)\n"), "Python")
        self.assertEqual(langs.detect("bin/run", b"#!/bin/bash\n"), "BASH")
        self.assertIsNone(langs.detect("notes.unknownext"))
        self.assertEqual(langs.detect("include/x.h"), "C Header")

    def test_count_code(self):
        lines = ["# c", "", "x = 1", "y = 2  # c"]
        self.assertEqual(langs.count_code(lines, "Python"), 2)
        self.assertEqual(langs.count_code(["/* a", "b */", "int x;"], "C"), 1)


class TestExtract(unittest.TestCase):
    def test_python_ast(self):
        ex = extract.extract("Python", PY)
        self.assertEqual(ex["extractor"], "ast")
        s = by_name(ex["symbols"])
        self.assertEqual(s["Store"]["kind"], "class")
        self.assertEqual(s["load"]["kind"], "method")
        self.assertEqual(s["load"]["parent"], "Store")
        self.assertEqual(s["load"]["sig"], "def load(self, path: str) -> dict")
        self.assertEqual(s["authenticate_user"]["doc"], "사용자 인증을 처리한다.")
        self.assertEqual(s["authenticate_user"]["end"], 20)
        self.assertIn("body", s["authenticate_user"])
        self.assertEqual(s["MAX_SIZE"]["kind"], "const")
        self.assertEqual(s["MAX_SIZE"]["sig"], "MAX_SIZE")  # 값은 싣지 않는다
        self.assertEqual(ex["doc"], "모듈 설명. / Module doc.")
        self.assertIn("strip", ex["refs"])

    def test_python_fallback(self):
        ex = extract.extract("Python", "def broken(:\n    pass\n\nclass Ok:\n    pass\n")
        self.assertEqual(ex["extractor"], "regex")
        self.assertIn("Ok", by_name(ex["symbols"]))

    def test_typescript(self):
        s = by_name(syms("TypeScript", TS))
        self.assertEqual(s["readConfig"]["kind"], "function")
        self.assertEqual(s["readConfig"]["doc"], "설정을 읽는다.")
        self.assertEqual(s["readConfig"]["sig"], "export function readConfig(path: string): Config")
        self.assertEqual(s["Config"]["kind"], "interface")
        self.assertEqual(s["parseItem"]["kind"], "function")
        self.assertEqual(s["API_URL"]["kind"], "const")
        self.assertNotIn("example.com", s["API_URL"]["sig"])
        self.assertEqual(s["UserService"]["kind"], "class")
        self.assertEqual(s["findUser"]["kind"], "method")
        self.assertEqual(s["findUser"]["parent"], "UserService")
        self.assertIn("constructor", s)
        self.assertNotIn("lookup", s)  # 몸통 안의 호출은 정의가 아니다
        self.assertEqual(s["UserService"]["end"], 31)

    def test_go_rust(self):
        g = by_name(syms("Go", GO))
        self.assertEqual(g["Server"]["kind"], "struct")
        self.assertEqual(g["Start"]["kind"], "method")
        self.assertEqual(g["Start"]["parent"], "Server")
        self.assertEqual(g["Start"]["doc"], "Start runs the server.")
        self.assertEqual(g["NewServer"]["kind"], "function")
        rust = syms("Rust", RUST)
        self.assertIn(("Point", "impl"), {(x["name"], x["kind"]) for x in rust})
        r = by_name(rust)
        self.assertEqual(r["Point"]["kind"], "struct")
        self.assertEqual(r["Point"]["doc"], "A point in space.")
        self.assertEqual(r["Shape"]["kind"], "trait")
        self.assertEqual(r["new"]["kind"], "method")
        self.assertEqual(r["new"]["parent"], "Point")
        self.assertEqual(r["distance"]["kind"], "function")

    def test_java_ruby_shell_c(self):
        j = by_name(syms("Java", JAVA))
        self.assertEqual(j["Billing"]["kind"], "class")
        self.assertEqual(j["total"]["kind"], "method")
        self.assertEqual(j["total"]["doc"], "Total price.")
        self.assertIn("names", j)
        self.assertNotIn("helper", j)
        self.assertNotIn("compute", j)
        rb = by_name(syms("Ruby", RUBY))
        self.assertEqual(rb["Greeter"]["end"], 10)
        self.assertEqual(rb["greet?"]["kind"], "method")
        sh = by_name(syms("BASH", SHELL))
        self.assertEqual(set(sh), {"deploy", "cleanup"})
        self.assertEqual(sh["deploy"]["doc"], "Deploy the app.")
        c = by_name(syms("C", C))
        self.assertEqual(c["MAX"]["kind"], "macro")
        self.assertEqual(c["node"]["kind"], "struct")
        self.assertEqual(c["add_numbers"]["kind"], "function")
        self.assertEqual(c["add_numbers"]["end"], 14)
        self.assertEqual(c["add_numbers"]["doc"], "Add two numbers.")

    def test_more_languages(self):
        self.assertIn("load", by_name(syms("Kotlin", "class Repo {\n    suspend fun load(id: Int): User {\n    }\n}\n")))
        self.assertIn("render", by_name(syms("Swift", "struct View {\n    func render() -> String {\n    }\n}\n")))
        self.assertIn("handle", by_name(syms("PHP", "<?php\nclass A {\n    public function handle($r) {\n    }\n}\n")))
        self.assertIn("Get-Item", by_name(syms("Powershell", "function Get-Item {\n}\n")))
        self.assertIn("users", by_name(syms("SQL", "CREATE TABLE IF NOT EXISTS users (\n id int\n);\n")))

    def test_markdown_sections(self):
        s = syms("Markdown", MD)
        names = [x["name"] for x in s]
        self.assertEqual(names, ["프로젝트", "설치 · Install", "쓰는 법"])
        install = s[1]
        self.assertEqual(install["doc"], "설치하는 법.")
        self.assertEqual(install["end"], 12)
        self.assertEqual(s[0]["end"], 16)


SECRET = "TOKEN=" + "x" * 20 + "\n"


class TestMapProject(TempProject):
    def setUp(self):
        super().setUp()
        self.write("src/한글 폴더/인증 모듈.py", PY)
        self.write("web/app.ts", TS)
        self.write("svc/main.go", GO)
        self.write("lib/greeter.rb", RUBY)
        self.write("docs/guide.md", MD)
        self.write("src/caller.py", "from 인증 import authenticate_user\n\n\ndef login(n):\n"
                                    "    return authenticate_user(n) or authenticate_user(n, 1)\n")
        self.write(".env", SECRET)
        self.write("keys/id_rsa", "-----BEGIN KEY-----\n")

    def ctx(self):
        return Context.load(self.root, "ko")

    def test_build_and_secrets(self):
        idx, st = index.build(self.ctx())
        files = idx["files"]
        self.assertIn("src/한글 폴더/인증 모듈.py", files)
        self.assertNotIn(".env", files)
        self.assertNotIn("keys/id_rsa", files)
        self.assertEqual(idx["excluded"]["secret"], 2)
        self.assertEqual(files["svc/main.go"]["lang"], "Go")
        self.assertEqual(files["web/app.ts"]["extractor"], "regex")
        self.assertTrue((self.root / ".habitree" / "state" / "map.json").exists())
        self.assertEqual((self.root / ".habitree" / "state" / ".gitignore").read_text(encoding="utf-8"), "*\n")
        dump = (self.root / ".habitree" / "state" / "map.json").read_text(encoding="utf-8")
        self.assertNotIn("x" * 20, dump)

    def test_incremental(self):
        ctx = self.ctx()
        _, st = index.build(ctx)
        self.assertEqual(st["read"], st["files"])
        _, st = index.build(ctx)
        self.assertEqual((st["read"], st["touched"], st["saved"]), (0, 0, False))
        self.write("svc/main.go", GO + "\nfunc Extra() {\n}\n")
        p = self.root / "lib" / "greeter.rb"
        future = time.time() + 100
        os.utime(p, (future, future))
        (self.root / "docs" / "guide.md").unlink()
        idx, st = index.build(ctx)
        self.assertEqual((st["read"], st["touched"], st["removed"]), (1, 1, 1))
        self.assertIn("Extra", by_name(idx["files"]["svc/main.go"]["symbols"]))
        full, _ = index.build(ctx, full=True)

        def strip(files):
            return {k: {a: b for a, b in v.items() if a != "mtime_ns"} for k, v in files.items()}
        self.assertEqual(strip(idx["files"]), strip(full["files"]))

    def test_show_budget(self):
        idx = index.ensure(self.ctx())
        for budget in (300, 800, 2000):
            text = rank.show(idx, None, budget, "ko")
            self.assertLessEqual(len(text), budget)
        text = rank.show(idx, None, 0, "ko")
        self.assertIn("authenticate_user", text)
        self.assertNotIn("예산 때문에", text)
        entries, _, _ = rank.rank(idx)
        self.assertEqual(entries[0][2]["name"], "authenticate_user")  # 다른 파일이 부르는 정의가 위로
        focused = rank.show(idx, ["svc"], 400, "en")
        self.assertIn("svc/main.go", focused)

    def test_find_korean_and_names(self):
        idx = index.ensure(self.ctx())

        def top(q, n=1):
            hits = search.Searcher(idx).search(q)
            names = [h[2]["name"] for h in hits[:n]]
            return names[0] if n == 1 and names else names
        self.assertIn("authenticate_user", top("인증", 2))  # 파일 '인증 모듈.py'와 함께 위에
        self.assertIn("인증 모듈.py", top("인증", 2))
        self.assertEqual(top("인증을"), "authenticate_user")
        self.assertEqual(top("auth"), "authenticate_user")
        self.assertEqual(top("read config"), "readConfig")
        self.assertEqual(top("readConfig"), "readConfig")
        self.assertEqual(top("users"), "UserService")
        self.assertEqual(top("설치"), "설치 · Install")
        data, text = search.find(self.root, idx, "인증", level=2, limit=3, budget=4000, lang="ko")
        self.assertEqual(data["status"], "ok")
        self.assertIn("def authenticate_user(name, token=None)", text)
        self.assertIn("사용자 인증을 처리한다.", text)
        data, text = search.find(self.root, idx, "authenticate", level=3, limit=1, budget=4000, lang="ko")
        self.assertIn("return check == token", text)
        self.assertIn("return check == token", data["hits"][0]["body"])
        data, text = search.find(self.root, idx, "존재하지않는말", lang="ko")
        self.assertEqual(data["status"], "absent")
        self.assertIn("못 찾음", text)
        self.assertIn("다음에 할 일", text)

    def test_cli(self):
        code, out, err = self.cli("map", "build")
        self.assertEqual(code, 0, err)
        self.assertIn("색인을 만들었습니다", out)
        code, out, _ = self.cli("map", "find", "인증을", "--json")
        data = json.loads(out)
        self.assertEqual(data["hits"][0]["name"], "authenticate_user")
        self.assertEqual(data["hits"][0]["precision"], "exact")
        code, out, _ = self.cli("map", "show", "--budget", "500")
        self.assertEqual(code, 0)
        self.assertLessEqual(len(out.rstrip("\n")), 500)
        code, out, _ = self.cli("map", "stats")
        self.assertIn("Python", out)
        self.assertIn("비밀일 수 있어 뺌 2", out)
        code, out, _ = self.cli("--lang", "en", "map", "churn")
        self.assertEqual(code, 0)
        self.assertIn("Skipped", out)

    def test_dupes(self):
        body = "".join(f"    total = total + {i}\n" for i in range(8))
        self.write("a.py", f"def first(x):\n    total = 0\n{body}    return total\n")
        self.write("b.py", f"def second(y):\n    total = 0\n{body}    return total\n")
        self.write("c.js", "function one() {\n" + "".join(f"  run({i});\n" for i in range(7)) + "}\n"
                   + "function two() {\n" + "".join(f"  run({i});\n" for i in range(7)) + "  done();\n}\n")
        idx = index.ensure(self.ctx())
        res = find_dupes(self.root, idx, 6)
        groups = [{s["name"] for _, s in g} for g in res["same_body"]]
        self.assertIn({"first", "second"}, groups)
        pairs = {(c[0], c[3]) for c in res["clones"]}
        self.assertIn(("a.py", "b.py"), pairs)
        self.assertIn(("c.js", "c.js"), pairs)
        code, out, _ = self.cli("map", "dupes")
        self.assertIn("같은 몸통", out)


def git(root, *args, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, env=env)


@unittest.skipUnless(HAS_GIT, "git이 없음 / git not available")
class TestGitHistory(TempProject):
    def setUp(self):
        super().setUp()
        self.init()
        self.write("src/README.md", "# src\n\n- 마지막 갱신: 2026-10-28\n\n[앱](app.py) [웹](https://x.y)\n")
        self.write("src/app.py", "def main():\n    return 1\n")
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "one", date="2026-01-01T00:00:00Z")

    def test_stale_code_and_churn(self):
        code, findings = self.check_json("--only", "docs.stale-code")
        self.assertEqual(findings, [])
        self.write("src/app.py", "def main():\n    return 2\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "two", date="2026-02-01T00:00:00Z")
        code, findings = self.check_json("--only", "docs.stale-code")
        self.assertEqual([(f["id"], f["path"], f["line"]) for f in findings], [("docs.stale-code", "src/README.md", 5)])
        self.assertEqual(code, 0)  # 알림만
        self.write("src/README.md", self.read("src/README.md") + "\n갱신함\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "three", date="2026-03-01T00:00:00Z")
        code, findings = self.check_json("--only", "docs.stale-code")
        self.assertEqual(findings, [])
        code, out, _ = self.cli("map", "churn", "--json")
        rows = {r["path"]: r for r in json.loads(out)}
        self.assertEqual(rows["src/app.py"]["changes"], 2)
        self.assertEqual(rows["src/app.py"]["score"], 2 * 2)


if __name__ == "__main__":
    unittest.main()
