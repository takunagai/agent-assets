# koboyo カテゴリ早見（日本語）

71,238 点 / 111 カテゴリ。カテゴリ ID は `group/subgroup` 形式で、`search_icons` / `find_icons_for` / `list_icons` の `category` に渡す。group 名だけ（`people` 等）でも絞り込める。

## 目次

- [日本語からの逆引き](#日本語からの逆引き)
- [group 別カテゴリ一覧](#group-別カテゴリ一覧)
- [絞り込みの効かせ方](#絞り込みの効かせ方)

## 日本語からの逆引き

依頼に出てくる日本語から、まず見るべき棚を引く。翻訳語で全体検索するより先にここを見ると外さない。

| 依頼の言葉 | 見る棚 | 補足 |
|---|---|---|
| 空状態 / データがありません / 検索結果ゼロ | `scene/uistate` | 空状態・確認画面のために作られた棚。翻訳検索では絶対に辿り着かない |
| 完了画面 / 送信しました / ありがとうございました | `scene/uistate` | `confirmation-for-*` の命名で揃っている |
| マスコット / ゆるキャラ / キャラクター | `object/mascot`（8,658）`people/character` | 動物・ブロブ等の擬人化キャラは people/character 側 |
| 表情 / 感情 / 満足度 | `people/emotion` `face` | 5 段階評価は face が揃えやすい |
| 職業 / 職種 / チーム紹介 | `people/profession` | エンジニア・デザイナー等 |
| 動作 / 〜している人 | `people/action`（5,282） | 最大の人物棚 |
| ポーズ / 立ち姿 | `people/pose` `people/figure` | |
| 手 / ジェスチャー / 指差し | `object/hand` `people/gesture` | |
| ステータス / 成功・警告・エラー | `mark/status` | コールアウトやバッジ向け |
| 記号 / マーク / 汎用アイコン | `mark/icon`（6,614）`mark/symbol` | UI の小さな記号はここ |
| 塗り / ベタ / シルエット | `solid/solid` `mark/solid` | 線画でなく面で見せたいとき |
| 構成図 / アーキテクチャ / システム | `object/sysdesign` `object/tech` `object/compsci` | |
| 開発 / コード / ターミナル | `object/dev` | |
| データ / グラフ / 分析 | `object/data` `object/infographic` | |
| AI / 機械学習 | `object/ai` | |
| 画面 / ボタン / フォーム部品 | `object/interface` `people/interface` | |
| ファイル / 書類 | `object/file` `object/document` `object/content` | |
| 買い物 / 決済 / EC | `object/commerce` `object/business` | |
| 販促 / 集客 / SNS | `object/marketing` `object/social` | |
| 会社 / 職場 / オフィス | `object/workplace` `people/workplace` `people/business` | |
| 学習 / 教育 | `object/education` `people/education` | |
| 医療 / 健康 | `object/health` `people/health` | |
| 安全 / 防災 / 事故 | `object/safety` `object/incident` | |
| セキュリティ / 認証 | `object/security` | |
| 法務 / 契約 | `object/legal` | |
| 物流 / 配送 | `object/logistics` | |
| 食べ物 / 飲み物 | `object/food`（1,287） | |
| 動物 | `object/animal`（1,141） | 擬人化キャラは people/character |
| 自然 / 天気 / 環境 | `object/nature`（1,475）`object/environment` | |
| 場所 / 建物 / 地図 | `object/place` | |
| 乗り物 | `object/vehicle` `object/rail` `object/aviation` `object/maritime` | |
| 時間 / カレンダー | `object/time` | |
| 道具 / 工具 | `object/tool` `object/workshop` | |
| 文房具 | `object/stationery` | |
| 遊び / ゆるい絵 | `object/playful`（4,727） | トーンを軽くしたいとき |
| 抽象概念 / 比喩 | `object/concept`（871） | 「気づき」「成長」等の抽象語はここが当たりやすい |
| 場面 / 情景イラスト | `scene/vignette` | 記事の挿絵向け |

## group 別カテゴリ一覧

### face — 719

`face`(719) 顔・表情単体

### mark — 7,088

汎用の記号・マーク類。UI の小さなアイコンはまずここ。

`icon`(6,614) 汎用アイコン ｜ `status`(182) 状態表示 ｜ `texture`(95) 模様・質感 ｜ `symbol`(85) シンボル ｜ `mark`(45) マーク ｜ `math`(44) 数式記号 ｜ `solid`(23) 塗り記号

### object — 39,962

最大の group。モノ・概念・場面を広く覆う。

**キャラ・遊び**: `mascot`(8,658) マスコット ｜ `playful`(4,727) 遊び・ゆるい絵 ｜ `toy`(177) おもちゃ ｜ `fantasy`(192) ファンタジー

**自然・生き物・食**: `nature`(1,475) 自然 ｜ `food`(1,287) 食べ物 ｜ `animal`(1,141) 動物 ｜ `environment`(188) 環境 ｜ `agriculture`(180) 農業

**技術・開発**: `tech`(1,011) テクノロジー ｜ `dev`(963) 開発 ｜ `sysdesign`(481) システム構成 ｜ `compsci`(376) 情報科学 ｜ `data`(566) データ ｜ `ai`(194) AI ｜ `telecom`(184) 通信 ｜ `communication`(190) コミュニケーション

**人の動作・身体**: `hand`(984) 手

**生活・住まい**: `home`(733) 家庭 ｜ `everyday`(313) 日用品 ｜ `family`(180) 家族 ｜ `hospitality`(187) もてなし ｜ `property`(187) 不動産

**仕事・商い**: `workplace`(697) 職場 ｜ `business`(392) ビジネス ｜ `commerce`(271) 商取引 ｜ `marketing`(288) マーケティング ｜ `industry`(310) 産業 ｜ `logistics`(186) 物流 ｜ `legal`(187) 法務 ｜ `security`(191) セキュリティ

**文化・娯楽**: `culture`(470) 文化 ｜ `entertainment`(415) 娯楽 ｜ `media`(550) メディア ｜ `sport`(685) スポーツ ｜ `gaming`(233) ゲーム ｜ `hobby`(201) 趣味 ｜ `history`(194) 歴史 ｜ `military`(185) 軍事

**場所・移動**: `place`(526) 場所 ｜ `vehicle`(455) 乗り物 ｜ `travel`(200) 旅行 ｜ `rail`(191) 鉄道 ｜ `aviation`(182) 航空 ｜ `maritime`(175) 海事 ｜ `civic`(193) 公共

**書類・情報**: `file`(288) ファイル ｜ `content`(241) コンテンツ ｜ `document`(176) 文書 ｜ `infographic`(204) 図表 ｜ `print`(188) 印刷 ｜ `stationery`(203) 文房具

**UI・機能**: `interface`(310) 画面部品 ｜ `feature`(285) 機能 ｜ `iso`(240) ISO 記号 ｜ `mark`(190) マーク ｜ `symbol`(242) シンボル ｜ `math`(189) 数式

**学び・健康・安全**: `education`(243) 教育 ｜ `science`(468) 科学 ｜ `health`(252) 健康 ｜ `safety`(310) 安全 ｜ `incident`(242) 事故・障害

**作る**: `tool`(524) 道具 ｜ `workshop`(244) 工房 ｜ `craft`(195) 手芸 ｜ `beauty`(215) 美容 ｜ `fashion`(427) ファッション ｜ `collage`(192) コラージュ

**その他**: `concept`(871) 抽象概念 ｜ `misc`(426) 雑多 ｜ `social`(239) SNS ｜ `event`(206) イベント ｜ `time`(181) 時間 ｜ `plan`(20) 図面

### people — 20,545

人物表現が厚いのが koboyo の特徴。動作・感情・職業で細かく割れている。

`action`(5,282) 動作 ｜ `person`(2,248) 人物 ｜ `emotion`(1,486) 感情 ｜ `character`(1,470) キャラクター ｜ `profession`(1,086) 職業 ｜ `interface`(751) 画面操作 ｜ `workplace`(746) 職場 ｜ `tech`(651) 技術 ｜ `creative`(604) 創作 ｜ `health`(552) 健康 ｜ `gesture`(534) ジェスチャー ｜ `education`(457) 教育 ｜ `event`(431) イベント ｜ `pose`(427) ポーズ ｜ `present`(410) 発表 ｜ `business`(408) ビジネス ｜ `outdoor`(408) 屋外 ｜ `sport`(408) スポーツ ｜ `group`(401) 集団 ｜ `misc`(387) 雑多 ｜ `home`(365) 家庭 ｜ `vehicle`(361) 乗り物 ｜ `famous`(240) 著名人 ｜ `figure`(240) 人影 ｜ `culture`(192) 文化

### scene — 1,075

`uistate`(739) UI 状態（空状態・完了・確認画面） ｜ `vignette`(336) 情景・挿絵

### solid — 1,849

`solid`(1,849) 塗り・シルエット表現

## 絞り込みの効かせ方

- **候補が多すぎるとき**: group だけで絞る（`category: "people"`）。それでも多ければ subgroup まで指定する。
- **候補が出ないとき**: category を外して全体検索に戻す。カテゴリの当てが外れているほうが多い。
- **画風を揃えたいとき**: 同じ category、さらに同じ命名パターン（`confirmation-for-*`、`*-character-working-laptop` 等）から選ぶ。手描きなので画風の混在は目立つ。
- **棚を眺めたいとき**: `list_icons` に category を渡す。`order: "generality"`（既定）でその棚の代表格が先に出る。`order: "random"` は発想を広げたいとき。
