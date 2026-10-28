"""모델 대응표: (등급, 강도) 칸을 회사의 실제 모델 ID와 강도 값으로 옮긴다. / Vendor table.

정책(규칙 DB의 cell)은 회사와 무관한 칸으로 쓰고, 회사별 실제 모델은 이 표에서 읽는다.
기본 표는 data/vendors.json(형식: data/schema/vendors.schema.json)이고, 프로젝트의
.habitree/vendors.json이 있으면 항목 단위로 덮어쓴다(모델 하나의 가격만 바꾸기, 회사 더하기,
null로 모델·회사 빼기).

공개 함수(다른 명령과 다음 버전이 쓴다. 이름과 반환 형태를 바꾸지 않는다):
  load(ctx=None) -> dict                       기본 표 + 프로젝트 덮어쓰기, 스키마 검사
  resolve(cell, vendor, table=None) -> dict    칸 → 모델 ID·강도 값·이유
  price(model_id, table=None, on=None) -> dict | None
  deprecations(within_days=90, table=None, today=None, models=None) -> list[dict]
  checked_age_days(table=None, vendor=None, today=None) -> int | None | dict
"""
import copy
import json
from datetime import date, datetime
from importlib import resources

from . import HabitreeError
from . import io as hio
from .config import deep_merge
from .schema import load_schema, validate
from .timeutil import now_utc

TIERS = ("low", "mid", "high", "top")
EFFORTS = ("low", "medium", "high", "max")
# 회사들이 쓰는 강도 값을 약한 것부터. / Vendor effort values, weakest first.
VENDOR_EFFORT_ORDER = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
OVERRIDE_REL = ".habitree/vendors.json"
PRICE_KEYS = ("input", "output", "cache_read", "cache_write", "cache_write_long", "cache_storage_hour")
TIER_TEXT = {"low": {"ko": "하", "en": "low"}, "mid": {"ko": "중", "en": "mid"},
             "high": {"ko": "상", "en": "high"}, "top": {"ko": "최상", "en": "top"}}
EFFORT_TEXT = {"low": {"ko": "낮음", "en": "low"}, "medium": {"ko": "보통", "en": "medium"},
               "high": {"ko": "높음", "en": "high"}, "max": {"ko": "최대", "en": "max"}}


# ── 칸 · Cells ──

def parse_cell(value, lang="ko"):
    """'mid:medium', 'mid', {"tier": …} → {"tier", "effort"}. 강도를 빼면 medium. / Parse a cell."""
    if isinstance(value, dict):
        tier, effort = value.get("tier"), value.get("effort", "medium")
    else:
        text = str(value or "").strip().lower()
        tier, _, effort = text.partition(":")
        effort = effort or "medium"
    if tier not in TIERS or effort not in EFFORTS:
        raise HabitreeError(
            (f"칸 형식이 틀렸습니다: {value!r} (등급 {'·'.join(TIERS)}, 강도 {'·'.join(EFFORTS)}, 예: mid:medium)"
             if lang == "ko" else
             f"Bad cell: {value!r} (tier {'/'.join(TIERS)}, effort {'/'.join(EFFORTS)}, e.g. mid:medium)"))
    return {"tier": tier, "effort": effort}


def cell_str(cell):
    if not cell:
        return "-"
    return f"{cell['tier']}:{cell.get('effort', 'medium')}"


def cell_key(cell):
    """칸 순서(등급 먼저, 같으면 강도). / Order: tier first, then effort."""
    return TIERS.index(cell["tier"]), EFFORTS.index(cell.get("effort", "medium"))


# ── 불러오기 · Loading ──

def bundled():
    """패키지에 든 기본 표(새 사본). / A fresh copy of the bundled table."""
    text = resources.files("habitree.data").joinpath("vendors.json").read_text(encoding="utf-8")
    return json.loads(text)


