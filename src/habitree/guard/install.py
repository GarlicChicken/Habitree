"""훅 연결 정의: 플러그인의 hooks/hooks.json과 `init --hooks`가 같은 정의를 쓴다(원본은 하나).
/ Hook wiring shared by the plugin's hooks/hooks.json and `init --hooks` (one source).

훅은 셸을 거치지 않는 exec 형식(command + args)으로 `habitree hook <이벤트>`를 부른다.
셸 문법이 없어 bash·zsh·PowerShell·cmd 어디서나 같게 돈다. Windows exec 형식은 진짜 실행 파일이 필요한데,
`uv tool install`·`pipx install`이 만드는 `habitree` 실행 파일이 그 역할을 한다.
"""
import copy
import json
from pathlib import Path

from ..core import HabitreeError
from ..core import io as hio

COMMAND = "habitree"
# (이벤트, 시간 한도 초). Stop은 빠른 점검을 돌리므로 넉넉히. / (event, timeout seconds)
EVENTS = [("SessionStart", 30), ("UserPromptSubmit", 10), ("PreToolUse", 10), ("PostToolUse", 15),
          ("PostToolUseFailure", 10), ("Stop", 60)]
SETTINGS_REL = ".claude/settings.json"


def handler(event, timeout):
    return {"type": "command", "command": COMMAND, "args": ["hook", event], "timeout": timeout}


def hooks_map():
    """settings.json·hooks.json의 "hooks" 안쪽. 맞춤 조건(matcher)을 비워 모든 도구에 건다.
    / The inner "hooks" map; no matcher, so it applies to every tool."""
    return {event: [{"hooks": [handler(event, timeout)]}] for event, timeout in EVENTS}


def plugin_hooks_file():
    return {"description": "Habitree: 작업 중 비효율을 먼저 알리고, 위임을 기록하고, 끝내기 전에 점검한다. / "
                           "Warns about inefficient work early, records delegation, checks before finishing.",
            "hooks": hooks_map()}


def _has(groups, event):
    for g in groups or []:
        for h in (g or {}).get("hooks") or []:
            cmd, args = h.get("command", ""), h.get("args") or []
            if isinstance(cmd, str) and cmd.split("/")[-1].split("\\")[-1].lower().startswith(COMMAND) and \
                    list(args[:2]) == ["hook", event]:
                return True
            if isinstance(cmd, str) and f"{COMMAND} hook {event}" in cmd:
                return True
    return False


def merge_settings(root, dry=False):
    """프로젝트 .claude/settings.json에 훅을 더한다. 있는 내용은 그대로, 이미 있으면 다시 넣지 않는다.
    사용자 전역 설정(~/.claude/settings.json)은 건드리지 않는다. 돌려주는 값: 더한 이벤트 목록.
    / Merge hooks into the project settings, keeping existing content; never the user-global file."""
    path = Path(root) / SETTINGS_REL
    home = Path.home() / SETTINGS_REL
    try:
        same = path.resolve() == home.resolve()
    except OSError:
        same = False
    if same:
        raise HabitreeError("이 폴더의 .claude/settings.json은 사용자 전역 설정과 같은 파일이라 건드리지 않습니다. / "
                            "This .claude/settings.json is your user-global settings file; not touching it.")
    try:
        data = hio.load_json(path, {}) or {}
    except json.JSONDecodeError as e:
        raise HabitreeError(f"{SETTINGS_REL} JSON이 깨져 고치지 않았습니다 / Broken JSON, not changed: {e}")
    if not isinstance(data, dict):
        raise HabitreeError(f"{SETTINGS_REL}의 맨 위가 객체가 아닙니다 / Top level is not an object")
    new = copy.deepcopy(data)
    hooks = new.setdefault("hooks", {})
    added = []
    for event, timeout in EVENTS:
        groups = hooks.setdefault(event, [])
        if _has(groups, event):
            continue
        groups.append({"hooks": [handler(event, timeout)]})
        added.append(event)
    if added and not dry:
        hio.save_json(path, new)
    return added
