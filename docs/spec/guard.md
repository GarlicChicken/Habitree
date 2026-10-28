# 작업 중 경고와 위임

## 왜 만들었나

AI와 일하다 보면 낭비는 대개 끝난 뒤에야 보입니다. 같은 명령을 다섯 번 돌렸고, 같은 오류에 같은 수정을 되풀이했고, 파일 하나가 덧붙이기만으로 두 배가 됐다는 사실을 세션 기록을 읽고 나서 알게 됩니다. 그때는 이미 시간과 사용량을 쓴 뒤입니다.

v0.2는 이것을 일하는 도중에 알려 줍니다. 원칙은 세 가지입니다.

- **행동만 본다.** 도구 이름, 입력, 결과의 성패와 길이, 파일 경로, 요청 길이와 시각만 봅니다. 어떤 프로그래밍 언어의 프로젝트든, 코드가 아닌 문서 작업이든 똑같이 돕니다.
- **먼저 AI에게, 그래도 안 되면 사람에게.** 처음에는 AI 맥락에 사실을 한 줄 넣어 스스로 방향을 바꾸게 합니다. 그래도 되풀이하면 멈추고 사용자에게 묻습니다. 이미 막힘 감지를 가진 오픈소스(OpenHands, Gemini CLI, Cline)가 모두 이 두 단계를 씁니다.
- **경고도 규칙이다.** 감지 기준과 문구는 코드가 아니라 규칙 DB에 있습니다. 사용자가 "이 경고 맞았어", "틀렸어"라고 하면 `rules hit`·`rules miss`로 쌓이고, 그 반응이 기준값과 등급을 움직입니다. 말로 한 피드백이 규칙이 되는 사다리와 같은 길입니다.

## 어떻게 도나

AI 도구의 훅이 `habitree hook <이벤트>`를 부릅니다. 엔진은 훅 입력을 도구와 무관한 표준 이벤트로 바꾸고, 세션 상태에 적고, 그 이벤트에 걸린 감지 규칙을 돌린 뒤, 결과를 그 도구의 공식 출력 형식으로 돌려줍니다. 지금 어댑터는 Claude Code 하나이고, 다른 도구는 어댑터만 더하면 같은 감지기를 씁니다.

| 시점 · 훅 | 하는 일 |
|---|---|
| 세션 시작 `SessionStart` | 작업 순환과 필수 규칙 요약을 AI에게 넣는다(AGENTS.md가 이미 실리면 한 줄만). 새 세션과 `/clear`면 상태를 새로 열고(이어 가기·압축 때는 이어 쓴다), 7일 지난 상태를 지우고, 복사 코드 탐색용 파일 목록을 캐시한다. |
| 요청 `UserPromptSubmit` | 요청 쪼개기, 바로잡는 말, 거듭 정정, 섞인 주제, 위임 신호. |
| 도구 전 `PreToolUse` | 같은 호출, 고리, 같은 오류의 다음 시도 멈춤, 위임 중 위험한 일 확인. |
| 도구 뒤 `PostToolUse`·`PostToolUseFailure` | 잔수정, 파일 커짐, 복사 코드, 큰 결과, 같은 오류. |
| 끝 `Stop` | 빠른 점검(오류가 있으면 한 번 더 일하게), 위임 끝 보고, 이번 답의 알림을 모아 사용자에게. |

## 무엇을 잡나

기준값은 모두 출발값이고, 규칙의 `detect`에서 읽습니다. 프로젝트마다 `rules edit`이나 반응으로 바뀝니다.

