"""복사 코드 찾기: 새로 쓴 줄 묶음이 다른 파일에 이미 있는지 줄 해시로 본다.
/ Copy detection: are newly written lines already present in another file? Line-window hashes.

언어와 무관하게 돈다. 줄 앞뒤 공백을 지우고, 빈 줄·주석만 있는 줄·괄호만 있는 줄을 뺀 뒤
연속된 k줄(기본 6줄)씩 해시한다. 이름만 바꾼 복사는 못 잡는다(그건 jscpd 같은 언어별 도구의 몫).
"""
import difflib
import hashlib
import os
import re

from ..core.paths import nfc
from .events import read_text_small

_COMMENT = re.compile(r"^(#|//|--|;|/\*|\*|<!--|%|rem\s)", re.I)
_TRIVIAL = re.compile(r"^[\W_]*$")
MAX_DIFF_LINES = 3000


def norm_lines(text):
    """[(원래 줄 번호, 정리한 줄)] 의미 있는 줄만. / Significant lines with their line numbers."""
    out = []
    for i, raw in enumerate(nfc(text).split("\n"), 1):
        s = " ".join(raw.split())
        if len(s) < 4 or _TRIVIAL.match(s) or _COMMENT.match(s):
            continue
        out.append((i, s))
    return out


def window_hashes(lines, k, min_chars):
    """정리한 줄 목록에서 k줄 창 해시 {해시: 첫 줄 정리본}. / k-line window hashes."""
    out = {}
    texts = [s for _, s in lines]
    for i in range(len(texts) - k + 1):
        block = texts[i:i + k]
        if sum(len(x) for x in block) < min_chars:
            continue
        out[hashlib.sha1("\n".join(block).encode("utf-8")).hexdigest()[:16]] = block[0]
    return out


def inserted_text(old, new):
    """old → new에서 새로 들어간 줄들(연속 묶음마다 하나의 글). / Inserted runs from old to new."""
    a, b = old.split("\n"), new.split("\n")
    if len(a) > MAX_DIFF_LINES or len(b) > MAX_DIFF_LINES:
        return [new] if not old else []
    runs = []
    for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("insert", "replace") and j2 > j1:
            runs.append("\n".join(b[j1:j2]))
    return runs


def line_delta(old, new):
    """(더한 줄, 지운 줄). git diff처럼 바뀐 줄은 둘 다에 센다. / (added, removed) like git diff."""
    a = old.split("\n") if old else []
    b = new.split("\n") if new else []
    if len(a) > MAX_DIFF_LINES or len(b) > MAX_DIFF_LINES:
        return max(0, len(b) - len(a)), max(0, len(a) - len(b))
    added = removed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("insert", "replace"):
            added += j2 - j1
        if tag in ("delete", "replace"):
            removed += i2 - i1
    return added, removed


def new_windows(runs, k, min_chars):
    """새로 들어간 묶음들의 창 해시 {해시: 첫 줄}. / Window hashes of the inserted runs."""
    out = {}
    for run in runs:
        lines = norm_lines(run)
        if len(lines) >= k:
            out.update(window_hashes(lines, k, min_chars))
    return out


def find_copy(root, files, wanted, k, skip_key, keyfn, max_files=400, max_file_bytes=262144,
              max_total_bytes=8 * 1024 * 1024, prefer_ext=""):
    """다른 파일에서 같은 창을 찾는다. (상대 경로, 줄 번호) 또는 None.
    / Search other files for a matching window: (relative path, line) or None.

    files: [(상대 경로, 크기)] 세션 시작 때 캐시한 목록. 탐색 파일 수·크기에 상한을 둔다."""
    if not wanted:
        return None
    first = {}
    for h, line in wanted.items():
        first.setdefault(line, set()).add(h)
    ordered = sorted(files, key=lambda x: (0 if prefer_ext and x[0].lower().endswith(prefer_ext) else 1, x[0]))
    seen_files = total = 0
    for rel, size in ordered:
        if seen_files >= max_files or total >= max_total_bytes:
            break
        if size > max_file_bytes or keyfn(rel) == skip_key:
            continue
        data = read_text_small(os.path.join(str(root), rel))
        if data is None:
            continue
        seen_files += 1
        total += size
        lines = norm_lines(data)
        texts = [s for _, s in lines]
        for i, s in enumerate(texts):
            hs = first.get(s)
            if not hs or i + k > len(texts):
                continue
            h = hashlib.sha1("\n".join(texts[i:i + k]).encode("utf-8")).hexdigest()[:16]
            if h in hs:
                return rel, lines[i][0]
    return None
