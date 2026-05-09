"""
デュエル・マスターズ Python実装
設計書: C:/Users/masak/OneDrive/Duel/設計書.docx
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from player import Player
from game import Game
from deck_builder import load_deck, load_deck_from_json, CIVILIZATION_NAMES
import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

EXTRA_DECKS = {
    "6": ("god",     "ゴッドデッキ（光/火/水/自然・ゴッドリンク）"),
    "7": ("shinrei", "神帝デッキ（5文明混合・神帝クリーチャー）"),
    "8": ("atom",    "神核アトムデッキ（光/闇・ゴッドリンク）"),
    "9": ("kakusei", "覚醒デッキ（光/水・覚醒呪文召喚）"),
}

ALL_DECKS = {**CIVILIZATION_NAMES, **EXTRA_DECKS}


def pick_deck(player_label: str) -> tuple[list, str]:
    print(f"\n--- {player_label} デッキ選択 ---")
    for key, (civ_or_file, desc) in ALL_DECKS.items():
        print(f"  {key}: {desc}")
    while True:
        choice = input("番号を入力 (1-7): ").strip()
        if choice in CIVILIZATION_NAMES:
            civ, desc = CIVILIZATION_NAMES[choice]
            deck = load_deck(civ)
            print(f"  → {desc} を選択。")
            return deck, civ
        if choice in EXTRA_DECKS:
            file_key, desc = EXTRA_DECKS[choice]
            path = os.path.join(_DATA_DIR, f"{file_key}_deck.json")
            deck = load_deck_from_json(path)
            print(f"  → {desc} を選択。({len(deck)}枚)")
            return deck, file_key
        print("  無効な入力。1〜9 で選択してください。")


def pick_ai_level() -> int:
    print("\nAIレベル選択:")
    print("  1: ランダムAI（簡単）")
    print("  2: ルールベースAI（普通）")
    print("  3: 戦略AI（難しい）")
    while True:
        choice = input("番号を入力 (1-3): ").strip()
        if choice in ("1", "2", "3"):
            return int(choice)
        print("  無効な入力。")


def _select_decks_and_build(mode: str, ai_level: int) -> tuple:
    """デッキ選択を行い (player1, player2) を返す。再戦ごとに呼び出す。"""
    if mode == "1":
        p1_deck, _ = pick_deck("プレイヤー1（あなた）")
        ai_choice_key = random.choice(list(ALL_DECKS.keys()))
        if ai_choice_key in CIVILIZATION_NAMES:
            ai_civ, ai_desc = CIVILIZATION_NAMES[ai_choice_key]
            ai_deck = load_deck(ai_civ)
        else:
            file_key, ai_desc = EXTRA_DECKS[ai_choice_key]
            ai_deck = load_deck_from_json(os.path.join(_DATA_DIR, f"{file_key}_deck.json"))
        print(f"\nAI は {ai_desc} を使用。（レベル{ai_level}）")
        return (
            Player("プレイヤー1", p1_deck, is_human=True),
            Player("AI", ai_deck, is_human=False, ai_level=ai_level),
        )

    elif mode == "2":
        all_keys = list(ALL_DECKS.keys())
        k1, k2 = random.sample(all_keys, 2)
        _, desc1 = ALL_DECKS[k1]
        _, desc2 = ALL_DECKS[k2]
        def _load_by_key(k):
            if k in CIVILIZATION_NAMES:
                return load_deck(CIVILIZATION_NAMES[k][0])
            fk, _ = EXTRA_DECKS[k]
            return load_deck_from_json(os.path.join(_DATA_DIR, f"{fk}_deck.json"))
        deck1 = _load_by_key(k1)
        deck2 = _load_by_key(k2)
        name1 = f"AI-1({desc1.split('（')[0]})"
        name2 = f"AI-2({desc2.split('（')[0]})"
        print(f"\n{name1} vs {name2}")
        return (
            Player(name1, deck1, is_human=False, ai_level=ai_level),
            Player(name2, deck2, is_human=False, ai_level=ai_level),
        )

    else:  # mode == "3"
        p1_deck, _ = pick_deck("プレイヤー1")
        p2_deck, _ = pick_deck("プレイヤー2")
        return (
            Player("プレイヤー1", p1_deck, is_human=True),
            Player("プレイヤー2", p2_deck, is_human=True),
        )


def main():
    print("=" * 55)
    print("    デュエル・マスターズ  Python版")
    print("=" * 55)
    print("\nゲームモード:")
    print("  1: 人間 vs AI")
    print("  2: AI vs AI（観戦）")
    print("  3: 人間 vs 人間")

    mode = input("モードを選択 (1-3): ").strip()
    if mode not in ("1", "2", "3"):
        print("無効なモード。終了します。")
        return

    # AIレベルは最初に1度だけ選択（再戦でも同じレベルを使用）
    ai_level = pick_ai_level() if mode in ("1", "2") else 1

    # ── ゲームループ（再戦ごとにデッキ選択）────────────────────
    first_game = True
    while True:
        if not first_game:
            print("\n" + "=" * 55)
            print("    再戦！  デッキを選択してください。")
            print("=" * 55 + "\n")
        first_game = False

        player1, player2 = _select_decks_and_build(mode, ai_level)
        game = Game(player1, player2)
        game.run()

        print("再戦しますか？ (yes: 再戦 / Enter: 終了): ", end="")
        ans = input().strip().lower()
        if ans not in ("yes", "y"):
            print("\nありがとうございました！")
            break


if __name__ == "__main__":
    main()
