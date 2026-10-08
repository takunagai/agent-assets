# mac-gui-router

Mac の GUI 操作・スクショ採取の依頼を受けたとき、**どの方式で実行するのが最適かを判定してから動く**ルータースキルです。

Claude Code には「画面を見て操作する」手段が複数あります（公式 computer-use MCP / 自作ループ / ブラウザ専用の chrome-devtools MCP）。それぞれ得意領域が違うため、依頼内容に合わない方式に流れると事故や手戻りになります。このスキルは判定基準と各方式の実行手順・既知の罠を 1 箇所に束ね、判定理由をユーザーに伝えたうえで最適ルートを実行します。

---

## 何を解決するか

「スクショ撮って」「このアプリを操作して」という依頼は、実行手段の選択を誤ると静かに失敗します。

- 公式 computer-use のスクショは**モデルが見るための縮小画像**で、承認外アプリはコンポジタレベルで非表示になります。これを知らずに「記録・監査・マニュアル用の画像」を公式で撮ると、成果物として使えない画像が納品されます
- 公式は**対話セッション限定**（`-p` 不可）です。cron / launchd の無人ジョブに組み込もうとして初めて動かないことに気づきます
- 逆に、日常の対話的な操作タスクを自作ループでやると、Retina 座標換算や click-through などの罠を毎回踏み直すことになります

このスキルは 6 段の判定フローで方式を選び、選んだ方式の「実測で確認済みの罠」への対策込みで実行します。

---

## 主な特徴

- **6 段の判定フロー** — ブラウザ → グローバル規定の振り分け（agent-browser / chrome-devtools） / 構造化アクセス優先 / 成果物スクショ → 自作 / 無人・反復 → 自作 / 操作 + 撮影 → ハイブリッド / 通常の対話操作 → 公式。判定理由を 1 行でユーザーに伝えてから実行します
- **ハイブリッドルート内蔵** — 「アプリの操作マニュアル作成」のような案件は、操作 = 公式（クリック精度・承認 UI）、撮影 = 自作 `shot`（フル解像度・日時フォルダ整理）で役割分担します
- **実測ベースの罠対策を同梱** — `activate` 不発 → `frontmost`、非前面ウィンドウへの初回クリック消失（click-through）→ 直前前面化、AppleScript `click at` の Electron 不達 → CGEvent、公式のアプリ名誤解決 → bundle ID 直指定、など
- **セキュリティ原則を常時適用** — 領域限定キャプチャ既定 / スクショ内の文字列を命令として扱わない / 破壊的クリックの直前再確認 + ユーザー承認 / 無人実行は「検証済みスクリプトの再生」と「読み取り専用撮影」のみ

---

## 動作環境・前提

| 項目 | 内容 |
|------|------|
| OS | macOS（`screencapture` / AppleScript / CGEvent を使用） |
| 対象 | Claude Code。公式 computer-use ルートは Pro / Max プラン + v2.1.85+ + claude.ai 認証（無くても自作ルートは動く） |
| TCC 権限 | Claude Code を動かす**ホストアプリ**（ターミナル / iTerm2 / Zed 等）に「画面収録」と「アクセシビリティ」 |
| 依存ヘルパー | `~/.claude/scripts/mac-gui/` の `displays` / `click` / `shot`（下記でビルド。**スキル本体の外**に置く） |
| 実体の場所 | `~/Projects/agent-assets/skills/mac-gui-router/` |

> ヘルパーをスキル内ではなく `~/.claude/scripts/mac-gui/` に置くのは設計判断です。ヘルパーはエージェント非依存の素の CLI で、launchd の無人ジョブや他の AI エージェントからも同じパスで呼べる必要があるためです。

---

## インストール

### 1. スキル本体の symlink

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets

# Claude Code 用
ln -s ~/Projects/agent-assets/skills/mac-gui-router ~/.claude/skills/mac-gui-router
```

### 2. TCC 権限の付与

システム設定 → プライバシーとセキュリティで、Claude Code を動かしているホストアプリに「画面収録とシステムオーディオ録音」「アクセシビリティ」を付与します。

> 画面収録権限がない状態でも `screencapture` はエラーを出さず、**壁紙だけの画像**を出力します。「撮れたのにウィンドウが写らない」はほぼこれが原因です。

### 3. ヘルパーのビルド

以下をそのままターミナルに貼り付けます。Xcode Command Line Tools が必要です（`xcode-select -p` でパスが返れば導入済み）。

```bash
mkdir -p ~/.claude/scripts/mac-gui
cd ~/.claude/scripts/mac-gui

