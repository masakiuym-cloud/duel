# デュエル・マスターズ Python実装 進捗記録

## 状態: フェーズ16完了 ✅

---

## 完成済みファイル一覧

| ファイル | 説明 | 状態 |
|----------|------|------|
| `gui_main.py` | GUIエントリーポイント（別ウィンドウ起動） | ✅ 完成 |
| `main.py` | ターミナル版エントリーポイント（従来通り使用可） | ✅ 完成 |
| `card.py` | Cardデータクラス（全属性・display・多文明対応） | ✅ 完成 |
| `player.py` | Playerクラス（手札・マナ・バトルゾーン管理・多文明対応） | ✅ 完成 |
| `effects.py` | エフェクトディスパッチャー（全効果実装・説明文辞書） | ✅ 完成 |
| `game.py` | Gameクラス（ターン管理・フェーズ処理・ビジュアルUI） | ✅ 完成 |
| `ai.py` | AIレベル1〜3（ランダム/ルールベース/戦略） | ✅ 完成 |
| `deck_builder.py` | JSONからデッキを読み込む（多文明フィールド対応） | ✅ 完成 |
| `data/fire_deck.json` | 火文明デッキ 40枚 | ✅ 完成 |
| `data/water_deck.json` | 水文明デッキ 40枚 | ✅ 完成 |
| `data/nature_deck.json` | 自然文明デッキ 40枚 | ✅ 完成 |
| `data/light_deck.json` | 光文明デッキ 40枚 | ✅ 完成 |
| `data/dark_deck.json` | 闇文明デッキ 40枚 | ✅ 完成 |
| `data/god_deck.json` | ゴッドリンクデッキ 40枚（光/火/水/自然） | ✅ 完成 |
| `data/shinrei_deck.json` | 神帝デッキ 40枚（5文明混合） | ✅ 完成 |
| `standalone/duel_masters.py` | 全モジュール+デッキデータを1ファイルに統合（1810行） | ✅ 完成 |

---

## 実装済みゲームルール

- ✅ 初期セットアップ（シールド5枚、手札5枚）
- ✅ ターン構造（アンタップ→ドロー→マナチャージ→メイン→アタック）
- ✅ マナ支払い（文明条件含む・多文明対応）
- ✅ 召喚酔い（召喚ターンは攻撃不可）
- ✅ クリーチャー召喚
- ✅ 呪文使用
- ✅ 進化クリーチャー（即時攻撃可能）
- ✅ ブロッカー選択
- ✅ バトル解決（パワー比較・相打ち）
- ✅ シールドブレイク（Single/Double/Triple Breaker）
- ✅ シールドトリガー（即時発動）
- ✅ 直接攻撃・勝利判定
- ✅ デッキ切れ判定

## 実装済みエフェクト

- draw_1, draw_2, draw_3
- destroy_opponent_creature
- destroy_creature_power_lte_3000
- destroy_all_creatures_power_lte_3000
- destroy_all_opponent_creatures
- destroy_all_non_light（アポカリプス・デイ）
- bounce_opponent_creature
- hand_destruction_1, hand_destruction_all（ロスト・ソウル）
- mana_add_2
- power_plus_2000_own
- summon_blocker_from_hand（ヘブンズ・ゲート）
- mana_creature_to_play（母なる大地）
- revival_creature（地獄門デス・ゲート）
- when_enter_draw_1, when_enter_bounce, when_enter_discard_1
- cant_be_blocked（ボルメテウス）
- shield_burn（ボルメテウス）
- power_scale_fire_graveyard（ボルシャック・ドラゴン）
- god_link_untap_draw（ゴッドリンク後アンタップ時ドロー）
- god_when_attack_burn（ゴッドリンク後攻撃時シールド焼却）

---

## フェーズ16で追加した変更（2026-04-29）

### UI改善: 攻撃対象選択 & 文明表示

#### 攻撃対象の選択（game.py / standalone）

**変更前:** アタックフェーズでクリーチャーを選ぶと、常に相手シールドを攻撃していた。

**変更後:** 攻撃クリーチャーを選んだ後、**相手のバトルゾーンにクリーチャーがいる場合**に攻撃対象を選べるようになった。

```
  [ボルシャック・ドラゴン（PWR:6000）] の攻撃対象:
  [S] シールドを攻撃（シールド3枚）
  [0] クリーチャーを攻撃: [ブロッカー]（光）Cost:3 PWR:3000 Blk（PWR:3000）
  [1] クリーチャーを攻撃: [アクア・ハルカス]（水）Cost:2 PWR:2000（PWR:2000）
  対象 (S=シールド / 番号=クリーチャー):
```

