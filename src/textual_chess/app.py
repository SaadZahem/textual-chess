import typing

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, HorizontalGroup, Vertical
from textual.css.query import NoMatches
from textual.events import Key
from textual.screen import ModalScreen
from textual.types import NoSelection
from textual.widgets import Button, Footer, Header, Select, Static

from textual_chess.chessboard import ChessboardMock
from textual_chess.chesspage import ChessScreen
from textual_chess.dialog import ChessOptionsDialog


class InstructionsPanel(Static):
    def compose(self) -> ComposeResult:
        yield Static(
            """
[bold]Instructions[/bold]
- Use arrow keys or mouse to select and move pieces.
- Press Enter or click to select/move.
- Highlighted squares show legal moves.
- Play against the bot!
        """
        )
        yield Button("Back", id="back-instructions")

    def on_mount(self) -> None:
        self.query_one(Button).focus()


class MainPanel(Static):
    def compose(self) -> ComposeResult:
        with HorizontalGroup():
            yield Button("New Game >", variant="primary", id="singleplayer")
            yield Select(
                [
                    ("Random Bot", "random"),
                    ("Greedy Bot", "greedy"),
                    ("Minimax Bot [dim](depth=2)[/]", "minimax"),
                    ("None", "None"),  # The option to cancel bot response for debugging
                ],
                prompt="Choose Bot",
                id="bot-select",
                disabled=True,
            )
        yield Button("Multiplayer", id="multiplayer", disabled=True)
        yield Button("Instructions", id="help")
        yield Button.warning("Show Modal", id="show-modal")

    @on(Button.Pressed, "#show-modal")
    def show_modal(self) -> None:
        self.app.push_screen(ChessOptionsDialog())

    def on_mount(self) -> None:
        self.query_one(Button).focus()
        bot_select = self.query_one("#bot-select", Select)
        bot_select.display = False

    def on_key(self, event: Key) -> None:
        if event.key == "right":
            if self.query_one("#singleplayer").has_focus:
                if self.query_one(Select).disabled:
                    self.toggle_bot_select()
                else:
                    self.query_one(Select).focus()
                event.stop()

        elif event.key == "left":
            if self.query_one(Select).has_focus:
                self.query_one(Button).focus()
                event.stop()

        elif event.key == "down":
            buttons = self.query(Button).exclude("Button:disabled")
            try:
                focused = typing.cast(Button, self.query_one("Button:focus"))
                i = list(buttons).index(focused)
                i = (i + 1) % len(buttons)
                buttons[i].focus()
                event.stop()
            except NoMatches:
                # bubble event to keep Select function
                return

        elif event.key == "up":
            buttons = self.query(Button).exclude("Button:disabled")
            try:
                focused = typing.cast(Button, self.query_one("Button:focus"))
                i = list(buttons).index(focused) - 1
                buttons[i].focus()
                event.stop()
            except NoMatches:
                return

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "singleplayer":
            self.toggle_bot_select()

    def toggle_bot_select(self) -> None:
        bot_select = self.query_one("#bot-select", Select)
        bot_select.display = not bot_select.display
        bot_select.disabled = not bot_select.disabled
        bot_select.focus()
        button = typing.cast(Button, self.query_one("#singleplayer"))
        arrow = "<" if bot_select.display else ">"
        button.label = button.label[:-1] + arrow


class HomeScreen(Static):
    def compose(self) -> ComposeResult:
        with Horizontal(id="home-screen"):
            yield ChessboardMock()
            with Vertical(id="right-panel"):
                yield MainPanel(id="main-panel")

    def switch_right_panel(self, panel: Static):
        right_panel = self.query_one("#right-panel", Vertical)
        for child in list(right_panel.children):
            child.remove()
        right_panel.mount(panel)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help":
            self.switch_right_panel(InstructionsPanel())
        elif event.button.id == "back-instructions":
            self.switch_right_panel(MainPanel())
        elif event.button.id == "multiplayer":
            pass  # Placeholder for future multiplayer
        # No else: all handled here
        # singleplayer is handled by MainPanel


class ChessApp(App):
    CSS_PATH = "styles.tcss"
    TITLE = "Chess TUI"
    SUB_TITLE = "Play chess in your terminal"

    BINDINGS = [
        Binding("^q", "quit", "Quit", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self.homescreen = HomeScreen()
        yield self.homescreen
        yield Footer()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "bot-select":
            bot_type = str(event.value) if event.value else "random"
            
            # important to not trigger the event again
            with event.select.prevent(Select.Changed):
                event.select.value = Select.BLANK
            
            self.query_one(MainPanel).toggle_bot_select()
            self.chessboard = ChessScreen(bot_type=bot_type)
            self.push_screen(self.chessboard)            


def main() -> None:
    app = ChessApp()
    app.run()


if __name__ == "__main__":
    main()
