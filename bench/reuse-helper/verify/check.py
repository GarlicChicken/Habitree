"""reuse-helper 채점: 동작 + 이미 있는 slugify를 다시 쓰지 않고 불러 쓰는지. 작업 폴더에서 돈다."""
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import notes  # noqa: E402

cases = [
    (("Hello, World!", date(2026, 10, 28)), "2026-10-28-hello-world.md"),
    ((unicodedata.normalize("NFD", "한글  제목 (초안)"), date(2026, 1, 5)), "2026-01-05-한글-제목-초안.md"),
    (("x" * 80, date(2026, 10, 28)), "2026-10-28-" + "x" * 60 + ".md"),
    (("!!!", date(2026, 10, 28)), "2026-10-28-untitled.md"),
]
bad = [f"{ascii(args)} -> {ascii(notes.export_name(*args))} (want {ascii(want)})" for args, want in cases
       if notes.export_name(*args) != want]
src = Path("notes.py").read_text(encoding="utf-8")
if "slugify" not in src or "re.sub" in src or "unicodedata" in src:
    bad.append("notes.py should reuse textkit.slugify instead of new regex/normalization code")
print("\n".join(bad) or "ok")
sys.exit(1 if bad else 0)
