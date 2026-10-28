"""Markdown 읽기: 링크, 제목 앵커, 생성 구역. / Links, heading anchors and managed blocks."""
import hashlib
import re
import unicodedata

FENCE = re.compile(r"^(```|~~~)")
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
HTML_SRC = re.compile(r"""\b(?:src|href)=["']([^"']+)["']""")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
INLINE_CODE = re.compile(r"`+[^`]*`+")


def strip_code(text):
    """코드 블록과 인라인 코드를 빈 줄로(줄 번호는 유지). / Blank out code, keep line numbers."""
    out, in_fence = [], False
    for line in text.split("\n"):
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else INLINE_CODE.sub("", line))
    return out


def links(text):
    """(줄 번호, 대상) 목록. 코드 안 링크는 뺀다. / (line, target) pairs outside code."""
    out = []
    for i, line in enumerate(strip_code(text), 1):
        for rx in (LINK, IMAGE, HTML_SRC):
            for m in rx.finditer(line):
                out.append((i, m.group(1)))
    return out


def slug(title):
    """GitHub 방식 제목 앵커(한글 유지). / GitHub-style anchor, keeps Hangul."""
    title = unicodedata.normalize("NFC", title).strip().lower()
    title = re.sub(r"<[^>]+>", "", title)
    title = re.sub(r"`", "", title)
    title = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)
    out = []
    for ch in title:
        cat = unicodedata.category(ch)
        if ch in "-_" or cat[0] in "LN" or cat == "Mn":
            out.append(ch)
        elif ch == " ":
            out.append("-")
    return "".join(out)


def anchors(text):
    """문서 안의 모든 제목 앵커(중복은 -1, -2). / All heading anchors."""
    seen, out = {}, set()
    for line in strip_code_keep_headings(text):
        m = HEADING.match(line)
        if not m:
            continue
        s = slug(m.group(2))
        if s in seen:
            seen[s] += 1
            s2 = f"{s}-{seen[s]}"
        else:
            seen[s] = 0
            s2 = s
        out.add(s2)
    for m in re.finditer(r"""<a\s+(?:name|id)=["']([^"']+)["']""", text):
        out.add(m.group(1))
    return out


def strip_code_keep_headings(text):
    out, in_fence = [], False
    for line in text.split("\n"):
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return out


# ── 생성 구역: 도구가 만든 부분만 고치고 사람이 쓴 부분은 건드리지 않는다 ──

def _markers(name):
    return f"<!-- habitree:begin {name} -->", f"<!-- habitree:end {name} -->"


def get_block(text, name):
    b, e = _markers(name)
    i, j = text.find(b), text.find(e)
    if i < 0 or j < 0 or j < i:
        return None
    return text[i + len(b):j].strip("\n")


def put_block(text, name, content, where="end"):
    """구역을 바꾸거나(있으면) 더한다(없으면). / Replace or insert a managed block."""
    b, e = _markers(name)
    block = f"{b}\n{content.strip()}\n{e}"
    i, j = text.find(b), text.find(e)
    if i >= 0 and j > i:
        return text[:i] + block + text[j + len(e):]
    if i >= 0 or j >= 0:
        raise ValueError(f"구역 표시가 깨졌습니다(시작·끝 중 하나만 있음): {name}")
    if where == "start":
        return block + "\n\n" + text.lstrip("\n")
    return text.rstrip("\n") + ("\n\n" if text.strip() else "") + block + "\n"


def digest(content):
    return hashlib.sha256((content or "").strip().encode("utf-8")).hexdigest()[:16]
