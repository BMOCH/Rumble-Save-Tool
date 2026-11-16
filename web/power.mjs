// Power calculation for the game's normal, uncapped initialization path.
function uncappedPower(r, stats) {
  if (r.length < 44) return null;
  const u16 = p => r[p] * 256 + r[p + 1];
  const packed = u16(0), species = packed >> 7, form = (packed & 127) >> 2, level = u16(6), base = form ? stats.forms[`${species}:${form}`] : stats.species[species];
  if (!base || level < 1 || level > 127) return null;
  const view = new DataView(r.buffer, r.byteOffset, r.byteLength), signedSeed = view.getInt32(20);
  if (signedSeed === -2147483648) return null;
  const seed = Math.abs(signedSeed);
  const bonus = Array.from({length: 4}, (_, i) => (u16(24 + 2 * i) << 16) | u16(8 + 2 * i));
  if (bonus.some(v => v < -20 || v > 20)) return null;
  const f = Math.fround, pow = (a,b) => f(Math.pow(f(a),f(b)));
  const spread = Math.floor(pow(level, 1.4));
  const attackBase = Math.floor(f(f(f(pow(base.attack,.5) * f(level * level)) * .5) + 5));
  const attack = Math.ceil(Math.max(1, f(f(attackBase * pow(1.4,bonus[1])) + seed % (2*spread+1) - spread)));
  const defenseBase = Math.floor(f(f(f(base.defense * level) * .0625) + 5));
  const width = level < 5 ? 1 : level < 10 ? 2 : 3;
  const defense = Math.trunc(Math.max(1, f(f(defenseBase * pow(1.4,bonus[2])) + seed % (2*width+1) - width)));
  const hpBase = Math.floor(f(f(pow(base.hp,.66) * level) / 3));
  const hp = Math.ceil(f(f(f(hpBase * (level + (level < 60 ? 20 : 3000))) / f(level < 60 ? 80 : 3060)) + 20));
  const weighted = f(f(f(12 * pow(attack,.5)) + defense) + f(f(.9) * hp));
  const result = Math.trunc(pow(Math.floor(f(weighted / f(3.9))),1.1));
  return Number.isFinite(result) ? result : null;
}

export function slotPowerContext(data, boxStart) {
  const start = boxStart - 5 - 4864;
  if (start < 0 || boxStart > data.length) return null;
  const rank = data[start + 12], difficulty = data[start + 13];
  if (difficulty > 2 || rank < 1 || rank > 4) return null;
  return {rank, difficulty, owner: new DataView(data.buffer, data.byteOffset, data.byteLength).getUint32(start + 4832)};
}

export function estimatePower(r, stats, context = null) {
  const value = uncappedPower(r, stats);
  if (value === null || context === null) return value;
  const trainer = new DataView(r.buffer, r.byteOffset, r.byteLength).getUint32(40);
  if (trainer === context.owner || context.difficulty > 1) return value;
  const limit = [[100, 200, 400, 600], [1000, 1200, 1500, 1800]][context.difficulty][context.rank - 1];
  if (value < limit) return value;
  const trial = r.slice(); let level = trial[6] * 256 + trial[7];
  while (level > 1) {
    level--; trial[6] = level >>> 8; trial[7] = level & 255;
    const capped = uncappedPower(trial, stats);
    if (capped === null) return null;
    if (level === 1) return capped;
    if (capped < limit) return limit - 1;
  }
  return value;
}
