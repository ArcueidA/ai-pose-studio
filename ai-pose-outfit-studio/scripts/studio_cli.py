#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Pose & Outfit Reference Studio CLI (Commercial Edition v1.5.0)
100% Original Copyrighted Assets + Daily Douyin/Xiaohongshu Influencer Expansion | Author: tcccE

Commands:
  stats     : View catalog counts, category breakdown, and 16 style presets
  search    : Multi-dimensional filtering across pose / costume / anime / portrait
  detail    : Inspect full metadata and prompt tags for specific asset ID(s)
  random    : Randomly pick matching assets for inspiration
  fetch     : Download / resolve asset image(s) (or ControlNet depth map) to local cache
  recipe    : Combine Pose + Costume + Portrait into 3-in-1 reference sheet & Scene-First prompts
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
    "influencer_ootd": (
        "小红书/抖音高赞网红OOTD街拍（松弛感自然抓拍构图，高颅顶精致网红妆造，通透原生感奶油冷白皮与高级织物肌理，85mm f/1.8 真实街景柔焦空气感，百万赞种草封面质感）",
        "viral Xiaohongshu and Douyin influencer OOTD street snap, effortless candid vibe, high-cranial-top refined influencer makeup, luminous creamy skin and crisp garment texture, 85mm f/1.8 natural urban bokeh, high-engagement social media fashion lookbook",
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
    "波浪": ["卷发", "大波浪", "外翻", "S型", "高颅顶"],
    "微卷": ["卷发", "内扣", "外翻", "S型"],
    "黑长直": ["长发", "直发", "公主切"],
    "丸子头": ["盘发", "团子头", "高马尾"],
    "白领": ["通勤", "职场", "西装", "衬衫", "知识分子"],
    "街拍": ["站姿", "回眸", "行走", "斜侧", "网红", "小红书", "松弛感"],
    "网红": ["小红书", "抖音", "爆款", "街拍", "松弛感", "纯欲", "千金", "辣妹", "美拉德", "韩系", "ootd"],
    "小红书": ["网红", "爆款", "松弛感", "知识分子", "美拉德", "老钱风", "芭蕾风", "千金", "汉南洞"],
    "抖音": ["网红", "爆款", "辣妹", "纯欲", "街拍", "潮童", "新中式", "甜酷", "摸胯"],
    "松弛感": ["回眸", "插兜", "漫步", "慵懒", "斜侧", "咖啡", "知识分子", "狼尾"],
    "纯欲": ["挂脖", "露肩", "修身", "针织", "白开水妆", "麻花辫", "抹胸", "辣妹"],
    "辣妹": ["短款", "露脐", "高腰", "工装", "甜酷", "y2k", "羽毛剪", "摸胯", "交叉腿"],
    "美拉德": ["焦糖", "棕", "麂皮", "巴恩风", "复古", "秋季", "风衣", "皮衣"],
    "巴恩风": ["美拉德", "麂皮", "灯芯绒", "工装", "夹克", "复古"],
    "千金": ["小香风", "粗花呢", "财阀", "汉南洞", "高颅顶", "大波浪", "老钱风"],
    "老钱风": ["静奢", "羊绒", "针织", "极简", "高级感", "知识分子", "宋锦"],
    "知识分子": ["上宽下窄", "格纹", "衬衫", "针织", "百褶裙", "金丝眼镜", "老钱风"],
    "芭蕾风": ["balletcore", "丝带", "纱裙", "堆堆袜", "玛丽珍", "绑带"],
    "新中式": ["宋锦", "盘扣", "马面裙", "立领", "提花", "国风", "东方"],
    "网球风": ["alo", "百褶短裙", "运动", "polo", "瑜伽", "活力"],
    "潮童": ["童装", "儿童", "抖音爆款", "卫衣", "背带裤", "新中式童装"],
    "地雷系": ["量产型", "蝴蝶结", "蕾丝", "哥特", "双马尾", "洛丽塔"],
    "天使界隈": ["水色系", "机能", "透明感", "二次元", "白发", "潮服"],
}

