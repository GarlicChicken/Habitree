"""MCP 서버 왕복 시험: 서브프로세스로 `python -m habitree mcp`를 띄워 줄 단위 JSON-RPC를 주고받는다.
/ MCP round trip over a real subprocess with line-delimited JSON-RPC."""
import json
import os
import subprocess
import sys
import unittest

from helpers import SRC, TempProject


def rpc(mid, method, params=None):
    msg = {"jsonrpc": "2.0", "id": mid, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def call(mid, name, arguments):
    return rpc(mid, "tools/call", {"name": name, "arguments": arguments})


class TestMCP(TempProject):
    def setUp(self):
        super().setUp()
        self.init()
        self.write("src/인증 모듈.py", '"""인증."""\n\n\ndef verify_token(token):\n    """사용자 인증을 처리한다."""\n'
                                     '    return bool(token)\n')

    def session(self, messages, raw_lines=()):
        """메시지를 보내고 (응답 목록, 표준 출력 전체, 표준 오류)를 돌려준다."""
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        env["HABITREE_LANG"] = "ko"
        lines = [json.dumps(m, ensure_ascii=False) for m in messages] + list(raw_lines)
        data = ("\n".join(lines) + "\n").encode("utf-8")
        proc = subprocess.run([sys.executable, "-m", "habitree", "-C", str(self.root), "mcp"], input=data,
                              capture_output=True, env=env, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        out = proc.stdout.decode("utf-8")
        replies = [json.loads(line) for line in out.splitlines() if line.strip()]  # stdout은 JSON 줄만
        return replies, out, proc.stderr.decode("utf-8", "replace")

    def test_round_trip(self):
        init = rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "test", "version": "0"}})
        msgs = [init, {"jsonrpc": "2.0", "method": "notifications/initialized"},
                rpc(2, "tools/list"),
                call(3, "map_find", {"query": "인증을", "level": 2}),
                call(4, "map_find", {"query": "쀍뛇꿹똷"}),
                call(5, "rules_brief", {"scopes": ["work"], "must": False}),
                call(6, "check", {}),
                call(7, "map_show", {"budget": 300}),
                call(8, "map_show", {"focus": ["../밖"]}),
                call(9, "nope", {}),
                rpc(10, "foo/bar"),
                rpc(11, "ping")]
        replies, out, err = self.session(msgs, raw_lines=["이건 JSON이 아님"])
        by_id = {r.get("id"): r for r in replies}
        self.assertEqual(len(replies), 12)  # 알림에는 답이 없다. 깨진 줄에는 id 없는 오류
        r = by_id[1]["result"]
        self.assertEqual(r["protocolVersion"], "2025-06-18")
        self.assertIn("tools", r["capabilities"])
        self.assertEqual(r["serverInfo"]["name"], "habitree")
        self.assertIn("map_find", r["instructions"])
        tools = by_id[2]["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, {"map_find", "map_show", "rules_brief", "check"})
        self.assertTrue(all("inputSchema" in t and "title" in t for t in tools))
        found = by_id[3]["result"]
        self.assertFalse(found["isError"])
        self.assertIn("verify_token", found["content"][0]["text"])
        self.assertIn("사용자 인증을 처리한다.", found["content"][0]["text"])
        missing = by_id[4]["result"]["content"][0]["text"]
        self.assertIn("못 찾음", missing)
        self.assertIn("map_show", missing)  # MCP에서는 다음 할 일도 도구 이름으로
        self.assertIn("# 규칙", by_id[5]["result"]["content"][0]["text"])
        self.assertIn("점검", by_id[6]["result"]["content"][0]["text"])
        self.assertLessEqual(len(by_id[7]["result"]["content"][0]["text"]), 300)
        self.assertTrue(by_id[8]["result"]["isError"])
        self.assertEqual(by_id[9]["error"]["code"], -32602)
        self.assertEqual(by_id[10]["error"]["code"], -32601)
        self.assertEqual(by_id[11]["result"], {})
        self.assertEqual(by_id[None]["error"]["code"], -32700)
        self.assertNotIn("\r", out)

    def test_version_fallback_and_old_shape(self):
        replies, _, _ = self.session([rpc(1, "initialize", {"protocolVersion": "1999-01-01"}),
                                      rpc(2, "tools/list")])
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-11-25")
        replies, _, _ = self.session([rpc("a", "initialize", {"protocolVersion": "2024-11-05"}),
                                      rpc("b", "tools/list"), rpc("c", "server/discover")])
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2024-11-05")
        self.assertNotIn("title", replies[0]["result"]["serverInfo"])
        tool = replies[1]["result"]["tools"][0]
        self.assertNotIn("title", tool)
        self.assertNotIn("annotations", tool)
        self.assertEqual(replies[2]["error"]["code"], -32601)  # 새 방식 클라이언트는 이걸 보고 initialize로 돌아온다


if __name__ == "__main__":
    unittest.main()
