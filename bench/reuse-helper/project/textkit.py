"""글 다루기 도우미. / Text helpers."""
import re
import unicodedata


def slugify(text, max_len=60):
    """파일 이름·주소에 쓸 글: NFC, 소문자, 한글·영문·숫자 말고는 '-', 최대 max_len자."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = re.sub(r"[^0-9a-z가-힣]+", "-", text).strip("-")
    return text[:max_len].rstrip("-") or "untitled"
