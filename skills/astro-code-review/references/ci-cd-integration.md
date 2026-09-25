# CI/CD 統合ガイド（GitHub Actions / pre-commit）

`SKILL.md` から分離。CI に組み込むときに Read し、雛形をコピーして使う。

### 運用上の注記: AI エージェント環境での dev / preview の自動バックグラウンド化

コードの検出項目ではない（欠陥として報告しない）。エージェントや CI から `astro dev` / `astro preview` を動かすときの前提として知っておく。

- AI エージェント環境を検出すると、`astro dev` は **7.0.0**（#16610）から、`astro preview` は **7.2.0**（#17174）から、自動でバックグラウンド起動する。コマンドはすぐ戻り、サーバーは裏で動き続ける
- 管理コマンド: `astro dev stop` / `astro preview stop`（`status` / `logs [--follow]` もある）。使い終わったら `stop` で止める
- フォアグラウンドで動かす: dev は `ASTRO_DEV_BACKGROUND=0`、preview は `ASTRO_PREVIEW_BACKGROUND=0`（変数は別々。dev の変数は preview に効かない）
- 明示的にバックグラウンドにする: `--background` フラグ（dev / preview の両方にある）
- Windows では 7.3.4（#18029）から、エージェント検出時の既定がフォアグラウンド


### GitHub Actions での使用例

```yaml
# .github/workflows/astro-review.yml
name: Astro Code Review

on:
  pull_request:
    paths:
      - 'src/**/*.astro'

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Astro Code Review
        # Claude Code CLI または MCP を使用
        run: |
          echo "Changed .astro files:"
          git diff --name-only ${{ github.event.pull_request.base.sha }} | grep '\.astro$' || true
```

### Pre-commit フック

```bash
#!/bin/bash
# .git/hooks/pre-commit

# 変更された .astro ファイルを検出
ASTRO_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.astro$')

if [ -n "$ASTRO_FILES" ]; then
  echo "🔍 Astro files changed, consider running: /astro-code-review"
  echo "$ASTRO_FILES"
fi
```
