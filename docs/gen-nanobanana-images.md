# gen-nanobanana-images

Google の画像生成モデル **Nano Banana** シリーズ（GA 版）— **Flash2 / Nano Banana 2**（推奨・万能型）、**Pro**（最高品質・テキスト精度最高）、**Lite / Nano Banana 2 Lite**（最速・最安・1K 専用）を使って、テキストからの画像生成・既存画像の編集・スタイルリファレンス・マルチターン反復修正を行う Claude Code スキルです。

## できること

- テキストから画像を生成（写真、イラスト、3Dレンダリング等）
- 同じプロンプトで最大10枚のバリエーションを一括生成（`-N`）
- 既存画像を AI で編集・加工（複数画像の同時編集も可能）
- リファレンス画像からスタイル・色調・構図を転写（`-r`、全モデルで最大14枚）
- マルチターンで画像を段階的に修正（flash2/pro/lite）
- 画像内にテキストを正確に描画（Pro が最高精度、日本語テキストがデフォルト。生成後の目視確認が必須）
- Google 検索に基づく正確な図解・インフォグラフィック生成（flash2/pro）
- Image Search で実在物の正確な写実表現（flash2 のみ）
- 14種類のアスペクト比（flash2 は超縦長・超横長対応）、最大4K解像度に対応
- `config.json` でデフォルト設定をカスタマイズ可能

## モデル比較

いずれも GA 版（Flash2 / Pro は 2026-05-28、Lite は 2026-06-30 リリース）:

| | Flash2（推奨） | Pro（最高品質） | Lite（最速最安） |
|---|---|---|---|
| モデル ID | `gemini-3.1-flash-image` | `gemini-3-pro-image` | `gemini-3.1-flash-lite-image` |
| 速度 | 約5〜15秒 | 約15〜60秒 | 最速（sub-2秒） |
| 解像度 | 512px / 1K / 2K / 4K | 1K / 2K / 4K | 1K のみ |
| テキスト描画 | 良好 | 最高精度 | 基本 |
| 入力画像（内訳、合計は各14枚） | 物体10 + 人物4 | 物体6 + 人物5 + スタイル参照3 | 物体14 |
| スタイルリファレンス | 対応 | 対応 | 対応 |
| マルチターン編集 | 対応 | 対応 | 対応 |
| Google 検索連携 | 対応 | 対応 | 非対応 |
| Image Search 連携 | 対応（独占機能） | 非対応 | 非対応 |
| アスペクト比 | 14種類（超縦長・超横長対応） | 10種類 | 10種類 |
| 思考レベル | minimal/high | low/high | minimal/high |
| コスト | 低い | 高い | 最低 |

**使い分け**: ほとんどのタスクには **Flash2**（デフォルト）を使用。テキスト描画の精度が最重要な場合のみ **Pro** を選択。最速・最安のドラフトや大量生成には **Lite**（1K 専用・検索連携なし）を使用。

### 料金の目安（画像1枚あたり, Standard tier, 2026-07-12 時点, 出典 https://ai.google.dev/gemini-api/docs/pricing）

| モデル | 512px | 1K | 2K | 4K |
|---|---|---|---|---|
| Lite | ─ | $0.0336 | ─ | ─ |
| Flash2 | $0.045 | $0.067 | $0.101 | $0.151 |
| Pro | ─ | $0.134 | $0.134 | $0.24 |

概算コストが **$0.5 を超える実行**（例: Pro 4K、`-N` 4 枚以上、4K のバッチ）は、実行前に「枚数 × 単価」の概算を提示して確認するのが安全です。

---

## セットアップ

### 1. API キーを取得

