# 규칙 · Rules

> 이 문서는 [rules.json](rules.json)에서 자동으로 만든다. 직접 고치지 말고 `habitree rules`로 고친다.
> Generated from [rules.json](rules.json). Do not edit by hand; use `habitree rules`.

- 규칙 53개 · 피드백 0건 · 마지막 피드백 -
- 53 rules · 0 feedback entries · last feedback -

## 범위 · Scopes

| 범위 · Scope | 뜻 · Meaning | 규칙 · Rules |
|---|---|---|
| `global` | 모든 작업 · All work | 0 |
| 　`work` | AI가 일하는 방식 · How the AI works | 1 |
| 　　`work/cycle` | 작업 순환: 찾기·쓰기·만들기·기록·고치기·점검 · Work cycle: find, reuse, build, record, fix, check | 7 |
| 　　`work/loop` | 제자리 돌기: 같은 호출·같은 오류·고리·잔수정 · Going in circles: same call, same error, cycles, small edits | 4 |
| 　　`work/request` | 요청 주고받기: 쪼개 보내기, 거듭 정정 · Requests: split messages, repeated corrections | 2 |
| 　　`work/context` | 대화 기록 아끼기: 큰 결과, 섞인 주제 · Context thrift: large results, mixed topics | 2 |
| 　　`work/verify` | 검증: 기계로 확인하고 끝내기 · Verification: machine checks before finishing | 1 |
| 　　`work/delegate` | 위임: 맡긴 작업의 범위와 경계, 끝 보고 · Delegation: scope, boundaries and the end report | 3 |
| 　`docs` | 문서와 지도 · Docs and map | 2 |
| 　`code` | 코드 · Code | 0 |
| 　　`code/structure` | 코드 구조(모듈, 파일 크기, 중복) · Code structure (modules, file size, duplication) | 6 |
| 　`security` | 보안과 개인정보 · Security and privacy | 1 |
| 　`task` | 작업 유형(모델 배분) · Task types (model allocation) | 6 |
| 　　`task/explore` | 탐색·검색 · Exploration and search | 1 |
| 　　`task/summarize` | 요약 · Summaries | 1 |
| 　　`task/commit-message` | 커밋 메시지·제목·이름 · Commit messages, titles, names | 1 |
| 　　`task/bulk` | 대량 분류·추출·변환 · Bulk classification, extraction, conversion | 1 |
| 　　`task/plan` | 계획·설계 · Planning and design | 1 |
| 　　`task/code` | 코드 작성 · Writing code | 1 |
| 　　　`task/code/clear-spec` | 명세가 분명한 코드 · Code with a clear spec | 1 |
| 　　　`task/code/ambiguous` | 모호하거나 여러 파일에 걸친 코드 · Ambiguous or multi-file code | 1 |
| 　　`task/refactor` | 리팩터링 · Refactoring | 1 |
| 　　　`task/refactor/mechanical` | 기계적 리팩터링 · Mechanical refactoring | 1 |
| 　　　`task/refactor/structural` | 구조 리팩터링 · Structural refactoring | 1 |
| 　　`task/debug` | 디버깅 · Debugging | 1 |
| 　　`task/test` | 테스트 작성 · Writing tests | 1 |
| 　　`task/review` | 리뷰·판정 · Review and judging | 1 |
| 　　　`task/review/security` | 보안 리뷰 · Security review | 1 |
| 　　`task/docs` | 문서 · Documentation | 1 |
| 　　`task/risky` | 위험 작업(인증·돈·개인정보·비밀값·마이그레이션·삭제·배포) · Risky work (auth, money, personal data, secrets, migrations, deletion, deploys) | 1 |
| 　　`task/long-autonomous` | 몇 시간 도는 자율 작업 · Long-running autonomous work | 1 |

## 관점 · Aspects

| 관점 · Aspect | 뜻 · Meaning | 규칙 · Rules |
|---|---|---|
| `process` | 절차와 작업 순서 · Process and order of work | 13 |
| `structure` | 구조와 나누기 · Structure and modularity | 7 |
| `quality` | 품질과 검증 · Quality and verification | 3 |
| `docs` | 문서와 기록 · Docs and records | 4 |
| `security` | 보안과 개인정보 · Security and privacy | 2 |
| `style` | 문체와 표기 · Style and wording | 0 |
| `content` | 내용 · Content | 0 |
| `model` | 모델 배분(등급·강도) · Model allocation (tier and effort) | 24 |

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

### `work/loop` · 제자리 돌기: 같은 호출·같은 오류·고리·잔수정 · Going in circles: same call, same error, cycles, small edits

- **[권장 · should · process] 몇 단계가 같은 순서로 맴돌면 고치기를 멈추고, 지금까지 시도한 것과 원인 가설 하나를 먼저 적는다. / When a few steps keep circling in the same order, stop editing and first write down what was tried and one hypothesis.**
  - 이유 · Why: 고치고 확인하기가 같은 결과로 맴돌면 진전 없이 대화 기록만 길어진다. / Circling through fix-and-check with the same result only makes the history longer.
  - 점검 · Check (자동 · auto): PreToolUse 훅이 최근 호출에서 길이 1~5짜리 묶음이 같은 순서로 되풀이된 바퀴 수를 센다. / The PreToolUse hook counts laps of a 1 to 5 call block repeating in order.
  - 감지 · Detect: `cycle` · PreToolUse · threshold 5 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.loop.cycle`
- **[권장 · should · process] 도구를 똑같은 입력으로 잇달아 부르게 되면 그 호출을 멈추고, 마지막 결과를 다시 읽은 뒤 다른 방법을 고른다. / When calling a tool again with the very same input, stop, reread the last result, and pick another approach.**
  - 이유 · Why: 입력이 같으면 결과도 같아서 부를 때마다 시간과 사용량만 든다. / The same input gives the same result, so each call only costs time and usage.
  - 점검 · Check (자동 · auto): PreToolUse 훅이 도구 이름과 키를 정렬한 입력의 해시가 잇달아 같은 횟수를 센다. / The PreToolUse hook counts consecutive calls whose tool name and key-sorted input hash match.
  - 감지 · Detect: `same_call_streak` · PreToolUse · threshold 3 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.loop.same-call`
