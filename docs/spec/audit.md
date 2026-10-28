# 세션 기록 분석

Habitree는 "재지 않은 숫자는 말하지 않는다"를 원칙으로 둔다. 토큰이 어디로 새는지 말하려면 먼저 실제로 쓴 기록을 읽어야 한다. `habitree audit`은 AI 코딩 도구가 남긴 세션 기록을 읽어 토큰과 비용, 도구 호출, 그리고 돈이 많이 새는 몇 가지 버릇을 보여 준다. 사람이 부를 때만 돌고, 훅이나 `habitree check`처럼 자주 도는 길에는 들어가지 않는다. 영어 본문은 [아래](#english)에 있다.

## 1. 왜 기록을 읽나

"얼마나 썼나"를 세는 도구는 이미 많고 잘 만들어져 있다(ccusage가 사실상 표준이다). 모자란 것은 그다음이다. 무엇 때문에 썼는지, 무엇을 고치면 되는지, 그리고 그 고침을 다음 세션까지 가져가는 길이다. Habitree에는 규칙 DB와 규칙 사다리가 있으니, audit은 기록에서 찾은 낭비를 처방과 규칙 후보로 바꿔 사다리의 입구에 올려놓는 데까지 간다.

그래서 audit은 많은 것을 재지 않는다. 근거가 분명하고 비용이 큰 것만 본다. 보고서도 기본은 몇 줄이고, 자세한 것은 `--detail`과 `--json`에 있다.

## 2. 무엇을 어떻게 세나

### 이 프로젝트의 세션만

Claude Code는 기록을 `~/.claude/projects/<프로젝트>/<세션 ID>.jsonl`에 둔다(`CLAUDE_CONFIG_DIR`가 있으면 그 폴더). `<프로젝트>`는 작업 폴더 경로에서 영문자와 숫자가 아닌 글자를 모두 `-`로 바꾼 이름이다(공식 문서 sessions.md). 이 바꾸기는 되돌릴 수 없다. 한글은 글자마다 `-` 하나가 되고, macOS가 자모로 풀어 쓴(NFD) 경로는 자모마다 `-` 하나가 된다. 그래서 `C:\work\한글 프로젝트`와 `C:\work\다른 프로젝트`는 같은 폴더 이름이 된다.

audit은 폴더 이름으로 후보만 고르고, 이 프로젝트의 세션인지는 기록 안의 작업 폴더(`cwd`)로 정한다. 경로는 Windows와 POSIX 표기를 모두 받아 NFC로 맞춰 비교한다.

### 중복 함정

기록을 그냥 더하면 틀린다. Claude Code는 응답 하나를 내용 블록마다 한 줄씩 쓰고, 그 줄들에 같은 사용량을 되풀이해 적는다. 입력과 캐시 값은 같고 출력만 뒤 줄로 갈수록 커진다. 2026-10-28에 이 PC의 한 프로젝트 기록으로 재 보니, 줄을 그냥 더하면 입력은 2.27배, 캐시 읽기는 2.24배, 캐시 쓰기는 2.26배로 부풀었고, 같은 응답의 첫 줄만 쓰면 출력이 마지막 줄 값의 29%로 줄었다. 줄마다 다른 `uuid`를 열쇠로 쓰면 아무것도 묶이지 않는다. 검토한 도구 여럿이 이 가운데 하나에 걸려 있었다.

audit은 이렇게 센다.

- `assistant` 줄만 보고, `(message.id, requestId)`가 같은 줄을 응답 하나로 묶는다. 칸마다 가장 큰 값을 남긴다. ccusage, tokscale, Harbor가 모인 방식이다.
- 도구 호출은 `tool_use.id` 하나에 한 번이다. `api-request-blob` 줄에 든 `tool_use`는 같은 호출의 사본이라 세지 않는다.
- 같은 `uuid`가 다시 붙은 줄(편집기를 다시 열 때 생긴다는 보고, claude-code #56196)은 한 번만 읽는다.
- 서브에이전트 기록(`<세션 ID>/subagents/agent-<id>.jsonl`)은 본 세션에 합치되 맥락은 따로 둔다.

공식 Agent SDK 비용 문서도 "한 차례에 여러 도구를 부르면 메시지들이 같은 ID를 공유하니 ID로 중복을 거르라"고 적는다. 같은 문서는 SDK가 흘려보내는 메시지의 단계별 `output_tokens`가 응답이 시작될 때의 자리표시 값이라고도 밝힌다. 기록 파일에서는 출력이 뒤 줄로 갈수록 커지고 마지막 줄이 가장 크다는 것을 확인했지만, 그 값이 최종 청구 값과 같은지는 공식으로 확인하지 못했다. 그래서 출력 토큰은 "기록이 말하는 최댓값"으로 읽고, bench는 실행 결과 메시지의 값을 기준으로 삼는다.

### 모르는 형식

기록의 줄 구조는 공식 계약이 아니다. 형식을 문서로 정해 달라는 요청(claude-code #53516)은 계획 없음으로 닫혔고, 실제로 줄 종류가 계속 늘어 왔다. audit은 아는 종류만 읽고, 쓰지 않는 종류는 조용히 넘기고, 처음 보는 종류는 개수를 세어 알린다. 그 알림이 보이면 형식이 바뀌었을 수 있으니 숫자를 조심해서 본다. 시험에는 실제 형식을 본뜬 합성 기록(중복 줄, 처음 보는 줄, 깨진 줄, 한글 경로, Windows와 POSIX 경로)을 두어 회귀를 막는다.

### 비용

토큰에 [모델 대응표](models.md#5-모델-관리)의 단가를 곱한다. 요청마다 그날 효력이 있는 가격을 쓰고, 캐시 쓰기는 5분과 1시간 단가를 나누고, 프롬프트가 구간을 넘으면 그 구간 단가를 쓴다. 가격을 모르는 모델은 0원이 아니라 "모름"으로 남기고 합계에서 뺀다는 것을 함께 적는다. 웹 검색 같은 요청당 요금과 지역 처리 가산은 넣지 않았다. 공식 문서도 SDK가 내는 비용이 청구서가 아닌 추정이라고 적고, audit의 비용도 같은 뜻의 추정이다.

## 3. 낭비 신호

| 신호 | 보는 것 | 기준 | 근거 |
|---|---|---|---|
| `big_output` | 큰 도구 결과가 대화에 남아 뒤의 요청마다 다시 청구되는 비용 | 결과 2만 자 이상, 또는 1,000줄 넘는 파일을 범위 없이 읽음 | keel의 FLOOD 기준 2만 자. SWE-agent 실험에서 파일 전체를 보여 주면 100줄 창보다 해결률이 낮았다(12.7%, 18.0%) |
| `same_call_streak` | 같은 도구를 같은 입력으로 연속 호출 | 3번 | Cline 3번 경고·5번 멈춤, Kilo Code·OpenCode 3번, Gemini CLI 5번(소스 코드로 확인) |
| `same_error_streak` | 같은 도구가 같은 오류로, 그 도구의 성공 없이 되풀이 | 3번 | OpenHands, keel, claudewatch 모두 3번 |
| `repeat_correction` | 한 세션 안에서 사람이 AI를 거듭 바로잡음 | 2번(200자 이하 글) | Claude Code 모범 사례: 두 번 실패한 정정 뒤에는 새 대화. 판정 구조는 agentsview(짧은 사용자 응답 + 정정 표지) |
| `expensive_simple` | 상·최상 등급 모델로 돈 서브에이전트가 읽기·검색만 함 | 쓰기 없는 서브에이전트 | Claude Code 비용 문서: 단순한 서브에이전트 작업은 작은 모델. E 조사 4-4의 판정 초안(추정) |
| `rewritten_script` | 비슷한 스크립트를 다른 세션에서 또 새로 씀(정보) | 낱말 3개 묶음 자카드 0.65 이상, 낱말 50개 이상 | cctx가 서브에이전트 지시문 비교에 쓴 값을 빌렸다. 스크립트에 맞는지는 우리 제안이다 |

`big_output`이 가장 비싸다. 결과가 컨텍스트에 들어가면 그 뒤 모든 요청이 캐시 읽기로 그 값을 다시 치른다(캐시 쓰기 1번 + 남은 요청 수만큼 캐시 읽기). claude-context-optimizer는 자기 기록을 보고 "바뀌지 않은 파일 반복 읽기는 드물었고, 긴 Opus 세션 비용의 약 60%는 캐시 읽기였다"고 적었다. 그 프로젝트가 스스로 밝힌 관찰이고, 우리가 audit의 첫 신호를 이것으로 둔 이유다. 결과의 토큰 수는 다음 요청의 프롬프트가 얼마나 늘었는지로 잰다(같은 요청이 부른 다른 도구가 있으면 글자 수 비율로 나눈다). 다음 요청이 없을 때만 글자 수 ÷ 4로 추정하고 "추정"이라고 표시한다. 이 나눗셈은 영어 기준이라 한국어가 많으면 맞지 않을 수 있다.

`expensive_simple`의 "줄일 수 있었던 비용"은 같은 토큰을 `task/explore` 칸 모델의 단가로 다시 매긴 값이다. 작은 모델은 토큰을 다르게 쓸 수 있으니 이 값은 방향을 보여 주는 추정이다. 실제로 칸을 바꿀지는 [models](models.md)의 기록과 검증으로 정한다.

정정 표지(한국어·영어)와 셸 읽기 명령, 도구 범주는 코드가 아니라 [data/sessions.json](../../src/habitree/data/sessions.json)에 있다. 다른 언어나 셸을 다루려면 그 표에 줄을 더하면 된다.

기준값은 규칙 DB를 따른다. 같은 `detect.signal`을 가진 감지 규칙에 `threshold`가 있으면 audit도 그 값을 쓴다. `habitree rules miss`로 기준이 완화되면 audit도 함께 느슨해진다.

넣지 않은 신호도 있다. 같은 파일 잔수정, 덧대기로 커지는 파일, 복사한 코드, 요청 쪼개 보내기는 조사에서 근거가 약하거나 정보 등급으로 시작하라고 한 것들이다. 작업 중 경고(v0.2 guard)가 다루고, audit은 가볍게 둔다.

## 4. 신호에서 규칙까지

`--suggest`는 신호를 종류별로 묶어, 여러 세션에서 되풀이된 것부터 보여 준다. 사람의 지적을 모아 둔 도구가 실제로 겪은 일이 근거다. claude-reflect는 한 사용자의 후보 102개 가운데 다시 쓸 규칙이 약 20%뿐이었고, 같은 규칙이 넉 달 동안 표현만 바꿔 네 번 나왔는데 후보 더미에 묻혔다고 적었다. 반복된 것이 먼저 보여야 묻히지 않는다.

신호마다 처방은 고정된 문장이다(모델에게 묻지 않는다). 규칙 DB에서 이어 붙일 규칙은 이 순서로 찾는다.

1. `detect.signal`이 같은 감지 규칙
2. 이 신호와 묶어 둔 기본 규칙(예: 거듭된 정정은 `work.cycle.feedback-to-rule`)
3. 같은 뜻으로 보이는 규칙. 모델 칸 규칙은 빼는데, hit하면 권장이 필수가 되어 칸이 하한으로 굳어 버리기 때문이다

찾으면 `habitree rules hit <id> --feedback "…"`를, 못 찾으면 `habitree rules add …` 초안을 보여 준다. 범위가 규칙 DB에 없으면 가장 가까운 상위 범위로 바꾼다. 명령은 보여 주기만 하고 실행하지 않는다. 고칠지는 사람이 정한다.

Claude Code 자동 메모리에 `feedback` 유형 메모가 있으면 "규칙 후보 받은편지함"으로 함께 보여 준다. 정정을 잡아내는 일은 이미 자동 메모리가 하니 감지기를 새로 만들지 않고, 그 메모를 규칙으로 올리는 길만 놓았다. 메모는 이름과 한 줄 설명만 보여 주고, 본문은 읽어 옮기지 않으며, 어디에도 저장하지 않는다.

## 5. 개인정보

세션 기록에는 코드, 경로, 대화가 들어 있다.

- 기록은 이 컴퓨터 안에서만 읽는다. 어디에도 보내지 않고, 리포에 저장하지 않는다.
- 보고서(화면, JSON)에는 개수, 토큰, 도구 이름, 해시, 프로젝트 안의 상대 경로만 넣는다. 프로젝트 밖의 경로는 파일 이름만 남긴다. 사람이 친 글, 도구 입력, 도구 결과는 판정할 때 메모리에서만 쓴다. 정정 신호에는 걸린 표지(우리 목록의 낱말)만 적는다.
- 시각은 UTC로 저장하고 화면에서는 그 컴퓨터의 시간대로 보여 준다.
- Claude Code는 기본으로 30일이 지난 기록을 지운다(`cleanupPeriodDays`). 오래된 세션이 안 보이는 것은 그 때문이다.

## 6. 명령

```
habitree audit                       최근 10개 세션 요약
habitree audit --last 3 | --since 2026-10-01 | --session 0cb25a02
habitree audit --detail              세션별·모델별·신호별 자세히
habitree audit --suggest             처방, 규칙 명령 초안, 자동 메모리 받은편지함
habitree audit --json                전부(시각은 UTC)
habitree audit --claude-dir <폴더>   기록 위치를 직접 줄 때
```

## 7. 다른 도구

읽는 일은 도구마다 어댑터 하나가 맡고(`src/habitree/sessions/`), 판정은 공통 레코드 위에서 한다. 지금은 Claude Code만 읽는다. Codex CLI는 자리만 있다(`--tool codex`). 조사에서 형식을 다른 도구의 소스로만 봤고 공식 스키마 문서를 찾지 못해서다. 확인된 형식이 생기면 어댑터를 채운다.

---

## English

Habitree keeps one rule: no numbers we have not measured. To say where tokens go, we first have to read what was actually spent. `habitree audit` reads the session transcripts an AI coding tool leaves behind and shows tokens, cost, tool calls and a few habits that leak the most money. It runs only when a person calls it; nothing is added to hooks or to `habitree check`.

### 1. Why read transcripts

Tools that count "how much" already exist and are good (ccusage is the de facto standard). What is missing comes after: why the tokens were spent, what to change, and how to carry that change into the next session. Habitree has a rule DB and a rule ladder, so audit goes one step further and turns waste found in transcripts into a prescription and a rule candidate at the bottom of the ladder.

So audit measures few things: only signals with clear evidence and real cost. The default report is a few lines; details live in `--detail` and `--json`.

### 2. What is counted, and how

**Only this project's sessions.** Claude Code stores transcripts at `~/.claude/projects/<project>/<session-id>.jsonl` (or under `CLAUDE_CONFIG_DIR`). `<project>` is the working directory with every non-alphanumeric character replaced by `-` (official sessions docs). That mapping cannot be reversed: each Korean syllable becomes one `-`, and a path macOS stored decomposed (NFD) becomes one `-` per jamo, so `C:\work\한글 프로젝트` and `C:\work\다른 프로젝트` share a folder name. Audit uses folder names only to pick candidates and decides membership by the working directory (`cwd`) recorded inside. Windows and POSIX paths are both accepted and compared in NFC.

**The duplication trap.** Summing lines is wrong. Claude Code writes one line per content block of a response and repeats the same usage on each; input and cache values are identical and only output grows on later lines. Measured on 2026-10-28 on one project's transcripts on this machine, a plain sum inflated input 2.27x, cache reads 2.24x and cache writes 2.26x, while keeping only the first line cut output to 29% of the last line's value. `uuid` differs on every line, so it groups nothing. Several reviewed tools fall into one of these traps.

Audit counts as follows:

- Only `assistant` lines, grouped by `(message.id, requestId)` into one response, keeping the largest value per field (the approach ccusage, tokscale and Harbor converged on).
- One tool call per `tool_use.id`; `tool_use` blocks inside `api-request-blob` lines are copies and are skipped.
- A line re-appended with the same `uuid` (reported in claude-code #56196) is read once.
- Subagent transcripts (`<session-id>/subagents/agent-<id>.jsonl`) join their session but keep their own context.

The official Agent SDK cost docs also say that messages from one turn with several tool calls share an ID and should be deduplicated by it. The same docs state that per-step `output_tokens` in the SDK message stream is a placeholder taken when the response starts. In transcript files we saw output grow line by line with the last line largest, but we could not confirm officially that this equals the billed value. Output tokens are therefore read as "the largest value the transcript reports", and bench uses the run's result message as its reference.

**Unknown formats.** The line structure is not a public contract: the request to document it (claude-code #53516) was closed as not planned, and record types keep being added. Audit reads the types it knows, skips the ones it does not use, and counts and reports any type it has never seen. When that notice appears, the format may have changed and the numbers deserve care. Tests use synthetic transcripts modeled on the real format (duplicate lines, unknown and broken lines, Korean paths, Windows and POSIX paths) to catch regressions.

**Cost.** Tokens are multiplied by prices from the [vendor table](models.md#5-모델-관리), using the price in effect on each request's date, separate 5-minute and 1-hour cache-write prices, and prompt-size bands. A model without a price is reported as unknown rather than free and is left out of the total, with a note saying so. Per-request fees such as web search and regional surcharges are not included. The official docs call the SDK's cost figures estimates, not bills; audit's costs are estimates in the same sense.

### 3. Waste signals

| Signal | What it looks at | Threshold | Basis |
|---|---|---|---|
| `big_output` | A large tool result that stays in context and is billed again on every later request | Result of 20,000+ characters, or a 1,000+ line file read without a range | keel's FLOOD threshold of 20,000 characters; in SWE-agent experiments, showing whole files solved fewer tasks than a 100-line window (12.7% vs 18.0%) |
| `same_call_streak` | The same tool called with the same input in a row | 3 | Cline warns at 3 and stops at 5, Kilo Code and OpenCode use 3, Gemini CLI 5 (checked in source) |
| `same_error_streak` | The same tool failing with the same error, with no success of that tool in between | 3 | OpenHands, keel and claudewatch all use 3 |
| `repeat_correction` | A person correcting the AI repeatedly in one session | 2 (messages of 200 characters or less) | Claude Code best practices: after two failed corrections, start a fresh conversation. Detection follows agentsview (short reply plus correction markers) |
| `expensive_simple` | A subagent on a high or top tier model that only read and searched | A subagent with no writes | Claude Code cost docs: simple subagent work suits a small model; the draft rule in our model-allocation research, section 4-4 (an estimate) |
| `rewritten_script` | A similar script written from scratch again in another session (info) | Jaccard of 3-token shingles 0.65 or more, at least 50 tokens | Borrowed from the value cctx uses to compare subagent prompts; whether it suits scripts is our proposal |

`big_output` is the most expensive. Once a result enters the context, every later request pays for it again as cache reads (one cache write plus one cache read per remaining request). claude-context-optimizer wrote, from its own transcripts, that rereading unchanged files was rare and that about 60% of the cost of long Opus sessions was cache reads. That is the project's own observation, and it is why audit leads with this signal. A result's token count is measured from how much the next request's prompt grew (split by character share when the same request called other tools). Only when there is no next request is it estimated as characters ÷ 4 and marked as an estimate; that ratio is English-based and can be off for Korean text.

For `expensive_simple`, "could have saved" reprices the same tokens at the price of the `task/explore` cell model. A smaller model may use a different number of tokens, so this is a directional estimate. Whether to change the cell is decided through the records and verification in [models](models.md).

Correction markers (Korean and English), read-only shell commands and tool categories live in [data/sessions.json](../../src/habitree/data/sessions.json), not in code. Supporting another language or shell means adding a row there.

Thresholds follow the rule DB: if a detection rule with the same `detect.signal` has a `threshold`, audit uses it, so when `habitree rules miss` relaxes a threshold, audit relaxes with it.

Some signals were left out on purpose. Many small edits to one file, files growing by patches, copied code and requests split into pieces were rated weak or info-only in our research. The in-flight warnings (v0.2 guard) cover them, and audit stays light.

### 4. From signals to rules

`--suggest` groups hits by signal and lists the ones repeated across the most sessions first. The reason comes from a tool that collected human corrections: claude-reflect reported that only about 20% of one user's 102 candidates were reusable rules, and that one rule came back four times over four months in different words, buried in the queue. Repeated items have to come first or they get buried.

Each signal has a fixed prescription (no model is asked). The rule to attach is found in this order:

1. A detection rule with the same `detect.signal`
2. A base rule linked to the signal (for example, repeated corrections link to `work.cycle.feedback-to-rule`)
3. A rule that looks the same in meaning. Model cell rules are skipped, because a hit would turn a should rule into a must rule and freeze the cell as a floor

When a rule is found, audit shows `habitree rules hit <id> --feedback "…"`; otherwise it shows a `habitree rules add …` draft, moving the scope up to the nearest scope that exists in the rule DB. Commands are shown, never run. A person decides.

If Claude Code's auto memory holds `feedback` notes, they appear as a rule candidate inbox. Auto memory already captures corrections, so we did not build another detector; we only added a path from those notes to rules. Only a note's name and one-line description are shown; bodies are not copied and nothing is saved.

### 5. Privacy

Transcripts contain code, paths and conversations.

- They are read only on this computer, never sent anywhere and never stored in the repository.
- Reports (screen and JSON) contain counts, tokens, tool names, hashes and paths relative to the project; paths outside the project keep only the file name. Text people typed, tool inputs and tool output are used in memory for detection only. Correction hits record only which markers from our list matched.
- Times are stored in UTC and shown in the computer's local time zone.
- Claude Code deletes transcripts older than 30 days by default (`cleanupPeriodDays`), which is why old sessions disappear.

### 6. Commands

The command block in the Korean section above lists every option: a short summary by default, `--detail` for a full breakdown, `--suggest` for prescriptions, rule command drafts and the memory inbox, `--json` for everything with UTC times, and `--claude-dir` to point at a different transcript location.

### 7. Other tools

Each tool gets one adapter (`src/habitree/sessions/`), and detection runs on common records. Only Claude Code is read today. Codex CLI has a placeholder (`--tool codex`) because we only saw its format through other tools' source code and found no official schema; the adapter will be filled in once the format is confirmed.
