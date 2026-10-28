def shorten(text, width=20):
    return text if len(text) <= width else text[: width - 1] + "…"
