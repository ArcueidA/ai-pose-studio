# AI Pose & Outfit Reference Studio (`ai-pose-studio`)

> **100% 原创自有版权 3D 动作白模 · 四季穿搭人台 · 二次元设定集 · 正脸发型模特参考资产库**  
> Author: **tcccE** | WorkBuddy Skill Package: `ai-pose-outfit-studio`

---

## 📦 资产库概览（当前已收录 1,902 组原创资产 + 490 张 ControlNet 深度图）

| 模块 | 收录数量 | 规格与内容 | 资产路径 |
| :--- | :---: | :--- | :--- |
| **3D 姿势动作参考 (`pose`)** | **490 组** | 日常站姿/坐姿/动态/可爱系，含正面、侧面、斜侧面(3/4)、俯视、仰视 5 大机位 | `assets/pose/pose-XXXX.webp` |
| **ControlNet 深度图 (`pose_depth`)** | **490 张** | 与 490 组 3D 姿势白模 1:1 对应的深度图（Depth Map） | `assets/pose_depth/pose-XXXX.webp` |
| **现实四季穿搭库 (`costume`)** | **540 套** | 春季/夏季/秋季/冬季完整上下装+鞋履无头人台穿搭图与材质拆解 | `assets/costume/costume-XXXX.webp` |
| **二次元服装设定库 (`anime`)** | **440 套 (100%)** | 学院制服、女仆装、洛丽塔、奇幻战斗服、偶像演出服、和服汉服、泳装全系列 | `assets/anime/anime-XXXX.webp` |
| **正脸发型模特库 (`portrait`)** | **432 位** | 短发/中长发/长发/卷发/扎发/编发，含脸型、发色与微表情标签 | `assets/portrait/portrait-XXXX.webp` |

---

## 🚀 目录结构

```text
ai-pose-studio/
├── assets/                          # 云端高清 WebP 资产图床 (2,392 文件)
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
