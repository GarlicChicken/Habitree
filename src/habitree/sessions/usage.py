"""토큰을 돈으로, 세션을 합계로. core/vendors.py의 price()로 요청마다 그날의 단가를 쓴다. / Cost and totals.

- 캐시 쓰기는 5분(cache_write)과 1시간(cache_write_long) 단가를 나눠 쓴다.
- 프롬프트(입력 + 캐시 읽기 + 캐시 쓰기)가 표의 above 구간을 넘으면 그 구간 단가를 쓴다.
- 모르는 모델은 0원이 아니라 '모름'(None). 단가 칸이 비면 그 칸을 빼고 '일부만 셈'으로 표시한다.
- 웹 검색 같은 요청당 요금과 지역 처리 가산은 넣지 않는다(docs/spec/audit.md).
"""
from ..core import vendors
from .model import MAIN, category, iso

RATE_FOR = (("input", "input"), ("output", "output"), ("cache_read", "cache_read"),
            ("cache_write_5m", "cache_write"), ("cache_write_1h", "cache_write_long"))
KEYS = ("input", "output", "cache_read", "cache_write")


class Pricer:
    def __init__(self, table=None):
        self.table = table if table is not None else vendors.load()
        self._cache = {}
        self.unpriced, self.partial = set(), set()

    def rates(self, model, day, prompt=0):
        if (model, day) not in self._cache:
            self._cache[(model, day)] = vendors.price(model, self.table, on=day) if model else None
        p = self._cache[(model, day)]
        if p is None:
            return None
        r = {k: p.get(k) for k in ("input", "output", "cache_read", "cache_write", "cache_write_long")}
        for band in sorted(p.get("above") or [], key=lambda b: b.get("prompt_tokens", 0)):
            if prompt > band.get("prompt_tokens", 0):
                r.update({k: v for k, v in band.items() if k in r and v is not None})
        return r

    def cost(self, tokens, model, day=None):
        """토큰 묶음의 USD(모르면 None). / USD for a token bundle, None when unknown."""
        prompt = sum(tokens.get(k, 0) for k in ("input", "cache_read", "cache_write_5m", "cache_write_1h"))
        r = self.rates(model, day, prompt)
        if r is None:
            if prompt + tokens.get("output", 0):
                self.unpriced.add(model or "?")
            return None
        usd = 0.0
        for field, key in RATE_FOR:
            if tokens.get(field):
                if r.get(key) is None:
                    self.partial.add(model)
                else:
                    usd += tokens[field] * r[key] / 1e6
        return usd

    def request(self, req):
        return self.cost(req.tokens(), req.model, req.ts.date() if req.ts else None)


def tier_of(table, model):
    """모델 → 등급. 대응표에 등급이 없는 옛 Claude 모델은 이름으로 짐작한다(추정). / Tier of a model."""
    found = vendors.find_model(table, model or "")
    if found and found[2].get("tier"):
        return found[2]["tier"]
    name = (found[1] if found else str(model or "")).lower()
    return next((t for fam, t in (("fable", "top"), ("opus", "high"), ("sonnet", "mid"), ("haiku", "low"))
                 if fam in name), None)


def _tok(t):
    return {"input": t["input"], "output": t["output"], "cache_read": t["cache_read"],
            "cache_write": t["cache_write_5m"] + t["cache_write_1h"]}


def _add(dst, src):
    for k in KEYS:
        dst[k] = dst.get(k, 0) + src.get(k, 0)


def summarize(sessions, pricer):
    """세션별·모델별 토큰과 비용, 도구 호출 수(내용 없이). / Per-session and per-model totals, no content."""
    rows, models, total = [], {}, {"requests": 0, "lines": 0, "tool_calls": 0, "cost_usd": 0.0, "complete": True}
    tools = {}
    for ses in sessions:
        row = {"id": ses.id, "started": iso(ses.started), "ended": iso(ses.ended), "versions": sorted(ses.versions),
               "requests": len(ses.requests), "lines": 0, "tool_calls": len(ses.calls),
               "subagents": sum(1 for c in ses.contexts() if c != MAIN), "cost_usd": 0.0, "complete": True,
               "models": {}}
        for r in ses.requests.values():
            row["lines"] += r.lines
            t = _tok(r.tokens())
            for bucket in (row["models"].setdefault(r.model or "?", {"requests": 0, "cost_usd": 0.0}),
                           models.setdefault(r.model or "?", {"requests": 0, "cost_usd": 0.0})):
                bucket["requests"] += 1
                _add(bucket, t)
            usd = pricer.request(r)
            if usd is None:
                if any(t.values()):
                    row["complete"] = False
                    row["models"][r.model or "?"]["cost_usd"] = models[r.model or "?"]["cost_usd"] = None
                continue
            row["cost_usd"] += usd
            for bucket in (row["models"][r.model or "?"], models[r.model or "?"]):
                if bucket["cost_usd"] is not None:
                    bucket["cost_usd"] += usd
        for c in ses.calls.values():
            tools[c.name] = tools.get(c.name, 0) + 1
        for k in ("requests", "lines", "tool_calls", "cost_usd"):
            total[k] += row[k]
        total["complete"] = total["complete"] and row["complete"]
        rows.append(row)
    total["tokens"] = {}
    for m in models.values():
        _add(total["tokens"], m)
    cats = {}
    for name, n in tools.items():
        cats[category(name)] = cats.get(category(name), 0) + n
    total["tools"] = dict(sorted(tools.items(), key=lambda x: -x[1]))
    total["categories"] = dict(sorted(cats.items(), key=lambda x: -x[1]))
    return rows, dict(sorted(models.items(), key=lambda x: -(x[1]["cost_usd"] or 0))), total