- 相手のバトルゾーンが空の場合はシールドを直接攻撃（メニュー表示なし）
- `S` または Enter → シールドを攻撃（既存の blocker 選択フロー）
- 番号 → 相手クリーチャーに直接バトル（`_resolve_battle` を即呼び出し）
- クリーチャー攻撃時はブロッカー選択・シールドブレイクを**スキップ**（直接バトル解決）
- ゴッドリンクのパートナー側は表示しない（`_linked_partner_ids()` でフィルタ）

**変更ファイル:**

| ファイル | 変更 |
|----------|------|
| `game.py` | `_do_attack` に `direct_target` パラメータ追加・`_human_attack` で攻撃対象選択UI追加 |
| `standalone/duel_masters.py` | 同上を反映 |

#### 文明名の日本語表示（card.py）

手札のカード名表示 (`display()`) を改善。

**変更前:** `[ボルシャック・ドラゴン] (Fire) Cost:6 PWR:6000 DoubleBreaker`

**変更後:** `[ボルシャック・ドラゴン] (火) Cost:6 PWR:6000 DB`

- `_CIV_JP` 辞書追加: `Fire→火`, `Water→水`, `Nature→自然`, `Light→光`, `Dark→闇`
- 多文明カードは `(光/水)` のように `/` で区切って表示
- `DoubleBreaker→DB`, `TripleBreaker→TB`, `Blocker→Blk` に短縮

---

## フェーズ15で追加した変更（2026-04-29）

### バグ修正（effects.py / game.py / standalone）

#### 発見・修正したバグ一覧

| # | 深刻度 | バグ内容 | 修正 |
|---|--------|---------|------|
| 1 | **重大** | destroy系エフェクトが `_send_to_graveyard` 直呼びのためゴッドリンク状態を清算しない。片方だけ破壊されると `is_linked=True` + 無効な `link_partner` が残りゲーム状態が破損 | `_destroy(player, card)` ヘルパーを新設し全destroyエフェクトをこれに統一 |
| 2 | **重大** | `destroy_creature_power_lte_3000` / `destroy_all_creatures_power_lte_3000` が `c.power`（個別値）で判定。リンク後パワーが高くても個別パワーが低ければ誤って破壊対象になる | `c.linked_power()` に変更 |
| 3 | 中 | `bounce_opponent_creature` がリンク済みゴッドをバウンスしても `is_linked`/`link_partner` が残り、パートナーが破損したリンク状態のまま | バウンス時にリンク解除処理を追加（対象のみバウンス・パートナーはBZに残りリンク解除） |
| 4 | 小 | `_try_god_link` のatomバウンスログが対象なし（空BZ）でも「バウンス成功」と表示 | 重複ログを削除（bounce関数が自前でログ出力） |

#### `_destroy` ヘルパーの仕様

```python
def _destroy(player, card):
    # カードがBZになければ何もしない（AoE時の二重破壊防止）
    if card not in player.battle_zone: return
    # ゴッドリンク中なら両方を墓地へ、リンク状態をクリア
    if card.is_linked and card.link_partner:
        ...両方破壊...
    else:
        _send_to_graveyard(player, card)
```

- AoE効果（全体破壊）でリンクペアの片方が先に処理された後、もう片方は `card not in BZ` で安全にスキップ（二重graveyard追加バグ防止）

#### 変更ファイル
| ファイル | 変更 |
|----------|------|
| `effects.py` | `_destroy` 追加・全5つのdestroy関数を修正・bounce god link対応 |
| `game.py` | atom bounce重複ログ削除 |
| `standalone/duel_masters.py` | 上記全て反映 |

---

## フェーズ14で追加した変更（2026-04-29）

### 覚醒デッキ追加（デッキ選択肢9）

#### デッキコンセプト
光/水の2文明。**覚醒呪文コンボデッキ**。
コスト4-5の覚醒呪文を使って、コスト8-9の超強力な「覚醒クリーチャー」を手札から無料召喚する。
序盤は光のブロッカーと水のドロークリーチャーでマナを伸ばし、手札に覚醒クリーチャーを貯めてから一気に降臨させる。

#### 新メカニクス: 覚醒召喚

| 仕組み | 説明 |
|--------|------|
| 覚醒クリーチャー | `race: "Awakened"` を持つコスト8-9の強力クリーチャー |
| 覚醒呪文 | `awaken_from_hand` 効果で手札の覚醒クリーチャーを1体無料でBZへ |
| 制約 | 召喚酔いあり（即攻撃不可）、登場時効果は発動しない |

#### 新カード一覧

**覚醒クリーチャー（Awakened）** ×2枚ずつ:

