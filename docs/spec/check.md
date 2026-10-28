# 점검 항목

`habitree check`가 보고하는 항목입니다. AI에게 판단을 맡기는 점검은 비용이 들고 할 때마다 결과가 달라질 수 있어서, Habitree의 점검은 모두 정해진 방식으로만 확인합니다. 항목 id는 바뀌지 않는 약속이라 다른 구현도 같은 id를 씁니다([적합성 시험](conformance.md)).

| id | 등급 | 찾는 것 |
|---|---|---|
| `map.missing-folder` | 오류 | 지도 파일(`docs.map`)이 없거나, 최상위 폴더가 지도에서 링크되지 않음 |
| `map.folder-readme` | 경고(설정으로 바꿈) | 최상위 폴더에 README.md가 없음. `docs.folder_readme`를 `"error"`, `"warn"`, `false` 중에서 고름 |
| `docs.updated` | 경고, 알림 | 지도와 폴더 README에 '마지막 갱신'(`docs.updated_labels`) 날짜가 없으면 경고, `docs.stale_days`보다 오래되면 알림 |
| `docs.link` | 오류 | Markdown 상대 링크의 대상이 없거나, `.md` 대상의 제목 앵커가 없음. 코드 안 링크와 웹 주소는 보지 않음 |
| `docs.log` | 경고 | 변경 기록 파일(`docs.log`)이 없음 |
| `docs.instructions-size` | 오류, 경고 | AGENTS.md가 `docs.agents_md_max_bytes`(32768)를 넘으면 오류, CLAUDE.md가 `docs.claude_md_max_lines`(200)를 넘으면 경고 |
| `docs.import` | 오류 | AGENTS.md·CLAUDE.md의 `@경로` 대상이 없음 |
| `docs.hidden-unicode` | 오류 | 지침 파일과 규칙 DB 안의 방향 바꿈·폭 없는 제어 문자 |
| `docs.home-path` | 경고 | 지침 파일에 박힌 개인 폴더 경로(`C:\Users\…`, `/Users/…`, `/home/…`) |
| `rules.invalid` | 오류 | 규칙 DB가 스키마나 뜻(없는 범위·관점·상황, id 중복)에 맞지 않음 |
| `rules.doc-stale` | 경고 | RULES.md(`rules.doc`)가 규칙 DB에서 만든 결과와 다름 |
| `rules.duplicate` | 경고 | 같은 뜻으로 보이는 규칙 쌍 |
| `rules.noisy` | 경고, 알림 | 감지 규칙에 '틀렸다' 반응이 25%를 넘으면 경고, 10% 이상이면 알림(보호관찰) |
| `rules.auto.<규칙 id>` | 오류, 경고 | 규칙의 자동 검사(`check.run`) 위반. 필수 규칙이면 오류, 권장이면 경고 |
| `generated.edited` | 알림 | 생성 구역을 사람이 직접 고침(`.habitree/manifest.json`과 다름) |
| `paths.collision` | 오류, 경고 | 대소문자나 NFC·NFD만 다른 파일 이름(오류), git에 NFD로 등록된 이름(경고) |
| `git.precompose` | 경고 | macOS에서 git `core.precomposeUnicode`가 꺼져 있음 |
| `models.deprecated` | 경고 | 쓰는 모델(기본 회사의 등급 모델, `models.agents`에 묶인 에이전트 파일의 model)이 `models.deprecation_days`(90) 안에 단종되거나 이미 단종됨. 설정에 `models` 절이 없으면 보지 않음 |
| `models.floor` | 오류 | 에이전트 파일의 model(같은 등급이면 강도까지)이 그 작업의 하한(필수 규칙의 `cell`)보다 낮거나, 대응표를 읽지 못함 |
| `models.price-stale` | 알림 | 쓰는 회사의 가격·모델 확인일이 `models.price_stale_days`(90)보다 오래됨 |
| `custom.<id>` | 설정대로 | 설정 `checks.custom`의 명령이 0이 아닌 코드로 끝남 |

## 설정

```json
{
  "docs": {"map": "README.md", "log": "LOG.md", "folder_readme": "warn", "stale_days": 60},
  "checks": {
    "disable": ["docs.updated"],
    "custom": [{"id": "lint", "cmd": ["npm", "run", "lint"], "level": "warn"}]
  },
  "exclude": ["node_modules", "dist"]
}
```

git이 있으면 `.gitignore`를 따라 파일을 고르고, 없으면 `exclude`에 적은 것을 뺀 전체를 봅니다. 명령줄의 `--only`와 `--skip`은 id 앞부분으로 항목을 고르고, `--no-auto`는 자동 검사를 건너뜁니다.

---

## English

The items reported by `habitree check`. Checks that ask an AI to judge cost money and can answer differently each time, so every Habitree check is deterministic. Item ids are a stable contract that other implementations use too ([conformance](conformance.md)).

| id | Level | What it finds |
|---|---|---|
| `map.missing-folder` | error | The map file (`docs.map`) is missing, or a top-level folder is not linked from it |
| `map.folder-readme` | warn (configurable) | A top-level folder has no README.md; set `docs.folder_readme` to `"error"`, `"warn"` or `false` |
| `docs.updated` | warn, info | No "last updated" date (`docs.updated_labels`) in the map or a folder README (warn), or older than `docs.stale_days` (info) |
| `docs.link` | error | A relative Markdown link points nowhere, or a heading anchor is missing in an `.md` target; code spans and URLs are skipped |
| `docs.log` | warn | The change log (`docs.log`) is missing |
| `docs.instructions-size` | error, warn | AGENTS.md over `docs.agents_md_max_bytes` (32768) is an error; CLAUDE.md over `docs.claude_md_max_lines` (200) is a warning |
| `docs.import` | error | An `@path` import in AGENTS.md or CLAUDE.md points nowhere |
| `docs.hidden-unicode` | error | Bidi or zero-width control characters in instruction files or the rule DB |
| `docs.home-path` | warn | A hard-coded personal home path in an instruction file |
| `rules.invalid` | error | The rule DB breaks the schema or its own references (unknown scope, aspect or context, duplicate id) |
| `rules.doc-stale` | warn | RULES.md (`rules.doc`) differs from what the rule DB generates |
| `rules.duplicate` | warn | A pair of rules that look the same |
| `rules.noisy` | warn, info | A detection rule with more than 25% "wrong" votes (warn) or at least 10% (info, probation) |
| `rules.auto.<rule id>` | error, warn | An automatic check (`check.run`) failed: error for must rules, warning for should rules |
| `generated.edited` | info | A managed block was edited by hand (differs from `.habitree/manifest.json`) |
| `paths.collision` | error, warn | File names that differ only by case or NFC/NFD (error); names stored in git as NFD (warn) |
| `git.precompose` | warn | On macOS, git `core.precomposeUnicode` is off |
| `models.deprecated` | warn | A model in use (the default vendor's tier models, or the model in an agent file bound by `models.agents`) retires within `models.deprecation_days` (90) or already has; skipped without a `models` section |
| `models.floor` | error | An agent file's model (and effort, within the same tier) is below the task's floor (the `cell` of a must rule), or the vendor table cannot be read |
| `models.price-stale` | info | The vendor's prices and models were checked longer ago than `models.price_stale_days` (90) |
| `custom.<id>` | as configured | A command in `checks.custom` exited with a non-zero code |

### Configuration

The JSON above shows the main settings. With git, files are chosen according to `.gitignore`; without it, everything except `exclude` is scanned. On the command line, `--only` and `--skip` take id prefixes and `--no-auto` skips automatic checks.
