import random
from card import Card


class Player:
    def __init__(self, name: str, deck_cards: list, is_human: bool = True, ai_level: int = 1):
        self.name = name
        self.is_human = is_human
        self.ai_level = ai_level
        self.deck = [c.make_copy() for c in deck_cards]
        self.hand: list[Card] = []
        self.mana: list[Card] = []
        self.shields: list[Card] = []
        self.battle_zone: list[Card] = []
        self.graveyard: list[Card] = []
        self.mana_charged_this_turn = False

    # ── Setup ──────────────────────────────────────────

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def setup(self):
        self.shuffle_deck()
        for _ in range(5):
            if self.deck:
                self.shields.append(self.deck.pop(0))
        self.draw(5)

    # ── Draw ───────────────────────────────────────────

    def draw(self, n: int = 1) -> bool:
        drew = False
        for _ in range(n):
            if not self.deck:
                return False
            self.hand.append(self.deck.pop(0))
            drew = True
        return drew

    # ── Mana ───────────────────────────────────────────

    def total_mana(self) -> int:
        return len(self.mana)

    def untapped_mana_count(self) -> int:
        return sum(1 for c in self.mana if not c.tapped)

    def has_civ_in_mana(self, civs: list) -> bool:
        return any(c.civilization in civs and not c.tapped for c in self.mana)

    def effective_cost(self, card: Card) -> int:
        cost = card.cost
        if card.race == "Dragon" and any("dragon_cost_reduce" in c.effects for c in self.battle_zone):
            cost = max(1, cost - 1)
        return cost

    def can_pay(self, card: Card) -> bool:
        if self.untapped_mana_count() < self.effective_cost(card):
            return False
        return self.has_civ_in_mana(card.all_civs)

    def pay_mana(self, cost: int, civs: list) -> bool:
        if not self.has_civ_in_mana(civs):
            return False
        # First tap one card matching the required civilization(s)
        for c in self.mana:
            if not c.tapped and c.civilization in civs:
                c.tap()
                cost -= 1
                break
        # Then tap any remaining
        for c in self.mana:
            if cost <= 0:
                break
            if not c.tapped:
                c.tap()
                cost -= 1
        return cost <= 0

    def charge_mana(self, card: Card) -> bool:
        if card not in self.hand:
            return False
        self.hand.remove(card)
        card.tapped = False
        self.mana.append(card)
        self.mana_charged_this_turn = True
        return True

    def untap_all(self):
        for c in self.mana:
            c.tapped = False
        for c in self.battle_zone:
            c.tapped = False
            c.summoning_sick = False
        self.mana_charged_this_turn = False

    # ── Battle ─────────────────────────────────────────

    def _linked_partner_ids(self) -> set:
        """Return id() set of right-side partners (hidden from action lists)."""
        return {
            id(c.link_partner)
            for c in self.battle_zone
            if c.is_linked and c.link_partner and c.god_link_side == "left"
        }

    def attackers(self) -> list:
        partner_ids = self._linked_partner_ids()
        return [c for c in self.battle_zone if c.can_attack() and id(c) not in partner_ids]

    def available_blockers(self) -> list:
        partner_ids = self._linked_partner_ids()
        blocker_flag = lambda c: c.blocker or (c.is_linked and c.link_partner and c.link_partner.blocker)
        return [c for c in self.battle_zone if blocker_flag(c) and not c.tapped and id(c) not in partner_ids]

    # ── Display ────────────────────────────────────────

    def show_hand(self):
        if not self.hand:
            print("  (手札なし)")
            return
        for i, c in enumerate(self.hand):
            print(f"  [{i}] {c.display()}")

    def show_battle_zone(self):
        if not self.battle_zone:
            print("  (クリーチャーなし)")
            return
        for i, c in enumerate(self.battle_zone):
            print(f"  [{i}] {c.display()}")

    def show_mana(self):
        if not self.mana:
            print("  マナ: (なし)")
            return
        from collections import Counter
        total_civ = Counter(c.civilization for c in self.mana)
        untap_civ = Counter(c.civilization for c in self.mana if not c.tapped)
        CIV_JP = {"Fire": "火", "Water": "水", "Nature": "自", "Light": "光", "Dark": "闇"}
        parts = []
        for civ in ["Fire", "Water", "Nature", "Light", "Dark"]:
            if total_civ[civ] > 0:
                jp = CIV_JP[civ]
                u = untap_civ[civ]
                t = total_civ[civ]
                parts.append(f"{jp}{u}/{t}")
        print(f"  マナ: {' '.join(parts)}  (合計{len(self.mana)}, 未タップ{self.untapped_mana_count()})")
