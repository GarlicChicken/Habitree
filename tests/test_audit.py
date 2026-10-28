"""세션 기록 읽기와 audit 시험. 실제 사용자 홈의 기록은 읽지 않는다(경로를 넣어 준다).
/ Session parsing and audit tests; never reads the real home folder."""
import itertools
import json
import unittest
from pathlib import Path

from helpers import ROOT, TempProject
from habitree.core import vendors
from habitree.core.ruledb import RuleDB, load_pack
from habitree.sessions import claude, signals
from habitree.sessions.model import norm_path, read_only_shell, show_path, within
from habitree.sessions.usage import Pricer, summarize

FIX = ROOT / "tests" / "fixtures" / "sessions" / "claude"
WIN = "C:\\work\\한글 프로젝트"
POSIX = "/home/dev/한글 프로젝트"
SEQ = itertools.count(1)


def pricer():
    return Pricer(vendors.bundled())


class TestPaths(unittest.TestCase):
    def test_encode_and_match(self):
        self.assertEqual(claude.encode_dir_name(WIN), "C--work--------")
        self.assertEqual(claude.encode_dir_name(POSIX), "-home-dev--------")
        names = [d.name for d in claude.candidate_dirs(FIX / "projects", WIN)]
        self.assertEqual(sorted(names), ["C--work--------", "C--work-----------------"])  # NFC와 NFD 둘 다
        self.assertEqual([d.name for d in claude.candidate_dirs(FIX / "projects", POSIX)], ["-home-dev--------"])

    def test_within_any_os(self):
        self.assertTrue(within("c:/WORK/한글 프로젝트/src", WIN))
        self.assertTrue(within(WIN + "\\", WIN))
        self.assertFalse(within("C:\\work\\한글 프로젝트-old", WIN))
        self.assertTrue(within(POSIX + "/a", POSIX))
        self.assertFalse(within("/home/dev/한글 프로젝트2", POSIX))
        self.assertFalse(within("/HOME/dev/한글 프로젝트", POSIX))  # POSIX는 대소문자를 가린다
        self.assertEqual(norm_path("C:\\a\\\\b\\"), "c:/a/b")
        self.assertEqual(show_path(WIN + "\\src\\app.py", WIN), "src/app.py")
        self.assertEqual(show_path("D:\\secret\\x.txt", WIN), "<out>/x.txt")

    def test_read_only_shell(self):
        self.assertTrue(read_only_shell("git log --oneline | head -5"))
        self.assertTrue(read_only_shell("Get-Content a.txt"))
        self.assertFalse(read_only_shell("cat a > b"))
        self.assertFalse(read_only_shell("rm -rf x"))
        self.assertFalse(read_only_shell("find . -delete"))


class TestGoldenFixture(unittest.TestCase):
    def setUp(self):
        self.scan = claude.scan(WIN, claude_dir=FIX)

    def test_sessions_by_cwd(self):
        self.assertEqual(sorted(self.scan.sessions), ["s-nfd", "s-win"])  # 같은 폴더의 다른 작업 폴더는 뺀다
        self.assertEqual(self.scan.other_cwd, 1)
        self.assertEqual(self.scan.unknown_types, {"future-record": 1})
        self.assertEqual((self.scan.bad_lines, self.scan.duplicate_lines), (1, 1))
        self.assertEqual(sorted(claude.scan(POSIX, claude_dir=FIX).sessions), ["s-posix"])

    def test_dedupe_differs_from_naive_sum(self):
        ses = self.scan.sessions["s-win"]
        self.assertEqual(len(ses.requests), 4)
        tot = {k: sum(r.tokens()[k] for r in ses.requests.values()) for k in ses.requests[("msg_1", "req_1")].tokens()}
        self.assertEqual(tot, {"input": 165, "output": 140, "cache_read": 2300, "cache_write_5m": 300,
                               "cache_write_1h": 400})
        naive_in = naive_out = 0
        for p in [FIX / "projects" / "C--work--------" / "s-win.jsonl"]:
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("type") == "assistant":
                    naive_in += r["message"]["usage"]["input_tokens"]
                    naive_out += r["message"]["usage"]["output_tokens"]
        self.assertEqual((naive_in, naive_out), (370, 185))
        self.assertNotEqual(naive_in, tot["input"] - 5)  # 서브에이전트 5를 뺀 본체 값과도 다르다
        self.assertEqual(sorted(ses.calls), ["t1", "t2", "t9"])  # api-request-blob의 사본은 세지 않는다
        self.assertTrue(ses.calls["t2"].error)
        self.assertEqual(ses.calls["t1"].info["totalLines"], 1)
        self.assertEqual([h[1] for h in ses.human], ["로그인 버그 고쳐 줘"])
        self.assertEqual(ses.agents, {"agent:ab1": {"type": "Explore"}})

    def test_cost(self):
        rows, models, total = summarize([self.scan.sessions["s-win"]], pricer())
        # opus 5.5 (100만 토큰당): 입력 4, 출력 20, 캐시 읽기 0.2, 5분 쓰기 5, 1시간 쓰기 8
        # req_1 0.0026 + req_2 0.0041 + 서브에이전트 0.00072
        self.assertAlmostEqual(models["claude-opus-5-5"]["cost_usd"], 0.00742, places=8)
        self.assertIsNone(models["mystery-model-1"]["cost_usd"])
        self.assertFalse(total["complete"])
        self.assertEqual(total["tokens"]["cache_write"], 700)
        self.assertEqual(rows[0]["lines"], 6)

    def test_feedback_memory_inbox(self):
        mems = claude.feedback_memories(self.scan.memory_dirs)
        self.assertEqual(mems, [{"file": "fb-commit.md", "name": "commit-language",
                                 "description": "커밋 메시지는 한국어로 쓴다"}])
        db = RuleDB({"scopes": {}, "aspects": {}, "contexts": {}, "rules": []})
        db.merge_pack(load_pack("base"))
        out = signals.inbox(mems, db, "ko")
        self.assertIn("rules add --scope global", out[0]["commands"][0])
        db.add("work", "process", "커밋 메시지는 한국어로 쓴다", "팀", "처음")
        self.assertIn("rules hit work.", signals.inbox(mems, db, "ko")[0]["commands"][0])


