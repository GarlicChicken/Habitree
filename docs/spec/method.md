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

## AI가 읽는 분량

AI가 매번 읽는 파일(AGENTS.md, CLAUDE.md)은 짧게 유지합니다. 작업 순환과 필수 규칙 요약만 넣고, 나머지는 `habitree rules brief`로 필요한 범위만 꺼내 읽게 합니다. 이 파일들은 한 언어로만 만들어서 같은 내용을 두 번 읽지 않게 합니다. 여러 도구가 읽는 AGENTS.md는 32KiB 안쪽, Claude Code가 읽는 CLAUDE.md는 200줄 안쪽을 기준으로 삼습니다.

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

### What the AI reads

Keep the files an agent reads on every session (AGENTS.md, CLAUDE.md) short: the work cycle and a summary of must rules, with everything else pulled per scope through `habitree rules brief`. These files are generated in one language so the same content is not read twice. The working limits are 32 KiB for AGENTS.md, which several tools read, and 200 lines for CLAUDE.md.
