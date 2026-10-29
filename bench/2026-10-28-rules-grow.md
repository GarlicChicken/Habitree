# 규칙이 자라는지 (2026-10-28)

[첫 측정](2026-10-28-first-measurement.md)은 이미 들어 있는 규칙의 효과만 봤습니다. Habitree라는 이름이 말하는 것, 곧 사용자가 바로잡은 것이 규칙으로 자라서 다음 세션에서 같은 실수를 막는지는 따로 재야 했습니다. 이 기록은 그 측정과, 재다가 발견해서 고친 것입니다.

- [English](#english)

## 조건

| 항목 | 값 |
|---|---|
| 과제 | `reuse-helper`(이미 있는 `textkit.slugify`를 다시 쓰는가, Python), `money-rules`(팀이 정한 반올림 함수와 오류 규칙을 지키는가, JavaScript) |
| 흐름 | 세션 1에서 과제 A를 시킵니다. 채점에 떨어지면 같은 세션에서 한 번 바로잡습니다. 그다음 코드 파일만 처음 상태로 되돌리고, 같은 폴더에서 새 세션을 열어 비슷한 과제 B를 시킵니다 |
| 바로잡는 말 | "제목을 바꾸는 코드를 새로 짜지 마. textkit.py에 slugify()가 이미 있으니 그걸 불러 써서 고쳐 줘." / "우리 팀은 금액을 money.js의 roundWon()으로 원 단위로 맞추고, 잘못된 입력(음수, 100을 넘는 비율, 모르는 종류)은 null 대신 RangeError를 던지기로 했어. 그렇게 고쳐 줘." "기억해 줘" 같은 말은 일부러 넣지 않았습니다 |
| 과제 B | `draft_name(title)`: 'draft-제목.md' 꼴의 파일 이름 / `splitBill(total, people)`: 한 사람이 낼 금액 |
| 갈래 | with: `habitree init --hooks`, 규칙 0개에서 시작 / without: 아무것도 깔지 않음. 두 갈래 모두 `habitree` 명령을 쓸 수 있게 허용 |
| 모델 | Claude Sonnet(`claude -p --model sonnet`), 호출당 한도 $1 |
| 반복 | 과제·갈래마다 3번 |
| 채점 | 작업 폴더 밖의 채점 스크립트. B의 채점은 동작과 함께 그 함수(`slugify`, `roundWon`)를 불러 쓰는지 봅니다 |
| 환경 | Windows 개발 컴퓨터 한 대, 격리 없음 |
| 규모 | 본 측정 12번(호출 35번), 약 $4.6. 그 전의 시험 실행 2번은 결과에서 뺐습니다 |

세션 2에서 코드만 되돌린 것은, 세션 1에서 고친 코드가 힌트가 되지 않게 하려는 것입니다. 지침 파일, `.habitree/`, 도구가 남긴 기억은 그대로 이어집니다. 실제로 프로젝트를 이어 쓸 때와 같습니다.

## 재기 전에 드러난 것: 고리가 끊겨 있었다

본 측정 전에 한 번씩 돌려 보니, 규칙이 자라는 고리가 세 군데서 끊겨 있었습니다.

1. **규칙을 더해도 AI 지침이 그대로였습니다.** `habitree rules add`는 규칙 DB와 RULES.md만 고쳤고, 다음 세션이 읽는 AGENTS.md는 손으로 다시 만들어야 했습니다. 이제 규칙을 더하거나 고치면 이미 있는 AI 지침의 생성 구역도 바로 고칩니다. 직접 고친 구역은 그대로 두고 알립니다.
2. **"바로잡으면 규칙으로 남긴다"는 지침 한 줄만으로는 남기지 않았습니다.** AI는 바로잡힌 코드만 고치고 끝냈고, 다음 세션은 같은 실수를 했습니다. 세션을 시작할 때 읽은 줄이 몇 턴 뒤 바로잡히는 순간에는 떠오르지 않았습니다. 원래 있던 정정 감지는 "아니", "틀렸어"처럼 불만이 드러나는 말만 봤고, 두 번째 정정부터 알렸습니다. 실제 정정은 "~하지 마", "대신", "~써야 해", "~하기로 했어"처럼 차분한 경우가 많습니다. 그래서 이런 말을 잡아 그 순간 AI에게 알리는 감지 규칙(`work.request.correction-to-rule`)을 더했습니다.
3. **알림을 받은 AI가 쓰는 법을 찾느라 헤맸습니다.** 범위와 관점 이름을 찾으려고 도움말과 비슷한 규칙 찾기를 열 번 가까이 돌렸고, 결국 구체적인 규칙 대신 일반 규칙에 지적만 붙였습니다. 알림에 바로 쓸 기본값과 "비슷한 규칙은 add가 알려 준다"를 적자, `habitree rules add` 한 번으로 끝났습니다.

## 결과

| 과제 | 갈래 | 세션 1 합격 | 바로잡음 | 규칙을 남김 | 다음 세션 합격 |
|---|---|---|---|---|---|
| reuse-helper | with | 1/3 | 2 | 2 | 2/3 |
| reuse-helper | without | 0/3 | 3 | 0 | 0/3 |
| money-rules | with | 0/3 | 3 | 3 | 3/3 |
| money-rules | without | 0/3 | 3 | 0 | 0/3 |

바로잡힌 흐름만 보면, with는 시키지 않았는데도 5번 모두 규칙을 남겼고 다음 세션 5번이 모두 합격했습니다. without은 6번 바로잡혀 그 자리에서는 6번 모두 고쳤지만, 남긴 것이 없어서 다음 세션 6번 모두 같은 실수를 되풀이했습니다. Claude Code의 자동 메모리는 두 갈래 모두 켜져 있었지만, 이번에는 어느 쪽도 쓰지 않았습니다.

AI가 남긴 규칙은 이런 것이었습니다.

- "파일 이름·주소용 글 변환(제목 정리 등)은 새로 짜지 않고 textkit.slugify()를 불러 쓴다."
- "금액 계산 결과는 money.js의 roundWon()으로 원 단위에 맞추고, Math.round 등을 직접 쓰지 않는다. 잘못된 입력(음수, 100을 넘는 비율, 모르는 종류)은 null을 돌려주거나 일반 Error를 던지지 않고 RangeError를 던진다."

비용(평균):

| | 바로잡는 턴 | 다음 세션 |
|---|---|---|
| reuse-helper with / without | $0.20 / $0.16 | $0.11 / $0.10 |
| money-rules with / without | $0.19 / $0.16 | $0.11 / $0.10 |

규칙을 남기는 데 바로잡을 때마다 약 $0.03~0.04가 더 들었습니다. 다음 세션의 비용은 거의 같았습니다. 다음 세션의 토큰도 평균 181K 대 177K, 183K 대 177K로 비슷했습니다. 다른 점은 with 쪽이 같은 비용으로 맞혔다는 것입니다. 그 작업 하나를 맞히는 데 든 비용으로 보면, without 쪽은 다시 틀려서 바로잡는 한 바퀴가 또 필요해 약 $0.26(첫 시도 $0.10 + 바로잡기 $0.16), with 쪽은 한 번에 맞혀 약 $0.11이었습니다.

## 알게 된 것

1. **규칙은 바로잡힌 그 순간에 남겨야 자랍니다.** 시작할 때 읽는 지침 한 줄로는 부족했고, 바로잡는 말이 온 그때의 알림이 차이를 만들었습니다.
2. **남긴 규칙은 비슷한 다른 과제에도 통했습니다.** 다음 세션의 과제는 처음과 다른 함수였는데, 규칙이 함수 이름과 하지 말 것을 구체적으로 적고 있어서 그대로 지켜졌습니다.
3. **효율은 되풀이되는 실수를 막는 데서 나옵니다.** 프로젝트 전체의 토큰을 크게 줄이는 것이 아니라, 한 번 바로잡은 실수에 드는 틀리고 고치는 한 바퀴를 다음부터 없애는 것입니다. 같은 실수가 자주 나올 프로젝트일수록 아끼는 양이 커집니다.
4. **운 좋게 맞힌 것은 이어지지 않습니다.** reuse-helper with의 한 번은 AI가 세션 1에서 스스로 slugify를 찾아 맞혔습니다. 바로잡을 일이 없었으니 규칙도 남지 않았고, 다음 세션에서는 직접 코드를 짰습니다. 규칙은 바로잡힐 때만 자랍니다.

## 한계와 다음에 잴 것

- 훅이 있는 도구(Claude Code)에서 잰 결과입니다. 지침 파일만 읽는 도구에서는, 시험 실행 한 번에서 AI가 규칙을 남기지 않았습니다. 그런 도구에서 고리를 잇는 방법은 아직 숙제입니다.
- 작은 과제 2개, 3번씩, Sonnet 하나, Windows 한 대입니다. 격리하지 않아 이 컴퓨터의 전역 지침이 두 갈래에 함께 들어갔습니다.
- 바로잡는 말은 미리 정한 문장입니다. 실제 사용자의 말은 더 다양해서, 감지 표현에 걸리지 않는 정정도 있을 수 있습니다.
- 원자료(`bench/results/`)는 이 컴퓨터의 경로와 대화가 들어 있어 올리지 않았습니다. `habitree`가 PATH에 있으면 같은 흐름을 다시 잴 수 있습니다: `python bench/grow.py reuse-helper --hooks --yes`.

---

## English

The [first measurement](2026-10-28-first-measurement.md) only looked at rules that were already in place. What the name Habitree promises, that a user's correction grows into a rule and keeps the next session from repeating the mistake, had to be measured separately. This is that measurement, and what we found and fixed while making it.

### Conditions

Two tasks: `reuse-helper` (does the agent reuse the existing `textkit.slugify`, Python) and `money-rules` (does it follow the team's rounding helper and error rule, JavaScript). In session 1 the agent gets task A. If it fails grading, it is corrected once in the same session with a plain sentence such as "Do not write new code to convert the title. textkit.py already has slugify(); call it and fix this." We deliberately did not say "remember this". Then only the code files are reset, and a new session in the same folder gets a similar task B (`draft_name(title)` or `splitBill(total, people)`). The with arm runs `habitree init --hooks` and starts with zero rules; the without arm has nothing installed; both may run `habitree`. Claude Sonnet with a $1 cap per call, three flows per task and arm, graded by scripts outside the working folder (task B also checks that the helper is called). One Windows machine without isolation. 12 flows (35 calls), about $4.6; two trial runs before that are excluded. Code is reset so that the fixed code from session 1 is not a hint; instruction files, `.habitree/` and anything the tools remembered carry over, as when a project continues.

### The loop was broken before we measured

Trial runs showed three breaks:

1. Adding a rule did not update the agent instructions: `habitree rules add` changed the rule DB and RULES.md, but AGENTS.md, which the next session reads, had to be regenerated by hand. Now adding or changing a rule refreshes the existing generated blocks right away, keeping and reporting hand-edited ones.
2. The line "record corrections as rules" in the instructions was not enough. The agent fixed the code and stopped, and the next session repeated the mistake. A line read at session start was not recalled at the moment of correction, several turns later. The existing correction detector only saw frustrated words ("no", "that's wrong") and spoke from the second correction on, while real corrections are often calm ("don't", "instead", "should use", "we decided"). So a detection rule (`work.request.correction-to-rule`) now catches these and tells the agent at that moment.
3. Once told, the agent searched for how to do it, running help and similarity searches nearly ten times to find scope and aspect names, and ended up attaching the feedback to a generic rule instead of writing a specific one. With ready-to-use defaults in the note and "add reports similar rules itself", it took a single `habitree rules add`.

### Results

| Task | Arm | Session 1 pass | Corrected | Rule recorded | Next session pass |
|---|---|---|---|---|---|
| reuse-helper | with | 1/3 | 2 | 2 | 2/3 |
| reuse-helper | without | 0/3 | 3 | 0 | 0/3 |
| money-rules | with | 0/3 | 3 | 3 | 3/3 |
| money-rules | without | 0/3 | 3 | 0 | 0/3 |

Among corrected flows, the with arm recorded a rule all 5 times without being asked, and all 5 next sessions passed. The without arm was corrected 6 times and fixed the code each time, but kept nothing, so all 6 next sessions repeated the mistake. Claude Code's auto memory was on in both arms, but neither used it this time. Recorded rules named the helper and what not to do, for example "Amounts are rounded to whole won with roundWon() from money.js, not Math.round; bad input (negative, a rate over 100, an unknown type) throws RangeError instead of returning null or a plain Error."

Recording cost about $0.03 to $0.04 extra per correction ($0.20 vs $0.16 and $0.19 vs $0.16 per correction turn). Next sessions cost about the same ($0.11 vs $0.10) with similar tokens (181K vs 177K, 183K vs 177K on average); the difference is that the with arm got it right. Counted as the cost of getting that one task right, the without arm needed another round of being wrong and corrected, about $0.26 (first try $0.10 plus correction $0.16), while the with arm got it right at once for about $0.11.

### What we learned

1. Rules grow only if they are recorded at the moment of correction. A line read at the start was not enough; the note at the moment of correction made the difference.
2. Recorded rules carried over to a similar but different task, because they named the function and what not to do.
3. The efficiency comes from stopping repeated mistakes. It does not cut a whole project's tokens by much; it removes, from then on, the round of being wrong and corrected that a mistake costs. The more often the same mistake would come back, the more it saves.
4. Luck does not carry over. In one with flow the agent found slugify on its own in session 1; with nothing to correct, no rule was recorded, and the next session wrote its own code. Rules grow only from corrections.

### Limits and next measurements

Measured on a tool with hooks (Claude Code). On a tool that only reads instruction files, a trial run showed the agent not recording the rule; closing the loop there is still open. Two small tasks, three flows each, one model, one Windows machine, no isolation. The corrections were fixed sentences; real users phrase corrections in more ways, and some will not match the detector. Raw data (`bench/results/`) contains local paths and conversations and is not published; with `habitree` on PATH, rerun with `python bench/grow.py reuse-helper --hooks --yes`.
