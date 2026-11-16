"""Regression cases derived from controlled observations and live Dolphin checks."""
import unittest

from src.rumble_save_tool.power import estimate_power, slot_power_context


def record(species, level, seed, trainer=1, form=0):
    result = bytearray(45)
    result[:2] = ((species << 7) | (form << 2)).to_bytes(2, 'big')
    result[6:8] = level.to_bytes(2, 'big')
    result[20:24] = seed.to_bytes(4, 'big')
    result[40:44] = trainer.to_bytes(4, 'big')
    return result


class PowerTests(unittest.TestCase):
    def test_rattata_level_change(self):
        r = record(19, 30, 0x00010000)
        self.assertEqual(estimate_power(r), 388)
        r[6:8] = (31).to_bytes(2, 'big')
        self.assertEqual(estimate_power(r), 405)

    def test_transferred_pokemon_cap(self):
        # Slot B's live Giratina and Shaymin are capped at 399 at rank A.
        context = (2, 0, 3)
        for r, uncapped in ((record(487, 98, 0x963dc723, form=1), 2331),
                            (record(492, 105, 0xeb9fb4cf, form=1), 2335)):
            self.assertEqual(estimate_power(r), uncapped)
            self.assertEqual(estimate_power(r, context), 399)
            self.assertEqual(estimate_power(r, (1, 0, 3)), uncapped)
            self.assertEqual(estimate_power(r, (2, 2, 1)), uncapped)

    def test_slot_context(self):
        data = bytearray(5000)
        data[12:14] = bytes([3, 0])
        data[4832:4836] = (2).to_bytes(4, 'big')
        self.assertEqual(slot_power_context(data, 4869), (2, 0, 3))
        self.assertIsNone(slot_power_context(data, 10))

    def test_unsupported_form(self):
        self.assertIsNone(estimate_power(record(19, 30, 0, form=31)))


if __name__ == '__main__':
    unittest.main()
