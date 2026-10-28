from shop.utils.money import format_won


def daily_total(orders):
    return format_won(sum(o.total() for o in orders))
