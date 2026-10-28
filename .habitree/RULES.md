# 규칙 · Rules

> 이 문서는 [rules.json](rules.json)에서 자동으로 만든다. 직접 고치지 말고 `habitree rules`로 고친다.
> Generated from [rules.json](rules.json). Do not edit by hand; use `habitree rules`.

- 규칙 12개 · 피드백 0건 · 마지막 피드백 -
- 12 rules · 0 feedback entries · last feedback -

## 범위 · Scopes

| 범위 · Scope | 뜻 · Meaning | 규칙 · Rules |
|---|---|---|
| `global` | 모든 작업 · All work | 0 |
| 　`work` | AI가 일하는 방식 · How the AI works | 1 |
| 　　`work/cycle` | 작업 순환: 찾기·쓰기·만들기·기록·고치기·점검 · Work cycle: find, reuse, build, record, fix, check | 7 |
| 　`docs` | 문서와 지도 · Docs and map | 2 |
| 　`code` | 코드 · Code | 0 |
| 　　`code/structure` | 코드 구조(모듈, 파일 크기, 중복) · Code structure (modules, file size, duplication) | 1 |
| 　`security` | 보안과 개인정보 · Security and privacy | 1 |

## 관점 · Aspects

| 관점 · Aspect | 뜻 · Meaning | 규칙 · Rules |
|---|---|---|
| `process` | 절차와 작업 순서 · Process and order of work | 3 |
| `structure` | 구조와 나누기 · Structure and modularity | 2 |
| `quality` | 품질과 검증 · Quality and verification | 2 |
| `docs` | 문서와 기록 · Docs and records | 4 |
| `security` | 보안과 개인정보 · Security and privacy | 1 |
| `style` | 문체와 표기 · Style and wording | 0 |
| `content` | 내용 · Content | 0 |

## 상황 태그 · Contexts

| 태그 · Tag | 뜻 · Meaning | 규칙 · Rules |
|---|---|---|
| `task:implement` | 기능을 만들거나 고칠 때 · When building or changing features | 0 |
| `task:research` | 조사하거나 읽기만 할 때 · When researching or only reading | 0 |
| `task:review` | 검토할 때 · When reviewing | 0 |

## 규칙 · Rules

### `work` · AI가 일하는 방식 · How the AI works

- **[권장 · should · quality] 결과를 확인할 기계 검증(테스트·빌드·린트 명령)을 정해 설정 `verify`에 등록하고, 고칠 때마다 돌린다. / Register machine checks (test, build, lint commands) under `verify` in the config and run them after each change.**
  - 이유 · Why: 통과·실패가 분명해야 AI가 스스로 고치고, 낮은 등급 모델의 실수도 잡힌다. / A clear pass/fail lets the AI fix its own mistakes and catches errors from lower-tier models.
  - 점검 · Check (눈으로 · review): 설정의 verify에 명령이 하나 이상 있는지 본다. / The config lists at least one verify command.
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `work.verify.define-check`

### `work/cycle` · 작업 순환: 찾기·쓰기·만들기·기록·고치기·점검 · Work cycle: find, reuse, build, record, fix, check

