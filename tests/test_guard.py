"""guard 시험: 감지기, 반복 제한, 위임, Stop 점검, 경로 키, 상태 파일. / guard tests.

훅은 commands.hook.handle을 직접 부르거나(빠름) 표준 입력을 바꿔 CLI로 부른다(끝에서 끝까지).
"""
import io
import json
import os
import sys
import time
import unicodedata
import unittest
from pathlib import Path

from helpers import TempProject, run_cli
from habitree.commands.hook import handle
from habitree.core import state as hstate
from habitree.core.paths import path_key
from habitree.core.ruledb import RuleDB, vote_stats
from habitree.guard import delegate
from habitree.guard.events import error_parts, signature

ERR = "Exit code 1\nError: Cannot find module 'left-pad'"


class GuardProject(TempProject):
    """init한 임시 프로젝트에 훅 이벤트를 보낸다. / Send hook events to an initialized temp project."""

    def setUp(self):
        super().setUp()
        self.old_pd = os.environ.pop("CLAUDE_PROJECT_DIR", None)
        self.init()
        self.sid = "세션-1"
        self.n = 0

    def tearDown(self):
        if self.old_pd is not None:
            os.environ["CLAUDE_PROJECT_DIR"] = self.old_pd
        super().tearDown()

    def config(self, **over):
        p = self.root / ".habitree/config.json"
        cfg = json.loads(p.read_text(encoding="utf-8"))
        for k, v in over.items():
            cur = cfg
            parts = k.split("__")
            for part in parts[:-1]:
                cur = cur.setdefault(part, {})
            cur[parts[-1]] = v
        p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    def send(self, event, **payload):
        payload.setdefault("session_id", self.sid)
        payload.setdefault("hook_event_name", event)
        payload.setdefault("cwd", str(self.root))
        return handle(event, payload, str(self.root))

    def pre(self, tool, inp, tid=None):
        self.n += 1
        self.last_id = tid or f"t{self.n}"
        return self.send("PreToolUse", tool_name=tool, tool_input=inp, tool_use_id=self.last_id)

    def post(self, tool, inp, ok=True, error=ERR, response=None):
        if ok:
            return self.send("PostToolUse", tool_name=tool, tool_input=inp, tool_use_id=self.last_id,
                             tool_response=response if response is not None else {"stdout": "ok", "stderr": ""})
        return self.send("PostToolUseFailure", tool_name=tool, tool_input=inp, tool_use_id=self.last_id,
                         error=error)

    def call(self, tool, inp, ok=True, error=ERR, response=None):
        return self.pre(tool, inp), self.post(tool, inp, ok, error, response)

    def prompt(self, text):
        return self.send("UserPromptSubmit", prompt=text)

    def stop(self, active=False, message="끝났습니다."):
        return self.send("Stop", stop_hook_active=active, last_assistant_message=message + str(time.time()))

    @staticmethod
    def ai(out):
        return (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")

    @staticmethod
    def perm(out):
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def state(self):
        return hstate.read(self.root / ".habitree/state", self.sid)

    def edit(self, rel, old, new, apply=True):
        path = self.root / rel
        inp = {"file_path": str(path), "old_string": old, "new_string": new}
        pre = self.pre("Edit", inp)
        if apply:
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
        return pre, self.post("Edit", inp)


class TestLoops(GuardProject):
    def test_same_call_warn_then_stop(self):
        cmd = {"command": "npm test", "description": "테스트"}
        outs = [self.pre("Bash", dict(cmd, description=f"설명 {i}")) for i in range(6)]
        self.assertEqual(self.ai(outs[1]), "")
        self.assertIn("work.loop.same-call", self.ai(outs[2]))     # 3번째: 경고
        self.assertIn("3번", self.ai(outs[2]))
        self.assertEqual(self.ai(outs[3]), "")                     # 같은 연속에는 한 번만
        self.assertEqual(self.perm(outs[4]), "ask")                 # 5번째: 멈춤(사용자 확인)
        self.assertIn("work.loop.same-call", outs[4]["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIsNone(self.perm(outs[5]))

    def test_not_a_loop(self):
        for name in ("a.py", "b.py", "c.py", "d.py"):          # 다른 파일 대상
            self.assertEqual(self.ai(self.pre("Read", {"file_path": str(self.root / name)})), "")
        for i in range(4):                                     # 인자를 바꾼 재시도
            self.assertEqual(self.ai(self.pre("Bash", {"command": f"pytest -k case{i}"})), "")
        self.write("app.py", "x = 0\n")
        for i in range(4):                                     # 코드를 고친 뒤 테스트 다시 돌리기
            self.edit("app.py", f"x = {i}", f"x = {i + 1}")
            pre, _ = self.call("Bash", {"command": "pytest"})
            self.assertNotIn("work.loop.same-call", self.ai(pre))

    def test_same_error_streak(self):
        bash = {"command": "node build.js"}
        outs = []
        for i in range(3):
            self.call("Read", {"file_path": str(self.root / "build.js")})  # 읽기만 하는 호출은 사이에 껴도 된다
            outs.append(self.call("Bash", bash, ok=False))
        self.assertEqual(self.ai(outs[1][1]), "")
        self.assertIn("work.loop.same-error", self.ai(outs[2][1]))
        self.assertIn("left-pad", self.ai(outs[2][1]))
        self.call("Read", {"file_path": str(self.root / "build.js")})
        fourth = self.pre("Bash", bash)
        self.assertEqual(self.perm(fourth), "ask")
        self.assertIn("work.loop.same-error", fourth["hookSpecificOutput"]["permissionDecisionReason"])

    def test_error_chain_breaks_on_edit_or_new_error(self):
        self.write("build.js", "a\n")
        bash = {"command": "node build.js"}
        self.call("Bash", bash, ok=False)
        self.call("Bash", bash, ok=False, error="Exit code 1\nError: other")
        self.edit("build.js", "a", "b")
        _, out = self.call("Bash", bash, ok=False)
        self.assertNotIn("work.loop.same-error", self.ai(out))

    def test_cycle(self):
        a = {"file_path": str(self.root / "x.py")}
        b = {"command": "pytest -x"}
        outs = []
        for _ in range(5):
            outs.append(self.pre("Read", a))
            outs.append(self.pre("Bash", b))
        self.assertTrue(all("work.loop.cycle" not in self.ai(o) for o in outs[:-1]))
        self.assertIn("work.loop.cycle", self.ai(outs[-1]))
        self.assertIn("5바퀴", self.ai(outs[-1]))

    def test_error_parts_drop_volatile_numbers(self):
        k1, line = error_parts("Exit code 1\nTimeout after 12034 ms at 0x7ffe12")
        k2, _ = error_parts("Exit code 1\nTimeout after 99881 ms at 0x7aa000")
        self.assertEqual(k1, k2)
        self.assertTrue(line.startswith("Timeout"))


class TestFiles(GuardProject):
    def test_small_edits_info_then_summary(self):
        self.write("page.html", "".join(f"<p>{i}</p>\n" for i in range(20)))
        for i in range(6):
            _, out = self.edit("page.html", f"<p>{i}</p>", f"<p>{i}!</p>")
            self.assertEqual(self.ai(out), "")                # 정보 등급은 바로 말하지 않는다
        stop = self.stop()
        self.assertIn("work.loop.small-edits", stop.get("systemMessage", ""))
        self.assertNotIn("decision", stop)

    def test_small_edits_reset_by_verify(self):
        self.config(verify={"test": ["python", "-m", "unittest"]})
        self.write("page.html", "".join(f"<p>{i}</p>\n" for i in range(20)))
        for i in range(5):
            self.edit("page.html", f"<p>{i}</p>", f"<p>{i}!</p>")
        self.call("Bash", {"command": "python3 -m unittest discover"})
        for i in range(5, 8):
            self.edit("page.html", f"<p>{i}</p>", f"<p>{i}!</p>")
        self.assertNotIn("work.loop.small-edits", self.stop().get("systemMessage", ""))
        self.assertEqual(self.state()["verify_runs"], 1)

    def test_file_growth(self):
        self.write("src/big.py", "".join(f"line_{i} = {i}\n" for i in range(200)))
        added = "".join(f"extra_{i} = {i}\n" for i in range(70))
        _, out = self.edit("src/big.py", "line_100 = 100\n", "line_100 = 100\n" + added)
        text = self.ai(out)
        self.assertIn("code.structure.file-growth", text)
        self.assertIn("200줄에서 270줄", text)

    def test_file_growth_not_when_balanced_or_small(self):
        self.write("small.py", "".join(f"v{i} = {i}\n" for i in range(40)))
        _, out = self.edit("small.py", "v1 = 1\n", "v1 = 1\n" + "w = 2\n" * 30)
        self.assertNotIn("file-growth", self.ai(out))          # 최소 줄 수 아래
        self.write("mid.py", "".join(f"m{i} = {i}\n" for i in range(200)))
        old = "".join(f"m{i} = {i}\n" for i in range(10, 60))
        new = "".join(f"n{i} = {i}\n" for i in range(110))
        _, out = self.edit("mid.py", old, new)
        self.assertNotIn("file-growth", self.ai(out))          # 지운 것도 많다(10:1 아님)

    def test_copy_block(self):
        block = "".join(f"    total_{i} = compute_value(items[{i}], factor={i}) + offset_{i}\n" for i in range(8))
        self.write("src/util.py", "def helper(items):\n" + block + "    return total_0\n")
        self.send("SessionStart", source="startup")
        path = self.root / "src/new_feature.py"
        content = "def feature(items):\n" + block + "    return total_1\n"
        inp = {"file_path": str(path), "content": content}
        self.pre("Write", inp)
        path.write_text(content, encoding="utf-8")
        text = self.ai(self.post("Write", inp))
        self.assertIn("code.structure.copy-block", text)
        self.assertIn("src/util.py", text)

    def test_copy_block_ignores_trivial_lines(self):
        braces = "}\n" * 3 + "{\n" * 3 + "  \n" * 3 + "# 주석\n" * 6
        self.write("src/a.js", braces)
        self.send("SessionStart", source="startup")
        path = self.root / "src/b.js"
        inp = {"file_path": str(path), "content": braces}
        self.pre("Write", inp)
        path.write_text(braces, encoding="utf-8")
        self.assertNotIn("copy-block", self.ai(self.post("Write", inp)))

    def test_big_output(self):
        inp = {"file_path": str(self.root / "huge.log")}
        self.pre("Read", inp)
        out = self.post("Read", inp, response={"type": "text", "file": {"content": "x" * 25000}})
        self.assertIn("work.context.big-output", self.ai(out))
        self.assertRegex(self.ai(out), r"250\d\d자")


class TestRequests(GuardProject):
    def test_request_split_to_user(self):
        self.assertEqual(self.prompt("버튼 색 바꿔 줘"), {})
        self.assertEqual(self.prompt("응"), {})                   # 짧은 대답은 세지 않는다
        self.prompt("그리고 글씨도 크게")
        out = self.prompt("아 그리고 여백도")
        self.assertIn("work.request.split", out.get("systemMessage", ""))
        self.assertIn("work.request.split", self.ai(out))        # 화면에 안 보일 때를 위한 AI 전달
        self.assertIn("«", self.ai(out))

    def test_ack_does_not_split(self):
        for text in ("좋아", "응", "ok", "계속", "/clear"):
            self.assertNotIn("systemMessage", self.prompt(text))

    def test_repeat_correction(self):
        self.prompt("로그인 화면의 버튼 색을 파란색으로 바꾸고 글씨 크기를 조금 키워 주세요. 다른 곳은 그대로 두고요.")
        self.prompt("아니 그게 아니라 로그인 화면 버튼 색 말이에요. 배경이 아니라 버튼이 파란색이어야 해요.")
        out = self.prompt("아니 로그인 버튼 색이 아직도 그대로예요. 버튼 자체를 파란색으로 바꿔 주세요, 다시요.")
        self.assertIn("work.request.repeat-correction", out.get("systemMessage", ""))

    def test_topic_mix_info(self):
        self.prompt("로그인 화면 버튼 색을 파란색으로 바꾸고 테스트를 고쳐 주세요")
        with hstate.session(self.root / ".habitree/state", self.sid) as st:
            st["turns"] = 40
        out = self.prompt("다음 달 여행 일정표와 숙소 예산을 엑셀로 정리해 줘")
        self.assertNotIn("systemMessage", out)                  # 정보 등급: 바로 말하지 않음
        self.assertIn("work.context.topic-mix", self.stop().get("systemMessage", ""))


class TestVerifyAndStop(GuardProject):
    def test_no_verify_note(self):
        self.config(verify={"test": ["python", "-m", "unittest"]})
        self.write("notes.md", "a\n")
        self.edit("notes.md", "a", "b")
        self.assertIn("work.verify.run-before-done", self.stop().get("systemMessage", ""))

    def test_no_verify_quiet_after_verify(self):
        self.config(verify={"test": ["python", "-m", "unittest"]})
        self.write("notes.md", "a\n")
        self.edit("notes.md", "a", "b")
        self.call("Bash", {"command": "python -m unittest discover -s tests"})
        self.assertNotIn("run-before-done", self.stop().get("systemMessage", ""))

    def test_stop_check_blocks_once(self):
        self.write("notes.md", "a\n")
        self.edit("notes.md", "a", "b")
        self.write("README.md", self.read("README.md") + "\n[깨진 링크](없는-파일.md)\n")
        first = self.stop()
        self.assertEqual(first.get("decision"), "block")
        self.assertIn("docs.link", first["reason"])
        self.assertIn("habitree check", first["reason"])
        self.assertEqual(self.stop(active=True), {})             # stop_hook_active면 막지 않는다
        self.edit("notes.md", "b", "c")
        self.assertNotIn("decision", self.stop())               # 같은 오류로 두 번 막지 않는다

    def test_stop_check_off_and_no_edits(self):
        self.write("README.md", self.read("README.md") + "\n[깨진 링크](없는-파일.md)\n")
        self.assertNotIn("decision", self.stop())               # 수정이 없었으면 점검하지 않는다
        self.config(guard__stop_check=False)
        self.write("notes.md", "a\n")
        self.edit("notes.md", "a", "b")
        self.assertNotIn("decision", self.stop())


class TestDelegation(GuardProject):
    def test_phrases(self):
        for text in ("알아서 끝까지 해 줘", "묻지 말고 진행해", "이건 다 맡길게", "just do it", "Use your judgment and finish",
                     "추천대로 해 주세요"):
            self.assertTrue(delegate.find_phrase(text), text)
        for text in ("'알아서 해 줘'라고 하면 어떻게 돼?", "알아서 해 줄 수 있어?", "팀장님이 알아서 하래",
                     "알아서 하지 마", "he said just do it", "끝까지 읽어 봐"):
            self.assertIsNone(delegate.find_phrase(text), text)

    def test_boundaries(self):
        b = delegate.boundaries("알아서 끝까지 해 줘. 다만 파일은 지우지는 마")
        self.assertEqual(b, ["파일은 지우지는 마"])
        self.assertEqual(delegate.boundary_category(b[0]), "delete")
        self.assertEqual(delegate.boundaries("묻지 말고 끝까지 해"), [])
        en = delegate.boundaries("just do it, but don't push to main")
        self.assertEqual(delegate.boundary_category(en[0]), "deploy")

    def test_flow(self):
        out = self.prompt("로그인 화면 고치는 거 알아서 끝까지 해 줘. 다만 파일은 지우지는 마")
        text = self.ai(out)
        self.assertIn("work.delegate.declare", text)
        self.assertIn("되묻기 없이", text)
        self.assertIn("파일은 지우지는 마", text)
        d = self.state()["delegation"]
        self.assertTrue(d["active"])
        self.assertEqual(d["boundaries"][0]["category"], "delete")
        # 위험한 일은 위임 중에도 묻는다(경계도 함께 보인다)
        risky = self.pre("Bash", {"command": "rm -rf build"})
        self.assertEqual(self.perm(risky), "ask")
        reason = risky["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("지우기", reason)
        self.assertIn("파일은 지우지는 마", reason)
        self.assertEqual(self.perm(self.pre("Bash", {"command": "git push origin main"})), "ask")
        self.assertIsNone(self.perm(self.pre("Bash", {"command": "pytest -q"})))
        # skip 규칙은 위임 중 생략하고 끝 보고에 모은다
        for text in ("버튼 색", "글씨도", "여백도"):
            self.assertNotIn("systemMessage", self.prompt(text))
        # 막힘(nudge)은 위임 중에도 감지: 멈춤 등급이면 묻지 않고 막는다
        outs = [self.pre("Bash", {"command": "npm run build"}) for _ in range(5)]
        self.assertIn("work.loop.same-call", self.ai(outs[2]))
        self.assertEqual(self.perm(outs[4]), "deny")
        # 끝: 한 번 막고 끝 보고를 받은 뒤 위임을 끝낸다
        stop = self.stop()
        self.assertEqual(stop.get("decision"), "block")
        self.assertIn("work.delegate.end-report", stop["reason"])
        self.assertIn("work.request.split", stop["reason"])
        self.assertIsNone(self.state()["delegation"])
        self.assertNotIn("decision", self.stop(active=True))
        self.assertIsNone(self.perm(self.pre("Bash", {"command": "rm -rf build2"})))  # 위임이 끝나면 평소대로

    def test_outside_root_and_secrets(self):
        self.prompt("묻지 말고 끝까지 진행해 줘")
        outside = Path(self.tmp) / "밖.txt"
        self.assertEqual(self.perm(self.pre("Write", {"file_path": str(outside), "content": "x"})), "ask")
        self.assertEqual(self.perm(self.pre("Write", {"file_path": str(self.root / ".env"), "content": "K=1"})), "ask")
        self.assertIsNone(self.perm(self.pre("Write", {"file_path": str(self.root / "ok.md"), "content": "x"})))

    def test_cancel_and_new_topic(self):
        self.prompt("알아서 끝까지 해 줘")
        out = self.prompt("이제 물어보고 해")
        self.assertIn("위임을 거뒀다", self.ai(out))
        self.assertIsNone(self.state()["delegation"])
        self.prompt("로그인 화면 버튼 고치는 일은 알아서 끝까지 해 줘")
        self.prompt("다음 달 여행 일정표와 숙소 예산 엑셀 정리")
        self.assertIsNone(self.state()["delegation"])
        self.assertEqual(self.state()["delegations"][-1]["end_reason"], "new_topic")

    def test_quoted_not_delegation(self):
        self.prompt("'알아서 해 줘'라고 하면 어떻게 동작해?")
        self.assertIsNone(self.state()["delegation"])

    def test_explicit_command_and_cli(self):
        self.prompt("/habitree:delegate 문서 정리")
        self.assertEqual(self.state()["delegation"]["granted_by"], "command")
        self.prompt("/habitree:delegate off")
        self.assertIsNone(self.state()["delegation"])
        code, out, err = self.cli("guard", "delegate", "on", "--task", "표 정리", "--boundary", "배포는 하지 마",
                                  "--session", self.sid)
        self.assertEqual(code, 0, err)
        d = self.state()["delegation"]
        self.assertEqual(d["task"], "표 정리")
        self.assertEqual(d["boundaries"][0]["category"], "deploy")
        code, out, _ = self.cli("guard", "delegate", "status")
        self.assertIn("표 정리", out)
        code, out, _ = self.cli("guard", "report")
        self.assertIn("표 정리", out)
        code, out, _ = self.cli("guard", "delegate", "off")
        self.assertIn("끝냈습니다", out)

    def test_limit(self):
        self.config(guard__delegate__max_tools=2)
        self.prompt("알아서 끝까지 해 줘")
        self.pre("Read", {"file_path": str(self.root / "a")})
        self.pre("Read", {"file_path": str(self.root / "b")})
        out = self.pre("Read", {"file_path": str(self.root / "c")})
        self.assertIn("한도", self.ai(out))
        self.assertIsNone(self.state()["delegation"])


class TestLimitsAndVotes(GuardProject):
    def test_max_per_session(self):
        warned = 0
        for i in range(4):
            outs = [self.pre("Bash", {"command": f"make target{i}"}) for _ in range(3)]
            warned += "work.loop.same-call" in self.ai(outs[2])
        self.assertEqual(warned, 3)                                # max_per_session 3

    def test_guard_off_and_vote_kind(self):
        self.pre("Bash", {"command": "ls"})
        code, out, err = self.cli("guard", "off", "work.loop.same-call", "--session", self.sid)
        self.assertEqual(code, 0, err)
        outs = [self.pre("Bash", {"command": "npm test"}) for _ in range(5)]
        self.assertTrue(all("same-call" not in self.ai(o) and not self.perm(o) for o in outs))
        r = RuleDB.load(self.root / ".habitree/rules.json").find("work.loop.same-call")
        self.assertEqual(r["votes"][-1]["kind"], "off")
        self.assertEqual(vote_stats(r)["total"], 0)               # 끄기는 '틀렸다'로 세지 않는다
        self.cli("guard", "on", "work.loop.same-call", "--session", self.sid)
        outs = [self.pre("Bash", {"command": "cargo build"}) for _ in range(3)]
        self.assertIn("same-call", self.ai(outs[2]))

    def test_paused_rule_is_silent(self):
        self.cli("rules", "pause", "work.loop.same-call", "--why", "시험")
        outs = [self.pre("Bash", {"command": "npm test"}) for _ in range(5)]
        self.assertTrue(all("work.loop.same-call" not in self.ai(o) and not self.perm(o) for o in outs))
        # 규칙은 서로 독립이다: 주기 1짜리 고리 규칙은 5바퀴에서 따로 알린다
        self.assertIn("work.loop.cycle", self.ai(outs[4]))

    def test_miss_votes_relax_threshold(self):
        rid = "work.loop.same-call"
        for _ in range(4):
            self.cli("rules", "hit", rid, "--feedback", "맞았다")
        code, out, err = self.cli("rules", "miss", rid, "--feedback", "이번엔 잔소리")
        self.assertEqual(code, 0, err)
        r = RuleDB.load(self.root / ".habitree/rules.json").find(rid)
        self.assertEqual(r["detect"]["threshold"], 4)             # 쓸모없음 20% → 기준 한 단계 완화
        self.assertEqual(r["detect"]["stop_at"], 5)
        outs = [self.pre("Bash", {"command": "npm test"}) for _ in range(4)]
        self.assertNotIn("same-call", self.ai(outs[2]))
        self.assertIn("same-call", self.ai(outs[3]))

    def test_hits_promote_info_to_warn(self):
        rid = "work.loop.small-edits"
        self.cli("rules", "hit", rid, "--feedback", "맞았다")
        self.cli("rules", "hit", rid, "--feedback", "또 맞았다")
        r = RuleDB.load(self.root / ".habitree/rules.json").find(rid)
        self.assertEqual(r["detect"]["severity"], "warn")
        self.write("page.html", "".join(f"<p>{i}</p>\n" for i in range(20)))
        outs = [self.edit("page.html", f"<p>{i}</p>", f"<p>{i}!</p>")[1] for i in range(6)]
        self.assertIn(rid, self.ai(outs[5]))                     # 이제는 바로 AI에게

    def test_explain_and_status(self):
        self.pre("Bash", {"command": "ls"})
        code, out, _ = self.cli("guard", "explain", "work.loop.same-call")
        self.assertEqual(code, 0)
        self.assertIn("same_call_streak", out)
        self.assertIn("rules miss", out)
        code, out, _ = self.cli("guard", "status")
        self.assertIn("도구 호출 1", out)
        code, out, _ = self.cli("guard", "status", "--json")
        self.assertEqual(json.loads(out)["session"], hstate.safe_id(self.sid))


class TestHookEndToEnd(GuardProject):
    def run_hook(self, event, payload, cwd=None):
        raw = payload if isinstance(payload, (bytes, str)) else json.dumps(payload, ensure_ascii=False)
        data = raw.encode("utf-8") if isinstance(raw, str) else raw
        old_stdin, old_cwd = sys.stdin, os.getcwd()
        sys.stdin = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8")
        try:
            os.chdir(str(cwd or self.root))
            return run_cli("hook", event)
        finally:
            sys.stdin = old_stdin
            os.chdir(old_cwd)

    def test_session_start(self):
        code, out, err = self.run_hook("SessionStart", {"session_id": "s", "source": "startup"})
        self.assertEqual(code, 0, err)
        ctx = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(ctx["hookEventName"], "SessionStart")
        self.assertIn("AGENTS.md", ctx["additionalContext"])     # AGENTS.md가 이미 실리면 짧게
        (self.root / "CLAUDE.md").unlink()
        code, out, _ = self.run_hook("SessionStart", {"session_id": "s2", "source": "startup"})
        text = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("작업 순환", text)
        self.assertIn("필수 규칙", text)
        self.assertLess(len(text), 3000)

    def test_pre_tool_output_shape(self):
        for i in range(3):
            code, out, err = self.run_hook("PreToolUse", {"session_id": "s", "tool_name": "Bash",
                                                          "tool_input": {"command": "npm test"},
                                                          "tool_use_id": f"u{i}", "cwd": str(self.root)})
            self.assertEqual(code, 0, err)
        data = json.loads(out)
        self.assertEqual(set(data), {"hookSpecificOutput"})
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertNotIn("permissionDecision", data["hookSpecificOutput"])

    def test_passes_without_config(self):
        bare = self.tmp / "설정 없음"
        bare.mkdir()
        code, out, err = self.run_hook("PreToolUse", {"session_id": "s", "tool_name": "Bash",
                                                      "tool_input": {"command": "x"}, "cwd": str(bare)}, cwd=bare)
        self.assertEqual((code, out), (0, ""))
        self.assertFalse((bare / ".habitree").exists())

    def test_internal_errors_never_block(self):
        for event, payload in (("PreToolUse", b"not json"), ("Foo", {"session_id": "s"}), ("Stop", b"")):
            code, out, err = self.run_hook(event, payload)
            self.assertEqual(code, 0)
        (self.root / ".habitree/rules.json").write_text("{ broken", encoding="utf-8")
        code, out, err = self.run_hook("PreToolUse", {"session_id": "s", "tool_name": "Bash",
                                                      "tool_input": {"command": "x"}, "cwd": str(self.root)})
        self.assertEqual((code, out), (0, ""))
        log = (self.root / ".habitree/state/hook-errors.log").read_text(encoding="utf-8")
        self.assertIn("PreToolUse", log)

    def test_busy_state_passes(self):
        lock = hstate.session_path(self.root / ".habitree/state", "s")
        lock.parent.mkdir(parents=True, exist_ok=True)
        Path(str(lock) + ".lock").write_text("", encoding="utf-8")
        start = time.time()
        code, out, err = self.run_hook("PreToolUse", {"session_id": "s", "tool_name": "Bash",
                                                      "tool_input": {"command": "x"}, "cwd": str(self.root)})
        self.assertEqual((code, out), (0, ""))
        self.assertLess(time.time() - start, 5)

    def test_duplicate_install_counted_once(self):
        payload = {"tool_name": "Bash", "tool_input": {"command": "npm test"}}
        for i in range(3):
            self.send("PreToolUse", tool_use_id=f"dup{i}", **payload)
            self.assertEqual(self.send("PreToolUse", tool_use_id=f"dup{i}", **payload), {})
        self.assertEqual(self.state()["counter"], 3)
        self.prompt("같은 요청")
        self.assertEqual(self.prompt("같은 요청"), {})
        self.assertEqual(self.state()["turns"], 1)


class TestStateAndPaths(GuardProject):
    def test_nfc_and_case_keys(self):
        nfc_name = "한글 파일.py"
        nfd_name = unicodedata.normalize("NFD", nfc_name)
        a = hstate.file_key(self.root, str(self.root / nfc_name), {})
        b = hstate.file_key(self.root, str(self.root / nfd_name), {})
        self.assertEqual(a, b)
        self.assertEqual(path_key(self.root, "SRC\\App.py", ci=True), path_key(self.root, "src/app.py", ci=True))
        self.assertNotEqual(path_key(self.root, "SRC/App.py", ci=False), path_key(self.root, "src/app.py", ci=False))
        self.assertEqual(path_key(self.root, str(self.root / "docs" / "a.md"), ci=False), "docs/a.md")

    def test_same_call_with_nfd_path(self):
        keyfn = lambda p: hstate.file_key(self.root, p, {})  # noqa: E731
        s1 = signature("Read", {"file_path": str(self.root / "문서.md")}, keyfn)
        s2 = signature("Read", {"file_path": str(self.root / unicodedata.normalize("NFD", "문서.md"))}, keyfn)
        self.assertEqual(s1, s2)
        self.assertNotEqual(s1, signature("Read", {"file_path": str(self.root / "다른.md")}, keyfn))

    def test_cleanup_and_limits(self):
        sdir = self.root / ".habitree/state"
        with hstate.session(sdir, "old") as st:
            for i in range(100):
                hstate.push(st, "calls", {"c": i}, 40)
        self.assertEqual(len(hstate.read(sdir, "old")["calls"]), 40)
        with hstate.session(sdir, "new"):
            pass
        old = hstate.session_path(sdir, "old")
        past = time.time() - 8 * 86400
        os.utime(str(old), (past, past))
        self.assertEqual(hstate.cleanup(sdir, 7), 1)
        self.assertFalse(old.exists())
        self.assertTrue(hstate.session_path(sdir, "new").exists())
        self.assertEqual(hstate.latest(sdir), "new")

    def test_stale_lock_is_broken(self):
        sdir = self.root / ".habitree/state"
        path = hstate.session_path(sdir, "x")
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = Path(str(path) + ".lock")
        lock.write_text("", encoding="utf-8")
        with self.assertRaises(hstate.StateBusy):
            with hstate.session(sdir, "x", timeout=0.1):
                pass
        past = time.time() - 60
        os.utime(str(lock), (past, past))
        with hstate.session(sdir, "x", timeout=0.5) as st:
            st["turns"] = 5
        self.assertEqual(hstate.read(sdir, "x")["turns"], 5)

    def test_safe_id(self):
        self.assertEqual(hstate.safe_id("abc-123"), "abc-123")
        self.assertNotIn("/", hstate.safe_id("../../etc/passwd"))
        self.assertTrue(hstate.safe_id(""))


if __name__ == "__main__":
    unittest.main()
