#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
归档到资料库：确保「<文件夹>/<YYYY-MM-DD>/」两级目录存在，输出可用于上传的父节点 ID。

用法：
    python3 archive_to_library.py --date 2026-11-03
    python3 archive_to_library.py --date 2026-11-03 --folder 祝超 --space-id <spaceId>

输出（stdout）：
    SPACE_ID=<spaceId>
    PARENT_ID=<日期子文件夹 nodeId>
    SPACE_URL=<空间链接>
    FOLDER_URL=<「祝超」文件夹链接>

已存在的同名文件夹会直接复用，不会重复创建。上传文件请配合 LibraryUpload，
把 PARENT_ID 作为 parent_id 传入。
"""

import argparse
import json
import subprocess
import sys

LIBRARY = "/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library"
API = f"{LIBRARY}/space_api.py"
CREATE_FOLDER = f"{LIBRARY}/manage/create_folder.py"


def run(args):
    proc = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"调用失败：{' '.join(args)}\n{proc.stderr.strip()}")
    return proc.stdout


def api_json(api_name, *extra):
    out = run([API, api_name, *extra])
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise SystemExit(f"接口返回无法解析：{out[:300]}")


def personal_space(space_id=None):
    if space_id:
        return space_id
    data = api_json("space.workspace.list-user-spaces", "--limit", "100")
    for s in data.get("data", {}).get("spaces", []):
        if s.get("category") == "personal":
            return s["spaceId"]
    raise SystemExit("没有找到个人资料库，请用 --space-id 指定")


def list_children(space_id, parent_id=None):
    args = ["space.workspace.list-nodes", "--space-id", space_id, "--limit", "100"]
    if parent_id:
        args += ["--parent-node-id", parent_id]
    data = api_json(*args)
    return data.get("data", {}).get("nodes", [])


def find_folder(space_id, title, parent_id=None):
    for node in list_children(space_id, parent_id):
        if node.get("title") == title:
            return node
    return None


def create_folder(space_id, title, parent_id=None):
    args = [CREATE_FOLDER, "--title", title, "--space-id", space_id]
    if parent_id:
        args += ["--parent-id", parent_id]
    out = run(args)
    for line in out.splitlines():
        if line.startswith("KS_FOLDER_CREATE"):
            parts = line.split("\t")
            return {"id": parts[1], "url": parts[3] if len(parts) > 3 else ""}
    raise SystemExit(f"创建文件夹失败：{out[:300]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日期目录名，如 2026-11-03")
    parser.add_argument("--folder", default="祝超", help="一级文件夹名，默认「祝超」")
    parser.add_argument("--space-id", default=None, help="资料库空间 ID，默认取个人资料库")
    args = parser.parse_args()

    space_id = personal_space(args.space_id)

    top = find_folder(space_id, args.folder)
    if top is None:
        created = create_folder(space_id, args.folder)
        top = {"id": created["id"], "url": created.get("url", "")}

    date_node = find_folder(space_id, args.date, top["id"])
    if date_node is None:
        created = create_folder(space_id, args.date, top["id"])
        date_node = {"id": created["id"], "url": created.get("url", "")}

    print(f"SPACE_ID={space_id}")
    print(f"PARENT_ID={date_node['id']}")
    print(f"SPACE_URL=https://www.workbuddy.cn/space/s/{space_id}")
    print(f"FOLDER_URL=https://www.workbuddy.cn/space/d/{top['id']}")


if __name__ == "__main__":
    main()
