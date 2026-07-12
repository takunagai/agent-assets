#!/usr/bin/env python3
"""Nano Banana Image Generation CLI.

Generate and edit images using Google Gemini image models
(Flash2 (Nano Banana 2) / Pro (Nano Banana Pro) / Lite (Nano Banana 2 Lite)).

Supports text-to-image generation, image editing, and multi-turn refinement.
Gemini Interactions API ベースで実装している。
"""

import argparse
import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path


# ---------------------------------------------------------------------------
# モデル定義 — ModelSpec dataclass で一元管理
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelSpec:
    id: str
    thinking_levels: tuple
    aspect_ratios: tuple
    image_sizes: tuple          # 空 = imageSize 指定不可
    max_input_images: int
    supports_multi_turn: bool
    supports_google_search: bool
    supports_image_search: bool


ASPECT_RATIOS_BASE = (
    "1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
)
ASPECT_RATIOS_EXTENDED = ("1:4", "4:1", "1:8", "8:1")  # flash2 のみ

# モデルは GA 版の 3 構成（flash2 / pro / lite）。
# 旧 flash (2.5 系) と preview ID は廃止済みのため使用しない。
# 詳細は references/api-reference.md「旧モデル（廃止）」を参照。
MODEL_SPECS: dict = {
    "flash2": ModelSpec(
        id="gemini-3.1-flash-image",
        thinking_levels=("minimal", "high"),
        aspect_ratios=ASPECT_RATIOS_BASE + ASPECT_RATIOS_EXTENDED,
        image_sizes=("512px", "1K", "2K", "4K"),
        max_input_images=14,
        supports_multi_turn=True,
        supports_google_search=True,
        supports_image_search=True,
    ),
    "pro": ModelSpec(
        id="gemini-3-pro-image",
        thinking_levels=("low", "high"),
        aspect_ratios=ASPECT_RATIOS_BASE,
        image_sizes=("1K", "2K", "4K"),
        max_input_images=14,
        supports_multi_turn=True,
        supports_google_search=True,
        supports_image_search=False,
    ),
    "lite": ModelSpec(
        id="gemini-3.1-flash-lite-image",
        thinking_levels=("minimal", "high"),
        aspect_ratios=ASPECT_RATIOS_BASE,
        image_sizes=("1K",),
        max_input_images=14,
        supports_multi_turn=True,
        supports_google_search=False,
        supports_image_search=False,
    ),
}

# ヘルプ表示・argparse 用の集約値
ALL_ASPECT_RATIOS = ASPECT_RATIOS_BASE + ASPECT_RATIOS_EXTENDED
ALL_IMAGE_SIZES = ("512px", "1K", "2K", "4K")
MODEL_CHOICES = list(MODEL_SPECS.keys())

# -s の受理値を Interactions API の公式 image_size 値へマップする。
# 512px のみ公式値が "512"。他は受理値そのまま。
SIZE_MAP = {"512px": "512", "1K": "1K", "2K": "2K", "4K": "4K"}

# Negative Constraints は既定 OFF（空文字）。付加したい場合は config.json の
# "negative_constraints" キーに文字列を設定する（opt-in）。以下は設定例:
#   "negative_constraints": "Avoid: low quality, blurry, noisy, deformed hands,
#                            watermark, oversaturated colors."

MAX_FILE_SIZE_MB = 7
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2

DEFAULT_NUM_IMAGES = 1
MAX_NUM_IMAGES = 10  # Google Cloud ドキュメントの記載上限に合わせる

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}

# 返却 mime が jpeg 等で PIL 保存に失敗したとき、raw bytes を書き出す際の拡張子。
EXT_FROM_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}

# ユーザーが config.json で変更可能なデフォルト値
# negative_constraints は既定 OFF（空文字）。config.json で opt-in する。
CONFIGURABLE_DEFAULTS = {
    "model": "flash2",
    "aspect_ratio": "1:1",
    "output_dir": ".",
    "num_images": DEFAULT_NUM_IMAGES,
    "timeout": 120,
    "thinking_level": None,
    "negative_constraints": "",
}


def load_config():
    """スキルディレクトリの config.json を読み込む。存在しなければ空辞書を返す。"""
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir.parent / "config.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        valid_keys = set(CONFIGURABLE_DEFAULTS.keys())
        unknown = set(config.keys()) - valid_keys
        if unknown:
            print(
                f"Warning: config.json に不明なキーがあります（無視されます）: {', '.join(sorted(unknown))}",
                file=sys.stderr,
            )
        return {k: v for k, v in config.items() if k in valid_keys}
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: config.json の読み込みに失敗しました: {e}", file=sys.stderr)
        return {}


