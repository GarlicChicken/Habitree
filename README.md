# Habitree

AI와 함께 일하는 습관을 나무처럼 키우는 도구입니다. 피드백은 규칙으로, 되풀이는 모듈로 자라게 하고, 그렇게 자란 것이 짐이 되지 않게 함께 다듬습니다.

- 마지막 갱신: 2026-10-28
- 상태: v0.7 알파
- 라이선스: [MIT](LICENSE)
- [English](#english)

## 왜 만들었나

AI에게 일을 맡기다 보면 같은 말을 여러 번 하게 됩니다. 지난주에 고쳐 달라고 한 버릇이 이번 주에 또 나오고, 이미 있는 함수를 모른 채 비슷한 함수를 새로 만들고, 같은 파일을 몇 번이고 다시 읽습니다. 그때마다 시간과 토큰이 조금씩 샙니다. 하나하나는 작아 보여도 쌓이면 꽤 큽니다.

Habitree는 [Open Prompt](https://github.com/GarlicChicken)를 운영하며 쓰던 방식에서 나왔습니다. 그 프로젝트는 작업할 때마다 조금씩 나아지는 하나의 두뇌처럼 굴러갑니다. 일을 시작하면 지도부터 보고, 있는 것은 다시 쓰고, 없는 것은 되풀이될 것을 생각해 만들고, 바꾼 것은 기록하고, 받은 피드백은 그 자리에서 규칙으로 남깁니다. 그렇게 하니 같은 지적이 다시 나오는 일이 눈에 띄게 줄었습니다. 이 습관을 다른 프로젝트에서도 쓸 수 있게 꺼내 놓은 것이 Habitree입니다.

목표는 처음부터 하나였습니다. **효율과 재사용.** 덜 읽고, 덜 되풀이하고, 이미 만든 것을 다시 쓰게 하는 것입니다.

## 생각하는 방식

**같은 피드백은 두 번 하지 않는다.** 피드백은 말로 들어옵니다. 같은 말이 또 나오면 그 규칙은 필수가 되고, 기계로 확인할 수 있으면 자동 검사가 되고, 그래도 되풀이되는 실수는 코드에서 막습니다. 규칙은 글 한 덩어리가 아니라 범위·관점·상황으로 나눠 쌓아서, AI는 지금 하는 일에 맞는 규칙만 꺼내 읽습니다.

```
말로 한 피드백 → 권장 규칙 → 필수 규칙 → 자동 검사 → 코드에서 막기
```

**만들기 전에 찾는다.** 낭비는 대개 "이미 있는 것을 몰라서" 생깁니다. 그래서 모든 작업은 찾는 것에서 시작합니다. 사람이 쓴 지도로 큰 그림을 보고, 코드 색인으로 함수 하나까지 찾고, 그다음에 만듭니다.

**쌓는 만큼 덜어낸다.** 규칙과 도구와 모듈은 쌓을수록 좋은 것이 아닙니다. 한 번 쓰고 마는 도구, 아무도 다시 쓰지 않는 추상화, 끝없이 늘어나는 규칙은 그 자체로 짐입니다. 그래서 되풀이될 때만 도구로 만들고, 겹치거나 안 쓰이는 규칙은 합치거나 버리고, 정리를 권할 때도 더하는 해법보다 덜어내는 해법을 먼저 보여 줍니다. Habitree 자신도 마찬가지입니다. AI가 매번 읽는 분량과 훅이 붙이는 시간에는 예산이 있고, 무거운 기능은 쓸 때만 켭니다.

**확인은 기계가, 결정은 사람이.** 점검은 AI에게 판단을 맡기지 않고 정해진 방식으로만 해서 매번 같은 결과가 나옵니다. 사람의 말은 믿을 만한 근거라 빠르게 반영하고, 자동 신호는 오탐이 섞이기 마련이라 천천히 반영합니다. 작업을 멈추게 하는 결정과 되돌리기 어려운 일은 늘 사람이 정합니다. "알아서 해 줘"라고 맡겨도 지우기, 배포, 외부로 보내기 같은 일은 그때 다시 묻습니다.

**어떤 언어, 어떤 환경에서도.** 규칙과 설정은 JSON과 Markdown으로 된 명세이고, 이 엔진은 그 명세를 따르는 참조 구현입니다. 프로젝트가 어떤 언어로 짜였든, Windows든 macOS든 Linux든, Claude Code든 Codex든 Cursor든 같은 원본을 씁니다. 한글 파일 이름과 한국어 검색도 처음부터 챙겼습니다. 개발자가 아니어도 AI에게 무언가를 맡기는 사람이라면 쓸 수 있게 쉬운 말로 알려 주려고 합니다.

**재지 않은 숫자는 말하지 않는다.** 토큰을 몇 퍼센트 줄인다는 식의 말은, 같은 과제를 규칙을 켜고 끈 채 여러 번 돌려 재고 그 과정까지 공개하기 전에는 하지 않습니다.

## 언제 무엇을 돕나

| 언제 | 하는 일 | 명령 |
|---|---|---|
| 작업 전 | 지켜야 할 규칙과 이미 있는 코드를 적은 분량으로 찾기 | `rules brief`, `map` |
| 작업 중 | 같은 일을 맴돌거나 파일에 덧대기만 할 때 그 자리에서 알리기, 맡긴 일은 경계 안에서 | `hook`, `guard`(Claude Code 플러그인) |
| 끝낼 때 | 지도·문서·규칙이 실제와 맞는지, 검증 명령이 통과하는지 확인하고, 이 프로젝트가 지는 무게를 한 줄로 보여 주기 | `check`, `verify` |
| 되돌아볼 때 | 어디서 토큰이 샜는지, 무엇을 합치고 덜어낼지 | `audit`, `refactor` |
| 모델을 고를 때 | 일마다 알맞은 등급에서 시작하고, 검증이 실패할 때만 올리기 | `models` |
| 효과를 잴 때 | 규칙을 켜고 끈 채 같은 과제를 여러 번 돌려 비교 | `bench` |

각 기능이 왜 그렇게 동작하는지는 [docs/](docs/README.md)의 명세에 있습니다.

## 시작하기

Python 3.9 이상에서 돌고, 바깥 패키지에 기대지 않습니다. [uv](https://docs.astral.sh/uv/)로 설치하면 컴퓨터에 Python이 없어도 uv가 알아서 준비합니다.

```
uv tool install git+https://github.com/GarlicChicken/habitree
cd 내-프로젝트
habitree init       # 지도, 기본 규칙, AI 지침 파일을 깐다
habitree check      # 지도·문서·규칙이 실제와 맞는지 본다
```

Claude Code를 쓴다면 플러그인을 더하면 작업 도중 알림과 스킬이 들어옵니다.

```
claude plugin marketplace add GarlicChicken/habitree
claude plugin install habitree@habitree
```

`init`은 이미 있는 파일에서 사람이 쓴 내용을 지우지 않습니다. AGENTS.md와 CLAUDE.md에는 표시된 생성 구역 하나만 두고, 나중에 다시 실행하면 새로 생긴 기본 규칙만 더합니다. 프로젝트에 옮겨 적는 것은 기본 규칙뿐이고, 작업 중 경고와 모델 배분의 규칙은 쓸 때 패키지에서 바로 읽습니다.

## 피드백을 규칙으로

AI의 결과를 바로잡을 때는 고치는 것과 함께 규칙으로 남깁니다. AGENTS.md에 방법이 적혀 있어서 대개는 AI가 직접 기록합니다.

```
habitree rules add --scope work --aspect process \
  --rule "커밋 메시지는 한국어로 쓴다" --why "팀 규칙" --feedback "영어로 썼음"
habitree rules hit <id> --feedback "또 영어로 씀"       # 같은 지적: 권장에서 필수로
habitree rules miss <id> --feedback "이번 경고는 틀렸음"  # 규칙이나 경고가 틀렸을 때
```

새 규칙을 더하기 전에 같은 뜻의 규칙이 이미 있는지 먼저 찾아 줍니다. 같은 뜻이 둘로 갈라지면 지적 횟수가 흩어져 규칙이 단단해지지 못하기 때문입니다.

## 로드맵

| 버전 | 내용 | 상태 |
|---|---|---|
| v0.1 | 규칙 DB, 점검, 지침 파일 생성, 적합성 시험, 세 OS CI | 완료 |
| v0.2 | 작업 중 알림, 훅, 위임, Claude Code 플러그인 | 완료 |
| v0.3 | 모델 배분, 검증 명령 | 완료 |
| v0.4 | 코드 색인, MCP 서버 | 완료 |
| v0.5 | 세션 기록 분석, 전후 비교 측정 | 완료 |
| v0.6 | 리팩토링 제안(합치기와 덜어내기 먼저) | 완료 |
| v0.7 | 가볍게: 훅 비용과 기본 설치를 줄이고, 쓰는 프로젝트의 무게도 보여 주기 | 완료 |

## 문서와 지도

| 찾는 것 | 위치 |
|---|---|
| 일하는 방법: 작업 순환, 지도, 규칙 사다리 | [docs/spec/method.md](docs/spec/method.md) |
| 기능별 명세 | [docs/](docs/README.md) |
| 구조와 기여 방법 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 바뀐 것 | [CHANGELOG.md](CHANGELOG.md) |
| 빌려 온 생각과 출처 | [NOTICE.md](NOTICE.md) |

| 폴더 | 하는 일 |
|---|---|
| [src/](src/) | 엔진 코드(`habitree` 패키지) |
| [docs/](docs/) | 명세 |
| [tests/](tests/) | 시험 |
| [conformance/](conformance/) | 다른 구현과 결과를 맞추는 적합성 시험 사례 |
| [skills/](skills/) | AI가 필요할 때만 불러 읽는 짧은 절차 |
| [hooks/](hooks/) | Claude Code 플러그인 훅 |
| [.claude-plugin/](.claude-plugin/) | Claude Code 플러그인과 마켓플레이스 정의 |
| [bench/](bench/) | 규칙을 켜고 끈 채 비교하는 측정 과제 |

## 만든 곳

Habitree는 [Open Prompt](https://github.com/GarlicChicken)의 첫 오픈소스입니다. Open Prompt는 AI가 소수의 기술이 아니라 모두의 도구가 되도록, 누구나 AI를 쉽게 배우고 일상과 일에서 능률을 높이게 돕는 프로젝트입니다. 만든 것은 조건 없이 공개하고, 좋은 생각은 기꺼이 빌리되 어디서 왔는지 밝힙니다.

---

## English

Habitree grows your habits for working with AI, like a tree. Feedback grows into rules and repetition grows into modules, and what grows is trimmed so it never turns into a burden.

### Why

When you hand work to an AI, you end up saying the same things again and again. A habit you corrected last week shows up again this week, a function that already exists gets written a second time, and the same file gets read over and over. Each time a little time and a few tokens leak away. Each leak looks small; together they add up.

Habitree comes from the way we run [Open Prompt](https://github.com/GarlicChicken). That project works like a brain that gets a little better every time someone works on it: you start from the map, reuse what exists, build what is missing with repetition in mind, record what changed, and turn feedback into a rule on the spot. Doing that, the same correction came back noticeably less often. Habitree takes that habit out so other projects can use it.

The goal has been the same from the start: **efficiency and reuse.** Read less, repeat less, and use again what has already been built.

### How we think about it

**Never give the same feedback twice.** Feedback arrives as words. When the same words come back the rule becomes a must; when a machine can verify it, it becomes an automatic check; and mistakes that still repeat are blocked in code. Rules are stored by scope, aspect and context rather than as one block of prose, so the agent reads only the rules that fit the task at hand.

```
spoken feedback → should rule → must rule → automatic check → blocked in code
```

**Look before you build.** Most waste comes from not knowing what already exists, so every task starts with looking: the hand-written map for the big picture, the code index down to single functions, and only then building.

**Trim as much as you grow.** More rules, tools and modules are not automatically better. A tool used once, an abstraction nobody reuses and a rule list that keeps growing are weight in themselves. So tools are made only when work actually repeats, overlapping or unused rules are merged or dropped, and cleanup suggestions show the subtracting fix before the adding one. The same goes for Habitree itself: what the agent reads every session and the time hooks add have budgets, and heavier features are switched on only when you use them.

**Machines check, people decide.** Checks never ask an AI to judge; they are deterministic and give the same result every time. Human words are strong evidence and take effect quickly, while automatic signals always carry some false positives and move slowly. Decisions that stop work, and anything hard to undo, are always made by a person. Even when you say "just do it", deleting, deploying or sending data outside is confirmed at that moment.

**Any language, any environment.** Rules and settings are a JSON and Markdown specification, and this engine is a reference implementation of it. Whatever language your project uses, whether you are on Windows, macOS or Linux, and whether you work with Claude Code, Codex or Cursor, they share one source. Korean file names and Korean search were handled from the start, and we try to speak in plain words so that anyone who hands work to an AI can use it, not only developers.

**No numbers we have not measured.** Claims such as "saves N% of tokens" wait until the same tasks have been run several times with the rules on and off, and the process is published.

### What it helps with

| When | What it does | Commands |
|---|---|---|
| Before work | Find the rules to follow and the code that already exists, in few tokens | `rules brief`, `map` |
| During work | Point out going in circles or patching onto one file on the spot; keep delegated work inside its boundaries | `hook`, `guard` (Claude Code plugin) |
| When finishing | Check that the map, docs and rules match reality and that verify commands pass, and show in one line the weight the project carries | `check`, `verify` |
| Looking back | See where tokens leaked and what to merge or remove | `audit`, `refactor` |
| Choosing a model | Start each kind of work at a suitable tier and move up only when verification fails | `models` |
| Measuring | Run the same tasks with the rules on and off and compare | `bench` |

Why each feature behaves the way it does is explained in the specs under [docs/](docs/README.md).

### Getting started

Runs on Python 3.9+ with no third-party dependencies. With [uv](https://docs.astral.sh/uv/), uv takes care of Python even when it is not installed.

```
uv tool install git+https://github.com/GarlicChicken/habitree
cd your-project
habitree init       # install the map, default rules and agent instruction files
habitree check      # check that map, docs and rules match reality
```

If you use Claude Code, add the plugin for in-flight warnings and skills:

```
claude plugin marketplace add GarlicChicken/habitree
claude plugin install habitree@habitree
```

`init` never deletes what you wrote in existing files. AGENTS.md and CLAUDE.md get a single marked managed block, and running `init` again later only adds new default rules. Only the base rules are copied into the project; the rules for in-flight warnings and model allocation are read straight from the package when used.

### Turning feedback into rules

When you correct the AI, record the correction as a rule while fixing it; AGENTS.md explains how, so the agent usually records it itself. Use `rules add` for a new rule, `rules hit` when the same feedback comes back (should becomes must), and `rules miss` when a rule or warning was wrong. Before adding a rule, Habitree looks for one that already means the same thing, because duplicates split the feedback count and never harden.

### Roadmap

| Version | Contents | Status |
|---|---|---|
| v0.1 | Rule DB, checks, instruction file generation, conformance suite, CI on three OSes | Done |
| v0.2 | In-flight warnings, hooks, delegation, Claude Code plugin | Done |
| v0.3 | Model allocation, verify commands | Done |
| v0.4 | Code index, MCP server | Done |
| v0.5 | Session audit, before/after benchmark | Done |
| v0.6 | Refactoring suggestions (merging and removing first) | Done |
| v0.7 | Lighter: smaller hook cost and default install, and showing the weight of the project that uses it | Done |

### Made by

Habitree is the first open-source project from [Open Prompt](https://github.com/GarlicChicken), which works so that AI becomes everyone's tool rather than a skill for a few: helping anyone learn AI easily and get more out of it in daily life and work. What we make is published without conditions, and we gladly borrow good ideas while saying where they came from.