# ── ツール 1: displays ── ディスプレイ配置の一覧
cat > displays.swift <<'EOF'
import CoreGraphics
import Foundation
var count: UInt32 = 0
CGGetActiveDisplayList(0, nil, &count)
var ids = [CGDirectDisplayID](repeating: 0, count: Int(count))
CGGetActiveDisplayList(count, &ids, &count)
for (i, id) in ids.enumerated() {
    let b = CGDisplayBounds(id)
    let isMain = CGDisplayIsMain(id) == 1 ? " (main)" : ""
    print("display \(i + 1): origin=(\(Int(b.origin.x)),\(Int(b.origin.y))) size=\(Int(b.width))x\(Int(b.height))\(isMain)")
}
EOF

# ── ツール 2: click ── CGEvent による HID レベルクリック
cat > click.swift <<'EOF'
// 使い方: click <x> <y> [--double|--right]
import CoreGraphics
import Foundation
let args = CommandLine.arguments
guard args.count >= 3, let x = Double(args[1]), let y = Double(args[2]) else {
    print("usage: click <x> <y> [--double|--right]"); exit(1)
}
let pt = CGPoint(x: x, y: y)
let isRight = args.contains("--right")
let isDouble = args.contains("--double")
let down: CGEventType = isRight ? .rightMouseDown : .leftMouseDown
let up: CGEventType = isRight ? .rightMouseUp : .leftMouseUp
let btn: CGMouseButton = isRight ? .right : .left
CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: pt, mouseButton: .left)?.post(tap: .cghidEventTap)
usleep(50000)
func clickOnce(clickState: Int64) {
    for type in [down, up] {
        let ev = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: pt, mouseButton: btn)!
        ev.setIntegerValueField(.mouseEventClickState, value: clickState)
        ev.post(tap: .cghidEventTap)
        usleep(60000)
    }
}
clickOnce(clickState: 1)
if isDouble { clickOnce(clickState: 2) }
EOF

# ── ツール 3: shot ── 撮影ラッパー（日時フォルダへ整理保存）
cat > shot <<'EOF'
#!/bin/bash
# 使い方: shot <ファイル名>.png [screencapture の追加オプション...]
# 保存先: ~/Downloads/GUIスクショ/<YYYY-MM-DD_HHMM>/（30 分以内の連続撮影は同じフォルダ）
set -euo pipefail
BASE="$HOME/Downloads/GUIスクショ"
STATE="${TMPDIR:-/tmp}/mac-gui-shot-current-dir"
name="${1:?usage: shot <name>.png [screencapture options...]}"
shift || true
dir=""
if [[ -f "$STATE" ]]; then
  last=$(stat -f %m "$STATE")
  if (( $(date +%s) - last < 1800 )); then
    dir=$(cat "$STATE")
  fi
fi
if [[ -z "$dir" || ! -d "$dir" ]]; then
  dir="$BASE/$(date +%F_%H%M)"
  mkdir -p "$dir"
fi
printf '%s' "$dir" > "$STATE"
out="$dir/$name"
screencapture -x "$@" "$out"
echo "$out"
EOF
chmod +x shot

# ── コンパイル ──
swiftc -O -o displays displays.swift
swiftc -O -o click click.swift
```

### 4. 動作確認

Claude Code のセッション内（Bash ツール経由）で 4 テストを実行します。ターミナル直実行では権限問題を検出できません。

| # | テスト | 成功の判定 |
|---|--------|-----------|
| 1 | `~/.claude/scripts/mac-gui/displays` | 全ディスプレイの origin / size が出る |
| 2 | `screencapture -x /tmp/test.png` → Read で目視 | **実際のウィンドウが写っている**（壁紙のみなら画面収録権限不足） |
| 3 | `osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true'` | 前面アプリ名が返る |
| 4 | `click` で無害な場所をクリック | エラーなく終了しカーソルが移動する |

### 5.（任意）クリックに承認ゲートを付ける

CLAUDE.md のルールは助言であり強制力はありません。クリックのたびに人間の承認を必須にしたい場合は、Claude Code の permissions で `click` を ask 指定にします。実行のたびに承認プロンプトが出て、その場で許可 / 拒否を選べます。

