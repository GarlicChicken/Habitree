def format_won(amount):
    """금액을 '45,000원'처럼 쓴다."""
    return f"{amount:,}원"


def parse_won(text):
    return int(text.replace(",", "").replace("원", "").strip())
