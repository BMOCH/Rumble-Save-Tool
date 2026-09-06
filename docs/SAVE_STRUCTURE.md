# Pokemon Rumble Wii save structure

Applies to the supplied `savedata*.bin` files. All offsets refer to decrypted data. Multi-byte values below are big-endian.

## File layout

- File size: **0x34000 bytes** (212,992 bytes).
- Three save slots: **A, B, C**.
- First 20 bytes: **SHA-1 of all bytes from 0x14 onward**.
- Slot A money: **4-byte unsigned integer at `0x65`**, big-endian.
- Remaining header and slot metadata: not fully decoded.
- File encoding: additive obfuscation in 16-byte blocks; see `src/rumble_save_tool/inspect_saves.py`.

## Pokemon boxes

Each box contains a count followed by **45-byte (0x2D) records**:

```text
01 00 2C | count (2 bytes) | Pokemon records | 02 00 04 ...

The tested Slot A capacity is **1000 Pokémon**. A maxed experimental save contained 1001 A records and the game reported that it was one over the limit. Slot C being empty did not increase Slot A's capacity; the boxes use separate record areas.
```

```text
record_offset = box_start + index * 0x2D
box_end       = box_start + count * 0x2D
```

Indices start at zero. Box positions depend on preceding data lengths.

Locations in the original `savedata.bin`:

| Slot | Count offset | First record | Count |
|---|---|---|---:|
| A | `0x1360` | `0x1362` | 195 |
| B | `0x6B19` | `0x6B1B` | 96 |
| C | `0xB152` | `0xB154` | 62 |

## Save timestamps

The timestamp field is a 4-byte big-endian count of seconds since **2000-01-01 00:00:00**, using the console clock; timezone handling is unknown.

| Slot | Offset in the current samples |
|---|---|
| A | `0x1341` |
| B | `0x6AFA` |
| C | `0xB133` |

These fields sit `0x21` bytes before their box starts; absolute offsets shift with preceding data. A's timestamp in `savedata-metadata-only.bin` is **2026-09-04 16:22:45**. The B/C timestamp interpretation uses the same relative field layout.

## Selected Pokemon (slot A)

Offsets below are relative to A's box start. In the current saves:

| Offset | Absolute offset | Bytes | Field |
|---|---|---:|---|
| `-0x10` | `0x1352` | 3 | First three bytes of selected Pokemon's record at `+0x21`. |
| `-0x0D` | `0x1355` | 2 | Selected species ID, unsigned big-endian. |
| `-0x09` | `0x1359` | 4 | Four bytes of selected Pokemon's record at `+0x24`. |

Match the species ID and combined seven identity bytes to find the selected record. Other bytes in this metadata region are unknown. B/C selection fields have not been confirmed.

## Pokemon record

Current field interpretations used by the editor:

| Offset | Bytes | Field |
|---|---:|---|
| `+0x00` | 2 | Packed species and form: `species_id = value >> 7`. For supported form species, `form_no = (value & 0x7F) >> 2`; the bottom two bits remain unknown. This form encoding is confirmed for Rotom, Giratina, and Shaymin. Rotom groups are `0x00–0x03` Base, `0x04–0x07` Heat, `0x08–0x0B` Wash, `0x0C–0x0F` Frost, `0x10–0x13` Fan, and `0x14–0x17` Mow. |
| `+0x02` | 2 | Move slot 2 ID; zero means empty. |
| `+0x04` | 2 | Move slot 1 ID; zero means empty. |
| `+0x06` | 2 | Level/progression value stored as big-endian hex. The field can represent `0x0000–0xFFFF`; naturally observed records ranged from `0x0002` to `0x0075`. The true game-valid upper bound is unknown, and values above `0x0075` are experimental. A controlled Rattata edit `0x001E → 0x001F` changed power `388 → 405` and HP `79 → 82`. |
| `+0x08` | 8 | Unknown. |
| `+0x10` | 2 | Trait ID. High byte is zero in supplied records; exact field width unconfirmed. |
| `+0x12` | 2 | Flags: favorite is mask `0x0002` (bit 1 of byte `+0x13`). Other bits unknown. |
| `+0x14` | 4 | Individual value affecting power. Garchomp byte tests gave +2/+13/+4/+2, while `+0x15` gave +7 on two Machamp. Effects are quantized and species-specific; Dolphin preserves edits. Exact encoding unknown. |
| `+0x18` | 9 | Unknown. |
| `+0x21` | 7 | Unknown identity-related data. |
| `+0x28` | 4 | Identity/shiny value. For the confirmed shiny pattern, set this to the two 16-bit halves of `+0x14` in reverse order. Other identity uses remain unknown. |
| `+0x2C` | 1 | Unknown. |

