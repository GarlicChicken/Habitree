# 방법

Habitree의 중심은 코드가 아니라 일하는 방법입니다. `habitree` 명령은 이 방법을 덜 번거롭게 해 주는 도구일 뿐이라, 엔진이 없어도 사람과 AI가 이 문서대로 일할 수 있습니다.

## 작업 순환

AI와 일하면서 생기는 낭비는 대부분 "이미 있는 것을 몰라서" 생깁니다. 그래서 모든 작업을 찾는 것부터 시작합니다.

1. **찾기.** 지도와 규칙에서 같은 일을 하는 문서, 도구, 코드가 있는지 먼저 봅니다.
2. **있으면 쓰기.** 있는 것을 씁니다. 쓰다가 낡았거나 틀린 곳을 보면 그 자리에서 고칩니다.
3. **없으면 만들기.** 되풀이될 일이면 처음부터 도구나 모듈, 양식으로 만듭니다.
4. **기록하기.** 바꾼 것을 폴더 README, 지도, 변경 기록에 함께 반영합니다.
5. **고치기.** 지금 고치지 못한 문제는 변경 기록의 '손볼 것'에 적어 둡니다.
6. **점검하기.** 끝내기 전에 `habitree check`와 검증 명령을 돌립니다.

이 순서가 몸에 배면, 다음 작업은 지난 작업이 남긴 지도와 규칙 위에서 시작합니다. 프로젝트가 작업할 때마다 조금씩 똑똑해지는 것입니다.

## 지도

프로젝트에는 나무 모양의 지도가 있습니다. 루트 README에 최상위 폴더의 지도와 '무엇이 어디에' 색인을 두고, 최상위 폴더마다 목적, 구조, 마지막 갱신일을 적은 README를 둡니다.

AI는 프로젝트 전체를 뒤지기 전에 이 지도부터 읽습니다. 지도는 짧을수록 좋습니다. 지도를 쓰는 것은 사람이고, 지도가 실제 폴더나 링크와 어긋나지 않았는지 확인하는 것은 `habitree check`의 몫입니다.

## 원본은 하나

같은 내용이 두 곳에 있으면 언젠가 둘이 서로 다른 말을 합니다. 그래서 내용은 한 곳에 두고 나머지는 링크합니다.

도구가 만든 파일과 구역도 마찬가지입니다. 생성 구역은 `<!-- habitree:begin 이름 -->`와 `<!-- habitree:end 이름 -->` 사이에 있고, 바꾸고 싶으면 원본(규칙 DB)을 고친 뒤 다시 만듭니다. 누군가 생성 구역을 직접 고쳤다면 Habitree는 그 구역을 덮어쓰지 않고 그대로 둡니다.

## 규칙 사다리

```
말로 한 피드백 → 권장(should) → 필수(must) → 자동 검사(check.run) → 코드에서 막기
```

피드백은 처음에 말로 들어옵니다. 같은 말이 또 나오면 그 규칙은 필수가 됩니다. 기계로 확인할 수 있는 규칙은 자동 검사로 옮기고, 그래도 되풀이되는 실수는 코드에서 아예 막습니다.

오르내리는 속도는 근거에 따라 다르게 했습니다.

| 근거 | 올라갈 때 | 내려갈 때 |
|---|---|---|
| 사람이 말한 피드백 | 같은 지적이 또 나오면 바로 필수로 | 사람이 이유를 적을 때만(`demote`) |
| 감지 규칙에 대한 반응 | '맞았다'가 두 번이고 '틀렸다'가 없으면 정보에서 경고로 | 최근 반응에서 '틀렸다'가 10% 이상이면 기준을 완화하고, 25%를 넘으면 끄자고 제안 |
| 멈춤·차단 | 자동으로 올리지 않음 | 자동으로 내리지 않음 |

사람의 말은 믿을 만한 근거라 빠르게 반영하고, 자동 신호는 오탐이 섞이기 마련이라 천천히 반영합니다. 작업을 멈추게 하는 결정은 오탐의 대가가 크기 때문에 늘 사람이 정합니다. 이 비율 기준은 Google이 정적 분석 경고를 운영하며 쓴 방식(Tricorder)에서 빌려 왔습니다.

규칙은 맞는 곳 중 가장 넓은 범위에 둡니다. 그리고 새 규칙을 만들기 전에 같은 뜻의 규칙이 있는지 먼저 찾습니다. 같은 뜻이 두 규칙으로 갈라지면 지적 횟수가 흩어져서 사다리를 오르지 못하기 때문입니다.

## 쌓는 만큼 덜어내기