| 규칙 | 패턴 | 신호 | 시점 | 기본 기준 | 제안 |
|---|---|---|---|---|---|
| `work.loop.same-call` | 같은 호출 되풀이 | 도구 이름 + 키를 정렬한 입력의 해시가 잇달아 같음 | 도구 전 | 3번 경고, 5번 멈춤 | 마지막 결과 다시 읽기, 다른 방법 하나 |
| `work.loop.same-error` | 같은 오류 되풀이 | 같은 호출이 같은 오류로 실패(사이의 읽기 호출은 허용) | 도구 뒤·전 | 3번 경고, 4번째 시도 전 멈춤 | 오류 문장에서 원인 찾기 |
| `work.loop.cycle` | 제자리 돌기 | 길이 1~5짜리 호출 묶음이 같은 순서로 반복 | 도구 전 | 5바퀴 경고, 7바퀴 멈춤 | 시도한 것과 가설 하나 적기 |
| `work.loop.small-edits` | 한 파일 잔수정 | 바뀐 줄 3줄 이하 수정, 15분 창, 검증 실행 사이 | 도구 뒤 | 6번(정보) | 고칠 곳 모아 한 번에 |
| `code.structure.file-growth` | 덧대기로 커지는 파일 | 세션 처음 대비 줄 수 증가, 더한 줄:지운 줄 | 도구 뒤 | 30% 이상, 10:1 이상, 150줄 이상 파일 | 새 기능은 따로 파일·함수로 |
| `code.structure.copy-block` | 복사 코드 | 새로 들어간 줄을 정리해 6줄씩 해시, 다른 파일과 비교 | 도구 뒤 | 6줄, 파일 400개·파일당 256KiB 상한 | 있는 코드 불러 쓰기 |
| `work.context.big-output` | 큰 결과 | 도구 결과의 글자 수 | 도구 뒤 | 20,000자 | 검색 뒤 필요한 범위만 |
| `work.request.split` | 요청 쪼개 보내기 | 40자 이하 요청이 5분 안에(대답 한 마디·/명령 제외) | 요청 | 3개 | 원하는 것·조건·끝 기준을 한 메시지로 |
| `work.request.correction-to-rule` | 바로잡는 말 | 세션 첫 요청이 아닌 메시지에 바로잡는 말(…하지 마, 대신, …써야 해, …하기로 했어, 아니 등) | 요청 | 1번, 그때 AI에게 | 고친 뒤 규칙으로 남기기 |
| `work.request.repeat-correction` | 같은 지적 거듭 | 정정 표현이 같은 주제로 이어짐 | 요청 | 2번 | 배운 것을 담아 새로 시작, 규칙으로 남기기 |
| `work.context.topic-mix` | 한 세션에 여러 주제 | 긴 세션에서 새 요청 낱말이 앞 요청과 거의 안 겹침 | 요청 | 30턴 또는 기록 1MB(정보) | 새 대화로 |
| `work.verify.run-before-done` | 검증 없이 끝 | 수정은 있었는데 설정 `verify` 명령 실행 0번 | 끝 | 수정 1번 이상(정보) | 검증 한 번 |
| `work.delegate.declare` | 위임 시작 | 위임 표현(아래) | 요청 | 늘 | 범위를 되말하기 |
| `work.delegate.risky-ask` | 위임 중 위험한 일 | 명령·도구 이름·경로 | 도구 전 | 늘(위임 중) | 사용자 확인 |
| `work.delegate.end-report` | 위임 끝 보고 | 위임 중 Stop | 끝 | 한 번 | 대신 정한 것 보고 |

같은 호출 3번·5번, 같은 오류 3번은 조사한 도구들의 코드에서 확인한 값입니다(Cline 3번 경고·5번 멈춤, OpenHands 같은 오류 3번 뒤 넛지, Gemini CLI 5바퀴). 20,000자는 keel이 한 사용자의 기록으로 맞춘 값이라 출발값일 뿐입니다. 요청을 여러 턴에 나눠 주면 한 번에 줄 때보다 결과가 평균 39% 나빠졌다는 실험이 요청 쪼개기 규칙의 근거입니다(Laban 외 2025, "LLMs Get Lost In Multi-Turn Conversation"). 근거가 약하거나 오탐이 잦을 패턴(잔수정, 섞인 주제, 검증 없이 끝)은 정보 등급으로 시작합니다.

**고리가 아닌 것.** 정상 작업을 고리로 오해하지 않게 판정 방식에 예외를 넣었습니다. Gemini CLI가 판정 지시문에 적어 둔 목록을 따랐습니다.

- 다른 파일을 차례로 읽거나 고치는 일: 입력이 달라 같은 호출이 아닙니다.
- 인자를 바꾼 재시도: 해시가 달라집니다.
- 코드를 고친 뒤 테스트를 다시 돌리는 일: 사이의 수정이 연속을 끊습니다.
- 백그라운드 작업 결과를 다시 보는 호출(`BashOutput` 등): 세지 않습니다.
- 설명만 다른 같은 명령: 설명 칸은 빼고 비교합니다(이건 고리로 셉니다).

