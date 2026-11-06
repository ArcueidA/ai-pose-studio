#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Pose & Outfit Reference Studio CLI (Commercial Edition v1.4.0)
100% Original Copyrighted Assets + 288 Live Motion Previews | Author: tcccE

Commands:
  stats     : View catalog counts, category breakdown, and 15 style presets
  search    : Multi-dimensional filtering across pose / costume / anime / portrait
  detail    : Inspect full metadata and prompt tags for specific asset ID(s)
  random    : Randomly pick matching assets for inspiration
  fetch     : Download / resolve asset image(s) (depth map / live preview WebP) to local cache
  recipe    : Combine Pose + Costume + Portrait into start/end 3-in-1 reference sheets & Scene-First prompts
  pack-live : Synthesize Animated Live Preview WebP & True XMP Motion Photo (.jpg + .mp4)
  preload   : Batch warm-up local asset cache with multi-threading
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
        "电商女装模特实景带货主图（高清全身/半身商品展示，版型挺括清晰，自然实景与环境光柔和包裹，85mm浅景深人景合一，高转化种草视觉）",
        "commercial e-commerce fashion lifestyle photography, crisp garment fit and fabric details, natural environment light wrapping, 85mm f/1.8 shallow depth of field, seamless subject-background integration",
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


_CATALOG_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def load_catalog(asset_type: str) -> List[Dict[str, Any]]:
    if asset_type in _CATALOG_CACHE:
        return _CATALOG_CACHE[asset_type]
    path = DATA_FILES.get(asset_type)
    if not path or not path.exists():
        raise FileNotFoundError(f"Catalog file not found for '{asset_type}': {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    res: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for k in ("items", "data", "poses", "costumes", "portraits"):
            if k in data and isinstance(data[k], list):
                res = data[k]
                break
    elif isinstance(data, list):
        res = data
    _CATALOG_CACHE[asset_type] = res
    return res


SYNONYM_MAP: Dict[str, List[str]] = {
    "风衣": ["大衣", "外套", "长款外套"],
    "外套": ["大衣", "夹克", "开衫", "西装"],
    "毛衣": ["针织", "针织衫", "高领"],
    "短袖": ["T恤", "女衫", "衬衫"],
    "裙子": ["连衣裙", "半身裙", "长裙", "迷你裙"],
    "裤子": ["长裤", "牛仔", "阔腿裤", "短裤"],
    "高跟": ["高跟鞋", "浅口鞋", "凉鞋"],
    "靴": ["靴子", "短靴", "长靴"],
    "波浪": ["卷发", "大波浪", "外翻", "S型"],
    "微卷": ["卷发", "内扣", "外翻", "S型"],
    "黑长直": ["长发", "直发", "公主切"],
    "丸子头": ["盘发", "团子头", "高马尾"],
    "白领": ["通勤", "职场", "西装", "衬衫"],
    "街拍": ["站姿", "回眸", "行走", "斜侧"],
}


def find_item_by_id(asset_id: str, asset_type: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    target = asset_id.strip().lower()
    search_types = [asset_type] if asset_type else ["costume", "anime", "pose", "portrait"]
    for atype in search_types:
        items = load_catalog(atype)
        for item in items:
            if str(item.get("id", "")).lower() == target:
                return atype, item

    # Fallback: smart keyword scoring match so callers can pass natural language directly
    import re
    raw_tokens = [t.strip().lower() for t in re.split(r"[\s,，、·/+]+", target) if t.strip()]
    stop_words = {"的", "与", "和", "风", "感", "款", "穿搭", "造型", "模特", "参考", "女生", "女性", "单人"}
    tokens = [t for t in raw_tokens if t not in stop_words] or raw_tokens

    expanded_groups: List[List[str]] = []
    for tk in tokens:
        grp = [tk]
        for k_syn, v_list in SYNONYM_MAP.items():
            if k_syn in tk or tk in k_syn:
                grp.extend(x.lower() for x in v_list)
        expanded_groups.append(list(dict.fromkeys(grp)))

    scored_candidates: List[Tuple[float, str, Dict[str, Any]]] = []
    for atype in search_types:
        items = load_catalog(atype)
        for item in items:
            title_s = get_item_title(item).lower()
            cat_s = str(item.get("分类") or item.get("发长") or item.get("体系") or "").lower()
            ang_s = str(item.get("角度") or "").lower()
            tags_s = " ".join(str(x).lower() for x in (item.get("标签") or []))
            kw_s = str(item.get("关键词") or item.get("检索") or "").lower()
            blob_s = f"{title_s} {cat_s} {ang_s} {tags_s} {kw_s}"

            score = 0.0
            matched_tokens = 0
            for grp in expanded_groups:
                grp_best = 0.0
                for cand_tk in grp:
                    cur = 0.0
                    if cand_tk in title_s:
                        cur += 5.0
                    if cand_tk in cat_s or cand_tk in ang_s:
                        cur += 4.0
                    elif cand_tk in tags_s or cand_tk in kw_s:
                        cur += 2.5
                    else:
                        for i in range(max(0, len(cand_tk) - 1)):
                            sub = cand_tk[i : i + 2]
                            if len(sub) == 2 and sub not in stop_words:
                                if sub in title_s or sub in cat_s:
                                    cur += 1.2
                                elif sub in blob_s:
                                    cur += 0.5
                    if cur > grp_best:
                        grp_best = cur
                if grp_best > 0:
                    score += grp_best
                    matched_tokens += 1

            # Heavy bonus for matching MORE distinct concept groups simultaneously
            score += matched_tokens * 8.0
            if item.get("热门"):
                score += 0.3
            if atype == "pose" and "标准系" in str(item.get("体系") or ""):
                score += 2.5
            scored_candidates.append((score, atype, item))

    if scored_candidates:
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_score = scored_candidates[0][0]
        top_pool = [c for c in scored_candidates[:8] if c[0] >= top_score - 0.35]
        picked = random.choice(top_pool)
        return picked[1], picked[2]
    raise KeyError(f"Asset ID '{asset_id}' not found in catalogs ({', '.join(search_types)}).")


def resolve_or_download_relpath(rel_path: str, timeout: int = 20) -> Path:
    """
    Resolve a relative asset path like 'assets/pose/full_single_P001_front.webp':
    1. Check local repository parent folder (if running directly inside cloned repo)
    2. Check local cache (~/.workbuddy/cache/ai-pose-outfit-studio/assets/...)
    3. Check local personal skill owned_assets if present (0ms instant read)
    4. Download from multi-CDN mirrors and save to local cache
    """
    rel_clean = rel_path.lstrip("/").replace("\\", "/")

    # 1. Check sibling/parent repo assets folder & local caches
    for candidate in (
        SKILL_ROOT / rel_clean,
        SKILL_ROOT.parent / rel_clean,
        CACHE_DIR / rel_clean,
    ):
        if candidate.exists() and candidate.stat().st_size > 100:
            return candidate

    # 2. Check personal studio owned_assets (if installed on the same machine)
    parts = rel_clean.split("/")
    if len(parts) >= 3 and parts[0] == "assets":
        cat_dir = parts[1]
        stem = Path(parts[2]).stem
        personal_root = Path.home() / ".workbuddy" / "skills" / "ai-pose-studio" / "owned_assets"
        for ext in (".webp", ".png", ".jpg"):
            p_cand = personal_root / cat_dir / f"{stem}{ext}"
            if p_cand.exists() and p_cand.stat().st_size > 100:
                return p_cand

    cached_file = CACHE_DIR / rel_clean

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
        base_group = str(aid).rsplit("_", 1)[0] if "_" in str(aid) else str(aid)
        base.update(
            {
                "体系": item.get("体系", ""),
                "分类": item.get("分类", ""),
                "姿势编号": item.get("姿势编号", ""),
                "角度": item.get("角度", ""),
                "图片": item.get("图片") or f"assets/pose/{aid}.webp",
                "深度图": item.get("深度图") or f"assets/pose_depth/{aid}.webp",
                "实况预览": item.get("实况预览") or f"assets/pose_live/{base_group}.webp",
                "实况尾帧ID": item.get("实况尾帧ID", ""),
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
        "version": "1.4.0",
        "author": "tcccE",
        "copyright": "100% Original Owned Assets (4,785 Static + 1,439 Depth + 288 Live Motion Previews)",
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
        if getattr(args, "live_preview", False) and atype == "pose":
            base_group = str(item["id"]).rsplit("_", 1)[0]
            rel_img = item.get("实况预览") or f"assets/pose_live/{base_group}.webp"
            local_img = resolve_or_download_relpath(rel_img)
            final_img = local_img
            if out_dir:
                out_dir.mkdir(parents=True, exist_ok=True)
                final_img = out_dir / local_img.name
                shutil.copy2(local_img, final_img)
            mode_str = "live_preview"
        elif args.depth and atype == "pose":
            rel_img = item.get("深度图") or f"assets/pose_depth/{item['id']}.webp"
            local_img = resolve_or_download_relpath(rel_img)
            final_img = process_fetched_image(local_img, args.flip, args.resize_mode, out_dir)
            mode_str = "depth"
        else:
            rel_img = item.get("图片") or f"assets/{atype}/{item['id']}.webp"
            local_img = resolve_or_download_relpath(rel_img)
            final_img = process_fetched_image(local_img, args.flip, args.resize_mode, out_dir)
            mode_str = "normal"

        entry: Dict[str, Any] = {
            "id": item["id"],
            "type": atype,
            "标题": get_item_title(item),
            "mode": mode_str,
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


def build_smart_scene_and_lighting(
    outfit_type: Optional[str],
    outfit_item: Optional[Dict[str, Any]],
    style_code: str,
    custom_scene: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Auto-derive a contextually matched environment, color temperature, and Global Illumination
    light-wrapping rules based on outfit category/tags and style preset, eliminating the 'pasted cutout' look.
    """
    if style_code == "concept_sheet":
        return (
            "纯白无瑕角色设定集背景，均匀柔和的角色全身立体布光，脚底带自然柔和接触投影",
            "clean pure white character concept sheet background, even studio lighting with soft ground contact shadow",
        )

    cat = str((outfit_item or {}).get("分类") or "")
    title = get_item_title(outfit_item) if outfit_item else ""
    blob = f"{cat} {title} {custom_scene or ''}"

    if custom_scene:
        scene_zh = custom_scene
        scene_en = custom_scene
    elif style_code == "ecommerce_kid" or "童" in blob:
        scene_zh = "阳光明媚的莫兰迪奶油风儿童生活美学馆或春日草坪花园实景（85mm f/2.0 柔和光学浅景深虚化）"
        scene_en = "sunlit warm cream-toned kids lifestyle studio or sunny garden lawn with soft f/2.0 optical bokeh"
    elif outfit_type == "anime" or style_code in ("anime", "cel_anime", "semi_real"):
        if "制服" in cat or "校园" in cat:
            scene_zh = "午后阳光斜射的日系樱花校园窗边走廊与蓝天白云远景，通透空气感丁达尔光束"
            scene_en = "sunlit Japanese high school corridor window with cherry blossoms and vibrant sky, volumetric light rays"
        elif "和服" in cat:
            scene_zh = "暮色暖光灯笼映照的古都神社木质回廊与枫叶庭院景深"
            scene_en = "traditional Kyoto wooden shrine corridor with warm glowing lanterns and autumn maple bokeh"
        elif "奇幻" in cat:
            scene_zh = "唯美奇幻流光森林与柔和魔法星尘光斑实景，电影级体积光包裹"
            scene_en = "enchanted fantasy forest with glowing magical particles and cinematic volumetric lighting"
        elif "偶像" in cat:
            scene_zh = "绚丽梦幻的演唱会舞台追光灯与柔焦星光散景（Bokeh）"
            scene_en = "dazzling idol concert stage with atmospheric spotlights and dreamy starlight bokeh"
        elif "赛博" in cat or "军事" in cat or style_code == "cyberpunk":
            scene_zh = "赛博朋克雨夜霓虹都市街角，青紫冷暖双色霓虹反射光映照地面与人物边缘"
            scene_en = "cyberpunk neon rainy street with cyan and magenta neon reflections wrapping around the character"
        else:
            scene_zh = "新海诚式唯美通透阳光街角与微风绿植实景，丰富环境漫反射色彩融合"
            scene_en = "Makoto Shinkai style sunlit street corner with lush greenery and rich ambient color bounce"
    elif "泳装" in cat or "度假" in cat or "比基尼" in blob:
        scene_zh = "阳光明媚的海岛奢华度假酒店无边泳池畔与椰林阳光露台（清澈水波光斑与碧海浅景深）"
        scene_en = "sun-drenched luxury tropical resort infinity pool deck with palm shadows and sparkling water reflections"
    elif "派对" in cat or "礼服" in cat or "晚礼" in blob:
        scene_zh = "高级微醺香槟金法式晚宴厅与水晶壁灯柔和暖色散景（Cinematic warm bokeh）"
        scene_en = "luxurious champagne-gold evening gala hall with warm crystal chandelier bokeh and ambient glow"
    elif "居家" in cat or "睡衣" in cat or "内搭" in cat or "内衣" in cat:
        scene_zh = "清晨第一缕暖阳透过白纱帘洒入的极简原木奶油风卧室与亚麻软装实景"
        scene_en = "cozy minimalist cream-toned bedroom with soft morning sunlight filtering through sheer white curtains"
    elif "通勤" in cat or "职场" in cat or "西装" in blob:
        scene_zh = "现代极简建筑感落地窗CBD写字楼艺术长廊与高级设计买手店实景（85mm f/1.8 浅景深）"
        scene_en = "modern architectural glass-walled CBD gallery office and high-end minimalist boutique with f/1.8 shallow depth of field"
    elif "运动" in cat or "瑜伽" in blob or "健身" in blob:
        scene_zh = "阳光通透的全景落地窗现代普拉提生活馆或清晨活力城市绿道实景"
        scene_en = "sunlit floor-to-ceiling window modern Pilates studio or vibrant morning urban park pathway"
    elif "春" in cat:
        scene_zh = "春日午后暖阳透射的法式街角咖啡馆外摆区与微风绿植林荫街景（85mm f/1.8 自然光学浅景深）"
        scene_en = "spring afternoon sunlit French street corner cafe patio with soft green foliage and f/1.8 optical bokeh"
    elif "夏" in cat:
        scene_zh = "夏日清新通透的阳光露台买手店与明媚街景，柔和树影斑驳漫反射自然光"
        scene_en = "bright breezy summer sunlit terrace boutique and street scene with dappled sunlight and airy bokeh"
    elif "秋" in cat:
        scene_zh = "秋日午后4点暖阳下的复古红砖画廊街区与金黄银杏大道（温暖电影感浅景深）"
        scene_en = "golden hour autumn street with vintage red-brick gallery and warm ginkgo trees in cinematic shallow depth of field"
    elif "冬" in cat or "大衣" in blob or "羽绒" in blob:
        scene_zh = "冬日北欧极简暖光精品买手店橱窗街景与柔和城市漫射天光（远景温暖散景光斑）"
        scene_en = "winter Nordic luxury boutique window street scene with soft daylight and warm cozy interior bokeh glow"
    else:
        scene_zh = "高级自然采光的现代买手店美学空间与通透街景窗光（85mm f/1.8 真实光学浅景深）"
        scene_en = "high-end sunlit modern fashion showroom with natural window daylight and 85mm f/1.8 optical bokeh"

    harmony_zh = (
        f"{scene_zh}。"
        "【人景光影融合铁律（彻底消除抠图感）】：严禁照搬参考图1/2/3中的灰白棚拍纯色背景或网格底！"
        "必须建立统一的三维全局光照（Global Illumination）："
        "1) 环境主光源的冷暖色温必须真实洒在人物面部、发丝边缘（形成自然的发丝环境轮廓光 Rim Light）及服装褶皱上，让肤色与衣料自然吸收环境漫反射光（Ambient Light Wrapping）；"
        "2) 人物与背景地面必须处于同一相机高度与透视地平线上，脚底或坐姿接触面必须生成真实的地面接触阴影（Contact Shadow & Ambient Occlusion）；"
        "3) 背景采用 85mm f/1.8 光学镜头自然浅景深渐变虚化，人物边缘与环境空气感无缝过渡融合。"
    )
    harmony_en = (
        f"{scene_en}. "
        "[Environment & Lighting Integration Rules]: Do NOT copy the plain grey/white studio backgrounds from the reference panels. "
        "Integrate the model seamlessly into the 3D environment with unified Global Illumination: "
        "1) Natural ambient light wrapping and subtle rim light on hair and garment edges matching the background color temperature; "
        "2) Realistic ground contact shadows and ambient occlusion with matched camera horizon perspective; "
        "3) Natural 85mm f/1.8 optical bokeh depth-of-field transition with zero cutout border artifacts."
    )
    return harmony_zh, harmony_en


def exact_find_item_by_id(asset_id: str, asset_type: Optional[str] = None) -> Optional[Tuple[str, Dict[str, Any]]]:
    target = asset_id.strip().lower()
    search_types = [asset_type] if asset_type else ["pose", "costume", "anime", "portrait"]
    for atype in search_types:
        for item in load_catalog(atype):
            if str(item.get("id", "")).lower() == target:
                return atype, item
    return None


def cmd_recipe(args: argparse.Namespace) -> None:
    Image, ImageDraw, ImageFont, ImageOps = ensure_pillow()

    # Support one-shot --auto "<query>" so callers never need separate search calls
    auto_q = getattr(args, "auto", None)
    portrait_arg = args.portrait or (auto_q if auto_q else None)
    costume_arg = args.costume or (auto_q if auto_q else None)
    pose_arg = args.pose or (auto_q if auto_q else None)

    slot_specs: List[Tuple[str, str, Optional[str], bool]] = []
    if portrait_arg:
        slot_specs.append(("【参考图1：人物面部与发型 (PORTRAIT)】", portrait_arg, "portrait", False))
    if costume_arg:
        c_expect = "anime" if args.style in ("anime", "cel_anime", "semi_real", "concept_sheet", "manga") else None
        slot_specs.append(("【参考图2：服装穿搭造型 (OUTFIT)】", costume_arg, c_expect, False))
    if pose_arg:
        slot_specs.append(("【参考图3：身体动作姿势 (POSE)】", pose_arg, "pose", args.depth))

    if not slot_specs:
        raise ValueError("Please provide --auto <keywords> or at least one of --portrait, --costume, or --pose.")

    # Resolve & fetch all slots in parallel for maximum speed
    resolved_map: Dict[int, Tuple[str, Dict[str, Any], Path]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        fut_map = {
            ex.submit(resolve_slot_input, val, exp_type, use_d): idx
            for idx, (_lbl, val, exp_type, use_d) in enumerate(slot_specs)
        }
        for fut, idx in fut_map.items():
            resolved_map[idx] = fut.result()

    panels: List[Tuple[str, str, Dict[str, Any], Path]] = []
    outfit_type_resolved: Optional[str] = None
    outfit_item_resolved: Optional[Dict[str, Any]] = None
    pose_item_resolved: Optional[Dict[str, Any]] = None

    for idx, (label, _val, _exp, _used) in enumerate(slot_specs):
        rtype, ritem, rpath = resolved_map[idx]
        panels.append((label, rtype, ritem, rpath))
        if rtype in ("costume", "anime", "custom") and "OUTFIT" in label:
            outfit_type_resolved = rtype
            outfit_item_resolved = ritem
        if rtype == "pose":
            pose_item_resolved = ritem
            if args.include_depth and not args.depth and ritem.get("深度图"):
                d_path = resolve_or_download_relpath(ritem["深度图"])
                panels.append(("【参考图3B：动作深度图 (DEPTH)】", "depth", ritem, d_path))

    # Compact high-clarity panel dimensions (450x600 saves 45% encoding/upload time while keeping crisp details)
    card_w, card_h = 450, 600
    header_h = 72
    footer_h = 54
    pad = 18
    n = len(panels)
    canvas_w = pad + n * (card_w + pad)
    canvas_h = header_h + card_h + footer_h + pad

    canvas = Image.new("RGB", (canvas_w, canvas_h), (248, 250, 252))
    draw = ImageDraw.Draw(canvas)
    title_font = load_cjk_font(ImageFont, 22)
    sub_font = load_cjk_font(ImageFont, 15)
    meta_font = load_cjk_font(ImageFont, 14)

    draw.rectangle([0, 0, canvas_w, header_h - 6], fill=(15, 23, 42))
    draw.text(
        (pad, 20),
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
            fitted = ImageOps.fit(im_rgb, (card_w, card_h), method=Image.Resampling.BILINEAR)
            canvas.paste(fitted, (x0, y0))

        draw.rectangle([x0, y0, x0 + card_w, y0 + 38], fill=(15, 23, 42))
        draw.text((x0 + 10, y0 + 8), f"{label}  {item['id']}", fill=(56, 189, 248), font=sub_font)

        title_text = get_item_title(item)
        draw.rectangle([x0, y0 + card_h, x0 + card_w, y0 + card_h + footer_h - 6], fill=(255, 255, 255))
        draw.rectangle([x0, y0, x0 + card_w, y0 + card_h + footer_h - 6], outline=(203, 213, 225), width=2)
        draw.text((x0 + 10, y0 + card_h + 14), title_text[:26], fill=(30, 41, 59), font=meta_font)

        if ptype != "depth":
            zh_desc, en_desc = build_prompt_for_item(ptype, item)
            zh_parts.append(f"- {label}: {zh_desc}")
            en_parts.append(en_desc)

    # Auto-align angle with selected pose's actual camera angle if user left default
    effective_angle = args.angle
    if pose_item_resolved and args.angle == "front" and pose_item_resolved.get("角度"):
        effective_angle = str(pose_item_resolved["角度"])

    angle_zh, angle_en = ANGLE_MAP.get(effective_angle, ANGLE_MAP["front"])
    shot_zh, shot_en = SHOT_MAP.get(args.shot, SHOT_MAP["full"])
    style_zh, style_en = STYLE_PRESETS.get(args.style, STYLE_PRESETS["realistic"])

    subject_zh = args.subject or "单人模特"
    user_custom_scene = args.extra_prompt or args.scene
    extra_zh, extra_en = build_smart_scene_and_lighting(
        outfit_type_resolved, outfit_item_resolved, args.style, user_custom_scene
    )

    if args.out:
        out_path = Path(args.out).resolve()
    else:
        out_path = CACHE_DIR / "outputs" / f"recipe_{int(time.time())}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG", compress_level=3)

    zh_prompt = (
        f"【单张完整实景摄影成片 · 严禁输出分栏拼图或照搬参考图灰白底色】\n"
        f"请生成一张【{subject_zh}】置身于真实三维环境中的高清商业大片（{shot_zh}，{angle_zh}）：\n"
        f"- 【核心场景与全局光影包裹 (Scene & Global Illumination - 最高权重)】: {extra_zh}\n"
        f"- 【摄影画风与镜头质感 ({args.style})】: {style_zh}\n"
        + "\n".join(zh_parts)
        + "\n【人景合一执行标准】：必须将人物完全融入上述实景光场中——让环境主光源色温自然洒在人物面部、发丝边缘（形成柔和环境轮廓光）与服装面料褶皱上，脚底与地面产生真实的接触阴影（Contact Shadow），远景呈现 85mm f/1.8 真实光学浅景深虚化；同时人物五官发型对齐【参考图1】、全身服饰款式颜色对齐【参考图2】（必须穿在鲜活真人身上，严禁画成塑料假人台）、肢体动作对齐【参考图3】，画面干净无任何文字标签或水印。"
    )

    en_prompt = (
        f"[Single Full-Frame Photograph - Do NOT output split panels or studio grey backgrounds] "
        f"Masterpiece, {style_en}, {shot_en}, {angle_en}, subject: {subject_zh} seamlessly integrated into a real 3D environment: {extra_en} | "
        + " | ".join(en_parts)
        + " | Exact facial features and hairstyle from Panel 1, exact outfit design and fabric from Panel 2 worn naturally by a living model, exact body pose and camera angle from Panel 3, unified global illumination, natural rim light and ground contact shadow, no text or watermark."
    )

    live_info = None
    if getattr(args, "live", False):
        next_angle_map = {
            "_front": ("_diag", "由正面自然微侧身30度至斜侧视角，展示服装立体剪裁与侧身线条"),
            "_diag": ("_front", "由斜侧视角自然转回正面微笑看向镜头，发丝与衣摆随之轻盈摆动"),
            "_side": ("_diag", "由侧面缓步微转至斜侧45度视角，展现穿搭层次与呼吸感"),
            "_high": ("_front", "镜头由微俯拍平滑过渡至平视正面，模特抬头自然眨眼浅笑"),
            "_low": ("_front", "镜头由微仰拍平滑过渡至平视正面，模特身姿舒展自然呼吸"),
        }
        end_pose_id = None
        end_pose_item = None
        transition_zh = "模特保持站姿自然呼吸、眨眼1次并露出浅笑，微风轻拂发丝与衣摆"
        actual_pose_id = str(pose_item_resolved["id"]) if pose_item_resolved else ""
        live_preview_local = None

        if actual_pose_id:
            base_group = actual_pose_id.rsplit("_", 1)[0] if "_" in actual_pose_id else actual_pose_id
            rel_live_webp = (pose_item_resolved or {}).get("实况预览") or f"assets/pose_live/{base_group}.webp"
            try:
                live_preview_local = str(resolve_or_download_relpath(rel_live_webp))
            except Exception:
                live_preview_local = None

            for suf, (target_suf, t_desc) in next_angle_map.items():
                if actual_pose_id.endswith(suf):
                    cand_id = actual_pose_id[: -len(suf)] + target_suf
                    found_cand = exact_find_item_by_id(cand_id, "pose")
                    if found_cand:
                        end_pose_id = cand_id
                        end_pose_item = found_cand[1]
                        transition_zh = t_desc
                    break

        # Build End-Frame Composite Reference Sheet (locks Panel 1 & Panel 2, swaps Panel 3 to end_pose_id)
        end_composite_path = None
        end_frame_prompt_zh = None
        if end_pose_id and end_pose_item:
            try:
                _, _, end_pose_img_path = resolve_slot_input(end_pose_id, "pose", use_depth=args.depth)
                end_canvas = canvas.copy()
                end_draw = ImageDraw.Draw(end_canvas)
                for p_idx, (p_lbl, p_tp, _p_it, _p_path) in enumerate(panels):
                    if p_tp == "pose":
                        x0 = pad + p_idx * (card_w + pad)
                        y0 = header_h
                        with Image.open(end_pose_img_path) as eim:
                            efitted = ImageOps.fit(eim.convert("RGB"), (card_w, card_h), method=Image.Resampling.BILINEAR)
                            end_canvas.paste(efitted, (x0, y0))
                        end_draw.rectangle([x0, y0, x0 + card_w, y0 + 38], fill=(15, 23, 42))
                        end_draw.text((x0 + 10, y0 + 8), f"{p_lbl}  {end_pose_id} (实况尾帧)", fill=(250, 204, 21), font=sub_font)
                        etitle = get_item_title(end_pose_item)
                        end_draw.rectangle([x0, y0 + card_h, x0 + card_w, y0 + card_h + footer_h - 6], fill=(255, 255, 255))
                        end_draw.rectangle([x0, y0, x0 + card_w, y0 + card_h + footer_h - 6], outline=(203, 213, 225), width=2)
                        end_draw.text((x0 + 10, y0 + card_h + 14), etitle[:26], fill=(30, 41, 59), font=meta_font)
                end_out = out_path.with_name(f"{out_path.stem}_end_frame.png")
                end_canvas.save(end_out, format="PNG", compress_level=3)
                end_composite_path = str(end_out)
                end_ang = str(end_pose_item.get("角度") or "斜侧")
                end_frame_prompt_zh = (
                    zh_prompt.replace(f"（{shot_zh}，{angle_zh}）", f"（{shot_zh}，{end_ang}·实况连续尾帧）")
                    + f"\n【实况连续尾帧锁死要求】：本图作为实况照片（Live Photo）的第 2.5 秒连续尾帧，人物面部五官发型、全身服饰细节、实景背景与环境光色温必须与首帧 100% 保持同一时空恒定，仅身体姿势自然过渡至【{end_pose_id}（{end_ang}机位：{transition_zh}）】。"
                )
            except Exception:
                pass

        sprite_sheet_live_prompt_zh = (
            f"【3×2 六帧连续人物动作实况序列图 (6-Frame Seamless Loop Animation Sprite Sheet)】\n"
            f"请严格绘制一张 3列×2行（共6格，零边框、零文字、零分割线）的高清连续动作序列图，画面中 6 格的相机机位、实景背景（{extra_zh}）、人物五官发型（对齐【参考图1】）与全身服饰材质细节（对齐【参考图2】）必须 100% 锁死在同一时空：\n"
            f"- 第1帧(左上)：{subject_zh}按【参考图3】初始姿势自然静立看向镜头，神态灵动；\n"
            f"- 第2帧(中上)：微风轻拂发丝与衣摆，模特自然闭眼完成一次轻柔眨眼；\n"
            f"- 第3帧(右上)：睁眼露出温柔甜美浅笑，同时单手自然微抬轻触衣领或耳畔发丝；\n"
            f"- 第4帧(左下)：头部微倾約5度、笑意加深，微风吹动服装下摆呈现真实垂坠飘动感；\n"
            f"- 第5帧(中下)：抬起的手臂缓缓自然回落，衣摆与发丝渐趋平稳；\n"
            f"- 第6帧(右下)：平滑回到与第1帧完全衔接的初始姿势，形成完美无缝循环（Seamless Loop）。"
        )
        sprite_sheet_live_prompt_en = (
            f"Create a seamless 3x2 grid (3 columns, 2 rows, 6 equal frames, zero borders, zero text) sequential Live Photo animation sprite sheet. "
            f"Strict consistency across all 6 frames: exact facial features & hairstyle from Panel 1, exact outfit from Panel 2, and exact 3D background ({extra_en}). "
            f"Frame 1 (top-left): initial pose from Panel 3 looking at camera; "
            f"Frame 2 (top-middle): gentle breeze blowing hair and coat hem, natural soft eye blink; "
            f"Frame 3 (top-right): eyes open with a warm sweet smile, one hand gently raising to touch collar/hair; "
            f"Frame 4 (bottom-left): slight head tilt with deeper smile, fabric folds flowing in breeze; "
            f"Frame 5 (bottom-middle): hand smoothly lowering back down; "
            f"Frame 6 (bottom-right): smoothly returning to Frame 1 pose for a seamless loop."
        )

        live_info = {
            "enabled": True,
            "duration_sec": "2.0s - 3.0s (iPhone Live Photo / 小红书抖音实况标准时长)",
            "live_pose_preview_webp": live_preview_local,
            "start_composite_image": str(out_path),
            "end_pose_id": end_pose_id,
            "end_composite_image": end_composite_path,
            "transition_action": transition_zh,
            "end_frame_prompt_zh": end_frame_prompt_zh,
            "sprite_sheet_live_prompt_zh": sprite_sheet_live_prompt_zh,
            "sprite_sheet_live_prompt_en": sprite_sheet_live_prompt_en,
            "chatgpt_live_prompt_zh": (
                f"{zh_prompt}\n"
                f"【Live Photo 实况微动附加指令】：生成具有 iPhone 实况照片（Live Photo）呼吸感的动态实况效果。"
                f"动态轨迹：{transition_zh}；手持相机极轻微呼吸感晃动，环境光影自然流动；"
                f"【防崩坏铁律】：全程严禁五官变形或肢体扭曲，衣服领口/袖口/面料花纹与人物脸型必须100%锁死一致。"
            ),
            "video_i2v_prompt_zh": (
                f"2.5秒高清电商实况写真（Live Photo）：{subject_zh}，{transition_zh}。"
                f"微风轻拂发丝与面料褶皱，眼神灵动自然眨眼一次，手持镜头轻微呼吸感，人物与实景背景光影自然融合，五官与服装细节严格恒定不变。"
            ),
            "video_i2v_prompt_en": (
                f"2.5s realistic iPhone Live Photo, subtle natural micro-motion: {subject_zh}, gentle breeze blowing hair and fabric folds, "
                f"natural eye blink and soft smile, subtle handheld camera breathing motion, seamless environment lighting, strict facial and outfit consistency, 60fps smooth motion."
            ),
            "workflow_for_non_live_models": (
                "【真·人物动作实况双通道】："
                "通道A（推荐·Codex GPT-Image-2.6直出）：运行 `studio_cli.py codex-live --ref-image <composite_image>`（或用 ImageGen 传入 sprite_sheet_live_prompt_zh 生成 3×2 连续动作序列图后执行 `studio_cli.py pack-live --photo 序列图.png --sprite-sheet`），直接通过 2D FFT 防抖对齐 + MCI 双向光流补帧产出真·人物眨眼微笑动作实况照片；"
                "通道B（首尾帧/呼吸感实况）：用 start_composite_image 与 end_composite_image 生成首尾帧后运行 `studio_cli.py pack-live --photo 首帧.png --end-photo 尾帧.png`。"
            ),
        }

    result_payload = {
        "composite_image": str(out_path),
        "style": {"code": args.style, "zh": style_zh, "en": style_en},
        "panels": [
            {"role": p[1], "id": p[2]["id"], "title": get_item_title(p[2]), "local_file": str(p[3])}
            for p in panels
        ],
        "shot": {"code": args.shot, "zh": shot_zh, "en": shot_en},
        "angle": {"code": effective_angle, "zh": angle_zh, "en": angle_en},
        "prompt_zh": zh_prompt,
        "prompt_en": en_prompt,
    }
    if live_info:
        result_payload["live_photo"] = live_info

    print(
        json.dumps(
            result_payload,
            ensure_ascii=False,
            indent=2,
        )
    )


def inject_motion_photo_xmp(jpeg_bytes: bytes, mp4_bytes: bytes) -> bytes:
    """
    Inject Google Camera / Android / Xiaohongshu standard MotionPhoto XMP metadata into JPEG APP1
    and append the MP4 video stream at the end of the file.
    """
    mp4_len = len(mp4_bytes)
    xmp_str = (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.1.0-jc003">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" '
        'xmlns:GCamera="http://ns.google.com/photos/1.0/camera/" '
        'xmlns:Camera="http://ns.google.com/photos/1.0/camera/" '
        'xmlns:Container="http://ns.google.com/photos/1.0/container/" '
        'xmlns:Item="http://ns.google.com/photos/1.0/container/item/" '
        'GCamera:MicroVideo="1" '
        'GCamera:MicroVideoVersion="1" '
        f'GCamera:MicroVideoOffset="{mp4_len}" '
        'GCamera:MicroVideoPresentationTimestampUs="0" '
        'Camera:MotionPhoto="1" '
        'Camera:MotionPhotoVersion="1" '
        'Camera:MotionPhotoPresentationTimestampUs="0">'
        '<Container:Directory><rdf:Seq>'
        '<rdf:li rdf:parseType="Resource">'
        '<Item:Mime>image/jpeg</Item:Mime>'
        '<Item:Semantic>Primary</Item:Semantic>'
        '<Item:Length>0</Item:Length>'
        '<Item:Padding>0</Item:Padding>'
        '</rdf:li>'
        '<rdf:li rdf:parseType="Resource">'
        '<Item:Mime>video/mp4</Item:Mime>'
        '<Item:Semantic>MotionPhoto</Item:Semantic>'
        f'<Item:Length>{mp4_len}</Item:Length>'
        '<Item:Padding>0</Item:Padding>'
        '</rdf:li>'
        '</rdf:Seq></Container:Directory>'
        '</rdf:Description></rdf:RDF></x:xmpmeta>'
    )
    xmp_payload = b"http://ns.adobe.com/xap/1.0/\x00" + xmp_str.encode("utf-8")
    seg_len = len(xmp_payload) + 2
    app1_seg = b"\xff\xe1" + seg_len.to_bytes(2, "big") + xmp_payload

    if jpeg_bytes[:2] != b"\xff\xd8":
        raise ValueError("Invalid JPEG header")
    return jpeg_bytes[:2] + app1_seg + jpeg_bytes[2:] + mp4_bytes


def find_ffmpeg_binary() -> Optional[str]:
    try:
        import imageio_ffmpeg  # type: ignore
        ff_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if ff_exe and Path(ff_exe).exists():
            return str(ff_exe)
    except Exception:
        pass
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    winget_pkgs = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_pkgs.exists():
        found_ff = list(winget_pkgs.rglob("ffmpeg.exe"))
        if found_ff:
            return str(found_ff[0])
    return None


def extract_and_stabilize_sprite_frames(
    sheet_rgb: Any,
    cols: int = 3,
    rows: int = 2,
    target_w: int = 900,
) -> List[Any]:
    """
    Split a 3x2 (6-frame) continuous human-action sprite sheet, stabilize sub-frame shifts
    via 2D FFT phase correlation, crop border seams cleanly, and upscale with LANCZOS + UnsharpMask.
    """
    Image, _ImageDraw, _ImageFont, _ImageOps = ensure_pillow()
    from PIL import ImageFilter

    sw, sh = sheet_rgb.size
    cw, ch = sw // cols, sh // rows
    raw_cells = []
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * cw, r * ch
            raw_cells.append(sheet_rgb.crop((x0, y0, x0 + cw, y0 + ch)))

    # 2D FFT phase-correlation stabilization against Frame 0
    shifts = [(0, 0)]
    try:
        import numpy as np  # type: ignore
        ref_arr = np.asarray(raw_cells[0].convert("L"), dtype=np.float32)
        ref_arr = ref_arr - ref_arr.mean()
        f_ref = np.fft.fft2(ref_arr)
        h_a, w_a = ref_arr.shape
        for cell in raw_cells[1:]:
            cur_arr = np.asarray(cell.convert("L"), dtype=np.float32)
            cur_arr = cur_arr - cur_arr.mean()
            cross = f_ref * np.conj(np.fft.fft2(cur_arr))
            denom = np.abs(cross)
            denom[denom < 1e-8] = 1e-8
            corr = np.real(np.fft.ifft2(cross / denom))
            dy, dx = np.unravel_index(np.argmax(corr), corr.shape)
            if dy > h_a // 2:
                dy -= h_a
            if dx > w_a // 2:
                dx -= w_a
            dx = int(max(-14, min(14, dx)))
            dy = int(max(-14, min(14, dy)))
            shifts.append((dx, dy))
    except Exception:
        shifts = [(0, 0) for _ in raw_cells]

    # Safe inner crop margin to eliminate grid borders & shift padding
    mx = max(6, int(cw * 0.02) + max(abs(s[0]) for s in shifts))
    my = max(6, int(ch * 0.02) + max(abs(s[1]) for s in shifts))
    inner_w = max(64, cw - 2 * mx)
    inner_h = max(64, ch - 2 * my)

    out_w = target_w - (target_w % 2)
    out_h = int(round(out_w * inner_h / float(inner_w)))
    out_h -= out_h % 2

    clean_frames = []
    for cell, (dx, dy) in zip(raw_cells, shifts):
        # Shift cell by (dx, dy) via crop offset (-dx, -dy)
        bx0 = mx - dx
        by0 = my - dy
        cropped = cell.crop((bx0, by0, bx0 + inner_w, by0 + inner_h))
        up = cropped.resize((out_w, out_h), Image.Resampling.LANCZOS)
        up = up.filter(ImageFilter.UnsharpMask(radius=1.15, percent=60, threshold=2))
        clean_frames.append(up)
    return clean_frames


def synthesize_sprite_live_bundle(
    clean_frames: List[Any],
    out_dir: Path,
    stem: str,
    cover_index: int = 2,
) -> Dict[str, Any]:
    """
    Turn 6 stabilized human-action frames into:
    1) High-res single-frame cover photo (*_key_photo.png) & Frame 1 photo (*_frame1_photo.png)
    2) True-color Animated WebP (*_live_preview.webp) & GIF (*_live_action.gif)
    3) 24fps Optical-Flow (ffmpeg minterpolate MCI) smooth human-action MP4 (*_motion_live.mp4)
    4) Single-frame cover True XMP Motion Photo (*_motion_live.jpg)
    """
    Image, ImageDraw, ImageFont, _ImageOps = ensure_pillow()
    from io import BytesIO
    import subprocess
    import tempfile
    import wave

    out_dir.mkdir(parents=True, exist_ok=True)
    safe_idx = max(0, min(len(clean_frames) - 1, cover_index))
    cover_rgb = clean_frames[safe_idx]
    frame1_rgb = clean_frames[0]

    key_photo_path = out_dir / f"{stem}_key_photo.png"
    frame1_photo_path = out_dir / f"{stem}_frame1_photo.png"
    cover_rgb.save(key_photo_path, format="PNG", compress_level=3)
    frame1_rgb.save(frame1_photo_path, format="PNG", compress_level=3)

    # Ping-pong / seamless loop sequence: 0 -> 1 -> 2 -> 3 -> 4 -> 5 (-> 0)
    # Using all 6 sequential loop frames with natural dwell on pose & smile peak
    seq_frames = list(clean_frames)
    seq_durations = [420, 320, 460, 480, 340, 380]
    if len(seq_durations) != len(seq_frames):
        seq_durations = [380] * len(seq_frames)

    font = load_cjk_font(ImageFont, 18)
    stamped_webp = []
    for fr in seq_frames:
        fc = fr.copy()
        dr = ImageDraw.Draw(fc)
        dr.rounded_rectangle([18, 18, 138, 50], radius=16, fill=(15, 23, 42))
        dr.ellipse([29, 28, 41, 40], fill=(239, 68, 68))
        dr.text((48, 22), "LIVE 实况", fill=(255, 255, 255), font=font)
        stamped_webp.append(fc)

    preview_webp = out_dir / f"{stem}_live_preview.webp"
    stamped_webp[0].save(
        preview_webp,
        format="WEBP",
        save_all=True,
        append_images=stamped_webp[1:],
        duration=seq_durations,
        loop=0,
        quality=88,
        method=4,
    )

    companion_mp4_path = out_dir / f"{stem}_motion_live.mp4"
    motion_jpg_path = None
    ffmpeg_bin = find_ffmpeg_binary()

    if ffmpeg_bin:
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            # Save 7 frames (0..5 + 0 at the end) so optical flow closes the loop seamlessly over ~2.6s
            loop_seq = list(clean_frames) + [clean_frames[0]]
            for idx, fr in enumerate(loop_seq):
                fr.save(td_p / f"s_{idx:02d}.png", format="PNG")

            wav_p = td_p / "silence.wav"
            with wave.open(str(wav_p), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(b"\x00\x00\x00\x00" * int(44100 * 2.65))

            # Bidirectional block-matching Motion Compensated Interpolation (MCI) -> 24fps smooth human action
            vf_filter = "minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,format=yuv420p"
            cmd_ff = [
                ffmpeg_bin, "-y",
                "-framerate", "2.6",
                "-i", str(td_p / "s_%02d.png"),
                "-i", str(wav_p),
                "-t", "2.60",
                "-vf", vf_filter,
                "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                str(companion_mp4_path),
            ]
            r_ff = subprocess.run(cmd_ff, capture_output=True)
            if r_ff.returncode == 0 and companion_mp4_path.exists() and companion_mp4_path.stat().st_size >= 10_240:
                mp4_bytes = companion_mp4_path.read_bytes()
                buf = BytesIO()
                # Primary cover MUST be the clean single-frame portrait photo, NOT the 6-panel grid!
                cover_rgb.save(buf, format="JPEG", quality=95)
                motion_jpg_path = out_dir / f"{stem}_motion_live.jpg"
                motion_jpg_path.write_bytes(inject_motion_photo_xmp(buf.getvalue(), mp4_bytes))

    return {
        "status": "ok",
        "mode": "sprite_sheet_optical_flow_mci",
        "frame_count": len(clean_frames),
        "cover_frame_index": safe_idx,
        "key_photo_png": str(key_photo_path),
        "frame1_photo_png": str(frame1_photo_path),
        "live_preview_webp": str(preview_webp),
        "companion_mp4": str(companion_mp4_path) if companion_mp4_path.exists() else None,
        "motion_photo_jpg": str(motion_jpg_path) if motion_jpg_path else None,
        "platform_guide": {
            "小红书/安卓相册": "直接上传 motion_photo_jpg（高清单帧人物封面 + 内置XMP视频流，自动点亮LIVE实况标）",
            "抖音/快手图文实况": "上传 companion_mp4 或 motion_photo_jpg 即可发布实况图文",
            "高清静态主图": "直接使用 key_photo_png 或 frame1_photo_png",
        },
    }


def cmd_pack_live(args: argparse.Namespace) -> None:
    """
    Package a 3x2 human-action sprite sheet (--sprite-sheet) OR static model photo (+ optional end-frame / MP4) into:
    1) Animated WebP Live Preview (*_live_preview.webp)
    2) True XMP Motion Photo (*_motion_live.jpg) with clean single-person cover & H.264 MP4 stream
    """
    Image, ImageDraw, ImageFont, ImageOps = ensure_pillow()
    from io import BytesIO

    photo_path = Path(args.photo).resolve()
    if not photo_path.exists():
        raise FileNotFoundError(f"Primary photo not found: {photo_path}")

    out_dir = Path(args.out_dir).resolve() if args.out_dir else (CACHE_DIR / "live_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name if getattr(args, "name", None) else photo_path.stem

    with Image.open(photo_path) as im0:
        base_rgb = im0.convert("RGB")
        w, h = base_rgb.size

    if getattr(args, "sprite_sheet", False):
        clean_frames = extract_and_stabilize_sprite_frames(
            base_rgb,
            cols=getattr(args, "cols", 3),
            rows=getattr(args, "rows", 2),
            target_w=getattr(args, "target_width", 900),
        )
        bundle = synthesize_sprite_live_bundle(
            clean_frames,
            out_dir=out_dir,
            stem=stem,
            cover_index=getattr(args, "cover_index", 2),
        )
        bundle["source_sprite_sheet"] = str(photo_path)
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        return

    # 1. Generate smooth breathing / keyframe Animated WebP preview
    preview_webp = out_dir / f"{stem}_live_preview.webp"
    frames = []
    durations = []
    prev_w, prev_h = min(w, 720), min(h, int(720 * h / max(1, w)))
    f_start = base_rgb.resize((prev_w, prev_h), Image.Resampling.BILINEAR)

    if args.end_photo and Path(args.end_photo).exists():
        with Image.open(args.end_photo) as im1:
            f_end = ImageOps.fit(im1.convert("RGB"), (prev_w, prev_h), method=Image.Resampling.BILINEAR)
        steps = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 0.8, 0.6, 0.4, 0.2]
        for s in steps:
            blended = Image.blend(f_start, f_end, s)
            frames.append(blended)
            durations.append(480 if s in (0.0, 1.0) else 110)
    else:
        # Subtle handheld camera breathing & micro-zoom (1.00x -> 1.035x -> 1.00x)
        scales = [1.0, 1.008, 1.016, 1.024, 1.032, 1.038, 1.032, 1.024, 1.016, 1.008]
        for sc in scales:
            cw, ch = int(prev_w / sc), int(prev_h / sc)
            left = (prev_w - cw) // 2
            top = int((prev_h - ch) * 0.35)  # Focus on upper-body/face center
            cropped = f_start.crop((left, top, left + cw, top + ch)).resize((prev_w, prev_h), Image.Resampling.BILINEAR)
            frames.append(cropped)
            durations.append(360 if sc in (1.0, 1.038) else 110)

    # Add subtle LIVE badge on preview WebP
    font = load_cjk_font(ImageFont, 16)
    stamped_frames = []
    for fr in frames:
        fc = fr.copy()
        dr = ImageDraw.Draw(fc)
        dr.rounded_rectangle([14, 14, 118, 42], radius=13, fill=(15, 23, 42))
        dr.ellipse([24, 23, 34, 33], fill=(239, 68, 68))
        dr.text((40, 17), "LIVE 实况", fill=(255, 255, 255), font=font)
        stamped_frames.append(fc)

    stamped_frames[0].save(
        preview_webp,
        format="WEBP",
        save_all=True,
        append_images=stamped_frames[1:],
        duration=durations,
        loop=0,
        quality=82,
        method=0,
    )

    # 2. Synthesize real 2.5s H.264 MP4 (if not provided or <10KB) via ffmpeg, then pack Motion Photo (.jpg)
    motion_jpg_path = None
    companion_mp4_path = out_dir / f"{stem}_motion_live.mp4"

    valid_video_path: Optional[Path] = None
    if args.video and Path(args.video).exists() and Path(args.video).stat().st_size >= 10_240:
        valid_video_path = Path(args.video).resolve()
    else:
        ffmpeg_bin = find_ffmpeg_binary()
        if ffmpeg_bin:
            import math
            import subprocess
            import tempfile
            import wave

            vw = w - (w % 2)
            vh = h - (h % 2)
            fps = 30
            n_frames = 75  # 2.5s @ 30fps
            with tempfile.TemporaryDirectory() as td:
                td_p = Path(td)
                wav_p = td_p / "silence.wav"
                with wave.open(str(wav_p), "wb") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(44100)
                    wf.writeframes(b"\x00\x00\x00\x00" * int(44100 * 2.5))

                src_even = base_rgb.resize((vw, vh), Image.Resampling.LANCZOS)
                end_even = None
                if args.end_photo and Path(args.end_photo).exists():
                    with Image.open(args.end_photo) as im_e:
                        end_even = ImageOps.fit(im_e.convert("RGB"), (vw, vh), method=Image.Resampling.LANCZOS)

                for idx in range(n_frames):
                    wt = 0.5 - 0.5 * math.cos(2.0 * math.pi * (idx / float(n_frames)))
                    if end_even is not None:
                        fr_im = Image.blend(src_even, end_even, wt)
                    else:
                        sc = 1.0 + 0.042 * wt
                        cw, ch = int(vw / sc), int(vh / sc)
                        lx = (vw - cw) // 2
                        ty = int((vh - ch) * 0.35)
                        fr_im = src_even.crop((lx, ty, lx + cw, ty + ch)).resize((vw, vh), Image.Resampling.BICUBIC)
                    fr_im.save(td_p / f"f_{idx:04d}.jpg", "JPEG", quality=94)

                cmd_ff = [
                    ffmpeg_bin, "-y",
                    "-framerate", str(fps),
                    "-i", str(td_p / "f_%04d.jpg"),
                    "-i", str(wav_p),
                    "-t", "2.50",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                    str(companion_mp4_path),
                ]
                r_ff = subprocess.run(cmd_ff, capture_output=True)
                if r_ff.returncode == 0 and companion_mp4_path.exists() and companion_mp4_path.stat().st_size >= 10_240:
                    valid_video_path = companion_mp4_path

    if valid_video_path and valid_video_path.exists():
        ffmpeg_bin = find_ffmpeg_binary()
        if ffmpeg_bin and valid_video_path != companion_mp4_path:
            import subprocess
            # Trim to 3.0s Live Photo standard with stereo 44.1kHz AAC audio track
            subprocess.run(
                [
                    ffmpeg_bin, "-y", "-i", str(valid_video_path),
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                    "-t", "3.0",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
                    str(companion_mp4_path),
                ],
                capture_output=True,
            )
        if not companion_mp4_path.exists() or companion_mp4_path.stat().st_size < 10_240:
            shutil.copy2(valid_video_path, companion_mp4_path)
        mp4_bytes = companion_mp4_path.read_bytes()
        buf = BytesIO()
        base_rgb.save(buf, format="JPEG", quality=94)
        motion_bytes = inject_motion_photo_xmp(buf.getvalue(), mp4_bytes)
        motion_jpg_path = out_dir / f"{stem}_motion_live.jpg"
        motion_jpg_path.write_bytes(motion_bytes)
    else:
        companion_mp4_path = None

    print(
        json.dumps(
            {
                "status": "ok",
                "source_photo": str(photo_path),
                "source_end_photo": str(Path(args.end_photo).resolve()) if args.end_photo else None,
                "source_video": str(Path(args.video).resolve()) if args.video else None,
                "live_preview_webp": str(preview_webp),
                "motion_photo_jpg": str(motion_jpg_path) if motion_jpg_path else None,
                "companion_mp4": str(companion_mp4_path) if companion_mp4_path else None,
                "platform_guide": {
                    "小红书/安卓相册": "直接上传或导入 motion_photo_jpg（内置GCamera/MotionPhoto双标准XMP视频流，自动点亮LIVE实况标）或companion_mp4",
                    "抖音/快手图文实况": "在发布图文时直接勾选 companion_mp4 或 motion_photo_jpg 即可作为实况图文发布",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_codex_live(args: argparse.Namespace) -> None:
    """
    Directly invoke local Codex OAuth backend with OpenAI's latest GPT-Image-2.6
    (`gpt-image-2.6-sunburst` or `gpt-image-2.6-flare`) to generate a 6-frame continuous
    human-action sprite sheet from a 3-in-1 reference board (or auto-built recipe),
    then automatically run 2D FFT stabilization + MCI optical-flow 24fps synthesis + XMP Motion Photo packing!
    """
    import base64
    import uuid
    from io import BytesIO, StringIO
    import contextlib

    Image, _ImageDraw, _ImageFont, _ImageOps = ensure_pillow()

    auth_path = Path(args.auth_file).expanduser().resolve()
    if not auth_path.exists():
        raise FileNotFoundError(f"Codex auth.json not found at {auth_path}. Please sign in to Codex CLI first.")

    auth_obj = json.loads(auth_path.read_text(encoding="utf-8"))
    tokens = auth_obj.get("tokens") or {}
    access_token = tokens.get("access_token", "")
    account_id = tokens.get("account_id", "")
    if not access_token or not account_id:
        raise ValueError("Missing access_token or account_id in ~/.codex/auth.json")

    ref_image_path: Optional[Path] = Path(args.ref_image).resolve() if args.ref_image else None
    sprite_prompt = args.prompt or ""
    recipe_meta = None

    # If no ref_image is given, auto-build a 3-in-1 recipe board in 0.2s from --auto / --portrait / --costume / --pose
    if not ref_image_path and (args.auto or args.portrait or args.costume or args.pose):
        rec_ns = argparse.Namespace(
            auto=args.auto,
            portrait=args.portrait,
            costume=args.costume,
            pose=args.pose,
            style=args.style,
            subject=args.subject,
            extra_prompt=args.scene,
            scene=args.scene,
            angle="front",
            shot="full",
            depth=False,
            include_depth=False,
            live=True,
            out=None,
        )
        buf_out = StringIO()
        with contextlib.redirect_stdout(buf_out):
            cmd_recipe(rec_ns)
        recipe_meta = json.loads(buf_out.getvalue())
        ref_image_path = Path(recipe_meta["composite_image"]).resolve()

    action_desc = args.action or "自然眨眼一次、露出温柔甜美微笑、单手轻柔抬起轻触衣领/耳畔发丝，微风吹动衣摆与发丝后自然回落至初始站姿"
    if not sprite_prompt:
        if recipe_meta and not args.action:
            sprite_prompt = recipe_meta.get("live_photo", {}).get("sprite_sheet_live_prompt_zh", "")
        else:
            base_zh = recipe_meta.get("prompt_zh", "") if recipe_meta else ""
            scene_desc = args.scene or "通透自然采光的时尚街拍实景，85mm f/1.8 真实光学浅景深"
            sprite_prompt = (
                f"【3×2 六帧连续人物动作实况序列图 (6-Frame Seamless Loop Animation Sprite Sheet · 严禁分割线与文字水印)】\n"
                f"{base_zh}\n"
                f"【序列帧排版与连续动作硬性要求】：请将整张画面严格均分为 3列×2行（共6个紧邻无缝的等大矩形单人竖版取景格，零边框、零白边、零文字标签）。"
                f"6 格画面的相机机位、实景背景（{scene_desc}）、人物五官脸型发型（严格对齐【参考图1】）与全身服饰材质细节（严格对齐【参考图2】，绝不画成塑料人台）必须 100% 锁死恒定，仅人物神态与肢体展现如下连贯丝滑的 2.5 秒实况动作（{action_desc}）：\n"
                f"- 第1帧(左上)：按【参考图3】初始姿势自然看向镜头，眼神清澈灵动；\n"
                f"- 第2帧(中上)：微风轻拂发丝与衣摆，模特自然闭眼完成一次轻柔眨眼，手部开始微抬启动动作；\n"
                f"- 第3帧(右上)：睁眼露出温柔灵动微笑，核心动作自然展开（{action_desc}）；\n"
                f"- 第4帧(左下)：头部微倾、笑意与动作达到最美高光瞬间，微风吹动发丝与衣摆呈现真实动态飘逸感；\n"
                f"- 第5帧(中下)：抬起的手部与身姿自然舒缓回落，表情保持温柔浅笑；\n"
                f"- 第6帧(右下)：平滑回到与第1帧完全衔接的初始姿态，形成完美无缝循环（Seamless Loop）。"
            )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "ChatGPT-Account-Id": account_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "codex_cli_rs/0.1.0 (Windows 10.0.26100; x86_64)",
        "x-codex-image-turn-id": str(uuid.uuid4()),
    }

    t0 = time.time()
    if ref_image_path and ref_image_path.exists():
        mime = "image/png" if ref_image_path.suffix.lower() == ".png" else "image/jpeg"
        b64_ref = f"data:{mime};base64," + base64.b64encode(ref_image_path.read_bytes()).decode("ascii")
        endpoint = "https://chatgpt.com/backend-api/codex/images/edits"
        payload: Dict[str, Any] = {
            "model": args.model,
            "images": [{"image_url": b64_ref}],
            "prompt": sprite_prompt,
            "size": args.size,
            "quality": args.quality,
        }
    else:
        endpoint = "https://chatgpt.com/backend-api/codex/images/generations"
        payload = {
            "model": args.model,
            "prompt": sprite_prompt,
            "size": args.size,
            "quality": args.quality,
            "n": 1,
        }

    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=240) as resp:
        resp_body = json.loads(resp.read().decode("utf-8"))
        img_bytes = base64.b64decode(resp_body["data"][0]["b64_json"])
    gen_elapsed = round(time.time() - t0, 2)

    out_dir = Path(args.out_dir).resolve() if args.out_dir else (CACHE_DIR / "live_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name or f"codex26_live_{int(time.time())}"
    raw_sheet_path = out_dir / f"{stem}_spritesheet.png"
    raw_sheet_path.write_bytes(img_bytes)

    with Image.open(BytesIO(img_bytes)) as sh_im:
        clean_frames = extract_and_stabilize_sprite_frames(
            sh_im.convert("RGB"), cols=3, rows=2, target_w=args.target_width
        )
    bundle = synthesize_sprite_live_bundle(
        clean_frames, out_dir=out_dir, stem=stem, cover_index=args.cover_index
    )
    bundle["codex_model"] = args.model
    bundle["generation_elapsed_sec"] = gen_elapsed
    bundle["reference_board"] = str(ref_image_path) if ref_image_path else None
    bundle["raw_spritesheet_png"] = str(raw_sheet_path)
    if recipe_meta:
        bundle["recipe_panels"] = recipe_meta.get("panels")
    print(json.dumps(bundle, ensure_ascii=False, indent=2))


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
        description="AI Pose & Outfit Reference Studio CLI (Commercial v1.4.0)",
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
    p_fetch.add_argument("--live-preview", action="store_true", help="Fetch animated Live Photo motion preview WebP (for pose)")
    p_fetch.add_argument("--flip", action="store_true", help="Horizontally flip the fetched image")
    p_fetch.add_argument("--resize-mode", choices=["original", "crop", "pad"], default="original")
    p_fetch.add_argument("--out-dir", type=str, default=None, help="Optional directory to save processed image(s)")

    p_recipe = sub.add_parser("recipe", help="Create 3-in-1 composite reference image & bilingual prompt")
    p_recipe.add_argument("--auto", "-a", type=str, default=None, help="One-shot natural language query to auto-select portrait, costume, and pose in 0.2s")
    p_recipe.add_argument("--portrait", type=str, default=None, help="Portrait ID, keywords (e.g. '长发 微卷'), or local image path")
    p_recipe.add_argument("--costume", type=str, default=None, help="Costume/Anime ID, keywords (e.g. '春季 风衣'), or local image path")
    p_recipe.add_argument("--pose", type=str, default=None, help="Pose ID, keywords (e.g. '站姿 斜侧'), or local image path")
    p_recipe.add_argument("--style", choices=list(STYLE_PRESETS.keys()), default="realistic")
    p_recipe.add_argument("--subject", type=str, default=None, help="Custom subject description")
    p_recipe.add_argument("--extra-prompt", type=str, default=None, help="Additional scene/lighting instructions")
    p_recipe.add_argument("--scene", type=str, default=None, help="Alias for --extra-prompt")
    p_recipe.add_argument("--angle", type=str, default="front")
    p_recipe.add_argument("--shot", choices=["full", "upper", "closeup"], default="full")
    p_recipe.add_argument("--depth", action="store_true", help="Use depth map as the pose panel")
    p_recipe.add_argument("--include-depth", action="store_true", help="Include both pose and depth map panels")
    p_recipe.add_argument("--live", action="store_true", help="Generate Live Photo micro-motion prompts & continuous angle transition")
    p_recipe.add_argument("--out", type=str, default=None, help="Output PNG path for composite sheet")

    p_preload = sub.add_parser("preload", help="Pre-download assets into local cache")
    p_preload.add_argument("--type", choices=["all", "pose", "costume", "anime", "portrait"], default="all")
    p_preload.add_argument("--limit", type=int, default=50)
    p_preload.add_argument("--workers", type=int, default=8)

    p_pack_live = sub.add_parser("pack-live", help="Synthesize Animated Live Preview WebP & True XMP Motion Photo (.jpg + .mp4)")
    p_pack_live.add_argument("--photo", required=True, type=str, help="Primary static model photo OR 3x2 human-action sprite sheet (.png/.jpg/.webp)")
    p_pack_live.add_argument("--sprite-sheet", action="store_true", help="Treat --photo as a 3x2 (6-frame) continuous human-action sprite sheet, run 2D FFT stabilization + MCI optical-flow 24fps synthesis, and use single-person frame as Motion Photo cover")
    p_pack_live.add_argument("--cols", default=3, type=int, help="Sprite sheet columns (default 3)")
    p_pack_live.add_argument("--rows", default=2, type=int, help="Sprite sheet rows (default 2)")
    p_pack_live.add_argument("--cover-index", default=2, type=int, help="Frame index (0..5) to use as high-res single-person cover photo (default 2 = Frame 3 smile peak)")
    p_pack_live.add_argument("--target-width", default=900, type=int, help="Target upscaled width for each stabilized frame (default 900)")
    p_pack_live.add_argument("--name", default=None, type=str, help="Custom output filename stem")
    p_pack_live.add_argument("--end-photo", default=None, type=str, help="Optional continuous end-frame photo for zero-cost motion interpolation")
    p_pack_live.add_argument("--video", default=None, type=str, help="Optional 2-3s MP4/MOV video to embed into XMP Motion Photo (.jpg)")
    p_pack_live.add_argument("--out-dir", default=None, type=str, help="Output directory for live assets")

    p_codex_live = sub.add_parser(
        "codex-live",
        help="Invoke local Codex GPT-Image-2.6 (`gpt-image-2.6-sunburst` / `gpt-image-2.6-flare`) to generate a 6-frame human-action Live Photo bundle",
    )
    p_codex_live.add_argument("--ref-image", default=None, type=str, help="3-in-1 composite reference board or portrait/outfit reference image")
    p_codex_live.add_argument("--auto", "-a", default=None, type=str, help="Or auto-select portrait+costume+pose in 0.2s via natural keywords (e.g. '秋季 大衣 街拍')")
    p_codex_live.add_argument("--portrait", default=None, type=str, help="Portrait ID, keywords, or local path")
    p_codex_live.add_argument("--costume", default=None, type=str, help="Costume ID, keywords, or local path")
    p_codex_live.add_argument("--pose", default=None, type=str, help="Pose ID, keywords, or local path")
    p_codex_live.add_argument("--style", choices=list(STYLE_PRESETS.keys()), default="realistic")
    p_codex_live.add_argument("--subject", default=None, type=str, help="Custom model description")
    p_codex_live.add_argument("--scene", default=None, type=str, help="Custom scene & global illumination description")
    p_codex_live.add_argument("--action", default=None, type=str, help="Custom human action sequence (e.g. '眨眼微笑、抬手轻抚衣领、微风吹拂长发与裙摆')")
    p_codex_live.add_argument("--prompt", default=None, type=str, help="Override full sprite-sheet generation prompt")
    p_codex_live.add_argument(
        "--model",
        choices=["gpt-image-2.6-sunburst", "gpt-image-2.6-flare", "gpt-image-1.5", "gpt-image-1"],
        default="gpt-image-2.6-sunburst",
        help="Codex image model: gpt-image-2.6-sunburst (highest consistency) or gpt-image-2.6-flare (fastest)",
    )
    p_codex_live.add_argument("--size", default="1024x1536", type=str, help="Generation size (1024x1536 or 1536x1536)")
    p_codex_live.add_argument("--quality", choices=["low", "medium", "high"], default="medium")
    p_codex_live.add_argument("--cover-index", default=2, type=int, help="Frame index (0..5) for single-person cover photo (default 2)")
    p_codex_live.add_argument("--target-width", default=900, type=int, help="Upscaled frame width (default 900)")
    p_codex_live.add_argument("--name", default=None, type=str, help="Custom output filename stem")
    p_codex_live.add_argument("--out-dir", default=None, type=str, help="Output directory")
    p_codex_live.add_argument("--auth-file", default=str(Path.home() / ".codex" / "auth.json"), type=str, help="Path to ~/.codex/auth.json")

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
        "pack-live": cmd_pack_live,
        "codex-live": cmd_codex_live,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
