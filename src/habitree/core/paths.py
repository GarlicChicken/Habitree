"""경로: 같은 파일은 어느 OS에서나 같은 키로. / One key per file on every OS.

- 한글 파일 이름은 NFC로 맞춘다(macOS는 NFD로 기록하는 경우가 있다).
- 키는 루트 기준 상대 경로, 구분자는 '/'.
- 대소문자를 구분하지 않는 파일 시스템(Windows·macOS 기본)이면 키를 casefold한다.
- 외부 명령은 git 하나만 쓴다(셸을 거치지 않는다).
"""
import fnmatch
import os
import re
import shutil
import subprocess
import unicodedata
from functools import lru_cache
from pathlib import Path

DEFAULT_EXCLUDES = [
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".tox", ".nox", "dist", "build", ".next", ".nuxt", ".cache",
    "target", ".gradle", ".idea", ".vscode", ".habitree/state", "coverage", ".turbo",
]


def nfc(s):
    return unicodedata.normalize("NFC", s)


def find_root(start=None):
    """설정(.habitree/config.json) → git → 시작 폴더 순서로 프로젝트 루트를 찾는다."""
    start = Path(start or os.getcwd()).resolve()
    for d in [start, *start.parents]:
        if (d / ".habitree" / "config.json").is_file():
            return d
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return start


def rel(root, path):
    """루트 기준 상대 경로 문자열(NFC, '/'). / Relative POSIX path in NFC."""
    try:
        r = Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        r = Path(path)
    return nfc(r.as_posix())


@lru_cache(maxsize=64)
def case_insensitive(root):
    """이 폴더가 대소문자를 구분하지 않는가. / Is this filesystem case-insensitive?"""
    root = str(root)
    probe = os.path.join(root, ".HabitreeCaseProbe")
    try:
        with open(probe, "w"):
            pass
        return os.path.exists(os.path.join(root, ".habitreecaseprobe"))
    except OSError:
        return os.name == "nt"
    finally:
        try:
            os.remove(probe)
        except OSError:
            pass


def path_key(root, path, ci=None):
    """상태·색인에 쓰는 파일 키. / Stable key for state and indexes.

    ci: 대소문자 무시 여부를 이미 알면 넘긴다(훅처럼 자주 부를 때 매번 확인하지 않게).
    / Pass ci when already known, so frequent callers such as hooks skip the probe."""
    k = rel(root, path) if os.path.isabs(str(path)) else nfc(str(path).replace("\\", "/"))
    k = re.sub(r"^\./", "", k)
    if ci is None:
        ci = case_insensitive(str(Path(root).resolve()))
    return k.casefold() if ci else k


def _glob_regex(pattern):
    """'**'를 지원하는 글롭 → 정규식. / Glob with '**' to regex."""
    pattern = nfc(pattern.replace("\\", "/"))
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def glob_match(relpath, pattern):
    relpath = nfc(relpath.replace("\\", "/"))
    if "/" not in pattern and "**" not in pattern:
        return fnmatch.fnmatchcase(relpath.rsplit("/", 1)[-1], nfc(pattern))
    return bool(_glob_regex(pattern).match(relpath))


def is_excluded(relpath, excludes):
    parts = relpath.split("/")
    for ex in excludes:
        ex = ex.strip("/")
        if "/" in ex:
            if relpath == ex or relpath.startswith(ex + "/"):
                return True
        elif ex in parts:
            return True
    return False


def resolve(root, relpath):
    """NFC 상대 경로로 디스크의 실제 경로를 찾는다(NFD로 저장된 이름도). 없으면 None.
    / Find the real on-disk path for an NFC relative path, even if stored as NFD."""
    root = Path(root)
    direct = root / relpath
    if direct.exists():
        return direct
    cur = root
    for seg in nfc(relpath.replace("\\", "/")).split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            cur = cur.parent
            continue
        nxt = cur / seg
        if nxt.exists():
            cur = nxt
            continue
        try:
            match = next((c for c in cur.iterdir() if nfc(c.name) == seg), None)
        except OSError:
            return None
        if match is None:
            return None
        cur = match
    return cur


def git_exe():
    return shutil.which("git")


def git(root, *args, timeout=20):
    """git을 셸 없이 부른다. 없거나 실패하면 None. / Run git without a shell."""
    exe = git_exe()
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-C", str(root), *args], capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def iter_files(root, excludes=None):
    """프로젝트 파일(상대 경로 NFC). git이 있으면 .gitignore를 따른다. / Project files."""
    root = Path(root)
    excludes = list(DEFAULT_EXCLUDES if excludes is None else excludes)
    out = git(root, "ls-files", "-co", "--exclude-standard", "-z")
    if out is not None:
        seen = []
        for raw in out.split(b"\0"):
            if not raw:
                continue
            p = nfc(raw.decode("utf-8", errors="replace"))
            if not is_excluded(p, excludes) and (root / p).is_file():
                seen.append(p)
        return sorted(set(seen))
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rd = rel(root, dirpath)
        rd = "" if rd == "." else rd
        dirnames[:] = [d for d in dirnames if not is_excluded((rd + "/" + d).lstrip("/"), excludes)]
        for f in filenames:
            p = (rd + "/" + f).lstrip("/")
            if not is_excluded(p, excludes):
                found.append(nfc(p))
    return sorted(found)


def top_dirs(root, excludes=None):
    """지도에 올라야 할 최상위 폴더(숨김·'_' 시작 제외). / Top-level folders for the map."""
    excludes = DEFAULT_EXCLUDES if excludes is None else excludes
    out = []
    for d in Path(root).iterdir():
        name = nfc(d.name)
        if d.is_dir() and not name.startswith((".", "_")) and not is_excluded(name, excludes):
            out.append(name)
    return sorted(out)
