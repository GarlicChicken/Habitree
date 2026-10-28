"""메모 내보내기. / Exporting notes."""


def export_body(title, body):
    return f"# {title}\n\n{body.strip()}\n"
