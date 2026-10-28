"""mcp: 표준 입출력 MCP 서버. AI 도구가 Habitree를 도구로 부르게 한다. / A stdio MCP server.

- 전송: 줄마다 JSON-RPC 2.0 메시지 하나(UTF-8). stdout에는 MCP 메시지만 쓰고, 로그는 stderr로 보낸다.
  도구가 실수로 print해도 stdout을 더럽히지 않게, 도는 동안 sys.stdout을 stderr로 돌려 둔다.
- 판: initialize로 시작하는 판(2024-11-05 ~ 2025-11-25)을 따른다. 클라이언트가 보낸 protocolVersion을
  지원하면 그대로, 아니면 아는 것 중 최신을 돌려준다. 2026-07-28 방식(server/discover, 요청마다 _meta)은
  아직 따르지 않는다. server/discover에는 -32601을 돌려주므로 두 방식을 다 아는 클라이언트는 initialize로 되돌아온다.
- 도구는 넷: map_find, map_show, rules_brief, check. 결과는 글자 예산(map.mcp_budget) 안에서 짧게,
  빈 결과 대신 '못 찾음 + 다음에 할 일'을 낸다. 작업 폴더(루트) 밖은 읽지 않는다.
- check 도구는 check 명령의 collect()를 그대로 쓴다(명령끼리 부르는 예외, docs/spec/map.md).
"""
import contextlib
import json
import os
import sys
import traceback

from .. import __version__
from ..core import HabitreeError
from ..core.i18n import t, tr

SUMMARY = {"ko": "MCP 서버(표준 입출력): AI 도구가 map_find·map_show·rules_brief·check를 부르게 함",
           "en": "MCP server over stdio: lets AI tools call map_find, map_show, rules_brief and check"}

SUPPORTED = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
LATEST = SUPPORTED[0]
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32700, -32600, -32601, -32602, -32603
MAX_BUDGET = 20000

INSTRUCTIONS = {
    "ko": "새 함수·모듈·도구를 만들기 전에 map_find로 이미 있는 것을 먼저 찾는다. 처음 보는 코드는 map_show로 "
          "많이 쓰이는 정의부터 본다. 작업 전에는 rules_brief로 지킬 규칙을 읽고, 끝내기 전에는 check로 점검한다.",
    "en": "Before writing a new function, module or tool, call map_find to see whether it already exists. "
          "For unfamiliar code, call map_show to see the most used definitions first. Read rules with rules_brief "
          "before work and run check before finishing.",
}