def parse_args(config=None):
    """CLI 引数を解析する。config で指定された値が argparse のデフォルトになる。"""
    if config is None:
        config = {}
    defaults = {**CONFIGURABLE_DEFAULTS, **config}

    parser = argparse.ArgumentParser(
        description="Generate and edit images using Nano Banana (Gemini) models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # テキストから画像生成（Flash2 — デフォルト）
  %(prog)s -p "A red apple on white background"

  # Flash2 で 4K・超縦長生成
  %(prog)s -p "A tall lighthouse on a cliff" -a 1:8 -s 4K

  # Flash2 で Image Search 連携
  %(prog)s -p "Latest iPhone model photo" --image-search

  # Flash2 でマルチターンチャット
  %(prog)s -p "A cozy cabin in the woods" -c

  # Pro モデルで高解像度生成
  %(prog)s -p "A futuristic cityscape at sunset" -m pro -s 4K -a 16:9

  # 既存画像の編集
  %(prog)s -p "Make the sky sunset orange" -i photo.jpg

  # マルチターンチャット（継続）
  %(prog)s -p "Add snow on the roof" --session session.json

  # Google Search 連携
  %(prog)s -p "Accurate diagram of human heart anatomy" -g

  # Image Search + Google Search 同時使用（flash2 のみ）
  %(prog)s -p "Photo of the latest Tesla model" -m flash2 --image-search -g

  # スタイルリファレンスで新規生成
  %(prog)s -p "A mountain landscape" -r style.png

  # 複数画像の編集
  %(prog)s -p "Blend into double exposure" -i portrait.jpg landscape.jpg

  # 同一プロンプトで3枚のバリエーションを生成
  %(prog)s -p "A red apple on white background" -N 3

  # Lite モデルで最速・最安のドラフト生成（1K 専用）
  %(prog)s -p "Quick draft sketch" -m lite
""",
    )

    parser.add_argument(
        "-p", "--prompt", default=None, help="テキストプロンプト（--list-models 以外では必須）"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="API に問い合わせて利用可能な画像生成モデル一覧を表示",
    )
    # -m は CLI 明示を検出するため sentinel(None) を既定にし、解析後に config/builtin へ解決する。
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        choices=MODEL_CHOICES,
        help=(
            f"モデル選択: flash2 (推奨・万能), pro (最高品質・テキスト精度最高), "
            f"lite (最速最安・1K専用・ドラフト/大量生成向け) (default: {defaults['model']}). "
            f"旧 flash (2.5) は廃止。ドラフト用途は lite を使用"
        ),
    )
    parser.add_argument(
        "-i", "--input-image", nargs="+", default=None,
        help="編集用入力画像パス（複数指定可: -i img1.jpg img2.jpg）",
    )
    parser.add_argument(
        "-r", "--reference", nargs="+", default=None,
        help="スタイル/構図リファレンス画像パス（複数指定可: -r style1.png style2.png）",
    )
    parser.add_argument(
        "-o", "--output-dir", default=defaults["output_dir"],
        help=f"出力ディレクトリ (default: {defaults['output_dir']})",
    )
    parser.add_argument(
        "-n", "--output-name", default=None, help="出力ファイル名（拡張子なし）"
    )
    parser.add_argument(
        "-a",
        "--aspect-ratio",
        default=None,
        help=f"アスペクト比 (default: {defaults['aspect_ratio']}, choices: {', '.join(ALL_ASPECT_RATIOS)})",
    )
    parser.add_argument(
        "-s",
        "--image-size",
        default=None,
        choices=list(ALL_IMAGE_SIZES),
        help="解像度 (flash2: 512px/1K/2K/4K, pro: 1K/2K/4K, lite: 1K のみ)",
    )
    parser.add_argument(
        "-t",
        "--thinking-level",
        default=defaults["thinking_level"],
        help="思考レベル (flash2: minimal/high, pro: low/high, lite: minimal/high)",
    )
    parser.add_argument(
        "-g",
        "--google-search",
        action="store_true",
        help="Google Search 連携を有効化（flash2/pro）",
    )
    parser.add_argument(
        "--image-search",
        action="store_true",
        help="Image Search 連携を有効化（flash2 のみ。-g と併用可）",
    )
    parser.add_argument(
        "-c", "--chat", action="store_true",
        help="マルチターンチャットモード（新規セッション開始、flash2/pro/lite）",
    )
    parser.add_argument(
        "--session", default=None, help="セッション JSON パス（既存セッションを継続）"
    )
    # -N も CLI 明示を検出するため sentinel(None) を既定にし、解析後に config/builtin へ解決する。
    parser.add_argument(
        "-N", "--num-images", type=int, default=None,
        help=f"生成する画像の枚数 (default: {defaults['num_images']}, max: {MAX_NUM_IMAGES}). 各枚ごとに個別の API 呼び出しを行います",
    )
    parser.add_argument(
        "--timeout", type=int, default=defaults["timeout"],
        help=f"タイムアウト秒数 (default: {defaults['timeout']})",
    )

    args = parser.parse_args()

    # -m / -N / -a の CLI 明示有無を記録してから、未指定なら config/builtin へ解決する。
    args.model_explicit = args.model is not None
    if args.model is None:
        args.model = defaults["model"]
    args.aspect_ratio_explicit = args.aspect_ratio is not None
    if args.aspect_ratio is None:
        args.aspect_ratio = defaults["aspect_ratio"]
    args.num_images_explicit = args.num_images is not None
    if args.num_images is None:
        args.num_images = defaults["num_images"]

    # negative_constraints は CLI 引数ではなく config.json からのみ変更可能
    args.negative_constraints = defaults["negative_constraints"]
    return args


def _validate_image_file(path_str):
    """単一画像ファイルのバリデーション。エラー時はメッセージ文字列を返す。正常は None。"""
    p = Path(path_str)
    if not p.exists():
        return f"画像ファイルが見つかりません: {path_str}"
    ext = p.suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        return f"サポートされていない画像形式です: {path_str} (対応: {supported})"
    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return f"画像ファイルが大きすぎます: {path_str} ({size_mb:.1f}MB, 上限: {MAX_FILE_SIZE_MB}MB)"
    return None


def _unique_output_path(out_path):
    """出力先に同名ファイルがあれば連番を振って回避する。

    Returns:
        tuple: (Path, renamed: bool) — renamed が True なら連番回避したことを示す。
    """
    p = Path(out_path)
    if not p.exists():
        return p, False
    stem, suffix, parent = p.stem, p.suffix, p.parent
    i = 2
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate, True
        i += 1


def _augment_prompt(prompt, has_input, has_reference, input_count=0, ref_count=0):
    """入力/リファレンス画像の存在に応じてプロンプトに注釈を付加する。"""
    if has_input and has_reference:
        prefix = (
            f"Edit the {input_count} input image(s). "
            f"Use the {ref_count} reference image(s) for style and composition guidance. "
        )
        return prefix + prompt
    if has_reference and not has_input:
        prefix = (
            f"Use the {ref_count} reference image(s) for style and composition guidance. "
        )
        return prefix + prompt
    # -i のみ or 画像なし: 注釈なし（既存動作を維持）
    return prompt


def _peek_session_model_alias(session_path):
    """セッションファイルからモデルエイリアスだけを先読みする。

    バリデーション用の best-effort。存在しない・壊れている等の異常は None を返し、
    正式なエラー報告は validate_args の存在確認と load_session に委ねる。
    """
    try:
        with open(session_path, "r") as f:
            data = json.load(f)
        alias = data.get("model_alias")
        return alias if alias in MODEL_SPECS else None
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def validate_args(args):
    """引数のバリデーション。エラー時は sys.exit(1)。"""
    # API キー確認
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print(
            "Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required.",
            file=sys.stderr,
        )
        print(
            "  Get your key at: https://aistudio.google.com/apikey", file=sys.stderr
        )
        sys.exit(1)

    # セッション継続時は、実際に使われるモデル（セッション側）の spec で検査する。
    # -m/-a/-s は generate_chat が無視するため、ここでも検査対象から外す
    # （CLI/config のモデルで検査すると、無視されるはずの指定で誤って落ちる）。
    session_alias = _peek_session_model_alias(args.session) if args.session else None
    effective_model = session_alias or args.model
    spec = MODEL_SPECS[effective_model]

    if not args.session:
        # アスペクト比
        if args.aspect_ratio not in spec.aspect_ratios:
            print(
                f"Error: Invalid aspect ratio '{args.aspect_ratio}' for {effective_model}. "
                f"Valid: {', '.join(spec.aspect_ratios)}",
                file=sys.stderr,
            )
            sys.exit(1)

        # 画像サイズ
        if args.image_size:
            if not spec.image_sizes:
                print(
                    f"Error: --image-size is not available for the {effective_model} model.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if args.image_size not in spec.image_sizes:
                print(
                    f"Error: Invalid image size '{args.image_size}' for {effective_model}. "
                    f"Valid: {', '.join(spec.image_sizes)}",
                    file=sys.stderr,
                )
                sys.exit(1)
    elif args.aspect_ratio_explicit or args.image_size:
        print(
            "Note: セッション継続では -a / -s は無視されます"
            "（ターン 1 の設定を引き継ぎます）。",
            file=sys.stderr,
        )

    # Google Search（継続時も毎ターン効くため effective_model で検査する）
    if args.google_search and not spec.supports_google_search:
        print(
            f"Error: --google-search is not available for the {effective_model} model.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Image Search
    if args.image_search and not spec.supports_image_search:
        print(
            f"Error: --image-search is not available for the {effective_model} model. "
            f"Image Search is only supported by flash2.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 思考レベルのバリデーション
    if args.thinking_level:
        if args.thinking_level not in spec.thinking_levels:
            print(
                f"Error: Invalid thinking level '{args.thinking_level}' for {effective_model}. "
                f"Valid: {', '.join(spec.thinking_levels)}",
                file=sys.stderr,
            )
            sys.exit(1)

    # 生成枚数のバリデーション
    if args.num_images < 1:
        print("Error: --num-images は1以上を指定してください。", file=sys.stderr)
        sys.exit(1)
    if args.num_images > MAX_NUM_IMAGES:
        print(
            f"Error: --num-images の上限は {MAX_NUM_IMAGES} 枚です（指定: {args.num_images}枚）。",
            file=sys.stderr,
        )
        sys.exit(1)

    # マルチターンでは -N 無効（1回のターンで1枚が原則）。
    # CLI で明示された -N 2 以上はエラー、config.json 由来の値は 1 に丸めて続行する。
    if (args.chat or args.session) and args.num_images > 1:
        if args.num_images_explicit:
            print(
                "Error: マルチターンモード (--chat/--session) では --num-images は1のみ指定可能です。",
                file=sys.stderr,
            )
            sys.exit(1)
        args.num_images = 1
        print("Note: config.json の num_images はマルチターンモードでは無視され、1 に丸められます。")

    # 入力画像・リファレンス画像のバリデーション
    all_images = []
    if args.input_image:
        for img in args.input_image:
            err = _validate_image_file(img)
            if err:
                print(f"Error: {err}", file=sys.stderr)
                sys.exit(1)
            all_images.append(img)
    if args.reference:
        for img in args.reference:
            err = _validate_image_file(img)
            if err:
                print(f"Error: {err}", file=sys.stderr)
                sys.exit(1)
            all_images.append(img)

    if all_images:
        total_count = len(all_images)
        if total_count > spec.max_input_images:
            print(
                f"Error: {effective_model} モデルの画像上限は{spec.max_input_images}枚です"
                f"（指定: {total_count}枚）。",
                file=sys.stderr,
            )
            sys.exit(1)
        # 合計サイズチェック
        total_size_mb = sum(
            Path(img).stat().st_size / (1024 * 1024) for img in all_images
        )
        if total_size_mb > MAX_FILE_SIZE_MB:
            print(
                f"Error: 画像の合計サイズが上限を超えています: {total_size_mb:.1f}MB（上限: {MAX_FILE_SIZE_MB}MB）",
                file=sys.stderr,
            )
            sys.exit(1)

    # セッションファイルの存在確認
    if args.session and not Path(args.session).exists():
        print(f"Error: Session file not found: {args.session}", file=sys.stderr)
        sys.exit(1)

    # chat と session は排他
    if args.chat and args.session:
        print(
            "Error: --chat and --session are mutually exclusive. "
            "Use --chat for new sessions, --session to continue.",
            file=sys.stderr,
        )
        sys.exit(1)

    # マルチターン対応チェック
    if (args.chat or args.session) and not spec.supports_multi_turn:
        print(
            f"Error: Multi-turn chat (--chat/--session) is not available for the {effective_model} model.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 出力ディレクトリの確認
    out_dir = Path(args.output_dir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory: {out_dir}")

    # 4K 時のタイムアウト自動調整（-s 4K を明示した経路）。
    # 継続時は -s が無視されるためここでは調整せず、generate_chat がセッションの
    # 実効解像度を見て調整する。
    if not args.session and args.image_size == "4K" and args.timeout < 420:
        args.timeout = 420
        print("Note: Timeout auto-adjusted to 420s for 4K generation.")

    return api_key


def compose_full_prompt(args):
    """プロンプト注釈 + Negative Constraints を付加した最終プロンプトを組み立てる。"""
    has_input = bool(args.input_image)
    has_reference = bool(args.reference)
    input_count = len(args.input_image) if args.input_image else 0
    ref_count = len(args.reference) if args.reference else 0

    augmented = _augment_prompt(
        args.prompt, has_input, has_reference, input_count, ref_count
    )
    if args.negative_constraints:
        return f"{augmented}\n\n{args.negative_constraints}"
    return augmented


def _image_block(path_str):
    """画像ファイルを Interactions API の image 入力ブロック（明示 base64）に変換する。"""
    p = Path(path_str)
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    mime = MIME_MAP.get(p.suffix.lower(), "image/png")
    return {"type": "image", "data": data, "mime_type": mime}


def build_input(args, full_prompt):
    """input を組み立てる。画像がなければ文字列、あれば image/text ブロックの list を返す。"""
    has_input = bool(args.input_image)
    has_reference = bool(args.reference)
    if not has_input and not has_reference:
        return full_prompt

    blocks = []
    for img_str in (args.input_image or []):
        blocks.append(_image_block(img_str))
    for ref_str in (args.reference or []):
        blocks.append(_image_block(ref_str))
    # テキストは最後
    blocks.append({"type": "text", "text": full_prompt})
    return blocks


def build_response_format(aspect_ratio, image_size):
    """response_format（画像出力設定）を組み立てる。mime_type は指定しない。"""
    response_format = {"type": "image", "aspect_ratio": aspect_ratio}
    if image_size:
        response_format["image_size"] = SIZE_MAP.get(image_size, image_size)
    return response_format


def build_tools(args):
    """検索グラウンディング用の tools を組み立てる。無効なら None。"""
    if not (args.google_search or args.image_search):
        return None
    search_types = []
    if args.google_search:
        search_types.append("web_search")
    if args.image_search:
        search_types.append("image_search")
    return [{"type": "google_search", "search_types": search_types}]


def build_generation_config(thinking_level):
    """generation_config（thinking）を組み立てる。未指定なら None。"""
    if thinking_level:
        # thinking_level は小文字のまま渡す（minimal|low|high）。
        return {"thinking_level": thinking_level}
    return None


def load_session(session_path):
    """セッション JSON を読み込み、v2 形式を検証する。破損・旧形式は exit 1。"""
    try:
        with open(session_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error: セッションファイルの読み込みに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    # 旧形式（generate_content 世代）検出
    if not isinstance(data, dict) or "history" in data or "version" not in data:
        print(
            "Error: 旧形式（generate_content 世代）のセッションは継続できません。"
            "-c で新規セッションを開始してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    # v2 構造チェック（必須キー欠落・型不一致は破損扱い）
    try:
        if data.get("version") != 2 or data.get("api") != "interactions":
            raise KeyError("version/api")
        _ = data["model_id"]
        _ = data["model_alias"]
        turns = data["turns"]
        if not isinstance(turns, list) or not turns:
            raise KeyError("turns")
        _ = turns[-1]["interaction_id"]
    except (KeyError, TypeError, IndexError) as e:
        print(f"Error: セッションファイルの形式が不正です（key: {e}）。", file=sys.stderr)
        sys.exit(1)

    return data


def save_session(session_path, session_data):
    """セッション JSON を保存する。"""
    with open(session_path, "w") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)


def _build_filename(output_name, turn_num, call_index, img_count, timestamp=None):
    """保存ファイル名を組み立てる（-n / タイムスタンプ / _v / _t / 連番）。

    timestamp は -N の全バリエーションで同一の値を共有させるため呼び出し側から渡す
    （秒をまたいでもファイル名の TS が揃う）。
    """
    variant = f"_v{call_index + 1}" if call_index > 0 else ""
    turn = f"_t{turn_num}" if turn_num > 0 else ""
    if output_name:
        base = f"{output_name}{turn}{variant}"
        return f"{base}.png" if img_count == 1 else f"{base}_{img_count}.png"
    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"nanobanana_{timestamp}{turn}{variant}_{img_count}.png"


def extract_and_save_images(
    interaction, output_dir, output_name, turn_num=0, call_index=0, timestamp=None
):
    """Interaction のレスポンスから画像を抽出して保存する。

    steps を走査して model_output の image/text を収集し、画像ゼロなら
    便利プロパティ output_image / output_text をフォールバックとして確認する。

    Returns:
        tuple: (saved_paths, text_parts)
    """
    saved_paths = []
    text_parts = []
    images = []  # (base64_data, mime_type)

    steps = getattr(interaction, "steps", None) or []
    for step in steps:
        if getattr(step, "type", None) != "model_output":
            continue
        content = getattr(step, "content", None) or []
        for item in content:
            item_type = getattr(item, "type", None)
            if item_type == "image":
                data = getattr(item, "data", None)
                if data:
                    images.append((data, getattr(item, "mime_type", None)))
            elif item_type == "text":
                text = getattr(item, "text", None)
                if text:
                    text_parts.append(text)

    # フォールバック: steps から画像が取れなければ便利プロパティを見る
    if not images:
        output_image = getattr(interaction, "output_image", None)
        if output_image is not None and getattr(output_image, "data", None):
            images.append(
                (output_image.data, getattr(output_image, "mime_type", None))
            )
    if not text_parts:
        output_text = getattr(interaction, "output_text", None)
        if output_text:
            text_parts.append(output_text)

    for idx, (data, mime_type) in enumerate(images, start=1):
        try:
            img_bytes = base64.b64decode(data)
        except (ValueError, TypeError) as e:
            print(f"Error decoding image: {e}", file=sys.stderr)
            continue

        filename = _build_filename(output_name, turn_num, call_index, idx, timestamp)
        out_path = Path(output_dir) / filename
        # 既存ファイルの黙殺上書きを防ぐ（連番で回避）
        out_path, renamed = _unique_output_path(out_path)
        if renamed:
            print(f"Note: 同名ファイルが存在するため {out_path.name} に保存します（上書き回避）。")

        # PIL で PNG 保存に統一。失敗時のみ raw bytes を返却 mime の拡張子で保存。
        try:
            from PIL import Image

            image = Image.open(BytesIO(img_bytes))
            image.save(str(out_path))
            saved_paths.append(str(out_path))
            print(f"Saved: {out_path}")
        except Exception as e:
            try:
                ext = EXT_FROM_MIME.get(mime_type, ".png")
                raw_path, _ = _unique_output_path(out_path.with_suffix(ext))
                raw_path.write_bytes(img_bytes)
                saved_paths.append(str(raw_path))
                print(f"Saved (raw): {raw_path}")
            except Exception as e2:
                print(f"Error saving image: {e2} (PIL: {e})", file=sys.stderr)

    if not images:
        print(
            "Warning: No images in response. The prompt may have been filtered "
            "by safety settings, or the model returned text only.",
            file=sys.stderr,
        )

    return saved_paths, text_parts


def api_call_with_retry(client, create_kwargs):
    """Interactions API 呼び出しをリトライ付きで実行する。

    例外分類は status_code のダックタイピングで行う（Interactions API の例外は
    google.genai.errors.APIError と別階層のため）。
      - status_code == 429 / >= 500 / None（ネットワーク・タイムアウト系）→ リトライ
      - それ以外の 4xx → 即 raise
    タイムアウトは create_kwargs["timeout"]（秒）で各リクエストへ伝播する。
    """
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            return client.interactions.create(**create_kwargs)
        except Exception as e:
            last_error = e
            status_code = getattr(e, "status_code", None)

            # リトライ不可能なエラー（429 以外の 4xx）は即 raise
            if status_code is not None and not (status_code == 429 or status_code >= 500):
                raise

            # リトライ可能（429 / 5xx / status_code なし）
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                print(
                    f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES}): {e}",
                    file=sys.stderr,
                )
                time.sleep(delay)

    raise last_error


def list_available_models(api_key):
    """API に問い合わせて利用可能な画像生成モデル一覧を表示する。"""
    from google import genai

    client = genai.Client(api_key=api_key)
    print("Querying available image generation models...\n")

    image_models = []
    for m in client.models.list():
        name = m.name if hasattr(m, "name") else str(m)
        # "image" を含む Gemini モデルを抽出
        if "image" in name.lower() and "gemini" in name.lower():
            # models/ プレフィックスを除去
            model_id = name.replace("models/", "")
            image_models.append(model_id)

    if image_models:
        print("Available image generation models:")
        for model_id in sorted(image_models):
            # 現在の設定との対応を表示
            alias = None
            for key, spec in MODEL_SPECS.items():
                if spec.id == model_id:
                    alias = key
            if alias:
                print(f"  {model_id}  (--model {alias})")
            else:
                print(f"  {model_id}")

        # 設定済みモデルが一覧にない場合は警告
        for alias, spec in MODEL_SPECS.items():
            if spec.id not in image_models:
                print(
                    f"\nWarning: Configured '{alias}' model ({spec.id}) "
                    f"is NOT in the available models list."
                )
    else:
        print("No image generation models found.")

    print("\nCurrently configured:")
    for alias, spec in MODEL_SPECS.items():
        print(f"  {alias}: {spec.id}")


def generate_single_shot(args, api_key):
    """単発生成（text-to-image / 画像編集）。N 枚指定時はループで順次生成。"""
    from google import genai

    client = genai.Client(api_key=api_key)
    model_id = MODEL_SPECS[args.model].id

    full_prompt = compose_full_prompt(args)
    input_data = build_input(args, full_prompt)
    response_format = build_response_format(args.aspect_ratio, args.image_size)
    tools = build_tools(args)
    generation_config = build_generation_config(args.thinking_level)

    all_saved_paths = []
    # -N の全バリエーションで同一のタイムスタンプを共有する（秒またぎ対策）
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i in range(args.num_images):
        if args.num_images > 1:
            print(f"\nGenerating image {i + 1}/{args.num_images} with {args.model} model ({model_id})...")
        else:
            print(f"Generating with {args.model} model ({model_id})...")

        create_kwargs = {
            "model": model_id,
            "input": input_data,
            "response_format": response_format,
            # 単発生成は interaction_id を使わないため、サーバー側保持
            # （Paid 55 日 / Free 1 日）を発生させない
            "store": False,
            "timeout": args.timeout,
        }
        if tools:
            create_kwargs["tools"] = tools
        if generation_config:
            create_kwargs["generation_config"] = generation_config

        try:
            interaction = api_call_with_retry(client, create_kwargs)
            saved_paths, text_parts = extract_and_save_images(
                interaction,
                args.output_dir,
                args.output_name,
                call_index=i,
                timestamp=run_timestamp,
            )
            all_saved_paths.extend(saved_paths)
            for text in text_parts:
                print(f"\nModel response: {text}")
        except Exception as e:
            if args.num_images > 1:
                print(f"Warning: Image {i + 1}/{args.num_images} failed: {e}", file=sys.stderr)
                continue
            raise

    if not all_saved_paths:
        sys.exit(2)

    if args.num_images > 1:
        print(f"\nTotal: {len(all_saved_paths)} images generated.")

    return all_saved_paths


def generate_chat(args, api_key):
    """マルチターンチャット（セッションファイル v2 管理、サーバー側状態を利用）。"""
    from google import genai

    client = genai.Client(api_key=api_key)

    previous_interaction_id = None

    if args.session:
        # 既存セッションを継続。モデル・出力設定はセッション側を優先する。
        session_data = load_session(args.session)
        session_path = args.session
        model_alias = session_data["model_alias"]
        model_id = session_data["model_id"]
        if args.model_explicit and args.model != model_alias:
            print(
                f"Note: セッションのモデル {model_alias} を使用します（-m {args.model} は無視）。",
                file=sys.stderr,
            )
        turn_num = len(session_data["turns"]) + 1
        previous_interaction_id = session_data["turns"][-1]["interaction_id"]
        cfg = session_data.get("config", {})
        aspect_ratio = cfg.get("aspect_ratio", args.aspect_ratio)
        image_size = cfg.get("image_size")
        print(f"Continuing session (turn {turn_num}): {args.session}")
    else:
        # 新規セッション
        model_alias = args.model
        model_id = MODEL_SPECS[args.model].id
        turn_num = 1
        aspect_ratio = args.aspect_ratio
        image_size = args.image_size
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_path = str(Path(args.output_dir) / f"session_{timestamp}.json")
        session_data = {
            "version": 2,
            "api": "interactions",
            "model_alias": model_alias,
            "model_id": model_id,
            "created": datetime.now(timezone.utc).isoformat(),
            "config": {"aspect_ratio": aspect_ratio},
            "turns": [],
        }
        if image_size:
            session_data["config"]["image_size"] = image_size
        print(f"Starting new chat session: {session_path}")

    # 継続時、実効解像度が 4K ならタイムアウトを再調整する（-s 未指定でも効かせる）。
    if image_size == "4K" and args.timeout < 420:
        args.timeout = 420
        print("Note: Timeout auto-adjusted to 420s for 4K generation.")

    full_prompt = compose_full_prompt(args)
    input_data = build_input(args, full_prompt)
    response_format = build_response_format(aspect_ratio, image_size)
    tools = build_tools(args)
    generation_config = build_generation_config(args.thinking_level)

    create_kwargs = {
        "model": model_id,
        "input": input_data,
        "response_format": response_format,
        # store は指定しない: サーバー既定 (store=true) が previous_interaction_id
        # チェーンの状態管理を担う（保持期間 Paid 55 日 / Free 1 日）
        "timeout": args.timeout,
    }
    if previous_interaction_id:
        create_kwargs["previous_interaction_id"] = previous_interaction_id
    if tools:
        create_kwargs["tools"] = tools
    if generation_config:
        create_kwargs["generation_config"] = generation_config

    print(f"Generating with {model_alias} model ({model_id})...")
    try:
        interaction = api_call_with_retry(client, create_kwargs)
    except Exception as e:
        if previous_interaction_id and getattr(e, "status_code", None) == 404:
            print(
                "Error: 前回の interaction が見つかりません。セッションの保持期限切れ"
                "（Paid Tier 55 日 / Free Tier 1 日）の可能性があります。"
                "-c で新規セッションを開始してください。",
                file=sys.stderr,
            )
            sys.exit(2)
        raise

    saved_paths, text_parts = extract_and_save_images(
        interaction, args.output_dir, args.output_name, turn_num=turn_num
    )
    for text in text_parts:
        print(f"\nModel response: {text}")

    if not saved_paths and not text_parts:
        print("Error: No output from model.", file=sys.stderr)
        sys.exit(2)

    # セッション履歴（turn）を追記
    interaction_id = getattr(interaction, "id", None)
    session_data["turns"].append({
        "turn": turn_num,
        "prompt": full_prompt,
        "interaction_id": interaction_id,
        "images": [str(Path(p).resolve()) for p in saved_paths],
        "text": "\n".join(text_parts),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    save_session(session_path, session_data)
    print(f"\nSession saved: {session_path}")
    print(f"To continue: generate_image.py -p '<next prompt>' --session {session_path}")

    return saved_paths


def main():
    """エントリポイント。"""
    config = load_config()
    args = parse_args(config)

    # Lazy import チェック
    try:
        from google import genai  # noqa: F401
    except ImportError:
        print("Error: google-genai package is not installed.", file=sys.stderr)
        print(
            '  Install with: pip install -U "google-genai>=2.11.0" Pillow',
            file=sys.stderr,
        )
        sys.exit(1)

    # --list-models は --prompt 不要で実行可能
    if args.list_models:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print(
                "Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required.",
                file=sys.stderr,
            )
            sys.exit(1)
        list_available_models(api_key)
        sys.exit(0)

    # --prompt は --list-models 以外では必須
    if not args.prompt:
        print("Error: --prompt (-p) is required.", file=sys.stderr)
        sys.exit(1)

    api_key = validate_args(args)

    try:
        if args.chat or args.session:
            generate_chat(args, api_key)
        else:
            generate_single_shot(args, api_key)
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        # 例外分類は status_code のダックタイピングで行う（部分文字列マッチは廃止）
        status_code = getattr(e, "status_code", None)
        if status_code == 429:
            print(f"Error: Rate limit exceeded. Please wait and retry.\n{e}", file=sys.stderr)
        elif status_code == 403:
            print(f"Error: Permission denied. Check your API key.\n{e}", file=sys.stderr)
        elif status_code == 404:
            print(
                f"Error: Model not found. The model ID may have changed.\n{e}\n\n"
                f"Run with --list-models to see available image generation models.",
                file=sys.stderr,
            )
        elif status_code == 400:
            print(f"Error: Bad request. Check your prompt and parameters.\n{e}", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
