from textual import on
from textual.app import ComposeResult
from textual.events import Key
from textual.screen import ModalScreen, ScreenResultType
from textual.widgets import Button, Static


class Dialog(ModalScreen[ScreenResultType]):
    def compose(self) -> ComposeResult:
        yield Static("Hello, world from Dialog!", id="content")

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.dismiss()