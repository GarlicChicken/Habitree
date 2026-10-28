# 코드 색인과 MCP 서버

`habitree map`은 프로젝트의 함수, 클래스, 모듈, 문서 구역을 모은 색인을 만들고, `habitree mcp`는 그 색인과 규칙·점검을 AI 도구가 부를 수 있는 도구로 내놓습니다.

- [English](#english)

## 왜 색인이 필요한가

작업 순환의 첫 단계는 '찾기'입니다. 만들기 전에 이미 있는 것을 찾는 단계입니다. 지금까지 Habitree가 이 단계에 준 것은 사람이 쓴 README 지도뿐이었습니다. 지도는 폴더를 알려 주지만 그 안에 어떤 함수가 있는지는 알려 주지 않습니다. 그래서 AI는 있는 함수를 모른 채 비슷한 것을 새로 만들거나, 찾으려고 파일을 통째로 여러 번 읽습니다. 앞의 것은 같은 코드가 두 벌이 되는 문제이고, 뒤의 것은 토큰이 드는 문제입니다.

색인은 이름, 시그니처, 첫 줄 설명만 모읍니다. AI는 몸통을 읽기 전에 목록부터 보고, 필요한 것만 엽니다. 목록도 한꺼번에 주지 않고 글자 예산 안에서 중요한 것부터 줍니다. 목표는 '먼저 찾게 하기'이고, 토큰을 아끼는 것은 그 결과입니다.

색인이 있어도 AI가 부르지 않으면 소용없습니다. 그래서 같은 기능을 명령줄(`habitree map find`)과 MCP 도구(`map_find`) 두 곳에 두고, 도구 설명과 서버 안내문에 '새로 만들기 전에 먼저 부른다'를 적었습니다.

## 무거운 도구 없이 간 이유와 한계

코드 검색에는 벡터 DB와 임베딩, 언어 서버(LSP), tree-sitter 같은 강한 도구가 있습니다. 기본 설치에는 이것들을 넣지 않았습니다.

- 벡터 DB와 임베딩은 API 키, 외부 서비스, 비용이 들고 코드가 컴퓨터 밖으로 나갈 수 있습니다.
- 언어 서버는 언어마다 서버와 그 런타임을 설치하고 띄워 두어야 합니다.
- tree-sitter는 정확하지만 판이 바뀔 때 설치가 자주 깨집니다.

Habitree는 Python 표준 라이브러리만으로 돌고, 어떤 언어의 프로젝트에도 설치 없이 같은 명령으로 쓰는 것을 먼저 지킵니다. 그 대가로 생기는 한계는 숨기지 않습니다.

- Python 밖의 언어는 줄 단위 정규식으로 뽑으므로 결과가 대략입니다. 여러 줄에 걸친 시그니처, 매크로, 들여쓰기로 블록을 나누는 문법에서 놓치거나 끝 줄을 틀릴 수 있습니다. 결과마다 정확(`ast`)인지 대략(패턴)인지 표시합니다.
- 참조는 이름 단위로 셉니다. 타입을 풀지 않으므로 이름이 같은 다른 함수가 섞입니다.
- 실행 중에 만들어지는 이름(동적 등록, 문자열로 부르기)은 보지 못합니다.
- 예산은 글자 수입니다. 토큰 수가 아니고, 한국어는 글자 하나에 드는 토큰이 영어·코드와 다릅니다.

다른 도구들이 내세우는 토큰 절감 수치는 대부분 만든 사람이 직접 잰 좁은 조건의 결과입니다. 조건을 공개한 측정에서는 토큰은 줄었지만 정답률이 같거나 파일을 직접 읽을 때보다 낮은 경우가 있었고, 도구가 실제로 불리지 않은 측정을 스스로 거둬들인 사례도 있었습니다. 그래서 이 문서는 절감 수치를 적지 않습니다. 효과는 같은 과제를 켬·끔으로 되풀이하는 측정(`bench`, 예정)으로 재고, 조건과 함께 공개합니다.

## 구조: 언어와 무관한 공통 기반 위에 언어별 패턴

분석 대상은 어떤 언어든 같아야 합니다. 그래서 두 층으로 나눴습니다.

| 층 | 하는 일 | 어디에 |
|---|---|---|
| 공통 기반 (모든 언어) | 파일 목록(git이 있으면 `.gitignore`를 따름), 언어 판정(언어표 375개), 줄 수와 코드 줄 수, sha256, git 변경 기록, 창 단위 글 중복, Markdown 제목 | `mapper/langs.py`, `index.py`, `dupes.py`, `churn.py`, [languages.json](../../src/habitree/data/languages.json) |
| 언어별 심볼 | Python은 `ast`(정확). 그 밖의 언어는 패턴표(대략): JavaScript·TypeScript, Go, Rust, Java·C#·Groovy, Kotlin, Scala, Swift, C·C++·Objective-C, Ruby, PHP, Shell, PowerShell, Lua, Perl, R, Elixir, Dart, SQL, Markdown | `mapper/extract.py`, [symbols.json](../../src/habitree/data/symbols.json) |

어느 추출기를 쓰든 같은 심볼 레코드를 냅니다. 그래서 순위, 찾기, 중복, MCP 코드는 언어를 몰라도 됩니다.

| 칸 | 뜻 |
|---|---|
| `name`, `kind` | 이름과 종류(function, method, class, struct, interface, const, section …) |
| `line`, `end`, `start` | 정의 줄, 끝 줄, 장식자를 포함한 시작 줄(있을 때) |
| `sig` | 시그니처 한 줄. 상수는 이름(과 타입)까지만 싣고 값은 싣지 않습니다 |
| `doc` | 첫 줄 설명(docstring이나 바로 위 주석) |
| `parent` | 감싼 클래스·구조체·impl 등 |
| `body` | 몸통 해시(공백·주석을 지운 의미 있는 줄이 3줄 이상일 때). 중복 찾기에 씁니다 |

### 언어를 더하는 법

코드를 고치지 않고 데이터 두 곳만 고칩니다.

1. **언어표 한 줄.** `data/languages.json`에 확장자·파일 이름·주석 표시가 없으면 더합니다. 이것만으로 언어 판정, 줄 수, 글 중복, 변경 기록이 그 언어에 돕니다. 표는 scc의 것을 가져왔습니다([NOTICE.md](../../NOTICE.md)).
2. **패턴 묶음 하나.** `data/symbols.json`의 `groups`에 묶음을 더합니다. 줄마다 위에서부터 정규식을 맞춰 처음 맞은 것을 씁니다.
3. **시험 하나.** `tests/test_map.py`에 짧은 예제와 기대하는 심볼을 더합니다.

| 묶음 칸 | 뜻 |
|---|---|
| `languages` | 언어표의 언어 이름 목록 |
| `block` | 끝 줄을 찾는 법: `brace`(중괄호 깊이), `indent`(들여쓰기), `end`(같은 들여쓰기의 `end`), `heading`(같거나 높은 단계의 다음 제목), `line`(그 줄만) |
| `extractor` | `ast`면 Python 추출기를 먼저 쓰고, 문법 오류면 패턴으로 물러섭니다 |
| `fences`, `refs` | 코드 울타리 안 건너뛰기, 참조 이름 세기(기본 켬) |
| `patterns[].re` | Python `re` 문법. `(?P<name>…)`은 꼭, `(?P<kind>…)`, `(?P<parent>…)`, `(?P<level>…)`은 있으면 씁니다 |
| `patterns[].kind`, `kinds` | 종류 기본값, 잡은 종류 이름을 바꾸는 표(`{"def": "function"}`) |
| `patterns[].inside`, `member`, `top` | 이 종류 안에서만, 그 몸통 바로 아래 깊이에서만, 아무것에도 안 싸였을 때만 맞춥니다. 메서드 안의 함수 호출을 정의로 잘못 잡지 않게 합니다 |
| `patterns[].flags`, `block` | `i`면 대소문자 무시, 이 패턴만 다른 끝 찾기 |

맨 위의 `text_only`(코드가 아닌 문서·데이터 형식), `not_names`(이름이 될 수 없는 낱말), `ref_stop`(참조로 세지 않을 낱말), `common_names`(순위에서 약하게 볼 흔한 이름)도 데이터입니다.

## 색인 파일

색인은 `.habitree/state/map.json` 하나이고 커밋하지 않습니다. 파일 키는 루트 기준 NFC 상대 경로(`/`)라 Windows·macOS·Linux에서 같습니다. 파일마다 언어, 줄 수, 코드 줄 수, 크기, mtime, sha256, 추출기, 심볼, 참조 이름 수, 첫 줄 설명을 적습니다.

- **바뀐 것만 다시 읽기.** mtime과 크기가 같으면 그대로 두고, 다르면 sha256을 보고, 내용이 바뀐 파일만 다시 뽑습니다. `show`·`find`·`dupes`·`churn`·`stats`는 부를 때마다 이렇게 맞추므로 따로 `build`를 하지 않아도 늘 최신입니다. 패턴표·언어표·추출기 판이 바뀌면 처음부터 다시 만듭니다.
- **비밀은 처음부터 뺍니다.** `.env`, `.env.*`, 키 파일(`*.pem`, `*.key`, `id_rsa*` …), `.npmrc`, `*.tfstate`, 이름에 `secret`이 든 파일 등은 이름만 보고 읽지 않습니다. 목록은 설정 `map.secrets`로 바꿀 수 있습니다. 루트 밖을 가리키는 링크도 읽지 않습니다.
- **읽지 않는 파일.** 1MB(`map.max_bytes`)보다 큰 파일, 바이너리, 압축된 코드는 심볼을 뽑지 않고 '읽지 않음'으로 셉니다. 찾기 결과가 없을 때 이 수를 함께 알려 '없다'와 '못 읽었다'를 나눕니다.

## 순위와 예산

`map show`는 Aider의 repo map에서 생각을 빌렸고, 코드는 표준 라이브러리로 새로 썼습니다.

1. 파일을 점으로, '이름을 쓰는 파일 → 그 이름을 정의한 파일'을 선으로 그래프를 만듭니다. 쓴 횟수는 제곱근으로 눌러 한 파일이 판을 덮지 않게 합니다.
2. 흔한 이름(`get`, `add`, `run` …)은 다른 것(`dict.get` 등)을 부른 것일 때가 많아 선을 약하게 하고, 약해진 몫은 출발점으로 돌려보냅니다. 정규화 때문에 다시 커지지 않게 하려는 것입니다. 파일이 같은 이름을 스스로 정의하면 그것을 쓴 것으로 보고 다른 파일로 선을 잇지 않습니다. `_`로 시작하는 이름, 여러 파일(5개 넘게)에 정의된 이름도 약하게 봅니다.
3. PageRank로 파일 순위를 내고, 그 순위를 선을 따라 정의 하나하나에 나눠 정의 순위를 만듭니다. 시험 파일의 정의는 낮춥니다.
4. `--focus`에 경로(`src/api`, 폴더 이름)나 낱말(`auth`, `규칙`)을 주면 그쪽에서 출발하게 무게를 주고, 이름이나 설명이 맞는 정의를 올립니다.
5. 상위 N개로 지도를 그려 글자 수를 재고, 예산에 드는 가장 큰 N을 이진 탐색으로 찾습니다. 뺀 개수와 늘리는 법을 끝에 적습니다.

두 언어로 쓴 설명(`한국어 / English`)은 설정 언어 쪽만 보여 줍니다.

## 찾기와 한국어

`map find`는 이름, 설명, 경로, 시그니처를 함께 봅니다.

- 이름은 snake_case와 camelCase를 낱말로 나눠 맞춥니다(`readConfig` → read, config).
- 영어 낱말은 앞부분만 맞아도 찾고(`auth` → authenticate), 끝이 조금 다른 것도 찾습니다(`rules` → rule).
- 한국어는 두 글자 묶음으로 맞춥니다. 한국어는 낱말 뒤에 조사가 붙어 띄어쓰기 단위로 자르면 `인증을`과 `인증`이 서로 다른 낱말이 됩니다. 두 글자씩 묶으면 `인증을` → 인증, 증을이 되어 어느 쪽으로 물어도 맞습니다. 검토한 코드 검색 도구 중 이 문제를 다룬 곳은 찾지 못했습니다.
- 결과는 세 단계입니다. `--level 1`은 한 줄 요약, `2`는 시그니처와 설명, `3`은 지금 파일에서 읽은 몸통까지입니다. 목록을 먼저 보고 필요한 것만 몸통을 엽니다.
- 결과가 없으면 빈 결과 대신 '못 찾음'과 본 범위(파일·심볼 수, 못 읽은 파일 수), 다음에 할 일을 냅니다.

## 중복과 자주 바뀌는 곳

- `map dupes`는 같은 몸통 해시를 가진 함수(이름이 달라도)와, 공백·주석·뜻 없는 줄(괄호만, import 등)을 지운 뒤 6줄(`map.dupe_window`) 넘게 같은 글을 찾습니다. 문법을 모르므로 어떤 언어에도 같게 돕니다.
- `map churn`은 `git log --numstat`으로 파일별 변경 횟수를 세고, 변경 횟수 × 지금 줄 수를 점수로 핫스팟을 보여 줍니다. git이 없거나 리포가 아니면 건너뜁니다.

## check 연동

`habitree check`의 `docs.stale-code`(알림)는 Markdown 문서가 링크한 코드 파일이 그 문서의 마지막 커밋보다 나중에 커밋됐을 때 알립니다. 코드가 바뀌었는데 그 코드를 설명한 글은 그대로일 수 있다는 뜻입니다. 커밋 시각만 보므로 커밋하지 않은 수정은 보지 않고, git이 없으면 건너뜁니다. 항목 목록은 [check.md](check.md)에 있습니다.

## MCP 서버

`habitree mcp`는 표준 입출력으로 도는 MCP 서버입니다. 줄마다 JSON-RPC 2.0 메시지 하나를 UTF-8로 주고받고, stdout에는 MCP 메시지만 씁니다. 로그는 stderr로 보냅니다. 루트(설정이 있는 폴더, 없으면 git 루트)는 `-C 폴더`로 정할 수 있습니다.

| 도구 | 언제 부르나 |
|---|---|
| `map_find` | 새 함수·모듈·도구를 만들기 전에. 이름이나 설명으로 이미 있는 것을 찾습니다(`query`, `level`, `limit`) |
| `map_show` | 처음 보는 프로젝트나 폴더의 큰 그림을 볼 때(`focus`, `budget`) |
| `rules_brief` | 작업을 시작하기 전에. 작업 범위의 규칙만 짧게(`scopes`, `aspect`, `must`, `budget`) |
| `check` | 끝내기 전에. 점검 결과 요약(`only`, `auto`). 이 도구는 `check` 명령의 `collect()`를 그대로 씁니다 |

- 도구 결과는 글자 예산(`map.mcp_budget`, 기본 4000자) 안에서 자르고, 자른 사실을 적습니다. 잘못된 인자는 오류 결과(`isError`)로 돌려줘 AI가 읽고 고칠 수 있게 합니다.
- 작업 폴더 밖은 읽지 않습니다. `focus`에 절대 경로나 `..`가 들어오면 거절하고, 몸통을 읽을 때도 실제 경로가 루트 안인지 확인합니다.
- 서버는 메모리에 색인을 두고, 도구를 부를 때마다 바뀐 파일만 다시 읽습니다.
- 판은 `initialize`로 시작하는 방식(2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25)을 따릅니다. 클라이언트가 보낸 `protocolVersion`을 지원하면 그대로, 아니면 이 중 최신을 돌려줍니다. 2026-07-28 판의 요청마다 판을 싣는 방식(`server/discover`, `_meta`)은 아직 따르지 않습니다. 명세상 두 방식을 다 아는 클라이언트는 `server/discover`가 `-32601`로 끝나면 `initialize`로 돌아옵니다.

연결하는 법. 프로젝트 루트의 [.mcp.json](../../.mcp.json)이 예시입니다. Claude Code는 이 파일의 서버를 대화형 세션에서 처음 쓰기 전에 사용자에게 묻습니다.

```json
{"mcpServers": {"habitree": {"type": "stdio", "command": "habitree", "args": ["mcp"]}}}
```

- Claude Code 명령줄: `claude mcp add habitree -- habitree mcp`
- 그 밖의 MCP 클라이언트: 명령 `habitree`, 인자 `["mcp"]`. `habitree`가 PATH에 없으면 명령을 Python 실행 파일의 절대 경로로, 인자를 `["-m", "habitree", "mcp"]`로 둡니다.
- 훅·MCP 등록에는 `uvx` 같은 임시 환경보다 `uv tool install`이나 `pipx install`로 영구 설치한 명령이 맞습니다. 임시 환경은 경로가 바뀝니다.

## 설정

```json
{
  "map": {
    "exclude": [], "secrets": null, "max_bytes": 1000000,
    "show_budget": 4000, "find_limit": 10, "find_budget": 4000, "mcp_budget": 4000,
    "dupe_window": 6, "churn_commits": 2000, "churn_top": 15
  }
}
```

`secrets`가 `null`이면 기본 목록을 쓰고, 목록을 주면 그것으로 바꿉니다. `exclude`는 위의 `exclude`에 더해 색인에서만 뺄 폴더·경로입니다.

## English

### Why an index

The first step of the work cycle is "find": look for what already exists before building. Until now Habitree gave that step only a hand-written README map. The map tells you about folders, not about the functions inside them. So an agent either writes something that already exists, or reads whole files again and again to find it. The first gives you two copies of the same code; the second costs tokens.

The index keeps only names, signatures and the first line of each description. The agent looks at the list before it opens any body, and opens only what it needs. Even the list is not handed over all at once; it comes in order of importance, cut to a character budget. The aim is to make the agent look first; saving tokens follows from that.

An index nobody calls does nothing. So the same feature lives both on the command line (`habitree map find`) and as an MCP tool (`map_find`), and the tool descriptions and server instructions say to call it before writing something new.

### Why no heavy tools, and the limits

Strong tools exist for code search: vector databases with embeddings, language servers (LSP), tree-sitter. None of them are in the default install.

- Vector databases and embeddings need API keys, outside services and money, and code may leave the machine.
- Language servers need a server and its runtime installed and running for every language.
- tree-sitter is precise, but installs often break when versions change.

Habitree first keeps to running on the Python standard library alone, with the same commands for a project in any language and nothing to install. The limits that come with that are stated openly.

- Languages other than Python are read with line-based regular expressions, so results are approximate. Multi-line signatures, macros and indentation-based syntax can be missed or get the wrong end line. Every result says whether it is exact (`ast`) or approximate (patterns).
- References are counted by name. Types are not resolved, so different functions with the same name get mixed.
- Names created at run time (dynamic registration, calls by string) are not seen.
- Budgets are in characters, not tokens, and Korean text costs a different number of tokens per character than English or code.

Most token-saving figures that other tools advertise were measured by their own authors under narrow conditions. Where conditions were published, tokens went down but accuracy stayed the same or fell below reading the files directly in some cases, and one project withdrew a measurement because the tool had not actually been called. So this document gives no savings figures. The effect will be measured by running the same task with the feature on and off (`bench`, planned) and published with its conditions.

### Structure: a language-neutral base with per-language patterns

The target project can be in any language, so there are two layers.

| Layer | What it does | Where |
|---|---|---|
| Common base (every language) | file list (respects `.gitignore` with git), language detection (375 languages), line and code-line counts, sha256, git history, windowed text duplicates, Markdown headings | `mapper/langs.py`, `index.py`, `dupes.py`, `churn.py`, [languages.json](../../src/habitree/data/languages.json) |
| Per-language symbols | Python via `ast` (exact). Other languages via the pattern table (approximate): JavaScript/TypeScript, Go, Rust, Java/C#/Groovy, Kotlin, Scala, Swift, C/C++/Objective-C, Ruby, PHP, Shell, PowerShell, Lua, Perl, R, Elixir, Dart, SQL, Markdown | `mapper/extract.py`, [symbols.json](../../src/habitree/data/symbols.json) |

Every extractor produces the same symbol record, so ranking, search, duplicates and MCP never need to know the language.

| Field | Meaning |
|---|---|
| `name`, `kind` | name and kind (function, method, class, struct, interface, const, section, …) |
| `line`, `end`, `start` | definition line, end line, start line including decorators (when present) |
| `sig` | one-line signature. Constants carry the name (and type) only, never the value |
| `doc` | first line of the description (docstring or the comment just above) |
| `parent` | the enclosing class, struct, impl, … |
| `body` | body hash (when at least 3 meaningful lines remain after removing spaces and comments), used for duplicates |

#### Adding a language

No code changes; edit two data files.

1. **One row in the language table.** Add the extension, file names and comment markers to `data/languages.json` if missing. That alone turns on detection, line counts, text duplicates and history for the language. The table comes from scc ([NOTICE.md](../../NOTICE.md)).
2. **One pattern group.** Add a group under `groups` in `data/symbols.json`. Each line is tried against the regexes from the top, and the first match wins.
3. **One test.** Add a short sample and the expected symbols to `tests/test_map.py`.

| Group field | Meaning |
|---|---|
| `languages` | language names from the table |
| `block` | how to find the end line: `brace` (brace depth), `indent` (indentation), `end` (an `end` at the same indentation), `heading` (the next heading of the same or higher level), `line` (that line only) |
| `extractor` | `ast` tries the Python extractor first and falls back to patterns on a syntax error |
| `fences`, `refs` | skip code fences; count reference names (on by default) |
| `patterns[].re` | Python `re` syntax. `(?P<name>…)` is required; `(?P<kind>…)`, `(?P<parent>…)` and `(?P<level>…)` are used when present |
| `patterns[].kind`, `kinds` | default kind, and a table that renames captured kinds (`{"def": "function"}`) |
| `patterns[].inside`, `member`, `top` | match only inside these kinds, only at the depth right inside their body, or only when not enclosed. This keeps calls inside method bodies from being taken as definitions |
| `patterns[].flags`, `block` | `i` ignores case; a per-pattern way to find the end |

The top-level `text_only` (prose and data formats that are not code), `not_names` (words that cannot be names), `ref_stop` (words not counted as references) and `common_names` (common names weighted down in ranking) are data too.

### The index file

The index is a single `.habitree/state/map.json` and is not committed. File keys are NFC paths relative to the root with `/`, the same on Windows, macOS and Linux. Each file records its language, lines, code lines, size, mtime, sha256, extractor, symbols, reference counts and first-line description.

- **Only changed files are read again.** Same mtime and size: kept. Otherwise the sha256 decides, and only files whose content changed are extracted again. `show`, `find`, `dupes`, `churn` and `stats` refresh this way on every call, so the index is current without a separate `build`. A change to the pattern table, the language table or the extractor version triggers a full rebuild.
- **Secrets are left out from the start.** `.env`, `.env.*`, key files (`*.pem`, `*.key`, `id_rsa*`, …), `.npmrc`, `*.tfstate`, files with `secret` in the name and similar are skipped by name without being read. Change the list with `map.secrets`. Links that point outside the root are not read either.
- **Files that are not parsed.** Files over 1 MB (`map.max_bytes`), binaries and minified code get no symbols and are counted as unread. When a search finds nothing, that count is reported too, to tell "not there" from "could not read".

### Ranking and budget

`map show` borrows its idea from Aider's repo map; the code is new and uses only the standard library.

1. Files are nodes, and "file that uses a name → file that defines it" are edges. Use counts are square-rooted so one file cannot dominate.
2. Common names (`get`, `add`, `run`, …) often refer to something else (`dict.get`, …), so their edges are weakened and the weakened share flows back to the start instead of being renormalized away. A file that defines a name itself is taken to use its own, with no edge to other files. Names starting with `_` and names defined in more than 5 files are weighted down too.
3. PageRank ranks the files, and each file's rank is split along its edges into a rank for each definition. Definitions in test files are lowered.
4. `--focus` with paths (`src/api`, a folder name) or words (`auth`, `규칙`) starts the walk from there and lifts definitions whose name or description matches.
5. The map is drawn from the top N definitions and measured, and a binary search finds the largest N within the budget. The number left out, and how to see more, is written at the end.

Bilingual descriptions (`한국어 / English`) show only the side for the configured language.

### Search and Korean

`map find` looks at names, descriptions, paths and signatures together.

- Names are split at snake_case and camelCase (`readConfig` → read, config).
- English words match by prefix (`auth` → authenticate) and with slightly different endings (`rules` → rule).
- Korean is matched in two-character pieces. Korean attaches particles to words, so splitting on spaces makes `인증을` ("authentication" + object particle) and `인증` different words. Two-character pieces turn `인증을` into 인증, 증을, so either form finds the other. None of the code search tools we reviewed handled this.
- Results come in three levels. `--level 1` is one line each, `2` adds the signature and description, `3` adds the body read from the current file. Look at the list first, and open bodies only for what you need.
- When nothing matches, the answer is not an empty list but "not found", what was searched (files, symbols, unread files) and what to try next.

### Duplicates and hotspots

- `map dupes` finds functions with the same body hash (even under different names), and text that repeats for more than 6 lines (`map.dupe_window`) after removing spaces, comments and lines with no meaning (brackets only, imports, …). It needs no grammar, so it works the same for any language.
- `map churn` counts changes per file with `git log --numstat` and shows hotspots scored by changes × current lines. It is skipped without git or outside a repository.

### Check integration

`docs.stale-code` (notice) in `habitree check` reports when a code file linked from a Markdown doc was committed after the doc's last commit: the code changed, and the text describing it may not have. Only commit times are compared, so uncommitted edits are not seen, and the check is skipped without git. The item list is in [check.md](check.md).

### MCP server

`habitree mcp` is an MCP server over standard input and output. It exchanges one JSON-RPC 2.0 message per line in UTF-8 and writes only MCP messages to stdout; logs go to stderr. The root (the folder with the config, otherwise the git root) can be set with `-C folder`.

| Tool | When to call it |
|---|---|
| `map_find` | Before writing a new function, module or tool: finds what already exists by name or description (`query`, `level`, `limit`) |
| `map_show` | To see the big picture of an unfamiliar project or folder (`focus`, `budget`) |
| `rules_brief` | Before starting work: only the rules for the task's scopes, in short form (`scopes`, `aspect`, `must`, `budget`) |
| `check` | Before finishing: a summary of the checks (`only`, `auto`). This tool reuses `collect()` from the `check` command |

- Tool results are cut to a character budget (`map.mcp_budget`, default 4000) with a note when cut. Bad arguments come back as error results (`isError`) so the agent can read and fix them.
- Nothing outside the project folder is read. Absolute paths or `..` in `focus` are refused, and the real path is checked to be inside the root before a body is read.
- The server keeps the index in memory and re-reads only changed files on each tool call.
- It speaks the protocol revisions that open with `initialize` (2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25). If the client's `protocolVersion` is supported it is echoed; otherwise the latest of these is returned. The 2026-07-28 style with the version on every request (`server/discover`, `_meta`) is not implemented yet. Per the specification, a client that knows both styles falls back to `initialize` when `server/discover` ends with `-32601`.

How to connect. The [.mcp.json](../../.mcp.json) at the repository root is an example. In interactive sessions, Claude Code asks the user before it first uses a server from this file.

```json
{"mcpServers": {"habitree": {"type": "stdio", "command": "habitree", "args": ["mcp"]}}}
```

- Claude Code command line: `claude mcp add habitree -- habitree mcp`
- Other MCP clients: command `habitree`, arguments `["mcp"]`. If `habitree` is not on PATH, use the absolute path of the Python executable as the command and `["-m", "habitree", "mcp"]` as the arguments.
- For hooks and MCP registration, a command installed for good with `uv tool install` or `pipx install` fits better than a temporary environment like `uvx`, whose path changes.

### Configuration

The `map` settings are shown in the JSON block above. `secrets: null` uses the default list, and a list replaces it. `exclude` lists folders or paths to leave out of the index only, in addition to the top-level `exclude`.
