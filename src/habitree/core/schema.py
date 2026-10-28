"""JSON Schema의 작은 부분집합 검사기(표준 라이브러리만). / Tiny JSON Schema subset validator.

지원: type, enum, const, required, properties, additionalProperties, items, minItems,
minLength, pattern, minimum, maximum, anyOf, oneOf, $ref(#/$defs/...).
스키마 파일은 schema/ 폴더의 JSON Schema 2020-12 문서이고, 다른 언어 구현도 그대로 쓸 수 있다.
"""
import json
import re
from pathlib import Path

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


def _is_type(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def validate(data, schema, root=None, path="$"):
    """문제 목록(빈 목록이면 통과). / List of problems; empty means valid."""
    root = schema if root is None else root
    errs = []
    if "$ref" in schema:
        ref = schema["$ref"]
        target = root
        for part in ref.lstrip("#/").split("/"):
            target = target[part]
        return validate(data, target, root, path)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(data, t) for t in types):
            return [f"{path}: {'/'.join(types)} 이어야 함 (got {type(data).__name__})"]
    if "const" in schema and data != schema["const"]:
        errs.append(f"{path}: {schema['const']!r} 이어야 함")
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{path}: {schema['enum']} 중 하나여야 함 (got {data!r})")
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errs.append(f"{path}: 너무 짧음")
        if "pattern" in schema and not re.search(schema["pattern"], data):
            errs.append(f"{path}: 형식 {schema['pattern']} 에 맞지 않음 ({data!r})")
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errs.append(f"{path}: {schema['minimum']} 이상이어야 함")
        if "maximum" in schema and data > schema["maximum"]:
            errs.append(f"{path}: {schema['maximum']} 이하여야 함")
    if isinstance(data, dict):
        for k in schema.get("required", []):
            if k not in data:
                errs.append(f"{path}: '{k}' 없음")
        props = schema.get("properties", {})
        for k, v in data.items():
            if k in props:
                errs += validate(v, props[k], root, f"{path}.{k}")
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errs.append(f"{path}: 모르는 칸 '{k}'")
                elif isinstance(extra, dict):
                    errs += validate(v, extra, root, f"{path}.{k}")
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errs.append(f"{path}: 항목이 {schema['minItems']}개 이상이어야 함")
        if "items" in schema:
            for i, v in enumerate(data):
                errs += validate(v, schema["items"], root, f"{path}[{i}]")
    if "anyOf" in schema:
        if not any(not validate(data, s, root, path) for s in schema["anyOf"]):
            errs.append(f"{path}: 허용된 형태(anyOf) 중 어느 것에도 맞지 않음")
    if "oneOf" in schema:
        n = sum(1 for s in schema["oneOf"] if not validate(data, s, root, path))
        if n != 1:
            errs.append(f"{path}: 허용된 형태(oneOf) 중 정확히 하나에 맞아야 함 ({n}개 맞음)")
    return errs


def load_schema(name):
    """패키지에 들어 있는 스키마. / Schema bundled with the package."""
    path = Path(__file__).resolve().parent.parent / "data" / "schema" / name
    return json.loads(path.read_bytes().decode("utf-8"))