# ── 신호 시험용 기록 만들기 · Builder for signal tests ──

class Builder:
    def __init__(self, sid="s1", cwd=WIN, model="claude-opus-5-5"):
        self.sid, self.cwd, self.model, self.recs, self.sec = sid, cwd, model, [], 0

    def _ts(self, step=1):
        self.sec += step
        return f"2026-10-20T02:{self.sec // 60:02d}:{self.sec % 60:02d}.000Z"

    def _id(self):
        return next(SEQ)  # 기록 전체에서 겹치지 않는 번호(uuid·message.id·tool_use.id)

    def call(self, name, inp, result="ok", error=False, prompt=1000, out=10, ctx=None, tur=None, step=1):
        n = self._id()
        extra = {"isSidechain": True, "agentId": ctx} if ctx else {}
        self.recs.append({"type": "assistant", "uuid": f"a{n}", "sessionId": self.sid, "requestId": f"r{n}",
                          "timestamp": self._ts(step), "cwd": self.cwd, **extra,
                          "message": {"id": f"m{n}", "model": self.model, "usage": {
                              "input_tokens": 1, "output_tokens": out, "cache_read_input_tokens": prompt - 1,
                              "cache_creation_input_tokens": 0},
                              "content": [{"type": "tool_use", "id": f"t{n}", "name": name, "input": inp}]}})
        self.recs.append({"type": "user", "uuid": f"u{n}", "sessionId": self.sid, "timestamp": self._ts(),
                          "cwd": self.cwd, **extra, **({"toolUseResult": tur} if tur else {}),
                          "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n}",
                                                   "is_error": error, "content": result}]}})
        return self

    def say(self, text, step=10):
        n = self._id()
        self.recs.append({"type": "user", "uuid": f"h{n}", "sessionId": self.sid, "timestamp": self._ts(step),
                          "cwd": self.cwd, "origin": {"kind": "human"}, "message": {"content": text}})
        return self

    def write(self, base, name=None):
        folder = Path(base) / "projects" / claude.encode_dir_name(self.cwd)
        folder.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(r, ensure_ascii=False) for r in self.recs]
        if name:
            p = folder / self.sid / "subagents" / f"agent-{name}.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
        else:
            p = folder / f"{self.sid}.jsonl"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self


