import json
import os
import sys
from card import Card


# PyInstaller でビルドした場合は sys._MEIPASS を使う
_BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_BASE, "data")


def load_deck_from_json(filepath: str) -> list[Card]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    cards = []
    for entry in data:
        count = entry.get("count", 1)
        for _ in range(count):
            c = Card(
                name=entry["name"],
                card_type=entry["type"],
                civilization=entry["civilization"],
                cost=entry["cost"],
                power=entry.get("power", 0),
                breaker=entry.get("breaker", 1),
                blocker=entry.get("blocker", False),
                trigger=entry.get("trigger", False),
                effects=entry.get("effects", []),
                evolution_target=entry.get("evolution_target", None),
                civilizations=entry.get("civilizations", []),
                race=entry.get("race", ""),
                god_link_name=entry.get("god_link_name", ""),
                god_link_side=entry.get("god_link_side", ""),
            )
            # Store base power for dynamic scaling
            if "power_scale_fire_graveyard" in c.effects:
                c.base_power = c.power
            cards.append(c)

    return cards


def load_deck(civilization: str) -> list[Card]:
    filename = f"{civilization.lower()}_deck.json"
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"デッキファイルが見つかりません: {path}")
    deck = load_deck_from_json(path)
    print(f"  [{civilization}デッキ] {len(deck)} 枚読み込み完了。")
    return deck


CIVILIZATION_NAMES = {
    "1": ("Fire",   "火文明（速攻・ビートダウン）"),
    "2": ("Water",  "水文明（ドロー・コントロール）"),
    "3": ("Nature", "自然文明（マナブースト）"),
    "4": ("Light",  "光文明（ブロッカー・防御）"),
    "5": ("Dark",   "闇文明（除去・墓地）"),
}
