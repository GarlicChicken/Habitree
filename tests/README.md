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
| `test_guard.py` | 감지기, 반복 제한, 위임, Stop 점검, 훅 처음부터 끝까지, 경로 키, 상태 파일 |
| `test_plugin.py` | 플러그인·마켓플레이스·훅·스킬 파일, `init --hooks`, work 꾸러미 |
| `test_models.py` | 모델 대응표, 칸, 승격, 조정, 내보내기(`models`), 검증 명령(`verify`), 점검 연동 |
| `test_map.py` | 코드 색인: 여러 언어의 심볼, 증분 색인, 글자 예산, 한국어 찾기, 중복, git 기록 |
| `test_mcp.py` | MCP 서버를 따로 띄워 줄 단위 JSON-RPC로 주고받기 |
| `test_conformance.py` | [conformance/](../conformance/)의 사례 |

사용자 환경에서 가장 먼저 문제가 나는 곳이 경로라서, 임시 프로젝트 이름에 일부러 한글과 공백을 넣었습니다. 네트워크나 유료 API를 쓰는 시험은 두지 않습니다.

---

## English

Habitree's tests, using only the standard `unittest`; CI runs them on Windows, macOS and Linux. Paths are where real environments break first, so the temporary project names deliberately contain Korean characters and spaces. No test uses the network or a paid API.
