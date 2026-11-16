# Power calculation research

The displayed Power is the game's `BP` value. The stat screen displays `CPiiPersonalData::GetBP()`. The initialization script `CPiiPersonalData_init.pkc` contains the following calculation, recovered from its bytecode:

```text
weighted = 12 * sqrt(attack) + defense + 0.9 * hp_for_power
step = floor(weighted / 3.9)
power = integer(step ^ 1.1)
```

The game executes the arithmetic with 32-bit floating-point values and converts the final result to an integer by truncating it. Values near rounding boundaries require particular care. This is the core calculation: attack and defense must first be derived from species data, level, random seed, bonuses, and other game state.

`hp_for_power` is not always the visible maximum HP. In the normal initialization path, the script separately calculates it using species property 14, the capped level, a zero HP bonus, and a constant mode flag. An alternate path passes the current maximum HP instead. Transferred Pokemon can have their capped level adjusted, and the initialization script also contains a special cap adjustment after the core calculation; see the slot B verification below.

The attack helper uses species property 0 and the defense helper uses property 1. Both involve the saved stat bonus, the capped level, the random seed, and additional script-derived modifiers. The normal initialization routine resets the relevant stat registers to zero immediately before these calculations; the script makes separate boss adjustments. We have not yet independently reproduced the complete path from save bytes to these intermediate values.

## Intermediate stat findings

The game script supplies a species-specific base attack (property 0), base defense (property 1), and base HP (property 14). These are numeric game data, not the displayed star ratings. In the ordinary non-boss path, before any script-derived multipliers, it constructs the following components:

```text
attack_base = floor(sqrt(base_attack) * capped_level^2 / 2 + 5)
attack_spread = floor(capped_level^1.4)
attack_random = abs(signed_seed) % (2 * attack_spread + 1) - attack_spread

defense_base = floor(base_defense * capped_level / 16 + 5)
defense_spread = 1 if capped_level < 5 else 2 if capped_level < 10 else 3
defense_random = abs(signed_seed) % (2 * defense_spread + 1) - defense_spread
```

The attack value then applies powers of 1.4 using its saved bonus and a script-derived modifier, adds `attack_random`, clamps to at least 1, rounds up, and passes through further context-dependent logic. Defense uses corresponding defense modifiers and `defense_random`, clamped to at least 1. These descriptions are incomplete until the register modifiers, conversion rules, and game state are traced and tested. The seed is interpreted as a signed 32-bit integer by the VM; the minimum signed integer is a special overflow edge case.

For the normal HP-for-Power path when level is below 60, the extracted bytecode gives:

```text
base = floor(base_hp^0.66 * capped_level / 3)
hp_for_power = ceil(base * (capped_level + 20) / 80 + 20)
```

For Rattata, the game data gives base attack 72, defense 38, and HP 30. The HP formula gives **79 at level 30** and **82 at level 31**, matching the earlier controlled Rattata observation in SAVE_STRUCTURE.md. The backed-up save has a level-30 Rattata in slot A, record 986, with seed `0x00010000`, zero attack/defense bonuses, and zero high bonus words. Under the normal initialization path, registers 0-5 are reset before calculating these stats, so both attack and defense register multipliers are zero. Using those inputs produces:

| Level | Attack | Defense | HP-for-Power | Power |
| --- | ---: | ---: | ---: | ---: |
| 30 | 3770 | 75 | 79 | 388 |
| 31 | 4081 | 77 | 82 | 405 |

These numbers reproduce the previously recorded controlled Rattata observation when using that record's seed and changing only the level. This is a strong consistency check; it does not establish that the earlier observation used this exact Rattata, and it does not validate edge cases, cap behavior, or every species.

## Live verification

A Dolphin check on the US Wii version compared calculated Power with the visible values for 12 favorite records in save slot A. Every value matched: Aerodactyl 2277; Dialga 2489 and 2465; Moltres 2407; Mewtwo 2395, 2382 and 2380; Giratina 2387 and two at 2380; and two Palkia at 2384. The selected Aerodactyl was also matched by its Speedy trait and move pair. These observations cover six species and high levels; they do not establish correctness for every level, transfer cap, form, or unusual bonus value.

