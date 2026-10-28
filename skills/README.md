# skills

AI가 필요할 때만 불러 읽는 짧은 절차서입니다. 지침 파일에 늘 싣기에는 길고, 그렇다고 빼 두면 잊히는 것들을 여기 두었습니다. Claude Code 플러그인으로 설치하면 `/habitree:<이름>`으로도 부를 수 있습니다.

- 마지막 갱신: 2026-10-28

| 스킬 | 언제 쓰나 |
|---|---|
| [work-cycle](work-cycle/SKILL.md) | 작업을 시작하거나 끝낼 때. 찾기, 있으면 쓰기, 없으면 만들기, 기록, 점검 |
| [feedback-to-rule](feedback-to-rule/SKILL.md) | 사용자가 결과를 바로잡거나, Habitree의 경고가 맞았다·틀렸다고 할 때 |
| [delegate](delegate/SKILL.md) | "알아서 해 줘"처럼 작업을 맡길 때. 범위를 되말하고, 경계를 지키고, 끝에 보고 |

다른 도구로도 옮겨 쓸 수 있게 Agent Skills 표준의 기본 칸(`name`, `description`, `license`)만 썼습니다. 어느 말로 요청해도 불리도록 설명에는 한국어와 영어 표현을 함께 넣었고, 본문은 짧게 두었습니다. 자세한 배경은 [docs/spec/](../docs/spec/)에 있습니다.

---

## English

Short procedures the agent loads only when needed: too long to keep in the instruction files all the time, too important to leave out. With the Claude Code plugin installed they can also be called as `/habitree:<name>`.

| Skill | When |
|---|---|
| [work-cycle](work-cycle/SKILL.md) | Starting or finishing work: find, reuse, build, record, check |
| [feedback-to-rule](feedback-to-rule/SKILL.md) | When the user corrects the work, or says a Habitree warning was right or wrong |
| [delegate](delegate/SKILL.md) | When a task is handed over ("just do it"): restate the scope, keep the boundaries, report at the end |

Only the standard Agent Skills fields (`name`, `description`, `license`) are used, so the skills can move to other tools. Descriptions carry both Korean and English phrases so either language triggers them, and the bodies stay short. The background is in [docs/spec/](../docs/spec/).
