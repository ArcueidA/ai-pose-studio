---
name: ai-pose-outfit-studio
display_name: AI人像姿势与穿搭造型工坊
display_name_en: AI Pose & Outfit Reference Studio
description: 内置4785组100%原创3D动作姿势白模（含单人/双人正面、侧面、斜侧、俯视、仰视5机位、1439张ControlNet深度图与288组动态实况预览图）、四季时装与二次元设定集人台、正脸发型模特全量参考库，支持多维检索、一键合成首尾帧三合一参考拼图、生成中英双语提示词、联动生图/生视频工具并打包真·Motion Photo实况照片。触发词：姿势参考、人像姿势、3D白模、穿搭参考、模特换装、二次元服装设定、发型参考、三合一拼图、电商模特套图、实况图、Live Photo、pose studio。
description_zh: 提供4785组原创3D动作白模（含5机位、1439张深度图与288组动态实况素材）、四季穿搭人台、二次元设定与正脸发型库，一键拼接首尾帧参考板并直出商业级人像穿搭大图与实况照片。
description_en: Complete 4,785 original 3D pose mannequins (5 angles, 1,439 depth maps & 288 animated live previews), full-category outfits, anime costume sheets, and portrait hairstyle models with start/end frame stitching and Motion Photo synthesis.
version: 1.5.0
author: "tcccE"
allowed-tools: Bash, Read, ViewImage, ImageGen, VideoGen, present_files
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

1. **仅需单张或多张动作白模 / 深度图 / 动态实况预览 / 穿搭参考图时 (`fetch`)**：
   ```bash
   python "<SKILL_DIR>/scripts/studio_cli.py" fetch <ID_1> <ID_2> [--depth] [--live-preview] [--flip] [--resize-mode <original|crop|pad>]
   ```
   - `--depth`：将 3D 姿势白模一键切换为 ControlNet Depth 深度图；
   - `--live-preview`：拉取该动作对应的 **3D 五机位循环动态实况预览图 (`assets/pose_live/*.webp`)**；
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
   - **【面向无原生实况功能的模型 · 首尾帧双锚点与实况打包 (`--live` & `pack-live`)】**：
     - 当加上 `--live` 时，`recipe` 会同时输出：
       1. `live_pose_preview_webp`：该动作的 3D 动态循环预览动图；
       2. `start_composite_image`（首帧三合一参考板）与 `end_composite_image`（保持人像与衣服 100% 不变、仅将第 3 栏姿势自动替换为相邻连续机位如 `_front -> _diag` 的**尾帧三合一参考板**）；
       3. `end_frame_prompt_zh`（尾帧成片专用提示词）与 `video_i2v_prompt_zh`（2.5 秒微动视频指令）。
     - 支持**三通道交付真·人物动作实况照片（Motion Photo）**：
       - **通道 1（最强推荐 · 本机 Codex `GPT-Image-2.6` 直出真·人物动作实况）**：若本机已登录 Codex（存在 `~/.codex/auth.json`），可直接一条命令调用最新 `gpt-image-2.6-sunburst`（高精锁脸版）或 `gpt-image-2.6-flare`（极速版）绘制 3×2 六帧连续人物动作序列（眨眼、微笑、抬手抚衣领/发丝、风吹衣摆），并自动完成 2D FFT 亚像素防抖对齐 + `ffmpeg minterpolate` 双向光流 24fps 补帧 + 单帧超清封面 XMP Motion Photo 合成：
         ```bash
         python "<SKILL_DIR>/scripts/studio_cli.py" codex-live --ref-image "<composite_image>" [--action "眨眼微笑、抬手轻抚衣领、微风吹拂长发与衣摆"]
         ```
       - **通道 2（通用生图模型 · 3×2 连续动作序列光流实况）**：对没有原生实况接口的模型（如内置 `ImageGen`），将 `composite_image` 与 `sprite_sheet_live_prompt_zh` 传给 `ImageGen` 生成 1 张 3×2 连续人物动作序列图后，运行：
         ```bash
         python "<SKILL_DIR>/scripts/studio_cli.py" pack-live --photo "<3x2序列图.png>" --sprite-sheet
         ```
         自动切分防抖、光流补帧并提取高清单人微笑帧作为封面，产出 `*_key_photo.png`、`*_live_preview.webp`、`*_live_action.gif`、`*_motion_live.mp4` 与真·实况照片 `*_motion_live.jpg`。
       - **通道 3（首尾帧 / `VideoGen` 实况合成）**：用 `ImageGen` 生成静态成片（或配合 `VideoGen` 生成微动 MP4）后运行：
         ```bash
         python "<SKILL_DIR>/scripts/studio_cli.py" pack-live --photo "<首帧成片.png>" [--end-photo "<尾帧成片.png>"] [--video "<微动视频.mp4>"]
         ```
         自动向 JPEG 注入 Google Camera / Android `MotionPhoto` 双标准 XMP 元数据并内嵌 MP4 视频流，产出小红书与手机相册原生点亮 `LIVE` 标的 `*_motion_live.jpg`。

### 第三步：联动生图与交付展示 (`ImageGen` + `present_files`)

1. 若用户希望**直接看到最终生成的人物穿搭/立绘成片**，可在第 1 回合并行调用 `recipe` 与 `ToolSearch(tool_names=["ImageGen"])`，随后直接调用 `ImageGen`（`image1` 传入 `composite_image` 路径，`prompt` 完整传入 `prompt_zh`，`quality` 默认传 `"medium"` 以兼顾商业级高清画质与最快生成速度）。
2. 若用户明确要求生成**动态实况图（Live Photo）**，在 `ImageGen` 出图后可继续调用 `pack-live`（或先调 `VideoGen` 再调 `pack-live`），并将生成的**最终实景成片**、**动态实况预览图 (`*_live_preview.webp` / `*_motion_live.jpg`)** 与**三合一参考拼图**通过 `present_files` 一并展示给用户。
