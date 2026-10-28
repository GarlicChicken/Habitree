"""find-in-tree 채점: 주문 요약에 할인을 보이고, 이미 있는 format_won을 다시 쓰는지. 작업 폴더에서 돈다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from shop.orders.model import Item, Order  # noqa: E402
from shop.reports.summary import order_summary  # noqa: E402

bad = []
o1 = Order(12, [Item("빵", 15000, 2), Item("우유", 15000, 1)])
if order_summary(o1) != "주문 #12 · 3개 · 45,000원":
    bad.append(f"no discount: {order_summary(o1)!r}")
o2 = Order(13, [Item("빵", 15000, 2), Item("우유", 15000, 1)], discount=5000)
if order_summary(o2) != "주문 #13 · 3개 · 40,000원 · 할인 5,000원":
    bad.append(f"with discount: {order_summary(o2)!r}")
src = Path("shop/reports/summary.py").read_text(encoding="utf-8")
if ":," in src or "format(" in src:
    bad.append("summary.py should reuse format_won instead of new number formatting")
print("\n".join(bad) or "ok")
sys.exit(1 if bad else 0)