A further read-only comparison matched save records to live game objects by random seed, creation time, trainer ID, and level. All **988 matched records** in slot A matched the game's Power, spanning levels 28-117. This included 100 Pokemon with a different trainer ID, 13 records with nonzero bonuses, Heat Rotom, and Sky Shaymin. All matched objects had an in-game capped level equal to their saved level; therefore this did not test an active transfer cap. The nonzero bonuses in this sample were HP or speed bonuses; nonzero attack/defense bonuses remain unverified. One of 989 slot-A records could not be confidently matched in memory and was excluded.

The calculation uses the 12 form-specific stat sets explicitly initialized by the game and inherited stats for compatible forms. Heat Rotom matched 2118 and Sky Shaymin matched 2337 in the live comparison. Other forms and bonus values outside the tested range still need independent verification.

### Slot B and transfer caps

A second live comparison matched all 96 slot-B records, spanning saved levels 7-105. Seven transferred Pokemon had an active cap: each displayed Power 399, while their uncapped Power values ranged from 417 to 2335. The game checks the current slot trainer ID and progression, reduces the effective level for a transferred Pokemon, and when the resulting Power first drops below the progression threshold, sets the displayed Power to one less than that threshold. The editor now reads the slot owner, rank, and difficulty and applies this behavior. All seven capped records and all 89 uncapped records matched. This includes a Sunshine Cherrim whose form inherits its base-form stats.

The game saved while returning to the title screen and entering slot B during this check. Comparing the current save with the original backup showed no changes to any Pokemon box record in slots A, B, or C. The original backup was retained.

### Isolated synthetic verification

To cover cases absent from the real save, a separate Dolphin user profile and disposable slot-B save were used. The original backup and regular Dolphin profile were not modified. Each case was matched to a live game object using its random seed, creation time, trainer ID, and level, then the in-memory Power and effective level were compared with the calculation.

One sweep used 96 synthetic records covering levels 1-6 and Attack and Defense bonuses from -3 to +3. Every record matched. A second sweep used 96 synthetic foreign-trainer records at each rank and both difficulties. All **768 records** (96 per context) matched, including active and inactive caps across all eight thresholds:

| Difficulty | Ranks A, B, C, D thresholds | Matches |
| --- | --- | ---: |
| Normal | 100, 200, 400, 600 | 96 / 96 each |
| Advanced | 1000, 1200, 1500, 1800 | 96 / 96 each |

The calculation matched every tested level, bonus combination, and transfer context. It has not been checked against every possible signed 32-bit bonus value or boss-specific behavior, so untested game states may still differ.

## Save record fields

The decompiled `SD_PiiPersonalData::Data` and `CPiiPersonalData::Import` identify these fields in each 45-byte box record (the last byte is the vector terminator, not part of the 44-byte structure):

| Offset | Field |
| --- | --- |
| `+0x06` | Level, unsigned 16-bit big-endian |
| `+0x08` to `+0x0F` | Low 16 bits of four bonuses: maximum HP, attack, defense, speed |
| `+0x14` | 32-bit random seed, big-endian |
| `+0x18` to `+0x1F` | High 16 bits of the same four bonuses |
| `+0x28` | 32-bit original trainer ID, big-endian |

Each bonus is reconstructed as `(high << 16) | low`, then stored as a signed 32-bit integer. These field identities come from source reconstruction and still need cross-checking against live game behavior. The existing observation that editing the random seed changes displayed Power does not by itself establish which parts of the seed are used or how.

The decompiled rare-color test is `((seed & 0xffff) ^ (seed >> 16) ^ (trainer_id >> 16) ^ (trainer_id & 0xffff)) < 8`. The editor currently recognizes only the exact matching signature; it can therefore miss other rare-color seeds. Editing the seed can change shiny status.

## Next steps

Compare the recovered BP calculation against additional unmodified save records and displayed in-game values. Recover the remaining modifier calculations needed for boss-specific behavior. Separately test more signed bonus values and rare forms in an isolated test save. Never use the original save for mutation experiments.

## Sources

- [Stat screen displays GetBP](https://github.com/revvmp/pokemon-rumble-decomp/blob/main/src/game/ui/CUIPiiSpec.cpp)
- [Personal data import, rare-color test, and initialization script](https://github.com/revvmp/pokemon-rumble-decomp/blob/main/src/game/pokemon/CPiiPersonalData.cpp)
- [Save record structure](https://github.com/revvmp/pokemon-rumble-decomp/blob/main/include/game/io/SaveData.h)
