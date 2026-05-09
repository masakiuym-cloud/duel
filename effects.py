"""
Effect dispatcher. Each effect function receives (game, user, card, **kwargs).
"""
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game
    from player import Player
    from card import Card


def _opponent(game, user):
    return next(p for p in game.players if p is not user)


def _destroy(player, card):
    """Destroy a creature, correctly handling God Link (sends both halves to graveyard)."""
    if card not in player.battle_zone:
        return  # Already removed (partner was destroyed first by an AoE)
    if card.is_linked and card.link_partner:
        partner = card.link_partner
        card.is_linked = False
        card.link_partner = None
        partner.is_linked = False
        partner.link_partner = None
        _send_to_graveyard(player, card)
        if partner in player.battle_zone:
            _send_to_graveyard(player, partner)
        else:
            player.graveyard.append(partner)
    else:
        _send_to_graveyard(player, card)


# ──────────────────── Draw effects ────────────────────

def draw_1(game, user, card, **kw):
    user.draw(1)
    game.log(f"{user.name} が 1 枚ドロー。")

def draw_2(game, user, card, **kw):
    user.draw(2)
    game.log(f"{user.name} が 2 枚ドロー。")

def draw_3(game, user, card, **kw):
    user.draw(3)
    game.log(f"{user.name} が 3 枚ドロー。")


# ──────────────────── Destroy effects ────────────────────

def destroy_opponent_creature(game, user, card, **kw):
    opp = _opponent(game, user)
    if not opp.battle_zone:
        game.log("対象クリーチャーなし。")
        return
    target = game.choose_creature(opp, user, "破壊するクリーチャーを選択")
    if target:
        _destroy(opp, target)
        game.log(f"{target.name} が破壊された。")

def destroy_creature_power_lte_3000(game, user, card, **kw):
    opp = _opponent(game, user)
    # Use linked_power() so God-Linked pairs are evaluated at their combined power
    targets = [c for c in opp.battle_zone if c.linked_power() <= 3000]
    if not targets:
        game.log("パワー3000以下のクリーチャーなし。")
        return
    target = game.choose_from_list(targets, user, "破壊するクリーチャー(パワー≤3000)")
    if target:
        _destroy(opp, target)
        game.log(f"{target.name} が破壊された。")

def destroy_all_creatures_power_lte_3000(game, user, card, **kw):
    opp = _opponent(game, user)
    targets = [c for c in list(opp.battle_zone) if c.linked_power() <= 3000]
    destroyed = []
    for t in targets:
        if t in opp.battle_zone:  # may already be gone if it was a linked partner
            destroyed.append(t.name)
            _destroy(opp, t)
    if destroyed:
        game.log(f"パワー3000以下全破壊: {', '.join(destroyed)}")
    else:
        game.log("対象クリーチャーなし。")

def destroy_all_opponent_creatures(game, user, card, **kw):
    opp = _opponent(game, user)
    targets = list(opp.battle_zone)
    destroyed = []
    for t in targets:
        if t in opp.battle_zone:
            destroyed.append(t.name)
            _destroy(opp, t)
    if destroyed:
        game.log(f"相手の全クリーチャーを破壊: {', '.join(destroyed)}")
    else:
        game.log("相手にクリーチャーなし。")

def destroy_all_non_light(game, user, card, **kw):
    """アポカリプス・デイ: 光以外の全クリーチャーを破壊"""
    opp = _opponent(game, user)
    for player in [user, opp]:
        targets = [c for c in list(player.battle_zone) if c.civilization != "Light"]
        for t in targets:
            _destroy(player, t)
    game.log("アポカリプス・デイ: 光以外の全クリーチャーが破壊された。")


# ──────────────────── Bounce effects ────────────────────

def bounce_opponent_creature(game, user, card, **kw):
    opp = _opponent(game, user)
    if not opp.battle_zone:
        game.log("バウンス対象なし。")
        return
    target = game.choose_creature(opp, user, "手札に戻すクリーチャーを選択")
    if target:
        # Break God Link: only the targeted card bounces; partner stays in BZ unlinked
        if target.is_linked and target.link_partner:
            partner = target.link_partner
            target.is_linked = False
            target.link_partner = None
            partner.is_linked = False
            partner.link_partner = None
            game.log(f"ゴッドリンク解除！ [{partner.name}] はリンク解除でBZに残る。")
        opp.battle_zone.remove(target)
        target.tapped = False
        target.summoning_sick = False
        opp.hand.append(target)
        game.log(f"{target.name} が {opp.name} の手札に戻った。")


# ──────────────────── Hand destruction ────────────────────

def hand_destruction_1(game, user, card, **kw):
    opp = _opponent(game, user)
    if not opp.hand:
        game.log(f"{opp.name} の手札なし。")
        return
    if opp.is_human:
        discard = game.choose_from_list(opp.hand, user, f"{opp.name} の手札から捨てるカードを選択")
    else:
        discard = random.choice(opp.hand)
    if discard:
        opp.hand.remove(discard)
        opp.graveyard.append(discard)
        game.log(f"{opp.name} が {discard.name} を捨てた。")

