---
name: ai-pose-outfit-studio
display_name: AI人像姿势与穿搭造型工坊
display_name_en: AI Pose & Outfit Reference Studio
description: 内置4785组100%原创3D动作姿势白模（含单人/双人正面、侧面、斜侧、俯视、仰视5机位与1439张ControlNet深度图）、四季时装与二次元设定集人台、正脸发型模特全量参考库，支持多维检索、一键合成三合一参考拼图、生成中英双语提示词并联动生图工具直出商业级人像穿搭大图。触发词：姿势参考、人像姿势、3D白模、穿搭参考、模特换装、二次元服装设定、发型参考、三合一拼图、电商模特套图、pose studio。
description_zh: 提供4785组原创3D动作白模（含5机位与1439张深度图）、四季全品类穿搭人台、二次元服装设定与正脸发型模特全量库，一键拼接三合一参考图并直出商业级人像穿搭大图。
description_en: Complete 4,785 original 3D pose mannequins (5 angles & 1,439 depth maps), full-category outfits, anime costume sheets, and portrait hairstyle models with 3-in-1 reference stitching and AI photo generation.
version: 1.3.0
author: "tcccE"
allowed-tools: Bash, Read, ViewImage, ImageGen, present_files
examples_zh:
- "帮我挑一套秋季风衣穿搭、一位清冷感长发模特和斜侧站姿，合成三合一参考图并直接生成写实街拍大片"
- "检索5机位全套『后仰坐姿』3D白模与Depth深度图，生成角色动作参考拼图与SD/Flux双语提示词"
- "我想要一套洛丽塔风格的二次元角色立绘，帮我从库里配好服装人台、双马尾发型和可爱手势并出图"
examples_en:
- "Pick an autumn trench coat outfit, a long-hair portrait model, and a quarter-view standing pose to generate a photorealistic fashion shot"
- "Search 5-angle sitting poses with depth maps and export the 3D mannequin reference sheet and bilingual prompts"
- "Create a Lolita style anime character illustration by combining a costume sheet, twin-tail hairstyle, and cute upper-body pose"
---

# AI 人像姿势与穿搭造型工坊 (AI Pose & Outfit Reference Studio)

本技能提供一套涵盖 **「正脸发型模特 (`portrait`) + 四季现实穿搭 (`costume`) + 二次元服装设定 (`anime`) + 5机位3D动作白模/深度图 (`pose`)」** 的三合一视觉参考与角色生成工作台。详细分类体系与 15 种画风预设说明请参见 @references/catalog-guide.md 。

---

## 核心执行流程

当用户提出寻找姿势参考、搭配服装造型、拼装多图参考配方或生成特定动作/穿搭的人物图片时，按以下步骤执行：

### 第一步：检索或抽样参考图 (`search` / `stats`)

通过 Bash 工具运行技能目录下的 `scripts/studio_cli.py`：

```bash
# 1. 查看图库统计与 15 种画风预设
python "<SKILL_DIR>/scripts/studio_cli.py" stats

# 2. 按关键词、类型、分类、机位角度或发长检索
python "<SKILL_DIR>/scripts/studio_cli.py" search <关键词> --type <all|pose|costume|anime|portrait> [--category <分类>] [--angle <正面|斜侧|侧面|俯视|仰视>] [--hair-len <短发|中发|中长发|长发>] --limit 12
```

- 若用户未指定具体单品，可加 `--random` 从对应分类中智能抽样推荐。

### 第二步：单图拉取或三合一参考拼图合成 (`fetch` / `recipe`)

1. **仅需单张或多张动作白模 / 深度图 / 穿搭参考图时 (`fetch`)**：
   ```bash
   python "<SKILL_DIR>/scripts/studio_cli.py" fetch <ID_1> <ID_2> [--depth] [--flip] [--resize-mode <original|crop|pad>]
   ```
   - `--depth`：将 3D 姿势白模一键切换为 ControlNet Depth 深度图；
   - `--flip`：水平镜像翻转参考图。

2. **需要组合「人物脸型 + 服装造型 + 动作姿势」并出片时 (`recipe` 一键极速配单)**：
   - **【极速直出推荐】无需先运行 `search` 查 ID！** `recipe` 原生支持直接传入**自然语言关键词**（内置同义词自动展开，如「风衣→大衣」「微卷→卷发」）、**精确图库 ID** 或**用户上传的本地图片路径**，0.2 秒一步到位完成匹配与三合一拼图合成：
   ```bash
   python "<SKILL_DIR>/scripts/studio_cli.py" recipe \
     --portrait "<人像关键词 / ID / 本地图片路径>" \
     --costume "<服装关键词 / ID / 本地图片路径>" \
     --pose "<姿势关键词 / ID / 本地图片路径>" \
     --style <realistic|fashion|film|ecommerce_adult|ecommerce_kid|flatlay_to_model|anime|cel_anime|semi_real|concept_sheet|render3d|chibi_box|manga|cyberpunk> \
     [--live] \
     [--subject "自定义人物描述，如：5岁中国女童模特"] \
     [--scene "可选自定义场景；若不传则自动根据服装季节与品类匹配真实实景与全局光影"]
   ```
   - 该命令内置 **Scene-First 实景环境与全局光影融合引擎 (`build_smart_scene_and_lighting`)**，会自动根据穿搭季节/品类推导匹配的真实三维实景、环境主光源色温、发丝边缘逆光（Rim Light）、脚底地面接触阴影（Contact Shadow）与 85mm f/1.8 光学浅景深，彻底消除“人物与背景割裂像抠图”的问题。
   - 若加上 `--live`，还会自动匹配同动作的相邻连续机位（如正面→斜侧30度），输出专供 **ChatGPT 实况图（Live Photo）** 与 **图生视频（VideoGen / 可灵 / 即梦）** 的 2.5 秒微动防崩坏指令。

### 第三步：联动生图与交付展示 (`ImageGen` + `present_files`)

1. 若用户希望**直接看到最终生成的人物穿搭/立绘成片**，可在第 1 回合并行调用 `recipe` 与 `ToolSearch(tool_names=["ImageGen"])`，随后直接调用 `ImageGen`（`image1` 传入 `composite_image` 路径，`prompt` 完整传入 `prompt_zh`，`quality` 默认传 `"medium"` 以兼顾商业级高清画质与最快生成速度）。
2. 生成完毕后，调用 `present_files` 将**最终生成成片**与**三合一参考拼图**一并展示给用户，并在回复中附上完整的复现参数与中英双语提示词。