## 경고가 잔소리가 되지 않게

- **같은 연속에는 한 번만.** 규칙마다 `repeat`(`once_per_streak`·`once_per_session`·`always`)과 `max_per_session`이 있습니다.
- **겹치지 않게.** 같은 호출 되풀이와 같은 오류 되풀이처럼 한 사건을 두 규칙이 볼 때는 먼저 알린 쪽만 말합니다.
- **정보는 모아서.** 정보 등급은 그때그때 말하지 않고, 답이 끝날 때 "이번 답의 알림"으로 한 번에 보여 줍니다. AI에게 먼저 알린 경고도 사용자는 이 요약에서 봅니다.
- **세션별 끄기.** `habitree guard off <id>`는 이 세션에서만 끕니다. 이것은 '틀렸다'로 세지 않고 `votes`에 `off`로 따로 남깁니다. 바빠서 끈 것과 틀려서 끈 것은 다른 신호입니다.
- **반응으로 조정.** Google Tricorder의 방식을 따릅니다. 최근 반응 20개 중 '틀렸다'가 10% 이상이면 기준값을 한 단계 완화하고, 25%를 넘으면 `check`가 끄기를 제안합니다(Sadowski 외, ICSE 2015). '맞았다'가 2번이고 '틀렸다'가 없으면 정보에서 경고로 오릅니다. 멈춤 등급으로는 자동으로 올리지 않습니다.
- **문구.** 본 것을 숫자로, 왜 손해인지 한 문장, 무엇을 하면 되는지 번호 붙인 두세 단계. 강요하지 않고, 사람이 아니라 작업을 주어로 씁니다. AI에게 넣는 글은 명령조가 아니라 사실을 적는 말투로 씁니다(공식 훅 문서의 권고).
- **고쳐 달라는 길.** 모든 경고 끝에 규칙 id가 붙습니다. 사용자가 그 알림이 틀렸다고 말하면 AI가 `habitree rules miss <id>`로 남깁니다.

## 경고가 가는 길

| 대상 | 길 | 쓰는 때 |
|---|---|---|
| AI | `hookSpecificOutput.additionalContext` | 대부분의 경고. AI가 스스로 방향을 바꿀 수 있는 것 |
| 사용자 | `systemMessage` | 사용자 요청 방식에 대한 것(쪼개기, 거듭 정정), 멈춤 |
| 사용자(AI를 거쳐) | AI 맥락에 "다음 줄을 사용자에게 전하면 된다" | 사용자용 알림을 화면에 보여 주지 않는 앱을 대비해 함께 넣는다(`guard.relay`로 끌 수 있음) |
| 사용자(확인 창) | `permissionDecision: "ask"` + 이유 | 멈춤 등급, 위임 중 위험한 일 |
| AI(계속 일하게) | Stop의 `decision: "block"` + `reason` | 끝내기 전 점검 오류, 위임 끝 보고 |