TOOLS = [
    {"name": "map_find",
     "title": {"ko": "이미 있는 코드 찾기", "en": "Find existing code"},
     "description": {
         "ko": "이 프로젝트에 이미 있는 함수·클래스·모듈·문서 구역을 이름이나 설명으로 찾는다. 새로 만들기 전에 먼저 부른다. "
               "snake·camel 이름을 낱말로 나눠 맞추고, 앞부분만 맞아도 찾으며, 한국어는 조사가 붙어도 찾는다. "
               "level 1은 한 줄 요약, 2는 시그니처와 설명, 3은 몸통까지.",
         "en": "Find functions, classes, modules and doc sections that already exist in this project, by name or "
               "description. Call it before writing something new. Splits snake/camel names, matches prefixes, and "
               "handles Korean particles. level 1 is one line each, 2 adds signature and doc, 3 adds the body."},
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "찾을 말 / words to search for"},
         "level": {"type": "integer", "enum": [1, 2, 3], "default": 1},
         "limit": {"type": "integer", "minimum": 1, "maximum": 50}},
         "required": ["query"]}},
    {"name": "map_show",
     "title": {"ko": "코드 지도", "en": "Code map"},
     "description": {
         "ko": "다른 파일에서 많이 쓰이는 정의부터 글자 예산 안에 담은 코드 지도. 처음 보는 프로젝트나 폴더의 큰 그림을 볼 때 쓴다. "
               "focus에 경로(src/api)나 낱말(auth)을 주면 그쪽에 무게를 준다.",
         "en": "A code map of the most used definitions, cut to a character budget. Use it to get the big picture of "
               "an unfamiliar project or folder. Give focus paths (src/api) or words (auth) to weight toward them."},
     "inputSchema": {"type": "object", "properties": {
         "focus": {"type": "array", "items": {"type": "string"}},
         "budget": {"type": "integer", "minimum": 200, "maximum": MAX_BUDGET}}}},
    {"name": "rules_brief",
     "title": {"ko": "작업 전 규칙", "en": "Rules before work"},
     "description": {
         "ko": "이 프로젝트에서 사용자가 쌓은 규칙 중 지금 작업 범위의 것만 짧게 돌려준다. 작업을 시작하기 전에 부른다. "
               "scopes를 비우면 global(전체).",
         "en": "Returns, in short form, only the rules for the scopes of the current task, from the rules the user "
               "built up in this project. Call it before starting work. Empty scopes means global (all)."},
     "inputSchema": {"type": "object", "properties": {
         "scopes": {"type": "array", "items": {"type": "string"}},
         "aspect": {"type": "array", "items": {"type": "string"}},
         "must": {"type": "boolean", "description": "필수 규칙만 / must rules only"},
         "budget": {"type": "integer", "minimum": 200, "maximum": MAX_BUDGET}}}},
    {"name": "check",
     "title": {"ko": "점검 요약", "en": "Check summary"},
     "description": {
         "ko": "지도·문서·링크·규칙이 실제 파일과 맞는지 AI 없이 점검하고 요약한다. 작업을 끝내기 전에 부른다. "
               "only에 점검 id 앞부분(docs.link 등)을 주면 그것만. auto가 true면 규칙의 자동 검사 명령도 돌린다(느릴 수 있음).",
         "en": "Checks, without AI, that the map, docs, links and rules match the real files, and summarizes. Call it "
               "before finishing. Give check id prefixes in only (docs.link, …) to narrow. auto=true also runs the "
               "rules' automatic check commands (can be slow)."},
     "inputSchema": {"type": "object", "properties": {
         "only": {"type": "array", "items": {"type": "string"}},
         "auto": {"type": "boolean", "default": False}}}},
]


def add_arguments(p):
    p.add_argument("--budget", type=int, help="도구 결과의 글자 예산 / character budget for tool results")


class ToolError(Exception):
    """도구 실행 오류: isError 결과로 돌려준다(AI가 읽고 고칠 수 있게). / Returned as an isError result."""


def _strs(value, name):
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ToolError({"ko": f"'{name}'는 글자열 목록이어야 합니다", "en": f"'{name}' must be a list of strings"})
    return [v for v in value if v.strip()]


def _int(value, name, lo, hi, default):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise ToolError({"ko": f"'{name}'는 정수여야 합니다", "en": f"'{name}' must be an integer"})
    return max(lo, min(hi, int(value)))


def _safe_focus(items, lang):
    """작업 폴더 밖을 가리키는 경로는 받지 않는다. / Reject paths that leave the project folder."""
    for item in items:
        norm = item.replace("\\", "/")
        if os.path.isabs(item) or norm.startswith("/") or ".." in norm.split("/") or (len(norm) > 1 and norm[1] == ":"):
            raise ToolError("작업 폴더 안의 상대 경로만 받습니다: " + item if lang == "ko"
                            else "Only relative paths inside the project folder are accepted: " + item)
    return items


def _cut(text, budget, lang):
    if not budget or len(text) <= budget:
        return text
    note = (f"\n(결과가 길어 {budget}자에서 잘랐습니다. 더 좁혀서 다시 부르세요)" if lang == "ko"
            else f"\n(Cut at {budget} characters. Call again with a narrower request.)")
    keep = text[:max(0, budget - len(note))]
    if "\n" in keep:
        keep = keep[:keep.rfind("\n")]
    return keep + note