def merge(base, over):
    """항목 단위 병합: 회사 → 칸 → 모델 하나까지 들어가 합치고, null이면 뺀다. / Entry-level merge."""
    out = copy.deepcopy(base)
    for key, val in (over or {}).items():
        if key != "vendors":
            out[key] = copy.deepcopy(val)
            continue
        vendors = out.setdefault("vendors", {})
        for vname, vdata in (val or {}).items():
            if vdata is None:
                vendors.pop(vname, None)
                continue
            cur = vendors.get(vname)
            if cur is None:
                vendors[vname] = copy.deepcopy(vdata)
                continue
            for k, v in vdata.items():
                if k == "models":
                    models = cur.setdefault("models", {})
                    for mid, entry in (v or {}).items():
                        if entry is None:
                            models.pop(mid, None)
                        elif isinstance(models.get(mid), dict) and isinstance(entry, dict):
                            models[mid] = deep_merge(models[mid], entry)
                        else:
                            models[mid] = copy.deepcopy(entry)
                elif isinstance(v, dict) and isinstance(cur.get(k), dict):
                    cur[k] = deep_merge(cur[k], v)
                else:
                    cur[k] = copy.deepcopy(v)
    return out


def problems(table):
    """스키마와 뜻 검사(칸이 가리키는 모델이 있는가). / Schema and semantic problems."""
    out = validate(table, load_schema("vendors.schema.json"))
    if out:
        return out
    for vname, v in table["vendors"].items():
        for tier, slot in v["tiers"].items():
            if isinstance(slot, str) and slot not in v["models"]:
                out.append(f"$.vendors.{vname}.tiers.{tier}: 없는 모델 / unknown model {slot!r}")
            if isinstance(slot, dict):
                target = v["tiers"].get(slot["tier"])
                if not isinstance(target, str):
                    out.append(f"$.vendors.{vname}.tiers.{tier}: 대신할 등급 {slot['tier']}에 모델이 없음 / "
                               f"substitute tier has no model")
    return out


def load(ctx=None):
    """기본 표에 프로젝트의 .habitree/vendors.json을 항목 단위로 덮어쓴 표. / Bundled table plus project overrides."""
    table = bundled()
    if ctx is not None:
        path = ctx.p(OVERRIDE_REL)
        if path.is_file():
            try:
                over = hio.load_json(path)
            except json.JSONDecodeError as e:
                raise HabitreeError(f"대응표 JSON이 깨졌습니다 / Broken JSON: {OVERRIDE_REL}: {e}")
            table = merge(table, over)
    found = problems(table)
    if found:
        raise HabitreeError("대응표에 문제가 있습니다 / The vendor table has problems:\n  " + "\n  ".join(found))
    return table


def _table(table):
    return table if table is not None else load()


# ── 찾기 · Lookup ──

def _candidates(name):
    """세션 기록·설정에 나오는 여러 표기를 표의 ID로. / Normalize spellings seen in logs and configs."""
    n = str(name or "").strip().lower()
    if n.endswith("[1m]"):
        n = n[:-4]
    out = [n]
    if "/" in n:
        out.append(n.rsplit("/", 1)[1])  # anthropic/claude-…, openai/gpt-…
    for prefix in ("anthropic.", "us.anthropic.", "eu.anthropic.", "global.anthropic."):
        if n.startswith(prefix):
            out.append(n[len(prefix):])  # Amazon Bedrock ID
    return out


def find_model(table, name):
    """(회사, 모델 ID, 항목) 또는 None. 고정 ID를 먼저, 다음에 별칭으로 찾는다. / Find by ID, then alias."""
    names = _candidates(name)
    for n in names:
        for vname, v in table["vendors"].items():
            for mid, entry in v["models"].items():
                if mid.lower() == n:
                    return vname, mid, entry
    for n in names:
        for vname, v in table["vendors"].items():
            for mid, entry in v["models"].items():
                if n in (a.lower() for a in entry.get("aliases", [])):
                    return vname, mid, entry
    return None


def tier_models(table, vendor):
    """등급 → 모델 ID(대신하는 칸은 따라가서). / Tier to model ID, following substitutes."""
    v = table["vendors"].get(vendor)
    if not v:
        return {}
    out = {}
    for tier in TIERS:
        slot = v["tiers"].get(tier)
        if isinstance(slot, dict):
            slot = v["tiers"].get(slot["tier"])
        if isinstance(slot, str):
            out[tier] = slot
    return out


