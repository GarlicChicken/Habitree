# 바뀐 것

새 버전을 위에 씁니다.

## 0.1.0 (2026-10-28)

첫 버전입니다. 피드백을 규칙으로 쌓고, 프로젝트의 지도와 문서가 실제와 맞는지 확인하는 기반을 만들었습니다.

- `habitree init`: 설정, 규칙 DB(기본 꾸러미 `base`의 규칙 12개), RULES.md, AGENTS.md·CLAUDE.md 생성 구역, README 지도 초안, LOG.md를 만듭니다. 다시 실행하면 사용자가 고치지 않은 규칙만 새것으로 바꿉니다.
- `habitree rules`: 범위·관점·상황으로 규칙을 꺼내고(`brief`, 글자 예산), 같은 뜻 규칙을 먼저 확인한 뒤 더하며(`add`), 지적을 쌓고(`hit`, `miss`), 고치고 내리고 쉬고 폐기합니다.
- `habitree check`: 지도, 링크와 한글 앵커, 갱신일, 지침 크기와 `@import`, 숨은 유니코드, 개인 경로, 규칙 DB, 규칙의 자동 검사, 생성 구역 수정, NFC·대소문자 충돌을 확인합니다. `--json`을 지원합니다.
- `habitree export`: 규칙 DB에서 AGENTS.md·CLAUDE.md 생성 구역을 다시 만들고, 사람이 고친 구역은 그대로 둡니다.
- 명세 문서, JSON Schema, 적합성 시험 6사례, Windows·macOS·Linux CI.

---

## English

Newest first.

### 0.1.0 (2026-10-28)

The first release: the groundwork for growing feedback into rules and for checking that a project's map and docs match reality.

- `habitree init` installs settings, the rule DB (12 rules from the bundled `base` pack), RULES.md, managed blocks in AGENTS.md and CLAUDE.md, a draft README map and LOG.md. Rerunning it updates only the rules you have not edited.
- `habitree rules` pulls rules by scope, aspect and context (`brief`, with a size budget), checks for rules with the same meaning before adding one (`add`), records feedback (`hit`, `miss`), and edits, demotes, pauses or retires rules.
- `habitree check` covers the map, links and Korean heading anchors, last-updated dates, instruction size and `@import`, hidden Unicode, personal paths, the rule DB, automatic rule checks, edited managed blocks and NFC/case collisions, with `--json` output.
- `habitree export` regenerates the managed blocks in AGENTS.md and CLAUDE.md from the rule DB and keeps blocks edited by hand.
- Specification documents, JSON Schema, six conformance cases and CI on Windows, macOS and Linux.