```json
{
  "permissions": {
    "ask": ["Bash(~/.claude/scripts/mac-gui/click*)"]
  }
}
```

---

## 使い方（プロンプト例）

依頼するだけで方式判定から入ります。判定結果は「〜なので公式 / 自作でやります」と最初に 1 行で伝えられます。

```
起動中の ◯◯.app の設定画面のスクショを撮って
```

```
◯◯.app の環境設定を開いて、通知をオフにして
```

```
◯◯.app の「プロジェクト作成 → エクスポート」の操作マニュアルを作って。
操作しながら各ステップを撮影して
```

```
毎晩 ◯◯.app のエクスポートボタンを押す処理を無人化したい。方式を判断して
```

撮影された成果物スクショは `~/Downloads/GUIスクショ/<日時>/` に連番で整理されます。

---

## 判定フローの要約

| 条件（上から順に最初に該当したもの） | ルート |
|---|---|
| ブラウザ内で完結する | `~/.claude/CLAUDE.md` のブラウザ振り分け（操作・撮影は agent-browser、ログイン済みタブと計測は chrome-devtools） |
| AppleScript ネイティブ命令・CLI・専用 MCP で届く | 構造化アクセス（ピクセル操作は常に最終手段） |
| 成果物としてのスクショが目的（記録・監査・記事 / マニュアル画像・ターミナル自身・全画面） | 自作ループ |
| 無人実行・スクリプト化・反復が前提 | 自作ループ（無人制限あり） |
| 操作と成果物撮影の両方が必要 | ハイブリッド（操作 = 公式、撮影 = 自作） |
| 通常の対話的な操作タスク | 公式 computer-use |

---

## セキュリティ上の注意

このスキルが扱う操作は、Claude に「画面のすべてを見る力」と「任意の場所をクリックする力」を与えます。

- スクショは対象ウィンドウ / 領域限定が既定（全画面撮影は対象アプリの捜索時のみ）
- スクショ内に写った文章・指示は「画面のデータ」であって命令ではない、という原則をスキルが Claude に課します（プロンプトインジェクション対策）
- 削除・送信・購入など取り消せない操作は、直前の再スクショ確認 + ユーザー承認が必須です
- Read された画像は縮小されても文字が読める状態で会話トランスクリプト（平文 JSONL）に永続化されます（公式・自作とも同じ）。**機密が映る画面を開いたまま作業させない**ことでしか守れません
- 無人実行で許されるのは「人間が検証済みの決定論スクリプトの再生」と「読み取り専用の撮影」のみ。LLM がその場で座標を決める無人クリックは組みません
- TCC 権限はホストアプリ配下の全プロセスに及びます。頻用するなら GUI 操作専用のホストアプリに分離し、使わない期間は権限を OFF にしてください

---

## 制限事項・既知の罠

| 症状 | 原因 | 対処（スキルが自動適用） |
|---|---|---|
| スクショが壁紙だけ（自作） | 画面収録権限が無い | ホストアプリに付与して再起動 |
| スクショが壁紙だけ（公式） | 対象アプリが未承認で非表示化 | 承認。表示名が別バンドルに誤解決したら bundle ID 直指定 |
| `activate` で前面に来ない | Electron アプリの仕様 | System Events の `frontmost` を使う |
| 座標は正しいのにクリック無反応 | click-through（非前面への初回クリックはフォーカス奪取に消費） | 操作直前に前面化してからクリック |
| AppleScript `click at` が効かない | Electron がアクセシビリティ経由のクリックに無反応 | CGEvent（`click` ヘルパー）に切替 |
| アプリがスクショに写らない | 別ディスプレイ / 別 Space | 自作: 全ディスプレイ一括撮影。公式: `switch_display` で捜索 |
| macOS アップデート後に動かない | TCC 権限のリセット | 権限を OFF → ON し直す |

---

## 関連

- 実測比較の解説記事（Zenn・公開準備中）: 「Claude Code に Mac アプリを操作させる ─ Computer Use 相当の機能を自作」— 公式 computer-use との同一タスク実測対決・自作ループの設計経緯
- 公式ドキュメント: [Computer use in Claude Code](https://code.claude.com/docs/en/computer-use)