| カード名 | 文明 | コスト | パワー | 能力 |
|---------|------|-------|--------|------|
| 覚醒龍アウラ | 水 | 9 | 9000 | トリプルブレイカー |
| 覚醒聖霊アルファ | 光 | 8 | 8000 | DB・ブロッカー |
| 覚醒海神ネプチューン | 水 | 9 | 9000 | DB |
| 覚醒光神フェニックス | 光 | 9 | 9500 | DB・ブロックされない |

**サポートカード**:
- 光の盾兵/覚醒の守護者/覚醒の僕（光ブロッカー群）
- 水の斥候/水の探索者/覚醒の導き手（水ドロー/バウンス群）
- 覚醒の儀式（光 Cost4 `awaken_from_hand`）×4
- 大覚醒の祈り（光 Cost5 ST `awaken_from_hand`）×3
- 覚醒召喚陣（水 Cost3 ST `draw_2`）×4

#### 新エフェクト: `awaken_from_hand`

```python
def awaken_from_hand(game, user, card, **kw):
    # 手札から race == "Awakened" のクリーチャーを1体選択
    # summoning_sick=True でBZへ（登場時効果は発動しない）
```

- `_PASSIVE_EFFECTS` には含まない（呪文効果として通常発動）
- 召喚酔いあり、登場時効果なし（母なる大地・ヘブンズ・ゲートと同じ方針）

#### AI 対応（`ai.py` / `standalone`）
- Level2/3 AI: 手札に覚醒クリーチャーがあれば覚醒呪文を最優先で使用
- 優先順位: ゴッドリンク > **覚醒コンボ** > 進化 > 除去 > …

#### 変更ファイル

| ファイル | 変更 |
|----------|------|
| `data/kakusei_deck.json` | 新規作成 40枚 |
| `effects.py` | `awaken_from_hand` 追加（関数・EFFECT_MAP・EFFECT_DESC） |
| `ai.py` | 覚醒コンボ優先ロジック追加 |
| `main.py` | `EXTRA_DECKS` に9番追加 |
| `standalone/duel_masters.py` | `_KAKUSEI_DECK`・`_DECK_CHOICES`・効果・AI全て反映 |

---

## フェーズ13で追加した変更（2026-04-29）

### 神核アトムデッキ追加（デッキ選択肢8）

#### デッキコンセプト
光/闇の2文明混合。**ハンドコントロール型ゴッドリンクデッキ**。
相手の手札を削りながら守備を固め、ゴッドリンク成立と同時にバウンスで盤面リセット。

#### 新カード: ゴッドリンクペア

| カード名 | 文明 | コスト | パワー | 能力 |
|---------|------|-------|--------|------|
| 神核アトム・閃光 | 光 | Cost**6** | 6000 | DB・Blocker・登場時1ドロー（左） |
| 神核アトム・滅影 | 闇 | Cost**7** | 7500 | DB・登場時手札-1・**リンク時バウンス**（右） |

リンク後: PWR**13500** / DB / Blocker
- リンク成立時に相手クリーチャー1体を手札に戻す（新エフェクト `god_atom_link_bounce`）

#### サポートカード（40枚構成）

| カード名 | 文明 | コスト | 役割 |
|---------|------|-------|------|
| 光核の守護者 | 光 | 2 | 序盤ブロッカー ×4 |
| 核光の騎士 | 光 | 3 | 序盤ブロッカー ×4 |
| 聖核の使者 | 光 | 4 | ブロッカー+登場時ドロー ×3 |
| 核心の天使 | 光 | 5 | 中盤ブロッカー ×2 |
| 核闇の尖兵 | 闇 | 2 | 序盤ハンデス ×4 |
| 滅影の追従者 | 闇 | 3 | 序盤アタッカー ×4 |
| 核心の魔導士 | 闇 | 4 | 中盤ハンデス ×2 |
| 核光の裁き | 光 | 4 | 除去呪文 ×2 |
| 核滅の波動 | 闇 | 5 | ST+手札-1 ×4 |
| 聖核の光輝 | 光 | 5 | ST+ドロー2 ×2 |
| ロスト・ソウル | 闇 | 7 | 手札全滅 ×2 |
| ヘブンズ・ゲート | 光 | 6 | ST+ブロッカー召喚 ×1 |
| 核滅の嵐 | 闇 | 6 | 相手全体破壊 ×2 |

#### 新エフェクト: `god_atom_link_bounce`

| 項目 | 内容 |
|------|------|
| 分類 | パッシブ（summon時には発動しない） |
| 発動タイミング | `_try_god_link` でリンク成立時に1回 |
| 効果 | `bounce_opponent_creature` を呼び出し（相手クリーチャー1体を手札へ） |

