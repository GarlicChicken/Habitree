# Habitree

AI와 코딩할 때 토큰은 줄이고 재사용은 늘리도록 돕는 도구입니다. 피드백은 규칙으로, 반복은 모듈로 자라게 합니다.

- 마지막 갱신: 2026-10-28
- 상태: v0.3 알파
- 라이선스: [MIT](LICENSE)
- [English](#english)

## 왜 만들었나

AI에게 코딩을 맡기다 보면 같은 말을 여러 번 하게 됩니다. 지난주에 고쳐 달라고 한 버릇이 이번 주에 또 나오고, 이미 있는 함수를 모른 채 비슷한 함수를 새로 만들고, 같은 파일을 몇 번이고 다시 읽습니다. 그때마다 시간과 토큰이 샙니다.

이를 돕는 도구는 이미 많습니다. 다만 대부분은 지침 파일(CLAUDE.md 같은 것)에 한 줄을 덧붙이는 데서 끝납니다. 줄이 쌓일수록 파일은 커지고, AI는 매번 그 파일 전체를 읽습니다. 고치려던 낭비가 다른 모습으로 돌아오는 셈입니다.

Habitree는 피드백을 글이 아니라 구조로 쌓습니다. 규칙마다 범위(무엇에 대한 것인지), 관점, 상황이 붙어 있고, 지금 하는 작업에 맞는 범위의 규칙만 꺼내 읽게 합니다. 같은 지적이 다시 나오면 그 규칙이 단단해지고, 기계로 확인할 수 있는 것은 자동 검사로 옮겨 갑니다.

```
말로 한 피드백 → 권장 규칙 → 필수 규칙 → 자동 검사 → 코드에서 막기
```

목표는 하나입니다. 같은 피드백을 두 번 하지 않게 하는 것.

## 하는 일

- **규칙 DB:** 피드백을 범위 트리에 규칙으로 쌓고, 작업 전에 필요한 규칙만 정해진 분량 안에서 꺼냅니다. 새 규칙을 더하기 전에 같은 뜻의 규칙이 이미 있는지 먼저 찾아 줍니다.
- **점검:** 지도(README)와 실제 폴더, 문서 링크, 규칙 DB가 서로 맞는지 AI 없이 확인합니다. 매번 같은 결과가 나오니 CI나 훅에 그대로 붙일 수 있습니다.
- **지침 파일 생성:** 규칙에서 AGENTS.md와 CLAUDE.md를 만들어 냅니다. Codex, Cursor, Copilot, Gemini CLI, Claude Code가 같은 원본을 읽습니다. 사람이 쓴 부분은 건드리지 않습니다.

## 설치

Python 3.9 이상에서 돌아가고, 바깥 패키지에 의존하지 않습니다. [uv](https://docs.astral.sh/uv/)로 설치하면 컴퓨터에 Python이 없어도 uv가 알아서 준비합니다.

```
uv tool install git+https://github.com/GarlicChicken/habitree
# 또는
pipx install git+https://github.com/GarlicChicken/habitree
```

설치하면 `habitree` 명령과 짧은 별칭 `ht`가 생깁니다.

## 빠른 시작

```
cd 내-프로젝트
habitree init                 # 뼈대 깔기
habitree check                # 지도·문서·규칙 점검
habitree rules brief global   # 작업 전에 읽을 규칙
```

Claude Code를 쓴다면 플러그인도 함께 설치하세요. 작업 도중에 경고를 보내는 훅과 스킬이 들어옵니다.

```
claude plugin marketplace add GarlicChicken/habitree
claude plugin install habitree@habitree
```

플러그인 없이 훅만 프로젝트에 연결하려면 `habitree init --hooks`를 쓰면 됩니다.

`init`은 아래 파일을 만듭니다. 이미 있는 파일에서 사람이 쓴 내용은 지우지 않고, 나중에 다시 실행하면 새로 생긴 기본 규칙만 더합니다.

| 파일 | 하는 일 |
|---|---|
| `.habitree/config.json` | 설정: 언어, 검증 명령 등 |
| `.habitree/rules.json`, `.habitree/RULES.md` | 규칙 DB와 사람이 읽는 규칙 문서 |
| `AGENTS.md`, `CLAUDE.md` | AI 도구가 읽는 지침. 표시된 생성 구역만 고칩니다 |
| `README.md`의 지도 | 최상위 폴더 지도 초안 |
| `LOG.md` | 변경 기록과 '손볼 것' |

## 피드백을 규칙으로

AI에게 같은 지적을 하게 되면, 고치는 것과 함께 규칙으로 남깁니다. AGENTS.md에 방법이 적혀 있어서 대개는 AI가 직접 기록합니다.

```
habitree rules add --scope work --aspect process \
  --rule "커밋 메시지는 한국어로 쓴다" --why "팀 규칙" --feedback "영어로 썼음"
habitree rules hit <id> --feedback "또 영어로 씀"      # 같은 지적: 권장 → 필수
habitree rules miss <id> --feedback "이번엔 틀린 경고"  # 규칙이나 경고가 틀렸을 때
habitree rules similar "커밋 메시지 언어"               # 같은 뜻 규칙 찾기
```

규칙은 범위 트리(`work` → `work/cycle`)에 놓이고, 아래 범위는 위 범위의 규칙을 물려받습니다. 사람의 피드백은 빠르게 올라가고, 내릴 때는 사람이 이유를 적어야 합니다(`demote`). 같은 뜻의 규칙이 둘로 갈라지면 지적 횟수가 흩어지기 때문에, `add`는 비슷한 규칙이 보이면 먼저 멈추고 알려 줍니다.

## 점검

`habitree check`는 정해진 방식으로만 확인합니다. 오류가 있으면 종료 코드 1을 돌려주고, `--json`으로 기계가 읽을 결과도 냅니다.

| 점검 | 찾는 것 |
|---|---|
| `map.*` | 지도에 없는 폴더, README가 없는 폴더 |
| `docs.link` | 깨진 상대 링크와 제목 앵커(한글 앵커 포함) |
| `docs.updated`, `docs.log` | '마지막 갱신' 날짜, 변경 기록 |
| `docs.instructions-size`, `docs.import` | AGENTS.md 32KiB 한도, CLAUDE.md 길이, `@import` 대상 |
| `docs.hidden-unicode`, `docs.home-path` | 보이지 않는 제어 문자, 박혀 있는 개인 폴더 경로 |
| `rules.*` | 규칙 DB 형식, RULES.md 동기화, 같은 뜻 규칙, 자동 검사 |
| `generated.edited` | 생성 구역을 사람이 직접 고친 곳 |
| `paths.collision` | 대소문자나 NFC·NFD만 다른 파일 이름 |

규칙에 `check.run`을 적어 두면 사다리의 '자동 검사' 칸이 실제로 돌아갑니다. 명령(종료 코드 0이면 합격), 금지할 형식, 있어야 할 형식, 줄 수 한도 중에서 고를 수 있습니다. 프로젝트가 어떤 언어로 짜여 있든 똑같이 쓸 수 있습니다. 전체 목록은 [docs/spec/check.md](docs/spec/check.md)에 있습니다.

## 일하는 도중에 알려 주기

낭비는 대개 끝난 뒤에야 보입니다. 같은 명령을 다섯 번 돌렸고, 같은 오류에 같은 수정을 되풀이했고, 파일 하나가 덧붙이기만으로 두 배가 됐다는 사실을 세션 기록을 읽고 나서야 알게 됩니다.

Habitree는 이것을 일하는 도중에 알려 줍니다. 같은 명령을 세 번째 돌리거나, 같은 오류에 같은 수정을 되풀이하거나, 파일 하나를 덧붙이기만으로 키우고 있으면 그 자리에서 AI에게 한 줄을 건네 방향을 바꾸게 합니다. 그래도 계속되면 멈추고 사람에게 묻습니다. 감지는 도구 호출과 파일 변화 같은 행동만 보기 때문에 어떤 언어로 짠 프로젝트에도 똑같이 통합니다.

경고도 규칙 DB의 규칙입니다. "이 경고 맞았어", "잔소리야" 같은 반응(`rules hit`, `rules miss`)이 쌓여 기준이 조정되고, 같은 경고는 반복 횟수를 제한하며, 세션 단위로 끌 수도 있습니다(`habitree guard off <id>`).

"알아서 해 줘"라고 맡기면 그 작업에 한해서는 되묻지 않고 추천안대로 진행합니다. 다만 지우기, 배포, 외부로 보내기, 결제, 개인정보처럼 되돌리기 어려운 일은 그때도 묻고, 끝에 대신 정한 것과 미뤄 둔 경고를 모아 보고합니다. 자세한 것은 [docs/spec/guard.md](docs/spec/guard.md)에 있습니다.

## 일마다 알맞은 모델

AI에게 일을 맡길 때 가장 비싼 모델을 늘 쓰면 돈이 새고, 가장 싼 모델을 늘 쓰면 틀린 결과를 고치느라 시간이 샙니다. 알맞은 모델을 고르는 것도 습관입니다.

Habitree는 탐색, 요약, 코드 작성, 리뷰, 위험한 작업 같은 작업 유형마다 시작할 자리(등급과 추론 강도)를 정해 두고, 그 자리를 Anthropic, OpenAI, Google의 실제 모델 이름과 강도 값으로 옮겨 줍니다(`habitree models`). 싼 자리에서 시작한 일은 테스트나 빌드 같은 기계 검증(`habitree verify`)이 실패했을 때만 한 칸씩 올리고, 서버 장애 때는 등급을 올리지 않고 같은 등급의 다른 모델로 돌립니다. 인증, 결제, 배포 같은 위험한 작업에는 하한을 두어 자동으로 내려가지 않게 합니다.

라우터를 따로 띄우지 않습니다. 정책 하나에서 Claude Code 서브에이전트, Codex, Aider, LiteLLM, opencode 설정을 만들어 냅니다. 모델 가격과 단종일은 출처, 확인한 날짜와 함께 대응표에 두고, 오래되면 `habitree check`가 알려 줍니다. 자세한 것은 [docs/spec/models.md](docs/spec/models.md)에 있습니다.

## 방향

- **어떤 언어, 어떤 환경에서도.** 규칙과 설정은 JSON과 Markdown으로 된 명세이고, 이 엔진은 그 명세의 참조 구현입니다. Windows, macOS, Linux에서 같은 명령으로 돌고, 한글 파일 이름과 공백이 든 경로도 처리합니다. 다른 언어로 엔진을 새로 만들어도 [적합성 시험](docs/spec/conformance.md)을 통과하면 같은 규칙 DB를 쓸 수 있습니다.
- **AI가 읽는 분량은 작게.** 지침 파일에는 꼭 필요한 것만 넣고, 나머지는 필요할 때 범위별로 꺼내 읽게 합니다.
- **사람이 쓴 것은 지킨다.** 도구는 자기가 만든 구역만 고치고, 사람이 손댄 생성 구역은 덮어쓰지 않습니다.
- **재지 않은 숫자는 말하지 않는다.** 토큰을 몇 퍼센트 줄인다는 식의 말은 직접 재서 과정까지 공개하기 전에는 하지 않습니다.

## 로드맵

| 버전 | 내용 | 상태 |
|---|---|---|
| v0.1 | 규칙 DB, `init`·`rules`·`check`·`export`, 적합성 시험, 세 OS CI | 완료 |
| v0.2 | 작업 중 비효율 경고(`guard`), 훅, 위임 예외, Claude Code 플러그인 | 완료 |
| v0.3 | 모델 배분(`models`), 검증 명령(`verify`) | 완료 |
| v0.4 | 코드 색인(`map`), MCP 서버 | 진행 중 |
| v0.5 | 세션 기록 분석(`audit`), 전후 비교 측정(`bench`) | 예정 |

## 문서

| 찾는 것 | 위치 |
|---|---|
| 작업 순환, 지도, 규칙 사다리 | [docs/spec/method.md](docs/spec/method.md) |
| 규칙 DB 형식 | [docs/spec/rules-format.md](docs/spec/rules-format.md) |
| 점검 항목 | [docs/spec/check.md](docs/spec/check.md) |
| 작업 중 경고와 위임 | [docs/spec/guard.md](docs/spec/guard.md) |
| 모델 배분과 검증 | [docs/spec/models.md](docs/spec/models.md) |
| 적합성 시험 | [docs/spec/conformance.md](docs/spec/conformance.md) |
| 구조와 기여 방법 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 바뀐 것 | [CHANGELOG.md](CHANGELOG.md) |
| 빌려 온 생각과 출처 | [NOTICE.md](NOTICE.md) |

## 지도

| 폴더 | 하는 일 |
|---|---|
| [src/](src/) | 엔진 코드(`habitree` 패키지) |
| [docs/](docs/) | 명세 |
| [tests/](tests/) | 시험 |
| [conformance/](conformance/) | 적합성 시험 사례 |
| [skills/](skills/) | 필요할 때 불러 읽는 짧은 절차(작업 순환, 피드백을 규칙으로, 위임) |
| [hooks/](hooks/) | Claude Code 플러그인 훅 |
| [.claude-plugin/](.claude-plugin/) | Claude Code 플러그인과 마켓플레이스 정의 |

## 만든 곳

[Open Prompt](https://github.com/GarlicChicken)의 첫 오픈소스입니다. Open Prompt는 누구나 AI를 쉽게 배우고 일상과 일에서 능률을 높이도록 돕는 프로젝트이고, 만든 것은 조건 없이 공개합니다.

---

## English

Habitree helps you spend fewer tokens and reuse more when coding with AI. Feedback grows into rules, and repetition grows into modules.

### Why

When you hand coding work to an AI, you end up saying the same things again and again. A habit you corrected last week shows up again this week. A function that already exists gets written a second time. The same file gets read over and over. Each time, time and tokens leak away.

Plenty of tools try to help, but most stop at appending a line to an instruction file such as CLAUDE.md. The file keeps growing, and the AI reads all of it every time, so the waste you meant to remove comes back in another form.

Habitree stores feedback as structure rather than prose. Every rule has a scope (what it is about), an aspect and an optional context, and the agent reads only the rules for the scopes the current task touches. When the same feedback comes back, the rule hardens, and whatever a machine can verify moves into an automatic check.

```
spoken feedback → should rule → must rule → automatic check → blocked in code
```

There is one goal: you should never have to give the same feedback twice.

### What it does

- **Rule DB:** grows feedback into rules on a scope tree and pulls only what a task needs, within a size budget. Before adding a rule it looks for one that already means the same thing.
- **Checks:** verifies, without any AI, that the map (README), the real folders, the doc links and the rule DB agree. Results are the same every time, so they fit straight into CI or hooks.
- **Instruction files:** generates AGENTS.md and CLAUDE.md from the rules, so Codex, Cursor, Copilot, Gemini CLI and Claude Code all read one source. Text you wrote yourself is left alone.

### Install

Runs on Python 3.9+ with no third-party dependencies. If you install with [uv](https://docs.astral.sh/uv/), uv takes care of Python even when it is not on the machine.

```
uv tool install git+https://github.com/GarlicChicken/habitree
# or
pipx install git+https://github.com/GarlicChicken/habitree
```

This installs the `habitree` command and a short alias, `ht`.

### Quick start

```
cd your-project
habitree init                 # install the skeleton
habitree check                # check map, docs and rules
habitree rules brief global   # rules to read before working
```

If you use Claude Code, install the plugin too. It adds the hooks that warn you during work, plus a few skills.

```
claude plugin marketplace add GarlicChicken/habitree
claude plugin install habitree@habitree
```

To wire only the hooks into a project without the plugin, use `habitree init --hooks`.

`init` creates the files below. It never deletes what you wrote in existing files, and running it again later only adds new default rules.

| File | Purpose |
|---|---|
| `.habitree/config.json` | Settings: language, verify commands, and so on |
| `.habitree/rules.json`, `.habitree/RULES.md` | The rule DB and a readable rule document |
| `AGENTS.md`, `CLAUDE.md` | Instructions for AI tools; only the marked managed block is touched |
| Map in `README.md` | A draft map of top-level folders |
| `LOG.md` | Change log and a "to fix" list |

### Turning feedback into rules

When you find yourself correcting the AI, record the correction as a rule while fixing it. AGENTS.md explains how, so the agent usually records it on its own.

```
habitree rules add --scope work --aspect process \
  --rule "Write commit messages in Korean" --why "team rule" --feedback "wrote in English"
habitree rules hit <id> --feedback "English again"      # same feedback: should → must
habitree rules miss <id> --feedback "wrong warning"     # the rule or warning was wrong
habitree rules similar "commit message language"        # find rules with the same meaning
```

Rules sit on a scope tree (`work` → `work/cycle`), and child scopes inherit their parents' rules. Human feedback promotes quickly; demoting a rule needs a reason from a person (`demote`). Duplicate rules would split the feedback count, so `add` stops and tells you when it sees a similar rule.

### Checks

`habitree check` is deterministic. It exits with 1 on errors and can print machine-readable results with `--json`. The table above lists the check families; the full list is in [docs/spec/check.md](docs/spec/check.md).

Add `check.run` to a rule and the "automatic check" rung of the ladder actually runs: a command (exit 0 passes), a forbidden pattern, a required pattern or a line limit. It works the same whatever language your project is written in.

### Warnings while you work

Waste usually shows up only afterwards. You learn from the session log that the same command ran five times, the same fix was retried on the same error, or one file doubled in size by appending alone.

Habitree points these out while the work is happening. When the same command runs a third time, the same fix is retried on the same error, or a file keeps growing by appending alone, it hands the AI one line so it can change course. If that does not help, it stops and asks you. Detection looks only at behavior such as tool calls and file changes, so it works the same for a project in any language.

Warnings are rules in the rule DB too. Reactions such as "that was right" or "that was noise" (`rules hit`, `rules miss`) adjust the thresholds, repeated warnings are capped, and you can mute one for the session (`habitree guard off <id>`).

When you hand over a task with "just do it", the agent goes with the recommended options without asking, for that task only. It still asks before anything hard to undo, such as deleting, deploying, sending data outside, payments or personal data, and at the end it reports the decisions it made and the warnings it held back. See [docs/spec/guard.md](docs/spec/guard.md).

### The right model for each job

Using the most expensive model for everything wastes money; using the cheapest for everything wastes time fixing wrong results. Picking the right model is a habit too.

Habitree sets a starting place (tier and reasoning effort) for each kind of work, such as exploring, summarizing, writing code, reviewing or risky changes, and translates it into real model names and effort values for Anthropic, OpenAI and Google (`habitree models`). Work that starts in a cheap place moves up one step only when machine verification such as tests or builds fails (`habitree verify`), and outages switch to another model of the same tier instead of raising it. Risky work such as auth, payments and deploys has a floor that is never lowered automatically.

There is no router to run. One policy generates settings for Claude Code subagents, Codex, Aider, LiteLLM and opencode. Model prices and retirement dates live in a vendor table with their sources and checked dates, and `habitree check` tells you when they get old. See [docs/spec/models.md](docs/spec/models.md).

### Direction

- **Any language, any environment.** Rules and settings are a JSON and Markdown specification, and this engine is its reference implementation. The same commands run on Windows, macOS and Linux, including Korean file names and paths with spaces. An engine written in another language can share the same rule DB once it passes the [conformance suite](docs/spec/conformance.md).
- **Keep what the AI reads small.** Instruction files hold only what is essential; everything else is pulled per scope when needed.
- **Respect human edits.** The tool only rewrites the blocks it generated and never overwrites a generated block someone changed by hand.
- **No numbers we have not measured.** Claims such as "saves N% of tokens" wait until we have measured them and published how.

### Roadmap

| Version | Contents | Status |
|---|---|---|
| v0.1 | Rule DB, `init`/`rules`/`check`/`export`, conformance suite, CI on three OSes | Done |
| v0.2 | In-flight warnings (`guard`), hooks, delegation, Claude Code plugin | Done |
| v0.3 | Model allocation (`models`), verify commands (`verify`) | Done |
| v0.4 | Code index (`map`), MCP server | In progress |
| v0.5 | Session audit (`audit`), before/after benchmark (`bench`) | Planned |

### Made by

The first open-source project from [Open Prompt](https://github.com/GarlicChicken), which helps anyone learn AI easily and get more out of it in daily life and work. What we make is published without conditions.