INFLUENCER_HINT_WORDS = {
    "网红", "小红书", "抖音", "爆款", "ootd", "松弛感", "纯欲", "辣妹",
    "美拉德", "巴恩风", "千金", "汉南洞", "老钱风", "知识分子", "芭蕾",
    "balletcore", "新中式", "网球", "alo", "潮童", "地雷系", "天使界隈", "y2k",
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
    wants_influencer = any(any(hw in tk for hw in INFLUENCER_HINT_WORDS) for tk in raw_tokens)
    wants_kid = any(any(kw in tk for kw in ("童", "娃", "孩", "kid", "child")) for tk in raw_tokens)

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
            aid_s = str(item.get("id") or "").lower()
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
            if wants_influencer and ("xhs" in aid_s or "网红" in blob_s or "小红书" in blob_s or "抖音" in blob_s):
                score += 4.5
            is_kid_item = ("童装" in blob_s or "萌娃" in blob_s or "男童" in blob_s or "女童" in blob_s or "xhs-k" in aid_s)
            if wants_kid and is_kid_item:
                score += 8.0
            elif not wants_kid and is_kid_item:
                score -= 8.0
            if atype == "pose" and ("标准系" in str(item.get("体系") or "") or "网红" in str(item.get("体系") or "")):
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
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Pose-Outfit-Studio/1.5"
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
        "version": "1.5.0",
        "author": "tcccE",
        "copyright": "100% Original Owned Assets + Daily Douyin/Xiaohongshu Influencer Expansion",
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
        kw_l = kw.lower()
        if kw_l in blob:
            continue
        # Check synonym expansion
        syns = SYNONYM_MAP.get(kw_l, [])
        if any(s.lower() in blob for s in syns):
            continue
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
    tags_s = " ".join(str(x) for x in ((outfit_item or {}).get("标签") or []))
    blob = f"{cat} {title} {tags_s} {custom_scene or ''}"

    if custom_scene:
        scene_zh = custom_scene
        scene_en = custom_scene
    elif style_code == "ecommerce_kid" or "童" in blob:
        scene_zh = "阳光明媚的莫兰迪奶油风儿童生活美学馆或春日草坪花园网红打卡实景（85mm f/2.0 柔和光学浅景深虚化）"
        scene_en = "sunlit warm cream-toned kids lifestyle studio or sunny garden lawn with soft f/2.0 optical bokeh"
    elif outfit_type == "anime" or style_code in ("anime", "cel_anime", "semi_real"):
        if "地雷" in blob or "量产" in blob or "哥特" in blob:
            scene_zh = "东京涩谷/原宿黄昏霓虹街角与复古欧式雕花铁艺橱窗实景，梦幻柔焦光斑包裹"
            scene_en = "Tokyo Harajuku twilight street corner with vintage wrought-iron boutique window and dreamy neon bokeh"
        elif "天使界隈" in blob or "水色" in blob or "机能" in blob:
            scene_zh = "通透空灵的冰蓝水色系未来感透明落地窗展厅与柔和冷调空气感体积光"
            scene_en = "ethereal ice-blue futuristic glass showroom with soft cyan ambient volumetric light"
        elif "制服" in cat or "校园" in cat or "JK" in blob:
            scene_zh = "午后阳光斜射的日系樱花校园窗边走廊与蓝天白云远景，通透空气感丁达尔光束"
            scene_en = "sunlit Japanese high school corridor window with cherry blossoms and vibrant sky, volumetric light rays"
        elif "和服" in cat or "中华" in blob or "旗袍" in blob:
            scene_zh = "暮色暖光灯笼映照的东方古风木质回廊与庭院花窗景深"
            scene_en = "traditional oriental wooden corridor with warm glowing lanterns and garden window bokeh"
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
    elif "新中式" in blob or "宋锦" in blob or "马面裙" in blob or "盘扣" in blob:
        scene_zh = "江南苏式园林新中式茶空间与竹影花窗实景，午后温润暖阳透过木格花窗洒下斑驳光影（85mm f/1.8 浅景深）"
        scene_en = "modern Chinese Suzhou garden tea house with bamboo shadows and warm afternoon sunlight filtering through wooden lattice windows, 85mm f/1.8 bokeh"
    elif "美拉德" in blob or "巴恩风" in blob or "麂皮" in blob:
        scene_zh = "秋日午后4点暖金斜阳下的上海武康路/安福路梧桐落叶红砖街角与复古咖啡馆外摆区（浓郁美拉德电影感浅景深）"
        scene_en = "golden hour autumn Wukang Road plane-tree street corner with vintage red-brick cafe patio and warm Maillard cinematic bokeh"
    elif "千金" in blob or "汉南洞" in blob or "小香风" in blob or "老钱" in blob:
        scene_zh = "首尔汉南洞/巴黎蒙田大道高奢设计师买手店旋转石阶与暖光落地橱窗实景（高级静奢光影包裹）"
        scene_en = "Seoul Hannam-dong luxury designer boutique marble staircase and warm floor-to-ceiling window daylight with quiet-luxury bokeh"
    elif "芭蕾" in blob or "Balletcore" in blob or "纯欲" in blob:
        scene_zh = "法式奶油风阳光艺术画廊与落地白纱窗景，柔和漫反射晨光勾勒清透冷白皮与发丝高光"
        scene_en = "French cream-toned sunlit art studio with sheer white curtains and soft diffused daylight wrapping around skin and hair"
    elif "辣妹" in blob or "甜酷" in blob or "Y2K" in blob:
        scene_zh = "潮流买手街区阳光涂鸦水泥墙面与工业风金属街角实景（高反差自然阳光与鲜活街拍空气感）"
        scene_en = "trendy urban fashion district sunlit concrete and brushed-metal street corner with crisp natural daylight and shallow depth of field"
    elif "泳装" in cat or "度假" in cat or "比基尼" in blob:
        scene_zh = "阳光明媚的海岛奢华度假酒店无边泳池畔与椰林阳光露台（清澈水波光斑与碧海浅景深）"
        scene_en = "sun-drenched luxury tropical resort infinity pool deck with palm shadows and sparkling water reflections"
    elif "派对" in cat or "礼服" in cat or "晚礼" in blob:
        scene_zh = "高级微醺香槟金法式晚宴厅与水晶壁灯柔和暖色散景（Cinematic warm bokeh）"
        scene_en = "luxurious champagne-gold evening gala hall with warm crystal chandelier bokeh and ambient glow"
    elif "居家" in cat or "睡衣" in cat or "内搭" in cat or "内衣" in cat:
        scene_zh = "清晨第一缕暖阳透过白纱帘洒入的极简原木奶油风卧室与亚麻软装实景"
        scene_en = "cozy minimalist cream-toned bedroom with soft morning sunlight filtering through sheer white curtains"
    elif "通勤" in cat or "职场" in cat or "西装" in blob or "知识分子" in blob:
        scene_zh = "现代极简建筑感落地窗CBD写字楼艺术长廊与高级设计书店买手空间实景（85mm f/1.8 浅景深）"
        scene_en = "modern architectural glass-walled CBD gallery office and high-end minimalist bookstore boutique with f/1.8 shallow depth of field"
    elif "运动" in cat or "瑜伽" in blob or "健身" in blob or "网球" in blob or "Alo" in blob:
        scene_zh = "阳光通透的加州风户外红土/绿茵网球场边或全景落地窗现代普拉提生活馆实景"
        scene_en = "sunlit California-style outdoor tennis court club or floor-to-ceiling window modern Pilates studio"
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
        scene_zh = "小红书高赞网红打卡街角咖啡馆外摆区与阳光梧桐街景（85mm f/1.8 真实光学浅景深）"
        scene_en = "viral Xiaohongshu aesthetic sunlit street corner cafe patio with plane-tree shadows and 85mm f/1.8 optical bokeh"

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

    print(
        json.dumps(
            result_payload,
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
        description="AI Pose & Outfit Reference Studio CLI (Commercial v1.5.0)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="Show catalog statistics, categories, and 16 style presets")

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
    p_detail.add_argument("ids", nargs="+", help="Asset IDs (e.g. xhs_viral_P001_diag XHS-0001 charadb-XHS01)")

    p_random = sub.add_parser("random", help="Randomly pick assets from catalog")
    p_random.add_argument("--type", choices=["all", "pose", "costume", "anime", "portrait"], default="all")
    p_random.add_argument("--category", "-c", type=str, default=None)
    p_random.add_argument("--query", "-q", type=str, default="")
    p_random.add_argument("--count", "-n", type=int, default=3)

    p_fetch = sub.add_parser("fetch", help="Resolve or download asset image(s) to local cache")
    p_fetch.add_argument("ids", nargs="+", help="One or more Asset IDs (e.g. xhs_viral_P001_diag)")
    p_fetch.add_argument("--type", choices=["pose", "costume", "anime", "portrait"], default=None)
    p_fetch.add_argument("--depth", action="store_true", help="Fetch ControlNet depth map (for pose)")
    p_fetch.add_argument("--flip", action="store_true", help="Horizontally flip the fetched image")
    p_fetch.add_argument("--resize-mode", choices=["original", "crop", "pad"], default="original")
    p_fetch.add_argument("--out-dir", type=str, default=None, help="Optional directory to save processed image(s)")

    p_recipe = sub.add_parser("recipe", help="Create 3-in-1 composite reference image & bilingual prompt")
    p_recipe.add_argument("--auto", "-a", type=str, default=None, help="One-shot natural language query to auto-select portrait, costume, and pose in 0.2s")
    p_recipe.add_argument("--portrait", type=str, default=None, help="Portrait ID, keywords (e.g. '网红 高颅顶 大波浪'), or local image path")
    p_recipe.add_argument("--costume", type=str, default=None, help="Costume/Anime ID, keywords (e.g. '小红书 美拉德 巴恩风'), or local image path")
    p_recipe.add_argument("--pose", type=str, default=None, help="Pose ID, keywords (e.g. '抖音 松弛感 回眸'), or local image path")
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