#### 変更ファイル

| ファイル | 変更 |
|----------|------|
| `data/atom_deck.json` | 新規作成 40枚 |
| `effects.py` | `god_atom_link_bounce` 追加（関数・EFFECT_MAP・EFFECT_DESC） |
| `game.py` | `_PASSIVE_EFFECTS` に追加・`_try_god_link` でバウンス処理 |
| `main.py` | `EXTRA_DECKS` に8番追加 |
| `standalone/duel_masters.py` | `_ATOM_DECK`・`_DECK_CHOICES` 8番追加・上記全て反映 |

---

## フェーズ12で追加した変更（2026-04-29）

### ゴッドリンクデッキのバランス調整

**問題:** ゴッドデッキが他デッキに対して圧倒的に強すぎた。

#### 根本原因

| 問題 | 詳細 |
|------|------|
| ① 毎ターンドロー | リンク後に毎アンタップで1枚ドロー → 無限のカードアドバンテージ |
| ② DB + シールド焼却 | 2枚両方を焼却してSTを完全無効化 |
| ③ 神聖なる閃光 4枚 | コスト4・無条件破壊が4枚は除去が多すぎ |
| ④ 神・ゼン コスト5 | ブロッカーDB持ちが5マナから出せて序盤が強すぎ |

#### 修正内容

**`game.py` / `standalone/duel_masters.py`:**
- `_phase_untap`: `god_link_untap_draw` のアンタップ毎ドローを**削除**
- `_try_god_link`: ゴッドリンク成立時に**1回だけ**ドロー（リンク前後で変わらない総ドロー数でバランス維持しつつ毎ターン優位は解消）
- `_break_shield`: ゴッドリンクの焼却は**1枚のみ**に制限（`god_burn_limit = 1`）。DBで2枚目はSTが機能する。通常の `shield_burn`（ボルメテウス等）には影響なし

**`data/god_deck.json` / `standalone/_GOD_DECK`:**
- 神・ゼン: Cost **5 → 6**（リンク準備が1ターン遅くなる）
- 神聖なる閃光: **4枚 → 2枚**（除去を半減）
- 神域の見張り（光 Cost3 PWR2500 ブロッカー）を**2枚追加**（穴埋め、40枚維持）

**`effects.py` / `standalone/EFFECT_DESC`:**
- `god_link_untap_draw` の説明文を「ゴッドリンク成立時1枚ドロー」に更新
- `god_when_attack_burn` の説明文を「1枚焼却」に更新

#### 変更ファイル

| ファイル | 変更 |
|----------|------|
| `game.py` | アンタップドロー削除・リンク成立時ドロー追加・焼却1枚制限 |
| `effects.py` | 説明文更新 |
| `data/god_deck.json` | 神・ゼン Cost6・神聖なる閃光2枚・神域の見張り2枚追加 |
| `standalone/duel_masters.py` | 上記全て反映 |

---

## フェーズ11で追加した変更（2026-04-28）

### 単一ファイル版作成（`standalone/duel_masters.py`）

全モジュール（card/effects/player/game/ai/main/gui）＋全7デッキデータを1ファイルに統合。

**起動方法:**
```bash
# GUI版（推奨）
python standalone/duel_masters.py

# ターミナル版
python standalone/duel_masters.py --terminal
```

**変更点:**
- JSONファイル不要：デッキデータをPythonリストとして埋め込み
- モジュール間インポートなし：全て1ファイル内で完結
- `import main as gm; gm.main()` → `main()` を直接呼び出し
- `--terminal` 引数でターミナルモード切り替え

---

## フェーズ10で追加した変更（2026-04-28）

### ゴッドリンクシステム実装 + ゴッドデッキ・神帝デッキ追加

#### バランス設計（コスト非対称化）
全員がコスト同じだと極端に強いか弱いため、ペア内でコストを非対称に設定。
- 神・ゼン（左）: 光 Cost**5** PWR5000 → 中盤に出してブロッカーとして待機
- 神・ラ・ハール（右）: 火 Cost**7** PWR7000 → 後半に召喚してリンク完成
- リンク後: PWR12000 / DB / ブロッカー / 攻撃時シールド焼却 / アンタップ時ドロー
- 神・グレート・アクア（左）: 水 Cost**6** PWR6000 → ST持ち、ブロッカー
- 神・ガイル（右）: 自然 Cost**8** PWR8000 → マナ加速エンジン
- リンク後: PWR14000 / DB / ブロッカー

#### 変更ファイル

