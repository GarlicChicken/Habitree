# 기여하기

이슈와 PR 모두 반갑습니다. 쓰다가 어색했던 점, 다른 AI 도구에서 겪은 문제, 더 나은 규칙 아이디어 무엇이든 좋습니다.

## 구조

Habitree에서 가장 먼저 지키려는 것은 명세입니다. [docs/spec/](docs/spec/)의 문서와 [JSON Schema](src/habitree/data/schema/)가 약속이고, 이 Python 엔진은 그 약속을 따르는 참조 구현입니다. 그래서 동작을 바꿀 때는 명세와 시험을 같은 커밋에서 함께 고칩니다.

- 명령 하나는 모듈 하나입니다. `src/habitree/commands/<이름>.py`에 `SUMMARY`, `add_arguments(p)`, `run(args, ctx)`를 두고 `commands/__init__.py`의 `COMMANDS`에 등록합니다.
- 여러 명령이 함께 쓰는 코드는 `core/`에 둡니다. `run`이 받는 `ctx`에는 프로젝트 루트, 설정, 언어가 들어 있습니다.
- 기본 규칙 꾸러미는 `src/habitree/data/packs/`에 있습니다. 꾸러미를 고치면 `version`을 올려 주세요. `init`을 다시 돌린 사용자는 자기가 손대지 않은 규칙만 새것으로 받습니다.

## 세 OS에서 같게

Habitree는 Windows, macOS, Linux에서 같은 결과를 내야 합니다. 실제로 가장 먼저 문제가 나는 곳은 경로와 인코딩이라, 아래를 지켜 왔습니다.

- 파일은 `core/io.py`로 읽고 씁니다. UTF-8로 읽되 BOM이 있어도 받아들이고, 쓸 때는 LF로 맞춥니다.
- 경로는 `core/paths.py`의 NFC 키로 비교합니다. macOS는 한글 파일 이름을 자모로 풀어서(NFD) 기록하는 경우가 있어서, 디스크에서 파일을 찾을 때는 `paths.resolve`를 씁니다.
- 바깥 명령은 셸을 거치지 않고 인자 배열로 부릅니다. 기본으로 쓰는 바깥 명령은 git 하나입니다. zsh와 PowerShell, BSD와 GNU 도구의 차이에서 오는 문제를 피하려는 것입니다.
- 시각은 UTC로 저장하고, 보여 줄 때만 그 컴퓨터의 시간대로 바꿉니다.
- 런타임 의존성은 두지 않습니다. 무거운 기능이 필요하면 선택 설치로 두고, 없어도 기본 기능은 돌게 합니다.

## 시험

```
python -m unittest discover -s tests -t tests
PYTHONPATH=src python -m habitree check
```

첫 줄은 단위 시험과 적합성 시험이고, 둘째 줄은 이 리포를 Habitree 자신으로 점검합니다. 점검 항목을 더할 때는 [docs/spec/check.md](docs/spec/check.md)와 적합성 사례도 함께 더해 주세요. 다른 언어로 만든 구현도 같은 사례로 확인할 수 있어야 하기 때문입니다.

## 다른 프로젝트의 코드

좋은 생각은 기꺼이 빌립니다. 다만 코드나 데이터를 옮길 때는 MIT, Apache-2.0, BSD처럼 허용 범위가 넓은 라이선스만 쓰고, [NOTICE.md](NOTICE.md)에 출처와 원래 고지를 남깁니다. GPL·AGPL이나 비상업 라이선스 코드는 옮기지 않고 생각만 참고합니다.

## 커밋

한 커밋에는 한 가지 일을 담아 주세요. API 키나 개인정보, 자기 컴퓨터의 개인 폴더 경로는 올리지 않습니다. `habitree check`가 흔한 경우는 잡아 줍니다.

---

## English

Issues and pull requests are welcome: rough edges you ran into, problems with other AI tools, ideas for better rules, anything.

### Architecture

The specification comes first. The documents in [docs/spec/](docs/spec/) and the [JSON Schemas](src/habitree/data/schema/) are the contract, and this Python engine is a reference implementation of it. When behavior changes, the spec and the tests change in the same commit.

- One command, one module: `src/habitree/commands/<name>.py` with `SUMMARY`, `add_arguments(p)` and `run(args, ctx)`, registered in `COMMANDS` in `commands/__init__.py`.
- Code shared by several commands lives in `core/`. The `ctx` passed to `run` carries the project root, the settings and the language.
- Bundled rule packs live in `src/habitree/data/packs/`. Bump a pack's `version` when you change it; users who rerun `init` receive new versions only of the rules they have not edited.

### Same results on three operating systems

Habitree has to behave the same on Windows, macOS and Linux. Paths and encodings are where things break first, so we keep to the following.

- Read and write files through `core/io.py`: UTF-8 in (a BOM is fine), LF out.
- Compare paths as NFC keys from `core/paths.py`. macOS sometimes stores Korean names decomposed (NFD), so use `paths.resolve` to find files on disk.
- Run external commands as argument lists, never through a shell. git is the only external tool used by default; this sidesteps zsh vs PowerShell and BSD vs GNU differences.
- Store times in UTC and convert to local time only for display.
- No runtime dependencies. Heavy features become optional extras, and the basics keep working without them.

### Tests

```
python -m unittest discover -s tests -t tests
PYTHONPATH=src python -m habitree check
```

The first line runs unit and conformance tests; the second checks this repository with Habitree itself. When you add a check item, add it to [docs/spec/check.md](docs/spec/check.md) and add a conformance case, so implementations in other languages can be verified against it.

### Code from other projects

We happily borrow good ideas. When copying code or data, use only permissive licenses (MIT, Apache-2.0, BSD) and record the source and original notice in [NOTICE.md](NOTICE.md). GPL, AGPL or non-commercial code is not copied; we only learn from its ideas.

### Commits

Keep one change per commit. Never commit API keys, personal data or paths from your own home folder; `habitree check` catches the common cases.
