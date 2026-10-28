# bench

규칙이 정말 도움이 되는지 재는 곳입니다. 같은 과제를 Habitree 규칙을 켠 채로 몇 번, 끈 채로 몇 번 AI에게 맡기고, 토큰·비용·시간과 함께 정답을 맞혔는지를 나란히 놓습니다. 토큰이 줄었다는 말은 정답률과 함께 볼 때만 뜻이 있어서, 결과 표에는 늘 둘이 같이 나옵니다.

- 마지막 갱신: 2026-10-28

## 예제 과제

일부러 아주 작게 만들었습니다. 파일 몇 개짜리라 한 번 돌리는 데 드는 사용량이 적고, 결과를 사람이 바로 읽을 수 있습니다.

| 과제 | 보는 것 |
|---|---|
| `reuse-helper/` | 이미 있는 함수(`textkit.slugify`)를 찾아 다시 쓰는가. Python |
| `money-rules/` | 팀이 정한 규칙(원 단위 반올림 함수, 잘못된 입력은 오류)을 지키는가. JavaScript(Node) |

과제 하나는 `task.json`(지시문, 채점 명령, 시간 한도, with 갈래에 넣을 규칙)과 `project/`(시작 상태), `verify/`(채점 스크립트)로 되어 있습니다. 채점 스크립트는 작업 폴더 밖에 있어서 AI가 보거나 고칠 수 없습니다.

## 돌리기

```
habitree bench run reuse-helper --runner claude --dry-run     # 계획만 보기
habitree bench run reuse-helper --runner claude --max-budget-usd 1 --yes
habitree bench report bench/results/2026-10-28-reuse-helper
```

`claude` 실행기는 실제 사용량이 들어서 `--yes`가 있어야 돕니다. 먼저 `--dry-run`으로 무엇을 몇 번 돌릴지 확인하세요. 실행 격리, 반복 수, 결과를 공개할 때의 원칙은 [docs/spec/bench.md](../docs/spec/bench.md)에 있습니다.

결과는 `bench/results/`에 쌓이고 커밋하지 않습니다(`.gitignore`). 실행기 원본 출력에는 내 컴퓨터의 경로나 대화 글이 들어갈 수 있으니, 공개할 때는 `report.md`와 `report.json`을 읽어 보고 옮깁니다.

## 과제 더하기

새 폴더에 `task.json`, `project/`, `verify/`를 두면 됩니다. 채점은 종료 코드 0이 합격이고, 명령은 인자 배열로 적습니다(`{python}`은 지금 Python, `{task}`는 과제 폴더로 바뀝니다). 다른 언어 과제가 늘수록 "어떤 언어에서든 효과가 있는가"를 더 정직하게 말할 수 있습니다.

---

## English

This is where we measure whether rules actually help. The same task is given to an AI several times with Habitree rules on and several times with them off, and the results are laid side by side: tokens, cost and time, together with whether the answer was right. Fewer tokens only mean something next to the pass rate, so the result table always shows both.

The example tasks are deliberately tiny. With only a few files, one run costs little and a person can read the outcome at a glance.

| Task | What it looks at |
|---|---|
| `reuse-helper/` | Does the agent find and reuse an existing function (`textkit.slugify`)? Python |
| `money-rules/` | Does it follow team rules (a won rounding helper, errors for bad input)? JavaScript (Node) |

A task is a `task.json` (prompt, verify commands, time limit, rules for the "with" arm), a `project/` folder (the starting state) and a `verify/` folder (graders). The graders live outside the working copy, so the agent cannot see or change them.

Run `bench run … --dry-run` first to see the plan; the `claude` runner uses real usage and only runs with `--yes`. Isolation, repetitions and how to publish results are covered in [docs/spec/bench.md](../docs/spec/bench.md). Results collect in `bench/results/` and are not committed; raw runner output can contain local paths or conversation text, so read `report.md` and `report.json` before sharing them.

To add a task, create a folder with `task.json`, `project/` and `verify/`. A verify command passes with exit code 0 and is written as an argument list (`{python}` becomes the current Python, `{task}` the task folder). More tasks in more languages let us say more honestly whether the effect holds across languages.
