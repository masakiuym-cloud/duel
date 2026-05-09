import random
from card import Card
from player import Player
from effects import apply_effect, _send_to_graveyard, describe_card


# ── Visual field helpers ───────────────────────────────────

def _disp_w(text: str) -> int:
    """Display width: CJK/kana chars count as 2, ASCII as 1."""
    return sum(2 if ord(ch) >= 0x3000 else 1 for ch in text)


def _fit(text: str, width: int) -> str:
    """Truncate and right-pad text to exactly `width` display columns."""
    dw, result = 0, []
    for ch in text:
        cw = 2 if ord(ch) >= 0x3000 else 1
        if dw + cw > width:
            break
        result.append(ch)
        dw += cw
    return "".join(result) + " " * (width - dw)


# Effects that are checked elsewhere (passive) and must NOT re-fire on summon
_PASSIVE_EFFECTS = frozenset({
    "cant_be_blocked",
    "shield_burn",
    "power_scale_fire_graveyard",
    "dragon_cost_reduce",
    "god_link_untap_draw",
    "god_when_attack_burn",
    "god_atom_link_bounce",
})

_CIV_J = {"Fire": "火", "Water": "水", "Nature": "自", "Light": "光", "Dark": "闇"}
_CARD_W = 16  # inner display columns per card box


def _card_box(card) -> list:
    W = _CARD_W
    if card.is_linked and card.link_partner:
        # God Link: display as wide double box
        p = card.link_partner
        DW = W * 2 + 3  # combined inner width
        bk = " TB" if card.linked_breaker() >= 3 else " DB" if card.linked_breaker() == 2 else ""
        blk = " Blk" if (card.blocker or p.blocker) else ""
        pwr_str = f"{card.linked_power()}{bk}{blk}"
        flags = " ".join(f"[{f}]" for f in (["tap"] if card.tapped else []) + (["sick"] if card.summoning_sick else []))
        link_name = _fit(f"{card.name}=={p.name}", DW)
        civ_left = "/".join(_CIV_J.get(c, c[0]) for c in card.all_civs)
        civ_right = "/".join(_CIV_J.get(c, c[0]) for c in p.all_civs)
        content = [
            link_name,
            _fit(f"{civ_left}/{civ_right}  C:{card.cost}+{p.cost}", DW),
            _fit(pwr_str, DW),
            _fit(flags, DW),
        ]
        bar = "=" * DW
        return ["+" + bar + "+"] + ["|" + l + "|" for l in content] + ["+" + bar + "+"]

    civ = "/".join(_CIV_J.get(c, c[0]) for c in card.all_civs)
    bk = " TB" if card.breaker >= 3 else " DB" if card.breaker == 2 else ""
    blk = " Blk" if card.blocker else ""
    pwr_str = "(spell)" if card.card_type == "spell" else f"{card.power}{bk}{blk}"
    flags = " ".join(
        f"[{f}]" for f in
        (["tap"] if card.tapped else []) + (["sick"] if card.summoning_sick else [])
    )
    content = [
        _fit(card.name, W),
        _fit(f"{civ}  C:{card.cost}", W),
        _fit(pwr_str, W),
        _fit(flags, W),
    ]
    bar = "─" * W
    return ["┌" + bar + "┐"] + ["│" + l + "│" for l in content] + ["└" + bar + "┘"]


def _render_bz(creatures: list) -> list:
    """Return display lines for a battle zone (no trailing newline)."""
    # Exclude right-side partners (they are rendered inside the left card's box)
    partner_ids = {id(c.link_partner) for c in creatures if c.is_linked and c.link_partner and c.god_link_side == "left"}
    visible = [c for c in creatures if id(c) not in partner_ids]
    if not visible:
        return ["  (なし)"]
    PER_ROW, GAP = 3, "  "
    blank = " " * (_CARD_W + 2)
    out = []
    for i in range(0, len(visible), PER_ROW):
        boxes = [_card_box(c) for c in visible[i: i + PER_ROW]]
        for li in range(max(len(b) for b in boxes)):
            out.append("  " + GAP.join(b[li] if li < len(b) else blank for b in boxes))
    return out


