from shop.utils.money import format_won


def invoice_line(item):
    return f"{item.name} x{item.qty}: {format_won(item.price * item.qty)}"


def invoice_text(order):
    lines = [invoice_line(i) for i in order.items]
    lines.append(f"합계: {format_won(order.total())}")
    return "
".join(lines)
