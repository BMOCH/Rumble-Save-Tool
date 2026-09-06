"""Pokémon Rumble save decoding, box parsing, and structural validation utilities."""
import argparse
from collections import Counter
from hashlib import sha1
import json
from pathlib import Path

SIZE = 0x34000
STRIDE = 45


def decode_save(raw):
    if len(raw) != SIZE:
        raise ValueError(f"Expected {SIZE} bytes, got {len(raw)}")
    data = bytearray(raw)
    # Reverse the save's 16-byte block transform, including the chunk-zero dependency.
    for chunk in range(0x33FF, -1, -1):
        p = chunk * 16
        for i in range(16):
            data[p + i] = (data[p + i] - data[p + ((chunk + i) & 15) - 16]) & 255
    if sha1(data[20:]).digest() != data[:20]:
        raise ValueError("Decrypted SHA-1 mismatch")
    return bytes(data)


def encode_save(data):
    """Encode decoded save data using the format's 16-byte block transform."""
    if any(data[-16:]):
        raise ValueError("The final 16 bytes must be zero before encoding")
    result = bytearray(data)
    result[:20] = sha1(result[20:]).digest()
    for chunk in range(1, 0x3400):
        p = chunk * 16
        for i in range(16):
            result[p + i] = (result[p + i] + result[p + ((chunk + i) & 15) - 16]) & 255
    return bytes(result)


def find_box_sections(data):
    """Locate the three Pokémon box sections in decoded save data."""
    found = []
    pos = 0
    while (pos := data.find(b"\x01\x00\x2c", pos)) != -1:
        marker = pos
        pos += 1
        count = int.from_bytes(data[marker + 3:marker + 5], "big")
        start = marker + 5
        end = start + count * STRIDE
        if end + 3 > len(data) or data[end:end + 3] != b"\x02\x00\x04":
            continue
        records = [data[start + i * STRIDE:start + (i + 1) * STRIDE] for i in range(count)]
        found.append((start, records))
    if len(found) != 3:
        raise ValueError(f"Expected three Pokémon box sections, found {len(found)}")
    return found


def validate_save_data(data):
    """Validate decrypted save data and return basic structural information."""
    if len(data) != SIZE:
        raise ValueError(f"Expected {SIZE} decrypted bytes, got {len(data)}")
    if sha1(data[20:]).digest() != data[:20]:
        raise ValueError("Decrypted SHA-1 mismatch")
    box_sections = find_box_sections(data)
    encrypted = encode_save(data)
    return {
        "size": len(data),
        "box_counts": {label: len(records) for label, (_, records) in zip("ABC", box_sections)},
        "roundtrip_valid": decode_save(encrypted) == bytes(data),
    }


def validate_save_file(path):
    """Validate an encrypted or normal savedata.bin file."""
    path = Path(path)
    raw = path.read_bytes()
    data = decode_save(raw)
    result = validate_save_data(data)
    result.update({"path": str(path), "encrypted_size": len(raw), "encrypted_roundtrip": encode_save(data) == raw})
    if not result["encrypted_roundtrip"]:
        raise ValueError("Encryption round-trip mismatch")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or [Path(__file__).resolve().parent / "saves" / p for p in (
        "savedata.bin", "savedata-no-garchomp.bin",
        "savedata-save-c-deleted.bin", "savedata-save-c-initialized-rattata.bin")]
    results = []
    parsed_sections = []
    for path in paths:
        raw = path.read_bytes()
        data = decode_save(raw)
        if encode_save(data) != raw:
            raise ValueError(f"{path}: round trip mismatch")
        box_sections = find_box_sections(data)
        parsed_sections.append(box_sections)
        slots = []
        for label, (start, records) in zip("ABC", box_sections):
            species = [int.from_bytes(r[:2], "big") >> 7 for r in records]
            slots.append(dict(slot=label, start=hex(start), end_exclusive=hex(start + len(records) * STRIDE),
                              count=len(records), species_ids=species,
                              fingerprints=[r[34:44].hex() for r in records]))
        fingerprints = [set(s["fingerprints"]) for s in slots]
        results.append(dict(file=str(path), file_sha1=sha1(raw).hexdigest(),
                            checksum_valid=True, roundtrip_identical=True,
                            last_nonzero=hex(max(i for i, b in enumerate(data) if b)),
                            slots=slots, fingerprint_intersections=[len(fingerprints[i] & fingerprints[j])
                                                                    for i, j in ((0, 1), (0, 2), (1, 2))]))
    report = dict(saves=results)
    if len(parsed_sections) >= 2:
        before, after = (Counter(p[0][1]) for p in parsed_sections[:2])
        report["first_pair_box_A_removed_records"] = [r.hex() for r in (before - after).elements()]
        report["first_pair_box_A_added_records"] = [r.hex() for r in (after - before).elements()]
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