- **[권장 · should · process] 한 호출이 같은 오류로 거듭 실패하면 같은 시도를 다시 하지 않고, 오류 문장에서 원인부터 찾는다. / When one call keeps failing with the same error, do not retry it as is; find the cause in the error text first.**
  - 이유 · Why: 같은 방법을 또 쓰면 같은 오류가 날 가능성이 크고, 실패가 쌓일수록 회복이 어려워진다. / Retrying the same way likely fails the same way, and stacked failures make recovery harder.
  - 점검 · Check (자동 · auto): PostToolUse·PostToolUseFailure 훅이 같은 호출의 같은 오류를 세고, 다음 같은 호출 전에 멈춘다. / Post-tool hooks count the same error for the same call and stop before the next identical call.
  - 감지 · Detect: `same_error_streak` · PostToolUse|PreToolUse · threshold 3 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.loop.same-error`
- **[권장 · should · process] 짧은 고침이 한 파일에 잇달아 쌓이면 알린다. 남은 손질을 목록으로 묶어 한 번에 처리하길 제안한다. / Note when short fixes pile up on one file, and suggest bundling the remaining touch-ups into one pass.**
  - 이유 · Why: 왕복할 때마다 대화 전체가 다시 읽힌다. 다만 한 파일 여러 곳을 차례로 고치는 것은 정상 작업이기도 해서 정보로만 알린다. / Every round trip rereads the whole conversation. Fixing several spots in turn is also normal work, so this is only a note.
  - 점검 · Check (자동 · auto): PostToolUse 훅이 바뀐 줄 3줄 이하 수정을 파일별로 15분 창에서 센다. 검증 명령을 돌리면 다시 센다. / The PostToolUse hook counts edits of 3 lines or fewer per file in a 15 minute window; a verify run resets it.
  - 감지 · Detect: `small_edits_same_file` · PostToolUse · threshold 6 · info
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.loop.small-edits`

### `work/request` · 요청 주고받기: 쪼개 보내기, 거듭 정정 · Requests: split messages, repeated corrections

