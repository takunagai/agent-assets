"""persona-sheet の配布物を組み立てる（リポジトリの外に出力する）

使い方: python3 -I build_distribution.py [出力先フォルダ]
  出力先の既定: ~/Downloads/persona-sheet-dist/（既にあれば止まる。上書きしない）

出力: ペルソナシート作成スキル_v<版>.zip
  中身は persona-sheet/ / persona-sheet.zip（直下に persona-sheet/）の 2 つ
  配る側に不要な scripts/ は含めない

zip のファイル名は UTF-8 で記録する（Python の zipfile は日本語名に UTF-8 フラグを付ける）
"""

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

VERSION = "1.0"
SKIP_NAMES = {".DS_Store"}
SKILL_DIR = Path(__file__).resolve().parent.parent


def add_tree(archive: zipfile.ZipFile, folder: Path, base: Path) -> None:
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.name not in SKIP_NAMES:
            archive.write(path, path.relative_to(base).as_posix())


def main() -> None:
    output = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "Downloads" / "persona-sheet-dist"
    if output.exists():
        raise SystemExit(f"{output} が既にある。中身を確かめてから退避する")

    with tempfile.TemporaryDirectory() as work_name:
        work = Path(work_name)
        dist = work / "dist"
        dist.mkdir()

        # 配る側に不要な scripts/ は含めない
        shutil.copytree(SKILL_DIR, dist / "persona-sheet", ignore=shutil.ignore_patterns(*SKIP_NAMES, "scripts", "__pycache__"))

        # Claude アプリ用: zip の直下に persona-sheet/ フォルダを置く
        with zipfile.ZipFile(dist / "persona-sheet.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            add_tree(archive, dist / "persona-sheet", dist)

        output.mkdir(parents=True)
        bundle = output / f"ペルソナシート作成スキル_v{VERSION}.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(dist.iterdir()):
                if path.is_dir():
                    add_tree(archive, path, dist)
                elif path.name not in SKIP_NAMES:
                    archive.write(path, path.name)
    print(bundle)


if __name__ == "__main__":
    main()
