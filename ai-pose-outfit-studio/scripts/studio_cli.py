#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Pose & Outfit Reference Studio CLI (Commercial Edition v1.0.0)
100% Original Copyrighted Assets | Author: 唐家成 (ArcueidA)

Commands:
  stats   : View catalog counts, category breakdown, and 15 style presets
  search  : Multi-dimensional filtering across pose / costume / anime / portrait
  detail  : Inspect full metadata and prompt tags for specific asset ID(s)
  random  : Randomly pick matching assets for inspiration
  fetch   : Download / resolve asset image(s) (and depth map) to local cache
  recipe  : Combine Pose + Costume + Portrait (IDs or local files) into a 3-in-1 composite reference image & bilingual prompt
  preload : Batch warm-up local asset cache with multi-threading
"""

import argparse
import concurrent.futures
import json
import os
import random
import shutil
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure UTF-8 stdout/stderr on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SKILL_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = SKILL_ROOT / "references"
CACHE_DIR = Path.home() / ".workbuddy" / "cache" / "ai-pose-outfit-studio"

GITHUB_OWNER = "ArcueidA"
GITHUB_REPO = "ai-pose-studio"
GITHUB_BRANCH = "main"

# Multi-CDN fallback mirrors (fastest for China mainland & global users)
CDN_TEMPLATES = [
    f"https://gh-proxy.com/https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{{path}}",
    f"https://fastly.jsdelivr.net/gh/{GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH}/{{path}}",
    f"https://gcore.jsdelivr.net/gh/{GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH}/{{path}}",
    f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{{path}}",
]

DATA_FILES = {
    "pose": REFERENCES_DIR / "pose-zh.json",
    "costume": REFERENCES_DIR / "costume-zh.json",
    "anime": REFERENCES_DIR / "costume-anime-zh.json",
    "portrait": REFERENCES_DIR / "portrait-zh.json",
}

STYLE_PRESETS = {
    "realistic": (
        "写实人像写真（85mm定焦商业人像摄影，自然柔光，真实细腻肤质与织物纹理，8K超清细节）",
        "photorealistic portrait photography, 85mm f/1.4 lens, natural soft lighting, ultra-detailed skin and fabric texture, 8k resolution, masterpiece",
    ),
    "fashion": (
        "日韩时尚杂志画报（高级感棚拍光影，时尚Lookbook构图，精致妆造与高级色调）",
        "editorial fashion magazine photography, high-end studio lighting, stylish lookbook composition, refined makeup and color grading",
    ),
    "film": (
        "复古胶片写真（柯达Portra 400胶片质感，细腻银盐颗粒，温暖复古色调与电影氛围感）",
        "vintage Kodak Portra 400 film photography, subtle film grain, warm cinematic color grading, nostalgic atmosphere",
    ),
    "ecommerce_adult": (
        "电商女装模特带货主图（高清全身/半身商品展示，版型挺括清晰，干净明亮商业背景，高转化视觉）",
        "commercial e-commerce fashion model photography, crisp garment fit and fabric details, clean bright background, high conversion studio shot",
    ),
    "ecommerce_kid": (
        "电商童装实拍画报（阳光自然童模街拍/棚拍，色彩明快，服装面料舒适亲肤细节清晰）",
        "commercial kids fashion photography, bright cheerful lighting, crisp children clothing details, natural and lively expression",
    ),
    "flatlay_to_model": (
        "平铺服装转真人模特上身（严格还原参考服装的领口、袖型、版型、花色与材质，自然穿戴在真人模特身上）",
        "flat-lay garment to live model try-on, exact reproduction of neckline, sleeves, pattern, and fabric texture worn naturally by a fashion model",
    ),
    "anime": (
        "日系二次元精致插画（清透赛璐珞与柔和渐变光影结合，细腻发丝与高光眼神，番剧主视觉品质）",
        "high-quality anime illustration, refined cel shading with soft gradients, detailed hair strands and expressive eyes, key visual masterpiece",
    ),
    "cel_anime": (
        "新海诚感唯美动画电影（通透光影，电影级景深与唯美空气感，色彩饱满动人）",
        "Makoto Shinkai style anime movie frame, breathtaking volumetric lighting, cinematic depth of field, vibrant sky and atmospheric glow",
    ),
    "semi_real": (
        "2.5D次世代游戏原画立绘（二次元精致五官与写实立体光影材质融合，高精度服饰褶皱与金属皮革质感）",
        "2.5D semi-realistic game character splash art, exquisite anime facial features with realistic volumetric lighting and intricate material rendering",
    ),
    "concept_sheet": (
        "角色设定集立绘（纯白干净背景，标准角色全身立绘展示，线条干净利落，结构层次分明）",
        "character concept art reference sheet, clean pure white background, crisp line art, clear costume structure and proportions",
    ),
    "render3d": (
        "3D次世代角色渲染（Unreal Engine 5 / Octane渲染质感，次表面散射真实肌肤，毛发与布料物理渲染）",
        "3D next-gen character render, Unreal Engine 5 and Octane render, subsurface scattering skin, physically based hair and cloth shading, 8k",
    ),
    "chibi_box": (
        "3D潮玩盲盒手办质感（泡泡玛特风精致涂装，PVC哑光与高光材质对比，摄影棚柔和立体布光）",
        "3D designer art toy figure, Pop Mart style collectible figure, smooth matte PVC texture with glossy accents, studio product lighting",
    ),
    "manga": (
        "日式黑白漫画网点风（专业漫画G笔线稿，精细网点纸明暗过渡，戏剧性黑白对比）",
        "Japanese monochrome manga style, crisp G-pen ink lineart, intricate screentone shading, dramatic black and white contrast",
    ),
    "cyberpunk": (
        "赛博朋克霓虹夜景（雨夜霓虹冷暖对比光，未来都市机能氛围，高反差电影感布光）",
        "cyberpunk neon night aesthetic, cyan and magenta rim lighting, futuristic urban atmosphere, high-contrast cinematic lighting",
    ),
    "none": (
        "跟随参考图原生画风与质感，保持画面协调自然",
        "natural style matching the reference images, high detail, clean composition",
    ),
}

ANGLE_MAP = {
    "front": ("正面", "front view, facing camera"),
    "side": ("侧面", "side profile view"),
    "34": ("斜侧 (3/4)", "three-quarter angle view, 3/4 view"),
    "above": ("俯视", "high angle shot, from above"),
    "below": ("仰视", "low angle shot, from below"),
    "正面": ("正面", "front view, facing camera"),
    "侧面": ("侧面", "side profile view"),
    "斜侧": ("斜侧 (3/4)", "three-quarter angle view, 3/4 view"),
    "俯视": ("俯视", "high angle shot, from above"),
    "仰视": ("仰视", "low angle shot, from below"),
}

SHOT_MAP = {
    "full": ("全身照", "full body shot, head to toe"),
    "upper": ("上半身", "upper body shot, waist up, cowboy shot"),
    "closeup": ("面部特写", "close-up portrait shot, face focus"),
}


def ensure_pillow():
    """Import PIL, or auto-install Pillow if missing in customer environment."""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps
        return Image, ImageDraw, ImageFont, ImageOps
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "Pillow", "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        from PIL import Image, ImageDraw, ImageFont, ImageOps
        return Image, ImageDraw, ImageFont, ImageOps


def load_catalog(asset_type: str) -> List[Dict[str, Any]]:
    path = DATA_FILES.get(asset_type)
    if not path or not path.exists():
        raise FileNotFoundError(f"Catalog file not found for '{asset_type}': {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for k in ("items", "data", "poses", "costumes", "portraits"):
            if k in data and isinstance(data[k], list):
                return data[k]
    return data if isinstance(data, list) else []


def find_item_by_id(asset_id: str, asset_type: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    target = asset_id.strip().lower()
    search_types = [asset_type] if asset_type else ["pose", "costume", "anime", "portrait"]
    for atype in search_types:
        items = load_catalog(atype)
        for item in items:
            if str(item.get("id", "")).lower() == target:
                return atype, item
    raise KeyError(f"Asset ID '{asset_id}' not found in catalogs ({', '.join(search_types)}).")


def resolve_or_download_relpath(rel_path: str, timeout: int = 20) -> Path:
    """
    Resolve a relative asset path like 'assets/pose/full_single_P001_front.webp':
    1. Check local repository parent folder (if running directly inside cloned repo)
    2. Check local cache (~/.workbuddy/cache/ai-pose-outfit-studio/assets/...)
    3. Download from multi-CDN mirrors and save to local cache
    """
    rel_clean = rel_path.lstrip("/").replace("\\", "/")

    # 1. Check sibling/parent repo assets folder
    for candidate in (
        SKILL_ROOT / rel_clean,
        SKILL_ROOT.parent / rel_clean,
    ):
        if candidate.exists() and candidate.stat().st_size > 100:
            return candidate

    # 2. Check user cache
    cached_file = CACHE_DIR / rel_clean
    if cached_file.exists() and cached_file.stat().st_size > 100:
        return cached_file

    cached_file.parent.mkdir(parents=True, exist_ok=True)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    last_err = None
    for tpl in CDN_TEMPLATES:
        url = tpl.format(path=urllib.parse.quote(rel_clean, safe="/-_."))
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Pose-Outfit-Studio/1.0"
                },
            )
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read()
                if len(data) > 100:
                    tmp_path = cached_file.with_suffix(".tmp")
                    with open(tmp_path, "wb") as f:
                        f.write(data)
                    tmp_path.replace(cached_file)
                    return cached_file
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Failed to download asset '{rel_clean}' from all CDN mirrors. Last error: {last_err}")


def get_item_title(item: Dict[str, Any]) -> str:
    return str(
        item.get("姿势名称")
        or item.get("服装名称")
        or item.get("发型名称")
        or item.get("标题")
        or item.get("名称")
        or item.get("id")
    )


def item_summary(atype: str, item: Dict[str, Any]) -> Dict[str, Any]:
    aid = item.get("id")
    base: Dict[str, Any] = {
        "id": aid,
        "type": atype,
        "标题": get_item_title(item),
    }
    if atype == "pose":
        base.update(
            {
                "体系": item.get("体系", ""),
                "分类": item.get("分类", ""),
                "姿势编号": item.get("姿势编号", ""),
                "角度": item.get("角度", ""),
                "图片": item.get("图片") or f"assets/pose/{aid}.webp",
                "深度图": item.get("深度图") or f"assets/pose_depth/{aid}.webp",
            }
        )
    elif atype in ("costume", "anime"):
        base.update(
            {
                "分类": item.get("分类", ""),
                "标签": item.get("标签", [])[:10],
                "关键词": item.get("关键词", ""),
                "图片": item.get("图片") or f"assets/{atype}/{aid}.webp",
            }
        )
    elif atype == "portrait":
        base.update(
            {
                "分区": item.get("分区", ""),
                "发长": item.get("发长", ""),
                "发型名称": item.get("发型名称", ""),
                "热门": item.get("热门", False),
                "图片": item.get("图片") or f"assets/portrait/{aid}.webp",
            }
        )
    return base


def cmd_stats(_args: argparse.Namespace) -> None:
    report: Dict[str, Any] = {
        "skill": "ai-pose-outfit-studio",
        "version": "1.0.0",
        "author": "唐家成",
        "copyright": "100% Original Owned Assets",
        "cache_dir": str(CACHE_DIR),
        "catalogs": {},
        "total_assets": 0,
        "style_presets": {k: v[0] for k, v in STYLE_PRESETS.items()},
    }
    total = 0
    for atype in ("pose", "costume", "anime", "portrait"):
        items = load_catalog(atype)
        total += len(items)
        cats: Dict[str, int] = {}
        for it in items:
            if atype == "pose":
                c = f"{it.get('体系', '')} / {it.get('分类', '')}".strip(" /")
            elif atype == "portrait":
                c = it.get("发长") or it.get("分区") or "默认"
            else:
                c = it.get("分类") or "默认"
            cats[str(c)] = cats.get(str(c), 0) + 1
        report["catalogs"][atype] = {
            "count": len(items),
            "categories": dict(sorted(cats.items(), key=lambda x: -x[1])),
        }
    report["total_assets"] = total
    print(json.dumps(report, ensure_ascii=False, indent=2))


def match_item(
    item: Dict[str, Any],
    keywords: List[str],
    category: Optional[str],
    shot: Optional[str],
    angle: Optional[str],
    hair_len: Optional[str] = None,
) -> bool:
    blob = (str(item.get("检索", "")) + " " + json.dumps(item, ensure_ascii=False)).lower()
    if category and category.lower() not in blob:
        return False
    if shot and shot.lower() not in blob:
        return False
    if angle:
        a_val = str(item.get("角度") or "").lower()
        if angle.lower() not in a_val and angle.lower() not in blob:
            return False
    if hair_len:
        h_val = str(item.get("发长") or "").lower()
        if hair_len.lower() != h_val and hair_len.lower() not in blob:
            return False
    for kw in keywords:
        if kw.lower() not in blob:
            return False
    return True


def cmd_search(args: argparse.Namespace) -> None:
    raw_q = " ".join(args.keywords or []) + " " + (args.query or "")
    keywords = [k.strip() for k in raw_q.replace(",", " ").split() if k.strip()]

    types = [args.type] if args.type != "all" else ["pose", "costume", "anime", "portrait"]
    matched_all = []
    for atype in types:
        items = load_catalog(atype)
        for it in items:
            if match_item(it, keywords, args.category, args.shot, args.angle, args.hair_len):
                matched_all.append((atype, it))

    if args.random and matched_all:
        chosen = random.sample(matched_all, min(args.limit, len(matched_all)))
    else:
        chosen = matched_all[: args.limit]

    results = [item_summary(t, it) for t, it in chosen]

    print(
        json.dumps(
            {
                "query": raw_q.strip(),
                "type": args.type,
                "category": args.category,
                "total_matched": len(matched_all),
                "returned": len(results),
                "items": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_detail(args: argparse.Namespace) -> None:
    out = []
    for aid in args.ids:
        atype, item = find_item_by_id(aid)
        out.append({"type": atype, "data": item})
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_random(args: argparse.Namespace) -> None:
    keywords = [k.strip() for k in (args.query or "").replace(",", " ").split() if k.strip()]
    types = [args.type] if args.type != "all" else ["pose", "costume", "anime", "portrait"]
    pool = []
    for atype in types:
        for it in load_catalog(atype):
            if match_item(it, keywords, args.category, None, None, None):
                pool.append((atype, it))

    if not pool:
        print(json.dumps({"matched": 0, "items": []}, ensure_ascii=False, indent=2))
        return

    chosen = random.sample(pool, min(args.count, len(pool)))
    print(
        json.dumps(
            {
                "matched_pool": len(pool),
                "selected_count": len(chosen),
                "items": [item_summary(t, it) for t, it in chosen],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def process_fetched_image(
    src_path: Path, flip: bool, resize_mode: str, out_dir: Optional[Path]
) -> Path:
    if not flip and resize_mode == "original" and not out_dir:
        return src_path

    Image, _, _, ImageOps = ensure_pillow()
    target_dir = out_dir or (CACHE_DIR / "processed")
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix_tag = ""
    if flip:
        suffix_tag += "_flip"
    if resize_mode != "original":
        suffix_tag += f"_{resize_mode}"
    dst_path = target_dir / f"{src_path.stem}{suffix_tag}.png"

    with Image.open(src_path) as im:
        img = im.convert("RGB")
        if flip:
            img = ImageOps.mirror(img)
        if resize_mode == "crop":
            img = ImageOps.fit(img, (900, 1200), method=Image.Resampling.LANCZOS)
        elif resize_mode == "pad":
            img = ImageOps.pad(img, (900, 1200), color=(255, 255, 255), method=Image.Resampling.LANCZOS)
        img.save(dst_path, format="PNG")
    return dst_path


def cmd_fetch(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir).resolve() if args.out_dir else None
    results = []
    for raw_id in args.ids:
        atype, item = find_item_by_id(raw_id, args.type)
        if args.depth and atype == "pose":
            rel_img = item.get("深度图") or f"assets/pose_depth/{item['id']}.webp"
        else:
            rel_img = item.get("图片") or f"assets/{atype}/{item['id']}.webp"
        local_img = resolve_or_download_relpath(rel_img)
        final_img = process_fetched_image(local_img, args.flip, args.resize_mode, out_dir)

        entry: Dict[str, Any] = {
            "id": item["id"],
            "type": atype,
            "标题": get_item_title(item),
            "mode": "depth" if (args.depth and atype == "pose") else "normal",
            "local_image": str(final_img),
        }
        results.append(entry)

    print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=2))


def load_cjk_font(ImageFont, size: int):
    font_candidates = [
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for fp in font_candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def build_prompt_for_item(atype: str, item: Dict[str, Any]) -> Tuple[str, str]:
    """Return (chinese_desc, english_prompt) for an item."""
    title = get_item_title(item)
    keywords = str(item.get("关键词") or item.get("提示词") or "")
    tags = item.get("标签") or []
    tag_str = "、".join(str(t) for t in tags[:10])

    if atype == "pose":
        sys_cat = item.get("体系") or ""
        cat = item.get("分类") or ""
        ang = item.get("角度") or ""
        zh = f"{title}（{sys_cat} · {cat} · {ang}机位）"
        en = f"pose reference: {title} ({cat}, {ang} view)"
        return zh, en

    if atype in ("costume", "anime"):
        cat = item.get("分类") or ""
        zh = f"{title}（{cat}，包含：{tag_str or title}）"
        en = f"wearing {keywords or title} ({tag_str})"
        return zh, en

    if atype == "portrait":
        hair_len = item.get("发长") or ""
        hair_name = item.get("发型名称") or title
        zh = f"{hair_len} · {hair_name}"
        en = f"portrait model with {hair_len} hairstyle ({hair_name})"
        return zh, en

    return title, keywords or title


def resolve_slot_input(
    val: str, expected_type: Optional[str] = None, use_depth: bool = False
) -> Tuple[str, Dict[str, Any], Path]:
    """Accept either an asset ID from catalog OR a local image file path uploaded by user."""
    p = Path(val)
    if p.exists() and p.is_file():
        custom_item = {
            "id": p.stem,
            "标题": f"自定义参考图 ({p.name})",
            "关键词": "custom uploaded reference image",
        }
        return expected_type or "custom", custom_item, p.resolve()

    atype, item = find_item_by_id(val, expected_type)
    if use_depth and atype == "pose":
        rel = item.get("深度图") or f"assets/pose_depth/{item['id']}.webp"
    else:
        rel = item.get("图片") or f"assets/{atype}/{item['id']}.webp"
    local_path = resolve_or_download_relpath(rel)
    return atype, item, local_path


def cmd_recipe(args: argparse.Namespace) -> None:
    Image, ImageDraw, ImageFont, ImageOps = ensure_pillow()

    panels: List[Tuple[str, str, Dict[str, Any], Path]] = []

    if args.portrait:
        r_type, r_item, r_path = resolve_slot_input(args.portrait, "portrait")
        panels.append(("【参考图1：人物面部与发型 (PORTRAIT)】", r_type, r_item, r_path))

    if args.costume:
        c_type, c_item, c_path = resolve_slot_input(args.costume, None)
        panels.append(("【参考图2：服装穿搭造型 (OUTFIT)】", c_type, c_item, c_path))

    if args.pose:
        p_type, p_item, p_path = resolve_slot_input(args.pose, "pose", use_depth=args.depth)
        panels.append(("【参考图3：身体动作姿势 (POSE)】", p_type, p_item, p_path))
        if args.include_depth and not args.depth and p_item.get("深度图"):
            d_path = resolve_or_download_relpath(p_item["深度图"])
            panels.append(("【参考图3B：动作深度图 (DEPTH)】", "depth", p_item, d_path))

    if not panels:
        raise ValueError("Please provide at least one of --portrait, --costume, or --pose.")

    card_w, card_h = 600, 800
    header_h = 88
    footer_h = 64
    pad = 24
    n = len(panels)
    canvas_w = pad + n * (card_w + pad)
    canvas_h = header_h + card_h + footer_h + pad

    canvas = Image.new("RGB", (canvas_w, canvas_h), (248, 250, 252))
    draw = ImageDraw.Draw(canvas)
    title_font = load_cjk_font(ImageFont, 26)
    sub_font = load_cjk_font(ImageFont, 18)
    meta_font = load_cjk_font(ImageFont, 17)

    draw.rectangle([0, 0, canvas_w, header_h - 8], fill=(15, 23, 42))
    draw.text(
        (pad, 24),
        "AI 人像姿势与穿搭造型工坊 · 多维参考合成板 (Reference Sheet)",
        fill=(255, 255, 255),
        font=title_font,
    )

    zh_parts = []
    en_parts = []

    for idx, (label, ptype, item, img_path) in enumerate(panels):
        x0 = pad + idx * (card_w + pad)
        y0 = header_h

        with Image.open(img_path) as im:
            im_rgb = im.convert("RGB")
            fitted = ImageOps.fit(im_rgb, (card_w, card_h), method=Image.Resampling.LANCZOS)
            canvas.paste(fitted, (x0, y0))

        draw.rectangle([x0, y0, x0 + card_w, y0 + 44], fill=(15, 23, 42))
        draw.text((x0 + 14, y0 + 10), f"{label}  {item['id']}", fill=(56, 189, 248), font=sub_font)

        title_text = get_item_title(item)
        draw.rectangle([x0, y0 + card_h, x0 + card_w, y0 + card_h + footer_h - 8], fill=(255, 255, 255))
        draw.rectangle([x0, y0, x0 + card_w, y0 + card_h + footer_h - 8], outline=(203, 213, 225), width=2)
        draw.text((x0 + 14, y0 + card_h + 16), title_text[:30], fill=(30, 41, 59), font=meta_font)

        if ptype != "depth":
            zh_desc, en_desc = build_prompt_for_item(ptype, item)
            zh_parts.append(f"- {label}: {zh_desc}")
            en_parts.append(en_desc)

    angle_zh, angle_en = ANGLE_MAP.get(args.angle, ANGLE_MAP["front"])
    shot_zh, shot_en = SHOT_MAP.get(args.shot, SHOT_MAP["full"])
    style_zh, style_en = STYLE_PRESETS.get(args.style, STYLE_PRESETS["realistic"])

    subject_zh = args.subject or "单人模特"
    extra_zh = args.extra_prompt or args.scene or "干净高级背景，大师级光影构图"
    extra_en = args.extra_prompt or args.scene or "clean aesthetic background, studio lighting"

    if args.out:
        out_path = Path(args.out).resolve()
    else:
        out_path = CACHE_DIR / "outputs" / f"recipe_{int(time.time())}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG", optimize=True)

    zh_prompt = (
        f"请严格参考合成图中的各分栏设定，生成一张【{subject_zh}】高清图像：\n"
        + "\n".join(zh_parts)
        + f"\n- 【画风与质感预设 ({args.style})】: {style_zh}\n"
        + f"- 【镜头景别与机位】: {shot_zh}，{angle_zh}\n"
        + f"- 【补充场景与细节】: {extra_zh}\n"
        + "要求：人物的面部五官与发型严格对齐【参考图1】，全身穿搭服饰的款式/颜色/材质严格对齐【参考图2】（禁止将无头人台画成假人模型，必须穿在鲜活人物身上），肢体动作与透视机位严格对齐【参考图3】，画面干净无任何文字标签或水印。"
    )

    en_prompt = (
        f"Masterpiece, {style_en}, {shot_en}, {angle_en}, subject: {subject_zh}. "
        + " | ".join(en_parts)
        + f" | Additional details: {extra_en}. Exact facial features and hairstyle from Panel 1, exact outfit design and fabric from Panel 2 worn naturally by the character, exact body pose and camera angle from Panel 3, clean background, no text or watermark."
    )

    print(
        json.dumps(
            {
                "composite_image": str(out_path),
                "style": {"code": args.style, "zh": style_zh, "en": style_en},
                "panels": [
                    {"role": p[1], "id": p[2]["id"], "title": get_item_title(p[2]), "local_file": str(p[3])}
                    for p in panels
                ],
                "shot": {"code": args.shot, "zh": shot_zh, "en": shot_en},
                "angle": {"code": args.angle, "zh": angle_zh, "en": angle_en},
                "prompt_zh": zh_prompt,
                "prompt_en": en_prompt,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_preload(args: argparse.Namespace) -> None:
    types = [args.type] if args.type != "all" else ["pose", "costume", "anime", "portrait"]
    tasks = []
    for atype in types:
        items = load_catalog(atype)[: args.limit]
        for it in items:
            rel = it.get("图片") or f"assets/{atype}/{it['id']}.webp"
            tasks.append(rel)

    ok, fail = 0, 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(resolve_or_download_relpath, rel) for rel in tasks]
        for fut in concurrent.futures.as_completed(futs):
            try:
                fut.result()
                ok += 1
            except Exception:
                fail += 1

    print(
        json.dumps(
            {"requested": len(tasks), "cached_ok": ok, "failed": fail, "cache_dir": str(CACHE_DIR)},
            ensure_ascii=False,
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="studio_cli.py",
        description="AI Pose & Outfit Reference Studio CLI (Commercial v1.0.0)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="Show catalog statistics, categories, and 15 style presets")

    p_search = sub.add_parser("search", help="Search across pose/costume/anime/portrait catalogs")
    p_search.add_argument("keywords", nargs="*", help="Optional positional search keywords")
    p_search.add_argument("--type", choices=["all", "pose", "costume", "anime", "portrait"], default="all")
    p_search.add_argument("--query", "-q", type=str, default="", help="Keywords separated by space or comma")
    p_search.add_argument("--category", "-c", type=str, default=None, help="Filter by category name")
    p_search.add_argument("--shot", type=str, default=None, help="Filter pose by shot type")
    p_search.add_argument("--angle", type=str, default=None, help="Filter pose by camera angle (正面/斜侧/侧面/俯视/仰视)")
    p_search.add_argument("--hair-len", type=str, default=None, help="Filter portrait by hair length (短发/中发/中长发/长发)")
    p_search.add_argument("--random", action="store_true", help="Randomly sample from matching items")
    p_search.add_argument("--limit", "-n", type=int, default=12, help="Max results to return")

    p_detail = sub.add_parser("detail", help="Get full metadata for one or more asset IDs")
    p_detail.add_argument("ids", nargs="+", help="Asset IDs (e.g. full_single_P001_front SPR-0001 charadb-O001)")

    p_random = sub.add_parser("random", help="Randomly pick assets from catalog")
    p_random.add_argument("--type", choices=["all", "pose", "costume", "anime", "portrait"], default="all")
    p_random.add_argument("--category", "-c", type=str, default=None)
    p_random.add_argument("--query", "-q", type=str, default="")
    p_random.add_argument("--count", "-n", type=int, default=3)

    p_fetch = sub.add_parser("fetch", help="Resolve or download asset image(s) to local cache")
    p_fetch.add_argument("ids", nargs="+", help="One or more Asset IDs (e.g. full_single_P001_front)")
    p_fetch.add_argument("--type", choices=["pose", "costume", "anime", "portrait"], default=None)
    p_fetch.add_argument("--depth", action="store_true", help="Fetch ControlNet depth map (for pose)")
    p_fetch.add_argument("--flip", action="store_true", help="Horizontally flip the fetched image")
    p_fetch.add_argument("--resize-mode", choices=["original", "crop", "pad"], default="original")
    p_fetch.add_argument("--out-dir", type=str, default=None, help="Optional directory to save processed image(s)")

    p_recipe = sub.add_parser("recipe", help="Create 3-in-1 composite reference image & bilingual prompt")
    p_recipe.add_argument("--portrait", type=str, default=None, help="Portrait ID or local image path")
    p_recipe.add_argument("--costume", type=str, default=None, help="Costume/Anime ID or local image path")
    p_recipe.add_argument("--pose", type=str, default=None, help="Pose ID or local image path")
    p_recipe.add_argument("--style", choices=list(STYLE_PRESETS.keys()), default="realistic")
    p_recipe.add_argument("--subject", type=str, default=None, help="Custom subject description")
    p_recipe.add_argument("--extra-prompt", type=str, default=None, help="Additional scene/lighting instructions")
    p_recipe.add_argument("--scene", type=str, default=None, help="Alias for --extra-prompt")
    p_recipe.add_argument("--angle", type=str, default="front")
    p_recipe.add_argument("--shot", choices=["full", "upper", "closeup"], default="full")
    p_recipe.add_argument("--depth", action="store_true", help="Use depth map as the pose panel")
    p_recipe.add_argument("--include-depth", action="store_true", help="Include both pose and depth map panels")
    p_recipe.add_argument("--out", type=str, default=None, help="Output PNG path for composite sheet")

    p_preload = sub.add_parser("preload", help="Pre-download assets into local cache")
    p_preload.add_argument("--type", choices=["all", "pose", "costume", "anime", "portrait"], default="all")
    p_preload.add_argument("--limit", type=int, default=50)
    p_preload.add_argument("--workers", type=int, default=8)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {
        "stats": cmd_stats,
        "search": cmd_search,
        "detail": cmd_detail,
        "random": cmd_random,
        "fetch": cmd_fetch,
        "recipe": cmd_recipe,
        "preload": cmd_preload,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
