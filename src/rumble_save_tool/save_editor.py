"""Basic editor for the currently decoded Pokémon Rumble Wii save format."""
import argparse
from pathlib import Path
from .inspect_saves import STRIDE, decode_save, encode_save, find_box_sections, validate_save_file
from .paths import DATA

SIZE = 0x34000
CROWN_VALUES = {'none': 0x60, 'bronze': 0x64, 'silver': 0x68, 'gold': 0x6C}

def load_save(path):
    """Read and decode a savedata.bin file into editable bytes."""
    return bytearray(decode_save(Path(path).read_bytes()))

def write_save(data, path):
    """Encode and write save data, asking before replacing an existing file."""
    path = Path(path)
    if path.exists():
        try:
            answer = input(f'{path} already exists. Overwrite it? [y/N]: ').strip().lower()
        except EOFError:
            raise SystemExit('Output exists and no confirmation was available; existing file was left unchanged.')
        if answer not in {'y', 'yes'}:
            raise SystemExit('Cancelled; existing output was left unchanged.')
    path.write_bytes(encode_save(bytes(data)))
    print(f'Wrote {path}')

def find_pokemon_record(data, slot, index):
    """Return the offset and bytes for a Pokémon in save slot A, B, or C."""
    box_sections = find_box_sections(data)
    si = 'ABC'.index(slot)
    start, records = box_sections[si]
    if not 0 <= index < len(records):
        raise SystemExit(f'{slot} index {index} is outside 0..{len(records)-1}')
    return start + index * STRIDE, records[index]

def cmd_list(args):
    data = load_save(args.input)
    start, records = find_box_sections(data)['ABC'.index(args.slot)]
    species = __import__('json').loads((DATA / 'species.json').read_text())['species']
    for i, r in enumerate(records):
        sid = int.from_bytes(r[:2], 'big') >> 7
        trait = int.from_bytes(r[0x10:0x12], 'big')
        print(f'{i:4d}  {sid:3d}  {species.get(str(sid), {}).get("name", "?"):12s} '
              f'move2={int.from_bytes(r[2:4], "big"):03X} move1={int.from_bytes(r[4:6], "big"):03X} '
              f'trait={trait:02d} strength={int.from_bytes(r[6:8], "big"):04X} fav={bool(r[0x13] & 2)}')


def cmd_validate(args):
    try:
        result = validate_save_file(args.input)
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Invalid save: {exc}')
    counts = ', '.join(f'{slot}={count}' for slot, count in result['box_counts'].items())
    print(f"Valid save: {result['path']} ({result['encrypted_size']} bytes; boxes {counts})")

def cmd_edit(args):
    data = load_save(args.input)
    off, old = find_pokemon_record(data, args.slot, args.index)
    if args.species is not None:
        packed = int.from_bytes(old[:2], 'big')
        data[off:off+2] = ((args.species << 7) | (packed & 0x7F)).to_bytes(2, 'big')
    if args.move1 is not None: data[off+4:off+6] = args.move1.to_bytes(2, 'big')
    if args.move2 is not None: data[off+2:off+4] = args.move2.to_bytes(2, 'big')
    if args.trait is not None: data[off+0x10:off+0x12] = args.trait.to_bytes(2, 'big')
    if args.strength is not None: data[off+6:off+8] = args.strength.to_bytes(2, 'big')
    if args.individual is not None:
        raw = bytes.fromhex(args.individual)
        if len(raw) != 4: raise SystemExit('--individual requires exactly 4 bytes')
        data[off+0x14:off+0x18] = raw
    if args.favorite is True: data[off+0x13] |= 2
    if args.favorite is False: data[off+0x13] &= ~2
    write_save(data, args.output)

def cmd_dex(args):
    data = load_save(args.input)
    a_start, a_records = find_box_sections(data)[0]
    table = a_start + len(a_records) * STRIDE + 0x147
    entry = table + (args.species - 1) * 0x11
    if args.obtained is not None:
        data[entry] = CROWN_VALUES[args.crown] if args.crown else (0x60 if args.obtained else 0)
    elif args.crown:
        data[entry] = CROWN_VALUES[args.crown]
    if args.centered is not None:
        data[entry+1] = (data[entry+1] | 0x80) if args.centered else (data[entry+1] & 0x7F)
    if args.seen is not None:
        data[entry+0x0B] = (data[entry+0x0B] if args.forms is None else args.forms) if args.seen else 0
    elif args.forms is not None: data[entry+0x0B] = args.forms
    if args.shiny is not None: data[entry+0x0F] = 1 if args.shiny else 0
    write_save(data, args.output)


