"""Calculate displayed Power for ordinary boxed Pokemon from their save record."""
import json
import math
import struct
from .paths import DATA

_DATA = json.loads((DATA / 'power_stats.json').read_text(encoding='utf-8'))
_STATS = _DATA['species']
_FORMS = _DATA['forms']


def _f(value):
    return struct.unpack('>f', struct.pack('>f', value))[0]


def _pow(base, exponent):
    return _f(math.pow(_f(base), _f(exponent)))


def _uncapped_power(record):
    """Return uncapped Power, or None for unsupported data.

    Runtime trainer caps and float rounding may change the result.
    """
    if len(record) < 44:
        return None
    packed = int.from_bytes(record[:2], 'big')
    species, form = packed >> 7, (packed & 0x7f) >> 2
    stats = _FORMS.get(f'{species}:{form}') if form else _STATS.get(str(species))
    level = int.from_bytes(record[6:8], 'big')
    if stats is None or not 1 <= level <= 127:
        return None
    seed = int.from_bytes(record[20:24], 'big', signed=True)
    if seed == -0x80000000:
        return None
    seed = abs(seed)
    bonuses = [int.from_bytes(record[24 + 2*i:26 + 2*i] + record[8 + 2*i:10 + 2*i], 'big', signed=True) for i in range(4)]
    if not all(-20 <= x <= 20 for x in bonuses):
        return None
    try:
        spread = math.floor(_pow(level, 1.4))
        attack_base = math.floor(_f(_f(_f(_pow(stats['attack'], .5) * _f(level * level)) * .5) + 5))
        attack = max(1, _f(_f(attack_base * _pow(1.4, bonuses[1])) + seed % (2 * spread + 1) - spread))
        attack = math.ceil(attack)
        defense_base = math.floor(_f(_f(_f(stats['defense'] * level) * .0625) + 5))
        width = 1 if level < 5 else 2 if level < 10 else 3
        defense = int(max(1, _f(_f(defense_base * _pow(1.4, bonuses[2])) + seed % (2 * width + 1) - width)))
        hp_base = math.floor(_f(_f(_pow(stats['hp'], .66) * level) / 3))
        scaled = _f(_f(hp_base * (level + (20 if level < 60 else 3000))) / _f(80 if level < 60 else 3060))
        hp = math.ceil(_f(scaled + 20))
        weighted = _f(_f(_f(12 * _pow(attack, .5)) + defense) + _f(_f(.9) * hp))
        return int(_pow(math.floor(_f(weighted / _f(3.9))), 1.1))
    except (OverflowError, ValueError, ZeroDivisionError):
        return None


def slot_power_context(data, box_start):
    """Read the owning trainer and progression from a slot's serialized header."""
    slot_start = box_start - 5 - 4864
    if slot_start < 0 or box_start > len(data):
        return None
    rank, difficulty = data[slot_start + 12:slot_start + 14]
    if difficulty > 2 or not 1 <= rank <= 4:
        return None
    owner = int.from_bytes(data[slot_start + 4832:slot_start + 4836], 'big')
    return owner, difficulty, rank


def estimate_power(record, context=None):
    """Calculate Power, applying the game's transfer cap when context is known."""
    value = _uncapped_power(record)
    if value is None or context is None:
        return value
    owner, difficulty, rank = context
    if int.from_bytes(record[40:44], 'big') == owner or difficulty > 1:
        return value
    limit = ((100, 200, 400, 600), (1000, 1200, 1500, 1800))[difficulty][rank - 1]
    if value < limit:
        return value
    trial = bytearray(record)
    level = int.from_bytes(trial[6:8], 'big')
    while level > 1:
        level -= 1
        trial[6:8] = level.to_bytes(2, 'big')
        capped_value = _uncapped_power(trial)
        if capped_value is None:
            return None
        if level == 1:
            return capped_value
        if capped_value < limit:
            return limit - 1
    return value
