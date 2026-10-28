# 규칙 DB 형식

규칙 DB는 JSON 파일 하나입니다(기본 위치 `.habitree/rules.json`). 기계가 읽는 정의는 [rules.schema.json](../../src/habitree/data/schema/rules.schema.json)(JSON Schema 2020-12)이고, 이 문서는 각 칸이 왜 있는지를 설명합니다.

규칙을 글 한 덩어리가 아니라 칸으로 나눠 둔 이유는 두 가지입니다. 필요한 규칙만 골라 읽을 수 있어야 하고, 규칙마다 언제 누가 왜 그렇게 말했는지가 남아 있어야 나중에 고치거나 버릴 수 있기 때문입니다.

## 맨 위 칸

| 칸 | 뜻 |
|---|---|
| `scopes` | 범위 이름과 설명. `a/b`는 `a` 아래 범위이고 `a`의 규칙을 물려받습니다 |
| `parents` | 최상위 범위의 상위. 적지 않으면 `global` |
| `aspects` | 관점 이름과 설명(절차, 구조, 품질 등) |
| `contexts` | 상황 태그와 설명(`task:implement` 등) |
| `packs` | 들어온 기본 꾸러미와 버전 |
| `rules` | 규칙 목록 |

글이 들어가는 칸은 문자열 하나이거나 `{"ko": "…", "en": "…"}`입니다. 기본 꾸러미 규칙은 두 언어를 함께 갖고 있어서 설정한 언어로 보여 줄 수 있습니다.

## 규칙 하나

| 칸 | 뜻 |
|---|---|
| `id` | 고유 이름. 기본값은 `범위.낱말-낱말`이고 한글 낱말도 됩니다 |
| `scope`, `aspect`, `when` | 범위, 관점, 상황 태그. `when`이 비어 있으면 늘 적용됩니다 |
| `level` | `should`(권장) 또는 `must`(필수) |
| `rule`, `why` | 지킬 것과 그 이유. 이유가 있어야 나중에 규칙이 맞는지 판단할 수 있습니다 |
| `check` | `type`은 `review`(눈으로) 또는 `auto`(자동), `how`는 확인 방법, `run`은 자동 검사 정의 |
| `feedback` | `{date, note, ref}` 목록. 지적이 쌓인 기록 |
| `history` | `{date, change}` 목록. 규칙이 바뀐 기록 |
| `status` | `active`, `paused`, `retired`. 폐기한 규칙도 지우지 않고 이유와 함께 남깁니다 |
| `origin`, `origin_hash` | 기본 꾸러미에서 온 규칙의 출처와 원래 내용의 해시. 사용자가 고쳤는지 알아보는 데 씁니다 |
| `detect`, `message`, `votes`, `on_delegate` | 작업 중 감지 규칙에 쓰는 칸(v0.2) |
| `cell`, `max_cell`, `verify` | 모델 배분 규칙에 쓰는 칸(v0.3) |
| `retire_when` | 바깥 사정이 바뀌면 다시 볼 조건 |

## 자동 검사 `check.run`

규칙 사다리의 '자동 검사' 칸입니다. 프로젝트가 어떤 언어로 짜여 있든 같은 방식으로 씁니다.

| 칸 | 동작 |
|---|---|
| `cmd` | 명령을 셸 없이 실행하고, 종료 코드 0이면 합격 |
| `forbid` + `in` | `in` 글롭에 맞는 글 파일에 정규식이 나오면 위반 |
| `require` + `in` | 맞는 파일 어디에도 정규식이 없으면 위반 |
| `max_lines` + `in` | 줄 수가 한도를 넘는 파일마다 위반 |
| `timeout` | 명령의 시간 한도(초, 기본 120) |

위반은 `rules.auto.<규칙 id>`로 보고됩니다. 필수 규칙이면 오류, 권장 규칙이면 경고입니다. 글롭은 `**`를 지원하고, 경로는 NFC로 맞춰 비교합니다.

## 예전 형식

Habitree가 나오기 전 Open Prompt에서 쓰던 형식(같은 칸에서 `packs`, `detect` 등이 없는 것)도 그대로 읽습니다. 다른 위치의 DB는 `habitree rules --db 경로 brief …`로 다룰 수 있습니다.

---

## English

The rule DB is a single JSON file (default `.habitree/rules.json`). The machine definition is [rules.schema.json](../../src/habitree/data/schema/rules.schema.json) (JSON Schema 2020-12); this document explains why each field exists.

Rules are split into fields rather than kept as prose for two reasons: the agent must be able to read only the rules it needs, and every rule must keep a record of who said what and why, so it can be fixed or dropped later.

### Top level

| Field | Meaning |
|---|---|
| `scopes` | Scope names and descriptions. `a/b` sits under `a` and inherits its rules |
| `parents` | Parent of a top-level scope; `global` if omitted |
| `aspects` | Aspect names and descriptions (process, structure, quality, …) |
| `contexts` | Context tags and descriptions (`task:implement`, …) |
| `packs` | Bundled packs merged in, with versions |
| `rules` | The rules |

Text fields hold either a single string or `{"ko": "…", "en": "…"}`. Bundled rules carry both languages so they can be shown in the configured one.

### A rule

| Field | Meaning |
|---|---|
| `id` | Unique id; defaults to `scope.word-word` (Korean words are fine) |
| `scope`, `aspect`, `when` | Scope, aspect and context tags; an empty `when` means always |
| `level` | `should` or `must` |
| `rule`, `why` | What to do and why. The reason is what lets you judge the rule later |
| `check` | `type` is `review` or `auto`, `how` says how to check, `run` defines an automatic check |
| `feedback` | List of `{date, note, ref}`: the feedback that built the rule |
| `history` | List of `{date, change}`: how the rule changed |
| `status` | `active`, `paused` or `retired`. Retired rules stay, with the reason |
| `origin`, `origin_hash` | Pack origin and a hash of the original content, used to detect user edits |
| `detect`, `message`, `votes`, `on_delegate` | Fields for in-flight detection rules (v0.2) |
| `cell`, `max_cell`, `verify` | Fields for model allocation rules (v0.3) |
| `retire_when` | When to revisit the rule if outside conditions change |

### Automatic checks: `check.run`

This is the "automatic check" rung of the ladder, and it works the same whatever language the project uses.

| Field | Behavior |
|---|---|
| `cmd` | Runs the command without a shell; exit 0 passes |
| `forbid` + `in` | Violation if the regex appears in text files matching the `in` globs |
| `require` + `in` | Violation if no matching file contains the regex |
| `max_lines` + `in` | One violation per file over the line limit |
| `timeout` | Command time limit in seconds (default 120) |

Violations are reported as `rules.auto.<rule id>`: errors for must rules, warnings for should rules. Globs support `**`, and paths are compared in NFC.

### The earlier format

The format Open Prompt used before Habitree (the same fields, without `packs`, `detect` and so on) is read as is. Use `habitree rules --db PATH brief …` for a DB in another location.
