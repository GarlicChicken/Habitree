# 바뀐 것

새 버전을 위에 씁니다.

## 0.9.0 (2026-10-28)

이름 그대로 규칙이 자라는지 두 세션으로 재고, 재다가 발견한 끊긴 고리를 이은 버전입니다. 자세한 것은 [bench/2026-10-28-rules-grow.md](bench/2026-10-28-rules-grow.md).

- `habitree rules`로 규칙을 더하거나 고치면 이미 있는 AI 지침(AGENTS.md, CLAUDE.md)의 생성 구역을 바로 고칩니다. 전에는 `habitree export`를 따로 돌려야 해서, 다음 세션이 새 규칙을 보지 못했습니다. 직접 고친 구역은 그대로 두고 알립니다.
- 감지 규칙 `work.request.correction-to-rule`: 세션의 첫 요청이 아닌 메시지에 바로잡는 말("~하지 마", "대신", "~써야 해", "~하기로 했어", "이미 있어", "아니" 등)이 오면, 그 순간 AI에게 구체적인 규칙으로 남기라고 알립니다. 바로 쓸 명령과 기본값을 함께 줘서 쓰는 법을 찾느라 헤매지 않게 했습니다.
- 감지 규칙 칸 `detect.now`: 정보 등급이라도 답 끝까지 모으지 않고 그때 AI에게 알립니다.
- 꾸러미 규칙에 이 프로젝트의 지적이 붙으면(`rules hit`) AGENTS.md의 '이 프로젝트의 규칙'에 싣습니다.
- RULES.md 머리말과 `feedback-to-rule` 스킬이 미리 찾지 말고 바로 `rules add`를 쓰게 안내합니다. 같은 뜻 규칙은 add가 알려 줍니다.
- 두 세션 측정 `bench/grow.py`와, `reuse-helper`·`money-rules`의 다음 과제(`grow`).
- 두 세션 측정: 바로잡힌 흐름에서 Habitree 쪽은 5번 모두 시키지 않아도 규칙을 남겼고 다음 세션 5/5 합격, 없는 쪽은 6번 바로잡혔지만 다음 세션 0/6.

## 0.8.0 (2026-10-28)

처음으로 실제 측정을 하고, 그 결과에 따라 AI가 매번 읽는 지침을 걷어낸 버전입니다. 자세한 것은 [bench/2026-10-28-first-measurement.md](bench/2026-10-28-first-measurement.md).

- AI 지침의 기본을 걷어낸 판으로 바꿨습니다(`export.style: lean`). "있는 것을 먼저 찾아 쓴다", "바로잡힌 것은 규칙으로 남긴다"와 그 프로젝트에서 쌓인 규칙만 싣습니다. 검증 명령이 등록돼 있으면 그 명령을, 파일이 150개 이상이면 `habitree map find` 안내를 붙입니다. 늘 읽는 지침에는 도구 명령 이름을 쓰지 않고, 쓰는 법은 RULES.md 머리말에 둡니다. 여섯 단계 판은 `export.style: full`.
- 새 프로젝트는 규칙 0개로 시작합니다. `base`·`work`·`task` 꾸러미 모두 패키지에서 바로 읽고, 반응하거나 고친 규칙만 프로젝트에 남깁니다.
- 세션 시작 때 넣는 글도 같은 걷어낸 판을 씁니다.
- 큰 결과 알림이 `habitree map find`로 위치부터 찾으라고 제안합니다. `habitree init --mcp`가 프로젝트 `.mcp.json`에 MCP 서버를 더합니다.
- 측정 과제 `find-in-tree`(여러 폴더에서 고칠 곳 찾기)를 더했습니다.
- 첫 측정: 작은 과제 3개, Sonnet, 66번 실행. 피드백 규칙이 있는 과제에서 Habitree 쪽 29/29 합격, 없는 쪽 0/14. 일반 절차를 실은 이전 지침은 정답률 변화 없이 토큰 11~21%를 더 썼습니다.

## 0.7.0 (2026-10-28)