| ファイル | 変更内容 |
|----------|---------|
| `card.py` | `god_link_name` / `god_link_side` / `is_linked` / `link_partner` フィールド追加。`linked_power()` / `linked_breaker()` / `linked_effects()` メソッド追加 |
| `deck_builder.py` | `god_link_name` / `god_link_side` をJSONから読み込む |
| `player.py` | `_linked_partner_ids()` 追加。`attackers()` / `available_blockers()` でパートナー除外 |
| `effects.py` | `god_link_untap_draw` / `god_when_attack_burn` パッシブマーカー追加 |
| `game.py` | `_try_god_link(p)` 追加。`_god_send_to_graveyard()` 追加（リンク両方破壊）。`_render_bz` でパートナー非表示。`_card_box` でリンク表示（`+===+` ワイドボックス）。`_phase_untap` でドロー。`_do_attack` / `_break_shield` / `_resolve_battle` でリンクパワー合算対応 |
| `ai.py` | `_god_link_ready()` ヘルパー追加。レベル2/3でリンク完成カードを最優先召喚 |
| `main.py` | デッキ選択肢6（ゴッド）・7（神帝）追加。AI vs AI でも新デッキをランダム選択 |
| `data/god_deck.json` | 新規作成 40枚 |
| `data/shinrei_deck.json` | 新規作成 40枚 |

#### 神帝カード（コスト非対称バランス）

| カード名 | 文明 | コスト | パワー | 効果 | 備考 |
|---------|------|-------|--------|------|------|
| 神帝スヴァ | 光 | **5** | 5000 | DB・Blocker・登場時ドロー1 | 序盤に出せる守備役 |
| 神帝ムル | 水 | **6** | 5500 | DB・ST・ドロー2 | 中盤。STで奇襲も可能 |
| 神帝エムラ | 自然 | **6** | 6000 | DB・マナ+2 | 中盤。Cost7への橋渡し |
| 神帝ガリス | 闇 | **7** | 6500 | DB・相手手札全捨て | 後半フィニッシャー |
| 神帝アージュ | 火 | **7** | 7000 | DB・相手クリーチャー全滅 | 後半フィニッシャー |

> 全員Cost7 → 揃えやすすぎ/揃えにくすぎ問題を解消。5→6→6→7→7 のカーブで自然なゲーム展開に。
> 「光以外攻撃不可」は継続効果で実装複雑のため削除。

#### ゴッドリンクのルール実装
- メインフェーズ終了直前に `_try_god_link` が自動チェック
- 人間: Yes/No を選択。リンク後パワー・ブレイカーを事前表示
- AI: 自動リンク（最優先）
- 破壊時: 左右両方を墓地送り（`_god_send_to_graveyard`）
- リンク後パワー = 左右合算（合算でブレイカーは大きい方）

---

## フェーズ9で追加した変更（2026-04-27）

### GUI 大画面対応・バグ修正（`gui_main.py` 全面改修）

- **起動直後に最大化**: `root.state("zoomed")` により、起動時から画面いっぱいに表示（白背景）
- **入力欄が消える問題を修正**: tkinter pack の仕様上、`expand=True` のテキストエリアを先に pack すると下部要素が画面外へ押し出される。ステータスバー・入力行を `side=BOTTOM` で先に pack し、テキストエリアを最後に展開する正しい順序に変更
- **折り返しなし + 縦横スクロール**: `wrap=tk.NONE` + 縦・横スクロールバー追加。カードボックスが折り返さない
- **「ログをクリア」ボタン追加**: ヘッダー右端に配置
- **フォント定数化**: `FONT_MAIN(14pt) / FONT_BOLD / FONT_INPUT / FONT_TITLE(20pt) / FONT_LABEL / FONT_BTN / FONT_STAT`
- **マナ行を青色表示**: `"マナ:" in line` で判定し `#1565C0` で表示
- **送信ボタン**: "送信 ↵" 表示。Enter キーでも送信可

**起動方法（推奨）:**
```
python gui_main.py
```
`main.py` は内部で使われるため削除不可。直接起動不要。

---

## フェーズ8で追加した変更（2026-04-27）

### バグ修正・GUI改善

#### 変更ファイル
- `game.py`
  - `_PASSIVE_EFFECTS` 定数を追加（`cant_be_blocked` / `shield_burn` / `power_scale_fire_graveyard` / `dragon_cost_reduce`）
  - `summon_creature` / `evolve` / `_creature_st` のエフェクト発動条件を `when_enter_` プレフィックス限定 → **パッシブ以外は全てトリガー** に変更
  - これにより **悪魔神ドルバロム**（`destroy_all_opponent_creatures`）・**バロム**（`destroy_all_non_light`）・**光器ペトローバ**（`power_plus_2000_own`）が召喚時に正しく発動するようになった
