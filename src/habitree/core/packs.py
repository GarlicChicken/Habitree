"""기본 규칙 꾸러미 읽기. / Reading the bundled rule packs.

기본 꾸러미(base, work, task)는 프로젝트 규칙 DB에 옮겨 적지 않고 패키지에서 바로 읽는다(LIVE).
사용자가 그 규칙에 반응하거나 고칠 때만 그 규칙 하나가 프로젝트 DB에 남는다. 그래서 새 프로젝트는
규칙 0개로 시작하고, 프로젝트 DB에는 그 프로젝트에서 실제로 받은 피드백만 자란다.
일반 규칙은 기계 점검(check의 자동 검사)·훅·리팩토링 기준값이 쓰고, AI가 매번 읽는 지침에는 싣지 않는다.
꾸러미를 통째로 옮겨 적고 싶으면 `habitree init --packs base work task`.

훅처럼 자주 도는 길에서도 쓰므로 무거운 모듈을 불러오지 않는다.
"""
import json
from pathlib import Path

INSTALLED = ()
LIVE = ("base", "work", "task")
_DIR = Path(__file__).resolve().parent.parent / "data" / "packs"


def load_pack(name):
    with open(_DIR / f"{name}.json", "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def available():
    return sorted(p.stem for p in _DIR.glob("*.json"))


def live_rules(data, names=LIVE):
    """프로젝트 DB(data)에 없는 살아 있는 꾸러미 규칙들. 이미 옮겨 적은 꾸러미는 건너뛴다.
    / Live pack rules missing from the project DB; packs already copied in are skipped."""
    have = {r.get("id") for r in data.get("rules") or []}
    copied = data.get("packs") or {}
    out = []
    for name in names:
        if name in copied:
            continue
        try:
            pack = load_pack(name)
        except (OSError, ValueError):
            continue
        for r in pack.get("rules", []):
            if r.get("id") not in have:
                out.append(r)
    return out
