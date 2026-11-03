#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-Click Incremental Sync & Commercial Zip Builder
- Reads C:/Users/kewei/.workbuddy/skills/ai-pose-studio/references/owned-overrides.json
- Converts any newly generated owned PNGs to WebP (and generates Depth maps for new poses)
- Rebuilds commercial JSON catalogs in ai-pose-outfit-studio/references/ (1,902+ items)
- Re-packages C:/Users/kewei/Desktop/ai-pose-outfit-studio.zip for WorkBuddy Open Platform
- Optionally commits & pushes new assets to GitHub (ArcueidA/ai-pose-studio)
"""

import argparse
import concurrent.futures
import json
import subprocess
import zipfile
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

PERSONAL_SKILL_DIR = Path(r"C:\Users\kewei\.workbuddy\skills\ai-pose-studio")
PERSONAL_REF_DIR = PERSONAL_SKILL_DIR / "references"
OWNED_OVERRIDES_FILE = PERSONAL_REF_DIR / "owned-overrides.json"

REPO_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = REPO_ROOT / "assets"
COMM_SKILL_DIR = REPO_ROOT / "ai-pose-outfit-studio"
COMM_REF_DIR = COMM_SKILL_DIR / "references"
DESKTOP_ZIP_PATH = Path(r"C:\Users\kewei\Desktop\ai-pose-outfit-studio.zip")


def make_depth_webp(src_png: Path, dst_webp: Path) -> None:
    with Image.open(src_png) as im:
        gray = ImageOps.grayscale(im)
        inv = ImageOps.invert(gray)
        auto = ImageOps.autocontrast(inv, cutoff=2)
        smooth = auto.filter(ImageFilter.GaussianBlur(radius=1.2))
        dst_webp.parent.mkdir(parents=True, exist_ok=True)
        smooth.save(dst_webp, "WEBP", quality=82, method=0)


def convert_one(args_tuple):
    aid, src_path, dst_webp, depth_webp = args_tuple
    if not dst_webp.exists() or dst_webp.stat().st_size < 100:
        dst_webp.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src_path) as im:
            im.convert("RGB").save(dst_webp, "WEBP", quality=85, method=0)
    if depth_webp and (not depth_webp.exists() or depth_webp.stat().st_size < 100):
        make_depth_webp(src_path, depth_webp)
    return aid


def build_zip(skill_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file_path in sorted(skill_dir.rglob("*")):
            if file_path.is_file() and "__pycache__" not in file_path.parts:
                arcname = file_path.relative_to(skill_dir.parent).as_posix()
                zf.write(file_path, arcname)


def main():
    parser = argparse.ArgumentParser(description="Sync owned assets to GitHub repo & rebuild commercial zip")
    parser.add_argument("--push", action="store_true", help="Automatically git add, commit, and push to origin")
    args = parser.parse_args()

    with open(OWNED_OVERRIDES_FILE, "r", encoding="utf-8") as f:
        raw_ov = json.load(f)
    overrides = raw_ov.get("items", raw_ov) if isinstance(raw_ov, dict) else {}

    mapping = {
        "pose": "pose-zh.json",
        "costume": "costume-zh.json",
        "anime": "costume-anime-zh.json",
        "portrait": "portrait-zh.json",
    }

    # Build lookup of which catalog each ID belongs to
    id_to_type = {}
    raw_catalogs = {}
    for atype, fname in mapping.items():
        with open(PERSONAL_REF_DIR / fname, "r", encoding="utf-8") as f:
            items = json.load(f)
        raw_catalogs[atype] = items
        for it in items:
            id_to_type[it["id"]] = atype

    tasks = []
    valid_ids = set()
    for aid, rel_val in overrides.items():
        rel_str = rel_val.get("local_file", "") if isinstance(rel_val, dict) else str(rel_val)
        local_png = PERSONAL_SKILL_DIR / rel_str
        if not local_png.exists():
            local_png = Path(rel_str)
        if not local_png.exists():
            continue
        atype = id_to_type.get(aid)
        if not atype:
            continue
        valid_ids.add(aid)
        dst_webp = ASSETS_DIR / atype / f"{aid}.webp"
        depth_webp = (ASSETS_DIR / "pose_depth" / f"{aid}.webp") if atype == "pose" else None
        tasks.append((aid, local_png, dst_webp, depth_webp))

    print(f"[1/4] Checking/converting {len(tasks)} owned assets to WebP...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(convert_one, tasks))

    print("[2/4] Rebuilding commercial JSON catalogs...")
    counts = {}
    for atype, fname in mapping.items():
        clean_items = []
        for it in raw_catalogs[atype]:
            aid = it.get("id", "")
            if aid not in valid_ids:
                continue
            c = dict(it)
            # Clean third-party / internal fields
            for drop_key in ("source", "来源", "来源地址", "日文名称", "敏感", "仅限成人", "原文标题", "宽", "高", "字节数"):
                c.pop(drop_key, None)
            rel_webp = f"assets/{atype}/{aid}.webp"
            c["缩略图"] = rel_webp
            c["预览图"] = rel_webp
            c["原图"] = rel_webp
            c["图片"] = rel_webp
            if atype == "pose":
                c["深度图"] = f"assets/pose_depth/{aid}.webp"
            clean_items.append(c)

        COMM_REF_DIR.mkdir(parents=True, exist_ok=True)
        with open(COMM_REF_DIR / fname, "w", encoding="utf-8") as f:
            json.dump(clean_items, f, ensure_ascii=False, indent=2)
        counts[atype] = len(clean_items)

    print(f"      Catalog counts: {counts} (Total: {sum(counts.values())})")

    print(f"[3/4] Packaging commercial skill zip -> {DESKTOP_ZIP_PATH} ...")
    build_zip(COMM_SKILL_DIR, DESKTOP_ZIP_PATH)
    size_kb = DESKTOP_ZIP_PATH.stat().st_size / 1024
    print(f"      Done! Zip size: {size_kb:.1f} KB")

    if args.push:
        print("[4/4] Committing and pushing to GitHub...")
        subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: sync {sum(counts.values())} owned assets & commercial skill package"],
            cwd=REPO_ROOT,
            check=False,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
        print("      GitHub push completed!")


if __name__ == "__main__":
    main()
