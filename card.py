from dataclasses import dataclass, field
from typing import List, Optional
import copy


CIVILIZATIONS = ["Fire", "Water", "Nature", "Light", "Dark"]
CARD_TYPES = ["creature", "spell", "evolution"]

_CIV_JP = {"Fire": "火", "Water": "水", "Nature": "自然", "Light": "光", "Dark": "闇"}


@dataclass
class Card:
    name: str
    card_type: str          # creature / spell / evolution
    civilization: str       # primary civilization
    cost: int
    power: int = 0
    breaker: int = 1        # 1=single, 2=double, 3=triple
    blocker: bool = False
    trigger: bool = False   # Shield Trigger
    effects: List[str] = field(default_factory=list)
    evolution_target: Optional[str] = None
    civilizations: List[str] = field(default_factory=list)
    race: str = ""

    # God Link fields
    god_link_name: str = ""       # pair identifier e.g. "zen_lahar"
    god_link_side: str = ""       # "left" or "right"

    # Runtime state (not part of equality)
    tapped: bool = field(default=False, compare=False, repr=False)
    summoning_sick: bool = field(default=False, compare=False, repr=False)
    is_linked: bool = field(default=False, compare=False, repr=False)
    link_partner: "Card | None" = field(default=None, compare=False, repr=False)

    def __post_init__(self):
        self.tapped = False
        self.summoning_sick = False
        self.is_linked = False
        self.link_partner = None

    @property
    def all_civs(self) -> List[str]:
        return self.civilizations if self.civilizations else [self.civilization]

    def untap(self):
        self.tapped = False
        self.summoning_sick = False

    def tap(self):
        self.tapped = True

    def can_attack(self) -> bool:
        return not self.tapped and not self.summoning_sick

    def linked_power(self) -> int:
        if self.is_linked and self.link_partner:
            return self.power + self.link_partner.power
        return self.power

    def linked_breaker(self) -> int:
        if self.is_linked and self.link_partner:
            return max(self.breaker, self.link_partner.breaker)
        return self.breaker

    def linked_effects(self) -> list:
        if self.is_linked and self.link_partner:
            return self.effects + self.link_partner.effects
        return self.effects

    def make_copy(self) -> "Card":
        c = copy.copy(self)
        c.effects = self.effects.copy()
        c.tapped = False
        c.summoning_sick = False
        c.is_linked = False
        c.link_partner = None
        if hasattr(self, "base_power"):
            c.base_power = self.base_power
        return c

    def display(self) -> str:
        civs = self.civilizations if self.civilizations else [self.civilization]
        civ_str = "/".join(_CIV_JP.get(c, c) for c in civs)
        parts = [f"[{self.name}]", f"({civ_str})", f"Cost:{self.cost}"]
        if self.card_type in ("creature", "evolution"):
            parts.append(f"PWR:{self.power}")
            if self.breaker == 2:
                parts.append("DB")
            elif self.breaker >= 3:
                parts.append("TB")
            if self.blocker:
                parts.append("Blk")
        if self.trigger:
            parts.append("ST")
        flags = []
        if self.tapped:
            flags.append("tap")
        if self.summoning_sick:
            flags.append("sick")
        if flags:
            parts.append(f"({','.join(flags)})")
        return " ".join(parts)
