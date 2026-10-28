# tests

Habitree의 시험입니다. 표준 라이브러리 `unittest`만 쓰고, CI가 Windows·macOS·Linux에서 매번 돌립니다.

- 마지막 갱신: 2026-10-28

```
python -m unittest discover -s tests -t tests
```

| 파일 | 다루는 것 |
|---|---|
| `helpers.py` | 임시 프로젝트와 CLI 실행 도우미 |
| `test_core.py` | 경로, 글롭, Markdown, 같은 뜻 찾기, 스키마, 인코딩 |
| `test_rules.py` | 규칙 DB와 `rules` 명령 |
| `test_init_check.py` | `init`·`export`·`check`를 처음부터 끝까지 |
| `test_conformance.py` | [conformance/](../conformance/)의 사례 |

사용자 환경에서 가장 먼저 문제가 나는 곳이 경로라서, 임시 프로젝트 이름에 일부러 한글과 공백을 넣었습니다. 네트워크나 유료 API를 쓰는 시험은 두지 않습니다.

---

## English

Habitree's tests, using only the standard `unittest`; CI runs them on Windows, macOS and Linux. Paths are where real environments break first, so the temporary project names deliberately contain Korean characters and spaces. No test uses the network or a paid API.