Claude Code 데스크톱 앱은 Stop 말고는 `systemMessage`를 보여 주지 않는다는 이슈 보고가 있어(#103739) AI 전달을 함께 둡니다. 이 동작은 공식 문서에서 확인하지 못했습니다.

## 위임 예외

사용자가 "알아서 해 줘", "묻지 말고 끝까지 해", "just do it"처럼 맡기면, 그 작업 하나에 한해서는 되묻기와 경고를 줄이고 추천안대로 진행합니다. 맡김은 '묻지 말라'는 뜻이지 '낭비해도 된다'거나 '위험해도 된다'는 뜻이 아니므로, 지켜지는 경계가 있습니다.

- **범위를 되말한다.** AI는 답의 첫 줄에서 "이 작업에 한해서는 되묻기 없이 추천안대로 진행하겠습니다"라고 범위를 밝힙니다. 잘못 알아들었으면 사용자가 바로 바로잡을 수 있습니다.
- **위임으로 보지 않는 말.** 따옴표 안의 인용("'알아서 해 줘'라고 하면?"), 질문("알아서 해 줄 수 있어?"), 남의 말("팀장님이 알아서 하래"), 부정("알아서 하지 마").
- **경계는 저장한다.** 함께 들어온 부정·조건("다만 파일은 지우지는 마", "don't push")은 세션 상태에 경계로 남겨 대화가 압축돼도 사라지지 않습니다. 경계는 좁히기만 합니다.
- **위험한 일은 그때도 묻는다.** 지우기, 배포·올리기(`git push` 포함), 외부로 보내기, 결제, 비밀 정보, 작업 폴더 밖 수정, 맡긴 범위 밖 파일은 위임 중에도 `ask`로 확인을 받습니다. 경계와 범주가 맞으면 그 경계 문장을 함께 보여 줍니다.
- **규칙마다 처리 방식.** `on_delegate`가 `skip`이면 알리지 않고 끝 보고에 모으고(효율 경고 대부분), `nudge`면 AI에게만 알리고(막힘: 멈춤 등급이면 묻지 않고 그 호출을 막고 상황을 보고하게 함), `ask`면 위임 중에도 사용자에게 묻습니다.
- **끝 보고.** 위임 중 Stop에서 한 번 막고 끝 보고를 받습니다: 대신 정한 것마다 무엇·왜·다른 안·되돌리는 법, 미뤄 둔 알림, 실행한 검사와 결과, 확인이 필요한 것. 사용자가 그 보고에서 바로잡은 것은 피드백이고, 규칙으로 쌓입니다.
- **끝나는 때.** 끝 보고 뒤, 취소 표현("이제 물어보고 해", "ask me first"), 새 주제, 한도(기본 도구 호출 200번), `/clear`.
- **명시 명령.** 말 대신 `/habitree:delegate <작업>`이나 `habitree guard delegate on --task "…" --boundary "…"`로도 켜고 끕니다.

## 규칙 DB에 얹기

감지 규칙은 보통 규칙에 아래 칸을 더한 것입니다. 형식은 [rules.schema.json](../../src/habitree/data/schema/rules.schema.json)에 있습니다.

| 칸 | 뜻 |
|---|---|
| `detect.signal` | 감지기 이름(`same_call_streak` 등) |
| `detect.event` | 도는 훅(`PreToolUse`, 여럿이면 `PostToolUse\|PreToolUse`) |
| `detect.threshold`, `detect.stop_at` | 경고 기준, 멈춤 기준 |
| `detect.severity` | `info`·`warn`·`stop` |
| `detect.repeat`, `detect.max_per_session` | 반복 제한 |
| `detect.audience` | 먼저 알릴 대상 `ai`·`user`·`both` |
| `detect.now` | 정보 등급이라도 답 끝까지 모으지 않고 그때 AI에게 알림 |
| `detect.params` | 감지기별 값(창 길이, 최소 줄 수 등) |
| `message.ai`, `message.user`, `message.suggest` | 문구(두 언어), `{n}` 같은 자리표시자 |
| `on_delegate` | 위임 중 처리 `skip`·`ask`·`nudge` |
| `votes` | 반응 기록 `useful`·`miss`·`off` |

기본 감지 규칙은 `work` 꾸러미에 있고, `habitree init`이 넣습니다. 이미 설치한 프로젝트는 `habitree init`을 다시 돌리면 새 규칙만 더해집니다.

## 설치

**플러그인(권장).** 엔진을 먼저 설치하고, 같은 리포를 마켓플레이스로 더합니다.

```
uv tool install git+https://github.com/GarlicChicken/habitree
claude plugin marketplace add GarlicChicken/habitree
claude plugin install habitree@habitree
```

플러그인은 훅(`hooks/hooks.json`)과 스킬 세 개(작업 순환, 피드백을 규칙으로, 위임)를 넣습니다. 훅은 셸을 거치지 않는 exec 형식으로 `habitree hook <이벤트>`를 부르므로 bash·zsh·PowerShell 어디서나 같게 돕니다.

**플러그인 없이.** `habitree init --hooks`가 프로젝트의 `.claude/settings.json`에 같은 훅을 더합니다. 있는 내용은 그대로 두고, 이미 있으면 다시 넣지 않습니다. 사용자 전역 설정(`~/.claude/settings.json`)은 건드리지 않습니다. 둘을 함께 써도 같은 훅이 두 번 처리되지 않게 막아 두었지만, 하나만 쓰는 것을 권합니다.

프로젝트에 `.habitree/config.json`이 없으면 훅은 아무것도 하지 않습니다. 훅 안에서 오류가 나도 작업은 막지 않고(종료 코드 0), `.habitree/state/hook-errors.log`에만 남깁니다.

## 설정

`.habitree/config.json`의 `guard` 절입니다.

| 칸 | 기본 | 뜻 |
|---|---|---|
| `enabled` | `true` | 훅 전체 켜기·끄기 |
| `stop_check` | `true` | 끝내기 전 빠른 점검(`check`에서 자동 검사·사용자 명령을 뺀 것), 오류면 한 번 더 일하게 |
| `stop_check_max` | `3` | 세션당 점검으로 막는 최대 횟수 |
| `session_start` | `"auto"` | 세션 시작 글: `auto`(AGENTS.md가 실리면 짧게), `full`, `short`, `off` |
| `session_budget` | `1500` | 세션 시작 글의 필수 규칙 글자 예산 |
| `relay` | `"always"` | 사용자용 알림을 AI 맥락에도 넣을지(`never`로 끔) |
| `history` | `40` | 남기는 최근 호출·결과 수 |
| `state_days` | `7` | 세션 상태를 지우기까지 날짜 |
| `delegate.natural` | `true` | 말로 한 위임 감지 |
| `delegate.max_tools` | `200` | 위임 한 번의 도구 호출 한도 |

## 상태 파일과 개인정보

세션 상태는 `.habitree/state/sessions/<세션 id>.json`에 있고 git에 올리지 않습니다. 요청 원문은 저장하지 않고 낱말 묶음과 길이만 남깁니다. 예외는 위임한 작업의 첫 줄과 경계 문장으로, 끝 보고에 필요해서 남깁니다. 경로 키는 NFC로 맞추고 대소문자를 구분하지 않는 파일 시스템(Windows·macOS 기본)에서는 casefold해서, 같은 파일이 다른 철자로 두 번 세지지 않게 합니다. 여러 훅이 동시에 돌 수 있어 짧은 잠금 파일을 쓰고, 잠금을 못 잡으면 기다리지 않고 그냥 통과합니다.

## 한계

- 훅은 도구를 쓸 때마다 앞뒤로 두 번 돌고, 한 번에 Python을 새로 띄웁니다. 개발 컴퓨터(Windows)에서 Python 시작을 빼고 한 번에 약 55~115ms(부하에 따라)가 더해졌습니다. 읽기만 하는 도구는 '사용 전' 훅이 필요 없을 수 있어, 반복 감지를 '사용 후'로 옮겨 훅 호출을 줄이는 것을 다음에 볼 일로 남겨 두었습니다.
- 같음은 정확히 같은 입력으로만 봅니다. 말을 바꿔 같은 일을 되풀이하는 것은 못 잡습니다.
- 복사 코드는 줄 해시라 이름만 바꾼 복사는 못 잡습니다. 정밀하게 보려면 jscpd 같은 언어별 도구가 필요합니다.
- 정정·위임 표현은 한국어와 영어 사전입니다. 다른 언어는 `detect.params`로 더해야 합니다.
- 주제 판단은 낱말 겹침이라 틀릴 수 있어 정보로만 알립니다.
- 훅은 Python으로 돌아 이벤트마다 프로세스 시작 시간이 듭니다. 걸리는 시간은 직접 재서 공개하기 전에는 수치로 약속하지 않습니다.

## English

### Why

When working with an AI, waste usually shows up only afterwards. You read the session log and learn that the same command ran five times, the same fix was retried on the same error, and one file doubled in size through appending alone. By then the time and usage are already spent.

v0.2 says so while the work is happening. Three principles:

- **Only behavior is observed.** Tool name, input, success and size of the result, file path, prompt length and time. It works the same for a project in any programming language, or for writing that is not code at all.
- **The AI first, then the person.** First a one-line fact goes into the AI's context so it can change course on its own. If it keeps repeating, it stops and asks the user. The open-source tools that already detect getting stuck (OpenHands, Gemini CLI, Cline) all use these two steps.
- **Warnings are rules too.** Thresholds and wording live in the rule DB, not in code. When the user says "that warning was right" or "wrong", it is recorded with `rules hit` or `rules miss`, and those votes move the thresholds and levels. It is the same ladder that turns spoken feedback into rules.

### How it runs

An AI tool's hook calls `habitree hook <event>`. The engine turns the hook input into a tool-neutral event, records it in the session state, runs the detection rules for that event, and returns the result in that tool's official output format. Today the only adapter is Claude Code; another tool needs only a new adapter to reuse the same detectors.

| When · hook | What happens |
|---|---|
| Session start `SessionStart` | Injects the work cycle and a must-rule summary for the AI (a single line when AGENTS.md is already loaded). Opens fresh state for a new session or `/clear` (resume and compaction keep it), removes state older than 7 days, caches the file list for copy detection. |
| Prompt `UserPromptSubmit` | Split requests, correcting words, repeated corrections, mixed topics, delegation phrases. |
| Before a tool `PreToolUse` | Same call, cycles, stopping the next try of a repeated error, confirming risky actions during delegation. |
| After a tool `PostToolUse`, `PostToolUseFailure` | Small edits, file growth, copied code, large results, repeated errors. |
| End `Stop` | Quick check (one more round of work if it finds errors), the delegation end report, and the notes from this reply gathered for the user. |

### What it catches

All thresholds are starting values read from each rule's `detect`. They change per project through `rules edit` or votes.

| Rule | Pattern | Signal | When | Default | Suggestion |
|---|---|---|---|---|---|
| `work.loop.same-call` | Same call repeated | Hash of tool name and key-sorted input is the same in a row | Before tool | warn at 3, stop at 5 | Reread the last result, pick another approach |
| `work.loop.same-error` | Same error repeated | Same call fails with the same error (read-only calls in between are allowed) | After and before tool | warn at 3, stop before the 4th try | Find the cause in the error text |
| `work.loop.cycle` | Going in circles | A block of 1 to 5 calls repeats in order | Before tool | warn at 5 laps, stop at 7 | Write down attempts and one hypothesis |
| `work.loop.small-edits` | Many small edits to one file | Edits of 3 changed lines or fewer, 15 minute window, between verify runs | After tool | 6 (info) | Collect the spots, edit once |
| `code.structure.file-growth` | File grown by appending | Line growth since session start, added to removed ratio | After tool | 30% or more, 10:1 or more, files of 150+ lines | Put the new feature in its own file or function |
| `code.structure.copy-block` | Copied code | New lines trimmed and hashed in 6 line windows, compared with other files | After tool | 6 lines, limits of 400 files and 256 KiB per file | Call the existing code |
| `work.context.big-output` | Large result | Characters in the tool result | After tool | 20,000 | Search, then read only the range needed |
| `work.request.split` | Split requests | Prompts of 40 chars or fewer within 5 minutes (acknowledgements and / commands excluded) | Prompt | 3 | One message with goal, conditions and finish line |
| `work.request.correction-to-rule` | A correction | Correcting words (don't, instead, should use, we decided, no, and so on) in a message after the session's first | Prompt | 1, to the AI right away | Fix it and record a rule |
| `work.request.repeat-correction` | Same correction again | Correction phrases on the same topic | Prompt | 2 | Start fresh with what was learned; record a rule |
| `work.context.topic-mix` | Several topics in one session | In a long session, the new prompt shares almost no words with earlier ones | Prompt | 30 turns or a 1 MB transcript (info) | New conversation |
| `work.verify.run-before-done` | Done without verifying | Edits happened but the configured `verify` command never ran | End | 1 edit or more (info) | Run verify once |
| `work.delegate.declare` | Delegation starts | A delegation phrase (below) | Prompt | always | Restate the scope |
| `work.delegate.risky-ask` | Risky action while delegated | Command, tool name, path | Before tool | always while delegated | Ask the user |
| `work.delegate.end-report` | Delegation end report | Stop while delegated | End | once | Report the decisions made |

Same call 3 and 5 and same error 3 are values confirmed in the code of the tools we reviewed (Cline warns at 3 and stops at 5, OpenHands nudges after the same error 3 times, Gemini CLI uses 5 laps). 20,000 characters is a value keel tuned on one user's logs, so it is only a starting point. The split-request rule rests on an experiment where instructions split over several turns did 39% worse on average than the same instructions given at once (Laban et al. 2025, "LLMs Get Lost In Multi-Turn Conversation"). Patterns with weak evidence or likely false alarms (small edits, mixed topics, done without verifying) start at the info level.

**What is not a loop.** Exceptions are built into the judgment so normal work is not mistaken for a loop. They follow the list Gemini CLI wrote into its loop prompt.

- Reading or editing different files in turn: the inputs differ, so these are not the same call.
- Retrying with changed arguments: the hash changes.
- Rerunning tests after changing code: the edit in between breaks the streak.
- Calls that poll background work (`BashOutput` and similar): not counted.
- The same command with only a different description: the description field is ignored (this does count as a loop).

### Keeping warnings from becoming nagging

- **Once per streak.** Each rule has `repeat` (`once_per_streak`, `once_per_session`, `always`) and `max_per_session`.
- **No overlap.** When two rules see one event, like a repeated call that is also a repeated error, only the first one speaks.
- **Info is gathered.** Info-level notes are not said right away; they appear once at the end of the reply as "notes from this reply". The user also sees warnings that went to the AI first in this summary.
- **Mute per session.** `habitree guard off <id>` mutes a rule for this session only. It is not counted as "wrong"; it is stored separately in `votes` as `off`. Muting because you are busy and muting because it was wrong are different signals.
- **Votes adjust it.** This follows Google Tricorder. If 10% or more of the last 20 votes say "wrong", the threshold relaxes one step; above 25%, `check` suggests pausing the rule (Sadowski et al., ICSE 2015). Two "useful" votes and no "wrong" raise a rule from info to warn. Nothing is raised to the stop level automatically.
- **Wording.** State what was seen as a number, one sentence on why it costs, two or three numbered steps to take. No pressure, and the work is the subject, not the person. Text for the AI is written as plain facts, not commands, as the official hooks documentation advises.
- **A way to push back.** Every warning ends with its rule id. When the user says it was wrong, the AI records `habitree rules miss <id>`.

### Where warnings go

| To | Channel | Used for |
|---|---|---|
| AI | `hookSpecificOutput.additionalContext` | Most warnings, things the AI can correct by itself |
| User | `systemMessage` | Things about how the user sends requests (split, repeated corrections), and stops |
| User, through the AI | A line in the AI context saying the next line can be passed to the user | Added alongside, for apps that do not show user notes on screen (turn off with `guard.relay`) |
| User, confirmation dialog | `permissionDecision: "ask"` with a reason | Stop level, risky actions while delegated |
| AI, keep working | Stop `decision: "block"` with `reason` | Errors from the pre-finish check, the delegation end report |

An issue report says the Claude Code desktop app shows `systemMessage` only for Stop hooks (#103739), which is why the relay through the AI exists. We could not confirm this behavior in the official documentation.

### Delegation

When the user hands over a task with "just do it", "don't ask, finish it" or "알아서 해 줘", questions and warnings are reduced for that one task and the recommended options are used. Delegation means "don't ask me", not "waste is fine" or "risk is fine", so some boundaries hold.

- **The scope is restated.** The AI's first line says that, for this task only, it will proceed without asking. If it misunderstood, the user can correct it at once.
- **What is not delegation.** Quoted text ("what happens if I say 'just do it'?"), questions ("can you just do it?"), reported speech ("he said just do it"), and negation ("don't just do it").
- **Boundaries are stored.** Negations and conditions that come with it ("but don't delete files", "don't push") are kept in the session state as boundaries, so they survive context compaction. Boundaries only narrow.
- **Risky actions still ask.** Deleting, deploying or pushing (including `git push`), sending data outside, payments, secrets, changes outside the project, and files outside the delegated scope all ask for confirmation with `ask`, even while delegated. When a boundary matches the category, its sentence is shown too.
- **Per-rule handling.** With `on_delegate: skip` the warning is held for the end report (most efficiency warnings); with `nudge` only the AI hears it (for getting stuck: at the stop level the call is blocked without asking the user and the AI is told to report); with `ask` the user is asked even while delegated.
- **The end report.** At Stop during delegation, the hook blocks once to get the end report: each decision made with what, why, the alternative and how to undo it; the notes held back; the checks run and their results; anything that needs confirmation. Corrections the user makes to that report are feedback and become rules.
- **When it ends.** After the end report, on a cancel phrase ("ask me first", "이제 물어보고 해"), on a new topic, at the limit (200 tool calls by default), or on `/clear`.
- **Explicit commands.** Instead of words, `/habitree:delegate <task>` or `habitree guard delegate on --task "…" --boundary "…"` turns it on and off.

### On the rule DB

A detection rule is an ordinary rule with these extra fields. The format is in [rules.schema.json](../../src/habitree/data/schema/rules.schema.json).

| Field | Meaning |
|---|---|
| `detect.signal` | Detector name (`same_call_streak` and so on) |
| `detect.event` | Hook it runs on (`PreToolUse`; several as `PostToolUse\|PreToolUse`) |
| `detect.threshold`, `detect.stop_at` | Warning threshold, stop threshold |
| `detect.severity` | `info`, `warn`, `stop` |
| `detect.repeat`, `detect.max_per_session` | Repeat limits |
| `detect.audience` | Who hears it first: `ai`, `user`, `both` |
| `detect.now` | Tell the AI right away even at info level, instead of collecting it for the end of the reply |
| `detect.params` | Detector-specific values (window length, minimum lines, ...) |
| `message.ai`, `message.user`, `message.suggest` | Wording in two languages, with placeholders like `{n}` |
| `on_delegate` | Handling while delegated: `skip`, `ask`, `nudge` |
| `votes` | Votes: `useful`, `miss`, `off` |

The default detection rules are in the `work` pack, which `habitree init` installs. In a project that already has Habitree, running `habitree init` again adds only the new rules.

### Install

**Plugin (recommended).** Install the engine first, then add the same repository as a marketplace.

```
uv tool install git+https://github.com/GarlicChicken/habitree
claude plugin marketplace add GarlicChicken/habitree
claude plugin install habitree@habitree
```

The plugin adds the hooks (`hooks/hooks.json`) and three skills (work cycle, feedback to rules, delegation). The hooks call `habitree hook <event>` in exec form without a shell, so they behave the same under bash, zsh or PowerShell.

**Without the plugin.** `habitree init --hooks` adds the same hooks to the project's `.claude/settings.json`. Existing content stays, and nothing is added twice. The user-global settings (`~/.claude/settings.json`) are never touched. Using both is guarded so a hook is not processed twice, but using one of them is recommended.

When the project has no `.habitree/config.json`, the hooks do nothing. An error inside a hook never blocks work (exit code 0); it is only written to `.habitree/state/hook-errors.log`.

### Settings

The `guard` section of `.habitree/config.json`.

| Field | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Turn all hooks on or off |
| `stop_check` | `true` | Quick check before finishing (`check` without automatic checks and custom commands); one more round of work on errors |
| `stop_check_max` | `3` | Maximum check blocks per session |
| `session_start` | `"auto"` | Session start text: `auto` (short when AGENTS.md is loaded), `full`, `short`, `off` |
| `session_budget` | `1500` | Character budget for must rules in the session start text |
| `relay` | `"always"` | Also put user notes in the AI context (`never` turns it off) |
| `history` | `40` | Recent calls and results kept |
| `state_days` | `7` | Days before session state is removed |
| `delegate.natural` | `true` | Detect delegation in plain words |
| `delegate.max_tools` | `200` | Tool call limit for one delegation |

### State files and privacy

Session state lives in `.habitree/state/sessions/<session id>.json` and is not committed. Prompt text is not stored, only word sets and lengths. The exceptions are the first line of a delegated task and its boundary sentences, kept because the end report needs them. Path keys are normalized to NFC and casefolded on case-insensitive filesystems (the default on Windows and macOS), so one file is not counted twice under two spellings. Several hooks can run at once, so a short lock file is used; if the lock cannot be taken, the hook simply passes instead of waiting.

### Limits

- Hooks run twice per tool call and start a fresh Python each time. On the development machine (Windows) each call added about 55 to 115 ms on top of starting Python, depending on load. Read-only tools may not need the pre-use hook; moving repeat detection to the post-use hook to cut hook calls is left as a next step.
- Sameness means exactly the same input. Doing the same thing in different words is not caught.
- Copy detection uses line hashes, so copies with renamed identifiers are missed. A language-aware tool such as jscpd is needed for that.
- Correction and delegation phrases are Korean and English dictionaries. Other languages need entries in `detect.params`.
- Topic detection uses word overlap and can be wrong, so it is only a note.
- The hooks run in Python, so every event pays a process start. We do not promise speed figures until we measure and publish them.