def _shields_row(shields: list, total: int = 5) -> str:
    n = len(shields)
    cells = " ".join("[◆]" if i < n else "[ ]" for i in range(total))
    return f"  {cells}  ({n}枚)"


class Game:
    def __init__(self, player1: Player, player2: Player):
        self.players = [player1, player2]
        self.current_idx = 0
        self.turn = 1
        self.winner: Player | None = None
        self._skip_first_draw = False

    # ── Properties ─────────────────────────────────────

    @property
    def current(self) -> Player:
        return self.players[self.current_idx]

    @property
    def opp(self) -> Player:
        return self.players[1 - self.current_idx]

    # ── Logging ────────────────────────────────────────

    def log(self, msg: str):
        print(f"  >> {msg}")

    # ── Game flow ──────────────────────────────────────

    def setup(self):
        for p in self.players:
            p.setup()
        self.log("ゲーム開始！")

    def run(self):
        self.setup()
        # ランダムに先行・後攻を決定
        self.current_idx = random.randint(0, 1)
        first = self.players[self.current_idx]
        second = self.players[1 - self.current_idx]
        self._skip_first_draw = True

        print("\n" + "="*55)
        print("    デュエル・マスターズ  START")
        print("="*55)
        print(f"\n  先攻: {first.name}")
        print(f"  後攻: {second.name}")
        print(f"  （先攻は1ターン目ドローなし）")

        while self.winner is None:
            self._do_turn()
            if self.winner:
                break
            self.current_idx = 1 - self.current_idx
            self.turn += 1

        print("\n" + "="*55)
        print(f"  勝者: {self.winner.name}!")
        print("="*55 + "\n")

    def _do_turn(self):
        p = self.current
        o = self.opp
        print(f"\n{'─'*55}")
        print(f"  ターン {self.turn}  [{p.name}]")
        print(f"{'─'*55}")

        self._phase_untap(p)
        if not self._phase_draw(p):
            self.winner = o
            self.log(f"{p.name} のデッキが切れた！{o.name} の勝利！")
            return
        self._phase_mana_charge(p)
        self._phase_main(p, o)
        if self.winner:
            return
        self._phase_attack(p, o)

    # ── Phases ─────────────────────────────────────────

    def _phase_untap(self, p: Player):
        p.untap_all()
        # Recalculate dynamic powers
        for c in p.battle_zone:
            if "power_scale_fire_graveyard" in c.effects:
                base = getattr(c, "base_power", c.power)
                fire_count = sum(
                    1 for g in p.graveyard
                    if g.civilization == "Fire" and g.card_type in ("creature", "evolution")
                )
                c.power = base + fire_count * 1000
        self.log("[アンタップ] 完了。")

    def _phase_draw(self, p: Player) -> bool:
        if self._skip_first_draw:
            self._skip_first_draw = False
            self.log("[ドロー] 先行1ターン目のためドローなし。")
            return True
        ok = p.draw(1)
        if ok:
            self.log(f"[ドロー] {p.hand[-1].name} をドロー。（手札{len(p.hand)}枚）")
        return ok

    def _phase_mana_charge(self, p: Player):
        self.log("[マナチャージフェーズ]")
        if p.is_human:
            self._human_mana_charge(p)
        else:
            self._ai_mana_charge(p)

    def _human_mana_charge(self, p: Player):
        self._show_state(p)
        print("\n  手札:")
        if not p.hand:
            print("  (手札なし)")
        else:
            for i, c in enumerate(p.hand):
                print(f"  [{i}] {c.display()}")
                desc = describe_card(c)
                if desc:
                    print(f"       {desc}")
        print("\n  マナチャージするカードの番号を入力 (スキップ: Enter): ", end="")
        choice = input().strip()
        if choice == "":
            return
        try:
            idx = int(choice)
            if 0 <= idx < len(p.hand):
                card = p.hand[idx]
                p.charge_mana(card)
                self.log(f"{card.name} をマナへ。（マナ{p.total_mana()}）")
            else:
                print("  無効な番号。スキップします。")
        except ValueError:
            print("  無効な入力。スキップします。")

    def _ai_mana_charge(self, p: Player):
        from ai import decide_mana_charge
        card = decide_mana_charge(p, self)
        if card:
            p.charge_mana(card)
            self.log(f"[AI] {card.name} をマナへ。（マナ{p.total_mana()}）")

    def _phase_main(self, p: Player, o: Player):
        self.log("[メインフェーズ]")
        if p.is_human:
            self._human_main(p, o)
        else:
            from ai import ai_main_phase
            ai_main_phase(p, o, self)
        if not self.winner:
            self._try_god_link(p)

    def _human_main(self, p: Player, o: Player):
        while True:
            self._show_state(p)

            print("\n  手札:")
            if not p.hand:
                print("  (手札なし)")
            else:
                for i, c in enumerate(p.hand):
                    if p.can_pay(c):
                        if c.card_type == "creature":
                            tag = "  ← 召喚可"
                        elif c.card_type == "spell":
                            tag = "  ← 使用可"
                        elif c.card_type == "evolution":
                            has_base = any(
                                not c.evolution_target or b.civilization == c.evolution_target
                                for b in p.battle_zone
                            )
                            tag = "  ← 進化可" if has_base else "  ← 進化元なし"
                        else:
                            tag = ""
                    else:
                        tag = f"  (コスト不足: 必要{p.effective_cost(c)}, 未タップ{p.untapped_mana_count()})"
                    print(f"  [{i}] {c.display()}{tag}")
                    desc = describe_card(c)
                    if desc:
                        print(f"       {desc}")

            print("\n  番号を入力: 召喚/使用/進化  /  done: メインフェーズ終了")
            cmd = input("コマンド: ").strip().lower()

            if cmd in ("done", "d", ""):
                break

            try:
                idx = int(cmd)
            except ValueError:
                print("  不明なコマンド。番号か done を入力してください。")
                continue

            if not (0 <= idx < len(p.hand)):
                print("  無効な番号。")
                continue

            card = p.hand[idx]
            if not p.can_pay(card):
                print(f"  マナが不足しています。(必要:{p.effective_cost(card)}, 未タップ:{p.untapped_mana_count()})")
                continue

            if card.card_type == "creature":
                self.summon_creature(p, o, card)
                if self.winner:
                    return
            elif card.card_type == "spell":
                self.play_spell(p, o, card)
                if self.winner:
                    return
            elif card.card_type == "evolution":
                valid_bases = [b for b in p.battle_zone
                               if not card.evolution_target or b.civilization == card.evolution_target]
                if not valid_bases:
                    print(f"  進化元なし。(条件: {card.evolution_target or '任意'})")
                    continue
                if len(valid_bases) == 1:
                    base = valid_bases[0]
                else:
                    print("  進化元を選択:")
                    for j, b in enumerate(valid_bases):
                        print(f"    [{j}] {b.display()}")
                    try:
                        zi = int(input("  番号: "))
                        if 0 <= zi < len(valid_bases):
                            base = valid_bases[zi]
                        else:
                            print("  無効な番号。")
                            continue
                    except ValueError:
                        print("  無効な入力。")
                        continue
                self.evolve(p, o, card, base)
                if self.winner:
                    return

    def _phase_attack(self, p: Player, o: Player):
        self.log("[アタックフェーズ]")
        if p.is_human:
            self._human_attack(p, o)
        else:
            from ai import ai_attack_phase
            ai_attack_phase(p, o, self)

    def _human_attack(self, p: Player, o: Player):
        while True:
            atks = p.attackers()
            if not atks:
                self.log("攻撃可能なクリーチャーなし。")
                break
            self._show_state(p)
            print("\n  攻撃可能なクリーチャー:")
            for i, c in enumerate(atks):
                print(f"  [{i}] {c.display()}")
            print("\n  番号を入力: 攻撃  /  done: アタックフェーズ終了")

            cmd = input("コマンド: ").strip().lower()
            if cmd in ("done", "d", ""):
                break
            try:
                idx = int(cmd)
                if not (0 <= idx < len(atks)):
                    print("  無効な番号。")
                    continue
                attacker = atks[idx]

                # Show attack target selection when opponent has visible creatures
                partner_ids = o._linked_partner_ids()
                opp_visible = [c for c in o.battle_zone if id(c) not in partner_ids]
                direct_target = None
                if opp_visible:
                    print(f"\n  [{attacker.name}（PWR:{attacker.linked_power()}）] の攻撃対象:")
                    print(f"  [S] シールドを攻撃（シールド{len(o.shields)}枚）")
                    for ci, c in enumerate(opp_visible):
                        print(f"  [{ci}] クリーチャーを攻撃: {c.display()}（PWR:{c.linked_power()}）")
                    choice = input("  対象 (S=シールド / 番号=クリーチャー): ").strip().lower()
                    if choice not in ("s", ""):
                        try:
                            ci = int(choice)
                            if 0 <= ci < len(opp_visible):
                                direct_target = opp_visible[ci]
                            else:
                                print("  無効な番号。シールドを攻撃します。")
                        except ValueError:
                            pass

                self._do_attack(p, o, attacker, direct_target)
                if self.winner:
                    return
            except ValueError:
                print("  不明なコマンド。番号か done を入力してください。")

    # ── Action helpers ─────────────────────────────────

    def summon_creature(self, p: Player, o: Player, card: Card):
        p.hand.remove(card)
        p.pay_mana(p.effective_cost(card), card.all_civs)
        card.summoning_sick = True
        card.tapped = False
        p.battle_zone.append(card)
        self.log(f"{p.name} が {card.name} を召喚。（PWR:{card.power}）")
        for eff in card.effects:
            if eff not in _PASSIVE_EFFECTS:
                apply_effect(eff, self, p, card)
                if self.winner:
                    return

    def play_spell(self, p: Player, o: Player, card: Card):
        p.hand.remove(card)
        p.pay_mana(p.effective_cost(card), card.all_civs)
        self.log(f"{p.name} が呪文 [{card.name}] を使用。")
        for eff in card.effects:
            apply_effect(eff, self, p, card)
            if self.winner:
                break
        p.graveyard.append(card)

    def evolve(self, p: Player, o: Player, evo: Card, base: Card):
        if evo.evolution_target and base.civilization != evo.evolution_target:
            print(f"進化条件: {evo.evolution_target} のクリーチャーが必要。")
            return
        if not p.can_pay(evo):
            print("マナが不足しています。")
            return
        p.hand.remove(evo)
        p.pay_mana(p.effective_cost(evo), evo.all_civs)
        p.battle_zone.remove(base)
        evo.summoning_sick = False  # Evolution can attack immediately
        evo.tapped = False
        evo._under = base
        p.battle_zone.append(evo)
        self.log(f"{p.name} が {base.name} を進化 → {evo.name}。（PWR:{evo.power}）")
        for eff in evo.effects:
            if eff not in _PASSIVE_EFFECTS:
                apply_effect(eff, self, p, evo)
                if self.winner:
                    return

    # ── Attack / Battle ────────────────────────────────

    def _do_attack(self, atk_player: Player, def_player: Player, attacker: Card, direct_target: "Card | None" = None):
        attacker.tap()
        cant_block = "cant_be_blocked" in attacker.linked_effects()
        atk_power = attacker.linked_power()

        # Direct creature attack: skip blocker selection and shield break
        if direct_target is not None:
            self.log(f"{attacker.name}（PWR:{atk_power}）が {direct_target.name} に直接攻撃！")
            self._resolve_battle(atk_player, def_player, attacker, direct_target)
            return

        blocker = None
        available = def_player.available_blockers()
        if available and not cant_block:
            if def_player.is_human:
                print(f"\n  {attacker.name}（PWR:{atk_power}）が攻撃！")
                print("  ブロッカー:")
                for i, c in enumerate(available):
                    print(f"    {i}: {c.display()}")
                choice = input("  ブロックするか？ (番号 / no): ").strip().lower()
                if choice not in ("no", "n", ""):
                    try:
                        idx = int(choice)
                        if 0 <= idx < len(available):
                            blocker = available[idx]
                    except ValueError:
                        pass
            else:
                from ai import ai_choose_blocker
                blocker = ai_choose_blocker(def_player, attacker, self)

        if blocker:
            blocker.tap()
            self._resolve_battle(atk_player, def_player, attacker, blocker)
        elif def_player.shields:
            self._break_shield(atk_player, def_player, attacker)
        else:
            self.log(f"{attacker.name} が {def_player.name} にダイレクトアタック！")
            self.winner = atk_player

    def _resolve_battle(self, atk_p, def_p, attacker: Card, blocker: Card):
        atk_pow = attacker.linked_power()
        blk_pow = blocker.linked_power()
        self.log(f"バトル: {attacker.name}({atk_pow}) vs {blocker.name}({blk_pow})")
        if atk_pow > blk_pow:
            self._god_send_to_graveyard(def_p, blocker)
            self.log(f"{blocker.name} が破壊された！")
        elif blk_pow > atk_pow:
            self._god_send_to_graveyard(atk_p, attacker)
            self.log(f"{attacker.name} が破壊された！")
        else:
            self._god_send_to_graveyard(atk_p, attacker)
            self._god_send_to_graveyard(def_p, blocker)
            self.log(f"相打ち！ {attacker.name} と {blocker.name} が両方破壊。")

    def _god_send_to_graveyard(self, player: Player, card: Card):
        """リンク済みなら両方を墓地へ。"""
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

    def _break_shield(self, atk_p: Player, def_p: Player, attacker: Card):
        breaks = min(attacker.linked_breaker(), len(def_p.shields))
        has_normal_burn = "shield_burn" in attacker.linked_effects()
        has_god_burn = attacker.is_linked and "god_when_attack_burn" in attacker.linked_effects()
        shield_burn = has_normal_burn or has_god_burn
        # God burn only burns 1 shield even with DB (prevents nullifying 2 STs per swing)
        god_burn_limit = 1 if has_god_burn and not has_normal_burn else breaks
        self.log(f"{attacker.name} がシールドを {breaks} 枚ブレイク！")

        burn_count = 0
        for _ in range(breaks):
            if not def_p.shields:
                break
            idx = random.randint(0, len(def_p.shields) - 1)
            shield = def_p.shields.pop(idx)
            self.log(f"  シールド公開: [{shield.name}]")

            if shield_burn and burn_count < god_burn_limit:
                burn_count += 1
                def_p.graveyard.append(shield)
                self.log(f"  ({attacker.name} のシールド焼却 → 手札に来ない)")
            elif shield.trigger:
                self.log(f"  ★ シールドトリガー発動！ [{shield.name}]")
                if shield.card_type == "spell":
                    for eff in shield.effects:
                        apply_effect(eff, self, def_p, shield)
                    def_p.graveyard.append(shield)
                else:
                    self._creature_st(def_p, shield)
            else:
                def_p.hand.append(shield)
                self.log(f"  {shield.name} が手札へ。")

        if not def_p.shields:
            self.log(f"{def_p.name} のシールドが全滅！")

    def _creature_st(self, player: Player, card: Card):
        """クリーチャーSTの即時召喚処理。人間は選択、AIは常に召喚。"""
        card.summoning_sick = True
        card.tapped = False
        if player.is_human:
            print(f"\n  [{card.name}] を今すぐ召喚しますか？ (yes: 召喚 / Enter: 手札へ): ", end="")
            ans = input().strip().lower()
            if ans in ("yes", "y"):
                player.battle_zone.append(card)
                self.log(f"  {card.name} がSTで即時召喚！")
                for eff in card.effects:
                    if eff not in _PASSIVE_EFFECTS:
                        apply_effect(eff, self, player, card)
            else:
                player.hand.append(card)
                self.log(f"  {card.name} が手札へ。")
        else:
            player.battle_zone.append(card)
            self.log(f"  [AI] {card.name} がSTで即時召喚！")
            for eff in card.effects:
                if eff not in _PASSIVE_EFFECTS:
                    apply_effect(eff, self, player, card)

    # ── Display ────────────────────────────────────────

    def _show_state(self, perspective: Player):
        o = next(p for p in self.players if p is not perspective)
        print(f"\n{'═'*55}")
        print(f"  【相手】{o.name}  デッキ:{len(o.deck)}枚  手札:{len(o.hand)}枚  マナ:{o.total_mana()}")
        print(_shields_row(o.shields))
        for line in _render_bz(o.battle_zone):
            print(line)
        print(f"  {'─'*51}")
        for line in _render_bz(perspective.battle_zone):
            print(line)
        print(_shields_row(perspective.shields))
        perspective.show_mana()
        print(f"  【自分】{perspective.name}  デッキ:{len(perspective.deck)}枚")
        print(f"{'═'*55}")

    # ── Target choosers (used by effects) ──────────────

    def choose_creature(self, from_player: Player, chooser: Player, prompt: str = "クリーチャーを選択") -> Card | None:
        pool = from_player.battle_zone
        if not pool:
            return None
        if len(pool) == 1:
            return pool[0]
        if chooser.is_human:
            print(f"\n  {prompt}:")
            for i, c in enumerate(pool):
                print(f"    {i}: {c.display()}")
            while True:
                try:
                    idx = int(input("  番号: "))
                    if 0 <= idx < len(pool):
                        return pool[idx]
                except ValueError:
                    pass
                print("  無効な番号。")
        else:
            return max(pool, key=lambda c: c.power)

    def choose_from_list(self, cards: list, chooser: Player, prompt: str = "カードを選択", **_) -> Card | None:
        if not cards:
            return None
        if len(cards) == 1:
            return cards[0]
        if chooser.is_human:
            print(f"\n  {prompt}:")
            for i, c in enumerate(cards):
                print(f"    {i}: {c.display()}")
            while True:
                try:
                    idx = int(input("  番号: "))
                    if 0 <= idx < len(cards):
                        return cards[idx]
                except ValueError:
                    pass
                print("  無効な番号。")
        else:
            import random
            return random.choice(cards)

    # ── God Link ───────────────────────────────────────

    def _try_god_link(self, p: Player):
        """メインフェーズ終了直前にゴッドリンク可能なペアを検出し、リンクを試みる。"""
        already_linked_names = {
            c.god_link_name for c in p.battle_zone
            if c.is_linked and c.god_link_name
        }
        # Find linkable pairs (same god_link_name, left+right both present, not yet linked)
        bz_gods = [c for c in p.battle_zone if c.god_link_name and not c.is_linked]
        by_name: dict = {}
        for c in bz_gods:
            if c.god_link_name in already_linked_names:
                continue
            by_name.setdefault(c.god_link_name, {})
            by_name[c.god_link_name][c.god_link_side] = c

        for link_name, sides in by_name.items():
            if "left" not in sides or "right" not in sides:
                continue
            left = sides["left"]
            right = sides["right"]
            do_link = False
            if p.is_human:
                print(f"\n  ★ ゴッドリンク可能！ [{left.name}] == [{right.name}]")
                print(f"    リンク後パワー: {left.power + right.power} / ブレイカー: {'TB' if max(left.breaker, right.breaker) >= 3 else 'DB' if max(left.breaker, right.breaker) == 2 else 'SB'}")
                ans = input("  リンクしますか？ (yes: リンク / Enter: スキップ): ").strip().lower()
                do_link = ans in ("yes", "y")
            else:
                do_link = True  # AI always links

            if do_link:
                left.is_linked = True
                left.link_partner = right
                right.is_linked = True
                right.link_partner = left
                self.log(f"ゴッドリンク！ [{left.name}] == [{right.name}] (PWR:{left.linked_power()})")
                # Draw once on link formation (was: every untap — too strong)
                if "god_link_untap_draw" in left.effects or "god_link_untap_draw" in right.effects:
                    p.draw(1)
                    self.log(f"[ゴッドリンク成立] 1枚ドロー。")
                # Atom Sol: bounce 1 opponent creature on link formation
                if "god_atom_link_bounce" in left.effects or "god_atom_link_bounce" in right.effects:
                    from effects import bounce_opponent_creature
                    bounce_opponent_creature(self, p, left)