class TestSignals(TempProject):
    def hits(self, *builders, db=None, explore=("low:medium", "claude-haiku-5-5")):
        for b in builders:
            b.write(self.tmp / "cc")
        scan = claude.scan(WIN, claude_dir=self.tmp / "cc")
        env = signals.Env(WIN, pricer(), db, *explore)
        return signals.detect(sorted(scan.sessions.values(), key=lambda s: s.id), env)

    def names(self, hits):
        return sorted({h["signal"] for h in hits})

    def test_same_call_streak(self):
        b = Builder()
        for _ in range(3):
            b.call("Read", {"file_path": WIN + "\\a.py", "limit": 5})
        hits = [h for h in self.hits(b) if h["signal"] == "same_call_streak"]
        self.assertEqual([h["count"] for h in hits], [3])
        self.assertEqual(hits[0]["evidence"], {"tool": "Read"})
        self.assertGreater(hits[0]["cost_usd"], 0)

    def test_two_calls_or_changed_input_is_fine(self):
        b = Builder().call("Read", {"file_path": "a"}).call("Read", {"file_path": "a"}).call("Read", {"file_path": "b"})
        self.assertNotIn("same_call_streak", self.names(self.hits(b)))

    def test_same_error_streak(self):
        b = Builder()
        for i in range(3):
            b.call("Bash", {"command": f"pytest -k t{i}"}, result=f"Error: exit code {i}\nboom", error=True)
        self.assertIn("same_error_streak", self.names(self.hits(b)))
        b2 = Builder("s2")
        b2.call("Bash", {"command": "x"}, result="Error: 1", error=True)
        b2.call("Bash", {"command": "y"}, result="fine")  # 같은 도구가 한 번 성공하면 끊긴다
        b2.call("Bash", {"command": "x"}, result="Error: 1", error=True)
        b2.call("Bash", {"command": "x"}, result="Error: 1", error=True)
        self.assertNotIn("same_error_streak", self.names(h for h in self.hits(b2) if h["session"] == "s2"))

    def test_big_output_resident_cost(self):
        b = Builder().call("Bash", {"command": "cat big.log"}, result="x" * 30000, prompt=1000, out=10)
        for _ in range(4):
            b.call("Grep", {"pattern": f"p{_}"}, prompt=8510)  # 다음 요청부터 7,500토큰이 늘어 있다
        hit = next(h for h in self.hits(b) if h["signal"] == "big_output")
        self.assertEqual(hit["tokens"], 7500)
        self.assertTrue(hit["evidence"]["measured"])
        self.assertEqual(hit["evidence"]["later"], 4)
        # 캐시 쓰기 1번(5) + 캐시 읽기 3번(0.2), 100만 토큰당
        self.assertAlmostEqual(hit["cost_usd"], 7500 * (5 + 0.2 * 3) / 1e6, places=9)

    def test_whole_file_read(self):
        tur = {"file": {"filePath": "a", "numLines": 1500, "startLine": 1, "totalLines": 1500}}
        b = Builder().call("Read", {"file_path": WIN + "\\a.py"}, result="x" * 100, tur=tur).call("Grep", {"p": 1})
        hit = next(h for h in self.hits(b) if h["signal"] == "big_output")
        self.assertTrue(hit["evidence"]["whole_file"])

    def test_repeat_correction_korean(self):
        b = Builder().say("로그인 화면 고쳐 줘").call("Read", {"file_path": "a"})
        b.say("아니, 그게 아니라 버튼 색이야").say("또 틀렸어. 원래대로 돌려")
        hit = next(h for h in self.hits(b) if h["signal"] == "repeat_correction")
        self.assertEqual(hit["count"], 2)
        self.assertNotIn("버튼", json.dumps(hit, ensure_ascii=False))  # 사용자 글은 결과에 없다
        self.assertEqual(signals.correction_markers("아니면 이렇게 해 볼까?"), [])
        self.assertEqual(signals.correction_markers("No, that's not it"), ["no,", "that's not"])

    def test_expensive_simple(self):
        cc = self.tmp / "cc"
        Builder().call("Agent", {"prompt": "look"}).write(cc)
        Builder().call("Grep", {"pattern": "x"}, ctx="ag1").call("Bash", {"command": "git log -3"}, ctx="ag1"
                                                                 ).write(cc, "ag1")
        Builder().call("Edit", {"file_path": "a", "old_string": "x", "new_string": "y"}, ctx="ag2").write(cc, "ag2")
        hits = [h for h in self.hits() if h["signal"] == "expensive_simple"]
        self.assertEqual([h["ctx"] for h in hits], ["agent:ag1"])  # 쓰기가 있는 서브에이전트는 아니다
        self.assertEqual(hits[0]["count"], 2)
        self.assertGreater(hits[0]["saving_usd"], 0)
        self.assertLess(hits[0]["saving_usd"], hits[0]["cost_usd"])

    def test_rewritten_script_across_sessions(self):
        body = "import json, sys\n" + "\n".join(f"total_{i} = sum(len(x) for x in data_{i}) + {i}" for i in range(12))
        a = Builder("s1").call("Write", {"file_path": WIN + "\\tmp\\probe.py", "content": body})
        b = Builder("s2").call("Write", {"file_path": "D:\\scratch\\probe2.py", "content": body + "\nprint(1)"})
        same = Builder("s3").call("Write", {"file_path": WIN + "\\tmp\\probe.py", "content": body})
        hits = [h for h in self.hits(a, b, same) if h["signal"] == "rewritten_script"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["count"], 3)
        self.assertIn("<out>/probe2.py", hits[0]["evidence"]["names"])

    def test_detect_threshold_comes_from_rule_db(self):
        b = Builder()
        for _ in range(3):
            b.call("Read", {"file_path": "a"})
        db = RuleDB({"scopes": {"global": "g", "work": "w"}, "aspects": {"process": "p"}, "contexts": {}, "rules": [
            {"id": "work.loop.same-call", "scope": "work", "aspect": "process", "level": "should", "rule": "r",
             "why": "w", "check": {"type": "auto"}, "detect": {"signal": "same_call_streak", "threshold": 4}}]})
        self.assertNotIn("same_call_streak", self.names(self.hits(b, db=db)))

    def test_suggest_finds_existing_rule(self):
        db = RuleDB({"scopes": {}, "aspects": {}, "contexts": {}, "rules": []})
        db.merge_pack(load_pack("base"))
        db.data["scopes"]["work/loop"] = "loop"
        db.rules.append({"id": "work.loop.same-call", "scope": "work/loop", "aspect": "process", "level": "should",
                         "rule": "같은 호출", "why": "w", "check": {"type": "auto"},
                         "detect": {"signal": "same_call_streak", "threshold": 3}, "status": "active"})
        hits = [{"signal": "same_call_streak", "session": s, "cost_usd": 0.1} for s in ("a", "b")] + \
            [{"signal": "big_output", "session": "a", "cost_usd": 1.0}] + \
            [{"signal": "repeat_correction", "session": "a"}, {"signal": "expensive_simple", "session": "a"}]
        out = {s["signal"]: s for s in signals.suggestions(hits, db, "ko")}
        self.assertEqual(signals.suggestions(hits, db, "ko")[0]["signal"], "same_call_streak")  # 반복된 것부터
        self.assertEqual((out["same_call_streak"]["rule"], out["same_call_streak"]["match"]),
                         ("work.loop.same-call", "detect"))
        self.assertTrue(out["same_call_streak"]["commands"][0].startswith("habitree rules hit work.loop.same-call"))
        self.assertIn("--scope work ", out["big_output"]["commands"][0])  # work/context가 없으면 가까운 상위 범위
        self.assertEqual(out["repeat_correction"]["rule"], "work.cycle.feedback-to-rule")
        self.assertTrue(out["expensive_simple"]["commands"][0].startswith("habitree models"))