기능을 더하느라 도구 자신이 무거워지면 효율과 재사용이라는 목표가 흔들립니다. 그래서 이번 버전은 덜어내는 데 썼습니다.

- 훅이 도구를 쓸 때마다 붙이던 시간을 줄였습니다. 훅 경로는 명령줄 해석기, 규칙 DB 검사기, 임시 파일·암호 해시 모듈을 불러오지 않고, 정규식은 처음 쓸 때 만듭니다. 이 개발 컴퓨터(Windows)에서 전후 버전을 번갈아 25번씩 잰 중앙값으로, 훅 한 번에 Python 시작 말고 더해지는 시간이 약 165ms에서 약 115ms로 줄었습니다(약 30%). 부하가 적을 때 한 번 잰 값은 약 125ms에서 약 55ms였습니다. 컴퓨터와 부하에 따라 다릅니다.
- `init`은 기본 규칙(`base`)만 프로젝트에 옮겨 적습니다. 작업 중 경고(`work`)와 모델 배분(`task`) 규칙은 패키지에서 바로 읽고, 반응하거나 고친 규칙만 프로젝트에 남깁니다. 새 프로젝트에 깔리는 규칙은 53개에서 16개, 규칙 DB는 약 97KB에서 약 24KB, RULES.md는 약 57KB에서 약 8KB, AGENTS.md는 약 2.6KB에서 약 1.8KB가 됐습니다.
- RULES.md는 설정한 언어 한 벌로 만듭니다.
- `habitree check`가 끝에 이 프로젝트의 무게(규칙 수, AI가 매번 읽는 지침 크기)를 한 줄로 보여 줍니다. 지침이나 규칙 수가 예산을 넘으면 `rules.weight`, 오래 반응 없는 직접 규칙은 `rules.stale`로 알립니다.
- 기본 규칙 `work.cycle.trim`과 작업 순환 안내에 '쌓는 만큼 덜어낸다'를 넣었고, 방법 명세에 같은 절을 더했습니다.
- AI가 매번 읽는 분량, 세션 시작 글, 경고 한 건의 길이, 훅 경로의 모듈에 상한을 두고 시험으로 지킵니다.
- 꾸러미 규칙이 사용자가 손댄 것인지 가리는 해시가 빈 칸을 잘못 다뤄, 다시 `init`해도 새 규칙을 못 받던 문제를 고쳤습니다.

## 0.6.0 (2026-10-28)

문제를 찾는 데서 그치지 않고 어떻게 정리할지 제안하는 버전입니다. 나누기만 권하면 오히려 체계가 무거워지므로, 같은 문제라면 지우고 합치는 해법을 먼저 보여 줍니다.

- `habitree refactor`: 코드 색인을 읽어 한곳에 몰린 코드, 여러 곳의 같은 코드, 흩어진 기능, 덜어 낼 수 있는 코드를 찾고 정리 계획을 냅니다. 기본은 한 걸음씩 하는 작은 단계이고, 검증 수단이 있고 쓰는 곳이 적을 때만 큰 정리를 권하며 이유를 함께 적습니다. 단계마다 `habitree verify`로 확인하게 합니다. 코드는 고치지 않습니다.
- 기본 규칙에 몰림·중복·흩어짐 기준을 더했습니다(흩어짐과 덜어내기는 정보로만). 기준값은 규칙에 있어 반응에 따라 조정됩니다.
- 파일 커짐, 복사 코드, 잔수정 알림이 정리 계획(`habitree refactor --focus <파일>`)으로 이어집니다.
- 명세 `docs/spec/refactor.md`.

## 0.5.0 (2026-10-28)

재지 않은 숫자는 말하지 않기 위해, 실제로 어디에 토큰을 썼는지 읽고 효과를 재는 도구를 더했습니다. 둘 다 부를 때만 돕니다.

