# src

`habitree` 패키지입니다. 설치할 때 따라오는 것이 없도록 Python 표준 라이브러리만으로 짰습니다.

- 마지막 갱신: 2026-10-28

```
habitree/
├── cli.py            # 실행 입구 (habitree, ht)
├── commands/         # 명령 하나에 모듈 하나
│   ├── __init__.py   # 등록부 COMMANDS
│   └── init.py  rules.py  check.py  export.py
├── core/             # 여러 명령이 함께 쓰는 코드
│   ├── io.py         # UTF-8·LF 원자적 쓰기, 표준 입출력
│   ├── paths.py      # NFC 경로 키, 글롭, git 파일 목록
│   ├── config.py     # 설정과 실행 맥락
│   ├── i18n.py       # 한국어·영어 문구
│   ├── schema.py     # JSON Schema 일부를 검사하는 작은 검사기
│   ├── ruledb.py     # 규칙 DB
│   ├── textsim.py    # 같은 뜻 규칙 찾기
│   ├── markdown.py   # 링크, 앵커, 생성 구역
│   └── timeutil.py   # UTC 저장, 지역 시각 표시
└── data/
    ├── schema/       # JSON Schema (명세의 일부)
    └── packs/        # 기본 규칙 꾸러미
```

새 명령을 더하는 방법은 [CONTRIBUTING.md](../CONTRIBUTING.md)에 있습니다.

---

## English

The `habitree` package, written with the Python standard library only so installing it pulls in nothing else. The tree above shows the layout: `commands/` holds one module per command, `core/` holds shared code, and `data/` holds the JSON Schemas and bundled rule packs. See [CONTRIBUTING.md](../CONTRIBUTING.md) for adding a command.
