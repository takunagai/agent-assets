#!/usr/bin/env python3
"""公開共有された Google Drive フォルダの中身を、認証なしで列挙する。

embeddedfolderview は 50 件で切れず全件返すので、通常のフォルダページより素直。
API キーも OAuth も要らないかわり、Drive が HTML の形を変えたら壊れる前提の道具。

  python3 drive_ls.py <FOLDER_ID>              # 直下を列挙
  python3 drive_ls.py <FOLDER_ID> --tree       # 再帰的に全ファイルを列挙
"""
import html as htmllib
import json
import re
import subprocess
import sys

ROW = re.compile(
    r'<div class="flip-entry" id="entry-([A-Za-z0-9_-]{20,})".*?'
    r'<a href="(https://drive\.google\.com/[^"]+)".*?'
    r'<div class="flip-entry-title">([^<]*)</div>',
    re.S,
)


def ls(folder_id):
    """フォルダ直下の [{id, name, isFolder}] を返す。非公開なら空リスト。"""
    page = subprocess.run(
        ["curl", "-sL", "--max-time", "60", "-A", "Mozilla/5.0",
         f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"],
        capture_output=True, text=True, errors="replace").stdout
    return [
        {
            "id": file_id,
            "name": htmllib.unescape(name),
            "isFolder": "/drive/folders/" in href,
        }
        for file_id, href, name in ROW.findall(page)
    ]


def tree(folder_id, path="", depth=0, max_depth=6):
    """再帰的にファイルだけを [{id, path}] で返す。フォルダ名は path に積む。"""
    if depth > max_depth:
        return []
    out = []
    for item in ls(folder_id):
        child = f"{path}/{item['name']}"
        if item["isFolder"]:
            out += tree(item["id"], child, depth + 1, max_depth)
        else:
            out.append({"id": item["id"], "path": child})
    return out


if __name__ == "__main__":
    folder = sys.argv[1]
    result = tree(folder) if "--tree" in sys.argv else ls(folder)
    if not result:
        print("0 件。非公開・ID 違い・Drive の HTML 変更のいずれか（SKILL.md の「詰まったとき」を見る）",
              file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
