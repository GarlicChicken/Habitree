"""Codex CLI 어댑터 자리. 아직 읽지 않는다. / Placeholder for a Codex CLI adapter.

기록 형식을 공식 문서로 확인하지 못해서다. 조사(B 노트 3.2)에서 다른 도구의 소스로 본 내용은 이렇다.
위치 ${CODEX_HOME:-~/.codex}/sessions/YYYY/MM/DD/rollout-*.jsonl(닫힌 세션은 .jsonl.zst), event_msg의
token_count에 누적값과 직전 응답값, input은 캐시 포함, output은 reasoning 포함, 누적값이 잠깐 줄어드는 일이 있음.
확인되면 claude.py처럼 scan()을 채운다.
"""
from .model import Scan

NAME = "codex"
SUPPORTED = False
REASON = {"ko": "Codex 기록 형식은 공식 문서로 확인하지 못해 아직 읽지 않습니다(sessions/codex.py).",
          "en": "The Codex transcript format is not officially documented, so it is not read yet (sessions/codex.py)."}


def scan(root, claude_dir=None, folders=None):
    return Scan(NAME)
