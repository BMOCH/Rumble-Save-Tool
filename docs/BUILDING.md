# Building standalone releases

The editor uses only Python's standard library at runtime. Maintainers can
use PyInstaller to create a bundle that runs without a Python installation.

Install the build dependency in a development environment:

```powershell
python -m pip install -r requirements-build.txt
```

Build the default directory bundle:

```powershell
python build.py
```

Build a single executable instead:

```powershell
python build.py --onefile
```

Artifacts are written under `dist/`. The `resources/` directory is bundled,
including the species and move tables and the Rumble icon set.

Build on each target operating system separately. PyInstaller does not
cross-compile: a Windows build produces a Windows executable, a macOS build
produces a macOS application/binary, and a Linux build produces a Linux
binary. The source and build command are the same on all three systems.

The GitHub Actions workflow does this matrix build automatically. Pushing a
tag beginning with `v` (for example `v1.0.0`) creates a GitHub Release and
attaches the Windows, macOS, and Linux archives. The workflow uses GitHub's
built-in `GITHUB_TOKEN`; no additional secret is required. The repository's
Actions settings must allow workflows to write release contents.
