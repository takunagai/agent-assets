#!/usr/bin/env python3
"""drive_ls.py --tree の出力（またはそれを絞った JSON）を読んで、並列で落とす。

拡張子は信用せずマジックバイトで判定し、画像・PDF 以外や HTML（確認ページ・
エラーページ）が返ったものは捨てて report に残す。

  python3 drive_ls.py <FOLDER_ID> --tree > files.json
  python3 drive_fetch.py files.json <出力先ディレクトリ> [--workers 6]
"""
import json
import pathlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

# マジックバイトから決まる拡張子だけを受け入れる（名前の拡張子は当てにしない）
EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif", "image/heic": ".heic", "application/pdf": ".pdf",
    "video/mp4": ".mp4", "video/quicktime": ".mov",
}


def grab(job):
    index, item, out_dir = job
    tmp = out_dir / f"{index:03d}"
    subprocess.run(
        ["curl", "-sL", "--max-time", "300", "-A", "Mozilla/5.0",
         f"https://drive.google.com/uc?export=download&id={item['id']}",
         "-o", str(tmp)], check=False)
    if not tmp.exists() or tmp.stat().st_size == 0:
        return {"path": item["path"], "ok": False, "reason": "空 or 取得失敗"}
    mime = subprocess.run(["file", "-b", "--mime-type", str(tmp)],
                          capture_output=True, text=True).stdout.strip()
    if mime not in EXT:
        tmp.unlink()
        # text/html は「サイズ超過の確認ページ」か「権限エラー」。SKILL.md を見る
        return {"path": item["path"], "ok": False, "reason": f"想定外の型 {mime}"}
    final = tmp.with_suffix(EXT[mime])
    tmp.rename(final)
    return {"path": item["path"], "ok": True, "file": final.name,
            "bytes": final.stat().st_size, "id": item["id"]}


if __name__ == "__main__":
    items = json.load(open(sys.argv[1]))
    out_dir = pathlib.Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6

    jobs = [(n, item, out_dir) for n, item in enumerate(items, 1)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        report = list(pool.map(grab, jobs))

    ok = [r for r in report if r["ok"]]
    ng = [r for r in report if not r["ok"]]
    json.dump(report, open(out_dir / "_report.json", "w"), ensure_ascii=False, indent=2)
    print(f"取得 {len(ok)} / 失敗 {len(ng)}（{out_dir}/_report.json）", file=sys.stderr)
    for r in ng:
        print(f"  × {r['path']} ─ {r['reason']}", file=sys.stderr)
