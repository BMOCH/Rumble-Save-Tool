// Read the per-slot collection vector in the game's serialized save structure.
const SLOT_DATA_SIZE = 4864;
const VECTOR_ORDER = [1, 2, 4, 5, 6, 7, 8, 0];
const u16 = (data, offset) => data[offset] * 256 + data[offset + 1];
const u32 = (data, offset) => data[offset] * 0x1000000 + data[offset + 1] * 0x10000 + data[offset + 2] * 0x100 + data[offset + 3];

export function slotCollectionStats(data, boxStart) {
  const slotStart = boxStart - SLOT_DATA_SIZE - 5;
  if (slotStart < 0 || boxStart > data.length) return null;
  let cursor = slotStart + SLOT_DATA_SIZE;
  const vectors = new Map();
  for (const expected of VECTOR_ORDER) {
    if (cursor >= data.length || data[cursor++] !== expected) return null;
    if (expected === 0) break;
    if (cursor + 4 > data.length) return null;
    const size = u16(data, cursor), count = u16(data, cursor + 2);
    cursor += 4;
    const end = cursor + (size + 1) * count;
    if (end > data.length) return null;
    vectors.set(expected, {size, count, start: cursor});
    cursor = end;
  }
  const vector = vectors.get(7);
  if (!vector || vector.size !== 16) return null;
  const records = [];
  for (let speciesId = 0; speciesId < vector.count; speciesId++) {
    const p = vector.start + speciesId * 17;
    if (data[p + 16] !== 0) return null;
    const packed = u32(data, p);
    records.push({
      collectionType: packed >>> 29,
      battleRoyal: [(packed >>> 26) & 7, (packed >>> 23) & 7, (packed >>> 20) & 7],
      defeated: u32(data, p + 4),
      normalForms: u32(data, p + 8),
      rareForms: u32(data, p + 12) | ((packed >>> 19) & 1),
      recordOffset: p,
    });
  }
  return records;
}
