---
name: ai-pose-outfit-studio
display_name: AI人像姿势与穿搭造型工坊
display_name_en: AI Pose & Outfit Reference Studio
description: 内置4911+组100%原创3D动作姿势白模（含单人/双人正面、侧面、斜侧、俯视、仰视5机位、1489+张ControlNet深度图及抖音/小红书网红爆款街拍姿势）、四季时装与网红爆款穿搭人台、二次元亚文化潮服设定集、正脸网红妆造发型模特全量参考库（支持每日自动增量扩充），支持多维检索、0.2秒一键合成三合一参考拼图、Scene-First三维实景光影融合与商业级穿搭大片极速直出。触发词：姿势参考、人像姿势、3D白模、穿搭参考、网红穿搭、小红书穿搭、抖音街拍、模特换装、二次元服装设定、发型参考、三合一拼图、电商模特套图、pose studio。
description_zh: 提供4911+组原创3D动作白模（含5机位、ControlNet深度图与抖音/小红书网红街拍姿势）、四季与网红爆款穿搭人台、二次元设定与正脸发型库，0.2秒合成三合一参考板并直出商业级人像穿搭大片。
description_en: Complete 4,911+ original 3D pose mannequins (5 angles, ControlNet depth maps & viral Douyin/Xiaohongshu street poses), full-category & influencer outfits, anime costume sheets, and portrait hairstyle models with 0.2s 3-in-1 reference stitching and Scene-First photorealistic generation.
version: 1.6.0
author: "tcccE"
allowed-tools: Bash, Read, ViewImage, ImageGen, present_files
examples_zh:
- "帮我搭一套小红书爆款美拉德巴恩风穿搭、高颅顶大波浪网红模特和松弛感45度回眸姿势，合成三合一参考图并直接生成街拍大片"
- "检索5机位全套『抖音辣妹交叉腿摸胯』或『街角台阶伸腿坐姿』3D白模与Depth深度图，生成角色动作参考拼图与双语提示词"
- "我想要一套地雷系或天使界隈风格的二次元网红穿搭立绘，帮我从库里配好服装人台、发型和姿势并出图"
examples_en:
- "Pick a viral Xiaohongshu Maillard barn-jacket outfit, a high-cranial-top wavy-hair model, and an effortless look-back pose to generate a street snap"
- "Search 5-angle influencer sitting poses with depth maps and export the 3D mannequin reference sheet and bilingual prompts"
- "Create a Jirai-kei or Tenshi-kaiwai anime character illustration by combining a costume sheet, twin-tail hairstyle, and pose"
---

# AI 人像姿势与穿搭造型工坊 (AI Pose & Outfit Reference Studio)

本技能提供一套涵盖 **「正脸发型模特 (`portrait`) + 四季与抖音/小红书网红穿搭 (`costume`) + 二次元与亚文化潮服设定 (`anime`) + 5机位3D动作白模/深度图 (`pose`)」** 的三合一视觉参考与角色生成工作台，并支持每日自动从抖音、小红书趋势扩充最新网红感姿势与爆款衣服。详细分类体系与 16 种画风预设说明请参见 @references/catalog-guide.md 。

---

## 核心执行流程

当用户提出寻找姿势参考、搭配网红/电商服装造型、拼装多图参考配方或生成特定动作/穿搭的人物图片时，按以下步骤执行：

### 第一步：单指令 0.2 秒三合一参考拼图合成 (`recipe`)

- **【极速直出推荐】无需先运行 `search` 查 ID！** `recipe` 原生支持直接传入**自然语言关键词**（内置抖音/小红书网红热词与同义词自动展开，如「网红/小红书/抖音/松弛感/美拉德/巴恩风/纯欲/辣妹/千金/老钱风/知识分子/芭蕾风/新中式/潮童/地雷系/天使界隈」）、**精确图库 ID** 或**用户上传的本地图片路径**，0.2 秒一步到位完成匹配与三合一拼图合成：

```bash
python "<SKILL_DIR>/scripts/studio_cli.py" recipe \
  --portrait "<人像关键词 / ID / 本地图片路径，如：网红 高颅顶 大波浪>" \
  --costume "<服装关键词 / ID / 本地图片路径，如：小红书 美拉德 巴恩风>" \
  --pose "<姿势关键词 / ID / 本地图片路径，如：抖音 松弛感 回眸>" \
  --style <influencer_ootd|realistic|fashion|film|ecommerce_adult|ecommerce_kid|flatlay_to_model|anime|cel_anime|semi_real|concept_sheet|render3d|chibi_box|manga|cyberpunk> \
  [--subject "自定义人物描述，如：年轻女性时尚博主 / 5岁中国女童模特"] \
  [--scene "可选自定义场景；若不传则自动根据穿搭风格匹配武康路梧桐街角/汉南洞买手店/江南茶空间等真实实景与全局光影"]
```

- 该命令内置 **Scene-First 实景环境与全局光影融合引擎 (`build_smart_scene_and_lighting`)**，会自动根据穿搭品类与网红风格推导匹配的真实三维实景、环境主光源色温、发丝边缘逆光（Rim Light）、脚底地面接触阴影（Contact Shadow）与 85mm f/1.8 光学浅景深，彻底消除“人物与背景割裂像抠图”的问题。

### 第二步：联动生图与交付展示 (`ImageGen` + `present_files`)

1. 若用户希望**直接看到最终生成的人物穿搭/立绘成片**，可在第 1 回合并行调用 `recipe` 与 `ToolSearch(tool_names=["ImageGen"])`，随后直接调用 `ImageGen`（`image1` 传入 `composite_image` 路径，`prompt` 完整传入 `prompt_zh`，`quality` 默认传 `"medium"` 以兼顾商业级高清画质与最快生成速度）。
2. 将生成的**最终实景成片**与**三合一参考拼图**通过 `present_files` 一并展示给用户。

### 附：按需检索或单图拉取 (`search` / `stats` / `fetch`)

当用户仅需浏览图库目录或单独提取某张 3D 白模 / Depth 深度图时：

```bash
# 1. 查看图库统计与 16 种画风预设
python "<SKILL_DIR>/scripts/studio_cli.py" stats

# 2. 按关键词、类型、分类、机位角度或发长检索
python "<SKILL_DIR>/scripts/studio_cli.py" search <关键词> --type <all|pose|costume|anime|portrait> [--category <分类>] [--angle <正面|斜侧|侧面|俯视|仰视>] --limit 12

# 3. 拉取单张或多张白模 / ControlNet 深度图 (--depth)
python "<SKILL_DIR>/scripts/studio_cli.py" fetch <ID_1> <ID_2> [--depth] [--flip] [--resize-mode <original|crop|pad>]
```
