# 첫 측정 (2026-10-28)

Habitree가 실제로 도움이 되는지, 그리고 Habitree 자신이 짐이 되지 않는지 처음으로 재 본 기록입니다. 결과를 보고 지침을 걷어내고 다시 재기를 여러 번 되풀이했고, 그 과정에서 v0.8의 방향이 정해졌습니다.

- [English](#english)

## 조건

| 항목 | 값 |
|---|---|
| 과제 | 작은 과제 3개: `reuse-helper`(이미 있는 함수를 다시 쓰는가, Python), `money-rules`(팀이 정한 규칙을 지키는가, JavaScript), `find-in-tree`(여러 폴더에서 고칠 곳을 찾는가, 과제 규칙 없음, Python) |
| 갈래 | with: Habitree를 깐 프로젝트(과제에 정한 규칙이 있으면 그 규칙 포함) / without: 아무것도 깔지 않은 같은 프로젝트 |
| 모델 | Claude Sonnet(`claude -p --model sonnet`), 실행당 한도 $1 |
| 반복 | 회차마다 갈래당 3번 |
| 채점 | 작업 폴더 밖의 채점 스크립트, 종료 코드 0이 합격 |
| 환경 | Windows 개발 컴퓨터 한 대. 격리하지 않아서 이 컴퓨터의 전역 설정과 전역 CLAUDE.md가 두 갈래에 똑같이 들어갔다. 훅과 플러그인 없이 지침 파일만 비교했다 |
| 규모 | 66번 실행, 공개 단가로 어림하면 약 $8 |

## 회차별로 바꾼 것

| 회차 | with 갈래의 AI 지침 |
|---|---|
| 2 | v0.7: 여섯 단계 작업 순환 + 필수 규칙 요약(약 1.9KB) |
| 3 | 걷어낸 판 1: 세 줄(있는 것 먼저 찾기, 검증 돌리기, 바로잡은 것은 규칙으로) + 이 프로젝트의 규칙만 |
| 4 | 걷어낸 판 2: 색인 안내는 파일이 많을 때만, 검증 줄은 검증 명령이 등록됐을 때만 |
| 5 | 걷어낸 판 3: 피드백 줄을 "바로잡으면 그때"라는 조건문으로 |
| 6 | 걷어낸 판 4: 늘 읽는 지침에서 명령 이름을 빼고, 방법은 RULES.md 머리말로 |

1회차는 과제 문장이 모호해 find-in-tree가 두 갈래 모두 다르게 해석했습니다. 그래서 문장을 고치고 결과에서 뺐습니다.

## 결과

합격률(모든 회차를 합친 것):

| 과제 | with | without |
|---|---|---|
| reuse-helper | 13/13 | 0/7 |
| money-rules | 16/16 | 0/7 |
| find-in-tree | 15/15 | 6/6 |

평균 토큰(실행 하나당, 반올림):

| 판 | reuse-helper | money-rules | find-in-tree |
|---|---|---|---|
| without(2회차 / 4회차) | 223K / 178K | 176K / 177K | 192K / 179K |
| v0.7 지침(2회차) | 248K | 205K | 233K |
| 걷어낸 판 1(3회차) | 150K | 228K | 213K |
| 걷어낸 판 2(4회차) | 179K | 211K | 212K |
| 걷어낸 판 3(5회차) | - | 211K | 229K |
| 걷어낸 판 4(6회차) | 180K | 198K | 197K |

같은 시간대에 두 갈래를 함께 돌린 회차로 비교하면, without 대비 v0.7 지침은 토큰이 11%, 16%, 21% 더 들었습니다(2회차). 걷어낸 판은 1%, 12%, 10% 더 들었습니다(6회차, 4회차 without 기준). 반복이 3번뿐이고 실행마다 편차가 커서(표준편차 최대 약 ±27K) 10% 안팎의 차이는 확정적이지 않습니다.

## 알게 된 것

1. **가치는 그 프로젝트에서 받은 피드백 규칙에서 나왔습니다.** 규칙이 있는 두 과제에서 with는 29번 모두 합격했고, without은 14번 모두 실패했습니다. without은 파일 하나만 읽고 바로 고쳐서 토큰은 적게 썼지만, 이미 있는 함수를 다시 만들거나 팀 규칙을 몰랐습니다.
2. **일반 절차는 정답률을 올리지 못하고 비용만 더했습니다.** 과제 규칙이 없는 find-in-tree에서 v0.7 지침은 합격률이 같은 채 토큰 21%, 시간 86%가 더 들었습니다. AI가 작은 수정에도 변경 기록을 읽고 고치고 전체 점검을 돌렸기 때문입니다.
3. **작은 프로젝트에서는 색인 안내가 한 단계를 늘렸습니다.** AI가 `habitree map find`를 쓴 뒤에도 결국 grep과 Read를 했습니다. 그래서 파일이 150개 이상일 때만 안내합니다. 큰 프로젝트에서의 효과는 아직 재지 않았습니다.
4. **늘 읽는 지침에 명령 이름이 보이면 AI는 그 도구를 살펴봤습니다.** 5회차에서 6번 중 4번이 시작하자마자 `habitree rules list`나 `--help`를 돌렸습니다. 명령 이름을 빼자(6회차) 이런 탐색이 사라졌습니다. 대신 지침이 가리킨 RULES.md를 한 번 읽습니다.
5. **남은 차이는 대부분 일을 제대로 하는 데 든 비용이었습니다.** 규칙대로 도우미 파일을 읽고 다시 쓰고, 몇 번은 스스로 결과를 시험해 봤습니다.

## 그래서 정한 것

- AI가 매번 읽는 지침은 걷어낸 판을 기본으로 합니다(`export.style: lean`). 있는 것을 먼저 찾으라는 한 줄, 바로잡은 것은 규칙으로 남기라는 한 줄, 그리고 이 프로젝트의 규칙만 싣습니다. 검증 명령과 색인 안내는 해당될 때만 붙습니다.
- 새 프로젝트는 규칙 0개로 시작합니다. 일반 규칙은 패키지에서 읽어 기계 점검과 훅이 씁니다.
- 늘 읽는 지침에는 도구 명령 이름을 쓰지 않습니다. 쓰는 법은 필요할 때 보는 곳(RULES.md 머리말, 스킬, 훅 알림)에 둡니다.

## 한계와 다음에 잴 것

- 작은 과제 3개, 회차마다 3번, Sonnet 하나, Windows 한 대에서 잰 결과입니다. 큰 저장소, 다른 모델, 긴 작업에서는 다를 수 있습니다.
- 격리하지 않아 이 컴퓨터의 전역 지침이 두 갈래에 함께 들어갔습니다.
- 3·5·6회차는 with 갈래만 돌려 다른 시간대의 without과 비교했습니다.
- 훅과 플러그인(작업 중 알림, 위임)은 이번 측정에 들어가지 않았습니다.
- 원자료(`bench/results/`)는 이 컴퓨터의 경로와 대화가 들어 있어 올리지 않았습니다. 같은 과제와 명령으로 누구나 다시 잴 수 있습니다: `habitree bench run bench/<과제> --runner claude --model sonnet --reps 3 --yes`.

---

## English

The first measurement of whether Habitree actually helps, and whether Habitree itself becomes a burden. We trimmed the agent instructions based on the results and measured again several times, and that loop set the direction of v0.8.

### Conditions

Three small tasks: `reuse-helper` (does the agent reuse an existing function, Python), `money-rules` (does it follow rules the team set, JavaScript) and `find-in-tree` (does it find the place to change among folders, no task rules, Python). The with arm is the project with Habitree installed (including the task's rule when it has one); the without arm is the same project with nothing installed. Claude Sonnet (`claude -p --model sonnet`) with a $1 cap per run, three runs per arm per round, graded by a script outside the working folder (exit 0 passes). One Windows development machine with no isolation, so the machine's global settings and global CLAUDE.md went into both arms equally; only instruction files were compared, without hooks or the plugin. 66 runs in total, about $8 at public prices.

Round 2 used the v0.7 instructions (six-step cycle plus a must-rule summary, about 1.9 KB). Rounds 3 to 6 progressively trimmed them: three lines plus this project's own rules; the index hint only for projects with many files and the verify line only when verify commands exist; the feedback line phrased as a condition; and finally no command names in the always-read instructions, with the how-to moved to the head of RULES.md. Round 1 is excluded because an ambiguous task sentence was read differently by both arms; the sentence was fixed.

### Results

Pass counts over all rounds: `reuse-helper` 13/13 with vs 0/7 without, `money-rules` 16/16 vs 0/7, `find-in-tree` 15/15 vs 6/6. Average tokens per run are in the Korean table above. Comparing rounds where both arms ran in the same time window, the v0.7 instructions used 11%, 16% and 21% more tokens than without (round 2), and the trimmed version 1%, 12% and 10% more (round 6 against the round 4 without arm). With only three runs and large spread (standard deviation up to about ±27K), differences around 10% are not conclusive.

### What we learned

1. The value came from the feedback rules the project had received: on the two tasks with rules, with passed all 29 runs and without failed all 14. Without used fewer tokens by reading one file and editing at once, but rebuilt existing functions or missed the team's rules.
2. Generic procedure added cost without raising accuracy: on `find-in-tree`, the v0.7 instructions used 21% more tokens and 86% more time for the same pass rate, because the agent read and updated the change log and ran a full check even for a small fix.
3. In a small project the index hint added a step: after `habitree map find` the agent still used grep and Read. The hint now appears only for projects with 150 or more files. The effect in large projects is not measured yet.
4. Command names in always-read instructions made the agent explore the tool: in round 5, four of six runs started with `habitree rules list` or `--help`. Removing the names (round 6) stopped this; the agent now reads the referenced RULES.md once instead.
5. Most of the remaining difference was the cost of doing the job right: reading and reusing the helper the rule pointed to, and sometimes testing the result.

### Decisions

The trimmed instructions are now the default (`export.style: lean`): one line to look for what exists first, one line to record corrections as rules, and this project's own rules, with the verify and index lines only when they apply. New projects start with zero rules; generic rules are read from the package for checks and hooks. Command names stay out of always-read instructions; how-to lives where it is read when needed (the head of RULES.md, skills, hook notes).

### Limits and next measurements

Three small tasks, three runs per round, one model and one Windows machine; large repositories, other models and long tasks may differ. No isolation, so the machine's global instructions were present in both arms. Rounds 3, 5 and 6 ran only the with arm and were compared with a without arm from another time window. Hooks and the plugin were not part of this measurement. The raw data (`bench/results/`) contains local paths and conversations and is not published; anyone can rerun the same tasks with `habitree bench run bench/<task> --runner claude --model sonnet --reps 3 --yes`.
