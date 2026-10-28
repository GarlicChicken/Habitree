# 전후 비교 측정

규칙을 쌓으면 AI가 덜 헤매고 토큰을 덜 쓸 것이라는 기대는 그럴듯하지만, 재 보기 전에는 기대일 뿐이다. `habitree bench`는 같은 과제를 Habitree 규칙을 켠 갈래와 끈 갈래로 여러 번 돌려, 토큰·비용·시간과 정답률을 나란히 보여 준다. 사람이 부를 때만 돌고, 다른 명령이나 훅에는 아무것도 더하지 않는다. 영어 본문은 [아래](#english)에 있다.

## 1. 왜 따로 재나

조사에서 지침 파일(CLAUDE.md 같은 것)의 효과를 같은 과제로 통제 실험해 공개하는 도구는 찾지 못했다. 공식 평가 기능(`claude plugin eval`)은 격리 때문에 CLAUDE.md와 `.claude/`를 아예 읽지 않는다고 문서에 적혀 있어서, 지침 파일의 전후를 그대로 잴 수 없다. 절감 수치를 내건 프로젝트들도 대개 만든 사람이 좁게 잰 숫자였다.

Habitree가 "토큰을 줄인다"고 말하려면, 그 말이 어떤 과제에서 몇 번 돌려 얼마의 편차로 나왔는지까지 함께 내놓을 수 있어야 한다. bench는 그 숫자를 만드는 도구다.

## 2. 실험 설계

**두 갈래.** 지시문과 시작 상태는 같다. with 갈래에만 `habitree init`을 하고, 과제에 적힌 규칙을 더해 지침 파일(AGENTS.md, CLAUDE.md)을 만든다. without 갈래는 아무것도 깔지 않는다.

**작업 폴더는 리포 밖에.** 실행마다 과제의 `project/`를 시스템 임시 폴더로 복사해서 돌린다. Claude Code는 위쪽 폴더의 CLAUDE.md도 읽기 때문에, 리포 안에서 돌리면 이 리포의 지침이 without 갈래에 섞인다. 채점 스크립트는 과제의 `verify/`에 두어 AI가 보거나 고칠 수 없게 한다(Aider 벤치마크는 실행 직전에 테스트 원본을 되살린다).

**반복.** 기본은 갈래마다 3번이다. `claude plugin eval`의 기본 반복 수가 3이고, 조사에서 본 비교 하네스들은 3~5번을 썼다. 순서는 갈래를 번갈아(with 1, without 1, with 2 …) 돌려 시간대나 사용량 제한의 영향이 한쪽에 몰리지 않게 한다.

**채점.** 과제의 `verify` 명령이 모두 종료 코드 0이면 합격이다. 어떤 언어와 도구에서도 지켜지는 가장 넓은 약속이 종료 코드라서다. 실행기나 채점 명령을 아예 돌리지 못한 실행(프로그램이 없음 등)은 AI의 실패가 아니므로 채점에서 빼고 따로 센다. SWE-bench가 "아예 안 돈 것"을 통과로 세지 않고 인프라 실패를 따로 나누는 것과 같은 생각이다.

**지표.** 실행기 결과에서 읽는다.

| 지표 | 읽는 곳(`claude -p --output-format json`의 결과 메시지) |
|---|---|
| 토큰 | `modelUsage`의 입력·출력·캐시 읽기·캐시 쓰기 합. 공식 문서에 따르면 `usage`는 서브에이전트를 빼고 `modelUsage`는 넣는다. `modelUsage`가 없을 때만 `usage` |
| 비용 | `total_cost_usd`. 공식 문서가 밝힌 대로 청구서가 아니라 클라이언트에서 계산한 추정 |
| 시간 | `duration_ms` |
| 턴 | `num_turns` |
| 합격률 | `verify` 결과 |

갈래마다 평균과 표본 표준편차, 합격률, 합격 한 번당 비용을 낸다. 필드 이름은 2026-10-28에 공식 TypeScript SDK 문서의 `SDKResultMessage`·`ModelUsage` 정의로 확인했다. 그래도 형식이 바뀔 수 있어 방어적으로 읽고, 받지 못한 필드는 결과에 적어 둔다.

**교차 확인.** 결과의 `session_id`로 그 실행의 세션 기록을 찾아 [audit](audit.md)과 같은 방식(응답 하나를 한 번만)으로 토큰을 다시 센다. 공식 문서는 SDK 메시지의 단계별 출력 토큰이 자리표시 값이라고 하므로, 입력과 캐시 값을 맞춰 보는 데 주로 쓴다.

**정답률을 숨기지 않는다.** 토큰이 줄었다는 숫자는 합격률 옆에서만 뜻이 있다. 규칙을 켠 갈래가 토큰을 덜 쓰고 합격률도 떨어졌다면 아낀 것이 아니라 덜 한 것일 수 있어서, 보고서는 이 경우를 따로 경고한다. 채점된 실행이 갈래마다 3번보다 적을 때, 채점에서 뺀 실행이 있을 때, 비용을 받지 못한 실행이 있을 때도 경고를 붙인다.

## 3. 실행 격리의 한계

가장 어려운 문제는 "두 갈래의 설정이 정말 같은가"다. 헤드리스 실행(`claude -p`)은 따로 막지 않으면 대화형 세션과 똑같이 사용자 전역 설정, 훅, 플러그인, MCP 서버, `~/.claude/CLAUDE.md`를 읽는다(공식 헤드리스 문서). 두 갈래에 똑같이 들어가니 공정하긴 하지만, 전역 지침에 이미 비슷한 규칙이 있으면 차이가 줄어 보인다. 조사 때 이 문제를 깔끔하게 푸는 방법을 확인하지 못했고, 지금도 세 가지 선택지와 각각의 한계를 그대로 둔다.

| `--isolation` | 하는 일 | 한계 |
|---|---|---|
| `none`(기본) | 아무것도 떼지 않는다. 전역 CLAUDE.md의 해시를 결과에 남겨 두 갈래가 같은 것을 읽었다는 것만 확인한다 | 사용자 환경이 결과에 섞인다. 다른 사람의 컴퓨터에서 같은 숫자가 나온다고 말할 수 없다 |
| `bare` | `--bare`를 붙인다. 공식 문서상 훅, 스킬, 플러그인, MCP, 자동 메모리, CLAUDE.md를 읽지 않는다 | 구독 로그인 대신 `ANTHROPIC_API_KEY`가 필요하다. CLAUDE.md도 읽지 않으므로 with 갈래는 AGENTS.md를 `--append-system-prompt-file`로 넣는다. 그래서 "지침 파일을 읽는 효과"가 아니라 "같은 글을 시스템 프롬프트에 넣은 효과"를 잰다 |
| `config-dir` | 실행마다 `CLAUDE_CONFIG_DIR`를 결과 폴더 안으로 바꾼다. 공식 문서상 설정, 세션 기록, 플러그인, 로그인 파일이 그 폴더로 간다 | 그 폴더에서 다시 로그인하거나 API 키를 써야 한다. 조직이 관리하는 설정까지 떼어지는지는 확인하지 못했다 |

`--setting-sources`에서 `user`를 빼면 `~/.claude/CLAUDE.md`도 빠지는지는 공식 문서에서 확인하지 못해 선택지로 두지 않았다.

그 밖에 알아 둘 것이 있다.

- 권한은 과제의 `allowed_tools`로 좁힌다(예: `Bash(python *)`). 작업 폴더가 임시 폴더일 뿐 샌드박스는 아니어서, 허용한 명령은 실제 컴퓨터에서 돈다.
- Windows에서 npm으로 설치한 `claude.cmd`는 인자가 cmd.exe를 거친다. 지시문에 `% ^ & | < > "`가 있으면 bench가 멈추고 네이티브 설치(`claude.exe`)를 쓰라고 알린다.
- `claude` 실행기는 실제 사용량이 든다. `--dry-run`으로 계획과 명령을 먼저 보고, 실제로 돌릴 때는 `--yes`를 붙인다. `--max-budget-usd`를 주면 실행 하나마다 한도가 걸리고, 계획에 "최대 약 얼마"가 표시된다. 공식 문서는 비용이 한도를 조금 넘을 수 있다고 적는다.

## 4. 결과를 공개할 때

결과는 `bench/results/<UTC 날짜>-<과제>/`에 쌓이고 커밋하지 않는다. 실행기 원본 출력에는 컴퓨터의 경로나 대화 글이 들어갈 수 있다.

- 공개하는 것은 사람이 읽어 본 `report.md`와 `report.json`이다. 원본 출력은 개인정보를 뺀 형태로만 옮긴다.
- 숫자에는 과제 해시, 리포 커밋, Habitree와 Claude Code 버전, 모델, 반복 수, 격리 방식을 함께 적는다. 다른 사람이 같은 조건으로 다시 돌릴 수 있어야 한다.
- 정답률과 편차를 빼고 절감률만 옮기지 않는다. 불리한 결과도 같은 자리에 둔다.
- 작은 예제 과제 한두 개의 결과를 "Habitree는 토큰을 몇 퍼센트 줄인다"로 넓히지 않는다. 과제, 언어, 모델이 늘어날 때만 말할 수 있는 범위도 넓어진다.

## 5. 과제 형식

```
<과제>/
├── task.json
├── project/     시작 상태(실행마다 임시 폴더로 복사)
└── verify/      채점 스크립트(작업 폴더 밖)
```

| 필드 | 뜻 |
|---|---|
| `prompt` | 지시문. 글 하나 또는 `{"ko", "en"}`(`lang`으로 고름) |
| `verify` | 명령 배열의 목록. 모두 종료 코드 0이면 합격. `{python}`은 지금 Python, `{task}`는 과제 폴더 |
| `timeout` | 실행 하나의 시간 한도(초, 기본 900) |
| `description` | 무엇을 보는 과제인지 |
| `rules` | with 갈래에 더할 규칙(`scope`, `aspect`, `rule`, `why`, `level` 기본 필수) |
| `allowed_tools`, `permission_mode`, `max_turns` | claude 실행기에 넘기는 값 |
| `fake` | 시험용 fake 실행기의 갈래별 출력(`outputs`)과 덮어쓸 파일 폴더(`files`) |

예제 과제는 [bench/](../../bench/README.md)에 있다.

## 6. 명령

```
habitree bench run <과제> --runner claude --dry-run
habitree bench run <과제> [--arms with,without] [--reps 3] [--runner claude|fake] [--model M]
                          [--isolation none|bare|config-dir] [--max-budget-usd 1] [--out 폴더] --yes
habitree bench report <결과 폴더> [--json]
```

`fake` 실행기는 정해 둔 출력을 돌려주는 시험용이다. 실제 AI를 부르지 않고 준비, 채점, 보고까지 한 바퀴를 확인할 수 있다.

---

## English

The hope that accumulated rules make an AI wander less and spend fewer tokens is plausible, but it stays a hope until it is measured. `habitree bench` runs the same task several times with Habitree rules on and with them off, and lays tokens, cost and time next to the pass rate. It runs only when a person calls it and adds nothing to other commands or hooks.

### 1. Why measure separately

In our research we found no tool that runs controlled experiments on instruction files (such as CLAUDE.md) with the same task and publishes the results. The official evaluation feature (`claude plugin eval`) documents that, because of isolation, it does not read CLAUDE.md or `.claude/` at all, so it cannot measure instruction files as they are. Savings figures from other projects were mostly narrow measurements by their own authors.

For Habitree to say it saves tokens, it must be able to show on which task, over how many runs and with what spread the number came out. bench is the tool that produces that number.

### 2. Experiment design

**Two arms.** The prompt and the starting state are identical. Only the "with" arm gets `habitree init`, the task's rules and the generated instruction files (AGENTS.md, CLAUDE.md). The "without" arm gets nothing.

**Work outside the repository.** Each run copies the task's `project/` into a system temporary folder. Claude Code also reads CLAUDE.md files in parent folders, so running inside the repository would leak this repository's instructions into the "without" arm. Graders live in the task's `verify/` folder, where the agent cannot see or change them (Aider's benchmark restores original tests right before each run).

