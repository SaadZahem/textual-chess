import re

from textual.reactive import reactive, var
from textual.widgets import Static

class ChessPlayer(Static):
    material = reactive('')
    advantage = var(0)

    def __init__(self, name: str, color: str, is_bot: bool = False, bot_type: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player_name = name
        self.color = color  # 'white' or 'black'
        self.is_bot = is_bot
        self.bot_type = bot_type

    def render(self) -> str:
        lines = []
        lines.append(f"{self.player_name} ({self.color.capitalize()})")
        lines.append(f"{self.material}" + (f" +{self.advantage}" if self.advantage > 0 else ""))
        return "\n".join(lines)
    
    def watch_advantage(self, old_advantage: int, new_advantage: int):
        product = old_advantage * new_advantage
        if product < 0:
            self.refresh()
        elif product == 0 and old_advantage != new_advantage:
            self.refresh()
        else:
            pass
    
    def validate_material(self, material: str) -> str:
        """Arranges material from low to high, e.g. pppp NBB R Q"""
        material_list = list(material)
        material_list.sort()
        material = ' '.join(reversed(material_list))  # list reversed so that pawns come first
        material = material.rstrip()  # removes trailing space created after sorting
        material = re.sub(r"(.) (?=\1)", r"\1", material)  # removes spaces between identical pieces
        return material
    