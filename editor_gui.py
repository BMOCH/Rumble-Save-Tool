"""Source-tree launcher for the packaged Pokémon Rumble editor."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from rumble_save_tool.editor_gui import Editor


if __name__ == "__main__":
    Editor().mainloop()
