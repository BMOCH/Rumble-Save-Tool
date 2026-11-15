"""Tkinter GUI for the decoded Pokémon Rumble Wii save format."""
import json
import os
import tkinter as tk
import re
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from .inspect_saves import STRIDE, find_box_sections, decode_save, encode_save, validate_save_data
from .constants import MOVES, Trait
from .paths import DATA, RUMBLE_ICONS, default_dolphin_save
from .save_editor import CROWN_VALUES

SPECIES = json.loads((DATA / 'species.json').read_text(encoding='utf-8'))['species']
PLATINUM_VALID_MOVES = json.loads((DATA / 'platinum_valid_moves.json').read_text(encoding='utf-8'))['species']
DEFAULT_SAVE = default_dolphin_save()
FORM_SPECIES = {412, 413, 421, 422, 423, 479, 487, 492}
POKEMON_EXPORT_FORMAT = 'pokemon-rumble-box-record'


def write_pokemon_export(record, path):
    """Write one decrypted 45-byte box record as a portable JSON file."""
    raw = bytes(record)
    if len(raw) != STRIDE:
        raise ValueError(f'Pokemon record must be exactly {STRIDE} bytes')
    payload = {
        'format': POKEMON_EXPORT_FORMAT,
        'version': 1,
        'record_size': STRIDE,
        'record_hex': raw.hex(),
    }
    Path(path).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def read_pokemon_export(path):
    """Read and validate a portable Pokemon record export."""
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('format') != POKEMON_EXPORT_FORMAT:
        raise ValueError('This file is not a Pokemon Rumble record export')
    if payload.get('version') != 1 or payload.get('record_size') != STRIDE:
        raise ValueError('Unsupported Pokemon export version or record size')
    try:
        raw = bytes.fromhex(payload['record_hex'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Export has invalid record data') from exc
    if len(raw) != STRIDE:
        raise ValueError(f'Export record must be exactly {STRIDE} bytes')
    return raw

class Editor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Rumble Save Tool')
        self.geometry('1100x820')
        self.data = None
        self.path = None
        self.records = []
        self.slot = 'A'
        self.save_slot = tk.StringVar(value='A')
        self.sort_mode = tk.StringVar(value='Number')
        self.vars = {k: tk.StringVar() for k in ('species','move1','move2','trait','strength','individual','dex_species','forms','box_form')}
        self.money = tk.StringVar(value='0')
        self.path_text = tk.StringVar(value='No savefile loaded')
        self.danger = tk.BooleanVar(value=False)
        self.original_individual = ''
        self.selected_template = None
        self.selected_offset = None
        self.favorite = tk.BooleanVar(); self.box_shiny = tk.BooleanVar(); self.obtained = tk.BooleanVar(); self.seen = tk.BooleanVar(); self.shiny = tk.BooleanVar(); self.centered = tk.BooleanVar()
        self.crown = tk.StringVar(value='none')
        self.icon_images = {}
        self.dex_ids = []
        self.dex_search = ''
        self.dex_search_after = None
        self.box_search = ''
        self.box_search_after = None
        self.combo_search = {}
        self._build()
        if DEFAULT_SAVE.exists():
            self._load_path(DEFAULT_SAVE)

    def _build(self):
        ttk.Label(self, textvariable=self.path_text, anchor='w').pack(fill='x', padx=8, pady=(6, 0))
        top = ttk.Frame(self); top.pack(fill='x', padx=8, pady=8)
        file_row = ttk.Frame(top); file_row.pack(fill='x')
        ttk.Button(file_row, text='Open savefile', command=self.open).pack(side='left')
        ttk.Button(file_row, text='Save as', command=self.save_as).pack(side='left', padx=5)
        ttk.Button(file_row, text='Validate save', command=self.validate_save).pack(side='left', padx=5)
        utility = ttk.Frame(file_row); utility.pack(side='right')
        danger_row = ttk.Frame(utility); danger_row.pack(anchor='e')
        ttk.Checkbutton(danger_row, text='Enable danger operations', variable=self.danger, command=self.update_danger_state).pack(side='left')
        ttk.Label(danger_row, text='  Back up your save before using these operations.', foreground='#9b1c1c').pack(side='left')
        p_row = ttk.Frame(utility); p_row.pack(anchor='e')
        self.money_entry = ttk.Entry(p_row, textvariable=self.money, width=12)
        self.money_entry.pack(side='right')
        self.money_entry.bind('<FocusOut>', lambda _event: self.apply_money())
        self.money_entry.bind('<Return>', lambda _event: self.apply_money())
        ttk.Label(p_row, text='P:').pack(side='right', padx=(15, 2))
        self.status = ttk.Label(file_row, text='No save loaded', anchor='w'); self.status.pack(side='left', fill='x', expand=True, padx=12)

        selection_row = ttk.Frame(top); selection_row.pack(fill='x', pady=(5, 0))
        ttk.Label(selection_row, text='Box:').pack(side='left')
        ttk.Combobox(selection_row, textvariable=self.save_slot, values=('A', 'B', 'C'), state='readonly', width=4).pack(side='left', padx=(2, 0))
        self.save_slot.trace_add('write', lambda *_: self.refresh())
        ttk.Label(selection_row, text='Sort:').pack(side='left', padx=(12, 2))
        ttk.Combobox(selection_row, textvariable=self.sort_mode, values=('Number', 'Species', 'Pokédex order', 'Favorite first'), state='readonly', width=15).pack(side='left')
        self.sort_mode.trace_add('write', lambda *_: self.refresh())
        self.import_button = ttk.Button(selection_row, text='Import Pokémon', command=self.import_pokemon)
        self.import_button.pack(side='right', padx=(5, 0))
        self.export_button = ttk.Button(selection_row, text='Export Pokémon', command=self.export_pokemon)
        self.export_button.pack(side='right')
        left = ttk.Frame(self, width=440); left.pack(side='left', fill='both', expand=False, padx=8); left.pack_propagate(False)
        self.list = tk.Listbox(left, width=42, font=('Courier New', 10), exportselection=False); self.list.pack(side='left', fill='both', expand=True); self.list.bind('<<ListboxSelect>>', self.select); self.list.bind('<KeyPress>', self._box_key_search)
        sb = ttk.Scrollbar(left, orient='vertical', command=self.list.yview); sb.pack(side='right', fill='y'); self.list.configure(yscrollcommand=sb.set)
        right = ttk.Frame(self); right.pack(side='right', fill='both', expand=True, padx=8)
        self._pokemon_panel(right)
        self.tabs = ttk.Notebook(right); self.tabs.pack(fill='both', expand=True, pady=8)
        self._dex_panel(self.tabs)

    def _row(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=2)
        if label == 'Strength':
            entry = ttk.Spinbox(parent, from_=0, to=127, increment=1, textvariable=var, width=18)
        else:
            entry = ttk.Entry(parent, textvariable=var, width=18)
        entry.grid(row=row, column=1, pady=2)
        if label == 'Strength': self.strength_entry = entry
        if label == 'Individual hex': self.individual_entry = entry
        if label == 'Strength': self._tooltip(entry, 'Stored as a two-byte big-endian value at record offset +0x06.\nEnter a decimal value from 0 to 127.\nNaturally observed values: 2–117.\n127 is the highest synthetic value tested; displayed power is derived from this and other fields.')
        if label == 'Individual hex': self._tooltip(entry, 'Four bytes contributing to the Pokémon’s individual power and shiny signature.')

    def _combo(self, parent, label, var, values, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=2)
        combo = ttk.Combobox(parent, textvariable=var, values=values, width=24); combo.grid(row=row, column=1, pady=2)
        combo.bind('<KeyRelease>', lambda event, c=combo, vals=values: self._combo_search(c, vals, event))
        if label.startswith('Move'):
            combo.configure(postcommand=lambda c=combo: self._color_move_dropdown(c))
            # On some Tk versions the popdown listbox is created after the
            # postcommand runs, so retry once the dropdown has been mapped.
            combo.bind('<Button-1>', lambda _event, c=combo: self.after_idle(lambda: self._color_move_dropdown(c)), add='+')
        if label == 'Trait': self._tooltip(combo, lambda: (Trait.from_label(var.get().split(':', 1)[-1].strip()) or Trait.NONE).effect)
        elif label.startswith('Move'): self._tooltip(combo, 'Move stored in this Pokémon record.')
        elif label == 'Species': self._tooltip(combo, 'Species stored in this Pokémon record.')
        return combo

    def _species_value(self, text):
        """Resolve a visible species name to its internal numeric ID."""
        text = text.strip()
        for key, info in SPECIES.items():
            if info.get('name', '').casefold() == text.casefold():
                return int(key)
        # Accept the former ``ID: Name`` representation for compatibility.
        prefix = text.split(':', 1)[0].strip()
        try:
            return int(prefix, 0)
        except ValueError:
            try:
                return int(prefix, 10)
            except ValueError:
                match = re.search(r'\d+', prefix)
                if match:
                    return int(match.group())
                raise ValueError(f'Unknown species: {text}')

    def _move_value(self, text):
        """Resolve a visible move name to its internal numeric ID."""
        text = text.strip()
        for key, name in MOVES.items():
            if name.casefold() == text.casefold():
                return int(key)
        # Accept the former ``ID: Move`` representation for compatibility.
        prefix = text.split(':', 1)[0].strip()
        try:
            return int(prefix, 0)
        except ValueError:
            try:
                return int(prefix, 10)
            except ValueError:
                match = re.search(r'\d+', prefix)
                if match:
                    return int(match.group())
                raise ValueError(f'Unknown move: {text}')

    def _field_value(self, key):
        """Resolve an editor field to the numeric value stored in the record."""
        text = self.vars[key].get().strip()
        if key == 'species':
            return self._species_value(text)
        if key in ('move1', 'move2'):
            return self._move_value(text)
        if key == 'trait':
            trait = Trait.from_label(text)
            if trait is not None:
                return int(trait)
        prefix = text.split(':', 1)[0].strip()
        for base in (0, 10, 16):
            try:
                return int(prefix, base)
            except ValueError:
                pass
        match = re.search(r'\d+', text)
        if match:
            return int(match.group())
        raise ValueError(f'Invalid {key} value: {text}')

    def _set_move_options(self, sid):
        """Put Platinum-valid moves first and remember them for dropdown coloring."""
        if not hasattr(self, 'move1_combo'):
            return
        valid = {entry['name'].casefold() for entry in PLATINUM_VALID_MOVES.get(str(sid), {}).get('moves', [])}
        ordered = [name for name in self.move_values if name.casefold() in valid]
        ordered.extend(name for name in self.move_values if name.casefold() not in valid)
        self._valid_move_names = valid
        for combo in (self.move1_combo, self.move2_combo):
            combo.configure(values=ordered)

    def _color_move_dropdown(self, combo):
        """Color valid move entries green in Tk's native combobox popdown."""
        try:
            popdown = self.tk.call('ttk::combobox::PopdownWindow', str(combo))
            listbox = f'{popdown}.f.l'
            values = combo.cget('values')
            for index, name in enumerate(values):
                color = '#188038' if str(name).casefold() in self._valid_move_names else '#202124'
                self.tk.call(listbox, 'itemconfigure', index, '-foreground', color)
        except (tk.TclError, AttributeError):
            # Some Tk builds do not expose the popdown listbox until after it
            # has been mapped; grouping still works in those builds.
            return

    def _combo_search(self, combo, values, event):
        if event.keysym in ('BackSpace', 'Delete', 'Left', 'Right', 'Up', 'Down', 'Return', 'Escape', 'Tab'):
            return
        char = event.char.lower()
        if not char or not char.isprintable(): return
        key = str(combo)
        if key in self.combo_search and hasattr(self, '_combo_search_after'):
            self.after_cancel(self._combo_search_after)
        self.combo_search[key] = self.combo_search.get(key, '') + char
        query = self.combo_search[key]
        match = next((v for v in values if query in v.lower()), None)
        if match:
            combo.set(match); combo.selection_range(0, 'end')
        self._combo_search_after = self.after(900, lambda: self.combo_search.pop(key, None))

    def _tooltip(self, widget, text):
        def enter(_):
            self._tip_after = self.after(500, lambda: self._show_tooltip(widget, text() if callable(text) else text))
        def leave(_):
            if hasattr(self, '_tip_after'): self.after_cancel(self._tip_after)
            self._hide_tooltip()
        widget.bind('<Enter>', enter); widget.bind('<Leave>', leave)

    def _show_tooltip(self, widget, text):
        self._hide_tooltip(); self._tip = tk.Toplevel(self); self._tip.wm_overrideredirect(True)
        self._tip_label = tk.Label(self._tip, text=text, justify='left', wraplength=280, background='#fff8d5', relief='solid', borderwidth=1, padx=6, pady=4)
        self._tip_label.pack(); self._tip.geometry(f'+{widget.winfo_rootx()+widget.winfo_width()+6}+{widget.winfo_rooty()}')

    def _hide_tooltip(self):
        if hasattr(self, '_tip') and self._tip:
            self._tip.destroy(); self._tip = None

    def _mark_modified(self):
        """Clear validation status after changing the in-memory save."""
        if hasattr(self, 'status'):
            self.status.config(text='Unsaved changes')

    def _pokemon_panel(self, parent):
        f = ttk.LabelFrame(parent, text='Pokémon', padding=(12, 4, 4, 4)); f.pack(fill='x', pady=4)
        details = ttk.Frame(f); details.grid(row=0, column=0, sticky='nw')
        actions = ttk.Frame(f); actions.grid(row=0, column=1, sticky='nw', padx=(14, 0))
        self.icon_label = ttk.Label(f, text='', width=90, anchor='center')
        self.icon_label.grid(row=0, column=2, rowspan=8, padx=(18, 12), pady=8)
        species_values = [v.get("name", "?") for _, v in sorted(SPECIES.items(), key=lambda x: int(x[0]))]
        def selectable_move(name):
            if name.casefold() == 'hidden power ?':
                return False
            parts = name.split()
            if parts and parts[0] in ('B', 'M2'): return False
            return not any(p == 'L' or p.lower() == 'finish' or re.fullmatch(r'\d+(?:st|nd|rd|th)?', p.lower()) for p in parts)
        move_values = [v for _, v in sorted(MOVES.items()) if selectable_move(v)]
        self.move_values = move_values
        trait_values = [trait.label for trait in Trait if trait is not Trait.DUMMY]
        self.species_combo = self._combo(details, 'Species', self.vars['species'], species_values, 0)
        self.box_forms_combo = self._combo(details, 'Form', self.vars['box_form'], (), 1)
        self.box_forms_combo.configure(state='disabled')
        self.box_forms_combo.bind('<<ComboboxSelected>>', lambda _event: (self._species_icon_from_var(), self._auto_apply_current()), add='+')
        self.trait_combo = self._combo(details, 'Trait', self.vars['trait'], trait_values, 2)
        ttk.Checkbutton(details, text='Favorite', variable=self.favorite, command=self._auto_apply_current).grid(row=3, column=0, columnspan=2, sticky='w')
        ttk.Checkbutton(details, text='Shiny', variable=self.box_shiny, command=self._auto_apply_current).grid(row=4, column=0, columnspan=2, sticky='w')
        self._row(details, 'Strength', self.vars['strength'], 5)

        self.move1_combo = self._combo(actions, 'Move 1', self.vars['move1'], move_values, 0)
        self.move2_combo = self._combo(actions, 'Move 2', self.vars['move2'], move_values, 1)
        self._row(actions, 'Individual hex', self.vars['individual'], 2)
        self.strength_entry.bind('<FocusOut>', lambda _event: self._auto_apply_current())
        self.individual_entry.bind('<FocusOut>', lambda _event: self._auto_apply_current())
        self.randomize_button = ttk.Button(actions, text='Randomize individual', command=self.randomize_individual, width=20)
        self.randomize_button.grid(row=3, column=0, columnspan=2, sticky='ew', pady=2)
        self._tooltip(self.randomize_button, 'Generate four random bytes for the Individual hex field. The value is written automatically when editing is enabled.')
        self._valid_move_names = set()
        self.vars['species'].trace_add('write', lambda *_: self._species_icon_from_var())
        for combo in (self.species_combo, self.trait_combo, self.move1_combo, self.move2_combo):
            combo.bind('<<ComboboxSelected>>', lambda _event: self._auto_apply_current(), add='+')
            combo.bind('<FocusOut>', lambda _event: self._auto_apply_current(), add='+')
        self.duplicate_button = ttk.Button(actions, text='Duplicate Pokémon', command=self.duplicate_pokemon, width=20)
        self.duplicate_button.grid(row=4, column=0, columnspan=2, sticky='ew', pady=5)
        self.update_danger_state()

    def update_danger_state(self):
        state = 'normal' if self.danger.get() else 'disabled'
        if hasattr(self, 'duplicate_button'): self.duplicate_button.configure(state=state)
        if hasattr(self, 'import_button'): self.import_button.configure(state=state)
        if hasattr(self, 'randomize_button'): self.randomize_button.configure(state=state)
        if hasattr(self, 'individual_entry'): self.individual_entry.configure(state=state)

    def randomize_individual(self):
        if self.data is None or not self.danger.get():
            return
        self.vars['individual'].set(os.urandom(4).hex())
        self._auto_apply_current()

    def _auto_apply_current(self):
        """Commit the selected record after an editor control changes."""
        if self.data is None or self.selected_offset is None:
            return
        try:
            self.apply_pokemon(offset=self.selected_offset, refresh=False)
        except Exception as exc:
            messagebox.showerror('Auto-apply failed', str(exc))

    def _species_icon_from_var(self):
        if not hasattr(self, 'icon_label'):
            return
        try:
            sid = self._species_value(self.vars['species'].get())
        except ValueError:
            return
        self._set_box_forms_options(sid)
        form_no = self._box_form_value() or 0
        self._set_species_icon(sid, form_no)
        self._set_move_options(sid)

    def _set_species_icon(self, sid, form_no=0):
        """Show the icon matching the species and stored form index."""
        icon = RUMBLE_ICONS / f'{sid:03d}_{form_no:02d}.png'
        if not icon.exists() and form_no:
            # A missing form asset should still show the base species icon.
            icon = RUMBLE_ICONS / f'{sid:03d}_00.png'
        if icon.exists():
            try:
                self.icon_images['selected'] = tk.PhotoImage(file=str(icon)).zoom(2, 2)
                self.icon_label.configure(image=self.icon_images['selected'], text='')
                return
            except tk.TclError:
                pass
        self.icon_label.configure(image='', text='')

    def _set_box_forms_options(self, sid):
        if not hasattr(self, 'box_forms_combo'):
            return
        if sid in FORM_SPECIES:
            names = self._form_names(sid)
            values = names
            self.box_forms_combo.configure(values=values, state='readonly')
            current = self.vars['box_form'].get().strip()
            try:
                valid = current.casefold() in {name.casefold() for name in names} or (0 <= int(current.split(':', 1)[0].strip(), 10) < len(names))
            except ValueError:
                valid = False
            if not valid:
                self.vars['box_form'].set(values[0])
        else:
            self.box_forms_combo.configure(values=(), state='disabled')
            self.vars['box_form'].set('')

    def _box_form_value(self):
        text = self.vars['box_form'].get().strip()
        try:
            sid = self._species_value(self.vars['species'].get())
        except ValueError:
            sid = None
        if sid in FORM_SPECIES:
            names = self._form_names(sid)
            for i, name in enumerate(names):
                if name.casefold() == text.casefold():
                    return i
        text = text.split(':', 1)[0].strip()
        if not text:
            return None
        try:
            return int(text, 10)
        except ValueError:
            return None

    def _dex_panel(self, parent):
        f = ttk.Frame(parent); self.tabs.add(f, text='Pokedex')
        left = ttk.Frame(f, width=330); left.pack(side='left', fill='both', expand=False); left.pack_propagate(False)
        self.dex_list = tk.Listbox(left, width=30, font=('Courier New', 10), exportselection=False)
        self.dex_list.pack(side='left', fill='both', expand=True)
        dsb = ttk.Scrollbar(left, orient='vertical', command=self.dex_list.yview); dsb.pack(side='right', fill='y'); self.dex_list.configure(yscrollcommand=dsb.set)
        self.dex_ids = [int(k) for k, _ in sorted(SPECIES.items(), key=lambda x: int(x[0]))]
        for k in self.dex_ids:
            self.dex_list.insert('end', f'{k:03d}  {SPECIES[str(k)].get("name", "Unknown")}')
        self.dex_list.bind('<<ListboxSelect>>', self._dex_select)
        self.dex_list.bind('<KeyPress>', self._dex_key_search)
        controls = ttk.LabelFrame(f, text='Entry', width=320); controls.pack(side='left', fill='y', padx=8); controls.pack_propagate(False)
        ttk.Label(controls, text='Forms').grid(row=0, column=0, sticky='w', pady=2)
        forms_values = [self._forms_label(mask) for mask in range(0x40)]
        self.forms_combo = ttk.Combobox(controls, textvariable=self.vars['forms'], values=forms_values, width=20)
        self.forms_combo.grid(row=0, column=1, pady=2)
        self.forms_combo.configure(state='disabled')
        self.forms_combo.bind('<<ComboboxSelected>>', lambda _event: (self.seen.set(True), self._auto_apply_dex()))
        self.forms_combo.bind('<FocusOut>', lambda _event: self._auto_apply_dex(), add='+')
        self._tooltip(self.forms_combo, 'Form bitmask. The available masks and labels are limited to this species; for example, Rotom has Base, Heat, Wash, Frost, Fan, and Mow forms.')
        ttk.Checkbutton(controls, text='Seen', variable=self.seen, command=self._auto_apply_dex).grid(row=1, column=0, columnspan=2, sticky='w')
        ttk.Checkbutton(controls, text='Obtained', variable=self.obtained, command=self._auto_apply_dex).grid(row=2, column=0, columnspan=2, sticky='w')
        ttk.Checkbutton(controls, text='Shiny', variable=self.shiny, command=self._auto_apply_dex).grid(row=3, column=0, columnspan=2, sticky='w')
        ttk.Separator(controls, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky='ew', pady=6)
        ttk.Checkbutton(controls, text='Center crown', variable=self.centered, command=self._auto_apply_dex).grid(row=5, column=0, columnspan=2, sticky='w')
        ttk.Label(controls, text='Right crown').grid(row=6, column=0, sticky='w')
        self.crown_combo = ttk.Combobox(controls, textvariable=self.crown, values=list(CROWN_VALUES), state='readonly', width=15)
        self.crown_combo.grid(row=6, column=1)
        self.crown_combo.bind('<<ComboboxSelected>>', lambda _event: self._auto_apply_dex())
        ttk.Separator(controls, orient='horizontal').grid(row=8, column=0, columnspan=2, sticky='ew', pady=6)
        ttk.Button(controls, text='Mark all seen', width=18, command=self.mark_all_seen).grid(row=9, column=0, pady=3)
        ttk.Button(controls, text='Mark all obtained', width=18, command=self.mark_all_obtained).grid(row=9, column=1, pady=3)
        ttk.Button(controls, text='Mark all shiny', width=18, command=self.mark_all_shiny).grid(row=10, column=0, pady=3)
        ttk.Button(controls, text='Mark all crowned', width=18, command=self.mark_all_crowned).grid(row=10, column=1, pady=3)

    def _dex_select(self, _=None):
        s = self.dex_list.curselection()
        if s:
            self.vars['dex_species'].set(str(self.dex_ids[s[0]]))
            self.load_dex()

    def _auto_apply_dex(self):
        """Commit the selected Dex entry after one of its controls changes."""
        if self.data is None or not self.vars['dex_species'].get().strip():
            return
        self.apply_dex()

    def _dex_key_search(self, event):
        """Select a Dex entry by typing the beginning of its species name."""
        if event.keysym in ('BackSpace', 'Delete'):
            self.dex_search = self.dex_search[:-1]
        else:
            char = event.char.casefold()
            if not char or not char.isalpha():
                return
            self.dex_search += char
        if self.dex_search_after is not None:
            self.after_cancel(self.dex_search_after)
        query = self.dex_search
        match = next(
            (index for index, sid in enumerate(self.dex_ids)
             if SPECIES.get(str(sid), {}).get('name', '').casefold().startswith(query)),
            None,
        ) if query else None
        if match is not None:
            self.dex_list.selection_clear(0, 'end')
            self.dex_list.selection_set(match)
            self.dex_list.activate(match)
            self.dex_list.see(match)
            self._dex_select()
        self.dex_search_after = self.after(900, lambda: setattr(self, 'dex_search', ''))
        return 'break'

    def _box_key_search(self, event):
        """Select a box record by typing the beginning of its species name."""
        if self.data is None:
            return
        if event.keysym in ('BackSpace', 'Delete'):
            self.box_search = self.box_search[:-1]
        else:
            char = event.char.casefold()
            if not char or not char.isalpha():
                return
            self.box_search += char
        if self.box_search_after is not None:
            self.after_cancel(self.box_search_after)
        query = self.box_search
        match = None
        if query:
            for index, (_slot, _box_index, offset) in enumerate(self.records):
                sid = int.from_bytes(self.data[offset:offset + 2], 'big') >> 7
                name = SPECIES.get(str(sid), {}).get('name', '')
                if name.casefold().startswith(query):
                    match = index
                    break
        if match is not None:
            self.list.selection_clear(0, 'end')
            self.list.selection_set(match)
            self.list.activate(match)
            self.list.see(match)
            self.select()
        self.box_search_after = self.after(900, lambda: setattr(self, 'box_search', ''))
        return 'break'

    def _form_names(self, sid=None):
        """Return friendly names for the forms that are usable in the Dex UI."""
        named = {
            412: ['Plant', 'Sandy', 'Trash'],
            413: ['Plant', 'Sandy', 'Trash'],
            421: ['Overcast', 'Sunshine'],
            422: ['West', 'East'],
            423: ['West', 'East'],
            479: ['Base', 'Heat', 'Wash', 'Frost', 'Fan', 'Mow'],
            487: ['Giratina Origin', 'Giratina Altered'],
            492: ['Shaymin Land', 'Shaymin Sky'],
        }
        if sid in named:
            return named[sid]
        return ['Base'] + [f'Form {i}' for i in range(1, 6)]

    def _forms_label(self, mask, sid=None):
        if mask == 0: return 'None'
        names = self._form_names(sid)
        enabled = [names[i] for i in range(len(names)) if mask & (1 << i)]
        return ' + '.join(enabled) if enabled else 'None'

    def _forms_value(self, text, sid):
        """Resolve a visible Dex form label to its internal bitmask."""
        text = text.strip()
        for mask in range(1, 1 << len(self._form_names(sid))):
            if self._forms_label(mask, sid).casefold() == text.casefold():
                return mask
        # Accept the old ``XX: label`` representation for compatibility.
        prefix = text.split(':', 1)[0].strip()
        try:
            return int(prefix, 16 if not prefix.lower().startswith('0x') else 0)
        except ValueError:
            raise ValueError(f'Unknown form selection: {text}')

    def _set_forms_options(self, sid):
        count = len(self._form_names(sid)) if sid in {412, 413, 421, 422, 423, 479, 487, 492} else 0
        if count:
            self.forms_combo.configure(values=[self._forms_label(mask, sid) for mask in range(1, 1 << count)])
            self.forms_combo.configure(state='readonly')
        else:
            self.forms_combo.configure(values=())
            self.forms_combo.configure(state='disabled')

    def mark_all_seen(self):
        if self.data is None: return
        for sid in self.dex_ids:
            self.data[self.dex_offset(sid) + 11] |= 1
        self._mark_modified()
        self.update_dex_list()

    def mark_all_obtained(self):
        if self.data is None: return
        for sid in self.dex_ids:
            off = self.dex_offset(sid)
            if self.data[off] < 0x60:
                self.data[off] = 0x60
        self._mark_modified()
        self.update_dex_list()

    def mark_all_shiny(self):
        if self.data is None: return
        for sid in self.dex_ids:
            self.data[self.dex_offset(sid) + 15] = 1
        self._mark_modified()
        self.update_dex_list()

    def mark_all_crowned(self):
        if self.data is None: return
        for sid in self.dex_ids:
            off = self.dex_offset(sid)
            if self.data[off] < 0x60: self.data[off] = 0x60
            self.data[off + 11] |= 1
            self.data[off + 1] |= 0x80
        self._mark_modified()
        self.update_dex_list()

    def open(self):
        p = filedialog.askopenfilename(initialdir=str(DEFAULT_SAVE.parent), initialfile=DEFAULT_SAVE.name, filetypes=[('Save data', '*.bin'), ('All files', '*.*')])
        if not p: return
        self._load_path(Path(p))

    def _load_path(self, p):
        try: self.data = bytearray(decode_save(p.read_bytes()))
        except Exception as e: messagebox.showerror('Open failed', str(e)); return
        self.path = p; self.selected_template = None; self.selected_offset = None; self.path_text.set(str(self.path)); self.refresh(); self.status.config(text=f'{self.path.name} loaded')

    def refresh(self):
        self.list.delete(0, 'end'); self.records = []
        if self.data is None: return
        self.money.set(str(int.from_bytes(self.data[0x65:0x69], 'big')))
        self.update_dex_list()
        for slot, (start, records) in zip('ABC', find_box_sections(self.data)):
            if slot != self.save_slot.get():
                continue
            rows = []
            for i, r in enumerate(records):
                sid = int.from_bytes(r[:2], 'big') >> 7
                name = SPECIES.get(str(sid), {}).get('name', '?')
                rows.append((i, r, sid, name, bool(r[19] & 2)))
            if self.sort_mode.get() == 'Species':
                rows.sort(key=lambda row: (row[3].casefold(), row[0]))
            elif self.sort_mode.get() == 'Pokédex order':
                # Sort by the game's species/Pokédex number, with box number as a tie-breaker.
                rows.sort(key=lambda row: (row[2], row[0]))
            elif self.sort_mode.get() == 'Favorite first':
                rows.sort(key=lambda row: (not row[4], row[0]))
            for i, r, sid, name, _favorite in rows:
                self.records.append((slot, i, start + i * STRIDE))
                self.list.insert('end', self._box_row_text(slot, i, r))

    def _box_row_text(self, slot, index, record):
        """Format one box record for the compact selector list."""
        sid = int.from_bytes(record[:2], 'big') >> 7
        name = SPECIES.get(str(sid), {}).get('name', '?')
        shiny = record[40:44] == record[22:24] + record[20:22]
        trait_id = int.from_bytes(record[16:18], 'big')
        trait_name = '' if trait_id == 0 else Trait.label_for(trait_id)
        marker = '★ ' if shiny else '☆ '
        return f'{slot}{index:03d}  {marker}{name[:16]:16s} {trait_name}'

    def _update_box_row(self, offset):
        """Update a visible selector row after changing its record in memory."""
        for index, (slot, box_index, record_offset) in enumerate(self.records):
            if record_offset != offset:
                continue
            selected = self.list.curselection()
            record = self.data[offset:offset + STRIDE]
            self.list.delete(index)
            self.list.insert(index, self._box_row_text(slot, box_index, record))
            for selected_index in selected:
                if selected_index == index:
                    self.list.selection_set(index)
                else:
                    self.list.selection_set(selected_index)
            return

    def update_dex_list(self):
        if not hasattr(self, 'dex_list'):
            return
        selected = self.dex_list.curselection()
        selected_id = self.dex_ids[selected[0]] if selected else None
        self.dex_list.delete(0, 'end')
        for sid in self.dex_ids:
            name = SPECIES[str(sid)].get('name', 'Unknown')
            try:
                off = self.dex_offset(sid); b0, b1, shiny = self.data[off], self.data[off + 1], self.data[off + 15]
                first = ''.join((('S' if self.data[off + 11] else '-'), ('O' if b0 >= 0x60 else '-'), ('★' if shiny == 1 else '☆')))
                grade = {0x64: 'B', 0x68: 'S', 0x6C: 'G'}.get(b0, '-')
                crown = 'C' if grade != '-' or b1 & 0x80 else '-'
                status = f'[{first}][{crown}{grade}]'
            except Exception:
                status = '[---][--]'
            self.dex_list.insert('end', f'{sid:03d}  {name:14s} {status}')
        if selected_id in self.dex_ids:
            index = self.dex_ids.index(selected_id)
            self.dex_list.selection_set(index)
            self.dex_list.activate(index)
            self.dex_list.see(index)

    def select(self, _=None):
        s = self.list.curselection()
        if not s: return
        slot, i, off = self.records[s[0]]
        if self.selected_offset is not None and off != self.selected_offset:
            try:
                self.apply_pokemon(offset=self.selected_offset, refresh=False)
            except Exception as exc:
                messagebox.showerror('Auto-apply failed', str(exc))
        self.selected_offset = off
        r = self.data[off:off+STRIDE]
        self.selected_template = bytes(r)
        self.slot = slot
        sid = int.from_bytes(r[:2], 'big') >> 7
        form_no = 0
        move2 = int.from_bytes(r[2:4], 'big')
        move1 = int.from_bytes(r[4:6], 'big')
        trait = int.from_bytes(r[16:18], 'big')
        # Keep the readable name form in each dropdown when a record is selected.
        self.vars['species'].set(SPECIES.get(str(sid), {}).get("name", "Unknown"))
        if sid in FORM_SPECIES:
            form_no = (int.from_bytes(r[:2], 'big') & 0x7F) >> 2
            names = self._form_names(sid)
            self.vars['box_form'].set(names[form_no] if form_no < len(names) else 'Unknown')
        else:
            self.vars['box_form'].set('')
        self.vars['move2'].set(MOVES.get(move2, "Unknown move"))
        self.vars['move1'].set(MOVES.get(move1, "Unknown move"))
        self.vars['trait'].set(Trait.label_for(trait) if trait else 'None')
        self.vars['strength'].set(str(int.from_bytes(r[6:8], "big"))); self.vars['individual'].set(r[20:24].hex()); self.original_individual = r[20:24].hex(); self.favorite.set(bool(r[19] & 2)); self.box_shiny.set(r[40:44] == r[22:24] + r[20:22])
        self._set_species_icon(sid, form_no)

    def apply_pokemon(self, offset=None, refresh=True):
        s = self.list.curselection()
        if offset is None and not s: return False
        selected_index = s[0] if s else None
        if self.vars['individual'].get().lower() != self.original_individual.lower() and not self.danger.get():
            messagebox.showerror('Danger operation blocked', 'Enable danger operations before editing Individual hex. Back up your save first.')
            return False
        if offset is None:
            _, _, off = self.records[selected_index]
        else:
            off = offset
        r = self._field_value('species'); old = int.from_bytes(self.data[off:off+2], 'big')
        low = old & 0x7f
        if r in FORM_SPECIES:
            form_no = self._box_form_value()
            if form_no is not None and 0 <= form_no < len(self._form_names(r)):
                low = (form_no << 2) | (low & 0x03)
        self.data[off:off+2] = ((r << 7) | low).to_bytes(2, 'big')
        for key, pos in [('move2',2),('move1',4),('trait',16)]: self.data[off+pos:off+pos+2] = self._field_value(key).to_bytes(2,'big')
        strength = self.vars['strength'].get().strip()
        try:
            strength_value = int(strength, 10)
        except ValueError as exc:
            raise ValueError('Strength must be a decimal value from 0 to 127') from exc
        if not 0 <= strength_value <= 127:
            raise ValueError('Strength must be a decimal value from 0 to 127')
        self.data[off+6:off+8] = strength_value.to_bytes(2, 'big')
        raw = bytes.fromhex(self.vars['individual'].get());
        if len(raw) != 4: raise ValueError('Individual value requires 4 bytes')
        self.data[off+20:off+24] = raw
        if self.box_shiny.get():
            self.data[off+40:off+44] = self.data[off+22:off+24] + self.data[off+20:off+22]
        else:
            self.data[off+40:off+44] = b'\x00\x00\x00\x00'
        self.data[off+19] = (self.data[off+19] | 2) if self.favorite.get() else (self.data[off+19] & ~2)
        self._sync_dex_for_box(r, self.box_shiny.get())
        if refresh:
            self._mark_modified()
            self.refresh()
            if selected_index is not None and selected_index < self.list.size():
                self.list.selection_set(selected_index); self.list.see(selected_index); self.select()
        else:
            self._mark_modified()
            self._update_box_row(off)
            self.update_dex_list()
        return True

    def _append_record(self, record):
        """Append a complete record to the selected box and refresh the UI."""
        template = bytes(record)
        if len(template) != STRIDE:
            raise ValueError(f'Pokemon record must be exactly {STRIDE} bytes')
        slot_index = 'ABC'.index(self.save_slot.get())
        start, records = find_box_sections(self.data)[slot_index]
        if len(records) >= 1000:
            raise ValueError('This box is at the tested 1000-Pokemon capacity')
        marker = start - 5
        end = start + len(records) * STRIDE
        self.data[end:end] = template
        del self.data[0x34000:]
        self.data[marker + 3:marker + 5] = (len(records) + 1).to_bytes(2, 'big')
        sid = int.from_bytes(template[:2], 'big') >> 7
        shiny = template[40:44] == template[22:24] + template[20:22]
        self._sync_dex_for_box(sid, shiny)
        self._mark_modified()
        self.refresh()
        if self.list.size():
            self.list.selection_set(self.list.size() - 1)
            self.list.see(self.list.size() - 1)
            self.select()

    def export_pokemon(self):
        """Export the selected box record for transfer to another save."""
        selected = self.list.curselection()
        if not selected:
            messagebox.showerror('Export Pokémon failed', 'Select a Pokémon first.')
            return
        _, _, off = self.records[selected[0]]
        sid = int.from_bytes(self.data[off:off + 2], 'big') >> 7
        name = SPECIES.get(str(sid), {}).get('name', 'pokemon').replace(' ', '_')
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            initialfile=f'{name}.pokemon.json',
            filetypes=[('Pokémon record', '*.pokemon.json'), ('JSON files', '*.json')],
        )
        if not path:
            return
        try:
            write_pokemon_export(self.data[off:off + STRIDE], path)
            self.status.config(text=f'Exported {Path(path).name}')
        except Exception as exc:
            messagebox.showerror('Export Pokémon failed', str(exc))

    def import_pokemon(self):
        """Import a record as a new Pokémon in the selected save slot."""
        if self.data is None or not self.danger.get():
            messagebox.showerror('Danger operation blocked', 'Enable danger operations before importing Pokémon. Back up your save first.')
            return
        path = filedialog.askopenfilename(
            filetypes=[('Pokémon record', '*.pokemon.json'), ('JSON files', '*.json')],
        )
        if not path:
            return
        try:
            self._append_record(read_pokemon_export(path))
            self.status.config(text=f'Imported {Path(path).name}')
        except Exception as exc:
            messagebox.showerror('Import Pokémon failed', str(exc))

    def duplicate_pokemon(self):
        if self.data is None: return
        if not self.danger.get():
            messagebox.showerror('Danger operation blocked', 'Enable danger operations before duplicating Pokémon. Back up your save first.')
            return
        slot_index = 'ABC'.index(self.save_slot.get())
        start, records = find_box_sections(self.data)[slot_index]
        if len(records) >= 1000:
            messagebox.showerror('Duplicate Pokémon failed', 'This box is at the tested 1000-Pokémon capacity.')
            return
        selected = self.list.curselection()
        if selected:
            template = bytes(self.data[self.records[selected[0]][2]:][:STRIDE])
        elif self.selected_template is not None:
            # Box switching clears the list selection; retain the last chosen
            # Pokémon so Duplicate still copies it into the newly selected box.
            template = self.selected_template
        else:
            messagebox.showerror('Duplicate Pokémon failed', 'Select a Pokémon to duplicate first.')
            return
        template = bytearray(template)
        # When editor fields are populated, use them for the entire new record.
        # This also works after switching boxes, which clears the list selection.
        if self.vars['species'].get().strip():
            try:
                species = self._field_value('species')
                if not 0 <= species <= 0x1FF:
                    raise ValueError
                old_species = int.from_bytes(template[:2], 'big')
                low = old_species & 0x7F
                if species in FORM_SPECIES:
                    form_no = self._box_form_value()
                    if form_no is not None and 0 <= form_no < len(self._form_names(species)):
                        low = (form_no << 2) | (low & 0x03)
                template[:2] = ((species << 7) | low).to_bytes(2, 'big')
                template[2:4] = self._field_value('move2').to_bytes(2, 'big')
                template[4:6] = self._field_value('move1').to_bytes(2, 'big')
                trait = self._field_value('trait')
                if not 0 <= trait <= 0xFFFF:
                    raise ValueError
                template[16:18] = trait.to_bytes(2, 'big')
            except (ValueError, OverflowError):
                messagebox.showerror('Duplicate Pokémon failed', 'Species, moves, and trait must contain valid numeric IDs.')
                return
        # Apply the current checkbox state to the copied record. In particular,
        # do not carry a shiny signature over after Shiny has been unchecked.
        if self.box_shiny.get():
            template[40:44] = template[22:24] + template[20:22]
        else:
            template[40:44] = b'\x00\x00\x00\x00'
        strength_text = self.vars['strength'].get().strip()
        if strength_text:
            try:
                strength_value = int(strength_text, 10)
                if not 0 <= strength_value <= 127:
                    raise ValueError
            except ValueError:
                messagebox.showerror('Duplicate Pokémon failed', 'Strength must be a decimal value from 0 to 127.')
                return
            template[6:8] = strength_value.to_bytes(2, 'big')
        individual_text = self.vars['individual'].get().strip()
        if individual_text:
            try:
                individual_value = bytes.fromhex(individual_text)
                if len(individual_value) != 4:
                    raise ValueError
            except ValueError:
                messagebox.showerror('Duplicate Pokémon failed', 'Individual hex requires exactly 4 bytes.')
                return
            template[20:24] = individual_value
            if self.box_shiny.get():
                template[40:44] = template[22:24] + template[20:22]
        template[19] = (template[19] | 2) if self.favorite.get() else (template[19] & ~2)
        template = bytes(template)
        try:
            self._append_record(template)
        except ValueError as exc:
            messagebox.showerror('Duplicate Pokémon failed', str(exc))

    def apply_money(self):
        try:
            value = int(self.money.get(), 0)
            if not 0 <= value <= 0xFFFFFFFF: raise ValueError('P must fit in an unsigned 32-bit value')
            self.data[0x65:0x69] = value.to_bytes(4, 'big')
            self._mark_modified()
            self.status.config(text=f'P set to {value:,}')
        except Exception as e:
            messagebox.showerror('P edit failed', str(e))

    def dex_offset(self, sid):
        start, records = find_box_sections(self.data)[0]; return start + len(records) * STRIDE + 0x147 + (sid - 1) * 0x11

    def _sync_dex_for_box(self, sid, shiny=False):
        """Mark a boxed species as seen/obtained, preserving existing Dex history."""
        if sid < 1:
            return
        try:
            off = self.dex_offset(sid)
            if off + 15 >= len(self.data):
                return
            if self.data[off] < 0x60:
                self.data[off] = 0x60
            self.data[off + 11] |= 1
            if shiny:
                self.data[off + 15] = 1
        except (IndexError, ValueError):
            return

    def load_dex(self):
        try:
            sid = int(self.vars['dex_species'].get(), 0); off = self.dex_offset(sid)
            self._set_forms_options(sid)
            self.obtained.set(self.data[off] >= 0x60); self.seen.set(bool(self.data[off+11])); self.vars['forms'].set(self._forms_label(self.data[off+11], sid)); self.shiny.set(self.data[off+15] == 1); self.centered.set(bool(self.data[off+1] & 0x80)); self.crown.set(next((k for k,v in CROWN_VALUES.items() if self.data[off] == v), 'none'))
        except Exception as e: messagebox.showerror('Dex load failed', str(e))

    def apply_dex(self):
        try:
            sid = int(self.vars['dex_species'].get(), 0); off = self.dex_offset(sid); self.data[off] = CROWN_VALUES[self.crown.get()] if self.obtained.get() else 0; self.data[off+1] = (self.data[off+1] | 0x80) if self.centered.get() else (self.data[off+1] & 0x7f)
            forms = self.vars['forms'].get().strip()
            self.data[off+11] = self._forms_value(forms, sid) if self.seen.get() else 0
            self.data[off+15] = 1 if self.shiny.get() else 0; self._mark_modified(); self.update_dex_list()
        except Exception as e: messagebox.showerror('Dex edit failed', str(e))

    def save_as(self):
        if self.data is None: return
        p = filedialog.asksaveasfilename(defaultextension='.bin', filetypes=[('Save data','*.bin')])
        if not p: return
        try: Path(p).write_bytes(encode_save(bytes(self.data))); self.status.config(text=f'Saved {Path(p).name}')
        except Exception as e: messagebox.showerror('Save failed', str(e))

    def validate_save(self):
        if self.data is None:
            messagebox.showwarning('Validate save', 'Open a savefile first.')
            return
        try:
            # In-memory edits leave the stored SHA-1 unchanged until encoding.
            # Round-trip a temporary copy so validation checks the edited data
            # with the checksum that Save as will write.
            normalized = decode_save(encode_save(bytes(self.data)))
            result = validate_save_data(normalized)
            counts = ', '.join(f'{slot}: {count}' for slot, count in result['box_counts'].items())
            messagebox.showinfo('Save valid', f"Save structure and checksums are valid.\nBox records — {counts}")
            self.status.config(text='Save validation passed')
        except Exception as e:
            messagebox.showerror('Save invalid', str(e))
            self.status.config(text='Save validation failed')

if __name__ == '__main__': Editor().mainloop()

