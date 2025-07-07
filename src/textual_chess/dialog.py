from enum import Enum
import typing

from textual.app import ComposeResult, RenderResult
from textual.containers import Grid, Container, Center, HorizontalGroup
from textual.events import Key
from textual.widgets import Static, Button, Label

from textual_chess.modal import Dialog

class ChessOptions(Enum):
    Takeback = "Takeback"
    Resign = "Resign"
    Draw = "Draw"
    FlipBoard = "Flip Board"
    CopyFEN = "Copy FEN"
    Return = "Return"


class ChessOptionsDialog(Dialog[ChessOptions]):
    def compose(self) -> ComposeResult:
        with Container() as container:
            container.border_title = "Options Menu"
            container.border_subtitle = "<Esc> to dismiss"
            options = iter(ChessOptions)

            for _ in range(3):
                with HorizontalGroup():
                    for _ in range(2):
                        yield DialogButton(next(options).value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(ChessOptions(event.button.label))
    
    def on_key(self, event: Key) -> None:
        keys = {"down": 2, "up": -2, "right": 1, "left": -1}
        if event.key in keys:
            self.move_focus(keys[event.key])
    
    def move_focus(self, direction: int) -> None:
        focused = self.query_one("DialogButton:focus")
        focused_button = typing.cast(DialogButton, focused)
        buttons = list(self.query(DialogButton))
        i = buttons.index(focused_button) + direction
        i %= len(buttons)
        buttons[i].focus()
        

class DialogButton(Button):
    pass