**Repetitions.** The default is three runs per arm. Three is the default of `claude plugin eval`, and the comparison harnesses we reviewed used three to five. Arms are interleaved (with 1, without 1, with 2, …) so that time of day or rate limits do not pile up on one side.

**Grading.** A run passes when every `verify` command exits with 0, the broadest contract every language and tool keeps. A run where the runner or a grader could not start at all (a missing program, for example) is not the agent's failure, so it is left out of scoring and counted separately, the same idea as SWE-bench refusing to count "never ran" as a pass and separating infrastructure failures.

**Metrics** come from the runner's result message (`claude -p --output-format json`): tokens are the sum of input, output, cache reads and cache writes in `modelUsage` (the official docs say `usage` excludes subagents and `modelUsage` includes them; `usage` is used only when `modelUsage` is missing), cost is `total_cost_usd` (a client-side estimate, not a bill, as the docs state), time is `duration_ms`, turns is `num_turns`, and the pass rate comes from `verify`. Each arm reports the mean and sample standard deviation, the pass rate and the cost per passing run. Field names were checked on 2026-10-28 against the `SDKResultMessage` and `ModelUsage` definitions in the official TypeScript SDK reference. The parser still reads defensively and records any field it did not receive.

**Cross-check.** The result's `session_id` locates the run's transcript, and tokens are recounted the way [audit](audit.md) does it (each response once). The docs say per-step output tokens in SDK messages are placeholders, so the cross-check is mainly for input and cache values.

