"""색인: 프로젝트 파일과 심볼을 .habitree/state/map.json에 모은다. / Build and load the code index.

- 파일 키는 루트 기준 NFC 상대 경로('/')다.
- 다시 만들 때는 mtime·크기가 같으면 그대로 두고, 다르면 sha256을 보고, 내용이 바뀐 파일만 다시 읽는다.
- 비밀일 수 있는 파일(.env, 키 파일 등)은 이름으로 처음부터 뺀다. 루트 밖을 가리키는 링크도 뺀다.
- 패턴표·언어표·추출기 판이 바뀌면 전체를 새로 만든다.
"""
import hashlib
import json
import os
import time
import warnings
from collections import Counter

from ..core import io as hio
from ..core.config import STATE_REL
from ..core.paths import glob_match, iter_files, resolve
from ..core.timeutil import now_iso
from . import extract, langs

INDEX_VERSION = 1
INDEX_FILE = "map.json"
INDEX_REL = f"{STATE_REL}/{INDEX_FILE}"
DEFAULT_SECRETS = [
    ".env", ".env.*", "*.env", ".envrc", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore", "*.kdbx",
    "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*", ".npmrc", ".pypirc", ".netrc", ".git-credentials",
    ".htpasswd", "*.tfstate", "*.tfstate.*", "*.tfvars", "credentials*", "*secret*", "*.gpg",
]


def index_path(ctx):
    return ctx.state_dir / INDEX_FILE


def load(ctx):
    """저장된 색인(없거나 깨졌으면 None). / The saved index, or None."""
    p = index_path(ctx)
    if not p.exists():
        return None
    try:
        data = json.loads(hio.read_text(p))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("version") != INDEX_VERSION or not isinstance(data.get("files"), dict):
        return None
    return data


def save(ctx, index):
    path = index_path(ctx)
    hio.write_text(path, json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n")
    ignore = path.parent / ".gitignore"
    if not ignore.exists():  # init 전인 프로젝트에서도 색인이 git에 올라가지 않게
        hio.write_text(ignore, "*\n")


def is_secret(rel, patterns):
    name = rel.rsplit("/", 1)[-1].lower()
    return any(glob_match(name, p.lower()) for p in patterns)


def inside_root(root_real, path):
    try:
        real = os.path.realpath(path)
    except OSError:
        return False
    return real == root_real or real.startswith(root_real.rstrip(os.sep) + os.sep)


def analyze(rel, data, st, sha):
    """파일 하나의 기록. / The record for one file."""
    head = data[:8192]
    lang = langs.detect(rel, head)
    rec = {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "sha256": sha}
    if lang:
        rec["lang"] = lang
    if b"\0" in head:
        rec["skip"] = "binary"
        return rec
    text = hio.read_bytes_text(data).replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    rec["lines"] = len(lines)
    rec["code"] = langs.count_code(lines, lang)
    if not lang or not lines:
        return rec
    if sum(len(x) for x in lines) / len(lines) > 300:
        rec["skip"] = "minified"
        return rec
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ex = extract.extract(lang, text)
    if ex["extractor"]:
        rec["extractor"] = ex["extractor"]
    if ex["symbols"]:
        rec["symbols"] = ex["symbols"]
    if ex["refs"]:
        rec["refs"] = dict(sorted(ex["refs"].items()))
    if ex["doc"]:
        rec["doc"] = ex["doc"]
    return rec


def build(ctx, full=False, prev=None):
    """색인을 만들거나 바뀐 파일만 고친다. (색인, 통계)를 돌려준다. / Build or refresh the index."""
    t0 = time.time()
    if not full and prev is None:
        prev = load(ctx)
    if full or (prev and prev.get("engine") != extract.engine_id()):
        prev = None
    old = (prev or {}).get("files", {})
    excludes = list(ctx.get("exclude") or []) + list(ctx.get("map.exclude") or []) + [".habitree/state"]
    secrets = ctx.get("map.secrets")
    secrets = DEFAULT_SECRETS if secrets is None else secrets
    max_bytes = int(ctx.get("map.max_bytes", 1_000_000) or 1_000_000)
    root_real = os.path.realpath(str(ctx.root))
    files, counts = {}, Counter()
    for rel in iter_files(ctx.root, excludes):
        if is_secret(rel, secrets):
            counts["secret"] += 1
            continue
        p = resolve(ctx.root, rel)
        if p is None:
            continue
        try:
            st = p.stat()
        except OSError:
            counts["unreadable"] += 1
            continue
        o = old.get(rel)
        if o and o.get("size") == st.st_size and o.get("mtime_ns") == st.st_mtime_ns:
            files[rel] = o
            counts["same"] += 1
            continue
        if p.is_symlink() and not inside_root(root_real, p):  # 루트 밖을 가리키는 링크는 읽지 않는다
            counts["outside"] += 1
            continue
        if st.st_size > max_bytes:
            rec = {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "skip": "large"}
            lang = langs.detect(rel)
            if lang:
                rec["lang"] = lang
            files[rel] = rec
            counts["read"] += 1
            continue
        try:
            data = p.read_bytes()
        except OSError:
            counts["unreadable"] += 1
            continue
        sha = hashlib.sha256(data).hexdigest()
        if o and o.get("sha256") == sha:
            files[rel] = dict(o, size=st.st_size, mtime_ns=st.st_mtime_ns)
            counts["touched"] += 1
            continue
        files[rel] = analyze(rel, data, st, sha)
        counts["read"] += 1
    removed = len(set(old) - set(files))
    excluded = {k: counts[k] for k in ("secret", "outside", "unreadable") if counts[k]}
    changed = prev is None or counts["read"] or counts["touched"] or removed or excluded != prev.get("excluded", {})
    if changed:
        index = {"version": INDEX_VERSION, "engine": extract.engine_id(), "built": now_iso(),
                 "files": files, "excluded": excluded}
        save(ctx, index)
    else:
        index = prev
    stats = {"files": len(files), "read": counts["read"], "touched": counts["touched"], "same": counts["same"],
             "removed": removed, "excluded": excluded, "seconds": round(time.time() - t0, 2), "saved": bool(changed)}
    return index, stats


def ensure(ctx):
    """늘 최신인 색인(바뀐 파일만 다시 읽음). / An up-to-date index, refreshing changed files only."""
    return build(ctx)[0]


def totals(index):
    files = index.get("files", {})
    symbols = sum(len(r.get("symbols", [])) for r in files.values())
    unread = sum(1 for r in files.values() if r.get("skip") in ("large", "binary", "minified"))
    return {"files": len(files), "symbols": symbols, "unread": unread,
            "excluded": sum((index.get("excluded") or {}).values())}


def is_test_path(rel):
    low = rel.lower()
    name = low.rsplit("/", 1)[-1]
    return (any(part in ("test", "tests", "__tests__", "spec", "specs", "testing") for part in low.split("/")[:-1])
            or name.startswith("test_") or name.endswith(("_test.py", "_test.go", ".test.ts", ".test.js",
                                                          ".spec.ts", ".spec.js", "test.java", "tests.cs")))
