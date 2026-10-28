"""문구 고르기. 글은 문자열 또는 {"ko": ..., "en": ...}이다. / Picking texts in the configured language.

AI가 읽는 생성 파일은 설정한 언어 한 벌만 써서 같은 내용을 두 번 읽지 않게 한다.
"""
import locale
import os

LANGS = ("ko", "en")


def default_lang():
    for var in ("HABITREE_LANG",):
        v = os.environ.get(var, "")
        if v[:2] in LANGS:
            return v[:2]
    try:
        loc = locale.getlocale()[0] or ""
    except ValueError:
        loc = ""
    loc = loc or os.environ.get("LANG", "")
    return "ko" if loc.lower().startswith(("ko", "korean")) else "en"


def tr(text, lang="ko"):
    """글 하나를 고른다. / Pick one language."""
    if isinstance(text, dict):
        return text.get(lang) or text.get("en") or text.get("ko") or next(iter(text.values()), "")
    return "" if text is None else str(text)


def both(text, sep=" / "):
    """두 언어를 함께. / Both languages joined."""
    if isinstance(text, dict) and text.get("ko") and text.get("en") and text["ko"] != text["en"]:
        return f"{text['ko']}{sep}{text['en']}"
    return tr(text)


MSG = {
    "no_db": {"ko": "규칙 DB가 없습니다: {path}. 먼저 `habitree init`을 실행하세요.",
              "en": "No rule DB at {path}. Run `habitree init` first."},
    "unknown_rule": {"ko": "없는 규칙 id: {id}", "en": "Unknown rule id: {id}"},
    "unknown_names": {"ko": "없는 범위·관점·상황: {names}  (목록: habitree rules)",
                      "en": "Unknown scope/aspect/context: {names}  (list: habitree rules)"},
    "db_invalid": {"ko": "규칙 DB에 문제가 있어 저장하지 않았습니다:", "en": "The rule DB has problems; not saved:"},
    "nothing_changed": {"ko": "바뀐 것이 없습니다.", "en": "Nothing changed."},
    "similar_found": {"ko": "비슷한 규칙이 이미 있습니다. 같은 뜻이면 `habitree rules hit <id>`로 기록하고, "
                            "다른 규칙이면 `--force`를 붙여 다시 실행하세요.",
                      "en": "A similar rule already exists. If it means the same, record it with "
                            "`habitree rules hit <id>`; otherwise run again with `--force`."},
}


def t(key, lang="ko", **kw):
    return tr(MSG[key], lang).format(**kw)
