from rich.console import Console
from rich.text import Text
from textual.strip import Strip

_console = Console()

def strip_text(markup: str) -> Strip:
    text = Text.from_markup(markup)
    segments = text.render(console=_console)
    return Strip(segments)