이 방법은 쌓는 쪽으로 기울기 쉽습니다. 되풀이되면 도구로, 피드백은 규칙으로, 커지면 나눠서 모듈로. 그런데 그렇게 쌓인 것도 결국 읽고 지켜야 하는 짐입니다. 한 번 쓰고 마는 도구, 아무도 다시 쓰지 않는 추상화, 끝없이 늘어나는 규칙은 처음에 아끼려던 토큰과 시간을 다른 모습으로 다시 씁니다.

그래서 쌓는 방향마다 덜어내는 방향을 짝으로 둡니다.

| 쌓는 방향 | 짝이 되는 덜어내기 |
|---|---|
| 되풀이되면 도구·모듈로 | 실제로 다시 쓰일 때만 만든다. 한 곳에서만 쓰는 래퍼·설정 층은 풀어 넣는다 |
| 피드백은 규칙으로 | 같은 뜻 규칙은 합치고, 오래 반응이 없는 규칙은 다시 보고, 맞지 않으면 버린다 |
| 커지면 나눈다 | 서로만 쓰는 작은 파일 여러 개는 하나로 합친다. 새 층을 얹기보다 있는 경계를 따라 나눈다 |
| 기능을 켠다 | 쓰지 않는 기능의 규칙은 프로젝트에 옮겨 적지 않는다. 쓸 때 켠다 |

정리를 제안할 때도 같은 문제라면 덜어내는 해법을 먼저 보여 줍니다. `habitree check`는 끝에 프로젝트의 무게(규칙 수, AI가 매번 읽는 지침 크기)를 한 줄로 보여 주고, 예산을 넘거나 오래 반응이 없는 규칙이 있으면 알려 줍니다.

Habitree 자신에게도 같은 기준을 둡니다. AI가 매번 읽는 지침과 세션 시작 때 넣는 글, 경고 한 건의 길이에는 상한이 있고, 시험으로 지킵니다. 도구를 쓸 때마다 도는 훅은 무거운 모듈을 불러오지 않습니다. 작업 중 경고와 모델 배분의 규칙은 프로젝트에 옮겨 적지 않고 패키지에서 바로 읽으며, 사용자가 반응하거나 고친 규칙만 프로젝트에 남깁니다.

## AI가 읽는 분량

이 문서의 작업 순환은 사람을 위한 설명입니다. AI가 매번 읽는 지침(AGENTS.md, CLAUDE.md)에는 이것을 그대로 옮기지 않습니다.

같은 과제를 지침을 켜고 끈 채 여러 번 돌려 보니, 여섯 단계 작업 순환과 일반 규칙 요약을 실은 지침은 정답률을 올리지 못한 채 토큰과 시간만 늘렸습니다. AI가 작은 수정에도 변경 기록을 읽고 고치고 전체 점검까지 돌렸기 때문입니다. 반대로 그 프로젝트에서 실제로 받은 피드백 규칙은 정답률을 크게 바꿨습니다. 그래서 AI 지침에는 꼭 필요한 것만 둡니다.

- 있는 것을 먼저 찾아 쓰라는 한 줄. 파일이 많은 프로젝트에서만 `habitree map find` 안내를 붙입니다.
- 검증 명령이 등록돼 있으면 그 명령을 끝내기 전에 돌리라는 한 줄.
- 바로잡은 것은 규칙으로 남기라는 한 줄.
- 그리고 이 프로젝트에서 쌓인 규칙.

다만 시작할 때 읽은 한 줄은 몇 턴 뒤 바로잡히는 순간에 잘 떠오르지 않았습니다(두 세션 측정). 그래서 훅이 있는 도구에서는 바로잡는 말이 오면 그때 AI에게 알리고, 규칙을 더하거나 고치면 AI 지침의 생성 구역을 바로 고칩니다. 규칙은 그 순간에 남겨야 다음 세션에 닿습니다.

모델이 이미 잘 지키는 일반 규칙(비밀값을 넣지 않기 등)은 AI 지침에 싣지 않고 기계 점검과 훅이 지킵니다. 여섯 단계 판이 필요하면 설정 `export.style`을 `full`로 바꿉니다. 이 파일들은 한 언어로만 만들고, AGENTS.md는 32KiB, CLAUDE.md는 200줄 안쪽을 한도로 삼습니다.

---

## English

Habitree is a way of working first and code second. The `habitree` command only makes the method less tedious; people and AI agents can follow this document without the engine.

### The work cycle

Most waste in AI-assisted work comes from not knowing what already exists, so every task starts by looking.

