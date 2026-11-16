"""Read-only parsers for additional per-slot collection data."""

SLOT_DATA_SIZE = 4864
SLOT_PREFIX_SIZE = SLOT_DATA_SIZE + 5  # slot data, vector tag, element size and count
SLOT_VECTOR_ORDER = (1, 2, 4, 5, 6, 7, 8, 0)


def slot_collection_stats(data, box_start):
    """Return the game's per-species collection records, or None if malformed.

    The collection vector is stored in each slot after its personal-data,
    Battle Royal, and statistic vectors. Each serialized vector element has a
    trailing VECTOR_STRUCT_NONE byte in addition to its declared data size.
    """
    slot_start = box_start - SLOT_PREFIX_SIZE
    if slot_start < 0 or box_start > len(data):
        return None

    cursor = slot_start + SLOT_DATA_SIZE
    vectors = {}
    for expected_type in SLOT_VECTOR_ORDER:
        if cursor >= len(data):
            return None
        vector_type = data[cursor]
        cursor += 1
        if vector_type != expected_type:
            return None
        if vector_type == 0:
            break
        if cursor + 4 > len(data):
            return None
        size = int.from_bytes(data[cursor:cursor + 2], 'big')
        count = int.from_bytes(data[cursor + 2:cursor + 4], 'big')
        cursor += 4
        end = cursor + (size + 1) * count
        if end > len(data):
            return None
        vectors[vector_type] = (size, count, cursor)
        cursor = end

    entry = vectors.get(7)
    if entry is None:
        return None
    size, count, start = entry
    if size != 16:
        return None

    result = {}
    for species_id in range(count):
        offset = start + species_id * (size + 1)
        if data[offset + size] != 0:
            return None
        packed, defeats, normal_forms, rare_forms = (
            int.from_bytes(data[offset + i:offset + i + 4], 'big')
            for i in (0, 4, 8, 12)
        )
        result[species_id] = {
            'record_offset': offset,
            'collection_type': packed >> 29,
            'battle_royal': (
                (packed >> 26) & 7,  # Normal
                (packed >> 23) & 7,  # Hard
                (packed >> 20) & 7,  # Easy
            ),
            'defeated': defeats,
            'normal_forms': normal_forms,
            'rare_forms': rare_forms | ((packed >> 19) & 1),
        }
    return result
