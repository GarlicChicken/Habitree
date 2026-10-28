"""Claude Code 어댑터: 훅 입력 JSON → 표준 이벤트, 판정 결과 → 훅 출력 JSON.
/ Claude Code adapter: hook input JSON to a normalized event, outcome to hook output JSON.

형식은 공식 훅 문서(https://code.claude.com/docs/en/hooks)를 따른다.
- 공통 입력: session_id, transcript_path, cwd, hook_event_name. 도구 이벤트는 tool_name, tool_input, tool_use_id.
- PostToolUse는 tool_response, PostToolUseFailure는 error·is_interrupt, UserPromptSubmit은 prompt,
  SessionStart는 source, Stop은 stop_hook_active·last_assistant_message.
- 출력: AI 맥락은 hookSpecificOutput.additionalContext(hookEventName 필수), 사용자에게는 systemMessage,
  PreToolUse는 permissionDecision(ask·deny)과 permissionDecisionReason, Stop은 decision "block"과 reason.
- 글 한 칸은 10,000자 한도라 그 안으로 자른다.
"""
import os
from pathlib import Path

from ..core.paths import nfc, rel
from .events import Event, error_parts, output_length, signature, target_path

EVENTS = {"SessionStart": "start", "UserPromptSubmit": "prompt", "PreToolUse": "pre", "PostToolUse": "post",
          "PostToolUseFailure": "post", "Stop": "stop"}
MAX_FIELD = 9000


def to_event(name, payload, root, keyfn):
    kind = EVENTS[name]
    ev = Event(kind, name, session=str(payload.get("session_id") or ""),
               tool=str(payload.get("tool_name") or ""), input=payload.get("tool_input") or {},
               tool_id=str(payload.get("tool_use_id") or ""), prompt=str(payload.get("prompt") or ""),
               source=str(payload.get("source") or ""), stop_active=payload.get("stop_hook_active"),
               last_message=str(payload.get("last_assistant_message") or ""))
    if kind == "post":
        if name == "PostToolUseFailure":
            ev.ok = None if payload.get("is_interrupt") else False
            ev.error = str(payload.get("error") or "")
            ev.error_key, ev.error_line = error_parts(ev.error)
        else:
            ev.ok = True
            ev.out_len = output_length(payload.get("tool_response"))
    if kind == "prompt" and payload.get("transcript_path"):
        try:
            ev.transcript_bytes = os.path.getsize(os.path.expanduser(str(payload["transcript_path"])))
        except OSError:
            ev.transcript_bytes = 0
    path = target_path(ev.tool, ev.input)
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = Path(payload.get("cwd") or root) / p
        ev.path = str(p)
        ev.fkey = keyfn(str(p))
        ev.rel = nfc(rel(root, p))
    if ev.tool:
        ev.sig = signature(ev.tool, ev.input, keyfn)
    return ev


def render(name, out, lang, relay=True):
    """판정 결과를 공식 훅 출력으로. 할 말이 없으면 빈 dict. / Outcome to official hook output."""
    res = {}
    user = [u for u in out.user if u]
    if user:
        res["systemMessage"] = _cut("\n\n".join(user))
    if name == "Stop":
        if out.block:
            res["decision"] = "block"
            res["reason"] = _cut("\n\n".join(out.block))
        return res
    lines = list(out.ai)
    if relay and out.relay:
        from .texts import t
        lines += [t("relay", lang, line=r.replace("\n", " ")) for r in out.relay]
    hso = {"hookEventName": name}
    if lines:
        hso["additionalContext"] = _cut("\n".join(lines))
    if name == "PreToolUse" and out.permission:
        hso["permissionDecision"] = out.permission
        hso["permissionDecisionReason"] = _cut("\n".join(out.reasons))
    if len(hso) > 1:
        res["hookSpecificOutput"] = hso
    return res


def _cut(text):
    return text if len(text) <= MAX_FIELD else text[:MAX_FIELD - 3] + "..."