def neutral_effort(table, vendor, value):
    """회사의 강도 값 → 중립 강도 이름(하한 비교용). / Vendor effort value to a neutral name."""
    v = str(value or "").strip().lower()
    emap = (table["vendors"].get(vendor) or {}).get("effort_map", {})
    for neutral in reversed(EFFORTS):
        if emap.get(neutral) == v:
            return neutral
    if v in EFFORTS:
        return v
    if v in ("xhigh", "max"):
        return "max"
    if v in ("none", "minimal"):
        return "low"
    return None


def _clamp_effort(value, supported):
    if not supported or value in supported:
        return value
    order = list(VENDOR_EFFORT_ORDER)
    idx = order.index(value) if value in order else len(order) - 1
    below = [e for e in supported if e in order and order.index(e) <= idx]
    if below:
        return max(below, key=order.index)
    known = [e for e in supported if e in order]
    return min(known, key=order.index) if known else supported[0]


def resolve(cell, vendor, table=None):
    """칸 → 이 회사에서 쓸 모델 ID와 강도 값, 그리고 이유. / Resolve a cell for one vendor.

    돌려주는 칸: vendor, vendor_name, cell, tier, effort, model, model_name, aliases, pinned,
    used_tier, used_effort, effort_param, effort_value, substituted, reason{ko,en}, price, checked, source.
    """
    table = _table(table)
    cell = parse_cell(cell)
    v = table["vendors"].get(vendor)
    if v is None:
        raise HabitreeError(f"대응표에 없는 회사 / unknown vendor: {vendor} "
                            f"(있는 것 / available: {', '.join(table['vendors'])})")
    tier, effort = cell["tier"], cell["effort"]
    used_tier, used_effort = tier, effort
    slot = v["tiers"].get(tier)
    sub = None
    if isinstance(slot, dict):
        sub = slot
        used_tier = slot["tier"]
        if slot.get("effort") and EFFORTS.index(slot["effort"]) > EFFORTS.index(used_effort):
            used_effort = slot["effort"]
        slot = v["tiers"].get(used_tier)
    if not isinstance(slot, str):
        raise HabitreeError(f"{v['name']}에는 {tier} 등급 모델이 없습니다 / {v['name']} has no {tier}-tier model")
    entry = v["models"][slot]
    emap = dict(v["effort_map"])
    emap.update(entry.get("effort_map", {}))
    wanted = emap.get(used_effort, used_effort)
    value = _clamp_effort(wanted, entry.get("efforts"))
    checked = entry.get("checked") or v["checked"]
    param = v.get("effort_param", "")
    ko = [f"{TIER_TEXT[tier]['ko']} 등급·{EFFORT_TEXT[effort]['ko']} 강도 → {slot}"
          + (f"({entry['name']})" if entry.get("name") else "") + f", {param}={value}."]
    en = [f"{tier} tier, {effort} effort → {slot}" + (f" ({entry['name']})" if entry.get("name") else "")
          + f", {param}={value}."]
    if sub:
        note = sub.get("note") or {}
        ko.append(note.get("ko", "") if isinstance(note, dict) else str(note))
        en.append(note.get("en", "") if isinstance(note, dict) else str(note))
    if value != wanted:
        ko.append(f"이 모델은 강도 {wanted}를 받지 않아 {value}로 낮췄다.")
        en.append(f"This model does not accept effort {wanted}; using {value}.")
    ko.append(f"등급과 모델의 대응은 회사의 모델 설명으로 맞춘 추정이다(대응표 확인일 {checked}).")
    en.append(f"The tier-to-model mapping is an estimate from the vendor's model descriptions (checked {checked}).")
    return {
        "vendor": vendor, "vendor_name": v["name"], "cell": cell_str(cell), "tier": tier, "effort": effort,
        "model": slot, "model_name": entry.get("name", slot), "aliases": list(entry.get("aliases", [])),
        "pinned": entry.get("pinned"), "used_tier": used_tier, "used_effort": used_effort,
        "effort_param": param, "effort_value": value, "substituted": sub is not None,
        "reason": {"ko": " ".join(x for x in ko if x), "en": " ".join(x for x in en if x)},
        "price": price(slot, table), "checked": checked, "source": entry.get("source", ""),
    }


