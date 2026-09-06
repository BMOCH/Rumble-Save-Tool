# Data and resource files

The editor's bundled assets are under `resources/`.

Required at runtime:

- `resources/data/species.json` — species, star ratings, and form metadata.
- `resources/data/moves.json` — the observed internal move ID table.
- `resources/data/platinum_valid_moves.json` — valid move choices by species.
- `resources/rumble_icons/` — species images.

Optional:

- `resources/data/platinum_valid_moves.csv` is a human-readable export of the
  JSON compatibility table. The GUI does not load it.