def hand_destruction_all(game, user, card, **kw):
    """ロスト・ソウル: 相手の手札を全捨て"""
    opp = _opponent(game, user)
    count = len(opp.hand)
    opp.graveyard.extend(opp.hand)
    opp.hand.clear()
    game.log(f"ロスト・ソウル: {opp.name} の手札 {count} 枚が全滅。")


# ──────────────────── Mana effects ────────────────────

def mana_add_2(game, user, card, **kw):
    """デッキトップ2枚をマナへ"""
    added = 0
    for _ in range(2):
        if user.deck:
            c = user.deck.pop(0)
            c.tapped = False
            user.mana.append(c)
            added += 1
    game.log(f"{user.name} がデッキから {added} 枚マナへ追加。")


# ──────────────────── Power boost ────────────────────

def power_plus_2000_own(game, user, card, **kw):
    for c in user.battle_zone:
        c.power += 2000
    game.log(f"{user.name} のクリーチャー全員 +2000パワー。")


# ──────────────────── Special summon ────────────────────

def summon_blocker_from_hand(game, user, card, **kw):
    """ヘブンズ・ゲート: 手札からブロッカー2体を無料召喚"""
    summoned = 0
    for _ in range(2):
        blockers = [c for c in user.hand if c.card_type == "creature" and c.blocker]
        if not blockers:
            break
        target = game.choose_from_list(blockers, user, "無料召喚するブロッカーを選択")
        if target:
            user.hand.remove(target)
            target.summoning_sick = True
            target.tapped = False
            user.battle_zone.append(target)
            summoned += 1
            game.log(f"{target.name} が無料召喚。")
    if summoned == 0:
        game.log("手札にブロッカーなし。")

def awaken_from_hand(game, user, card, **kw):
    """覚醒呪文: 手札の覚醒クリーチャーを1体無料召喚（召喚酔いあり・登場時効果なし）"""
    targets = [c for c in user.hand if c.card_type == "creature" and c.race == "Awakened"]
    if not targets:
        game.log("手札に覚醒クリーチャーなし。")
        return
    target = game.choose_from_list(targets, user, "覚醒させるクリーチャーを選択")
    if target:
        user.hand.remove(target)
        target.summoning_sick = True
        target.tapped = False
        user.battle_zone.append(target)
        game.log(f"覚醒！ {target.name} が降臨！（PWR:{target.power}）")


def mana_creature_to_play(game, user, card, **kw):
    """母なる大地: マナのクリーチャーをバトルゾーンへ"""
    targets = [c for c in user.mana if c.card_type == "creature"]
    if not targets:
        game.log("マナにクリーチャーなし。")
        return
    target = game.choose_from_list(targets, user, "バトルゾーンに出すクリーチャーをマナから選択")
    if target:
        user.mana.remove(target)
        target.summoning_sick = True
        target.tapped = False
        user.battle_zone.append(target)
        game.log(f"{target.name} がマナからバトルゾーンへ。")

def revival_creature(game, user, card, **kw):
    """墓地からクリーチャーを復活"""
    targets = [c for c in user.graveyard if c.card_type in ("creature", "evolution")]
    if not targets:
        game.log("墓地にクリーチャーなし。")
        return
    target = game.choose_from_list(targets, user, "墓地から復活させるクリーチャーを選択")
    if target:
        user.graveyard.remove(target)
        target.summoning_sick = True
        target.tapped = False
        user.battle_zone.append(target)
        game.log(f"{target.name} が墓地から復活。")


# ──────────────────── When-enter effects ────────────────────

def when_enter_draw_1(game, user, card, **kw):
    user.draw(1)
    game.log(f"{card.name} 登場: {user.name} が 1 枚ドロー。")

def when_enter_bounce(game, user, card, **kw):
    bounce_opponent_creature(game, user, card, **kw)

def when_enter_discard_1(game, user, card, **kw):
    hand_destruction_1(game, user, card, **kw)


# ──────────────────── Passive markers (handled in battle logic) ────────────────────

def cant_be_blocked(game, user, card, **kw):
    pass  # Checked by name in _do_attack

def shield_burn(game, user, card, **kw):
    pass  # Checked by name in _break_shield

def power_scale_fire_graveyard(game, user, card, **kw):
    pass  # Recalculated each untap phase

def dragon_cost_reduce(game, user, card, **kw):
    pass  # Passive: checked in player.effective_cost

def god_link_untap_draw(game, user, card, **kw):
    pass  # Passive: triggered once in _try_god_link when link forms

def god_when_attack_burn(game, user, card, **kw):
    pass  # Passive: checked in _break_shield when linked

def god_atom_link_bounce(game, user, card, **kw):
    pass  # Passive: triggered in _try_god_link when atom_sol link forms


# ──────────────────── Description map ────────────────────

