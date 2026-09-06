"""Source-tree launcher for the command-line editor."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from rumble_save_tool.save_editor import main


if __name__ == "__main__":
    main()
