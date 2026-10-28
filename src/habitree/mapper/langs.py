"""언어표: 파일 이름·확장자·shebang으로 언어를 고른다. / Pick a language from name, extension or shebang.

표는 scc의 languages.json(MIT)에서 확장자·파일 이름·shebang·주석 표시만 남긴 것이다(NOTICE.md).
언어를 더할 때 코드를 고치지 않는다. data/languages.json에 한 줄을 더하면 된다.
"""
import hashlib
import json
import re
from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=1)
def _raw():
    return resources.files("habitree.data").joinpath("languages.json").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def table():
    """(언어 → 기록, 확장자 → 언어, 파일 이름 → 언어, shebang → 언어). / Lookup tables."""
    langs = json.loads(_raw())["languages"]
    by_ext, by_file, by_bang = {}, {}, {}
    for name, rec in langs.items():
        for e in rec.get("ext", []):
            by_ext.setdefault(e.lower(), name)
        for f in rec.get("files", []):
            by_file.setdefault(f.lower(), name)
        for s in rec.get("shebang", []):
            by_bang.setdefault(s, name)
    return langs, by_ext, by_file, by_bang


def digest():
    return hashlib.sha256(_raw().encode("utf-8")).hexdigest()[:12]


def _shebang(head):
    if not head.startswith(b"#!"):
        return None
    first = head.split(b"\n", 1)[0].decode("utf-8", errors="replace")[2:].strip().split()
    if not first:
        return None
    prog = first[0].rsplit("/", 1)[-1]
    if prog == "env":
        rest = [a for a in first[1:] if not a.startswith("-") and "=" not in a]
        prog = rest[0] if rest else ""
    by_bang = table()[3]
    for cand in (prog, re.sub(r"[\d.]+$", "", prog)):
        if cand in by_bang:
            return by_bang[cand]
    return None


def detect(relpath, head=b""):
    """언어 이름 또는 None. 파일 이름 → 가장 긴 확장자 → shebang 순서. / Language name or None."""
    _, by_ext, by_file, _ = table()
    name = relpath.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name in by_file:
        return by_file[name]
    parts = name.split(".")
    for i in range(1, len(parts)):
        ext = ".".join(parts[i:])
        if ext in by_ext:
            return by_ext[ext]
    return _shebang(head) if head else None


def comments(lang):
    """줄 주석 표시 목록. / Line comment markers."""
    return table()[0].get(lang, {}).get("comment", []) if lang else []


def blocks(lang):
    """여러 줄 주석의 (시작, 끝) 목록. / Block comment pairs."""
    return [tuple(b) for b in table()[0].get(lang, {}).get("block", [])] if lang else []


def count_code(lines, lang):
    """빈 줄과 주석만 있는 줄을 뺀 줄 수(대략). / Non-blank, non-comment lines (approximate)."""
    marks = tuple(comments(lang))
    pairs = blocks(lang)
    n, closing = 0, None
    for line in lines:
        s = line.strip()
        if closing:
            if closing in s:
                rest = s.split(closing, 1)[1].strip()
                closing = None
                if rest and not rest.startswith(marks or ("\0",)):
                    n += 1
            continue
        if not s or (marks and s.startswith(marks)):
            continue
        opened = next(((a, b) for a, b in pairs if s.startswith(a)), None)
        if opened and opened[1] not in s[len(opened[0]):]:
            closing = opened[1]
            continue
        if opened and s.endswith(opened[1]):
            continue
        n += 1
    return n