1. **Find.** Check the map and the rules for docs, tools or code that already do the job.
2. **Reuse.** Use what exists. If you notice something stale or wrong, fix it on the spot.
3. **Build.** If the work will repeat, make it a tool, module or template from the start.
4. **Record.** Reflect the change in the folder README, the map and the change log.
5. **Fix later.** Note problems you cannot fix now under "To fix" in the change log.
6. **Check.** Run `habitree check` and the verify commands before finishing.

Once this becomes habit, each task starts from the map and rules the previous task left behind. The project gets a little smarter every time someone works on it.

### The map

A project carries a tree-shaped map: the root README holds a map of top-level folders and a "where things are" index, and each top-level folder has a README with its purpose, layout and last-updated date.

The agent reads the map before searching the whole project, so shorter is better. People write the map; `habitree check` makes sure it still matches the real folders and links.

### One source of truth

When the same content lives in two places, the two eventually disagree. Keep content in one place and link to it.

The same holds for generated files and blocks. A managed block sits between `<!-- habitree:begin name -->` and `<!-- habitree:end name -->`; to change it, change the source (the rule DB) and regenerate. If someone edits a managed block by hand, Habitree leaves that block alone.

### The rule ladder

```
spoken feedback → should → must → automatic check (check.run) → blocked in code
```

Feedback arrives as words. When the same words come back, the rule becomes a must. Rules a machine can verify move into automatic checks, and mistakes that still repeat get blocked in code.

Rules move at different speeds depending on the evidence.

| Evidence | Moving up | Moving down |
|---|---|---|
| Human feedback | Straight to must when the same feedback repeats | Only with a reason from a person (`demote`) |
| Reactions to detection rules | Info becomes warn after two "useful" votes and no "wrong" votes | At 10% or more "wrong" votes the threshold relaxes; above 25% a pause is suggested |
| Stopping or blocking | Never automatic | Never automatic |

Human words are strong evidence, so they take effect quickly. Automatic signals always include some false positives, so they move slowly. Decisions that stop work are expensive when wrong, so a person always makes them. The ratio thresholds come from how Google ran static analysis warnings (Tricorder).

Place each rule at the widest scope where it holds, and look for a rule with the same meaning before adding a new one. Duplicates split the feedback count and never climb the ladder.

### Trim as much as you grow

This method leans toward adding: repeated work becomes a tool, feedback becomes a rule, growing code is split into modules. But whatever piles up is something to read and maintain. A tool used once, an abstraction nobody reuses and a rule list that keeps growing spend, in another form, the very tokens and time they were meant to save.

So every direction of growth is paired with a direction of trimming.

| Growing | Paired trimming |
|---|---|
| Repeated work becomes a tool or module | Build it only when it will actually be reused; inline wrappers and config layers used in one place |
| Feedback becomes a rule | Merge rules with the same meaning, revisit rules with no feedback for a long time, drop the ones that no longer fit |
| Growing code gets split | Merge clusters of tiny files that only use each other; split along existing boundaries rather than adding layers |
| Features get switched on | Rules of features you do not use are not copied into the project; switch them on when you use them |

Cleanup suggestions show the subtracting fix first when it solves the same problem. `habitree check` ends with one line on the project's weight (number of rules, size of the instructions read every session) and warns when a budget is exceeded or rules have gone quiet for a long time.

Habitree holds itself to the same standard. The instructions read every session, the text injected at session start and the length of a single warning have limits that tests enforce. Hooks, which run on every tool call, do not load heavy modules. The rules for in-flight warnings and model allocation are read straight from the package instead of being copied into the project; only rules you react to or edit are kept there.

### What the AI reads

The work cycle in this document is an explanation for people. It is not copied as is into the instructions an agent reads every session (AGENTS.md, CLAUDE.md).

Running the same tasks many times with and without the instructions showed that the version carrying the six-step cycle and a summary of generic rules raised tokens and time without raising the pass rate: the agent read and updated the change log and ran a full check even for a small fix. The feedback rules this project had actually received, on the other hand, changed the pass rate a great deal. So the agent instructions keep only what is needed:

- One line to look for what already exists and reuse it, with a `habitree map find` hint only in projects with many files.
- One line to run the registered verify commands before finishing, only if there are any.
- One line to record corrections as rules.
- The rules this project has grown.

A line read at the start, however, was rarely recalled at the moment of correction several turns later (two-session measurement). So on tools with hooks, a correcting message triggers a note to the agent right then, and adding or changing a rule refreshes the generated blocks of the agent instructions at once. A rule has to be recorded at that moment to reach the next session.

Generic rules a model already follows well (such as keeping secrets out) are left out of the instructions and enforced by checks and hooks. Set `export.style` to `full` if you want the six-step version. These files are generated in one language, with limits of 32 KiB for AGENTS.md and 200 lines for CLAUDE.md.
