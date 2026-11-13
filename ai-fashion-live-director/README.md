# AI电商穿搭与实况出片总监（苏织意 / `ai-fashion-live-director`）

内置 **4,785 组 100% 原创 3D 动作白模（含 5 机位与 1,439 张 ControlNet 深度图）、四季全品类穿搭人台、二次元服装设定与正脸发型模特库**，一键合成三合一参考拼图并直出高转化电商模特主图与小红书/抖音 Live Photo 实况带货大片。

## 类型

Agent 型（单个 AI 专家） | 行业分类：`07-SalesCommerce`（销售商务 / 电商视觉）

## 核心功能

1. **4,785 组全量原创四维图库 + 1,439 张深度图**：
   - `pose`：1,439 组五机位（正面/斜侧/侧面/俯视/仰视）3D 动作白模 + 1:1 配套 ControlNet Depth 深度图
   - `costume`：1,407 套四季全品类现实穿搭无头人台目录图
   - `anime`：440 套 15 大类二次元服装设定集立绘
   - `portrait`：1,499 位短/中/中长/长发 85mm 定焦正脸模特
2. **平铺服装转真人模特上身 (`flatlay_to_model` / `ecommerce_adult` / `ecommerce_kid`)**：支持上传单件服装平铺图，搭配库内动作白模与模特脸型直接生成真人上身带货主图。
3. **三合一防串色参考拼图合成 (`recipe`)**：自动拉取云端 WebP 原图并合成带分栏标注的参考拼图，输出中英双语结构化提示词。
4. **Live Photo 实况微动与 5 机位连续首尾帧配方 (`--live`)**：自动匹配同一动作的相邻连续机位（如正面→斜侧 30°），生成专供 ChatGPT 实况图与图生视频工具的 2.5 秒微动防崩坏指令。

## 使用示例

- `"帮我挑一套秋季风衣穿搭、一位清冷感长发模特和斜侧站姿，合成三合一参考图并直出电商主图与实况微动配方"`
- `"帮我搭配一套适合抖音/小红书种草的童装街拍造型，匹配自然站姿白模，生成高转化童模实拍图与2.5秒实况图指令"`
- `"检索5机位全套『坐姿』3D白模与Depth深度图，搭配一套晚宴礼服人台，生成影棚级时尚画报与双语提示词"`

## 头像

头像已生成在 `avatars/expert.png`（512×512 PNG，符合 `≤500KB` 规范）。

## 安装与注册

将专家包目录放到专家目录下：

```text
~/.workbuddy/plugins/marketplaces/my-experts/plugins/ai-fashion-live-director/
```

运行注册命令使其在 WorkBuddy【专家中心 - 我的专家】中可见：

```bash
python3 scripts/register_expert.py ~/.workbuddy/plugins/marketplaces/my-experts/plugins/ai-fashion-live-director
```