class TestAuditCommand(TempProject):
    def test_cli_json_and_text(self):
        self.init()
        b = Builder(cwd=str(self.root.resolve())).say("비밀 문장 하나")
        for _ in range(3):
            b.call("Read", {"file_path": str(self.root.resolve() / "a.py")})
        b.write(self.tmp / "cc")
        code, out, err = self.cli("audit", "--claude-dir", str(self.tmp / "cc"), "--json", "--suggest")
        self.assertEqual(code, 0, err)
        self.assertNotIn("비밀 문장", out)
        data = json.loads(out)
        self.assertEqual(len(data["sessions"]), 1)
        self.assertTrue(data["sessions"][0]["started"].endswith("Z"))
        self.assertEqual(data["signals"][0]["signal"], "same_call_streak")
        self.assertTrue(data["rule_db"])
        code, out, err = self.cli("audit", "--claude-dir", str(self.tmp / "cc"), "--suggest")
        self.assertEqual(code, 0, err)
        self.assertIn("같은 호출 되풀이", out)
        # 같은 신호의 감지 규칙이 규칙 DB에 있으면 hit, 없으면 add 초안을 낸다
        from habitree.core.ruledb import RuleDB
        db = RuleDB.load(self.root / ".habitree" / "rules.json")  # 살아 있는 꾸러미 포함
        same = [r["id"] for r in db.rules if (r.get("detect") or {}).get("signal") == "same_call_streak"]
        if same:
            self.assertIn(f"rules hit {same[0]}", out)
        else:
            self.assertIn("rules add --scope work", out)

    def test_no_records_and_codex(self):
        code, out, _ = self.cli("audit", "--claude-dir", str(self.tmp / "none"))
        self.assertEqual(code, 0)
        self.assertIn("세션 기록이 없습니다", out)
        code, _, err = self.cli("audit", "--tool", "codex")
        self.assertEqual(code, 2)
        self.assertIn("Codex", err)


if __name__ == "__main__":
    unittest.main()