EFFECT_DESC = {
    "draw_1":                           "カードを1枚引く",
    "draw_2":                           "カードを2枚引く",
    "draw_3":                           "カードを3枚引く",
    "destroy_opponent_creature":        "相手クリーチャーを1体破壊",
    "destroy_creature_power_lte_3000":  "相手のパワー3000以下を1体破壊",
    "destroy_all_creatures_power_lte_3000": "パワー3000以下を全体破壊",
    "destroy_all_opponent_creatures":   "相手クリーチャーを全滅",
    "destroy_all_non_light":            "光以外のクリーチャーを全滅（自分含む）",
    "bounce_opponent_creature":         "相手クリーチャー1体を手札に戻す",
    "hand_destruction_1":               "相手の手札を1枚捨てさせる",
    "hand_destruction_all":             "相手の手札を全て捨てさせる",
    "mana_add_2":                       "デッキトップ2枚をマナに置く",
    "power_plus_2000_own":              "自分のクリーチャー全員パワー+2000",
    "summon_blocker_from_hand":         "手札のブロッカーを2体タダで召喚",
    "mana_creature_to_play":            "マナのクリーチャーを1体タダで召喚",
    "revival_creature":                 "墓地のクリーチャーを1体召喚",
    "when_enter_draw_1":                "【登場時】カードを1枚引く",
    "when_enter_bounce":                "【登場時】相手クリーチャー1体を手札に戻す",
    "when_enter_discard_1":             "【登場時】相手の手札を1枚捨てさせる",
    "cant_be_blocked":                  "ブロックされない",
    "shield_burn":                      "シールドを焼却（手札に来ない）",
    "power_scale_fire_graveyard":       "墓地の火クリーチャー数×パワー+1000",
    "dragon_cost_reduce":               "自分のドラゴンのコストを1下げる",
    "god_link_untap_draw":              "【ゴッドリンク成立時】1枚ドロー",
    "god_when_attack_burn":             "【ゴッドリンク後】攻撃時シールドを1枚焼却",
    "god_atom_link_bounce":             "【ゴッドリンク成立時】相手クリーチャー1体をバウンス",
    "awaken_from_hand":                 "手札の覚醒クリーチャーを1体無料召喚",
}


def describe_card(card) -> str:
    """カードの効果・能力を日本語で説明する文字列を返す。"""
    parts = []
    if card.blocker:
        parts.append("ブロッカー")
    if card.breaker == 2:
        parts.append("ダブルブレイカー")
    elif card.breaker >= 3:
        parts.append("トリプルブレイカー")
    if card.trigger:
        parts.append("S・トリガー")
    for eff in card.effects:
        desc = EFFECT_DESC.get(eff)
        if desc:
            parts.append(desc)
    return " / ".join(parts)


# ──────────────────── Dispatch map ────────────────────

EFFECT_MAP = {
    "draw_1": draw_1,
    "draw_2": draw_2,
    "draw_3": draw_3,
    "destroy_opponent_creature": destroy_opponent_creature,
    "destroy_creature_power_lte_3000": destroy_creature_power_lte_3000,
    "destroy_all_creatures_power_lte_3000": destroy_all_creatures_power_lte_3000,
    "destroy_all_opponent_creatures": destroy_all_opponent_creatures,
    "destroy_all_non_light": destroy_all_non_light,
    "bounce_opponent_creature": bounce_opponent_creature,
    "hand_destruction_1": hand_destruction_1,
    "hand_destruction_all": hand_destruction_all,
    "mana_add_2": mana_add_2,
    "power_plus_2000_own": power_plus_2000_own,
    "summon_blocker_from_hand": summon_blocker_from_hand,
    "mana_creature_to_play": mana_creature_to_play,
    "revival_creature": revival_creature,
    "when_enter_draw_1": when_enter_draw_1,
    "when_enter_bounce": when_enter_bounce,
    "when_enter_discard_1": when_enter_discard_1,
    "cant_be_blocked": cant_be_blocked,
    "shield_burn": shield_burn,
    "power_scale_fire_graveyard": power_scale_fire_graveyard,
    "dragon_cost_reduce": dragon_cost_reduce,
    "god_link_untap_draw": god_link_untap_draw,
    "god_when_attack_burn": god_when_attack_burn,
    "god_atom_link_bounce": god_atom_link_bounce,
    "awaken_from_hand": awaken_from_hand,
}


def apply_effect(effect_id: str, game, user, card, **kwargs):
    fn = EFFECT_MAP.get(effect_id)
    if fn:
        fn(game, user, card, **kwargs)
    else:
        game.log(f"未知エフェクト: {effect_id}")


def _send_to_graveyard(player, card):
    """Remove card from battle_zone (and its base if evolution) to graveyard."""
    if card in player.battle_zone:
        player.battle_zone.remove(card)
    player.graveyard.append(card)
    if hasattr(card, "_under") and card._under is not None:
        player.graveyard.append(card._under)
        card._under = None
