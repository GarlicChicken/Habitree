# 적합성 시험

Habitree의 약속은 명세(이 폴더의 문서와 JSON Schema)이고, Python 엔진은 그 참조 구현입니다. 언젠가 누군가 Go나 Rust로 엔진을 새로 만들 수도 있고, 어떤 도구는 규칙 DB만 읽어서 쓸 수도 있습니다. 그때 "같은 것"인지 판단할 기준이 있어야 해서 적합성 시험을 두었습니다. EditorConfig와 CommonMark가 같은 방식으로 여러 구현을 맞춥니다.

## 구조

```
conformance/
└── check/                 # 명령 이름
    └── <사례>/
        ├── project/       # 입력 프로젝트(.habitree/config.json 포함)
        └── expected.json  # 기대 결과
```

```json
{"exit": 1, "findings": [{"id": "docs.link", "path": "README.md"}]}
```

## 통과 조건

1. `project/`를 git 리포 밖의 임시 폴더로 복사합니다.
2. `<엔진> -C <복사본> --lang en check --json`을 실행합니다.
3. 결과에 나온 `(id, path)` 쌍의 집합이 `expected.json`과 같고 종료 코드가 `exit`와 같으면 통과입니다. 메시지 문장과 줄 번호는 구현마다 다를 수 있어서 비교하지 않습니다.

참조 엔진은 `tests/test_conformance.py`에서 모든 사례를 돌립니다.

---

## English

Habitree's contract is its specification (these documents and the JSON Schemas), and the Python engine is a reference implementation. Someday someone may write an engine in Go or Rust, or a tool may read only the rule DB. When that happens there has to be a way to decide whether it is "the same thing", so there is a conformance suite, the way EditorConfig and CommonMark keep their implementations in line.

The layout and the `expected.json` format are shown above. A case passes when you copy `project/` to a temporary folder outside any git repository, run `<engine> -C <copy> --lang en check --json`, and get the same set of `(id, path)` pairs and the same exit code as `expected.json`. Messages and line numbers are not compared because they may differ between implementations. The reference engine runs every case in `tests/test_conformance.py`.
