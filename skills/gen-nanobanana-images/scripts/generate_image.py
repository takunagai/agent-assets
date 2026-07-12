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
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional


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


def _model_union(attr):
    """全モデルの対応値を宣言順で重複除去して集約する（argparse の choices / help 用）。"""
    return tuple(
        dict.fromkeys(v for spec in MODEL_SPECS.values() for v in getattr(spec, attr))
    )


def _models_supporting(attr):
    """指定の能力を持つモデルのエイリアスをカンマ区切りで返す（エラーメッセージ用）。"""
    return ", ".join(a for a, spec in MODEL_SPECS.items() if getattr(spec, attr))


ALL_ASPECT_RATIOS = _model_union("aspect_ratios")
ALL_IMAGE_SIZES = _model_union("image_sizes")
MODEL_CHOICES = list(MODEL_SPECS)

# -s の受理値のうち、Interactions API の公式 image_size 値と異なるものだけを持つ。
# それ以外は受理値をそのまま送る（build_response_format のフォールバック）。
API_IMAGE_SIZE_OVERRIDES = {"512px": "512"}

# Negative Constraints は既定 OFF（空文字）。付加したい場合は config.json の
# "negative_constraints" キーに文字列を設定する（opt-in）。以下は設定例:
#   "negative_constraints": "Avoid: low quality, blurry, noisy, deformed hands,
#                            watermark, oversaturated colors."

MAX_FILE_SIZE_MB = 7
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2

DEFAULT_NUM_IMAGES = 1
MAX_NUM_IMAGES = 10  # Google Cloud ドキュメントの記載上限に合わせる

TIMEOUT_4K = 420  # 4K は生成に時間がかかるため、これを下回るタイムアウトは引き上げる

# 入力画像の拡張子 → mime の正本。対応拡張子・raw 保存時の拡張子はここから導出する。
MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}

SUPPORTED_IMAGE_EXTENSIONS = set(MIME_MAP)

# 返却 mime が png 以外で PIL 保存に失敗したとき、raw bytes を書き出す際の拡張子。
# MIME_MAP の逆引き（reversed で先に定義した拡張子が勝つ = image/jpeg は .jpg）。
EXT_FROM_MIME = {mime: ext for ext, mime in reversed(MIME_MAP.items())}

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


@dataclass(frozen=True)
class EffectiveParams:
    """CLI / config / セッションを解決した実効パラメータ。

    セッション継続では model / aspect_ratio / image_size をセッション側が握る
    （ターン 1 の設定を引き継ぐ仕様）。この dataclass に解決結果を畳むことで、
    バリデーションも生成もセッションの有無を意識せず実効値だけを見ればよくなる。
    """

    model_alias: str
    model_id: str
    spec: ModelSpec
    aspect_ratio: str
    image_size: Optional[str]
    timeout: int
    turn_num: int                    # 0 = 単発生成（ファイル名に _t を付けない）
    previous_interaction_id: Optional[str]
    session_path: Optional[str]
    session_data: Optional[dict]


def _fail(*lines):
    """エラーを stderr に出して exit 1 する。"""
    for line in lines:
        print(line, file=sys.stderr)
    sys.exit(1)


def _note(msg):
    """Note を stderr に出す。stdout は Saved: 等の成果物パス専用に空けておく。"""
    print(msg, file=sys.stderr)


def _status_code(e):
    """例外の HTTP status を取り出す。

    Interactions API の例外は google.genai.errors.APIError と別階層のため、
    継承ではなく status_code のダックタイピングで分類する。
    """
    return getattr(e, "status_code", None)


def _require_api_key():
    """API キーを解決する。未設定なら exit 1。"""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        _fail(
            "Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required.",
            "  Get your key at: https://aistudio.google.com/apikey",
        )
    return api_key


def _client(api_key):
    """google-genai クライアントを生成する（import は遅延させる）。"""
    from google import genai

    return genai.Client(api_key=api_key)


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
    """単一画像ファイルを検査する。

    Returns:
        tuple: (error_message | None, size_mb) — stat は 1 回で済ませ、
        合計サイズは呼び出し側がこの戻り値を積み上げる。
    """
    p = Path(path_str)
    if not p.exists():
        return f"画像ファイルが見つかりません: {path_str}", 0.0
    ext = p.suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        return f"サポートされていない画像形式です: {path_str} (対応: {supported})", 0.0
    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return (
            f"画像ファイルが大きすぎます: {path_str} ({size_mb:.1f}MB, 上限: {MAX_FILE_SIZE_MB}MB)",
            size_mb,
        )
    return None, size_mb