**The pass rate is never hidden.** Fewer tokens mean something only next to the pass rate. If the "with" arm used fewer tokens and also passed less often, it may have done less rather than saved, and the report warns about exactly that case. It also warns when an arm has fewer than three scored runs, when some runs were not scored, and when some runs reported no cost.

### 3. Limits of isolation

The hardest question is whether both arms really run with the same setup. Unless told otherwise, headless runs (`claude -p`) load global settings, hooks, plugins, MCP servers and `~/.claude/CLAUDE.md` just like an interactive session (official headless docs). Both arms get the same thing, which is fair, but if the global instructions already contain similar rules the difference looks smaller. We did not find a clean fix during research, so bench keeps three options with their limits stated plainly:

- `none` (default): nothing is removed. A hash of the global CLAUDE.md is recorded to show both arms read the same file. The user's environment is mixed into the result, so we cannot claim the same numbers on another machine.
- `bare`: adds `--bare`, which per the official docs skips hooks, skills, plugins, MCP, auto memory and CLAUDE.md. It needs `ANTHROPIC_API_KEY` instead of a subscription login. Because CLAUDE.md is skipped too, the "with" arm receives AGENTS.md through `--append-system-prompt-file`, so this measures the same text as a system prompt addition rather than the effect of reading an instruction file.
- `config-dir`: points `CLAUDE_CONFIG_DIR` into the results folder for each run. Per the official docs, settings, session history, plugins and the login file move there, so you must log in again there or use an API key. Whether organization-managed settings are removed as well was not confirmed.