def show_help(args):
    if args.topic:
        args.command_parsers[args.topic].print_help()
    else:
        args.root_parser.print_help()


def main():
    p = argparse.ArgumentParser(
        description='Inspect and edit Pokémon Rumble Wii save files.',
        epilog='Use "help <command>" for detailed command help.',
    )
    sub = p.add_subparsers(dest='command', required=True, title='commands')

    l = sub.add_parser('list', help='List Pokémon records in one save slot.',
                       description='List stored Pokémon and their record values.')
    l.add_argument('input', type=Path, help='Encrypted or decrypted savedata.bin')
    l.add_argument('--slot', choices='ABC', default='A', help='Save slot to list (default: A).')
    l.set_defaults(func=cmd_list)

    e = sub.add_parser('edit-pokemon', help='Edit one Pokémon box record.',
                       description='Change selected fields in one 45-byte Pokémon record.')
    e.add_argument('input', type=Path, help='Input savedata.bin')
    e.add_argument('output', type=Path, help='Output savedata.bin')
    e.add_argument('--slot', choices='ABC', required=True, help='Save slot containing the record.')
    e.add_argument('--index', type=int, required=True, help='Zero-based record index within the slot.')
    e.add_argument('--species', type=int, help='Internal species ID.')
    e.add_argument('--move1', type=lambda x: int(x, 0), help='Move 1 internal ID (hex or decimal).')
    e.add_argument('--move2', type=lambda x: int(x, 0), help='Move 2 internal ID (hex or decimal).')
    e.add_argument('--trait', type=lambda x: int(x, 0), help='Trait ID (hex or decimal).')
    e.add_argument('--strength', type=lambda x: int(x, 0), help='Stored strength value at +0x06.')
    e.add_argument('--individual', help='Four individual bytes as eight hex digits.')
    e.add_argument('--favorite', action=argparse.BooleanOptionalAction, help='Set or clear the favorite flag.')
    e.set_defaults(func=cmd_edit)

    d = sub.add_parser('edit-dex', help='Edit one shared Pokédex entry.',
                       description='Change seen, obtained, shiny, form, or crown flags.')
    d.add_argument('input', type=Path, help='Input savedata.bin')
    d.add_argument('output', type=Path, help='Output savedata.bin')
    d.add_argument('--species', type=int, required=True, help='Internal species ID (1-based).')
    d.add_argument('--obtained', action=argparse.BooleanOptionalAction, help='Set or clear obtained state.')
    d.add_argument('--seen', action=argparse.BooleanOptionalAction, help='Set or clear seen state.')
    d.add_argument('--forms', type=lambda x: int(x, 0), help='Form bitmask (hex or decimal).')
    d.add_argument('--shiny', action=argparse.BooleanOptionalAction, help='Set or clear shiny state.')
    d.add_argument('--crown', choices=CROWN_VALUES, help='Set right crown: none, bronze, silver, or gold.')
    d.add_argument('--centered', action=argparse.BooleanOptionalAction, help='Set or clear the center crown.')
    d.set_defaults(func=cmd_dex)

    v = sub.add_parser('validate', help='Validate save checksums and box structure.',
                       description='Check file size, SHA-1, encryption round-trip, and all three box regions.')
    v.add_argument('input', type=Path, help='Encrypted or decrypted savedata.bin')
    v.set_defaults(func=cmd_validate)

    h = sub.add_parser('help', help='Show general or command-specific help.')
    h.add_argument('topic', nargs='?', choices=('list', 'edit-pokemon', 'edit-dex', 'validate'), help='Command to describe.')
    h.set_defaults(func=show_help, root_parser=p, command_parsers={
        'list': l, 'edit-pokemon': e, 'edit-dex': d, 'validate': v,
    })

    args = p.parse_args()
    args.func(args)

if __name__ == '__main__': main()
