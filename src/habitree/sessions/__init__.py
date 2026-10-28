"""세션 기록 읽기: AI 코딩 도구가 남긴 기록을 공통 레코드(model.py)로 바꾼다. / Read AI coding tool transcripts.

도구마다 어댑터가 하나다. 어댑터는 NAME, SUPPORTED, scan(root, claude_dir=None, folders=None) -> model.Scan을 둔다.
기록은 이 컴퓨터 안에서만 읽고 어디에도 보내거나 저장하지 않는다. audit과 bench가 부를 때만 돈다.
"""
from . import claude, codex

ADAPTERS = {claude.NAME: claude, codex.NAME: codex}
