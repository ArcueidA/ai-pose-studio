# AI Pose & Outfit Reference Studio (`ai-pose-studio`)

> **100% 原创自有版权 3D 动作白模 · 四季穿搭人台 · 二次元设定集 · 正脸发型模特参考资产库**  
> Author: **tcccE** | WorkBuddy Skill Package: `ai-pose-outfit-studio`

---

## 📦 资产库概览（100% 全量完结：4,785 组原创资产 + 1,439 张 ControlNet 深度图 = 6,224 个 WebP 文件）

| 模块 | 收录数量 | 规格与内容 | 资产路径 |
| :--- | :---: | :--- | :--- |
| **3D 姿势动作参考 (`pose`)** | **1,439 组 (100%)** | 全身标准系(365)+全身柔韧表现系(399)+上半身单人(400)+双人互动系(275)，含 5 大机位全满 | `assets/pose/*.webp` |
| **ControlNet 深度图 (`pose_depth`)** | **1,439 张 (100%)** | 与 1,439 组 3D 姿势白模 1:1 对应的深度图（Depth Map） | `assets/pose_depth/*.webp` |
| **现实全品类穿搭库 (`costume`)** | **1,407 套 (100%)** | 春(215)/夏(254)/秋(244)/冬(253)/派对礼服(48)/泳装度假(54)/居家内搭(199)/晚宴修身(140)全满 | `assets/costume/*.webp` |
| **二次元服装设定库 (`anime`)** | **440 套 (100%)** | 学院制服、女仆装、洛丽塔、奇幻战斗服、偶像演出服、和服汉服、泳装全系列大满贯 | `assets/anime/*.webp` |
| **正脸发型模特库 (`portrait`)** | **1,499 位 (100%)** | 短发(727)/中发(376)/中长发(260)/长发(136)全库大满贯 | `assets/portrait/*.webp` |

---

## 🚀 目录结构

```text
ai-pose-studio/
├── assets/                          # 云端高清 WebP 资产图床 (6,224 文件)
│   ├── pose/                        # 3D 姿势白模图 (900×1200 WebP)
│   ├── pose_depth/                  # ControlNet Depth 深度图
│   ├── costume/                     # 现实四季穿搭人台图
│   ├── anime/                       # 二次元服装设定图
│   └── portrait/                    # 人像发型与面部模特图
├── ai-pose-outfit-studio/           # WorkBuddy 开放平台标准 Skill 源码包
│   ├── SKILL.md                     # 技能主入口与工作流编排定义
│   ├── references/                  # 结构化中文索引与目录指南
│   │   ├── catalog-guide.md
│   │   ├── pose-zh.json
│   │   ├── costume-zh.json
│   │   ├── costume-anime-zh.json
│   │   └── portrait-zh.json
│   └── scripts/
│       └── studio_cli.py            # 检索、拼图合成与多通道 CDN 缓存 CLI
```

---

## 🛠️ 快速体验

```bash
# 1. 查看图库统计
python ai-pose-outfit-studio/scripts/studio_cli.py stats

# 2. 多维条件检索
python ai-pose-outfit-studio/scripts/studio_cli.py search 站姿 --type pose --angle 斜侧 --limit 5

# 3. 合成「姿势 + 服装 + 人像」三合一参考拼图与中英双语生图 Prompt
python ai-pose-outfit-studio/scripts/studio_cli.py recipe \
  --portrait f71f980dde3 \
  --costume SPR-0001 \
  --pose full_single_P001_front \
  --style fashion \
  --out ./composite_preview.png
```
