# CI/CD 統合ガイド（GitHub Actions / pre-commit）

`SKILL.md` から分離。CI に組み込むときに Read し、雛形をコピーして使う。


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
