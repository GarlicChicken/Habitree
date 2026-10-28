from shop.utils.money import format_won


def order_summary(order):
    """주문 한 줄 요약. 예: '주문 #12 · 3개 · 45,000원'"""
    count = sum(i.qty for i in order.items)
    return f"주문 #{order.number} · {count}개 · {format_won(order.total())}"