- `gui_main.py`
  - `_TAG_CFG` に `"mana": {"foreground": "#1565C0"}` を追加（青）
  - `_detect_tag()` に `"マナ:" in line` 判定を追加 → マナ行を青色表示
  - テキストエリアフォント: `Consolas 11` → `Consolas 13`（少し大きめ）
  - 入力欄フォント: `Consolas 12` → `Consolas 14`
  - タグフォント: `Consolas 11/11bold` → `Consolas 13/13bold`

#### 発見したバグ
- クリーチャー召喚時のエフェクト発動が `when_enter_` プレフィックスのみを対象にしていたため、JSON に `when_enter_` なしで定義されていた召喚時効果が全て未発動だった
  - 影響カード: 悪魔神ドルバロム・バロム・光器ペトローバ
  - 修正: パッシブマーカー以外は全て召喚時に発動するよう変更

---

## フェーズ7で追加した変更（2026-04-27）

### ゲームルール改修・再戦機能追加

#### 変更ファイル
- `game.py`
  - `Game.__init__` — `_skip_first_draw` フラグを追加
  - `Game.run()` — `random.randint(0,1)` で先攻/後攻をランダム決定し、冒頭に表示
  - `Game._phase_draw()` — `_skip_first_draw` が True の場合はドローをスキップして即フラグを False に
- `ai.py`
  - `ai_attack_phase()` — レベル3の消極ロジック（不利トレードで`break`）を削除。攻撃可能な限り最強クリーチャーで常に突撃するよう変更
- `main.py`
  - `_select_decks_and_build(mode, ai_level)` 関数を追加。ゲームループ内で毎回呼び出すことで再戦ごとにデッキ選択が可能に。
  - AIレベルは最初に1度だけ選択し再戦時も維持。モード2（AI vs AI）は再戦時もデッキをランダム再抽選。

#### 実装したルール
- 先攻・後攻: ゲーム開始時に `random.randint(0,1)` でランダム決定し、START 画面で告知
- 先行ドローなし: 先攻プレイヤーのターン1のみドローフェーズをスキップ（`_skip_first_draw` フラグ）
- 再戦: ゲーム終了後「再戦しますか？」を表示。`yes/y` で再戦ヘッダー表示→デッキ選択→新ゲーム開始
- AI積極攻撃: 全レベルで攻撃可能なクリーチャーがいる限り毎ターン攻撃。レベル3は不利トレードでも攻撃を止めない

---

## フェーズ6で追加した変更（2026-04-24）

### コッコ・ルピアのドラゴンコスト軽減効果実装

#### 変更ファイル
- `card.py` — `race: str = ""` フィールドを追加
- `data/fire_deck.json` — コッコ・ルピアに `"effects": ["dragon_cost_reduce"]` 追加。ドラゴン6種（ボルシャック・ドラゴン、超竜バジュラ、ボルシャック・クロス・NEX、ボルメテウス・ホワイト・ドラゴン、ボルグレス・バーズ、メガ・マナロック・ドラゴン）に `"race": "Dragon"` 追加
- `deck_builder.py` — `race` フィールドをJSONから読み込むよう対応
- `player.py` — `effective_cost(card)` メソッドを追加、`can_pay` を `effective_cost` ベースに変更
- `game.py` — `summon_creature` / `play_spell` / `evolve` の `pay_mana` 呼び出しを `effective_cost` に変更。コスト不足表示も対応
- `effects.py` — `dragon_cost_reduce` パッシブマーカーを追加（EFFECT_MAP / EFFECT_DESC）
- `ai.py` — AIのマナチャージ判定を `effective_cost` ベースに更新

#### ルール
- コッコ・ルピアがバトルゾーンにいる間、自分のドラゴン族クリーチャーのコストが -1（最小1）
- 複数のコッコ・ルピアがいても -1 のまま（重複なし）
- AI・人間プレイヤー両方に適用

#### 不要ファイル・フォルダの整理
- `build/` フォルダを削除（PyInstaller中間ファイル）
- `__pycache__/` フォルダを削除

#### EXEの再ビルド
- `dist/DuelMasters_debug.exe`（旧）を削除
- `DuelMasters.spec` を使用して `dist/DuelMasters.exe` を新規ビルド（PyInstaller 6.19.0）
- `backup_phase4/` 内の全 `.txt` を最新コードで更新

---

## フェーズ5で追加した変更（2026-04-24）

