STATUSES = ("new", "paid", "shipped", "done")


def next_status(cur):
    i = STATUSES.index(cur)
    return STATUSES[min(i + 1, len(STATUSES) - 1)]