class Server:
    def __init__(self, ctx, out, budget):
        self.ctx, self.out, self.budget = ctx, out, budget
        self.version = None
        self.lang = ctx.lang
        self.idx = None

    def index(self):
        """메모리의 색인을 바뀐 파일만 고쳐 쓴다(부를 때마다 최신). / In-memory index, refreshed per call."""
        from ..mapper import index
        self.idx = index.build(self.ctx, prev=self.idx)[0]
        return self.idx

    # ── 보내기 ──

    def send(self, msg):
        line = json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n"
        self.out.write(line.encode("utf-8"))
        self.out.flush()

    @staticmethod
    def error(mid, code, message, data=None):
        err = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return {"jsonrpc": "2.0", "id": mid, "error": err}

    # ── 받기 ──

    def handle_line(self, raw):
        raw = raw.strip()
        if not raw:
            return None
        try:
            msg = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as e:
            return self.error(None, PARSE_ERROR, f"Parse error: {e}")
        if isinstance(msg, list):
            if not msg:
                return self.error(None, INVALID_REQUEST, "Invalid Request: empty batch")
            out = [r for r in (self.handle(m) for m in msg) if r is not None]
            return out or None
        return self.handle(msg)

    def handle(self, msg):
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            return self.error(msg.get("id") if isinstance(msg, dict) else None, INVALID_REQUEST, "Invalid Request")
        method = msg.get("method")
        if method is None:
            return None  # 클라이언트가 보낸 응답(우리는 요청을 보내지 않으므로 무시)
        is_request = "id" in msg
        mid = msg.get("id")
        if not isinstance(method, str):
            return self.error(mid, INVALID_REQUEST, "Invalid Request: method must be a string") if is_request else None
        params = msg.get("params") or {}
        if not is_request:
            return None  # 알림(notifications/initialized, cancelled 등)에는 답하지 않는다
        if not isinstance(params, dict):
            return self.error(mid, INVALID_PARAMS, "Invalid params: params must be an object")
        handler = {"initialize": self.initialize, "ping": lambda p: {}, "tools/list": self.tools_list,
                   "tools/call": self.tools_call}.get(method)
        if handler is None:
            return self.error(mid, METHOD_NOT_FOUND, f"Method not found: {method}")
        try:
            result = handler(params)
        except _ProtocolError as e:
            return self.error(mid, e.code, e.message)
        except Exception as e:  # 서버가 죽지 않게
            traceback.print_exc(file=sys.stderr)
            return self.error(mid, INTERNAL_ERROR, f"Internal error: {e}")
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    # ── 메서드 ──

    def initialize(self, params):
        asked = params.get("protocolVersion")
        self.version = asked if asked in SUPPORTED else LATEST
        info = {"name": "habitree", "version": __version__}
        if self.version >= "2025-06-18":
            info["title"] = "Habitree"
        return {"protocolVersion": self.version, "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": info, "instructions": tr(INSTRUCTIONS, self.lang)}

    def tools_list(self, params):
        version = self.version or LATEST
        out = []
        for tool in TOOLS:
            item = {"name": tool["name"], "description": tr(tool["description"], self.lang),
                    "inputSchema": tool["inputSchema"]}
            if version >= "2025-06-18":
                item["title"] = tr(tool["title"], self.lang)
            if version >= "2025-03-26":
                item["annotations"] = {"readOnlyHint": tool["name"] != "check", "openWorldHint": False}
            out.append(item)
        return {"tools": out}

    def tools_call(self, params):
        name = params.get("name")
        args = params.get("arguments") or {}
        fn = {"map_find": self.map_find, "map_show": self.map_show, "rules_brief": self.rules_brief,
              "check": self.check}.get(name)
        if fn is None:
            raise _ProtocolError(INVALID_PARAMS, f"Unknown tool: {name}")
        if not isinstance(args, dict):
            return self._result(tr({"ko": "'arguments'는 객체여야 합니다", "en": "'arguments' must be an object"},
                                   self.lang), True)
        try:
            text = fn(args)
        except ToolError as e:
            return self._result(tr(e.args[0], self.lang), True)
        except HabitreeError as e:
            return self._result(str(e), True)
        return self._result(_cut(text, self.budget, self.lang), False)

    @staticmethod
    def _result(text, is_error):
        return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}

    # ── 도구 ──

    def map_find(self, args):
        from ..mapper import search
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ToolError({"ko": "'query'가 필요합니다(빈 글이 아닌 글자열)",
                             "en": "'query' is required (a non-empty string)"})
        level = _int(args.get("level"), "level", 1, 3, 1)
        limit = _int(args.get("limit"), "limit", 1, 50, 3 if level == 3 else self.ctx.get("map.find_limit", 10))
        _, text = search.find(self.ctx.root, self.index(), query.strip(), level, limit, self.budget, self.lang, via="mcp")
        return text

    def map_show(self, args):
        from ..mapper import rank
        focus = _safe_focus(_strs(args.get("focus"), "focus"), self.lang)
        default = min(self.ctx.get("map.show_budget", 4000) or 4000, self.budget or MAX_BUDGET)
        budget = _int(args.get("budget"), "budget", 200, MAX_BUDGET, default)
        return rank.show(self.index(), focus, budget, self.lang)

    def rules_brief(self, args):
        from ..core.ruledb import RuleDB
        db_path = self.ctx.p(self.ctx.get("rules.db"))
        if not db_path.exists():
            raise ToolError(t("no_db", self.lang, path=self.ctx.get("rules.db")))
        db = RuleDB.load(db_path, self.lang)
        scopes = _strs(args.get("scopes"), "scopes") or ["global"]
        aspects = _strs(args.get("aspect"), "aspect") or None
        must = bool(args.get("must", False))
        default = min(self.ctx.get("rules.brief_budget", 6000) or 6000, self.budget or MAX_BUDGET)
        budget = _int(args.get("budget"), "budget", 200, MAX_BUDGET, default)
        bad = db.unknown_names(scopes, aspects, None)
        if bad:
            known = ", ".join(sorted(db.scopes))
            raise ToolError((f"없는 범위·관점: {', '.join(bad)}. 있는 범위: {known}" if self.lang == "ko"
                             else f"Unknown scope or aspect: {', '.join(bad)}. Known scopes: {known}"))
        return db.brief(scopes, aspects, None, must, budget, self.lang)

    def check(self, args):
        from . import check as check_cmd
        only = _strs(args.get("only"), "only")
        auto = bool(args.get("auto", False))
        findings, files = check_cmd.collect(self.ctx, no_auto=not auto)[:2]
        if only:
            findings = [f for f in findings if check_cmd._match(f.id, only)]
        findings.sort(key=lambda f: (check_cmd.LEVEL_ORDER[f.level], f.id, f.path, f.line))
        ko = self.lang == "ko"
        counts = {lv: sum(1 for f in findings if f.level == lv) for lv in ("error", "warn", "info")}
        if not findings:
            return (f"점검: 문제 없음 (파일 {len(files)}개)" if ko else f"Check: no problems ({len(files)} files)")
        head = (f"점검: 오류 {counts['error']} · 경고 {counts['warn']} · 알림 {counts['info']} (파일 {len(files)}개)"
                if ko else f"Check: errors {counts['error']} · warnings {counts['warn']} · notices {counts['info']} "
                           f"({len(files)} files)")
        lines = [head]
        for f in findings[:30]:
            loc = f"{f.path}:{f.line}" if f.line else f.path
            lines.append(f"- [{tr(check_cmd.LEVEL_TEXT[f.level], self.lang)}] {f.id} {loc}: {tr(f.msg, self.lang)}")
        if len(findings) > 30:
            lines.append(f"(나머지 {len(findings) - 30}개는 only로 좁혀 보기)" if ko
                         else f"({len(findings) - 30} more; narrow with only)")
        return "\n".join(lines)


class _ProtocolError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def serve(ctx, stdin, stdout, budget):
    server = Server(ctx, stdout, budget)
    while True:
        raw = stdin.readline()
        if not raw:
            break  # stdin이 닫히면 끝낸다
        reply = server.handle_line(raw)
        if reply is not None:
            server.send(reply)


def run(args, ctx):
    budget = args.budget if args.budget is not None else ctx.get("map.mcp_budget", 4000)
    out = getattr(sys.stdout, "buffer", None)
    stdin = getattr(sys.stdin, "buffer", None)
    if out is None or stdin is None:
        print("habitree mcp: binary stdio is required", file=sys.stderr)
        return 2
    print(f"habitree mcp {__version__}: stdio ready", file=sys.stderr)
    with contextlib.redirect_stdout(sys.stderr):  # stdout에는 MCP 메시지만
        try:
            serve(ctx, stdin, out, budget)
        except KeyboardInterrupt:
            pass
    return 0