### GUIウィンドウ化（`gui_main.py` 新規作成）
- **起動:** `python gui_main.py`（ターミナルなしで別ウィンドウが開く）
- `tkinter`（Python標準ライブラリ）使用、追加インストール不要
- **白背景・明るいテーマ**でターミナルの黒画面を解消
- ゲームロジック（game.py 等）は一切変更なし。GUIがstdout/stdinを乗っ取る方式
- テキストエリア + 入力フィールド + 送信ボタン（Enterキーでも送信可）
- 行内容でカラー自動判定（緑: ログ/橙: ST/紫: 区切り/赤: AI行/茶: 勝利）
- ゲームは別スレッドで実行。UIは常にレスポンシブ
- ステータスバーで「入力待ち」/「処理中」/「ゲーム終了」を表示

### コードバックアップ（`backup_phase4/` フォルダ）
- 全 `.py` ファイルを `_py.txt` として保存
- 全 `data/*.json` ファイルを `_json.txt` として保存
- `PROGRESS.md` も `PROGRESS_md.txt` として保存

---

## フェーズ4で追加した変更（2026-04-24）

### 1. クリーチャーSTの即時召喚（`game.py`）
- シールドトリガーのクリーチャーが公開された時、**今すぐ召喚するか手札に追加するか**を選択できるように変更
- 人間プレイヤー: `yes` で即時召喚（バトルゾーンへ）、Enter で手札へ
- AIプレイヤー: 常に即時召喚（戦略的に有利）
- 即時召喚時は `summoning_sick = True` のため攻撃不可だが、**ブロックは可能**（次の攻撃を止められる）
- `when_enter_*` エフェクトも即時発動（例: ミスト・リエスの召喚時ドロー）
- `_creature_st()` メソッドとして分離して実装

### 2. 多文明カードの追加（`data/*.json`）
- `fire_deck.json`: `ボルグレス・バーズ` を2枚追加（火/自然・進化・Cost:7・PWR:9000・DB・火クリーチャーに進化）
  - 爆竜GENJI・XXと入れ替え
- `nature_deck.json`: `大地の怒竜ゲンメイ` を2枚追加（火/自然・Cost:6・PWR:6000・登場時ドロー1）
  - バルガゲイザーと入れ替え
- `light_deck.json`: `エンペラー・アクア` を2枚追加（光/水・ブロッカー・DB・Cost:7・PWR:7000・登場時ドロー1）
  - 光の守護者を4枚→2枚に削減
- 各デッキ40枚を維持

---

## フェーズ3で追加した変更（2026-04-23）

### 5. カード効果の説明文表示（`effects.py` / `game.py`）
- `effects.py` に `EFFECT_DESC` 辞書を追加（全21エフェクトを日本語対応）
- `describe_card(card) -> str` 関数を追加（ブロッカー・ブレイカー・ST・各エフェクトを `/` 区切りで出力）
- メインフェーズとマナチャージフェーズの手札表示で、各カードの下に説明文を表示:
  ```
  [0] [ボルシャック・ドラゴン] Fire Cost:6 PWR:6000  ← 召喚可
       ダブルブレイカー / 墓地の火クリーチャー数×パワー+1000
  [1] [ロスト・ソウル] Dark Cost:7  ← 使用可
       S・トリガー / 相手の手札を全て捨てさせる
  [2] [ブレイズ・クロー] Fire Cost:1 PWR:1000  ← 召喚可
  ```
- 効果なし（バニラクリーチャー）は説明文を表示しない

---

## フェーズ2で追加した変更（2026-04-23）

### 1. 召喚UIの刷新（`game.py`）
- **旧:** `s 0`・`p 0`・`e 0 1` などコマンド+番号の2段入力
- **新:** 手札の番号をそのまま入力するだけで召喚/呪文使用/進化
- 進化は番号入力後、進化元が複数いる場合のみ追加選択プロンプト
- アタックフェーズも同様に番号入力のみで攻撃可能に
- 手札に `← 召喚可` / `← 使用可` / `← 進化可` / `(コスト不足: 必要X, 未タップY)` タグ表示

### 2. ビジュアルバトルフィールド（`game.py`）
- シールドをカードボックス形式で視覚表示: `[◆] [◆] [◆] [ ] [ ]  (3枚)`
- クリーチャーをカードボックス形式で表示（3枚横並び、長い名前は自動truncate）:
  ```
  ┌────────────────┐  ┌────────────────┐
  │バジュラ        │  │ボルシャック・ド│
  │火  C:7         │  │火  C:6         │
  │9000 DB         │  │6000            │
  │                │  │[sick]          │
  └────────────────┘  └────────────────┘
  ```
- `tap` / `sick` / `DB`（ダブルブレイカー）/ `TB`（トリプル）/ `Blk`（ブロッカー）表示
- 全角文字の表示幅を正確に計算するヘルパー関数（`_disp_w`, `_fit`）を実装