def validate_args(args, params):
    """実効パラメータを検査する。エラー時は exit 1。

    セッション継続時の aspect_ratio / image_size はターン 1 で検証済みの値が
    params に入っているため、単発と同じ検査をそのまま通せばよい。
    """
    spec = params.spec
    model = params.model_alias

    if params.aspect_ratio not in spec.aspect_ratios:
        _fail(
            f"Error: Invalid aspect ratio '{params.aspect_ratio}' for {model}. "
            f"Valid: {', '.join(spec.aspect_ratios)}"
        )

    if params.image_size:
        if not spec.image_sizes:
            _fail(f"Error: --image-size is not available for the {model} model.")
        if params.image_size not in spec.image_sizes:
            _fail(
                f"Error: Invalid image size '{params.image_size}' for {model}. "
                f"Valid: {', '.join(spec.image_sizes)}"
            )

    # 検索グラウンディングは継続時も毎ターン効くため、実効モデルで検査する
    if args.google_search and not spec.supports_google_search:
        _fail(f"Error: --google-search is not available for the {model} model.")

    if args.image_search and not spec.supports_image_search:
        _fail(
            f"Error: --image-search is not available for the {model} model. "
            f"Image Search is only supported by {_models_supporting('supports_image_search')}."
        )

    if args.thinking_level and args.thinking_level not in spec.thinking_levels:
        _fail(
            f"Error: Invalid thinking level '{args.thinking_level}' for {model}. "
            f"Valid: {', '.join(spec.thinking_levels)}"
        )

    if args.num_images < 1:
        _fail("Error: --num-images は1以上を指定してください。")
    if args.num_images > MAX_NUM_IMAGES:
        _fail(f"Error: --num-images の上限は {MAX_NUM_IMAGES} 枚です（指定: {args.num_images}枚）。")

    # マルチターンでは -N 無効（1回のターンで1枚が原則）。
    # CLI で明示された -N 2 以上はエラー、config.json 由来の値は 1 に丸めて続行する。
    if (args.chat or args.session) and args.num_images > 1:
        if args.num_images_explicit:
            _fail("Error: マルチターンモード (--chat/--session) では --num-images は1のみ指定可能です。")
        args.num_images = 1
        _note("Note: config.json の num_images はマルチターンモードでは無視され、1 に丸められます。")

    images = (args.input_image or []) + (args.reference or [])
    total_size_mb = 0.0
    for img in images:
        err, size_mb = _validate_image_file(img)
        if err:
            _fail(f"Error: {err}")
        total_size_mb += size_mb
    if images:
        if len(images) > spec.max_input_images:
            _fail(
                f"Error: {model} モデルの画像上限は{spec.max_input_images}枚です"
                f"（指定: {len(images)}枚）。"
            )
        if total_size_mb > MAX_FILE_SIZE_MB:
            _fail(
                f"Error: 画像の合計サイズが上限を超えています: {total_size_mb:.1f}MB（上限: {MAX_FILE_SIZE_MB}MB）"
            )

    if (args.chat or args.session) and not spec.supports_multi_turn:
        _fail(
            f"Error: Multi-turn chat (--chat/--session) is not available for the {model} model."
        )

    out_dir = Path(args.output_dir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory: {out_dir}")


def resolve_params(args):
    """CLI / config / セッションから実効パラメータを解決し、検証まで済ませる。

    継続セッションでは -m / -a / -s が効かない（ターン 1 の設定を引き継ぐ）。
    この「効かない」という 1 つの事実をここだけに閉じ込め、Note の通知・実効値での
    バリデーション・4K のタイムアウト引き上げをすべてこの解決サイトで完結させる。
    """
    if args.session and not Path(args.session).exists():
        _fail(f"Error: Session file not found: {args.session}")
    if args.chat and args.session:
        _fail(
            "Error: --chat and --session are mutually exclusive. "
            "Use --chat for new sessions, --session to continue."
        )

    session_data = load_session(args.session) if args.session else None
    session_path = args.session
    previous_interaction_id = None

    if session_data:
        model_alias = session_data["model_alias"]
        model_id = session_data["model_id"]
        cfg = session_data.get("config", {})
        aspect_ratio = cfg.get("aspect_ratio", args.aspect_ratio)
        image_size = cfg.get("image_size")
        turn_num = len(session_data["turns"]) + 1
        previous_interaction_id = session_data["turns"][-1]["interaction_id"]
        if args.aspect_ratio_explicit or args.image_size:
            _note(
                "Note: セッション継続では -a / -s は無視されます"
                "（ターン 1 の設定を引き継ぎます）。"
            )
        if args.model_explicit and args.model != model_alias:
            _note(f"Note: セッションのモデル {model_alias} を使用します（-m {args.model} は無視）。")
    else:
        model_alias = args.model
        model_id = MODEL_SPECS[model_alias].id
        aspect_ratio = args.aspect_ratio
        image_size = args.image_size
        turn_num = 1 if args.chat else 0
        if args.chat:
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

    params = EffectiveParams(
        model_alias=model_alias,
        model_id=model_id,
        spec=MODEL_SPECS[model_alias],
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        timeout=args.timeout,
        turn_num=turn_num,
        previous_interaction_id=previous_interaction_id,
        session_path=session_path,
        session_data=session_data,
    )
    validate_args(args, params)

    # 検証を通ってから通知する（不正な組み合わせで落ちる場合に調整を告げないため）
    if params.image_size == "4K" and params.timeout < TIMEOUT_4K:
        _note(f"Note: Timeout auto-adjusted to {TIMEOUT_4K}s for 4K generation.")
        params = replace(params, timeout=TIMEOUT_4K)

    return params


def compose_full_prompt(args):
    """プロンプト注釈 + Negative Constraints を付加した最終プロンプトを組み立てる。"""
    input_count = len(args.input_image or [])
    ref_count = len(args.reference or [])

    prompt = args.prompt
    if ref_count:
        # -i のみ・画像なしのときは注釈を付けない（既存動作を維持）
        edit = f"Edit the {input_count} input image(s). " if input_count else ""
        prompt = (
            f"{edit}Use the {ref_count} reference image(s) "
            f"for style and composition guidance. {prompt}"
        )
    if args.negative_constraints:
        return f"{prompt}\n\n{args.negative_constraints}"
    return prompt


def _image_block(path_str):
    """画像ファイルを Interactions API の image 入力ブロック（明示 base64）に変換する。"""
    p = Path(path_str)
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    mime = MIME_MAP.get(p.suffix.lower(), "image/png")
    return {"type": "image", "data": data, "mime_type": mime}


def build_input(args, full_prompt):
    """input を組み立てる。画像がなければ文字列、あれば image/text ブロックの list を返す。"""
    images = (args.input_image or []) + (args.reference or [])
    if not images:
        return full_prompt
    # 順序は -i → -r → テキスト
    return [_image_block(p) for p in images] + [{"type": "text", "text": full_prompt}]


def build_response_format(aspect_ratio, image_size):
    """response_format（画像出力設定）を組み立てる。mime_type は指定しない。"""
    response_format = {"type": "image", "aspect_ratio": aspect_ratio}
    if image_size:
        response_format["image_size"] = API_IMAGE_SIZE_OVERRIDES.get(image_size, image_size)
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


def build_create_kwargs(args, params, input_data, *, store=None, previous_interaction_id=None):
    """interactions.create() の引数を組み立てる。

    単発生成は store=False（interaction_id を使わないため、サーバー側保持を発生させない）。
    継続は store を渡さず、サーバー既定 (store=true) に previous_interaction_id チェーンの
    状態管理を任せる（保持期間 Paid 55 日 / Free 1 日）。
    """
    create_kwargs = {
        "model": params.model_id,
        "input": input_data,
        "response_format": build_response_format(params.aspect_ratio, params.image_size),
        "timeout": params.timeout,
    }
    if store is not None:
        create_kwargs["store"] = store
    if previous_interaction_id:
        create_kwargs["previous_interaction_id"] = previous_interaction_id
    tools = build_tools(args)
    if tools:
        create_kwargs["tools"] = tools
    if args.thinking_level:
        # thinking_level は小文字のまま渡す（minimal|low|high）
        create_kwargs["generation_config"] = {"thinking_level": args.thinking_level}
    return create_kwargs


def load_session(session_path):
    """セッション JSON を読み込み、v2 形式を検証する。破損・旧形式は exit 1。"""
    try:
        with open(session_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        _fail(f"Error: セッションファイルの読み込みに失敗しました: {e}")

    # 旧形式（generate_content 世代）検出
    if not isinstance(data, dict) or "history" in data or "version" not in data:
        _fail(
            "Error: 旧形式（generate_content 世代）のセッションは継続できません。"
            "-c で新規セッションを開始してください。"
        )

    # v2 構造チェック（必須キー欠落・型不一致は破損扱い）
    try:
        if data.get("version") != 2 or data.get("api") != "interactions":
            raise KeyError("version/api")
        _ = data["model_id"]
        # 継続はセッションのモデルで行うため、未知のエイリアス（廃止モデル等）は
        # spec を引けず検証もできない。破損として扱う
        if data["model_alias"] not in MODEL_SPECS:
            raise KeyError("model_alias")
        turns = data["turns"]
        if not isinstance(turns, list) or not turns:
            raise KeyError("turns")
        _ = turns[-1]["interaction_id"]
    except (KeyError, TypeError, IndexError) as e:
        _fail(f"Error: セッションファイルの形式が不正です（key: {e}）。")

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


def extract_and_save_images(
    interaction, output_dir, output_name, turn_num=0, call_index=0, timestamp=None
):
    """Interaction のレスポンスから画像を抽出して保存する。

    steps を走査して model_output の image/text を収集し、画像ゼロなら
    便利プロパティ output_image / output_text をフォールバックとして確認する。

    Returns:
        tuple: (saved_paths, text_parts)
    """
    # PIL が要るのは非 PNG の変換時だけ。欠落時は raw 保存に落ちる（下の except）
    try:
        from PIL import Image
    except ImportError:
        Image = None

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
            _note(f"Note: 同名ファイルが存在するため {out_path.name} に保存します（上書き回避）。")

        try:
            if mime_type == "image/png":
                # 返却が PNG ならそのまま書く。PIL で開き直しても画素は同じで、
                # 4K だと 30MB 超のバッファと再圧縮が無駄に走るだけ
                out_path.write_bytes(img_bytes)
            else:
                if Image is None:
                    raise ImportError("Pillow is not installed")
                Image.open(BytesIO(img_bytes)).save(str(out_path))
            saved_paths.append(str(out_path))
            print(f"Saved: {out_path}")
        except Exception as e:
            # PNG 化に失敗したら、返却 mime の拡張子で raw bytes を保存する
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
            status_code = _status_code(e)

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
    client = _client(api_key)
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


def generate_single_shot(args, params, api_key):
    """単発生成（text-to-image / 画像編集）。N 枚指定時はループで順次生成。"""
    client = _client(api_key)
    create_kwargs = build_create_kwargs(
        args, params, build_input(args, compose_full_prompt(args)), store=False
    )

    all_saved_paths = []
    # -N の全バリエーションで同一のタイムスタンプを共有する（秒またぎ対策）
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i in range(args.num_images):
        if args.num_images > 1:
            print(f"\nGenerating image {i + 1}/{args.num_images} with {params.model_alias} model ({params.model_id})...")
        else:
            print(f"Generating with {params.model_alias} model ({params.model_id})...")

        try:
            interaction = api_call_with_retry(client, create_kwargs)
            saved_paths, text_parts = extract_and_save_images(
                interaction,
                args.output_dir,
                args.output_name,
                turn_num=params.turn_num,
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


def generate_chat(args, params, api_key):
    """マルチターンチャット（セッションファイル v2 管理、サーバー側状態を利用）。"""
    client = _client(api_key)
    session_data = params.session_data

    if args.session:
        print(f"Continuing session (turn {params.turn_num}): {params.session_path}")
    else:
        print(f"Starting new chat session: {params.session_path}")

    full_prompt = compose_full_prompt(args)
    create_kwargs = build_create_kwargs(
        args,
        params,
        build_input(args, full_prompt),
        previous_interaction_id=params.previous_interaction_id,
    )

    print(f"Generating with {params.model_alias} model ({params.model_id})...")
    try:
        interaction = api_call_with_retry(client, create_kwargs)
    except Exception as e:
        if params.previous_interaction_id and _status_code(e) == 404:
            print(
                "Error: 前回の interaction が見つかりません。セッションの保持期限切れ"
                "（Paid Tier 55 日 / Free Tier 1 日）の可能性があります。"
                "-c で新規セッションを開始してください。",
                file=sys.stderr,
            )
            sys.exit(2)
        raise

    saved_paths, text_parts = extract_and_save_images(
        interaction, args.output_dir, args.output_name, turn_num=params.turn_num
    )
    for text in text_parts:
        print(f"\nModel response: {text}")

    if not saved_paths and not text_parts:
        print("Error: No output from model.", file=sys.stderr)
        sys.exit(2)

    # セッション履歴（turn）を追記
    session_data["turns"].append({
        "turn": params.turn_num,
        "prompt": full_prompt,
        "interaction_id": getattr(interaction, "id", None),
        "images": [str(Path(p).resolve()) for p in saved_paths],
        "text": "\n".join(text_parts),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    save_session(params.session_path, session_data)
    print(f"\nSession saved: {params.session_path}")
    print(f"To continue: generate_image.py -p '<next prompt>' --session {params.session_path}")

    return saved_paths


def main():
    """エントリポイント。"""
    config = load_config()
    args = parse_args(config)

    # Lazy import チェック
    try:
        from google import genai  # noqa: F401
    except ImportError:
        _fail(
            "Error: google-genai package is not installed.",
            '  Install with: pip install -U "google-genai>=2.11.0" Pillow',
        )

    # --list-models は --prompt 不要で実行可能
    if args.list_models:
        list_available_models(_require_api_key())
        sys.exit(0)

    # --prompt は --list-models 以外では必須
    if not args.prompt:
        _fail("Error: --prompt (-p) is required.")

    api_key = _require_api_key()
    params = resolve_params(args)

    try:
        if args.chat or args.session:
            generate_chat(args, params, api_key)
        else:
            generate_single_shot(args, params, api_key)
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        status_code = _status_code(e)
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
