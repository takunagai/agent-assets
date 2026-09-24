#!/usr/bin/env python3
"""koboyo アイコン候補のコンタクトシート HTML を生成する。

slug を渡すと koboyo.com から SVG を取得し、1 枚の自己完結 HTML に並べる。
ライト / ダーク切替、実寸比の保持、番号付きカードで「番号で選ぶ」運用ができる。

使い方:
    contact_sheet.py --out /path/sheet.html search settings home
    contact_sheet.py --out /path/sheet.html --title "空状態の候補" \
        person-wishlist:カート空 confirmation-for-inbox:受信箱ゼロ
    contact_sheet.py --out /path/sheet.html --slugs-file slugs.txt

slug は "slug" または "slug:日本語ラベル" の形式。ラベルは検索時の概念名を残すために使う。
標準ライブラリのみ。依存パッケージなし。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SVG_URL = "https://koboyo.com/icons/svg/{slug}.svg"
PAGE_URL = "https://koboyo.com/icons/{slug}"
TIMEOUT_SECONDS = 15
MAX_WORKERS = 8
VIEWBOX_PATTERN = re.compile(r'viewBox\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


def parse_entry(raw: str) -> tuple[str, str]:
    """"slug" または "slug:ラベル" を (slug, label) に割る。"""
    slug, _, label = raw.partition(":")
    return slug.strip(), label.strip()


def fetch_svg(slug: str) -> tuple[str, str | None, str | None]:
    """(slug, svg_markup, error) を返す。"""
    url = SVG_URL.format(slug=slug)
    request = urllib.request.Request(url, headers={"User-Agent": "koboyo-icon-jp/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return slug, response.read().decode("utf-8"), None
    except urllib.error.HTTPError as error:
        return slug, None, f"HTTP {error.code}"
    except urllib.error.URLError as error:
        return slug, None, f"接続失敗: {error.reason}"
    except Exception as error:  # noqa: BLE001 - 1 枚の失敗で全体を落とさない
        return slug, None, str(error)


def read_viewbox(svg_markup: str) -> tuple[float, float] | None:
    match = VIEWBOX_PATTERN.search(svg_markup)
    if not match:
        return None
    parts = match.group(1).replace(",", " ").split()
    if len(parts) != 4:
        return None
    try:
        return float(parts[2]), float(parts[3])
    except ValueError:
        return None


CSS = """
:root { color-scheme: light dark; --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280; --line: #e5e7eb; --card: #fafafa; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg: #14161a; --fg: #e8eaed; --muted: #9aa0a6; --line: #2c3038; --card: #1c1f25; }
}
:root[data-theme="dark"] { --bg: #14161a; --fg: #e8eaed; --muted: #9aa0a6; --line: #2c3038; --card: #1c1f25; }
:root[data-theme="light"] { --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280; --line: #e5e7eb; --card: #fafafa; }
* { box-sizing: border-box; }
body { margin: 0; padding: 2rem 1.5rem 4rem; background: var(--bg); color: var(--fg);
  font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", "Noto Sans JP", sans-serif; }
header { display: flex; flex-wrap: wrap; gap: 1rem; align-items: baseline;
  justify-content: space-between; max-width: 1100px; margin: 0 auto 1.75rem; }
h1 { font-size: 1.25rem; margin: 0; font-weight: bold; }
.meta { color: var(--muted); font-size: 0.8rem; }
button { font: inherit; font-size: 0.8rem; padding: 0.4rem 0.9rem; cursor: pointer;
  border: 1px solid var(--line); border-radius: 999px; background: var(--card); color: var(--fg); }
.grid { display: grid; gap: 1rem; max-width: 1100px; margin: 0 auto;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
.card { border: 1px solid var(--line); border-radius: 12px; background: var(--card);
  padding: 1rem 0.9rem; display: flex; flex-direction: column; gap: 0.6rem; }
.stage { height: 108px; display: flex; align-items: center; justify-content: center; }
.stage svg { height: 88px; width: auto; max-width: 100%; }
.num { font-size: 0.75rem; font-weight: bold; color: var(--muted); }
.label { font-size: 0.85rem; line-height: 1.35; word-break: break-word; }
.slug { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.72rem;
  color: var(--muted); word-break: break-all; }
.slug a { color: inherit; }
.dim { font-size: 0.7rem; color: var(--muted); }
.error { color: #dc2626; font-size: 0.78rem; }
footer { max-width: 1100px; margin: 2.5rem auto 0; color: var(--muted); font-size: 0.75rem;
  border-top: 1px solid var(--line); padding-top: 1rem; line-height: 1.7; }
"""

SCRIPT = """
const root = document.documentElement;
document.getElementById('toggle').addEventListener('click', () => {
  const current = root.getAttribute('data-theme')
    || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  root.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
});
"""


def build_html(title: str, cards: list[dict], fragment: bool = False) -> str:
    """fragment=True では doctype / html / head / body を付けない（Artifact 用）。"""
    parts: list[str] = []
    for index, card in enumerate(cards, start=1):
        slug = html.escape(card["slug"])
        page = html.escape(PAGE_URL.format(slug=card["slug"]))
        label = html.escape(card["label"]) if card["label"] else ""
        if card["error"]:
            body = f'<div class="stage"><span class="error">取得失敗 ─ {html.escape(card["error"])}</span></div>'
            dim = ""
        else:
            body = f'<div class="stage">{card["svg"]}</div>'
            size = card["size"]
            dim = f'<div class="dim">{size[0]:g} x {size[1]:g}</div>' if size else ""
        label_line = f'<div class="label">{label}</div>' if label else ""
        parts.append(
            f'<div class="card"><div class="num">{index}</div>{body}{label_line}'
            f'<div class="slug"><a href="{page}" target="_blank" rel="noopener">{slug}</a></div>{dim}</div>'
        )

    inner = f"""<header>
  <div>
    <h1>{html.escape(title)}</h1>
    <div class="meta">{len(cards)} 件 ─ 番号で選んでください</div>
  </div>
  <button id="toggle" type="button">ライト / ダーク切替</button>
</header>
<div class="grid">
{"".join(parts)}
</div>
<footer>
アイコンは単色 <code>currentColor</code>。色は親要素の <code>color</code> で変わります。<br>
手描きのため縦横比はまちまち ─ 実装時は高さか幅の片側だけ指定し、もう片方は <code>auto</code> にしてください。<br>
出典: koboyo icon library (https://koboyo.com/icons)
</footer>
<script>{SCRIPT}</script>
"""

    if fragment:
        return f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n{inner}"

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
{inner}</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="koboyo アイコン候補のコンタクトシートを生成する")
    parser.add_argument("entries", nargs="*", help='slug または "slug:日本語ラベル"')
    parser.add_argument("--out", required=True, help="出力する HTML のパス")
    parser.add_argument("--title", default="koboyo アイコン候補", help="シートの見出し")
    parser.add_argument("--slugs-file", help="1 行 1 エントリのテキストファイル")
    parser.add_argument(
        "--fragment",
        action="store_true",
        help="doctype / html / head / body を付けない断片を書き出す（Artifact 公開用）",
    )
    args = parser.parse_args()

    raw_entries = list(args.entries)
    if args.slugs_file:
        raw_entries += [
            line.strip()
            for line in Path(args.slugs_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    if not raw_entries:
        parser.error("slug を 1 つ以上渡してください")

    parsed = [parse_entry(entry) for entry in raw_entries]
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for slug, label in parsed:
        if slug and slug not in seen:
            seen.add(slug)
            ordered.append((slug, label))

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fetched = dict(
            (slug, (markup, error))
            for slug, markup, error in pool.map(lambda item: fetch_svg(item[0]), ordered)
        )

    cards = []
    failures = 0
    for slug, label in ordered:
        markup, error = fetched[slug]
        if error:
            failures += 1
        cards.append(
            {
                "slug": slug,
                "label": label,
                "svg": markup or "",
                "error": error,
                "size": read_viewbox(markup) if markup else None,
            }
        )

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_html(args.title, cards, fragment=args.fragment), encoding="utf-8")

    print(f"生成: {out_path}")
    print(f"件数: {len(cards)} 件（取得失敗 {failures} 件）")
    for index, card in enumerate(cards, start=1):
        mark = "x" if card["error"] else "-"
        print(f"  {mark} {index}. {card['slug']}{(' / ' + card['label']) if card['label'] else ''}")
    return 1 if failures == len(cards) else 0


if __name__ == "__main__":
    sys.exit(main())
