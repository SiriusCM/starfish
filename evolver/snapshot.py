import os
import shutil
from datetime import datetime
from settings import SCRIPT_DIR, DATA_DIR

SNAP_DIR = os.path.join(DATA_DIR, ".snapshots")


def _snapshot_targets():
    files = []
    for name in os.listdir(SCRIPT_DIR):
        if name.startswith(".") or name == "__pycache__":
            continue
        p = os.path.join(SCRIPT_DIR, name)
        if os.path.isfile(p) and (name.endswith(".py") or name.endswith(".md")):
            files.append(name)
    return files


def take_snapshot() -> str:
    os.makedirs(SNAP_DIR, exist_ok=True)
    tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(SNAP_DIR, tag)
    os.makedirs(dst, exist_ok=True)
    for name in _snapshot_targets():
        shutil.copy2(os.path.join(SCRIPT_DIR, name), os.path.join(dst, name))
    return dst


def list_snapshots():
    if not os.path.exists(SNAP_DIR):
        return []
    return sorted(os.listdir(SNAP_DIR), reverse=True)


def rollback(tag: str = "") -> str:
    snaps = list_snapshots()
    if not snaps:
        return "无可回滚的快照。"
    target = tag or snaps[0]
    src_dir = os.path.join(SNAP_DIR, target)
    if not os.path.isdir(src_dir):
        return f"快照不存在：{target}"
    for name in os.listdir(src_dir):
        shutil.copy2(os.path.join(src_dir, name), os.path.join(SCRIPT_DIR, name))
    return f"已回滚到快照：{target}"