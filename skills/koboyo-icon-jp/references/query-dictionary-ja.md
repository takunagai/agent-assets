# 日本語 → 検索語 辞書

koboyo の検索は**英語のみ**。日本語クエリは 0 件で返る（`コーヒー` → `No icons match`、`coffee` → ヒット）。ここは「日本語の依頼文から、何を検索語として投げるか」の変換規約。

## 目次

- [変換の基本則](#変換の基本則)
- [直訳が滑る語](#直訳が滑る語)
- [カタカナ語の罠](#カタカナ語の罠)
- [抽象語を絵にする](#抽象語を絵にする)
- [複合語のほぐし方](#複合語のほぐし方)

## 変換の基本則

1. **依頼文から名詞だけを抜く**。「かっこいい設定アイコンがほしい」→ `settings`。形容詞・敬語・依頼形は捨てる。
2. **1 語で投げる**。多語クエリは全語 AND で、全語一致がないと近似結果に落ちる（応答に `NOT every word is reflected` と警告が出る）。この警告が出たら一番重要な 1 語で引き直す。
3. **複数の概念は 1 語ずつに割って `find_icons_for` に配列で渡す**。`search_icons` を概念の数だけ叩かない。
4. **単数形の一般名詞にする**。`documents` より `document`、`いろんな車` より `car`。
5. **当たらないときは上位語に上げる**。`sticky note` → `note` → `paper`。逆に多すぎるときは category で絞る（`references/categories-ja.md`）。

## 直訳が滑る語

直訳しても届かない、あるいは別の棚に行ったほうが早い語。

| 日本語 | 投げる語 / 行き先 | 理由 |
|---|---|---|
| 空状態 / 該当なし | category `scene/uistate` を直接見る | "empty state" で引くより棚を眺めるほうが確実 |
| 完了画面 / 送信完了 | `confirmation` | `confirmation-for-*` の系列がある |
| 吹き出し | `speech bubble` | "balloon" は風船に行く |
| ふきだし（考え） | `thought bubble` | |
| 看板 / 案内表示 | `signpost` / `sign` | "board" は板・掲示板に散る |
| 打ち合わせ | `meeting` | "discussion" より当たる |
| 資料 | `document` / `report` | "material" は素材・原料に行く |
| 議事録 | `notes` / `minutes` | |
| 締切 | `deadline` / `calendar` | |
| 稟議 / 承認 | `approval` / `stamp` | 日本固有の稟議はない。承認印で代替 |
| 名刺 | `business card` | |
| 判子 / 印鑑 | `stamp` / `seal` | |
| 引き継ぎ | `handover` / `relay` | 相当語がなければリレーの比喩へ |
| 棚卸し | `inventory` / `checklist` | |
| 導線 / 動線 | `path` / `flow` / `arrow` | |
| 見込み客 | `lead` / `customer` | |
| 問い合わせ | `inquiry` / `contact` / `mail` | |
| 定期購読 | `subscription` | `person-subscribing` 系がある |
| 決済 | `payment` / `checkout` / `receipt` | |
| 請求書 | `invoice` / `receipt` | |
| 障害 / 不具合 | category `object/incident` | "trouble" は当たりにくい |
| 保守 / メンテ | `maintenance` / `wrench` | |
| 権限 | `permission` / `key` / `lock` | |
| 認証 | `authentication` / `fingerprint` / `shield` | |
| 在宅勤務 | `remote work` / `home office` | |
| 副業 | `side job` / `freelance` | |
| 勉強会 | `workshop` / `study group` | |
| 登壇 / 発表 | category `people/present` | |
| ふりかえり | `retrospective` / `review` / `mirror` | |
| 気づき | `idea` / `lightbulb` | |
| 手戻り | `rework` / `undo` / `loop` | |

## カタカナ語の罠

カタカナをそのままローマ字化しない。英語の実語に直す。

| カタカナ | 投げる語 | 直訳するとどうなるか |
|---|---|---|
| コンセント | `power outlet` / `plug` | "consent" は同意に行く |
| クレーム | `complaint` | "claim" は請求・主張 |
| ノートパソコン | `laptop` | "notebook" は紙のノート |
| マンション | `apartment` / `building` | "mansion" は豪邸 |
| サイン（署名） | `signature` | "sign" は看板・標識 |
| バイキング | `buffet` | "viking" は北欧の戦士 |
| ホチキス | `stapler` | 商標由来 |
| コンロ | `stove` | |
| ピアス | `earring` | |
| シール | `sticker` | "seal" は封蝋・アザラシ |
| ベビーカー | `stroller` | |
| フリー（無料） | `free` は曖昧。`gift` / `zero price` へ | |
| アポ | `appointment` | |
| リストラ | `layoff` | |
| タレント | `celebrity` | |

## 抽象語を絵にする

「成長」「信頼」のような抽象語は、そのまま英訳しても絵にならない。**比喩に置き換えてから**投げる。`object/concept`（871 点）が受け皿。

| 抽象語 | 比喩に置き換える | 投げる語の例 |
|---|---|---|
| 成長 | 芽・階段・上向きグラフ | `sprout` / `stairs` / `growth chart` |
| 効率化 | 歯車・近道・ロケット | `gear` / `shortcut` / `rocket` |
| 連携 | 握手・歯車の噛み合い・橋 | `handshake` / `bridge` / `puzzle` |
| 信頼 | 握手・盾・錨 | `handshake` / `shield` / `anchor` |
| 発想 | 電球・種・地図 | `lightbulb` / `seed` / `map` |
| 迷い | 分岐路・迷路・？マーク | `crossroads` / `maze` / `question` |
| 蓄積 | 積み重ね・貯金箱・本棚 | `stack` / `piggy bank` / `bookshelf` |
| 自動化 | ロボット・ベルトコンベア | `robot` / `conveyor` |
| 選択 | 分岐・天秤・チェック | `fork` / `scales` / `checkmark` |
| 共有 | 分け合う手・ネットワーク | `sharing` / `network` |
| 分析 | 虫めがね・グラフ | `magnifier` / `chart` |
| 保護 | 盾・傘・鍵 | `shield` / `umbrella` / `lock` |

比喩を選んだら、**なぜその絵にしたかを一言添えてユーザーに確認する**。抽象語の絵は解釈が割れるので、勝手に確定させない。

## 複合語のほぐし方

日本語の複合語はそのまま英訳すると多語 AND で落ちる。**主語に当たる 1 語**へ削る。

| 依頼 | 削り方 | 投げる語 |
|---|---|---|
| ノート PC で作業する開発者 | 主語は「開発者」 | `developer`（多ければ category `people` で絞る） |
| 買い物カゴが空の画面 | 主語は「カゴ」＋状態は棚で | `cart` ＋ category `scene/uistate` |
| 会議室の予約 | 主語は「予約」 | `booking` / `calendar` |
| 請求書の発行完了 | 主語は「請求書」 | `invoice` ＋ `confirmation` を別概念として並列に |
| 顧客サポートの電話対応 | 主語は「サポート」 | `support` / `headset` |

複数語が本当に必要なら、`find_icons_for` に**別々の概念として**渡して並べ、組み合わせで見せる。1 個のアイコンに全部を背負わせない。
