"""Build a standalone editor bundle with PyInstaller.

Run this from a Python development environment after installing
``requirements-build.txt``. The resulting executable does not need Python.
"""
from pathlib import Path
import argparse
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
APP_NAME = "RumbleSaveTool"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="build one executable instead of the default directory bundle",
    )
    args = parser.parse_args()
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build" / "pyinstaller"),
        "--specpath",
        str(ROOT / "build"),
        "--paths",
        str(ROOT / "src"),
        "--add-data",
        f"{ROOT / 'resources'}{os.pathsep}resources",
    ]
    if args.onefile:
        command.append("--onefile")
    command.append("editor_gui.py")
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