- `habitree audit`: Claude Code 세션 기록을 이 컴퓨터 안에서만 읽어 세션별·모델별 토큰과 비용, 도구 호출, 낭비 신호를 보여 줍니다. 낭비 신호는 큰 결과가 뒤의 요청마다 다시 청구되는 비용, 같은 호출과 같은 오류의 되풀이, 거듭된 정정, 비싼 모델로 한 단순 작업, 세션마다 다시 쓴 스크립트입니다. 응답 하나는 한 번만 세고, 프로젝트는 기록에 남은 작업 폴더로 가립니다. `--suggest`는 처방과 `rules hit`·`rules add` 명령 초안을 보여 줄 뿐 실행하지 않습니다.
- `habitree bench`: 규칙을 켠 갈래와 끈 갈래를 번갈아 여러 번 돌리고 검증 명령으로 채점해, 토큰·비용·시간을 평균, 표준편차, 합격률과 나란히 놓습니다. 실제 실행에는 `--yes`가 필요하고 결과 폴더는 커밋하지 않습니다. 예제 과제 두 개(Python, JavaScript).
- 명세 `docs/spec/audit.md`, `docs/spec/bench.md`, 합성 세션 기록으로 만든 시험.

## 0.4.0 (2026-10-28)

새로 만들기 전에 이미 있는 것을 먼저 찾게 하는 버전입니다.

- `habitree map`: 코드 색인. `build`(바뀐 파일만 다시 읽음), `show`(PageRank 순위, 글자 예산, `--focus`), `find`(낱말 나누기, 앞부분 일치, 한국어 두 글자 묶음, 세 단계 결과, `--json`), `dupes`, `churn`, `stats`. Python은 문법 분석으로, 스무 개 남짓한 언어는 패턴으로 뽑습니다. 언어표 375개는 scc(MIT)에서 왔습니다. 비밀 파일은 처음부터 뺍니다.
- `habitree mcp`: 표준 입출력 MCP 서버. 도구는 `map_find`, `map_show`, `rules_brief`, `check` 네 개이고, `.mcp.json` 예시가 있습니다.
- 점검 항목 `docs.stale-code`: 문서가 링크한 코드가 그 문서보다 나중에 커밋됐으면 알립니다(git이 없으면 건너뜀).
- 명세 `docs/spec/map.md`, 적합성 사례 `check/stale-code-no-git`.

## 0.3.0 (2026-10-28)

일의 종류마다 알맞은 모델에서 시작하고, 기계 검증이 실패할 때만 올라가게 하는 버전입니다.

- `habitree models`: 작업 유형별 (등급, 강도) 칸 보기와 고르기(`show`, `pick`), 실패 신호별 승격(`escalate`), 결과 기록(`record`), 기록으로 기본 칸 조정(`tune`, 올림은 바로 하고 내림은 제안만), 사람이 이유와 함께 칸 정하기(`set`), Claude Code·Codex·Aider·LiteLLM·opencode 설정 내보내기(`export`), 점검(`check`).
- `habitree verify`: 설정의 검증 명령을 셸 없이 실행합니다. 종료 코드 0이 합격이고, `--task`를 주면 결과를 기록합니다.
- 모델 대응표 `vendors.json`과 스키마(Anthropic, OpenAI, Google, 확인일 2026-10-28). 프로젝트의 `.habitree/vendors.json`으로 덮어쓸 수 있습니다.
- 규칙 꾸러미 `task`: 작업 유형별 기본 칸과, 위험한 작업과 보안 리뷰의 하한.
- 점검 항목 `models.deprecated`, `models.floor`, `models.price-stale`과 적합성 사례 `check/models-floor`. 명세 `docs/spec/models.md`.

## 0.2.0 (2026-10-28)

끝난 뒤가 아니라 일하는 도중에 알려 주는 버전입니다.

