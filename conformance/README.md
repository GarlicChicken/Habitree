# conformance

어떤 언어로 만든 엔진이든 같은 결과를 내는지 확인하는 공용 사례입니다. 사례 안의 깨진 링크 같은 문제는 일부러 넣은 것이라, 이 리포를 점검할 때는 이 폴더를 빼 둡니다(`.habitree/config.json`의 `exclude`).

- 마지막 갱신: 2026-10-28

| 사례 | 확인하는 것 |
|---|---|
| `check/clean` | 문제가 없으면 종료 코드 0 |
| `check/broken-links` | 없는 파일과 없는 앵커로 가는 링크 |
| `check/map-missing` | 지도에 없는 폴더, README 없는 폴더(한글·공백 이름 포함) |
| `check/auto-forbid` | 규칙의 자동 검사(`forbid`와 `in` 글롭) |
| `check/instructions` | 숨은 제어 문자, 대상이 없는 `@import` |
| `check/no-log-no-date` | 변경 기록과 갱신일이 없을 때(경고만) |
| `check/models-floor` | 에이전트가 쓰는 모델이 그 작업의 하한보다 낮음(상위 범위의 하한을 물려받음) |

판정 방법은 [docs/spec/conformance.md](../docs/spec/conformance.md)에 있습니다.

---

## English

Shared cases that any engine, in any language, should pass. The broken links and similar problems inside are intentional, so this folder is excluded when the repository checks itself (`exclude` in `.habitree/config.json`). The table above lists what each case covers; how a case passes is described in [docs/spec/conformance.md](../docs/spec/conformance.md).
