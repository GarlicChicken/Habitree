# 바뀐 것

새 버전을 위에 씁니다.

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