- `habitree hook <이벤트>`: Claude Code 훅 입구(SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, Stop). 훅 안에서 오류가 나도 작업은 막지 않습니다.
- 감지 규칙 14개(`work` 꾸러미, `init`이 기본으로 넣음): 같은 호출, 같은 오류, 제자리 돌기, 잔수정, 파일 커짐, 복사 코드, 큰 결과, 요청 쪼개기, 거듭된 정정, 섞인 주제, 검증 없이 끝내기, 위임. 반복 제한과 세션별 끄기가 있고, 반응(`hit`, `miss`)으로 기준이 조정됩니다.
- 위임 예외: "알아서 해 줘"나 `/habitree:delegate`로 맡기면 그 작업만 되묻지 않고 진행합니다. 경계를 기억하고, 위험한 일은 그때도 묻고, 끝에 보고합니다.
- 끝낼 때 빠른 점검: 오류가 있으면 한 번 더 일하게 합니다.
- `habitree guard`: status, explain, off·on, report, delegate.
- `habitree init --hooks`: 프로젝트 `.claude/settings.json`에 훅을 병합합니다. 사용자 전역 설정은 건드리지 않습니다.
- Claude Code 플러그인과 같은 리포의 마켓플레이스, 스킬 세 개, 명세 `docs/spec/guard.md`.

## 0.1.0 (2026-10-28)

첫 버전입니다. 피드백을 규칙으로 쌓고, 프로젝트의 지도와 문서가 실제와 맞는지 확인하는 기반을 만들었습니다.

- `habitree init`: 설정, 규칙 DB(기본 꾸러미 `base`의 규칙 12개), RULES.md, AGENTS.md·CLAUDE.md 생성 구역, README 지도 초안, LOG.md를 만듭니다. 다시 실행하면 사용자가 고치지 않은 규칙만 새것으로 바꿉니다.
- `habitree rules`: 범위·관점·상황으로 규칙을 꺼내고(`brief`, 글자 예산), 같은 뜻 규칙을 먼저 확인한 뒤 더하며(`add`), 지적을 쌓고(`hit`, `miss`), 고치고 내리고 쉬고 폐기합니다.
- `habitree check`: 지도, 링크와 한글 앵커, 갱신일, 지침 크기와 `@import`, 숨은 유니코드, 개인 경로, 규칙 DB, 규칙의 자동 검사, 생성 구역 수정, NFC·대소문자 충돌을 확인합니다. `--json`을 지원합니다.
- `habitree export`: 규칙 DB에서 AGENTS.md·CLAUDE.md 생성 구역을 다시 만들고, 사람이 고친 구역은 그대로 둡니다.
- 명세 문서, JSON Schema, 적합성 시험 6사례, Windows·macOS·Linux CI.

---

## English

Newest first.

### 0.9.0 (2026-10-28)

Measured over two sessions whether rules actually grow, as the name says, and closed the breaks in the loop found along the way. Details in [bench/2026-10-28-rules-grow.md](bench/2026-10-28-rules-grow.md).

- Adding or changing a rule with `habitree rules` now refreshes the existing generated blocks of the agent instructions (AGENTS.md, CLAUDE.md) right away. Before, `habitree export` had to be run separately, so the next session never saw the new rule. Hand-edited blocks are kept and reported.
- Detection rule `work.request.correction-to-rule`: when a message after the session's first one carries correcting words ("don't", "instead", "should use", "we decided", "already has", "no" and so on), the agent is told at that moment to record a specific rule, with a ready command and defaults so it does not have to look up how.
- Detection field `detect.now`: tell the agent right away even at info level, instead of collecting the note for the end of the reply.
- A pack rule that receives this project's feedback (`rules hit`) now appears under "rules of this project" in AGENTS.md.
- The head of RULES.md and the `feedback-to-rule` skill point straight to `rules add` without searching first; add reports a rule with the same meaning.
- Two-session measurement `bench/grow.py`, with next tasks (`grow`) for `reuse-helper` and `money-rules`.
- Two-session results: in corrected flows the Habitree side recorded a rule without being asked all 5 times and passed 5/5 next sessions; the other side was corrected 6 times and passed 0/6 next sessions.

### 0.8.0 (2026-10-28)

The first real measurement, and agent instructions trimmed according to it. Details: [bench/2026-10-28-first-measurement.md](bench/2026-10-28-first-measurement.md).

