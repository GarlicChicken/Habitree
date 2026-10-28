"""프로젝트 설정(.habitree/config.json)과 실행 맥락. / Project config and run context."""
import copy
from pathlib import Path

from . import io as hio
from .i18n import LANGS, default_lang
from .paths import DEFAULT_EXCLUDES, find_root

CONFIG_REL = ".habitree/config.json"
STATE_REL = ".habitree/state"

DEFAULTS = {
    "version": 1,
    "lang": None,  # None이면 이 컴퓨터 언어 설정에서 고른다
    "exclude": list(DEFAULT_EXCLUDES),
    "rules": {
        "db": ".habitree/rules.json",
        "doc": ".habitree/RULES.md",
        "brief_budget": 6000,  # rules brief 기본 글자 예산(넘치면 필수 → 권장 순으로 자른다)
    },
    "docs": {
        "map": "README.md",
        "log": "LOG.md",
        "folder_readme": "warn",  # "error" | "warn" | false
        "updated_labels": ["마지막 갱신", "Last updated"],
        "stale_days": 60,
        "instructions": ["AGENTS.md", "CLAUDE.md"],
        "agents_md_max_bytes": 32768,
        "claude_md_max_lines": 200,
    },
    "export": {
        "targets": ["agents", "claude"],
        "brief_budget": 3000,  # AGENTS.md 안에 넣는 필수 규칙 요약의 글자 예산
    },
    "map": {
        "exclude": [],  # 색인에서만 더 뺄 폴더·경로(위 exclude에 더함)
        "secrets": None,  # None이면 기본 목록(mapper/index.py DEFAULT_SECRETS). 파일 이름 글롭
        "max_bytes": 1000000,  # 이보다 큰 파일은 심볼을 뽑지 않는다
        "show_budget": 4000,  # map show 기본 글자 예산
        "find_limit": 10,  # map find 기본 결과 수
        "find_budget": 4000,  # map find 글자 예산
        "mcp_budget": 4000,  # MCP 도구 결과의 글자 예산
        "dupe_window": 6,  # 글 중복을 보는 창(줄)
        "churn_commits": 2000,  # 핫스팟에 쓰는 최근 커밋 수
        "churn_top": 15,
    },
    "verify": {},  # 이름 → 명령 배열. 예: {"test": ["pytest", "-q"]}. 종료 코드 0이 합격
    "models": {  # 모델 배분(habitree models). 설정 파일에 이 절이 없으면 check가 모델 점검을 건너뛴다
        "vendor": "anthropic",       # pick·export가 쓸 회사(대응표 vendors.json의 이름)
        "agents": {},                # 에이전트 이름 → 작업. 예: {"explorer": "task/explore"} (.claude/agents/<이름>.md)
        "claude_model": "id",        # 에이전트 파일에 쓸 값: "id"(고정 ID) | "alias"(opus·sonnet·haiku)
        "deprecation_days": 90,      # 단종일이 이 날 수 안이면 경고
        "price_stale_days": 90,      # 가격·모델 확인일이 이보다 오래되면 알림
        "tune": {"window": 20, "min_runs": 10, "up_ratio": 0.2, "down_ratio": 0.05},
        "escalate": {"max_steps": 2, "max_attempts": 4},
    },
    "checks": {"disable": [], "custom": []},
    "guard": {
        "enabled": True,
        "stop_check": True,        # Stop 때 빠른 점검, 오류면 한 번 더 일하게 / quick check at Stop
        "stop_check_max": 3,       # 세션당 점검으로 막는 최대 횟수 / max check blocks per session
        "session_start": "auto",   # auto | full | short | off: 세션 시작 때 넣는 글 / session start context
        "session_budget": 1500,    # 세션 시작 글의 필수 규칙 글자 예산 / char budget for must rules
        "relay": "always",         # always | never: 사용자 알림을 AI도 함께 전하게 / AI relays user notes
        "history": 40,             # 남기는 최근 호출·결과 수 / recent calls and results kept
        "state_days": 7,           # 세션 상태를 지우기까지 날짜 / days before session state is removed
        "delegate": {"natural": True, "max_tools": 200},  # 말로 한 위임 감지, 위임 한도 / delegation
    },
}


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


class Context:
    """명령이 받는 실행 맥락: 루트, 설정, 언어. / What every command receives."""

    def __init__(self, root, cfg, lang):
        self.root = Path(root)
        self.cfg = cfg
        self.lang = lang

    @classmethod
    def load(cls, path=None, lang=None):
        root = find_root(path)
        raw = hio.load_json(root / CONFIG_REL, {}) or {}
        cfg = deep_merge(DEFAULTS, raw)
        chosen = lang or cfg.get("lang")
        if chosen not in LANGS:
            chosen = default_lang()
        return cls(root, cfg, chosen)

    @property
    def configured(self):
        return (self.root / CONFIG_REL).is_file()

    def p(self, relpath):
        return self.root / relpath

    @property
    def state_dir(self):
        return self.root / STATE_REL

    def get(self, dotted, default=None):
        cur = self.cfg
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur
