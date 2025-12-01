import html

def tg_escape(text: str) -> str:
    """Екранує спецсимволи для HTML."""
    return html.escape(str(text or ""))

def spoiler(text: str) -> str:
    """Створює tg-spoiler."""
    return f"<tg-spoiler>{tg_escape(text)}</tg-spoiler>"

def bold(text: str) -> str:
    """Виділення жирним."""
    return f"<b>{tg_escape(text)}</b>"