- The default agent instructions are now the trimmed version (`export.style: lean`): "look for what exists first", "record corrections as rules" and the rules this project has grown, plus the registered verify commands when there are any and a `habitree map find` hint for projects with 150 or more files. Command names stay out of the always-read instructions; how-to lives at the head of RULES.md. The six-step version is `export.style: full`.
- New projects start with zero rules. The `base`, `work` and `task` packs are all read straight from the package, and only rules you react to or edit are kept in the project.
- The session-start text uses the same trimmed version.
- The large-output note suggests locating code with `habitree map find` first, and `habitree init --mcp` adds the MCP server to the project's `.mcp.json`.
- New benchmark task `find-in-tree` (finding the place to change among folders).
- First measurement: three small tasks, Sonnet, 66 runs. On tasks with feedback rules, the Habitree side passed 29/29 and the other side 0/14. The previous instructions with generic procedure used 11 to 21% more tokens without changing accuracy.

### 0.7.0 (2026-10-28)

When a tool grows heavy from its own features, its goal of efficiency and reuse starts to wobble. This release was spent taking weight off.

- Hooks add less time to every tool call. The hook path no longer loads the argument parser, the rule DB validator or the tempfile and cryptographic hash modules, and regexes are compiled on first use. On the development machine (Windows), medians of 25 interleaved runs of the old and new versions show the time a hook adds on top of starting Python going from about 165 ms to about 115 ms (about 30%). A single run on a quieter machine showed about 125 ms to about 55 ms. Results depend on the machine and its load.
- `init` copies only the base rules into the project. The rules for in-flight warnings (`work`) and model allocation (`task`) are read straight from the package, and only rules you react to or edit are kept in the project. For a new project, installed rules went from 53 to 16, the rule DB from about 97 KB to about 24 KB, RULES.md from about 57 KB to about 8 KB and AGENTS.md from about 2.6 KB to about 1.8 KB.
- RULES.md is generated in the configured language only.
- `habitree check` ends with a line showing the project's weight (rules, size of instructions read every session). `rules.weight` warns when a budget is exceeded, and `rules.stale` notes your own rules that have gone quiet for a long time.
- The base rule `work.cycle.trim` and the work cycle text now say "trim as much as you grow", and the method spec has a section on it.
- Tests now hold limits on what the agent reads every session, the session-start text, the length of a warning and the modules loaded on the hook path.
- Fixed the hash that tells whether a pack rule was edited: it mishandled empty fields, so rerunning `init` did not deliver updated rules.

### 0.6.0 (2026-10-28)

Beyond finding problems, this release suggests how to clean them up. Advice that only says "split it" makes a structure heavier, so for the same problem the removing and merging fix comes first.

- `habitree refactor` reads the code index to find code piled up in one place, the same code in several places, scattered features and code that could simply go, and proposes a cleanup plan. The default is a small step at a time; a bold cleanup is suggested only when verification exists and few places depend on the code, with the reasons shown. Each step ends with `habitree verify`. No code is changed.
- The base rules gain thresholds for piling up, duplication and scattering (scattering and removal at info level only). The thresholds live in rules, so they adjust to feedback.
- File-growth, copied-code and small-edit warnings now point to the cleanup plan (`habitree refactor --focus <file>`).
- The spec `docs/spec/refactor.md`.

### 0.5.0 (2026-10-28)

To avoid quoting numbers we have not measured, this release adds tools that read where tokens actually went and measure the effect of the rules. Both run only when you call them.

- `habitree audit` reads Claude Code session transcripts on your own machine and shows tokens and cost per session and per model, tool calls and waste signals: large results billed again on every later request, repeated calls and errors, repeated corrections, simple work on expensive models and scripts rewritten every session. Each response is counted once, and the project is matched by the working directory recorded in the transcript. `--suggest` shows prescriptions and draft `rules hit`/`rules add` commands without running them.
- `habitree bench` alternates repeated runs with rules on and off, grades them with the verify command, and lays tokens, cost and time next to the mean, standard deviation and pass rate. Real runs need `--yes`, and results are not committed. Two example tasks (Python and JavaScript).
- Specs `docs/spec/audit.md` and `docs/spec/bench.md`, and tests built on synthetic transcripts.

