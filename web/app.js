import { estimatePower, slotPowerContext } from './power.mjs';
import { slotCollectionStats } from './save_stats.mjs';
const SIZE = 0x34000, STRIDE = 45;
const $ = id => document.getElementById(id);
const status = message => $('status').textContent = message;
let data, boxes, species, moves, powerStats, collectionData;
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
function loadCollectionData() { collectionData = boxes.map(box => slotCollectionStats(data, box.start)); }
function refreshList(selected = 0) {
  const list = $('record'), box = boxes[$('slot').selectedIndex]; list.replaceChildren();
  for (let i = 0; i < box.count; i++) { const p = box.start + i * STRIDE, id = u16(data, p) >> 7; const power = estimatePower(data.subarray(p, p + STRIDE), powerStats, slotPowerContext(data, boxes[$('slot').selectedIndex].start)); option(list, i, `${i + 1}. ${species[id]?.name || `Unknown (${id})`} - Power ${power === null ? '--' : power}${data[p + 19] & 2 ? ' favorite' : ''}`); }
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
  const power = estimatePower(data.subarray(p, p + STRIDE), powerStats, slotPowerContext(data, boxes[$('slot').selectedIndex].start));
  const context = slotPowerContext(data, boxes[$('slot').selectedIndex].start);
  $('power-value').textContent = power === null ? 'Power unavailable for this record.' : `Power: ${power}${context ? ' (includes transfer cap)' : ' (uncapped; slot progression unavailable)'}`;
  f.favorite.checked = !!(data[p + 19] & 2);
  f.shiny.checked = equal(data.slice(p + 40, p + 44), new Uint8Array([data[p + 22], data[p + 23], data[p + 20], data[p + 21]]));
}
function renderDex() {
  const rows = $('dex-rows'), query = $('dex-search').value.trim().toLowerCase();
  rows.replaceChildren();
  if (!boxes?.length) return;
  for (const [id, item] of Object.entries(species)) {
    if (query && !item.name.toLowerCase().includes(query) && !id.includes(query)) continue;
    const p = dexOffset(Number(id)), tr = document.createElement('tr');
    const name = document.createElement('th'); name.scope = 'row'; name.textContent = `${id.padStart(3, '0')} - ${item.name}`; tr.append(name);
    for (const [field, checked] of [['seen', !!data[p + 11]], ['obtained', data[p] >= 96], ['shiny', data[p + 15] === 1], ['centered', !!(data[p + 1] & 128)]]) {
      const td = document.createElement('td'), input = document.createElement('input'); input.type = 'checkbox'; input.checked = checked; input.dataset.field = field; input.dataset.id = id; input.setAttribute('aria-label', `${item.name} ${field}`); td.append(input); tr.append(td);
    }
    const crownCell = document.createElement('td'), crown = document.createElement('select'); crown.dataset.field = 'crown'; crown.dataset.id = id; crown.setAttribute('aria-label', `${item.name} right crown`);
    for (const [value, label] of [[96,'None'],[100,'Bronze'],[104,'Silver'],[108,'Gold']]) option(crown, value, label);
    if (![96,100,104,108].includes(data[p]) && data[p] >= 96) option(crown, data[p], `Unknown (${data[p]})`);
    crown.value = data[p] >= 96 ? data[p] : 96; crown.disabled = data[p] < 96; crownCell.append(crown); tr.append(crownCell);
    const formsCell = document.createElement('td'), forms = document.createElement('input'); forms.type = 'number'; forms.min = 0; forms.max = 255; forms.required = true; forms.value = data[p + 11]; forms.dataset.field = 'forms'; forms.dataset.id = id; forms.setAttribute('aria-label', `${item.name} seen forms mask`); formsCell.append(forms); tr.append(formsCell);
    const stats = collectionData?.[$('slot').selectedIndex]?.[Number(id)];
    const cell = value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); };
    const edit = (value, field, config = {}) => { const td = document.createElement('td'), input = document.createElement(config.tag || 'input'); Object.assign(input, config); input.value = value; input.dataset.collectionField = field; input.dataset.id = id; input.setAttribute('aria-label', `${item.name} ${field}`); td.append(input); tr.append(td); };
    if (stats) {
      const td = document.createElement('td'), select = document.createElement('select'); select.dataset.collectionField = 'status'; select.dataset.id = id; select.setAttribute('aria-label', `${item.name} collection status`);
      for (const [value, label] of [[0,'Unknown'],[1,'Appeared'],[2,'Defeated'],[3,'Collected']]) option(select, value, label);
      select.value = stats.collectionType; td.append(select); tr.append(td);
      edit(stats.defeated, 'defeated', {type:'number', min:0, max:9999999, step:1});
      const tdRanks = document.createElement('td');
      stats.battleRoyal.forEach((rank, i) => { if (i) tdRanks.append(' / '); const select = document.createElement('select'); select.dataset.collectionField = `rank${i}`; select.dataset.id = id; select.setAttribute('aria-label', `${item.name} Battle Royal ${['Normal','Hard','Easy'][i]} medal`); for (const [v,l] of [[0,'None'],[1,'Bronze'],[2,'Silver'],[3,'Gold']]) option(select,v,l); select.value = rank; tdRanks.append(select); }); tr.append(tdRanks);
    } else { cell('—'); cell('—'); cell('—'); }
    const formsCell = document.createElement('td');
    if (stats) {
      const details = document.createElement('details'), summary = document.createElement('summary'); summary.textContent = 'Edit forms'; details.append(summary);
      for (const [maskName, mask] of [['normal',stats.normalForms],['rare',stats.rareForms]]) {
        const group = document.createElement('fieldset'), legend = document.createElement('legend'); legend.textContent = `${maskName === 'normal' ? 'Normal' : 'Rare'} forms`; group.append(legend);
        const formList = species[id]?.forms || [];
        for (let bit = 0; bit < Math.min(32, Math.max(formList.length, mask ? 32 : 0)); bit++) {
          const label = document.createElement('label'), input = document.createElement('input'), form = formList.find(entry => entry.form === bit), model = form?.model_names?.[0];
          input.type = 'checkbox'; input.checked = !!(mask & (1 << bit)); input.dataset.maskField = maskName; input.dataset.bit = bit; input.dataset.id = id;
          label.append(input, ` ${bit === 0 ? 'Base' : model ? model.replaceAll('_',' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase()) : `Form ${bit + 1}`}`); group.append(label);
        }
        details.append(group);
      }
      formsCell.append(details);
    } else formsCell.textContent = '—';
    tr.append(formsCell);
    rows.append(tr);
  }
}
function changed() { status('Changes applied in memory. Download the edited save when you are ready.'); }
async function init() {
  const [s, m, p] = await Promise.all([fetch('resources/data/species.json'), fetch('resources/data/moves.json'), fetch('resources/data/power_stats.json')]);
  if (!s.ok || !m.ok || !p.ok) throw Error('Could not load the species and move data.');
  species = (await s.json()).species; moves = await m.json(); powerStats = await p.json();
  for (const [id, item] of Object.entries(species)) { option($('pokemon').elements.species, id, `${id} · ${item.name}`); }
  for (const [id, name] of Object.entries(moves)) for (const key of ['move1','move2']) option($('pokemon').elements[key], id, `${id} · ${name}`);
  $('open-file').disabled = false; $('open-file').textContent = 'Open savedata.bin';
}
$('open-file').addEventListener('click', () => $('file').click());
$('file').addEventListener('change', async e => {
  const file = e.target.files[0]; if (!file) return;
  try { const loaded = await decode(new Uint8Array(await file.arrayBuffer())); data = loaded; boxes = sections(data); loadCollectionData(); $('money').value = new DataView(data.buffer).getUint32(0x65); $('editor').hidden = false; refreshList(); renderDex(); status(`Loaded ${file.name}. Checksum and box structure are valid.`); }
  catch (err) { status(`Could not open save: ${err.message}`); }
  e.target.value = '';
});
$('slot').addEventListener('change', () => { refreshList(); renderDex(); }); $('record').addEventListener('change', loadPokemon);
$('moneyApply').addEventListener('click', () => { const input = $('money'); if (!input.checkValidity() || input.value === '') { input.reportValidity(); return; } new DataView(data.buffer).setUint32(0x65, Number(input.value)); changed(); });
$('pokemon').addEventListener('submit', e => {
  e.preventDefault(); const f = e.target.elements, p = currentOffset(), id = Number(f.species.value), individual = f.individual.value.match(/../g).map(x => parseInt(x, 16));
  put16(data, p, (id << 7) | (Number(f.form.value) << 2) | (data[p + 1] & 3));
  for (const [name, pos] of [['move1',4],['move2',2],['trait',16],['strength',6]]) put16(data, p + pos, Number(f[name].value));
  data.set(individual, p + 20); data[p + 19] = f.favorite.checked ? data[p + 19] | 2 : data[p + 19] & 253;
  data.set(f.shiny.checked ? [individual[2], individual[3], individual[0], individual[1]] : [0,0,0,0], p + 40);
  const d = dexOffset(id); if (data[d] < 96) data[d] = 96; data[d + 11] |= 1; if (f.shiny.checked) data[d + 15] = 1;
  refreshList(Number($('record').value)); renderDex(); changed();
});
$('dex-search').addEventListener('input', renderDex);
$('dex-rows').addEventListener('change', e => {
  const input = e.target, {field, id} = input.dataset; if (!field || !id) return;
  if (!input.checkValidity()) { input.reportValidity(); return; }
  const p = dexOffset(Number(id));
  if (field === 'seen') data[p + 11] = input.checked ? (data[p + 11] || 1) : 0;
  if (field === 'obtained') data[p] = input.checked ? (data[p] >= 96 ? data[p] : 96) : 0;
  if (field === 'shiny') data[p + 15] = input.checked ? 1 : 0;
  if (field === 'centered') data[p + 1] = input.checked ? data[p + 1] | 128 : data[p + 1] & 127;
  if (field === 'crown') data[p] = Number(input.value);
  if (field === 'forms') data[p + 11] = Number(input.value);
  renderDex(); changed();
});
$('dex-rows').addEventListener('change', e => {
  const input = e.target, field = input.dataset.maskField, id = Number(input.dataset.id), bit = Number(input.dataset.bit);
  if (!field || !id) return;
  const record = collectionData[$('slot').selectedIndex][id], p = record.recordOffset, view = new DataView(data.buffer), pos = field === 'normal' ? p + 8 : p + 12;
  const bitMask = (1 << bit) >>> 0, value = view.getUint32(pos), next = input.checked ? (value | bitMask) : (value & ~bitMask);
  view.setUint32(pos, next);
  if (field === 'rare' && bit === 0) { const packed = view.getUint32(p); view.setUint32(p, input.checked ? packed | (1 << 19) : packed & ~(1 << 19)); }
  loadCollectionData(); renderDex(); changed();
});
$('dex-rows').addEventListener('change', e => {
  const input = e.target, field = input.dataset.collectionField, id = Number(input.dataset.id);
  if (!field || !id || !input.checkValidity()) { if (field) input.reportValidity(); return; }
  const record = collectionData[$('slot').selectedIndex][id], p = record.recordOffset;
  const view = new DataView(data.buffer);
  if (field === 'status') { const packed = view.getUint32(p); view.setUint32(p, (packed & 0x1fffffff) | (Number(input.value) << 29)); }
  else if (field === 'defeated') view.setUint32(p + 4, Number(input.value));
  else { const index = Number(field.slice(4)), shift = [26,23,20][index], packed = view.getUint32(p), mask = 7 << shift; view.setUint32(p, (packed & ~mask) | (Number(input.value) << shift)); }
  loadCollectionData(); renderDex(); changed();
});
document.querySelectorAll('[data-bulk]').forEach(button => button.addEventListener('click', () => {
  for (const id of Object.keys(species)) {
    const p = dexOffset(Number(id));
    if (button.dataset.bulk === 'seen' || button.dataset.bulk === 'crowned') data[p + 11] |= 1;
    if ((button.dataset.bulk === 'obtained' || button.dataset.bulk === 'crowned') && data[p] < 96) data[p] = 96;
    if (button.dataset.bulk === 'shiny') data[p + 15] = 1;
    if (button.dataset.bulk === 'crowned') data[p + 1] |= 128;
  }
  renderDex(); changed();
}));
$('download').addEventListener('click', async () => { try { const output = await encode(data); const url = URL.createObjectURL(new Blob([output], {type:'application/octet-stream'})); const a = document.createElement('a'); a.href = url; a.download = 'savedata.bin'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); status('Edited save downloaded.'); } catch (err) { status(`Could not save: ${err.message}`); } });
init().catch(err => { $('open-file').textContent = 'Editor unavailable'; status(`Could not start the editor: ${err.message} Reload the page to try again.`); });