- **[권장 · should · process] 같은 점을 두 번 바로잡아도 안 되면 세 번째 정정 대신, 알게 된 것을 담아 새로 시작한다. / If the same point was corrected twice without success, start fresh with what was learned instead of a third correction.**
  - 이유 · Why: 실패한 시도가 대화 기록에 남아 계속 다시 읽힌다. Claude Code 공식 모범 사례도 두 번 실패한 정정 뒤에는 /clear를 권한다. / Failed attempts stay in the history and keep being reread. Claude Code's best practices also suggest /clear after two failed corrections.
  - 점검 · Check (자동 · auto): UserPromptSubmit 훅이 정정 표현(아니, 그게 아니라, 말했잖아 / no, that's not, I said 등)이 같은 주제로 이어지는지 본다. / The UserPromptSubmit hook looks for correction phrases on the same topic in a row.
  - 감지 · Detect: `repeat_correction` · UserPromptSubmit · threshold 2 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.request.repeat-correction`
- **[권장 · should · process] 원하는 것, 조건, 끝나는 기준은 한 메시지에 모아 보낸다. 짧은 요청이 잇달아 오면 모아 달라고 제안한다. / Send what you want, the conditions and the finish line in one message. When short requests keep coming, suggest bundling them.**
  - 이유 · Why: AI는 앞 문장만 보고 짐작해 시작했다가 되돌리기 쉽다. 여러 턴에 나눠 준 지시는 한 번에 준 것보다 결과가 크게 나빴다는 연구가 있다(Laban 외 2025). / The AI tends to start from a guess on the first line and backtrack. A study found much worse results when instructions were split over turns (Laban et al. 2025).
  - 점검 · Check (자동 · auto): UserPromptSubmit 훅이 5분 안에 들어온 40자 이하 요청을 센다(대답·승인 한 마디와 / 명령은 뺀다). / The UserPromptSubmit hook counts prompts of 40 characters or fewer within 5 minutes (acknowledgements and / commands excluded).
  - 감지 · Detect: `request_split` · UserPromptSubmit · threshold 3 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.request.split`

### `work/context` · 대화 기록 아끼기: 큰 결과, 섞인 주제 · Context thrift: large results, mixed topics

- **[권장 · should · process] 도구 결과가 아주 길면 통째로 읽지 말고, 검색으로 위치를 찾은 뒤 필요한 범위만 읽는다. / When a tool result is very long, do not read it whole; search for the spot and read only the range you need.**
  - 이유 · Why: 긴 결과는 대화 기록에 남아 다음 요청마다 다시 읽힌다. / Long results stay in the history and are read again on every later request.
  - 점검 · Check (자동 · auto): PostToolUse 훅이 도구 결과의 글자 수를 잰다. / The PostToolUse hook measures the characters in each tool result.
  - 감지 · Detect: `big_output` · PostToolUse · threshold 20000 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.context.big-output`
- **[권장 · should · process] 관련 없는 새 작업은 새 대화에서 시작한다. / Start unrelated new work in a new conversation.**
  - 이유 · Why: 앞 작업의 기록이 다음 요청마다 함께 읽혀 느려지고 사용량이 는다. 단어 겹침으로 대략 판단하므로 틀릴 수 있어 정보로만 알린다. / Earlier work is reread with every later request, which is slower and uses more. The word-overlap guess can be wrong, so it is only a note.
  - 점검 · Check (자동 · auto): UserPromptSubmit 훅이 긴 세션(30턴 이상 또는 기록 1MB 이상)에서 새 요청 낱말이 앞 요청들과 거의 안 겹치는지 본다. / In long sessions (30+ turns or a 1 MB transcript) the UserPromptSubmit hook checks whether the new prompt shares almost no words with earlier ones.
  - 감지 · Detect: `topic_mix` · UserPromptSubmit · threshold 30 · info
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.context.topic-mix`

### `work/verify` · 검증: 기계로 확인하고 끝내기 · Verification: machine checks before finishing

- **[권장 · should · quality] 파일을 바꾼 세션이 등록한 검증 명령을 한 번도 돌리지 않은 채 끝나면 알린다. / Note when a session that changed files ends without running any registered verify command.**
  - 이유 · Why: 통과·실패로 답하는 검사가 돌지 않으면 사람이 눈으로 확인해야 한다. / Without a pass or fail check, a person has to confirm by eye.
  - 점검 · Check (자동 · auto): Stop 훅이 이번 세션의 수정 횟수와 설정 verify 명령의 실행 횟수를 본다. / The Stop hook compares edits in this session with runs of the configured verify commands.
  - 감지 · Detect: `no_verify` · Stop · threshold 1 · info
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.verify.run-before-done`

### `work/delegate` · 위임: 맡긴 작업의 범위와 경계, 끝 보고 · Delegation: scope, boundaries and the end report

- **[권장 · should · process] '알아서 해 줘'처럼 맡기면 범위를 한 줄로 되말하고, 그 작업에 한해 되묻지 않고 추천안대로 진행한다. / When told 'just do it', restate the scope in one line and, for that task only, proceed with the recommended option without asking.**
  - 이유 · Why: 맡긴 뜻을 따르되, 범위를 되말해야 잘못 알아들었을 때 사용자가 바로 바로잡을 수 있다. / Following the delegation while restating the scope lets the user correct a misunderstanding right away.
  - 점검 · Check (자동 · auto): UserPromptSubmit 훅이 위임 표현을 찾아 세션 상태에 범위와 경계를 적고 AI 맥락에 알린다(인용·질문·남의 말은 뺀다). / The UserPromptSubmit hook finds delegation phrases, records scope and boundaries in the session state, and tells the AI (quotes, questions and reported speech excluded).
  - 감지 · Detect: `delegation` · UserPromptSubmit · threshold - · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.delegate.declare`
- **[필수 · must · process] 맡긴 작업을 마치면 대신 정한 것, 미뤄 둔 알림, 실행한 검사 결과를 모아 보고한다. / When a delegated task is done, report the decisions made, the notes held back, and the checks run.**
  - 이유 · Why: 묻지 않고 정한 것은 사용자가 끝에서라도 보고 바로잡을 수 있어야 한다. 바로잡은 것은 규칙으로 쌓인다. / Decisions made without asking must be visible at the end so the user can correct them. Corrections become rules.
  - 점검 · Check (자동 · auto): 위임 중 Stop 훅이 한 번 막고 끝 보고를 받은 뒤 위임을 끝낸다. / While delegated, the Stop hook blocks once to get the end report, then ends the delegation.
  - 감지 · Detect: `delegate_report` · Stop · threshold - · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.delegate.end-report`
- **[필수 · must · security] 맡긴 작업 중에도 지우기, 배포·올리기, 외부로 보내기, 결제, 비밀 정보, 작업 폴더 밖 수정은 사용자 확인을 받는다. / Even in a delegated task, deleting, deploying or pushing, sending outside, payments, secrets and changes outside the project need the user's confirmation.**
  - 이유 · Why: 되돌릴 수 없거나 밖으로 나가는 일은 '알아서'로 풀리지 않는다. 사용자가 함께 정한 경계도 위임 중에 그대로 지킨다. / Irreversible or outward actions are not unlocked by 'just do it'. Boundaries the user set are kept during delegation.
  - 점검 · Check (자동 · auto): 위임 중 PreToolUse 훅이 명령·도구 이름·파일 경로로 위험한 일을 찾아 permissionDecision ask로 확인을 받는다. / While delegated, the PreToolUse hook spots risky actions by command, tool name and path, and asks via permissionDecision ask.
  - 감지 · Detect: `risky_action` · PreToolUse · threshold - · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `work.delegate.risky-ask`

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

- **[권장 · should · structure] 코드가 파일 하나나 함수 하나에 몰려 있으면 먼저 덜어 낼 것을 덜고, 그다음 이미 있는 경계(클래스, 같은 접두어 묶음)를 따라 한 걸음씩 옮긴다. / When code piles up in one file or function, first remove what can go, then move it piece by piece along seams that already exist (classes, groups sharing a prefix).**
  - 이유 · Why: 몰린 코드는 고칠 때마다 통째로 읽혀 토큰이 들고, 한 곳을 고치다 엉뚱한 곳이 깨지기 쉽다. 새 층을 더하는 정리는 읽을 곳을 오히려 늘린다. / Piled-up code is read whole on every change and breaks in odd places. A cleanup that adds a new layer only adds more to read.
  - 점검 · Check (자동 · auto): `habitree refactor`가 파일·함수 줄 수를 프로젝트 중앙값과 견주고, git 변경 횟수로 순서를 정한다. / `habitree refactor` compares file and function lengths with the project median and orders them by git change counts.
  - 감지 · Detect: `refactor_concentration` · refactor · threshold 4 · warn
  - 피드백 · feedback 0 · `pack:base@0.6.0` · `code.structure.concentration`
- **[권장 · should · structure] 새로 쓰는 줄 묶음이 다른 파일에 이미 있으면 붙여 넣지 말고, 있는 것을 불러 쓰거나 공통 함수로 뺀다. / If newly written lines already exist in another file, do not paste them; call the existing code or extract a shared function.**
  - 이유 · Why: 복사본은 따로 낡아서 고칠 곳이 늘어난다. / Copies go stale separately, so there are more places to fix.
  - 점검 · Check (자동 · auto): PostToolUse 훅이 새로 들어간 줄을 공백을 정리해 6줄씩 해시하고 다른 파일과 비교한다(탐색 파일 수·크기 상한). / The PostToolUse hook hashes new lines in 6 line windows after trimming whitespace and compares other files (with file count and size limits).
  - 감지 · Detect: `copy_block` · PostToolUse · threshold 6 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `code.structure.copy-block`
- **[권장 · should · structure] 같은 코드가 이미 여러 곳에 있으면 한 곳을 남기고 나머지가 그곳을 부르게 바꾼 뒤 복사본을 지운다. 새 층은 남길 곳이 없을 때만 만든다. / When the same code already sits in several places, keep one, make the rest call it, and delete the copies. Add a new layer only when no place can serve as the keeper.**
  - 이유 · Why: 복사본은 따로 낡아서 고칠 곳이 늘고, AI는 같은 코드를 여러 번 읽는다. / Copies drift apart, so there are more places to fix, and the AI reads the same code several times.
  - 점검 · Check (자동 · auto): `habitree refactor`가 `map dupes`의 같은 몸통과 같은 글(기준 줄 수 이상)을 묶어 본다. / `habitree refactor` groups the same bodies and repeated text from `map dupes` (at least the threshold lines).
  - 감지 · Detect: `refactor_duplication` · refactor · threshold 6 · warn
  - 피드백 · feedback 0 · `pack:base@0.6.0` · `code.structure.duplication`
- **[권장 · should · structure] 한 세션 안에서 기존 파일이 거의 더하기만으로 크게 불어나면, 새 기능은 따로 파일이나 함수로 떼어 낸다. / When an existing file balloons within one session through additions alone, move the new feature into its own file or function.**
  - 이유 · Why: 덧붙이기로 커진 파일은 읽을 때마다 사용량이 많이 들고, 고칠 때 엉뚱한 곳이 깨지기 쉽다. / A file grown by appending costs more to read every time and breaks in odd places when changed.
  - 점검 · Check (자동 · auto): PostToolUse 훅이 세션 처음 줄 수와 지금 줄 수, 더한 줄과 지운 줄을 파일별로 비교한다. / The PostToolUse hook compares the start and current line count and the added and removed lines per file.
  - 감지 · Detect: `file_growth` · PostToolUse · threshold 30 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `code.structure.file-growth`
- **[권장 · should · structure] 한 기능이 여러 파일에 흩어졌거나 쓰이지 않는 코드, 한 곳에서만 쓰는 짧은 층이 있으면 나누기보다 합치기와 지우기를 먼저 검토한다. / When one feature is scattered over many files, or there is unused code or a short layer used in one place, consider merging and deleting before splitting further.**
  - 이유 · Why: 조각이 많을수록 한 기능을 보려고 여러 파일을 열어야 하고, 쓰이지 않는 코드도 읽을 때마다 토큰이 든다. 정적 분석이라 확실하지 않아 정보로 알린다. / The more pieces, the more files to open for one feature, and unused code still costs tokens to read. Static analysis cannot be sure, so these are notes.
  - 점검 · Check (자동 · auto): `habitree refactor`가 참조 그래프(들어오는 참조 수, 서로 참조)와 git의 함께 바뀐 기록, 같은 이름 정의를 본다. / `habitree refactor` reads the reference graph (incoming references, mutual references), git co-changes and same-name definitions.
  - 감지 · Detect: `refactor_fragmentation` · refactor · threshold 5 · info
  - 피드백 · feedback 0 · `pack:base@0.6.0` · `code.structure.fragmentation`
- **[권장 · should · structure] 기능을 더할 때 기존 함수·파일에 덧대지 말고 역할별 모듈·함수로 나눈다. 한 파일이 계속 커지면 나눌 때다. / When adding features, split by responsibility into modules and functions instead of patching onto existing ones. A file that keeps growing is due for a split.**
  - 이유 · Why: 덧대기로 커진 코드는 읽을 때마다 토큰이 많이 들고, 고칠 때 엉뚱한 곳이 깨진다. / Patched-up code costs more tokens to read and breaks in unexpected places when changed.
  - 점검 · Check (눈으로 · review): 이번에 크게 늘어난 파일이 있는지, 비슷한 코드가 복사됐는지 본다. / Did any file grow a lot, or was similar code copied?
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `code.structure.module-over-patch`

### `security` · 보안과 개인정보 · Security and privacy

- **[필수 · must · security] API 키·토큰·비밀번호·개인정보를 코드, 문서, 커밋에 넣지 않는다. 환경 변수나 .env(커밋 제외)로 받는다. / Never put API keys, tokens, passwords or personal data in code, docs or commits. Read them from environment variables or an uncommitted .env.**
  - 이유 · Why: 한 번 공개된 비밀은 지워도 이미 퍼졌을 수 있다. / A secret once published may already have spread, even after deletion.
  - 점검 · Check (자동 · auto): 잘 알려진 키 형식(sk-, ghp_, AKIA, 개인 키 머리말)이 파일에 없는지 자동으로 찾는다. / Automatically scans files for well-known key formats (sk-, ghp_, AKIA, private key headers).
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `security.no-secrets`

### `task` · 작업 유형(모델 배분) · Task types (model allocation)

- **[권장 · should · model] 작업 유형을 정하지 않은 일은 `mid:medium` 칸(등급:강도)에서 시작한다. 자동 승격은 `high:high`까지. / Work without a task type starts at the `mid:medium` cell (tier:effort). Automatic escalation stops at `high:high`.**
  - 이유 · Why: [확인] Claude Code 비용 문서: Sonnet이 대부분의 코딩을 잘 하고 Opus보다 싸다. [추정] 유형을 모를 때의 기본값으로 중 등급을 둔다. / [verified] Claude Code costs doc: Sonnet handles most coding tasks well and costs less than Opus. [estimate] mid tier as the default when the type is unknown.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.cell`
- **[권장 · should · model] 모델 비용은 토큰 단가가 아니라 끝낸 작업 하나당 비용으로 비교한다. 실패한 시도의 비용도 넣는다. / Compare model cost per completed task, not per token, including the cost of failed attempts.**
  - 이유 · Why: [확인] Anthropic 비용·지능 최적화 문서: 끝낸 작업에 돈을 내므로 토큰당이 아니라 끝낸 작업당 비용으로 비교한다. / [verified] Anthropic cost and intelligence guide: compare cost per completed task, not per token, because you pay for completed tasks.
  - 점검 · Check (눈으로 · review): 비교표에 실패한 시도의 비용이 들어 있는지 본다. / Comparisons include failed attempts.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.cost-per-task`
- **[권장 · should · model] 싼 서브에이전트에게 나눠 맡기는 것은 서로 독립이고 양이 많고 결과를 검사할 수 있는 일일 때만 한다. 한 줄로 이어지는 일은 쪼개지 않고 주 에이전트가 강도를 낮춰 한다. / Split work across cheap subagents only when the pieces are independent, numerous and checkable. Do not split one dependent chain; let the main agent do it at lower effort.**
  - 이유 · Why: [주장] Anthropic 비용·지능 최적화 문서의 내부 측정: 위임은 꼬리가 긴 반복 작업과 컨텍스트 하나를 넘는 일에서만 돈을 아꼈고, 한 줄로 이어지는 일은 지휘 모델 혼자 낮은 강도로 한 쪽이 측정한 모든 경우에 앞섰다. / [claim] Anthropic's internal measurements in the cost and intelligence guide: delegation saved money only for routine work with a long cost tail and for work larger than one context; for one dependent chain the orchestrator alone at lower effort came out ahead in every case measured.
  - 점검 · Check (눈으로 · review): 나눠 맡긴 조각들이 서로 기다리지 않는지 본다. / Delegated pieces do not wait on each other.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.delegate-independent`
- **[권장 · should · model] 칸을 올릴 때는 모델(등급)보다 강도를 먼저 본다. 둘 다 바꾸기 전에 지시문·맥락·도구·검증 명령이 빠지지 않았는지 먼저 확인한다. / When moving up a cell, look at effort before the model tier. Before changing either, check that instructions, context, tools and verify commands are not missing.**
  - 이유 · Why: [확인] Anthropic 비용·지능 최적화 문서: 두 번째 모델을 더하기 전에 지금 모델의 강도부터 훑어 본다. Anthropic의 Claude Code 모델·강도 글: 고칠 곳은 대개 위쪽(맥락, CLAUDE.md, 작업 범위)에 있다. / [verified] Anthropic cost and intelligence guide: sweep effort on the current model before adding a second one. Anthropic's Claude Code model and effort article: the fix is often upstream (context, CLAUDE.md, task scope).
  - 점검 · Check (눈으로 · review): 승격 전에 맥락·도구·검증 명령을 점검했는지 본다. / Context, tools and verify commands were checked before escalating.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.effort-first`
- **[권장 · should · model] 승격한 칸은 새 서브에이전트(새 대화)에서 돌리고 실패 요약만 넘긴다. 대화 중간에 모델을 바꾸지 않는다. / Run an escalated cell in a fresh subagent (new conversation) and pass only a failure summary. Do not switch models mid-conversation.**
  - 이유 · Why: [확인] Anthropic 강도 문서: 최상위 강도를 요청 사이에 바꾸면 캐시가 다시 시작된다. / [verified] Anthropic effort docs: changing top-level effort between requests restarts the prompt cache.
  - 점검 · Check (눈으로 · review): 승격이 같은 대화 안에서 모델만 바꿔 일어나지 않았는지 본다. / Escalation did not just swap the model inside the same conversation.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.escalate-fresh`
- **[권장 · should · model] 자동 승격은 기계 검증(설정 verify의 명령, 종료 코드 0이 합격)이 있는 작업만 한다. 건너뜀은 강도+1, 자신 있게 틀림·맴돌기는 등급+1, 형식 오류는 같은 칸 1번 더, 장애(429·5xx·과부하)는 등급을 올리지 않고 같은 등급의 다른 모델로. 작업당 자동 승격 2단계·시도 4번까지 하고 그다음은 사람에게 넘긴다(`habitree models escalate`). / Escalate automatically only for tasks with machine verification (verify commands in the config, exit 0 passes). Skipped steps: effort +1. Confidently wrong or looping: tier +1. Format errors: one more try in the same cell. Outages (429, 5xx, overload): keep the tier and switch to another model of the same tier. At most 2 automatic steps and 4 attempts per task, then hand over to a person (`habitree models escalate`).**
  - 이유 · Why: [확인] Anthropic 비용·지능 최적화 문서: 낮은 강도로 돌리고 실패만 높은 강도로 다시 돌리면 싸지만, 나쁜 결과를 통과시키는 판정이면 실패가 그대로 지나간다. [주장] RouterBench(arXiv 2403.12031): 계단식 라우터는 판정 오류율이 0.2를 넘으면 급격히 나빠진다. [확인] LiteLLM은 장애 대체(fallbacks)를 품질과 다른 설정으로 둔다. [추정] 2단계·4번 상한. / [verified] Anthropic cost and intelligence guide: running low and re-running only failures higher saves money, but a checker that passes bad work lets failures through. [claim] RouterBench (arXiv 2403.12031): cascades degrade sharply once judge error exceeds 0.2. [verified] LiteLLM keeps outage fallbacks separate from quality. [estimate] the 2-step and 4-attempt caps.
  - 점검 · Check (눈으로 · review): 승격 기록(models record)에 장애와 품질 실패가 섞이지 않았는지 본다. / Escalation records (models record) keep outages apart from quality failures.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.escalate-on-verify`

### `task/explore` · 탐색·검색 · Exploration and search

- **[권장 · should · model] 탐색·검색(파일·함수 위치 찾기, 문서 조회, 코드를 읽고 보고하기)은 `low:medium` 칸에서 시작한다. 자동 승격은 `mid:medium`까지. / Exploration and search (finding files and functions, looking up docs, reading code and reporting) starts at `low:medium`. Automatic escalation stops at `mid:medium`.**
  - 이유 · Why: [확인] Claude Code 비용 문서: 단순한 서브에이전트 작업은 model: haiku. [확인] Anthropic 강도 문서: Haiku 5.5는 긴 에이전트 프롬프트에서 low일 때 검색을 건너뛰거나 일찍 멈추기 쉽다. 그래서 보통 강도. / [verified] Claude Code costs doc: use model: haiku for simple subagent tasks. [verified] Anthropic effort docs: in long agent prompts Haiku 5.5 is more likely to skip a search or stop early at low, hence medium.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.explore.cell`

### `task/summarize` · 요약 · Summaries

- **[권장 · should · model] 로그·긴 문서·지난 대화 요약은 `low:low` 칸에서 시작하고, 입력이 크면 나눠서 넘긴다. 자동 승격은 `mid:medium`까지. / Summaries of logs, long documents and past sessions start at `low:low`; split large inputs. Automatic escalation stops at `mid:medium`.**
  - 이유 · Why: [확인] Aider는 대화 요약에 약한 모델을 쓰고, Claude Code는 지난 대화 요약 같은 배경 일에 haiku 별칭 모델을 쓴다. [확인] Anthropic 가격표: Haiku 5.5는 프롬프트가 10만 토큰을 넘으면 입력 단가가 0.10달러에서 0.50달러가 된다. / [verified] Aider summarizes chats with its weak model, and Claude Code runs background summaries on the haiku alias model. [verified] Anthropic pricing: Haiku 5.5 input goes from $0.10 to $0.50 per million tokens for prompts over 100,000 tokens.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.summarize.cell`

### `task/commit-message` · 커밋 메시지·제목·이름 · Commit messages, titles, names

- **[권장 · should · model] 커밋 메시지·세션 제목·PR 제목·이름 짓기는 `low:low` 칸에서 시작한다. 자동 승격은 `mid:low`까지. / Commit messages, session titles, PR titles and naming start at `low:low`. Automatic escalation stops at `mid:low`.**
  - 이유 · Why: [확인] Aider는 커밋 메시지를 약한 모델로 먼저 만들고 안 되면 주 모델로 만든다. opencode는 제목 생성 같은 가벼운 일에 small_model을 쓴다(설정 문서). / [verified] Aider writes commit messages with the weak model first and falls back to the main model. opencode uses small_model for light work such as title generation (config docs).
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.commit-message.cell`

### `task/bulk` · 대량 분류·추출·변환 · Bulk classification, extraction, conversion

- **[권장 · should · model] 대량 분류·추출·형식 변환은 `low:low` 칸에서 시작하고 결과를 스키마로 검사한다. 자동 승격은 `mid:medium`까지. / Bulk classification, extraction and format conversion start at `low:low`, with results checked against a schema. Automatic escalation stops at `mid:medium`.**
  - 이유 · Why: [확인] Anthropic 모델 개요: Haiku 5.5는 분류·추출·라우팅 같은 대량·지연 민감 작업용이고 Batch API는 50% 할인. OpenAI 모델 문서: Luna는 대량 작업용. / [verified] Anthropic models overview: Haiku 5.5 is for high-volume, latency-sensitive classification, extraction and routing, and the Batch API is 50% off. OpenAI models page: Luna is for high-volume tasks.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.bulk.cell`

### `task/plan` · 계획·설계 · Planning and design

- **[권장 · should · model] 계획·설계(구조 설계, 작업 나누기, 기술 선택)는 `high:high` 칸에서 읽기만 하며 한다. 자동 승격은 `top:high`까지. / Planning and design (architecture, breaking down work, choosing technology) runs read-only at `high:high`. Automatic escalation stops at `top:high`.**
  - 이유 · Why: [확인] Claude Code의 opusplan은 계획 모드에 opus, 실행에 sonnet을 쓴다. Anthropic의 모델·강도 글: 설계 결정은 큰 모델. [추정] 방향이 틀리면 뒤 작업이 모두 헛수고가 된다. / [verified] Claude Code's opusplan uses opus in plan mode and sonnet for execution. Anthropic's model and effort article: architecture decisions go to the larger model. [estimate] a wrong direction wastes all later work.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.plan.cell`

### `task/code` · 코드 작성 · Writing code

- **[권장 · should · model] 새 코드 작성과 기능 추가는 `mid:medium` 칸에서 시작하고, 명세가 분명한지 모호한지 알면 하위 유형(clear-spec, ambiguous)으로 고른다. 자동 승격은 `high:high`까지. / Writing new code and adding features starts at `mid:medium`; pick a subtype (clear-spec, ambiguous) once you know how clear the spec is. Automatic escalation stops at `high:high`.**
  - 이유 · Why: [확인] Claude Code 비용 문서: Sonnet이 대부분의 코딩을 잘 하고 Opus보다 싸다. Anthropic 강도 문서: Sonnet 5.5로 에이전트 코딩을 할 때 명세가 분명하면 medium부터, 어렵거나 길면 high. / [verified] Claude Code costs doc: Sonnet handles most coding well and costs less than Opus. Anthropic effort docs: for agentic coding on Sonnet 5.5, start at medium for well-specified tasks and move to high for harder or longer ones.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.code.cell`

### `task/code/clear-spec` · 명세가 분명한 코드 · Code with a clear spec

- **[권장 · should · model] 정해진 함수·화면·API 하나처럼 명세가 분명한 구현은 `mid:medium` 칸에서 시작한다. 자동 승격은 `high:high`까지. / Well-specified implementation, such as one defined function, screen or API, starts at `mid:medium`. Automatic escalation stops at `high:high`.**
  - 이유 · Why: [확인] Anthropic의 모델·강도 글: 정확히 설명할 수 있는 변경은 작은 모델. Anthropic 강도 문서: 명세가 분명한 에이전트 코딩은 medium부터. / [verified] Anthropic's model and effort article: edits you can describe precisely go to a smaller model. Anthropic effort docs: start well-specified agentic coding at medium.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.code.clear-spec.cell`

### `task/code/ambiguous` · 모호하거나 여러 파일에 걸친 코드 · Ambiguous or multi-file code

- **[권장 · should · model] 모호하거나 여러 모듈에 걸친 변경(새 기능, 여러 파일)은 `high:medium` 칸에서 시작한다. 자동 승격은 `top:high`까지. / Ambiguous or multi-module changes (new features, many files) start at `high:medium`. Automatic escalation stops at `top:high`.**
  - 이유 · Why: [확인] Anthropic 모델 개요: 잘 모르면 Opus 5.5로 시작한다(기본 강도 medium). 모델·강도 글: 큰 모델이 모호함을 더 잘 다룬다. / [verified] Anthropic models overview: if unsure, start with Opus 5.5 (default effort medium). Model and effort article: larger models handle ambiguity better.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.code.ambiguous.cell`

### `task/refactor` · 리팩터링 · Refactoring

- **[권장 · should · model] 종류를 정하지 않은 리팩터링은 `mid:medium` 칸에서 시작한다. 자동 승격은 `high:high`까지. / Refactoring of unspecified kind starts at `mid:medium`. Automatic escalation stops at `high:high`.**
  - 이유 · Why: [추정] 기계적인지 구조적인지 정하지 않았을 때의 중간값. / [estimate] a middle value when it is not yet clear whether the change is mechanical or structural.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.refactor.cell`

### `task/refactor/mechanical` · 기계적 리팩터링 · Mechanical refactoring

- **[권장 · should · model] 이름 바꾸기·함수 옮기기·형식 통일 같은 기계적 리팩터링은 `mid:low` 칸에서 시작한다. 자동 승격은 `high:medium`까지. / Mechanical refactoring such as renames, moving functions and unifying formats starts at `mid:low`. Automatic escalation stops at `high:medium`.**
  - 이유 · Why: [확인] Anthropic의 모델·강도 글: 기계적 변경은 작은 모델. [추정] 테스트가 있으면 낮은 강도로 충분하다. / [verified] Anthropic's model and effort article: mechanical changes go to a smaller model. [estimate] low effort is enough when tests exist.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.refactor.mechanical.cell`

### `task/refactor/structural` · 구조 리팩터링 · Structural refactoring

- **[권장 · should · model] 큰 구조 변경·의존성 교체 같은 구조 리팩터링은 `high:high` 칸에서 시작한다. 자동 승격은 `top:high`까지. / Structural refactoring such as large restructures or dependency swaps starts at `high:high`. Automatic escalation stops at `top:high`.**
  - 이유 · Why: [확인] Claude Code 비용 문서: Opus는 복잡한 설계 결정과 여러 단계 추론에 쓴다. [추정] 되돌리기 비용이 크고 여러 파일의 맞물림을 함께 봐야 한다. / [verified] Claude Code costs doc: reserve Opus for complex architectural decisions and multi-step reasoning. [estimate] high rollback cost and many interlocking files.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.refactor.structural.cell`

### `task/debug` · 디버깅 · Debugging

- **[권장 · should · model] 원인 모를 버그·간헐 실패는 `high:high` 칸에서 재현 테스트부터 만들며 고친다. 자동 승격은 `top:high`까지. / Unknown bugs and flaky failures are fixed at `high:high`, starting with a reproducing test. Automatic escalation stops at `top:high`.**
  - 이유 · Why: [확인] Anthropic의 모델·강도 글: 미묘한 버그는 큰 모델. Claude Code 강도 안내: high는 기존 코드의 버그 수정처럼 검증이 중요한 일. / [verified] Anthropic's model and effort article: subtle bugs go to the larger model. Claude Code effort guidance: high suits work where verification matters, such as fixing bugs in existing code.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.debug.cell`

### `task/test` · 테스트 작성 · Writing tests

- **[권장 · should · model] 테스트 작성은 `mid:medium` 칸에서 시작하고, 통과해도 아무것도 검사하지 않는 테스트가 없는지 사람이 본다. 자동 승격은 `high:medium`까지. / Writing tests starts at `mid:medium`; a person checks for tests that pass without asserting anything. Automatic escalation stops at `high:medium`.**
  - 이유 · Why: [추정] 테스트는 통과해도 의미가 없을 수 있어 기계 검증만으로는 품질을 다 알 수 없다. / [estimate] tests can pass while checking nothing, so machine verification alone cannot judge them.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.test.cell`

### `task/review` · 리뷰·판정 · Review and judging

- **[권장 · should · model] 리뷰·결과 판정은 `high:medium` 칸에서 하고, 되도록 작성한 모델과 다른 회사 모델로 한다. 하 등급으로 리뷰하지 않는다. 자동 승격은 `top:high`까지. / Review and judging run at `high:medium`, preferably on a different vendor than the author model. Never review with the low tier. Automatic escalation stops at `top:high`.**
  - 이유 · Why: [주장] LLM 판정자는 자기 계열 답을 좋게 보는 편향이 있다(Zheng 외, arXiv 2306.05685). [확인] Codex는 /review 전용 review_model을 따로 둔다. [추정] 작성 칸보다 한 단계 위. / [claim] LLM judges favor answers from their own family (Zheng et al., arXiv 2306.05685). [verified] Codex has a separate review_model for /review. [estimate] one step above the author cell.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.review.cell`

### `task/review/security` · 보안 리뷰 · Security review

- **[필수 · must · model] 보안 리뷰는 `high:high` 칸이 하한이다. 자동으로 내리지 않고, 결과가 미덥지 않으면 사람에게 넘긴다. 실제 모델은 `habitree models pick task/review/security`로 본다. / Security review has a floor of `high:high`. It is never lowered automatically, and doubtful results go to a person. Look up the real model with `habitree models pick task/review/security`.**
  - 이유 · Why: [추정] 놓친 문제를 되돌리는 비용이 매우 크다. / [estimate] a missed issue is very expensive to undo.
  - 점검 · Check (자동 · auto): `habitree check`의 models.floor가 에이전트 파일의 model을 하한과 비교하고, `habitree models export`는 하한보다 낮은 값을 쓰지 않는다. / `habitree check` (models.floor) compares agent files with the floor, and `habitree models export` never writes a lower value.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.review.security.floor`

### `task/docs` · 문서 · Documentation

- **[권장 · should · model] README·안내문·주석 같은 문서는 `mid:medium` 칸에서 쓰고, 쉬운 말과 정확성은 사람이 본다. 자동 승격은 `high:medium`까지. / Docs such as READMEs, guides and comments are written at `mid:medium`; a person checks plain wording and accuracy. Automatic escalation stops at `high:medium`.**
  - 이유 · Why: [추정] 링크·형식은 기계로 볼 수 있지만 읽기 쉬움은 사람이 본다. / [estimate] links and format can be machine-checked, readability cannot.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.docs.cell`

### `task/risky` · 위험 작업(인증·돈·개인정보·비밀값·마이그레이션·삭제·배포) · Risky work (auth, money, personal data, secrets, migrations, deletion, deploys)

- **[필수 · must · model] 인증·권한, 돈·결제, 개인정보, 비밀값, DB 마이그레이션, 삭제, 배포는 `high:high` 칸이 하한이다. 자동으로 내리지 않고, 실패하면 사람에게 넘긴다. 실제 모델은 `habitree models pick task/risky`로 본다. / Auth and permissions, money and payments, personal data, secrets, DB migrations, deletion and deploys have a floor of `high:high`. It is never lowered automatically, and failures go to a person. Look up the real model with `habitree models pick task/risky`.**
  - 이유 · Why: [추정] 되돌리기 비용이 매우 크다. 근거: Anthropic 'Building effective agents'는 자율 에이전트가 비용이 크고 오류가 쌓일 수 있어 격리 환경에서 충분히 시험하라고 한다. / [estimate] the cost of undoing is very high. Basis: Anthropic's 'Building effective agents' warns that autonomous agents cost more and compound errors, so test them extensively in sandboxes.
  - 점검 · Check (자동 · auto): `habitree check`의 models.floor가 에이전트 파일의 model을 하한과 비교하고, `habitree models export`는 하한보다 낮은 값을 쓰지 않는다. / `habitree check` (models.floor) compares agent files with the floor, and `habitree models export` never writes a lower value.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.risky.floor`

### `task/long-autonomous` · 몇 시간 도는 자율 작업 · Long-running autonomous work

- **[권장 · should · model] 몇 시간 도는 자율 조사·구현은 `top:high` 칸에서 하고, 끝나면 사람이 결과를 본다. / Autonomous research or implementation that runs for hours uses `top:high`, and a person reviews the result.**
  - 이유 · Why: [확인] Anthropic 모델 개요: Fable 5.1은 어려운 추론과 오래 도는 에이전트 작업용. [추정] 최상 등급은 승격이나 이런 명시적 지정으로만 쓴다. / [verified] Anthropic models overview: Fable 5.1 is for demanding reasoning and long-horizon agentic work. [estimate] the top tier is used only by escalation or explicit choice like this.
  - 점검 · Check (자동 · auto): `habitree models pick`·`export`가 이 칸을 쓴다. / `habitree models pick` and `export` use this cell.
  - 피드백 · feedback 0 · `pack:task@0.3.0` · `task.long-autonomous.cell`