The editor uses bytes `+0x22` through `+0x2B` as a ten-byte fingerprint when matching selected records. Its in-game purpose is unknown.

## Trait IDs

IDs are decimal. Unlisted IDs are unmapped.

| ID | Trait |
|---:|---|
| 0 | None |
| 1 | Speedy |
| 2 | Snappy |
| 3 | Punchy |
| 4 | Brawny |
| 5 | Hardy |
| 6 | Lucky |
| 7 | Healthy |
| 8 | Rally |
| 10 | Gutsy |
| 11 | Perky |
| 12 | Steady |
| 13 | Techie |
| 14 | Feisty |
| 15 | Mighty |
| 16 | Normal Guard |
| 17 | Fighting Guard |
| 18 | Flying Guard |
| 19 | Poison Guard |
| 20 | Ground Guard |
| 21 | Rock Guard |
| 22 | Bug Guard |
| 23 | Ghost Guard |
| 24 | Steel Guard |
| 25 | Dummy (test; “Explanation to dummy”) |
| 26 | Fire Guard |
| 27 | Water Guard |
| 28 | Grass Guard |
| 29 | Electric Guard |
| 30 | Psychic Guard |
| 31 | Ice Guard |
| 32 | Dragon Guard |
| 33 | Dark Guard |

Move ID names are mapped in `src/rumble_save_tool/constants.py` and `resources/data/moves.json`.

Trait effects (IDs are the values stored at record offset `+0x10`):

| ID | Trait | Effect |
|---:|---|---|
| 0 | None | No special effect |
| 1 | Speedy | Moves around faster |
| 2 | Snappy | Uses moves faster |
| 3 | Punchy | Higher Attack |
| 4 | Brawny | Higher HP |
| 5 | Hardy | Higher Defense |
| 6 | Lucky | Foes drop more P |
| 7 | Healthy | Slowly restores HP |
| 8 | Rally | Strengthens allies in multiplayer |
| 9 | Scrappy | Higher critical-hit rate |
| 10 | Gutsy | Very high critical-hit rate |
| 11 | Perky | Recovers quickly from status changes |
| 12 | Steady | Unaffected by status changes |
| 13 | Techie | Fewer-star moves become stronger |
| 14 | Feisty | Moves sweep foes farther |
| 15 | Mighty | Less affected by being swept away |
| 16 | Normal Guard | Resists Normal-type moves |
| 17 | Fighting Guard | Resists Fighting-type moves |
| 18 | Flying Guard | Resists Flying-type moves |
| 19 | Poison Guard | Resists Poison-type moves |
| 20 | Ground Guard | Resists Ground-type moves |
| 21 | Rock Guard | Resists Rock-type moves |
| 22 | Bug Guard | Resists Bug-type moves |
| 23 | Ghost Guard | Resists Ghost-type moves |
| 24 | Steel Guard | Resists Steel-type moves |
| 25 | Dummy (test) | Explanation to dummy |
| 26 | Fire Guard | Resists Fire-type moves |
| 27 | Water Guard | Resists Water-type moves |
| 28 | Grass Guard | Resists Grass-type moves |
| 29 | Electric Guard | Resists Electric-type moves |
| 30 | Psychic Guard | Resists Psychic-type moves |
| 31 | Ice Guard | Resists Ice-type moves |
| 32 | Dragon Guard | Resists Dragon-type moves |
| 33 | Dark Guard | Resists Dark-type moves |

| Move ID (hex) | Move |
|---|---|
| `0x0205` | Protect |
| `0x01B9` | Screech |

## Not yet decoded

- Power and HP formulas.
- Shiny behavior across other game versions/regions.
- Forms and low species bits.
- Full slot metadata and internal checksum rules.

Attack/defense star ratings are external species reference data in `resources/data/species.json`. Power and HP are not decoded save fields in this editor.

Species and the value at `+0x06` alone do not determine power.

For Garchomp, equal values at `+0x06` always have equal HP in the current sample. Power still varies at equal values, so the unknown individual fields contain an additional power input. No formula is implemented.
