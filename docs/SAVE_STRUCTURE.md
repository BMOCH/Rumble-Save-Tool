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

Move ID names are mapped in `src/rumble_save_tool/constants.py` and `resources/data/moves.json`.

Trait IDs and effects (IDs are the values stored at record offset `+0x10`; unlisted IDs are unmapped):

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
| `0x0000` | Empty |
| `0x0001` | B No Type Blast |
| `0x0002` | B No Type Restart |
| `0x0003` | B No Type Dash |
| `0x0004` | B Poisonpowder |
| `0x0005` | B Water Gun |
| `0x0006` | B Bonemerang |
| `0x0007` | B Fury Swipes |
| `0x0008` | B Poison Sting |
| `0x0009` | B Ember |
| `0x000A` | B Thunderbolt |
| `0x000B` | B Powder Snow |
| `0x000C` | B Thunderpunch |
| `0x000D` | B Gust |
| `0x000E` | B Rock Blast |
| `0x000F` | B Flamethrower |
| `0x0010` | B Water Pulse |
| `0x0011` | B Shadow Ball |
| `0x0012` | B Ancientpower |
| `0x0013` | B Ice Beam |
| `0x0014` | B Yawn |
| `0x0015` | B Hydro Pump |
| `0x0016` | B Thunder |
| `0x0017` | B Dragon Rage |
| `0x0018` | B Blizzard |
| `0x0019` | B Heat Wave |
| `0x001A` | B Razor Leaf |
| `0x001B` | B Bubble |
| `0x001C` | B Psywave |
| `0x001D` | B Poison Jab |
| `0x001E` | B Mach Punch |
| `0x001F` | B Attack Order |
| `0x0020` | B Sand Tomb |
| `0x0021` | B Confusion |
| `0x0022` | B Wing Attack |
| `0x0023` | B Ice Fang |
| `0x0024` | B Thunder Fang |
| `0x0025` | B Giga Drain |
| `0x0026` | B Whirlpool |
| `0x0027` | B Shadow Punch |
| `0x0028` | B Power Whip |
| `0x0029` | B Close Combat |
| `0x002A` | B Psycho Cut |
| `0x002B` | B Giga Impact |
| `0x002C` | B Ominous Wind |
| `0x002D` | B Aura Sphere |
| `0x002E` | B Dragon Claw |
| `0x002F` | B Magma Storm |
| `0x0030` | M2 Psycho Cut 1 |
| `0x0031` | M2 Psychic 1 |
| `0x0032` | M2 Psycho Cut 2 |
| `0x0033` | M2 Psychic 2 |
| `0x0034` | M2 Psycho Cut 3 |
| `0x0035` | M2 Psychic 3 |
| `0x0036` | Ice Ball |
| `0x0037` | Aqua Jet |
| `0x0038` | Aqua Tail |
| `0x0039` | Spacial Rend |
| `0x003A` | Vital Throw |
| `0x003B` | Dig |
| `0x003C` | Cut |
| `0x003D` | Rage |
| `0x003E` | Rock Throw |
| `0x003F` | Weather Ball |
| `0x0040` | Air Cutter |
| `0x0041` | Aeroblast |
| `0x0042` | Pursuit |
| `0x0043` | Doubleslap 5th |
| `0x0044` | Doubleslap 4th |
| `0x0045` | Doubleslap |
| `0x0046` | Doubleslap 2nd |
| `0x0047` | Doubleslap Finish |
| `0x0048` | Aurora Beam |
| `0x0049` | Octazooka |
| `0x004A` | Strength |
| `0x004B` | Shadow Sneak |
| `0x004C` | Gust |
| `0x004D` | Razor Wind |
| `0x004E` | Facade |
| `0x004F` | Facade L |
| `0x0050` | Karate Chop |
| `0x0051` | Brick Break |
| `0x0052` | Rock Wrecker |
| `0x0053` | Giga Impact |
| `0x0054` | Slash |
| `0x0055` | Crabhammer |
| `0x0056` | Cross Chop |
| `0x0057` | Attack Order |
| `0x0058` | Rapid Spin |
| `0x0059` | Ice Shard |
| `0x005A` | Rollout |
| `0x005B` | Psycho Cut |
| `0x005C` | Psychic |
| `0x005D` | Uproar 2 |
| `0x005E` | Uproar |
| `0x005F` | Uproar 4 |
| `0x0060` | Uproar 5 |
| `0x0061` | Water Spout |
| `0x0062` | Brine |
| `0x0063` | X-scissor |
| `0x0064` | Earthquake |
| `0x0065` | Shadow Claw |
| `0x0066` | Shadow Claw L |
| `0x0067` | Shadow Force |
| `0x0068` | Shadow Punch |
| `0x0069` | Thunderbolt |
| `0x006A` | Vacuum Wave |
| `0x006B` | Extremespeed |
| `0x006C` | Sky Uppercut |
| `0x006D` | Stone Edge |
| `0x006E` | Swift |
| `0x006F` | Solarbeam |
| `0x0070` | Fly |
| `0x0071` | Tackle |
| `0x0072` | Dive |
| `0x0073` | Muddy Water |
| `0x0074` | Slam |
| `0x0075` | Seed Bomb |
| `0x0076` | Bullet Seed |
| `0x0077` | Bullet Seed 4th |
| `0x0078` | Bullet Seed 3rd |
| `0x0079` | Bullet Seed 2nd |
| `0x007A` | Bullet Seed 1st |
| `0x007B` | Double Hit |
| `0x007C` | Double Hit Finish |
| `0x007D` | Egg Bomb |
| `0x007E` | Faint Attack |
| `0x007F` | Barrage |
| `0x0080` | Barrage 4th |
| `0x0081` | Barrage 3rd |
| `0x0082` | Barrage 2nd |
| `0x0083` | Barrage 1st |
| `0x0084` | Night Slash |
| `0x0085` | Peck |
| `0x0086` | Peck L |
| `0x0087` | Arm Thrust |
| `0x0088` | Arm Thrust 4th |
| `0x0089` | Arm Thrust 3rd |
| `0x008A` | Arm Thrust 2nd |
| `0x008B` | Arm Thrust Finish |
| `0x008C` | Horn Attack |
| `0x008D` | Wing Attack |
| `0x008E` | Aerial Ace |
| `0x008F` | Icicle Spear |
| `0x0090` | Icicle Spear 4th |
| `0x0091` | Icicle Spear 3rd |
| `0x0092` | Icicle Spear 2nd |
| `0x0093` | Icicle Spear 1st |
| `0x0094` | Vine Whip |
| `0x0095` | Test |
| `0x0096` | Shock Wave |
| `0x0097` | Quick Attack |
| `0x0098` | Roar Of Time |
| `0x0099` | Spike Cannon |
| `0x009A` | Spike Cannon 4th |
| `0x009B` | Spike Cannon 3rd |
| `0x009C` | Spike Cannon 2nd |
| `0x009D` | Spike Cannon 1st |
| `0x009E` | Dragon Claw |
| `0x009F` | Dragon Claw L |
| `0x00A0` | Triple Kick |
| `0x00A1` | Triple Kick 2 |
| `0x00A2` | Triple Kick Finish |
| `0x00A3` | Drill Peck |
| `0x00A4` | Surf |
| `0x00A5` | Double Kick |
| `0x00A6` | Double Kick 2 |
| `0x00A7` | Frenzy Plant |
| `0x00A8` | Hydro Cannon |
| `0x00A9` | Hydro Pump |
| `0x00AA` | Hyper Voice |
| `0x00AB` | Hyper Beam |
| `0x00AC` | Vicegrip |
| `0x00AD` | Pound |
| `0x00AE` | Razor Leaf |
| `0x00AF` | Aura Sphere |
| `0x00B0` | Bullet Punch |
| `0x00B1` | Power Whip |
| `0x00B2` | Power Gem |
| `0x00B3` | Scratch |
| `0x00B4` | Sucker Punch |
| `0x00B5` | Blast Burn |
| `0x00B6` | Eruption |
| `0x00B7` | Bone Rush 5th |
| `0x00B8` | Bone Rush 4th |
| `0x00B9` | Bone Rush |
| `0x00BA` | Bone Rush 2nd |
| `0x00BB` | Bone Rush Finish |
| `0x00BC` | Bonemerang |
| `0x00BD` | Bonemerang 2 |
| `0x00BE` | Magnet Bomb |
| `0x00BF` | Magical Leaf |
| `0x00C0` | Mach Punch |
| `0x00C1` | Mach Punch L |
| `0x00C2` | Pin Missile 5th |
| `0x00C3` | Pin Missile 4th |
| `0x00C4` | Pin Missile |
| `0x00C5` | Pin Missile 2nd |
| `0x00C6` | Pin Missile 1st |
| `0x00C7` | Water Gun |
| `0x00C8` | Fury Attack 5th |
| `0x00C9` | Fury Attack 4th |
| `0x00CA` | Fury Attack |
| `0x00CB` | Fury Attack 2nd |
| `0x00CC` | Fury Attack Finish |
| `0x00CD` | Fury Swipes |
| `0x00CE` | Fury Swipes 4th |
| `0x00CF` | Fury Swipes 3rd |
| `0x00D0` | Fury Swipes 2nd |
| `0x00D1` | Fury Swipes Finish |
| `0x00D2` | False Swipe |
| `0x00D3` | Mega Kick |
| `0x00D4` | Mega Punch |
| `0x00D5` | Megahorn |
| `0x00D6` | Wake-up Slap |
| `0x00D7` | Leaf Blade |
| `0x00D8` | Dragon Pulse |
| `0x00D9` | Fury Cutter |
| `0x00DA` | Fury Cutter 2 |
| `0x00DB` | Comet Punch 5th |
| `0x00DC` | Comet Punch |
| `0x00DD` | Comet Punch 3rd |
| `0x00DE` | Comet Punch 2nd |
| `0x00DF` | Comet Punch Finish |
| `0x00E0` | Rock Blast |
| `0x00E1` | Super Fang |
| `0x00E2` | Punishment |
| `0x00E3` | Reversal |
| `0x00E4` | Grass Knot |
| `0x00E5` | Low Kick |
| `0x00E6` | Psywave |
| `0x00E7` | Flail |
| `0x00E8` | Wring Out |
| `0x00E9` | Sonicboom |
| `0x00EA` | Seismic Toss |
| `0x00EB` | Night Shade |
| `0x00EC` | Crush Grip |
| `0x00ED` | Present |
| `0x00EE` | Magnitude |
| `0x00EF` | Hidden Power Normal |
| `0x00F0` | Hidden Power Fighting |
| `0x00F1` | Hidden Power Flying |
| `0x00F2` | Hidden Power Poison |
| `0x00F3` | Hidden Power Ground |
| `0x00F4` | Hidden Power Rock |
| `0x00F5` | Hidden Power |
| `0x00F6` | Hidden Power Ghost |
| `0x00F7` | Hidden Power Steel |
| `0x00F8` | Hidden Power ? |
| `0x00F9` | Hidden Power Fire |
| `0x00FA` | Hidden Power Water |
| `0x00FB` | Hidden Power Grass |
| `0x00FC` | Hidden Power Electric |
| `0x00FD` | Hidden Power Psychic |
| `0x00FE` | Hidden Power Ice |
| `0x00FF` | Hidden Power Dragon |
| `0x0100` | Hidden Power Dark |
| `0x0101` | Dragon Rage |
| `0x0102` | Cross Poison |
| `0x0103` | Smog |
| `0x0104` | Gunk Shot |
| `0x0105` | Twineedle |
| `0x0106` | Twineedle Finish |
| `0x0107` | Poison Gas |
| `0x0108` | Poison Jab |
| `0x0109` | Poison Jab L |
| `0x010A` | PoisonPowder |
| `0x010B` | Poison Sting |
| `0x010C` | Sludge |
| `0x010D` | Sludge Bomb |
| `0x010E` | Poison Tail |
| `0x010F` | Toxic |
| `0x0110` | Poison Fang |
| `0x0111` | Will-O-Wisp |
| `0x0112` | Flame Wheel |
| `0x0113` | Flamethrower |
| `0x0114` | Sacred Fire |
| `0x0115` | Fire Blast |
| `0x0116` | Heat Wave |
| `0x0117` | Ember |
| `0x0118` | Blaze Kick |
| `0x0119` | Lava Plume |
| `0x011A` | Fire Punch |
| `0x011B` | Iron Head |
| `0x011C` | Dark Pulse |
| `0x011D` | Rock Slide |
| `0x011E` | Air Slash |
| `0x011F` | Astonish |
| `0x0120` | Bite |
| `0x0121` | Sky Attack |
| `0x0122` | Zen Headbutt |
| `0x0123` | Extrasensory |
| `0x0124` | Headbutt |
| `0x0125` | Waterfall |
| `0x0126` | Twister |
| `0x0127` | Dragon Rush |
| `0x0128` | Needle Arm |
| `0x0129` | Fake Out |
| `0x012A` | Hyper Fang |
| `0x012B` | Stomp |
| `0x012C` | Bone Club |
| `0x012D` | Rolling Kick |
| `0x012E` | Bubble |
| `0x012F` | Constrict |
| `0x0130` | Rock Tomb |
| `0x0131` | Icy Wind |
| `0x0132` | Bubblebeam |
| `0x0133` | Mud Shot |
| `0x0134` | Iron Tail |
| `0x0135` | Rock Smash |
| `0x0136` | Energy Ball |
| `0x0137` | Crunch |
| `0x0138` | Focus Blast |
| `0x0139` | Shadow Ball |
| `0x013A` | Earth Power |
| `0x013B` | Crush Claw |
| `0x013C` | Crush Claw L |
| `0x013D` | Bug Buzz |
| `0x013E` | Acid |
| `0x013F` | Flash Cannon |
| `0x0140` | Luster Purge |
| `0x0141` | Mist Ball |
| `0x0142` | Double-edge |
| `0x0143` | Take Down |
| `0x0144` | Jump Kick |
| `0x0145` | Hi Jump Kick |
| `0x0146` | Flare Blitz |
| `0x0147` | Brave Bird |
| `0x0148` | Head Smash |
| `0x0149` | Skull Bash |
| `0x014A` | Powder Snow |
| `0x014B` | Blizzard |
| `0x014C` | Ice Punch |
| `0x014D` | Ice Beam |
| `0x014E` | Thunder |
| `0x014F` | Thunderpunch |
| `0x0150` | Lick |
| `0x0151` | Stun Spore |
| `0x0152` | Spark |
| `0x0153` | Thundershock |
| `0x0154` | Thunder Wave |
| `0x0155` | Zap Cannon |
| `0x0156` | Bounce |
| `0x0157` | Body Slam |
| `0x0158` | Force Palm |
| `0x0159` | Discharge |
| `0x015A` | Volt Tackle |
| `0x015B` | Dragonbreath |
| `0x015C` | Yawn |
| `0x015D` | Lovely Kiss |
| `0x015E` | Sing |
| `0x015F` | Spore |
| `0x0160` | Grasswhistle |
| `0x0161` | Hypnosis |
| `0x0162` | Sleep Powder |
| `0x0163` | Whirlpool 2 |
| `0x0164` | Whirlpool |
| `0x0165` | Whirlpool 4 |
| `0x0166` | Whirlpool 5 |
| `0x0167` | Clamp 2 |
| `0x0168` | Clamp |
| `0x0169` | Clamp 4 |
| `0x016A` | Clamp 5 |
| `0x016B` | Bind 2 |
| `0x016C` | Bind |
| `0x016D` | Bind 4 |
| `0x016E` | Bind 5 |
| `0x016F` | Sand Tomb 2 |
| `0x0170` | Sand Tomb |
| `0x0171` | Sand Tomb 4 |
| `0x0172` | Sand Tomb 5 |
| `0x0173` | Fire Spin 2 |
| `0x0174` | Fire Spin |
| `0x0175` | Fire Spin 4 |
| `0x0176` | Fire Spin 5 |
| `0x0177` | Wrap 2 |
| `0x0178` | Wrap |
| `0x0179` | Wrap 4 |
| `0x017A` | Wrap 5 |
| `0x017B` | Magma Storm 2 |
| `0x017C` | Magma Storm |
| `0x017D` | Magma Storm 4 |
| `0x017E` | Magma Storm 5 |
| `0x017F` | Confuse Ray |
| `0x0180` | Psybeam |
| `0x0181` | Signal Beam |
| `0x0182` | Supersonic |
| `0x0183` | Sweet Kiss |
| `0x0184` | Confusion |
| `0x0185` | Dynamicpunch |
| `0x0186` | Dizzy Punch |
| `0x0187` | Teeter Dance |
| `0x0188` | Water Pulse |
| `0x0189` | Rock Climb |
| `0x018A` | Ice Fang |
| `0x018B` | Thunder Fang |
| `0x018C` | Fire Fang |
| `0x018D` | Swagger |
| `0x018E` | Flatter |
| `0x018F` | Thrash |
| `0x0190` | Thrash 3 |
| `0x0191` | Outrage |
| `0x0192` | Outrage 3 |
| `0x0193` | Petal Dance |
| `0x0194` | Petal Dance 3 |
| `0x0195` | Selfdestruct |
| `0x0196` | Explosion |
| `0x0197` | Hammer Arm |
| `0x0198` | Giga Drain |
| `0x0199` | Leech Life |
| `0x019A` | Absorb |
| `0x019B` | Drain Punch |
| `0x019C` | Mega Drain |
| `0x019D` | Meteor Mash |
| `0x019E` | Charge Beam |
| `0x019F` | Metal Claw |
| `0x01A0` | Metal Claw L |
| `0x01A1` | Overheat |
| `0x01A2` | Psycho Boost |
| `0x01A3` | Leaf Storm |
| `0x01A4` | Draco Meteor |
| `0x01A5` | Superpower |
| `0x01A6` | Ingrain |
| `0x01A7` | Wood Hammer |
| `0x01A8` | Submission |
| `0x01A9` | Ominous Wind |
| `0x01AA` | Silver Wind |
| `0x01AB` | Ancientpower |
| `0x01AC` | Steel Wing |
| `0x01AD` | Close Combat |
| `0x01AE` | Close Combat L |
| `0x01AF` | Tri Attack |
| `0x01B0` | Smellingsalt |
| `0x01B1` | Harden |
| `0x01B2` | Mud-slap |
| `0x01B3` | Teleport |
| `0x01B4` | Revenge |
| `0x01B5` | Avalanche |
| `0x01B6` | Splash |
| `0x01B7` | Growl |
| `0x01B8` | Bide |
| `0x01B9` | Screech |
| `0x01BA` | Mirror Shot |
| `0x01BB` | Mud Bomb |
| `0x01BC` | Withdraw |
| `0x01BD` | Cosmic Power |
| `0x01BE` | Iron Defense |
| `0x01BF` | Acid Armor |
| `0x01C0` | Amnesia |
| `0x01C1` | Barrier |
| `0x01C2` | Defend Order |
| `0x01C3` | Defense Curl |
| `0x01C4` | Charge |
| `0x01C5` | Payback |
| `0x01C6` | Smokescreen |
| `0x01C7` | Sand-attack |
| `0x01C8` | Kinesis |
| `0x01C9` | Flash |
| `0x01CA` | Gravity |
| `0x01CB` | Charm |
| `0x01CC` | Featherdance |
| `0x01CD` | Counter |
| `0x01CE` | Mirror Coat |
| `0x01CF` | Metal Burst |
| `0x01D0` | Fake Tears |
| `0x01D1` | Metal Sound |
| `0x01D2` | Tail Whip |
| `0x01D3` | Leer |
| `0x01D4` | Aqua Ring |
| `0x01D5` | Aromatherapy |
| `0x01D6` | Heal Bell |
| `0x01D7` | Refresh |
| `0x01D8` | Safeguard |
| `0x01D9` | Glare |
| `0x01DA` | Torment |
| `0x01DB` | Disable |
| `0x01DC` | String Shot |
| `0x01DD` | Scary Face |
| `0x01DE` | Cotton Spore |
| `0x01DF` | Tailwind |
| `0x01E0` | Agility |
| `0x01E1` | Rock Polish |
| `0x01E2` | Tickle |
| `0x01E3` | Heal Order |
| `0x01E4` | Recover |
| `0x01E5` | Softboiled |
| `0x01E6` | Slack Off |
| `0x01E7` | Wish |
| `0x01E8` | Roost |
| `0x01E9` | Milk Drink |
| `0x01EA` | Rest |
| `0x01EB` | Leech Seed |
| `0x01EC` | Sharpen |
| `0x01ED` | Growth |
| `0x01EE` | Swords Dance |
| `0x01EF` | Howl |
| `0x01F0` | Tail Glow |
| `0x01F1` | Meditate |
| `0x01F2` | Nasty Plot |
| `0x01F3` | Belly Drum |
| `0x01F4` | Bulk Up |
| `0x01F5` | Calm Mind |
| `0x01F6` | Dragon Dance |
| `0x01F7` | Endeavor |
| `0x01F8` | Focus Energy |
| `0x01F9` | Focus Punch |
| `0x01FA` | Pain Split |
| `0x01FB` | Light Screen |
| `0x01FC` | Reflect |
| `0x01FD` | Spider Web |
| `0x01FE` | Mean Look |
| `0x01FF` | Block |
| `0x0200` | Haze |
| `0x0201` | Mist |
| `0x0202` | Mind Reader |
| `0x0203` | Lock-on |
| `0x0204` | Endure |
| `0x0205` | Protect |
| `0x0206` | Detect |
| `0x0207` | Fissure |
| `0x0208` | Sheer Cold |
| `0x0209` | Horn Drill |
| `0x020A` | Guillotine |
| `0x020B` | Perish Song |
| `0x020C` | Assurance |
| `0x020D` | Minimize |
| `0x020E` | Acupressure |
| `0x020F` | Helping Hand |
| `0x0210` | Toxic Spikes |
| `0x0211` | Spikes |
| `0x0212` | Thief |
| `0x0213` | Pay Day |
| `0x0214` | Knock Off |
| `0x0215` | Covet |
| `0x0216` | Bug-bite |
| `0x0217` | U-turn |
| `0x0218` | Whirlwind |
| `0x0219` | Roar |
| `0x021A` | Doom Desire |
| `0x021B` | Future Sight |
| `0x021C` | Secret Power |
| `0x021D` | Magic Coat |
| `0x021E` | Destiny Bond |
| `0x021F` | Morning Sun |
| `0x0220` | Synthesis |
| `0x0221` | Moonlight |
| `0x0222` | Seed Flare |
| `0x0223` | Dark Void |
| `0x0224` | Struggle |

## Not yet decoded

- Power and HP formulas.
- Shiny behavior across other game versions/regions.
- Forms and low species bits.
- Full slot metadata and internal checksum rules.

Attack/defense star ratings are external species reference data in `resources/data/species.json`. Power and HP are not decoded save fields in this editor.

Species and the value at `+0x06` alone do not determine power.

For Garchomp, equal values at `+0x06` always have equal HP in the current sample. Power still varies at equal values, so the unknown individual fields contain an additional power input. No formula is implemented.