### 3. マナ表示の改善（`player.py`）
- **旧:** `F F F W W (計5, 未タップ4)` のような記号列
- **新:** `マナ: 火3/3 水2/2  (合計5, 未タップ5)` の文明別タップ状況表示

### 4. 多文明カード対応（`card.py` / `player.py` / `deck_builder.py`）
- `Card` に `civilizations: list[str]` フィールドと `all_civs` プロパティを追加
- `can_pay` / `pay_mana` / `has_civ_in_mana` がリスト対応
- JSONに `"civilizations": ["Light", "Water"]` を追加するだけで多文明カード定義可能
- `display()` が多文明カードを `Light/Water` 形式で表示

---

## 動作確認済み

- [x] 全5文明デッキ 40枚ロード
- [x] AI vs AI 完走テスト（勝者判定あり）
- [x] シールドトリガー発動
- [x] シールドブレイク→ダイレクトアタック→勝利
- [x] ビジュアルバトルフィールド表示（カードボックス・シールド行）
- [x] 番号入力のみで召喚・呪文・進化・攻撃
- [x] 手札に効果説明文を表示（メインフェーズ・マナチャージフェーズ）

---

## 次回セッションでの追加実装（フェーズ17予定）

### タスク1: 新デッキ10番目（墓地回収デッキ）

**コンセプト:** 闇/水の2文明混合。墓地のクリーチャーを使い回す**墓地利用コントロールデッキ**。
- 水のドローと除去で手札・盤面をコントロールしつつ、闇の墓地回収呪文で強力クリーチャーを繰り返し展開する
- 新エフェクト候補: `revival_from_graveyard`（墓地からクリーチャーを1体BZへ）
- 既存の `revival_creature`（地獄門デス・ゲート）との差別化: 対象をプレイヤーが選べる汎用版
- デッキ選択肢 `10` として追加（`main.py` / `standalone/_DECK_CHOICES`）

**追加ファイル:**
- `data/graveyard_deck.json` — 40枚
- `effects.py` — `revival_from_graveyard` 追加
- `standalone/duel_masters.py` — `_GRAVEYARD_DECK` 埋め込み

---

### タスク2: ネクスト進化（Cross NEX）実装

**コンセプト:** 通常進化（手札→バトルゾーンの1体の上に重ねる）とは別に、**バトルゾーンの指定クリーチャーをNEXカードの下に置く**進化形式。
- `card.py`: `evolution_type: str = ""` フィールドを追加（`""` = 通常 / `"cross"` = クロス進化）
- `game.py` の `evolve()`: `evolution_type == "cross"` なら `base` をBZから取り除かず `evo._under` に追加（クロスNEXは通常進化と重なりが異なる）
- `deck_builder.py`: `evolution_type` をJSONから読み込む
- 代表カード例: ボルシャック・クロス・NEX（火/コスト8/PWR12000/DB/火ドラゴンの上に進化）
  - 現在の `fire_deck.json` に入っているが通常進化扱い → クロス進化に修正
- `standalone/duel_masters.py` にも同じ変更を反映

**変更ファイル:**
- `card.py` — `evolution_type` フィールド追加
- `deck_builder.py` — `evolution_type` 読み込み対応
- `game.py` — `evolve()` にクロス進化パス追加
- `data/fire_deck.json` — ボルシャック・クロス・NEX を `"evolution_type": "cross"` に更新
- `standalone/duel_masters.py` — 上記全て反映

---

### 後回し
- AIの攻撃対象選択（クリーチャーへの有利トレード判断）
- スコアトラッキング（勝敗をJSONに保存）
- タップ能力（継続効果の汎用実装）
- ネットワーク対戦

---

## 起動方法

```bash
cd C:/Users/masak/OneDrive/Duel

# ★ GUI版（推奨・白背景ウィンドウ）
python gui_main.py

# ターミナル版（従来通り）
python main.py
```

モード選択:
- 1: 人間 vs AI
- 2: AI vs AI（観戦）
- 3: 人間 vs 人間

---

## 設計書との対応

設計書: `C:/Users/masak/OneDrive/Duel/設計書.docx`

| 設計書セクション | 実装状況 |
|-----------------|----------|
| 1-12. 基本ルール | ✅ 実装済み |
| 13. データ構造 | ✅ card.py/player.py/game.py |
| 14. 今後の拡張 | 一部未実装（GUI等） |
| 16. 大量カード実装 | ✅ JSON駆動で実装 |
| 17. AI対戦 | ✅ レベル1〜3実装 |
| 18. デッキ構築 | ✅ 全5文明40枚 |
| 19. アーキテクチャ | ✅ モジュール分離 |
| 20-21. 詳細カードリスト | ✅ 設計書のカードを使用 |
