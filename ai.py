"""
AI decision-making module.
Levels:
  1 = Random
  2 = Rule-based (cost efficiency, power priority, blocker preference)
  3 = Strategic (lethal calculation, trigger awareness)
"""
import random
from card import Card
from player import Player


# ──────────────────── Mana charge ────────────────────

def decide_mana_charge(p: Player, game) -> Card | None:
    if not p.hand:
        return None
    level = p.ai_level

    if level == 1:
        # Random: always charge if hand > 2
        if len(p.hand) > 2:
            return random.choice(p.hand)
        return None

    # Level 2/3: charge the least impactful card
    mana = p.total_mana()
    unplayable = [c for c in p.hand if p.effective_cost(c) > mana]
    if unplayable:
        # Charge lowest-power unplayable
        return min(unplayable, key=lambda c: (c.power if c.power else 0))

    # All cards playable: charge lowest effective cost if hand is large
    if len(p.hand) >= 4:
        return min(p.hand, key=lambda c: p.effective_cost(c))
    return None


# ──────────────────── Main phase ─────────────────────

def _god_link_ready(p: Player) -> bool:
    """Return True if a new God Link pair can be formed in battle zone."""
    bz_gods = [c for c in p.battle_zone if c.god_link_name and not c.is_linked]
    by_name: dict = {}
    for c in bz_gods:
        by_name.setdefault(c.god_link_name, set()).add(c.god_link_side)
    return any("left" in s and "right" in s for s in by_name.values())


def ai_main_phase(p: Player, o: Player, game):
    level = p.ai_level
    acted = True
    while acted and not game.winner:
        acted = False
        playable_c = [c for c in p.hand if c.card_type == "creature"  and p.can_pay(c)]
        playable_s = [c for c in p.hand if c.card_type == "spell"     and p.can_pay(c)]
        playable_e = [c for c in p.hand if c.card_type == "evolution" and p.can_pay(c)]

        if level == 1:
            pool = [(c, "creature") for c in playable_c] + [(c, "spell") for c in playable_s]
            if pool:
                card, kind = random.choice(pool)
                if kind == "creature":
                    game.summon_creature(p, o, card)
                else:
                    game.play_spell(p, o, card)
                acted = True
            continue

        # Level 2 / 3 rule-based
        # 0. Play God card that would complete a link
        bz_god_names = {c.god_link_name for c in p.battle_zone if c.god_link_name and not c.is_linked}
        link_completer = next(
            (c for c in playable_c if c.god_link_name and c.god_link_name in bz_god_names),
            None,
        )
        if link_completer:
            game.summon_creature(p, o, link_completer)
            acted = True
            continue

        # 1a. Awakening spell when Awakened creature is in hand
        has_awakened_in_hand = any(c.card_type == "creature" and c.race == "Awakened" for c in p.hand)
        awaken_spells = [c for c in playable_s if "awaken_from_hand" in c.effects]
        if has_awakened_in_hand and awaken_spells:
            game.play_spell(p, o, awaken_spells[0])
            acted = True
            continue

        # 1. Evolution first (free attack)
        for evo in playable_e:
            base = next(
                (c for c in p.battle_zone if c.civilization == evo.evolution_target),
                None,
            )
            if base:
                game.evolve(p, o, evo, base)
                acted = True
                break
        if acted:
            continue

        # 2. Removal spells when opponent has creatures
        removal_effects = {
            "destroy_opponent_creature",
            "destroy_all_opponent_creatures",
            "destroy_creature_power_lte_3000",
            "destroy_all_creatures_power_lte_3000",
        }
        if o.battle_zone:
            removal = [c for c in playable_s if any(e in removal_effects for e in c.effects)]
            if removal:
                game.play_spell(p, o, removal[0])
                acted = True
                continue

        # 3. Blockers when shields low
        if len(p.shields) <= 2:
            block_creatures = [c for c in playable_c if c.blocker]
            if block_creatures:
                best = max(block_creatures, key=lambda c: c.power)
                game.summon_creature(p, o, best)
                acted = True
                continue

        # 4. Highest power creature
        if playable_c:
            best = max(playable_c, key=lambda c: c.power)
            game.summon_creature(p, o, best)
            acted = True
            continue

        # 5. Draw spell if hand low
        if len(p.hand) <= 2:
            draw_spells = [c for c in playable_s if any(e.startswith("draw_") for e in c.effects)]
            if draw_spells:
                game.play_spell(p, o, draw_spells[0])
                acted = True
                continue

        # 6. Any remaining spell
        if playable_s:
            game.play_spell(p, o, playable_s[0])
            acted = True


# ──────────────────── Attack phase ───────────────────

def ai_attack_phase(p: Player, o: Player, game):
    level = p.ai_level

    while not game.winner:
        atks = p.attackers()
        if not atks:
            break

        if level == 1:
            attacker = random.choice(atks)

        elif level == 2:
            attacker = max(atks, key=lambda c: c.power)

        else:  # level 3 strategic
            shields_left = len(o.shields)
            total_break = sum(c.breaker for c in atks)

            if total_break >= shields_left + 1 and not _has_dangerous_trigger(o):
                # Go for lethal
                attacker = max(atks, key=lambda c: c.breaker * 100 + c.power)
            else:
                # 積極的に攻撃: 相手クリーチャーの有無・有利不利に関わらず最強で突撃
                attacker = max(atks, key=lambda c: c.power)

        game._do_attack(p, o, attacker)


def _has_dangerous_trigger(p: Player) -> bool:
    """Estimate if opponent's shields might have a dangerous trigger."""
    return len(p.shields) > 0  # Conservative: always assume trigger possible


# ──────────────────── Blocker choice ─────────────────

def ai_choose_blocker(defender: Player, attacker: Card, game) -> Card | None:
    available = defender.available_blockers()
    if not available:
        return None
    level = defender.ai_level

    if level == 1:
        return random.choice(available) if random.random() < 0.5 else None

    # Level 2+: block only if we win or tie (or shields very low)
    atk_pow = attacker.linked_power()
    winning = [c for c in available if c.linked_power() >= atk_pow]
    if winning:
        return min(winning, key=lambda c: c.power)  # Use minimum resource to win
    if len(defender.shields) <= 1:
        return min(available, key=lambda c: c.power)  # Sacrifice weakest to survive
    return None
