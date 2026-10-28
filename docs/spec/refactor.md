# 리팩토링 제안

`habitree refactor`는 코드가 한곳에 몰렸거나, 같은 코드가 여러 곳에 있거나, 한 기능이 여기저기 흩어졌거나, 덜어 낼 수 있는 코드가 남은 곳을 찾아 정리 계획을 제안합니다. 코드는 고치지 않습니다. 무엇을 할지는 사람과 AI가 정합니다.

- [English](#english)

## 왜 있나

덧대기로 커진 코드는 두 번 비쌉니다. AI는 고칠 때마다 그 파일을 통째로 읽으니 읽을 때마다 토큰이 들고, 한 곳을 고치면 엉뚱한 곳이 깨지기 쉬워서 고친 뒤에도 시간이 듭니다. 작업 중 경고(`code.structure.file-growth`, `code.structure.copy-block`)는 "지금 커지고 있다", "지금 복사하고 있다"를 그 자리에서 알려 주지만, 이미 커진 코드를 어디서부터 어떻게 풀지는 알려 주지 않습니다. 이 명령이 그다음 걸음입니다. 그래서 그 경고의 제안 끝에 `habitree refactor --focus "<파일>"`을 이어 두었습니다.

정리도 잘못하면 비쌉니다. 한 번에 크게 갈아엎으면 무엇이 깨졌는지 찾기 어렵고, AI는 넓은 변경일수록 중간에 길을 잃기 쉽습니다. 그래서 기본은 작은 단계이고, 단계마다 기계 검증(`habitree verify`)을 둡니다. 큰 정리는 조건이 갖춰졌을 때만 권하고, 그때도 단계로 나눕니다.

## 더하기보다 덜어내기

정리 제안이 '나누기'와 '모듈로 빼기'만 권하면 거꾸로 체계가 무거워집니다. 파일과 층이 늘고, 기능 하나를 보려고 여러 파일을 열어야 합니다. 목표는 나누는 것이 아니라 읽고 고칠 곳을 줄이는 것입니다.

그래서 같은 문제라면 덜어 내는 해법을 먼저 보여 줍니다.

- 큰 파일을 나누기 전에, 그 파일에서 아무도 부르지 않는 정의와 한 곳에서만 쓰는 짧은 층부터 덜어 내게 합니다.
- 같은 코드가 여러 곳에 있으면 새 공통 모듈을 만들기보다 한 곳을 남기고 나머지가 그곳을 부르게 합니다. 새 함수는 같은 글이 함수 밖에 있을 때만 그 파일 안에 만듭니다.
- 한 기능이 작은 파일 여러 개로 쪼개졌으면 하나로 합치기를 권합니다.
- 몰린 코드를 풀 때도 관리자나 중간 층을 새로 세우기보다 이미 있는 경계(맨 위 클래스, 같은 접두어로 묶인 함수)를 따라 옮기게 합니다.

이 기능 자신도 같은 원칙을 따릅니다. 새 분석 엔진을 만들지 않고, 이미 있는 코드 색인(`map`)의 심볼, 참조 그래프, 중복, git 기록을 읽어 판단만 얹습니다. git 기록을 훑는 것처럼 비용이 드는 일은 이 명령을 직접 부를 때만 하고, 훅과 `check`처럼 자주 도는 길에는 아무것도 더하지 않았습니다.

## 무엇을 찾나

| 종류 | 찾는 것 | 재는 법 |
|---|---|---|
| 몰림 | 큰 파일, 긴 함수, 심볼이 너무 많은 파일 | 줄 수(빈 줄·주석 포함)와 함수 길이를 프로젝트 중앙값과 견줌. Python은 문법 분석의 끝 줄, 그 밖의 언어는 패턴이 찾은 끝 줄이나 다음 심볼까지의 거리. 순서는 줄 수 × git 변경 횟수 |
| 중복 | 같은 몸통의 함수, 같은 글 | `map dupes`의 결과를 파일 묶음별로 모음 |
| 흩어짐 | 다른 폴더의 같은 이름 정의, 같은 폴더에서 시그니처까지 같은 정의, 늘 함께 바뀌는 다른 폴더의 파일, 서로 참조하는 다른 폴더의 파일 | 심볼 이름, git 커밋별 파일 목록, 참조 그래프 |
| 덜어내기 | 어디서도 부르지 않는 정의와 파일, 한 곳에서만 쓰고 다른 함수를 부르기만 하는 짧은 층, 서로만 쓰는 작은 파일 무리, 한 곳만 쓰는 작은 파일 | 참조 그래프의 들어오는 참조, 모든 글 파일에서 이름이 나오는 곳(문서·설정·문자열 호출 포함) |

시험 파일은 후보에서 빼고, 안전망이 있는지 볼 때만 씁니다.

### 기준값과 근거

기준값은 코드에 박지 않고 base 꾸러미의 `code/structure` 규칙 세 개(`code.structure.concentration`, `code.structure.duplication`, `code.structure.fragmentation`)의 `detect`에 둡니다. 프로젝트 규칙 DB에 그 규칙이 없으면 꾸러미의 기본값을 씁니다.

| 값 | 기본 | 근거 |
|---|---|---|
| 몰림: 파일 줄 수, 함수 줄 수의 바닥 | 300줄, 50줄 | ESLint `max-lines`, `max-lines-per-function`의 기본값입니다. 둘 다 빈 줄과 주석까지 셉니다. 널리 쓰는 도구의 출발값이지 연구 결과는 아닙니다 |
| 몰림: 중앙값의 몇 배 | 4배(`threshold`) | 시작 값, 조정 가능 |
| 몰림: 심볼 수의 바닥 | 40개 | 시작 값, 조정 가능 |
| 몰림의 순서: 줄 수 × 변경 횟수 | | 자주 바뀌면서 큰 곳부터 보는 핫스팟(Adam Tornhill, "Your Code as a Crime Scene"). `map churn`과 같은 점수입니다 |
| 중복: 같은 글의 최소 줄 수 | 6줄(`threshold`) | `map dupes`와 작업 중 복사 경고가 쓰는 창과 같은 값 |
| 함께 바뀜: 파일마다 변경 5번 이상, 함께 5번 이상, 정도 30% 이상, 파일 30개 넘게 바꾼 커밋은 뺌 | | code-maat의 `min-revs`, `min-shared-revs`, `min-coupling`, `max-changeset-size` 기본값. 정도는 함께 바뀐 횟수를 두 파일 변경 횟수의 평균으로 나눈 값으로, 우리가 정한 식입니다 |
| 같은 이름이 5곳 넘게 정의되면 뺌 | 5곳 | `map` 순위가 Aider repo map에서 빌린 '흔한 이름' 기준과 같은 값. 여러 파일이 같은 약속으로 두는 이름(명령마다 `run`처럼)을 흩어짐으로 보지 않으려는 것 |
| 작은 파일, 작은 파일 무리, 짧은 층의 몸통 | 20줄, 3개, 2줄 | 시작 값, 조정 가능 |
| 규모: 큰 정리를 권하는 퍼진 곳의 수, 쓰는 곳의 한도, 자주 바뀜 | 3곳, 5곳, 위 10% | 시작 값, 조정 가능 |

흩어짐과 덜어내기는 근거가 약하고 정적 분석으로 확신할 수 없어 정보 등급(`info`)으로 시작합니다. 출력에 '알림'으로 표시합니다.

기준은 규칙 사다리와 같은 길로 움직입니다([method.md](method.md)). 제안이 틀렸으면 `habitree rules miss <규칙 id>`, 맞았으면 `habitree rules hit <규칙 id>`로 남깁니다. 최근 반응에서 '틀렸다'가 쌓이면 `threshold`가 한 단계 올라 덜 민감해지고, 정보 등급 규칙은 '맞았다'가 두 번이면 경고로 오릅니다. 세부 값은 `.habitree/rules.json`에서 그 규칙의 `detect.params`를 고치면 되고, 규칙을 쉬게 하면(`rules pause`) 그 종류는 찾지 않습니다.

## 작은 단계와 큰 정리 고르기

후보마다 아래를 보고 규모를 고르며, 고른 이유를 함께 보여 줍니다.

| 살펴보는 것 | 재는 법 | 작은 단계로 기우는 경우 |
|---|---|---|
| 검증 수단 | 설정 `verify`의 명령, 그 코드를 이름으로 쓰는 시험이나 모듈 이름이 든 시험 파일 | 둘 중 하나라도 없음 |
| 쓰는 곳 | 참조 그래프에서 들어오는 파일 수. 시험과 흔한 이름(`run`, `get` 등)은 뺌 | 5곳 넘음 |
| 바깥 공개 | 입구 파일(`__init__`, `index`, `main`, `cli`, `lib`, `mod`, `config` 등) | 입구 파일 |
| 최근 변경 | git 변경 횟수가 중앙값을 넘고 위 10% 안 | 자주 바뀜 |
| 퍼진 정도 | 문제가 있는 곳의 수 | 3곳 미만 |

큰 정리는 문제가 세 곳 넘게 퍼졌고, 앞의 네 가지 중 어느 것에도 걸리지 않을 때만 권합니다. 나머지는 모두 작은 단계입니다. 안전망 없이 넓게 바꾸면 깨진 곳을 알 수 없고, 쓰는 곳이 많으면 바깥 모양이 바뀔 때 깨지는 곳도 많고, 자주 바뀌는 코드를 크게 바꾸면 다른 작업과 부딪히기 때문입니다. 문제가 한두 곳뿐이면 한 걸음으로 충분합니다. `--mode mini|bold`로 규모를 정해 줄 수 있지만, 그때도 안전망 단계는 빠지지 않습니다.

## 단계

모든 계획은 같은 순서를 따르고, 단계마다 확인 방법(`habitree verify`)이 붙습니다.

1. **안전망.** 검증 수단이 없으면 첫 단계는 늘 그것을 만드는 일입니다. 바꾸기 전의 동작을 그대로 확인하는 시험을 쓰고 그 명령을 설정 `verify`에 등록합니다. Michael Feathers가 "Working Effectively with Legacy Code"에서 말한 특성 시험(characterization test)의 생각입니다. 지울 코드에는 시험을 쓰라고 하지 않고, 지우기 전에 `git grep`으로 문자열 호출과 문서 언급까지 확인하게 합니다.
2. **덜어 내기.** 같은 파일에 덜어 낼 것이 있으면 나누기보다 먼저 합니다.
3. **작은 단계라면** 한 걸음만 하고 검증한 뒤, `habitree refactor --focus <파일>`로 다음 걸음을 다시 봅니다. 한 번에 하나씩 하고 결과를 보고 다음을 정하는 방식은 Martin Fowler의 "Refactoring"이 권하는 작은 단계와, 목표를 바로 시도해 보고 막히면 되돌려 선행 작업부터 하는 Mikado 방법(Ellnestam·Brolund)을 참고했습니다.
4. **큰 정리라면** 네 단계로 나눕니다. 지금 상태가 합격인지 확인하고, 바깥 모양(쓰는 곳이 부르는 이름과 인자)을 고정한 채 새 자리를 정하고, 안쪽을 한 번에 한 곳씩 옮기고, 마지막에 옛 이름과 복사본, 중계 코드를 지웁니다. 옛 것을 살려 둔 채 새 것을 키우다가 옛 길을 걷어 내는 Strangler Fig 방식(Martin Fowler)을 코드 한 덩어리 크기로 줄인 것입니다.

예를 들어 같은 몸통의 함수가 세 파일에 있을 때, 시험과 `verify`가 없으면 이렇게 나옵니다.

```
1. [중복] 같은 몸통 3곳, 각 9줄: a.py:1 alpha_total, b.py:1 beta_total, c.py:1 gamma_total
   왜: 같은 코드가 3곳에 있어요. 고칠 때 3곳을 다 찾아 고쳐야 하고, 하나를 빠뜨리면 따로 낡아요.
   권함: 작은 단계 · 검증 명령 없음(설정 verify), 이 코드를 쓰는 시험 없음 · 규칙 code.structure.duplication
   ① 안전망 먼저: a.py, b.py의 지금 동작을 그대로 확인하는 시험을 하나 쓰고, 그 실행 명령을 설정 verify에 등록 → habitree verify
   ② a.py:alpha_total을(를) 남기고 b.py:beta_total은(는) 그것을 부르게 바꾼 뒤 몸통 지우기(새 함수 없이) → habitree verify
   ③ 다음 걸음은 `habitree refactor --focus a.py`로 다시 보기
```

시험과 `verify`가 있고 쓰는 곳이 적으면 같은 후보가 큰 정리가 됩니다.

```
   권함: 큰 정리 · 3곳에 퍼졌고 안전망이 있으며 쓰는 곳이 적음 · 규칙 code.structure.duplication
   ① 시작 전에 지금 상태가 합격인지 확인 → habitree verify
   ② 바깥 모양 고정: 다른 파일에서 부르는 곳이 없으니 새 자리만 정하기: 남길 한 곳 a.py:alpha_total → habitree verify
   ③ 안쪽 옮기기: 한 번에 한 곳씩, a.py:1 alpha_total, b.py:1 beta_total, c.py:1 gamma_total → habitree verify
   ④ 옛 길 지우기: 옛 이름·복사본·중계 코드를 지우고 `habitree map find alpha_total`으로 남은 곳 확인 → habitree verify
```

## 쓰는 법

```
habitree refactor                         # 후보 3개(종류마다 번갈아)
habitree refactor src/api --top 5         # 경로로 좁히기
habitree refactor --focus "src/big file.py"  # 경고에서 이어 온 파일 하나
habitree refactor --mode mini             # 규모를 정해 주기(auto, mini, bold)
habitree refactor --json                  # AI가 따라 할 단계 구조
```

`map` 색인이 없으면 먼저 만들고, 있으면 바뀐 파일만 다시 읽습니다. 후보는 종류마다 번갈아 늘어놓고, 한 바퀴 안에서는 경고 등급 종류가 먼저입니다. 보이지 않은 후보의 수는 끝에 종류별로 적습니다.

`--json`은 AI가 그대로 따라 할 수 있게 꼭 필요한 칸만 냅니다. 후보마다 `kind`(concentration, duplication, fragmentation, simplify), `sub`(세부 종류), `level`, `rule`, `files`, `facts`(숫자), `mode`(mini, bold), `reasons`(규모를 고른 이유 코드), `why`(왜 비효율인지 한 문장), `steps`(순서대로 `do`, `files`, `check`)가 있습니다.

MCP 도구는 더하지 않았습니다. 도구가 많을수록 AI가 매번 읽는 도구 설명이 늘고 고르기도 어려워지는데, 이 기능은 작업 도중에 자주 부를 일이 아니라 정리할 때 한 번 부르는 일이라 명령줄 `habitree refactor --json`으로 충분합니다.

## 한계

- 정적 분석이라 뜻은 모릅니다. 참조는 이름으로 세므로, 이름이 같고 뜻이 다른 정의가 '흩어짐'으로 나올 수 있습니다. 그래서 그 단계에는 '뜻이 다르면 이름을 구분'을 함께 적습니다.
- 문자열로 부르기, 실행 중 등록, 바깥 패키지가 부르는 공개 API는 보지 못합니다. 그래서 지우기 후보는 정보 등급이고, 모든 글 파일에서 그 이름이 나오는지 한 번 더 보며, 장식자가 붙은 정의와 입구 파일은 처음부터 뺍니다. 그래도 지우기 전에는 `git grep`으로 확인하게 합니다.
- Python 밖의 언어는 패턴으로 읽어 대략입니다. 함수 끝 줄을 모르는 문법에서는 다음 심볼까지의 거리로 길이를 셉니다.
- 몰림은 줄 수로만 봅니다. 복잡도는 재지 않습니다.
- 서로 참조는 두 파일 사이만 봅니다. 세 파일 넘게 도는 고리는 찾지 않습니다.
- '있는 경계'는 이름으로 짐작합니다. `get_`처럼 동사로 시작하는 묶음은 역할 경계가 아닐 수 있습니다.
- 시험 유무는 이름 참조와 시험 파일 이름으로 짐작합니다.
- 함께 바뀜은 커밋 습관에 따라 달라집니다. 한 커밋에 여러 일을 섞으면 거짓 묶음이 생깁니다. git이 없으면 변경 횟수와 함께 바뀜은 건너뜁니다.
- 이 제안을 따랐을 때 토큰이나 결함이 얼마나 주는지는 재지 않았습니다. 재면 조건과 함께 공개합니다.

## English

`habitree refactor` finds code that has piled up in one place, code that exists in several copies, features scattered across many files, and code that could simply go, and suggests a cleanup plan. It changes nothing; people and the agent decide what to do.

### Why

Code grown by patching costs twice. The agent reads the whole file on every change, so every read costs tokens, and a fix in one spot easily breaks another, so time is lost after the change too. The in-flight warnings (`code.structure.file-growth`, `code.structure.copy-block`) say "this is growing" or "this is being copied" while it happens, but not where to start untangling code that is already big. This command is that next step, which is why those warnings now end with `habitree refactor --focus "<file>"`.

A cleanup can be expensive too. A sweeping rewrite makes it hard to find what broke, and the wider the change, the more easily an agent loses its way halfway. So the default is a small step, with machine verification (`habitree verify`) after each one. A bold cleanup is suggested only when the conditions are in place, and even then it comes in stages.

### Remove before you add

If cleanup advice only ever says "split this" and "extract a module", the structure gets heavier instead of lighter. Files and layers multiply, and one feature takes several files to read. The goal is not to split things but to have fewer places to read and change.

So for the same problem, the subtractive fix comes first.

- Before splitting a big file, remove the definitions in it that nothing calls and the short layers used in one place.
- When the same code sits in several places, keep one and make the others call it, instead of creating a new shared module. A new function is created, inside that file, only when the repeated text is not already a function.
- When one feature is broken into many small files, suggest merging them.
- When untangling piled-up code, move it along seams that already exist (top-level classes, functions sharing a prefix) rather than introducing a new manager or middle layer.

The feature follows the same rule itself. It does not add a new analysis engine; it reads the symbols, reference graph, duplicates and git history the code index (`map`) already has and adds only judgment. Costly work such as walking the git history happens only when this command is called directly; nothing was added to frequent paths such as hooks and `check`.

### What it finds

| Kind | What | How |
|---|---|---|
| Concentration | Big files, long functions, files with too many symbols | Line counts (blank lines and comments included) and function lengths compared with the project median. Python uses the parser's end line; other languages use the end line the patterns found or the distance to the next symbol. Ordered by lines × git changes |
| Duplication | Functions with the same body, repeated text | Results of `map dupes`, grouped by the files involved |
| Fragmentation | The same name defined in different folders, definitions in one folder with the same signature, files in different folders that always change together, files in different folders that use each other | Symbol names, files per git commit, the reference graph |
| Simplify | Definitions and files nothing calls, short layers used in one place that only call another function, small files that only use each other, a small file used by only one other | Incoming references in the graph, and where the name appears in any text file (docs, config and calls by string included) |

Test files are never candidates; they are only used to decide whether a safety net exists.

#### Thresholds and their basis

Thresholds are not hard-coded. They live in the `detect` of three rules in the `code/structure` scope of the base pack (`code.structure.concentration`, `code.structure.duplication`, `code.structure.fragmentation`). When the project's rule DB lacks a rule, the pack's defaults are used.

| Value | Default | Basis |
|---|---|---|
| Concentration: floor for file lines and function lines | 300 lines, 50 lines | The defaults of ESLint `max-lines` and `max-lines-per-function`. Both count blank lines and comments. They are a widely used tool's starting values, not research results |
| Concentration: times the median | 4x (`threshold`) | Starting value, adjustable |
| Concentration: floor for symbols | 40 | Starting value, adjustable |
| Concentration order: lines × changes | | Hotspots, looking first at code that is both large and changes often (Adam Tornhill, "Your Code as a Crime Scene"). The same score as `map churn` |
| Duplication: minimum repeated lines | 6 lines (`threshold`) | The same window `map dupes` and the in-flight copy warning use |
| Co-change: each file changed 5 times or more, together 5 times or more, degree 30% or more, commits touching more than 30 files ignored | | The code-maat defaults for `min-revs`, `min-shared-revs`, `min-coupling` and `max-changeset-size`. The degree is shared changes divided by the average change count of the two files, a formula of our own |
| Names defined in more than 5 places are ignored | 5 | The same "common name" cutoff the `map` ranking borrowed from Aider's repo map. It keeps names that many files define by convention (`run` in every command) from counting as fragmentation |
| Small file, small-file group, body of a short layer | 20 lines, 3 files, 2 lines | Starting values, adjustable |
| Scale: places for a bold cleanup, limit on users, changes often | 3 places, 5 files, top 10% | Starting values, adjustable |

Fragmentation and simplification rest on weaker evidence and cannot be certain from static analysis, so they start at the info level and are marked as notes in the output.

Thresholds move along the same rule ladder ([method.md](method.md)). Record a wrong suggestion with `habitree rules miss <rule id>` and a useful one with `habitree rules hit <rule id>`. As "wrong" votes pile up, `threshold` goes up one step and the check gets less sensitive; an info-level rule becomes a warning after two "useful" votes. Fine-grained values are in the rule's `detect.params` in `.habitree/rules.json`, and pausing a rule (`rules pause`) stops that kind of search.

### Choosing a small step or a bold cleanup

For every candidate the scale is chosen from the following, and the reasons are shown with it.

| Looked at | Measured by | Leans to a small step when |
|---|---|---|
| Safety net | Commands under `verify`, and a test that uses the code by name or a test file named after the module | Either is missing |
| Users | Files with incoming references in the graph, excluding tests and common names (`run`, `get`, …) | More than 5 |
| Public surface | Entry files (`__init__`, `index`, `main`, `cli`, `lib`, `mod`, `config`, …) | It is an entry file |
| Recent change | git change count above the median and in the top 10% | It changes often |
| Spread | Number of places with the problem | Fewer than 3 |

A bold cleanup is suggested only when the problem is in three or more places and none of the first four applies. Everything else is a small step. A wide change without a safety net leaves breakage unseen; many users mean many breakages when the outside changes; a big change to code that changes often collides with other work. And a problem in one or two places needs only one step. `--mode mini|bold` sets the scale, but the safety net step is never dropped.

### Steps

Every plan follows the same order, and each step carries its check (`habitree verify`).

1. **Safety net.** Without a way to verify, the first step is always to build one: write a test that pins the current behavior and register its command under `verify`. This is the idea of the characterization test from Michael Feathers' "Working Effectively with Legacy Code". Code that is about to be deleted does not get a test; instead the step asks for a `git grep` for calls by string and mentions in docs before deleting.
2. **Remove.** Anything removable in the same file goes before any splitting.
3. **A small step** does one thing, verifies, and then looks at the next step again with `habitree refactor --focus <file>`. Doing one thing at a time and deciding the next from the result follows the small steps Martin Fowler's "Refactoring" recommends, and the Mikado method (Ellnestam and Brolund): try the goal, and when blocked, revert and do the prerequisites first.
4. **A bold cleanup** comes in four stages: confirm the current state passes; fix the outside (the names and arguments users call) and pick the new home; move the inside one place at a time; finally delete the old names, copies and forwarding code. It is the Strangler Fig approach (Martin Fowler), growing the new while the old keeps working and then removing the old path, shrunk to the size of one piece of code.

For example, with functions sharing one body in three files and no tests or `verify`, the advice reads:

```
1. [Duplication] Same body in 3 places, 9 lines each: a.py:1 alpha_total, b.py:1 beta_total, c.py:1 gamma_total
   Why: The same code lives in 3 places. Every fix has to find all 3, and a missed one drifts apart.
   Suggested: small step · no verify command (config verify), no test uses this code · rule code.structure.duplication
   1) Safety net first: write one test that pins the current behavior of a.py, b.py and register its command under verify → habitree verify
   2) Keep a.py:alpha_total; make b.py:beta_total call it and delete its body (no new function) → habitree verify
   3) For the next step, run `habitree refactor --focus a.py` again
```

With tests, `verify` and few users, the same candidate becomes a bold cleanup:

```
   Suggested: bold cleanup · spread over 3 places, safety net present, few users · rule code.structure.duplication
   1) Before starting, confirm the current state passes → habitree verify
   2) Fix the outside: no other file calls it, so just pick the new home: the one place to keep, a.py:alpha_total → habitree verify
   3) Move the inside, one place at a time: a.py:1 alpha_total, b.py:1 beta_total, c.py:1 gamma_total → habitree verify
   4) Remove the old path: delete old names, copies and forwarding code; check with `habitree map find alpha_total` → habitree verify
```

### Usage

```
habitree refactor                         # 3 candidates, kinds taking turns
habitree refactor src/api --top 5         # narrow by path
habitree refactor --focus "src/big file.py"  # the one file a warning pointed to
habitree refactor --mode mini             # set the scale (auto, mini, bold)
habitree refactor --json                  # steps for an agent to follow
```

If there is no `map` index it is built first; otherwise only changed files are read again. Candidates take turns by kind, with warning-level kinds first in each round, and the number of candidates not shown is listed by kind at the end.

`--json` carries only the fields an agent needs to follow the plan: for each candidate `kind` (concentration, duplication, fragmentation, simplify), `sub` (the finer kind), `level`, `rule`, `files`, `facts` (numbers), `mode` (mini, bold), `reasons` (codes for why that scale), `why` (one sentence on the cost) and `steps` (in order, each with `do`, `files` and `check`).

No MCP tool was added. Every tool adds a description the agent reads each time and makes choosing harder, and this is something called once when cleaning up rather than often during work, so the command line `habitree refactor --json` is enough.

### Limits

- Static analysis does not know meaning. References are counted by name, so definitions with the same name and different meanings can show up as fragmentation; the step says to rename them if they differ.
- Calls by string, registration at run time and public APIs called by other packages are not seen. So deletion candidates are notes, the name is looked up in every text file once more, decorated definitions and entry files are left out from the start, and the step still asks for a `git grep` before deleting.
- Languages other than Python are read with patterns and are approximate. Where the end of a function is unknown, its length is the distance to the next symbol.
- Concentration looks at line counts only; complexity is not measured.
- Mutual references are checked between two files only; longer cycles are not searched.
- Existing seams are guessed from names. A group starting with a verb such as `get_` may not be a real boundary of responsibility.
- Whether tests exist is guessed from name references and test file names.
- Co-change depends on commit habits; mixing several things in one commit creates false groups. Without git, change counts and co-change are skipped.
- How much following these suggestions saves in tokens or defects has not been measured. When it is, the result will be published with its conditions.
