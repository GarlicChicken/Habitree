# 변경 기록 · Change log

무엇이 언제 바뀌었는지와 다음에 손볼 것을 적는다. 새 기록을 위에 쓴다.
What changed and when, and what to fix next. Newest first.

## 손볼 것 · To fix

작업하다 발견했지만 그 자리에서 고치지 못한 것. / Found while working but not fixed yet.

- 걷어낸 지침의 피드백 줄에서 RULES.md 안내까지 빼면 RULES.md를 미리 읽는 일도 사라지는지 잰다. 바로잡힌 순간에 쓰는 법을 찾는지도 함께 본다.
- 큰 저장소(파일 수백 개 이상)에서 `habitree map find` 안내의 효과를 잰다. 작은 과제에서는 한 단계만 늘었다.
- 훅·플러그인을 켠 상태의 bench(작업 중 알림이 토큰과 정답률에 주는 영향)를 잰다.
- 읽기 도구(Read·Grep·Glob)의 PreToolUse 훅을 빼서 훅 호출을 줄인다. 같은 호출 반복 감지를 PostToolUse로 옮기는 설계가 필요하다(읽기 반복은 막지 않고 알리기만 하면 된다). / Drop the pre-use hook for read-only tools by moving repeat detection to post-use.
- guard 적합성 사례가 없다(입력 이벤트 묶음 → 기대 신호). 다른 엔진이 같은 판정을 하는지 볼 수 있게 `conformance/guard/`를 더한다. / Add guard conformance cases.
- 훅 한 번에 걸리는 시간을 세 OS에서 재서 공개하기 전이다. 지금은 수치를 약속하지 않는다. / Measure and publish hook latency on three OSes.
- 데스크톱 앱이 Stop 말고는 `systemMessage`를 안 보여 준다는 이슈(#103739)를 직접 확인하지 못했다. 확인되면 `guard.relay` 기본값을 다시 본다. / Confirm the desktop systemMessage behavior.

## 기록 · Log

### 2026-10-28

- v0.8: 첫 측정(66번 실행)과 그에 따른 AI 지침 걷어내기, 기본 규칙 0개로 시작, 먼저 찾게 하는 연결 세 개. 결과는 bench/2026-10-28-first-measurement.md.
- v0.2: 작업 중 비효율 경고(`guard`, `hook`), work 꾸러미, 위임 예외, Claude Code 플러그인(`hooks/`, `skills/`, `.claude-plugin/`), `init --hooks`, 명세 [docs/spec/guard.md](docs/spec/guard.md). / v0.2: in-flight warnings, the work pack, delegation, the Claude Code plugin, `init --hooks`, and the guard spec.
- Habitree를 설치했다(`habitree init`). / Installed Habitree (`habitree init`).
