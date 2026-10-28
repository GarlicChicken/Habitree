"""자주 도는 길(훅)을 가볍게 하는 작은 도구. / Small helpers that keep hot paths (hooks) light.

- short(): 같은 호출·같은 블록인지 알아보는 짧은 식별자. 보안용이 아니라서 암호 해시 대신
  zlib 체크섬 두 개(64비트)를 쓴다. hashlib은 불러오는 데만 몇 ms가 든다.
- lazy_re(): 정규식을 처음 쓸 때 만든다. 모듈을 불러올 때 수십 개를 미리 만들면 그것만으로 수십 ms가 든다.
"""
import zlib


def short(text, n=16):
    """글의 짧은 식별자(16진수 n자리, 최대 16). / Short non-cryptographic id."""
    b = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    return f"{zlib.crc32(b):08x}{zlib.adler32(b):08x}"[:n]


class lazy_re:  # noqa: N801  re.compile 자리에 그대로 쓰도록 소문자 이름
    """처음 쓸 때 컴파일되는 정규식. / A regex compiled on first use."""

    __slots__ = ("_args", "_rx")

    def __init__(self, pattern, flags=0):
        self._args = (pattern, flags)
        self._rx = None

    def __getattr__(self, name):
        rx = self._rx
        if rx is None:
            import re
            rx = self._rx = re.compile(*self._args)
        return getattr(rx, name)
