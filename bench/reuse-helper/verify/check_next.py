"""reuse-helper 다음 세션 채점: draft_name도 이미 있는 slugify를 불러 쓰는지. 작업 폴더에서 돈다."""
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import notes  # noqa: E402

cases = [
    ("Hello, World!", "draft-hello-world.md"),
    (unicodedata.normalize("NFD", "한글  제목 (초안)"), "draft-한글-제목-초안.md"),
    ("x" * 80, "draft-" + "x" * 60 + ".md"),
    ("!!!", "draft-untitled.md"),
]
bad = [f"{ascii(title)} -> {ascii(notes.draft_name(title))} (want {ascii(want)})" for title, want in cases
       if notes.draft_name(title) != want]
src = Path("notes.py").read_text(encoding="utf-8")
if "slugify" not in src or "re.sub" in src or "unicodedata" in src:
    bad.append("notes.py should reuse textkit.slugify instead of new regex/normalization code")
print("\n".join(bad) or "ok")
sys.exit(1 if bad else 0)
