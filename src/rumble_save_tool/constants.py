"""Editor-facing labels and constants loaded from the bundled data files."""
from enum import IntEnum
import json

from .paths import DATA


class Trait(IntEnum):
    """A trait's stored ID, display name, and in-game effect."""

    def __new__(cls, value, label, effect):
        member = int.__new__(cls, value)
        member._value_ = value
        member.label = label
        member.effect = effect
        return member

    NONE = (0, "None", "No special trait effect.")
    SPEEDY = (1, "Speedy", "Moves around faster.")
    SNAPPY = (2, "Snappy", "Can use moves quickly.")
    PUNCHY = (3, "Punchy", "Higher Attack.")
    BRAWNY = (4, "Brawny", "Higher HP.")
    HARDY = (5, "Hardy", "Higher Defense.")
    LUCKY = (6, "Lucky", "Foes drop more P.")
    HEALTHY = (7, "Healthy", "Slowly restores HP.")
    RALLY = (8, "Rally", "Strengthens other players’ Pokémon in multiplayer.")
    SCRAPPY = (9, "Scrappy", "Higher critical-hit rate.")
    GUTSY = (10, "Gutsy", "Very high critical-hit rate.")
    PERKY = (11, "Perky", "Recovers quickly from status changes.")
    STEADY = (12, "Steady", "Unaffected by status changes.")
    TECHIE = (13, "Techie", "Moves with fewer stars become stronger.")
    FEISTY = (14, "Feisty", "Moves sweep foes farther.")
    MIGHTY = (15, "Mighty", "Less affected by sweeping.")
    NORMAL_GUARD = (16, "Normal Guard", "Normal-type moves do less damage.")
    FIGHTING_GUARD = (17, "Fighting Guard", "Fighting-type moves do less damage.")
    FLYING_GUARD = (18, "Flying Guard", "Flying-type moves do less damage.")
    POISON_GUARD = (19, "Poison Guard", "Poison-type moves do less damage.")
    GROUND_GUARD = (20, "Ground Guard", "Ground-type moves do less damage.")
    ROCK_GUARD = (21, "Rock Guard", "Rock-type moves do less damage.")
    BUG_GUARD = (22, "Bug Guard", "Bug-type moves do less damage.")
    GHOST_GUARD = (23, "Ghost Guard", "Ghost-type moves do less damage.")
    STEEL_GUARD = (24, "Steel Guard", "Steel-type moves do less damage.")
    DUMMY = (25, "Dummy (test)", "Explanation to dummy.")
    FIRE_GUARD = (26, "Fire Guard", "Fire-type moves do less damage.")
    WATER_GUARD = (27, "Water Guard", "Water-type moves do less damage.")
    GRASS_GUARD = (28, "Grass Guard", "Grass-type moves do less damage.")
    ELECTRIC_GUARD = (29, "Electric Guard", "Electric-type moves do less damage.")
    PSYCHIC_GUARD = (30, "Psychic Guard", "Psychic-type moves do less damage.")
    ICE_GUARD = (31, "Ice Guard", "Ice-type moves do less damage.")
    DRAGON_GUARD = (32, "Dragon Guard", "Dragon-type moves do less damage.")
    DARK_GUARD = (33, "Dark Guard", "Dark-type moves do less damage.")

    @classmethod
    def from_label(cls, label):
        for trait in cls:
            if trait.label.casefold() == label.strip().casefold():
                return trait
        return None

    @classmethod
    def label_for(cls, value):
        trait = cls._value2member_map_.get(value)
        return trait.label if trait else f"Unknown ({value})"


MOVES = {int(key): value for key, value in json.loads(
    (DATA / "moves.json").read_text(encoding="utf-8")
).items()}

