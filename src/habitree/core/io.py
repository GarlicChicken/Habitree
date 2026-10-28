"""입출력: 세 OS에서 같게 읽고 쓴다. / I/O that behaves the same on Windows, macOS and Linux.

- 읽기는 UTF-8(BOM 허용), 쓰기는 UTF-8(BOM 없음)·LF.
- 쓰기는 임시 파일에 쓴 뒤 바꿔치기한다(동시에 도는 훅이 반쯤 쓴 파일을 읽지 않게).
- 표준 입출력은 바이트로 다뤄 콘솔 코드 페이지(cp949 등)에 흔들리지 않는다.
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path


def setup_stdio():
    """콘솔이면 못 그리는 글자를 ?로, 파이프면 UTF-8로. / Never crash on console encoding."""
    for stream in (sys.stdout, sys.stderr):
        if not hasattr(stream, "reconfigure"):
            continue
        try:
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def read_bytes_text(data):
    """바이트를 글로. UTF-8이 아니면 cp949, 그래도 안 되면 대체 문자. / Decode leniently."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_text(path):
    """줄 끝을 LF로 맞춘 글. / Text with LF line endings."""
    text = read_bytes_text(Path(path).read_bytes())
    return text.replace("\r\n", "\n").replace("\r", "\n")


def write_text(path, text):
    """UTF-8·LF로 원자적으로 쓴다. / Atomic UTF-8 + LF write."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").encode("utf-8")
    fd, tmp = tempfile.mkstemp(prefix=".ht-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        for attempt in range(5):  # Windows: 다른 프로그램이 잠깐 잡고 있으면 다시 시도
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(read_text(path))


def dumps(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def save_json(path, data):
    write_text(path, dumps(data))


def read_stdin_json():
    """훅 입력: 표준 입력의 JSON. 비었거나 깨졌으면 빈 dict. / Hook input from stdin."""
    try:
        raw = sys.stdin.buffer.read()
    except (OSError, AttributeError, ValueError):
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(read_bytes_text(raw))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def emit_json(obj):
    """표준 출력에 JSON 한 줄(UTF-8 바이트). 훅과 MCP용. / One JSON line to stdout."""
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    out = getattr(sys.stdout, "buffer", None)
    if out is not None:
        out.write(line.encode("utf-8"))
        out.flush()
    else:
        sys.stdout.write(line)
        sys.stdout.flush()