### 0.4.0 (2026-10-28)

Look for what already exists before building something new.

- `habitree map`: a code index. `build` (rereads only changed files), `show` (PageRank order, character budget, `--focus`), `find` (word splitting, prefix match, Korean two-character grams, three result levels, `--json`), `dupes`, `churn` and `stats`. Python is parsed exactly; about twenty other languages are matched by patterns. The table of 375 languages comes from scc (MIT). Secret files are left out from the start.
- `habitree mcp`: a stdio MCP server with four tools (`map_find`, `map_show`, `rules_brief`, `check`) and an example `.mcp.json`.
- Check item `docs.stale-code`: notes when code linked from a doc was committed after the doc (skipped without git).
- The spec `docs/spec/map.md` and the conformance case `check/stale-code-no-git`.

### 0.3.0 (2026-10-28)

Start each kind of work on a suitable model, and move up only when machine verification fails.

- `habitree models`: show and pick the (tier, effort) cell per task type (`show`, `pick`), escalate by failure signal (`escalate`), record outcomes (`record`), tune default cells from the records (`tune`: raises apply at once, lowering is only suggested), set a cell by hand with a reason (`set`), export settings for Claude Code, Codex, Aider, LiteLLM and opencode (`export`), and check (`check`).
- `habitree verify` runs the configured verify commands without a shell. Exit 0 passes, and `--task` records the result.
- The vendor table `vendors.json` with its schema (Anthropic, OpenAI, Google; checked 2026-10-28), overridable per project with `.habitree/vendors.json`.
- The `task` rule pack: default cells per task type, with floors for risky work and security review.
- Check items `models.deprecated`, `models.floor` and `models.price-stale`, the conformance case `check/models-floor`, and the spec `docs/spec/models.md`.

### 0.2.0 (2026-10-28)

The release that speaks up during the work rather than afterwards.

- `habitree hook <event>`: the entry point for Claude Code hooks (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, Stop). Errors inside a hook never block the work.
- 14 detection rules (the `work` pack, installed by `init`): repeated calls, repeated errors, loops, small edits, growing files, copied code, large outputs, split requests, repeated corrections, mixed topics, finishing without verification, delegation. Repeats are capped, warnings can be muted per session, and votes (`hit`, `miss`) tune the thresholds.
- Delegation: hand over a task with "just do it" or `/habitree:delegate` and it proceeds without questions for that task only, remembering boundaries, still confirming risky actions, and reporting at the end.
- A quick check at Stop that sends the agent back once when errors remain.
- `habitree guard`: status, explain, off/on, report, delegate.
- `habitree init --hooks` merges the hooks into the project's `.claude/settings.json`, never the user's global settings.
- The Claude Code plugin with a marketplace in the same repository, three skills and the spec `docs/spec/guard.md`.

### 0.1.0 (2026-10-28)

The first release: the groundwork for growing feedback into rules and for checking that a project's map and docs match reality.

- `habitree init` installs settings, the rule DB (12 rules from the bundled `base` pack), RULES.md, managed blocks in AGENTS.md and CLAUDE.md, a draft README map and LOG.md. Rerunning it updates only the rules you have not edited.
- `habitree rules` pulls rules by scope, aspect and context (`brief`, with a size budget), checks for rules with the same meaning before adding one (`add`), records feedback (`hit`, `miss`), and edits, demotes, pauses or retires rules.
- `habitree check` covers the map, links and Korean heading anchors, last-updated dates, instruction size and `@import`, hidden Unicode, personal paths, the rule DB, automatic rule checks, edited managed blocks and NFC/case collisions, with `--json` output.
- `habitree export` regenerates the managed blocks in AGENTS.md and CLAUDE.md from the rule DB and keeps blocks edited by hand.
- Specification documents, JSON Schema, six conformance cases and CI on Windows, macOS and Linux.