Whether leaving `user` out of `--setting-sources` also drops `~/.claude/CLAUDE.md` could not be confirmed in the official docs, so it is not offered.

Also worth knowing: permissions are narrowed with the task's `allowed_tools` (for example `Bash(python *)`); the work folder is only a temporary copy, not a sandbox, so allowed commands run on the real machine. On Windows, the npm-installed `claude.cmd` passes arguments through cmd.exe, so bench stops when a prompt contains `% ^ & | < > "` and suggests the native `claude.exe`. The `claude` runner uses real usage: check the plan with `--dry-run` first and add `--yes` to run it. `--max-budget-usd` caps each run and the plan shows the maximum total; the official docs note spend can slightly exceed the cap.

### 4. Publishing results

Results collect in `bench/results/<UTC date>-<task>/` and are not committed, because raw runner output can contain local paths or conversation text. Publish the `report.md` and `report.json` a person has read, and move raw output only with personal data removed. State the task hash, repository commit, Habitree and Claude Code versions, model, repetitions and isolation next to every number so others can rerun under the same conditions. Never quote a savings figure without its pass rate and spread, and keep unfavorable results in the same place. Do not stretch one or two small example tasks into "Habitree cuts tokens by N%"; the claim can only widen as tasks, languages and models are added.

### 5. Task format

A task folder holds `task.json`, `project/` (the starting state, copied to a temporary folder for each run) and `verify/` (graders outside the work folder). The fields of `task.json` are listed in the Korean table above: `prompt`, `verify`, `timeout`, `description`, `rules`, the claude runner values `allowed_tools`, `permission_mode` and `max_turns`, and `fake` for the test runner. Example tasks live in [bench/](../../bench/README.md).

### 6. Commands

The command block in the Korean section shows `bench run` with its options and `bench report`. The `fake` runner returns predefined output for tests, so setup, grading and reporting can be checked end to end without calling a real AI.
