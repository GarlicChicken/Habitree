"""글 비슷함: 같은 뜻 규칙을 찾을 때 쓴다(외부 모델 없이). / Text similarity without any model.

영어·숫자는 낱말(camelCase·snake_case는 나눔), 한글은 두 글자 묶음으로 쪼갠다.
한국어는 조사가 붙어 낱말이 갈라지므로('인증을'·'인증') 두 글자 묶음이 더 잘 맞는다.
"""
import re
import unicodedata

_STOP_EN = {"the", "a", "an", "to", "of", "and", "or", "in", "on", "for", "is", "be", "it", "with", "as", "at",
            "by", "that", "this", "when", "then", "do", "not", "no"}
_STOP_KO = {"한다", "는다", "않는", "하지", "있는", "것을", "에서", "으로", "하고", "한다", "된다", "하는", "이다",
            "있다", "없다", "니다", "습니", "합니", "에게", "부터", "까지"}
_HANGUL = re.compile(r"[가-힣]+")
_WORD = re.compile(r"[A-Za-z][a-z]+|[A-Z]+(?![a-z])|[0-9]+")


def tokens(text):
    text = unicodedata.normalize("NFC", text or "")
    out = set()
    for w in _WORD.findall(text):
        w = w.lower()
        if w not in _STOP_EN and len(w) > 1:
            out.add(w)
    for run in _HANGUL.findall(text):
        if len(run) == 1:
            out.add(run)
        out.update(b for b in (run[i:i + 2] for i in range(len(run) - 1)) if b not in _STOP_KO)
    return out


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def overlap(a, b):
    """작은 쪽이 큰 쪽에 얼마나 들어 있나. / Overlap coefficient."""
    if len(a) < 3 or len(b) < 3:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def similarity(x, y):
    """짧은 피드백과 긴 규칙도 같은 뜻이면 높게. / High for same meaning even at different lengths."""
    a, b = tokens(x), tokens(y)
    return max(jaccard(a, b), 0.6 * overlap(a, b))
