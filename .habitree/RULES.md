# 규칙 · Rules

> 이 문서는 [rules.json](rules.json)에서 자동으로 만든다. 직접 고치지 말고 `habitree rules`로 고친다.
> Generated from [rules.json](rules.json). Do not edit by hand; use `habitree rules`.

- 규칙 26개 · 피드백 0건 · 마지막 피드백 -
- 26 rules · 0 feedback entries · last feedback -

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
| 　　`code/structure` | 코드 구조(모듈, 파일 크기, 중복) · Code structure (modules, file size, duplication) | 3 |
| 　`security` | 보안과 개인정보 · Security and privacy | 1 |

## 관점 · Aspects

| 관점 · Aspect | 뜻 · Meaning | 규칙 · Rules |
|---|---|---|
| `process` | 절차와 작업 순서 · Process and order of work | 13 |
| `structure` | 구조와 나누기 · Structure and modularity | 4 |
| `quality` | 품질과 검증 · Quality and verification | 3 |
| `docs` | 문서와 기록 · Docs and records | 4 |
| `security` | 보안과 개인정보 · Security and privacy | 2 |
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

- **[권장 · should · structure] 새로 쓰는 줄 묶음이 다른 파일에 이미 있으면 붙여 넣지 말고, 있는 것을 불러 쓰거나 공통 함수로 뺀다. / If newly written lines already exist in another file, do not paste them; call the existing code or extract a shared function.**
  - 이유 · Why: 복사본은 따로 낡아서 고칠 곳이 늘어난다. / Copies go stale separately, so there are more places to fix.
  - 점검 · Check (자동 · auto): PostToolUse 훅이 새로 들어간 줄을 공백을 정리해 6줄씩 해시하고 다른 파일과 비교한다(탐색 파일 수·크기 상한). / The PostToolUse hook hashes new lines in 6 line windows after trimming whitespace and compares other files (with file count and size limits).
  - 감지 · Detect: `copy_block` · PostToolUse · threshold 6 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `code.structure.copy-block`
- **[권장 · should · structure] 한 세션 안에서 기존 파일이 거의 더하기만으로 크게 불어나면, 새 기능은 따로 파일이나 함수로 떼어 낸다. / When an existing file balloons within one session through additions alone, move the new feature into its own file or function.**
  - 이유 · Why: 덧붙이기로 커진 파일은 읽을 때마다 사용량이 많이 들고, 고칠 때 엉뚱한 곳이 깨지기 쉽다. / A file grown by appending costs more to read every time and breaks in odd places when changed.
  - 점검 · Check (자동 · auto): PostToolUse 훅이 세션 처음 줄 수와 지금 줄 수, 더한 줄과 지운 줄을 파일별로 비교한다. / The PostToolUse hook compares the start and current line count and the added and removed lines per file.
  - 감지 · Detect: `file_growth` · PostToolUse · threshold 30 · warn
  - 피드백 · feedback 0 · `pack:work@0.2.0` · `code.structure.file-growth`
- **[권장 · should · structure] 기능을 더할 때 기존 함수·파일에 덧대지 말고 역할별 모듈·함수로 나눈다. 한 파일이 계속 커지면 나눌 때다. / When adding features, split by responsibility into modules and functions instead of patching onto existing ones. A file that keeps growing is due for a split.**
  - 이유 · Why: 덧대기로 커진 코드는 읽을 때마다 토큰이 많이 들고, 고칠 때 엉뚱한 곳이 깨진다. / Patched-up code costs more tokens to read and breaks in unexpected places when changed.
  - 점검 · Check (눈으로 · review): 이번에 크게 늘어난 파일이 있는지, 비슷한 코드가 복사됐는지 본다. / Did any file grow a lot, or was similar code copied?
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `code.structure.module-over-patch`

### `security` · 보안과 개인정보 · Security and privacy

- **[필수 · must · security] API 키·토큰·비밀번호·개인정보를 코드, 문서, 커밋에 넣지 않는다. 환경 변수나 .env(커밋 제외)로 받는다. / Never put API keys, tokens, passwords or personal data in code, docs or commits. Read them from environment variables or an uncommitted .env.**
  - 이유 · Why: 한 번 공개된 비밀은 지워도 이미 퍼졌을 수 있다. / A secret once published may already have spread, even after deletion.
  - 점검 · Check (자동 · auto): 잘 알려진 키 형식(sk-, ghp_, AKIA, 개인 키 머리말)이 파일에 없는지 자동으로 찾는다. / Automatically scans files for well-known key formats (sk-, ghp_, AKIA, private key headers).
  - 피드백 · feedback 0 · `pack:base@0.1.0` · `security.no-secrets`