- **[권장 · should · process] 같은 파일을 조금씩 여러 번 고치지 않는다. 바꿀 것을 먼저 목록으로 모으고 한 번에 고친 뒤 한 번 확인한다. / Do not edit the same file in many small passes. Collect the changes first, apply them together, then verify once.**
  - 이유 · Why: 고칠 때마다 파일을 다시 읽어 토큰이 들고, 고친 곳끼리 어긋나기 쉽다. / Each pass re-reads the file, costing tokens, and separate edits drift apart.
  - 점검 · Check (눈으로 · review): 한 파일에 작은 수정이 여러 번 이어졌는지 본다. / Were there many small consecutive edits to one file?
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `work.cycle.batch-edits`
- **[필수 · must · process] 사용자 피드백은 고치는 것과 동시에 규칙으로 남긴다. 같은 뜻 규칙이 있으면 `habitree rules hit`, 없으면 `habitree rules add`(가장 넓게 맞는 범위에). / Record user feedback as a rule while fixing it: `habitree rules hit` when a rule with the same meaning exists, otherwise `habitree rules add` (at the widest scope that fits).**
  - 이유 · Why: 사용자가 같은 피드백을 두 번 하지 않게 한다. / So the user never has to give the same feedback twice.
  - 점검 · Check (눈으로 · review): 이번 피드백이 규칙 DB에 기록됐는지 본다. / This feedback is recorded in the rule DB.
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `work.cycle.feedback-to-rule`
- **[필수 · must · process] 새로 만들기 전에 지도(README 색인)와 규칙에서 같은 일을 하는 문서·도구·코드가 있는지 먼저 찾는다. 있으면 쓰고, 낡았으면 그 자리에서 고친다. / Before building anything, search the map (README index) and rules for docs, tools or code that already do the job. Reuse what exists and fix it on the spot if it is stale.**
  - 이유 · Why: 같은 것을 두 번 만들면 토큰과 유지 비용이 두 배가 되고, 원본이 둘이 된다. / Building the same thing twice doubles tokens and upkeep, and creates two sources of truth.
  - 점검 · Check (눈으로 · review): 새 파일·함수를 만들기 전에 찾은 근거(지도 항목, 검색 결과)를 말할 수 있는지 본다. / Before adding a file or function, can you name what you searched (map entry, search result)?
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `work.cycle.find-first`
- **[권장 · should · structure] 같은 작업이 두 번 되풀이되면 세 번째 전에 도구·함수·양식으로 만든다. / When the same task repeats twice, turn it into a tool, function or template before the third time.**
  - 이유 · Why: 되풀이할 때마다 같은 코드를 다시 쓰면 토큰을 매번 다시 쓰고 결과도 조금씩 달라진다. / Rewriting the same code each time spends tokens again and drifts slightly every time.
  - 점검 · Check (눈으로 · review): 이번 작업에서 전에 쓴 것과 비슷한 스크립트를 새로 썼는지 본다. / Did this task rewrite a script similar to an earlier one?
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `work.cycle.repeat-to-module`
- **[필수 · must · quality] 끝내기 전에 `habitree check`와 등록한 검증 명령(테스트·빌드)을 실행하고, 나온 문제를 고친 뒤 끝낸다. / Before finishing, run `habitree check` and the registered verify commands (tests, build), and fix what they report.**
  - 이유 · Why: 사람이 검사기 역할을 하면 '됐어?'를 되풀이하며 시간과 토큰이 샌다. / When the human acts as the test runner, 'is it done?' loops waste time and tokens.
  - 점검 · Check (눈으로 · review): 끝 보고에 점검·검증 결과가 들어 있는지 본다. / The final report includes check and verify results.
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `work.cycle.check-before-done`
- **[필수 · must · docs] 바꾼 것은 이어진 문서(폴더 README, 지도, 변경 기록)에 함께 반영한다. / Reflect every change in the linked docs (folder README, map, change log).**
  - 이유 · Why: 문서가 실제와 어긋나면 다음 작업이 틀린 지도를 읽는다. / When docs drift from reality, the next task reads a wrong map.
  - 점검 · Check (눈으로 · review): `habitree check`가 지도·링크·갱신일 문제를 보고하지 않는지 본다. / `habitree check` reports no map, link or date problems.
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `work.cycle.record`
- **[권장 · should · docs] 발견했지만 지금 고치지 못한 문제와 아이디어는 변경 기록의 '손볼 것'에 적는다. 처리하면 지우고 기록으로 옮긴다. / Write problems or ideas you found but could not fix now under 'To fix' in the change log. Move them to the log once done.**
  - 이유 · Why: 적지 않으면 다음 세션이 같은 문제를 처음부터 다시 찾는다. / Unrecorded findings get rediscovered from scratch in the next session.
  - 점검 · Check (눈으로 · review): 작업 중 미룬 문제가 '손볼 것'에 있는지 본다. / Deferred problems appear under 'To fix'.
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `work.cycle.todo`

### `docs` · 문서와 지도 · Docs and map

- **[필수 · must · docs] 도구가 만든 파일과 구역(habitree:begin/end 사이)은 직접 고치지 않는다. 원본을 고친 뒤 도구로 다시 만든다. / Do not hand-edit generated files or blocks (between habitree:begin/end). Change the source and regenerate.**
  - 이유 · Why: 직접 고친 내용은 다음 생성 때 사라지거나 원본과 어긋난다. / Hand edits are lost on the next generation or drift from the source.
  - 점검 · Check (눈으로 · review): `habitree check`의 generated.edited 알림이 없는지 본다. / `habitree check` shows no generated.edited notice.
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `docs.generated-no-edit`
- **[필수 · must · docs] 같은 내용을 여러 곳에 복사하지 않고 원본 한 곳에 두고 링크한다. / Keep one source for each piece of content and link to it instead of copying.**
  - 이유 · Why: 복사본은 따로 낡아 서로 어긋난다. / Copies go stale separately and contradict each other.
  - 점검 · Check (눈으로 · review): 같은 설명이 두 문서에 따로 있지 않은지 본다. / The same explanation does not live in two documents.
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `docs.single-source`

### `code/structure` · 코드 구조(모듈, 파일 크기, 중복) · Code structure (modules, file size, duplication)

- **[권장 · should · structure] 기능을 더할 때 기존 함수·파일에 덧대지 말고 역할별 모듈·함수로 나눈다. 한 파일이 계속 커지면 나눌 때다. / When adding features, split by responsibility into modules and functions instead of patching onto existing ones. A file that keeps growing is due for a split.**
  - 이유 · Why: 덧대기로 커진 코드는 읽을 때마다 토큰이 많이 들고, 고칠 때 엉뚱한 곳이 깨진다. / Patched-up code costs more tokens to read and breaks in unexpected places when changed.
  - 점검 · Check (눈으로 · review): 이번에 크게 늘어난 파일이 있는지, 비슷한 코드가 복사됐는지 본다. / Did any file grow a lot, or was similar code copied?
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `code.structure.module-over-patch`

### `security` · 보안과 개인정보 · Security and privacy

- **[필수 · must · security] API 키·토큰·비밀번호·개인정보를 코드, 문서, 커밋에 넣지 않는다. 환경 변수나 .env(커밋 제외)로 받는다. / Never put API keys, tokens, passwords or personal data in code, docs or commits. Read them from environment variables or an uncommitted .env.**
  - 이유 · Why: 한 번 공개된 비밀은 지워도 이미 퍼졌을 수 있다. / A secret once published may already have spread, even after deletion.
  - 점검 · Check (자동 · auto): 잘 알려진 키 형식(sk-, ghp_, AKIA, 개인 키 머리말)이 파일에 없는지 자동으로 찾는다. / Automatically scans files for well-known key formats (sk-, ghp_, AKIA, private key headers).
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `security.no-secrets`

