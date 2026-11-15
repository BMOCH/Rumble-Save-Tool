const SIZE = 0x34000, STRIDE = 45;
const $ = id => document.getElementById(id);
const status = message => $('status').textContent = message;
let data, boxes, species, moves;
const u16 = (a, p) => a[p] * 256 + a[p + 1];
const put16 = (a, p, v) => { a[p] = v >>> 8; a[p + 1] = v & 255; };
const digest = async a => new Uint8Array(await crypto.subtle.digest('SHA-1', a));
const equal = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
function sections(a) {
  const found = [];
  for (let p = 0; p < a.length - 5; p++) {
    if (a[p] !== 1 || a[p + 1] !== 0 || a[p + 2] !== 44) continue;
    const count = u16(a, p + 3), start = p + 5, end = start + count * STRIDE;
    if (end + 3 <= a.length && a[end] === 2 && a[end + 1] === 0 && a[end + 2] === 4) found.push({start, count});
  }
  if (found.length !== 3) throw Error(`Expected three Pokémon boxes, found ${found.length}.`);
  return found;
}
async function decode(raw) {
  if (raw.length !== SIZE) throw Error(`Expected ${SIZE} bytes; got ${raw.length}.`);
  const a = raw.slice();
  for (let chunk = 0x33ff; chunk >= 0; chunk--) {
    const p = chunk * 16;
    for (let i = 0; i < 16; i++) a[p + i] = (a[p + i] - a[(p + ((chunk + i) & 15) - 16 + SIZE) % SIZE]) & 255;
  }
  if (!equal(await digest(a.slice(20)), a.slice(0, 20))) throw Error('Save checksum does not match. Check that this is a Pokémon Rumble savedata.bin.');
  sections(a);
  return a;
}
async function encode(a) {
  if (a.slice(-16).some(Boolean)) throw Error('The final 16 bytes of the save must be zero.');
  const out = a.slice(); out.set(await digest(out.slice(20)), 0);
  for (let chunk = 1; chunk < 0x3400; chunk++) {
    const p = chunk * 16;
    for (let i = 0; i < 16; i++) out[p + i] = (out[p + i] + out[p + ((chunk + i) & 15) - 16]) & 255;
  }
  return out;
}
function dexOffset(id) { const off = boxes[0].start + boxes[0].count * STRIDE + 0x147 + (id - 1) * 0x11; if (id < 1 || off + 15 >= data.length) throw Error('Invalid Pokédex entry.'); return off; }
function option(select, value, label) { select.add(new Option(label, value)); }
function currentOffset() { const box = boxes[$('slot').selectedIndex]; return box.start + Number($('record').value) * STRIDE; }
function refreshList(selected = 0) {
  const list = $('record'), box = boxes[$('slot').selectedIndex]; list.replaceChildren();
  for (let i = 0; i < box.count; i++) { const p = box.start + i * STRIDE, id = u16(data, p) >> 7; option(list, i, `${i + 1}. ${species[id]?.name || `Unknown (${id})`}${data[p + 19] & 2 ? ' ♥' : ''}`); }
  list.value = String(Math.min(selected, box.count - 1));
  $('pokemon').querySelectorAll('input, select, button').forEach(el => el.disabled = !box.count);
  if (box.count) loadPokemon();
}
function loadPokemon() {
  const f = $('pokemon').elements, p = currentOffset(), packed = u16(data, p);
  f.species.value = packed >> 7; f.form.value = (packed & 127) >> 2;
  for (const [name, pos] of [['move1',4],['move2',2],['trait',16],['strength',6]]) {
    const value = u16(data, p + pos); if (f[name].tagName === 'SELECT' && ![...f[name].options].some(o => o.value === String(value))) option(f[name], value, `Unknown (${value})`); f[name].value = value;
  }
  f.individual.value = Array.from(data.slice(p + 20, p + 24), n => n.toString(16).padStart(2, '0')).join('');
  f.favorite.checked = !!(data[p + 19] & 2);
  f.shiny.checked = equal(data.slice(p + 40, p + 44), new Uint8Array([data[p + 22], data[p + 23], data[p + 20], data[p + 21]]));
}
function loadDex() {
  const f = $('dex').elements, p = dexOffset(Number(f.species.value));
  f.obtained.checked = data[p] >= 0x60; f.crown.value = [96,100,104,108].includes(data[p]) ? data[p] : 96;
  f.forms.value = data[p + 11]; f.shiny.checked = data[p + 15] === 1; f.centered.checked = !!(data[p + 1] & 128);
}
function changed() { status('Changes applied in memory. Download the edited save when you are ready.'); }
async function init() {
  const [s, m] = await Promise.all([fetch('resources/data/species.json'), fetch('resources/data/moves.json')]);
  if (!s.ok || !m.ok) throw Error('Could not load the species and move data.');
  species = (await s.json()).species; moves = await m.json();
  for (const [id, item] of Object.entries(species)) { option($('pokemon').elements.species, id, `${id} · ${item.name}`); option($('dex').elements.species, id, `${id} · ${item.name}`); }
  for (const [id, name] of Object.entries(moves)) for (const key of ['move1','move2']) option($('pokemon').elements[key], id, `${id} · ${name}`);
  $('file').disabled = false;
}
$('file').disabled = true;
$('file').addEventListener('change', async e => {
  const file = e.target.files[0]; if (!file) return;
  try { const loaded = await decode(new Uint8Array(await file.arrayBuffer())); data = loaded; boxes = sections(data); $('money').value = new DataView(data.buffer).getUint32(0x65); $('editor').hidden = false; refreshList(); loadDex(); status(`Loaded ${file.name}. Checksum and box structure are valid.`); }
  catch (err) { status(`Could not open save: ${err.message}`); }
  e.target.value = '';
});
$('slot').addEventListener('change', () => refreshList()); $('record').addEventListener('change', loadPokemon); $('dex').elements.species.addEventListener('change', loadDex);
$('moneyApply').addEventListener('click', () => { const input = $('money'); if (!input.checkValidity() || input.value === '') { input.reportValidity(); return; } new DataView(data.buffer).setUint32(0x65, Number(input.value)); changed(); });
$('pokemon').addEventListener('submit', e => {
  e.preventDefault(); const f = e.target.elements, p = currentOffset(), id = Number(f.species.value), individual = f.individual.value.match(/../g).map(x => parseInt(x, 16));
  put16(data, p, (id << 7) | (Number(f.form.value) << 2) | (data[p + 1] & 3));
  for (const [name, pos] of [['move1',4],['move2',2],['trait',16],['strength',6]]) put16(data, p + pos, Number(f[name].value));
  data.set(individual, p + 20); data[p + 19] = f.favorite.checked ? data[p + 19] | 2 : data[p + 19] & 253;
  data.set(f.shiny.checked ? [individual[2], individual[3], individual[0], individual[1]] : [0,0,0,0], p + 40);
  const d = dexOffset(id); if (data[d] < 96) data[d] = 96; data[d + 11] |= 1; if (f.shiny.checked) data[d + 15] = 1;
  refreshList(Number($('record').value)); loadDex(); changed();
});
$('dex').addEventListener('submit', e => { e.preventDefault(); const f = e.target.elements, p = dexOffset(Number(f.species.value)); data[p] = f.obtained.checked ? Number(f.crown.value) : 0; data[p + 1] = f.centered.checked ? data[p + 1] | 128 : data[p + 1] & 127; data[p + 11] = Number(f.forms.value); data[p + 15] = f.shiny.checked ? 1 : 0; changed(); });
$('download').addEventListener('click', async () => { try { const output = await encode(data); const url = URL.createObjectURL(new Blob([output], {type:'application/octet-stream'})); const a = document.createElement('a'); a.href = url; a.download = 'savedata.bin'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); status('Edited save downloaded.'); } catch (err) { status(`Could not save: ${err.message}`); } });
init().catch(err => status(err.message));