[Google AI Studio](https://aistudio.google.com/apikey) で Gemini API キーを発行します。

### 2. 環境変数に設定

`generate_image.py` は環境変数 `GEMINI_API_KEY`（無ければ `GOOGLE_API_KEY`）を `os.environ` から直接読み込みます。**`.env` ファイルの自動読み込みは行いません。**

**方法 A: シェルプロファイルに永続設定（推奨）**

`~/.zshrc`（bash なら `~/.bashrc`）に追記します。Claude Code の Bash ツールはユーザーのシェルプロファイルから初期化されるため、ここで `export` したキーは **Claude Code 経由のスクリプト実行にも、ターミナルからの直接実行にも継承されます**。

```bash
echo 'export GEMINI_API_KEY="YOUR_API_KEY"' >> ~/.zshrc
source ~/.zshrc   # 既存セッションに反映（新規ターミナルでは不要）
```

設定後、次が `True` を返せば反映済みです:

```bash
python3 -c "import os; print(bool(os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')))"
```

> **注**: Claude Code をシェルプロファイルを読み込まない構成（サンドボックス等）で使っている場合は、この方法が効かないことがあります。その場合は方法 B、または実行時に `GEMINI_API_KEY="..." python3 ...` と直接渡してください。

**方法 B: `.env` を手動で読み込む**

スクリプトは `.env` を自動では `source` しないため、実行前にシェルへ流し込みます:

```bash
set -a; source .env; set +a
python3 scripts/generate_image.py ...
```

### 3. 依存パッケージをインストール

```bash
pip install -U "google-genai>=2.11.0" Pillow
```

**SDK は 2.11.0 以上が必須**です。本スキルは Interactions API（`client.interactions.create`）で画像を生成しており、2.11.0 は画像＋テキストの複数入力ブロックを確実に受け付ける最初のリリースだからです。

> **注**: macOS の Homebrew Python では `pip3 install -U --break-system-packages "google-genai>=2.11.0"` のように `--break-system-packages` が必要になる場合があります。

| パッケージ | 説明 |
|-----------|------|
| `google-genai`（>=2.11.0） | Google Gemini API の公式 Python SDK。Interactions API 経由の画像生成・テキスト生成に使用 |
| `Pillow`（>=10.0.0） | Python の画像処理ライブラリ。API レスポンスから画像データを PNG ファイルとして保存する際に使用 |

### 4. スキルをインストール

**方法 A: `.skill` パッケージからインストール**

```
/install-skill /path/to/gen-nanobanana-images.skill
```

**方法 B: スキルディレクトリに直接配置**

`gen-nanobanana-images/` フォルダを Claude Code のスキルディレクトリにコピーします:

```bash
# macOS の場合
cp -r gen-nanobanana-images ~/.claude/skills/
```

配置後のパス構成:

```
~/.claude/skills/
└── gen-nanobanana-images/
    ├── SKILL.md
    ├── scripts/
    │   └── generate_image.py
    ├── references/
    │   ├── api-reference.md
    │   └── prompt-engineering.md
    └── requirements.txt
```

### 5. 動作確認

```bash
# 利用可能なモデルを確認
python3 scripts/generate_image.py --list-models
```

---

## Claude Code での使い方

このスキルをインストールすると、Claude Code に画像生成を自然言語で依頼できます。以下に様々な指示例を紹介します。

---

### 基本的な画像生成

```
赤いリンゴの写真を生成して
```

```
夕焼けの富士山の風景画を作って。16:9で。
```

```
白い背景にシンプルなロゴデザインを生成して。"カフェ東京"というテキスト入りで。
```

---

### モデルを指定して生成

```
Flash2 で 4K の風景画像を生成して。夕焼けの海辺、16:9。
```

```
Flash2 で超縦長（1:8）のバナーを生成して。竹林の小道、幻想的な雰囲気。
```

```
Flash2 で 512px のアプリアイコンを生成して。太陽をモチーフにしたフラットデザイン、明るいオレンジのグラデーション。
```

```
Flash2 で超横長（4:1）のウェブサイトヘッダーを生成して。夜のスカイライン、ネオンの反射。
```

```
Pro モデルで高解像度（4K）の画像を生成して。
近未来の東京の夜景、ネオンが雨に反射している。シネマティックな構図で。
```

```
Pro で "グランドオープン" と書かれたバナー画像を作って。
エレガントなゴールドの文字で、暗い背景に。
```

```
Lite モデルでラフスケッチを生成して。猫がソファで寝ている絵。
```

---

### アスペクト比を指定

```
Instagram 用の正方形（1:1）画像を生成して。おしゃれなカフェラテの写真。
```

```
スマホの壁紙用に 9:16 で画像を作って。桜並木の幻想的な夜景。
```

```
YouTube サムネイル用に 16:9 で生成して。
タイトル "生産性を10倍にする方法" をポップなデザインで。Pro モデルで。
```

```
ウルトラワイド（21:9）のデスクトップ壁紙を生成して。
宇宙から見た地球の壮大な景色。
```

---

### 複数バリエーションを一括生成

```
猫の水彩画イラストを 3パターン生成して。それぞれ違うポーズで。
```

```
ロゴデザインのバリエーションを5枚出して。
"東京珈琲" のテキスト入り、ミニマルなデザイン。Pro モデルで。
```

```
Lite で背景パターンを 10枚生成して。抽象的な幾何学模様、パステルカラー。
```

---

### 既存画像の編集

```
この写真 (photo.jpg) の空を夕焼けに変えて。
```

```
input.png の背景を白に変更して。Pro モデルで。
```

```
product_photo.jpg の商品の横に "50%オフ" というテキストを追加して。
Pro モデルで、テキストは赤色の太字で。
```

```
landscape.jpg の季節を冬に変えて。雪を積もらせて、木を枯れ木にして。
```

---

### 複数画像の同時編集（全モデル対応）

```
portrait.jpg と landscape.jpg を使って、ダブルエクスポージャー風に合成して。
```

```
photo1.jpg と photo2.jpg の2枚を自然に1枚のパノラマに合成して。
```

---

### スタイルリファレンス（全モデル対応）

リファレンス画像のスタイル・色調・構図を新しい画像に適用できます。**公式のスタイル参照スロットを持つのは Pro のみ**（最大3枚）で、スタイル転写は Pro が第一候補です。Flash2 と Lite にも参照画像は渡せます（全モデル共通で最大14枚）が、こちらは物体参照として扱われ、Pro のような専用のスタイル参照ではありません。

#### スタイルを参照して新規生成

```
この絵 (style.png) のタッチで、山と湖の風景画を生成して。
```

```
reference.jpg の色使いとライティングを参考に、都市のスカイラインを生成して。
```

#### 既存画像をリファレンスのスタイルで変換

```
photo.jpg をこのアート作品 (art_style.png) のスタイルで描き直して。
```

```
portrait.jpg を reference.png のアニメ風タッチに変換して。
```

#### 複数リファレンスのブレンド

```
lighting_ref.jpg のライティングと palette_ref.jpg の配色を組み合わせて、
海辺のカフェの画像を生成して。
```

#### スタイルリファレンス + バリエーション

```
style.png のタッチで花の絵を 3パターン生成して。
```

---

### マルチターン編集（段階的な修正、全モデル対応）

マルチターンの状態はサーバー側で管理されます（`previous_interaction_id` ベース）。セッションファイルは v2 形式で、各ターンの `interaction.id` を記録するだけのシンプルな構造です。旧形式（`generate_content` 世代、`history` キー方式）のセッションは継続できないため、`-c` で新規セッションを開始してください。継続はサーバー側の保持期間内のみ有効です（Paid Tier 55日 / Free Tier 1日）。また継続ターンでは、モデル・アスペクト比・解像度がセッション開始時の設定に固定されます（`-m`/`-a`/`-s` を指定しても無視されます）。

#### ステップ 1: 初回生成

```
マルチターンモードで、雪山の中のログハウスの画像を生成して。
暖かい光が窓からもれている夕方の雰囲気で。
```

#### ステップ 2: 修正を依頼

```
さっき生成したログハウスの画像を修正して。
煙突から煙を出して、ドアの前に雪だるまを追加して。
```

#### ステップ 3: さらに修正

```
同じセッションで続けて。
空にオーロラを追加して、もっと幻想的な雰囲気にして。
```

---

### Google 検索連携（事実ベースの画像生成、flash2/pro）

```
Google Search 連携で、人体の心臓の解剖図を正確に描いて。
各部位のラベル付きで、医学教科書スタイルで。
```

```
Google Search 連携で、太陽系の惑星の比較図を作って。
正確なサイズ比と距離で、教育用インフォグラフィックスタイル。
```

```
東京タワーの正確な外観をベースにした、桜に囲まれたイラストを Google Search 連携で生成して。
```

---

### Image Search 連携（実在物の写実表現、flash2 のみ）

```
Image Search 連携で、最新の iPhone の写真を生成して。デスクの上に置いた構図で。
```

```
Image Search + Google Search 連携で、最新のテスラ Model Y の外観写真を正確に生成して。
```

```
Image Search 連携で、北欧スタイルのダイニングテーブルの商品写真を生成して。白い壁の部屋、自然光。
```

---

### EC・マーケティング用途

```
白い背景に商品写真風のスニーカーの画像を生成して。
プロフェッショナルなスタジオ照明で。Pro モデル。
```

```
Pro モデルで、コーヒーパッケージのモックアップ画像を作って。
パッケージに "モーニングブレンド" と "100% アラビカ" のテキスト入り。
```

```
SNS 広告用のバナーを 16:9 で生成して。
夏のセール "サマーセール 最大70%オフ" というテキスト入り。
鮮やかなグラデーション背景。Pro モデルで。
```

```
ECサイト用の商品画像を 5バリエーション生成して。
白い背景に革製のトートバッグ、異なるアングルで。Pro モデルで。
```

```
Flash2 で SNS 投稿用の商品紹介画像を 5パターン生成して。
コーヒー豆のパッケージを木のテーブルに置いた構図、自然光。
```

---

### クリエイティブ・アート

```
85mm レンズ、f/1.4 で撮影したようなポートレート風の画像を生成して。
被写体は朝の光の中で本を読む女性。ボケ味のある背景。
```

```
スタジオジブリ風のイラストで、森の中の小さな家を描いて。
水彩画のようなタッチで、暖かい色調。
```

```
サイバーパンクスタイルの東京の路地裏を生成して。
ネオン看板、雨の反射、ローアングル。16:9 で Pro モデル 2K。
```

```
ミニマリストなフラットデザインのアイコンセットを生成して。
天気アイコン（晴れ、曇り、雨、雪）を1枚の画像に。
```

```
同じ構図でスタイル違いを比較したいので、
「夕日の灯台」を3パターン生成して。写真風、油絵風、水墨画風。
```

---

### 教育・ドキュメント用途

```
Pro モデルの Google Search 連携で、光合成のプロセスを説明する科学的な図解を生成して。
各ステップにラベルをつけて、教科書風のクリーンなスタイルで。
```

```
データベースの ER 図風のイラストを生成して。
User, Product, Order テーブルの関係を視覚的に。
```

```
プレゼン資料用のインフォグラフィックを Pro + Google Search 連携で生成して。
「2026年の AI トレンド TOP 5」。16:9 のモダンなデザイン。
```

---

### 思考レベルを指定

```
思考レベルを high にして、複雑な建築のインテリアデザインを生成して。
モダンなリビングルーム、大きな窓から自然光、ミニマリストな家具。
Pro モデル、4K で。
```

```
Flash2 で思考レベル high にして、複雑な日本庭園の俯瞰図を生成して。
枯山水、苔、石灯籠を精密に配置した構図で。
```

---

### 出力先・ファイル名を指定

```
画像を ./images フォルダに hero_banner という名前で保存して。
ヒーローバナー用の画像を 16:9 で生成。
```

```
./output に product という名前で 4バリエーション保存して。
→ product.png, product_v2.png, product_v3.png, product_v4.png が生成されます。
```

---

### ユーティリティ

```
このスキルで使えるモデルの一覧を表示して。
```

```
generate_image.py のヘルプを表示して。
```

---

## CLI 直接実行リファレンス

スクリプトを直接実行する場合のコマンド例:

```bash
# テキストから画像生成（Flash2 — デフォルト）
python3 scripts/generate_image.py \
  -p "A red apple on white background" -o ./output

# Flash2 で 4K・超縦長生成
python3 scripts/generate_image.py \
  -p "A tall lighthouse on a cliff" -a 1:8 -s 4K -o ./output

# Flash2 で 512px アイコン生成
python3 scripts/generate_image.py \
  -p "A cute app icon of a smiling sun" -s 512px -o ./output

# Pro モデルで 4K 生成
python3 scripts/generate_image.py \
  -p "A futuristic cityscape at sunset" -m pro -s 4K -a 16:9 -o ./output

# 3枚のバリエーションを一括生成
python3 scripts/generate_image.py \
  -p "A red apple on white background" -N 3 -o ./output

# 名前付きで4バリエーション → city.png, city_v2.png, city_v3.png, city_v4.png
python3 scripts/generate_image.py \
  -p "Cityscape at sunset" -n city -N 4 -o ./output

# 画像編集
python3 scripts/generate_image.py \
  -p "Make the sky sunset orange" -i photo.jpg -o ./output

# 複数画像の同時編集（全モデル対応）
python3 scripts/generate_image.py \
  -p "Blend into double exposure" -i portrait.jpg landscape.jpg -o ./output

# スタイルリファレンスで新規生成
python3 scripts/generate_image.py \
  -p "A mountain landscape" -r style.png -o ./output

# 入力画像 + スタイルリファレンス
python3 scripts/generate_image.py \
  -p "Repaint in this style" -i photo.jpg -r style.png -o ./output

# 複数リファレンスのスタイルブレンド
python3 scripts/generate_image.py \
  -p "Combine lighting and color palette" -r light.jpg palette.jpg -o ./output

# スタイルリファレンス + バリエーション
python3 scripts/generate_image.py \
  -p "Flower painting in this style" -r style.png -N 3 -o ./output

# マルチターン開始（全モデル対応）
python3 scripts/generate_image.py \
  -p "A cozy cabin in the woods" -c -o ./output

# マルチターン継続
python3 scripts/generate_image.py \
  -p "Add snow on the roof" --session ./output/session_xxx.json -o ./output

# Google 検索連携（flash2/pro）
python3 scripts/generate_image.py \
  -p "Accurate diagram of human heart" -g -o ./output

# Image Search 連携（flash2 のみ）
python3 scripts/generate_image.py \
  -p "Latest iPhone model photo" --image-search -o ./output

# Image Search + Google Search 同時使用（flash2 のみ）
python3 scripts/generate_image.py \
  -p "Photo of the latest Tesla model" --image-search -g -o ./output

# テキスト入り画像（日本語）
python3 scripts/generate_image.py \
  -p 'A sign reading "ようこそ" in bold letters' -m pro -o ./output

# Lite モデルで最速・最安のドラフト生成（1K 専用）
python3 scripts/generate_image.py \
  -p "Quick draft sketch" -m lite -o ./output

# 利用可能モデル一覧
python3 scripts/generate_image.py --list-models
```

### パラメータ一覧

| 引数 | 短縮 | デフォルト | 説明 |
|------|------|-----------|------|
| `--prompt` | `-p` | **必須** | テキストプロンプト |
| `--list-models` | | - | 利用可能モデル一覧を表示 |
| `--model` | `-m` | `flash2` | `flash2`（推奨）, `pro`, `lite` |
| `--input-image` | `-i` | なし | 編集用入力画像パス（複数指定可） |
| `--reference` | `-r` | なし | スタイル/構図リファレンス画像パス（複数指定可） |
| `--num-images` | `-N` | `1` | 生成する画像の枚数（最大10枚） |
| `--output-dir` | `-o` | `.` | 出力ディレクトリ |
| `--output-name` | `-n` | 自動 | 出力ファイル名（拡張子なし。既存ファイルは上書きせず `_2` の連番を付与） |
| `--aspect-ratio` | `-a` | `1:1` | アスペクト比 |
| `--image-size` | `-s` | なし | 解像度（flash2: 512px/1K/2K/4K, pro: 1K/2K/4K, lite: 1K のみ） |
| `--thinking-level` | `-t` | なし | 思考レベル（flash2/lite: minimal/high, pro: low/high） |
| `--google-search` | `-g` | なし | Google 検索連携（flash2/pro） |
| `--image-search` | | なし | Image Search 連携を有効化（flash2 のみ。`-g` と併用可） |
| `--chat` | `-c` | なし | マルチターン新規セッション（flash2/pro/lite） |
| `--session` | | なし | セッション JSON パス（既存セッションを継続。v2 形式のみ継続可、旧形式は `-c` で新規開始） |
| `--timeout` | | 120 | タイムアウト秒（4K は自動 420s。実際に API へ伝播） |

### アスペクト比

**全モデル共通**: `1:1` `3:2` `2:3` `3:4` `4:3` `4:5` `5:4` `9:16` `16:9` `21:9`

**flash2 のみ**: `1:4` `4:1` `1:8` `8:1`

---

## 設定ファイル（config.json）

スキルディレクトリ直下に `config.json` を作成すると、デフォルト値を変更できます。ファイルが存在しない場合はビルトインデフォルトが使われます。**CLI 引数は常に config.json より優先**されます。

### 設定可能なキー

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `model` | `"flash2"` / `"pro"` / `"lite"` | `"flash2"` | デフォルトモデル |
| `aspect_ratio` | string | `"1:1"` | デフォルトアスペクト比 |
| `output_dir` | string | `"."` | デフォルト出力ディレクトリ |
| `num_images` | int (1-10) | `1` | デフォルト生成枚数 |
| `timeout` | int | `120` | デフォルトタイムアウト秒数 |
| `thinking_level` | string / null | `null` | デフォルト思考レベル |
| `negative_constraints` | string | `""`（空文字） | **既定は付加しない**。文字列を設定した場合のみ全プロンプト末尾に付加する opt-in 方式。例: `"Avoid: low quality, blurry, deformed hands, watermark."` |

### 設定例

常に Pro モデル・16:9・出力先を固定にしたい場合:

```json
{
  "model": "pro",
  "aspect_ratio": "16:9",
  "output_dir": "./output"
}
```

毎回3枚バリエーションを生成したい場合:

```json
{
  "num_images": 3
}
```

ネガティブプロンプトを常時付加したい場合（既定は空文字＝付加しない。opt-in）:

```json
{
  "negative_constraints": "Avoid: low quality, blurry, deformed hands, watermark."
}
```

必要なキーだけ記述すれば OK です。未指定のキーはビルトインデフォルトが使われます。

---

## トラブルシューティング

| 問題 | 解決策 |
|------|--------|
| API キーエラー | `echo $GEMINI_API_KEY` で設定を確認 |
| モデルが見つからない (404) | `--list-models` でモデル ID を確認し、スクリプトの `MODEL_SPECS` を更新 |
| 画像が生成されない | プロンプトが安全フィルターに引っかかった可能性。内容を変更して再試行 |
| レート制限 (429) | 自動リトライ（最大3回）。頻発する場合は時間を空ける |
| 4K がタイムアウト | `--timeout 600` で延長（デフォルトは 4K 時自動 420s） |
| 旧形式セッションは継続できない | `history` キー方式（`generate_content` 世代）のセッションは非対応。`-c` で新規セッションを開始 |
| セッション継続時に 404 エラー | サーバー側の保持期限切れの可能性（Paid Tier 55日 / Free Tier 1日）。`-c` で新規セッションを開始 |
| パッケージ未インストール / Import error | `pip install -U "google-genai>=2.11.0" Pillow` |
| `python` が見つからない | macOS では `python3` を使用 |
| config.json が無視される | スキルディレクトリ直下（`SKILL.md` と同階層）に配置されているか確認 |

---

## ファイル構成

```
gen-nanobanana-images/
├── SKILL.md                        # スキル定義（Claude Code が読む）
├── config.json                     # デフォルト設定（任意、なくても動作可）
├── scripts/
│   └── generate_image.py           # メイン CLI スクリプト
├── references/
│   ├── api-reference.md            # API 仕様・エラーコード詳細
│   └── prompt-engineering.md       # プロンプト最適化ガイド
└── requirements.txt                # Python 依存パッケージ
```

