"""Small presentation helpers shared by the Streamlit UI."""
def hp_bar(current: int, maximum: int, width: int = 12) -> str:
    maximum = max(1, maximum)
    filled = round(width * max(0, current) / maximum)
    return "[" + "#" * filled + "." * (width - filled) + "]"