# ── 가격 · Prices ──

def _as_date(value):
    if value is None:
        return now_utc().date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def price(model_id, table=None, on=None):
    """모델 하나의 가격(100만 토큰당 USD). 고정 ID·별칭·'회사/ID'·Bedrock ID로 찾는다. 모르면 None.
    / Price of one model, found by pinned ID, alias, 'provider/ID' or Bedrock ID; None when unknown.

    돌려주는 칸(값을 모르면 None):
      model, vendor, currency("USD"), per_tokens(1000000),
      input, output, cache_read, cache_write, cache_write_long, cache_storage_hour,
      above: [{prompt_tokens, input, output, …}]  프롬프트가 prompt_tokens를 넘을 때의 단가
      upcoming: [{from, …}]                      아직 시작하지 않은 가격 변경
      as_of, checked, source, note
    on(날짜)을 주면 그날 효력이 있는 가격(예고된 변경 반영). 기본은 오늘(UTC).
    """
    table = _table(table)
    found = find_model(table, model_id)
    if not found:
        return None
    vendor, mid, entry = found
    p = entry.get("price") or {}
    if p.get("input") is None and p.get("output") is None:
        return None
    day = _as_date(on)
    out = {"model": mid, "vendor": vendor, "currency": "USD", "per_tokens": 1000000}
    for k in PRICE_KEYS:
        out[k] = p.get(k)
    upcoming = []
    for ch in sorted(p.get("changes", []), key=lambda c: c["from"]):
        if _as_date(ch["from"]) <= day:
            for k in PRICE_KEYS:
                if k in ch:
                    out[k] = ch[k]
        else:
            upcoming.append(copy.deepcopy(ch))
    out["above"] = copy.deepcopy(p.get("above", []))
    out["upcoming"] = upcoming
    out["as_of"] = day.isoformat()
    out["checked"] = entry.get("checked") or table["vendors"][vendor]["checked"]
    out["source"] = entry.get("source", "")
    out["note"] = p.get("note", "")
    return out


# ── 관리 · Upkeep ──

def deprecations(within_days=90, table=None, today=None, models=None):
    """단종일이 within_days 안이거나(지난 것 포함) 상태가 deprecated·retired인 모델. models로 좁힌다.
    / Models retiring within the window (or past it), or marked deprecated/retired."""
    table = _table(table)
    day = _as_date(today)
    wanted = set(models) if models is not None else None
    out = []
    for vname, v in table["vendors"].items():
        for mid, entry in v["models"].items():
            if wanted is not None and mid not in wanted:
                continue
            retire = entry.get("retire")
            left = (_as_date(retire) - day).days if retire else None
            status = entry.get("status", "active")
            if (left is not None and left <= within_days) or status in ("deprecated", "retired"):
                out.append({"vendor": vname, "model": mid, "name": entry.get("name", mid), "status": status,
                            "retire": retire, "days_left": left, "replacement": entry.get("replacement"),
                            "source": entry.get("source", "")})
    return sorted(out, key=lambda d: (d["retire"] or "9999-12-31", d["model"]))


def checked_age_days(table=None, vendor=None, today=None):
    """가격·모델 확인일이 며칠 지났나(회사 안에서 가장 오래된 확인일 기준). vendor를 주면 int|None, 안 주면 {회사: int|None}.
    / Days since the oldest checked date of a vendor."""
    table = _table(table)
    day = _as_date(today)

    def age(v):
        dates = [v.get("checked")] + [m.get("checked") for m in v["models"].values()]
        dates = [d for d in dates if d]
        if not dates:
            return None
        return (day - _as_date(min(dates))).days

    if vendor is not None:
        v = table["vendors"].get(vendor)
        return age(v) if v else None
    return {name: age(v) for name, v in table["vendors"].items()}


def same_tier_alternatives(table, cell, exclude_vendor):
    """다른 회사의 같은 칸 모델(장애 대체용). / Same cell at other vendors, for outage fallback."""
    out = []
    for vname in table["vendors"]:
        if vname == exclude_vendor:
            continue
        try:
            r = resolve(cell, vname, table)
        except HabitreeError:
            continue
        out.append(r)
    return out
