# 生图提示词指南

## 基本结构

一个好的场景提示词按这个顺序写，用英文效果最稳定（中文/日文也可以，但细节控制差一些）：

1. **主体**：画面里是什么、在做什么（`an engineer reviewing a car dashboard on a tablet`）
2. **构图**：景别、视角、主体位置（`wide shot, subject on the left third, empty space on the right`）
3. **环境**：场景、时间、氛围（`bright modern office, morning light`）
4. 风格、配色、光线 —— **交给 `--style` 预设**，场景提示词里不要重复写，保证整片统一

## 一致性

- 一个视频只用一个 style 预设。需要品牌色时，在 `styles.json` 新增预设并写明 hex 色值。
- 同一角色/产品出现在多个镜头：先生成一张"定妆图"，之后每个镜头用 `--ref 定妆图.png`，并在提示词里写 `the same character as in the reference image`。
- 局部修改用图生图：`--ref 原图.png --prompt "Keep everything the same, but change the background to a night city"`。

## 不要让模型画文字

图像模型画中文、日文经常出现错字或乱码。规则：

- 所有预设的 suffix 都带 `No text, no letters`。
- 标题、字幕、数字、Logo 全部由 Remotion 叠加。
- 需要留出叠字空间时，在构图里写明（`leave the upper third empty for a headline`）。

## 尺寸与比例

- 支持的比例：`1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9`
- 横屏视频 `16:9`，竖屏短视频 `9:16`。
- `--size 2K/4K` 只有 HQ 模型支持（`--hq`），成本更高，只在最终版或需要放大裁切时使用。

## 成本控制

- 每张图都是一次计费调用。先用默认模型出草稿，用户确认构图后再用 `--hq` 出终稿。
- `ai-video-pipeline` 的 `build_assets.py` 会缓存：提示词没变就不会重新生成。

## 合规

- 不生成真实人物（名人、员工）的肖像，除非对方书面同意。
- 不模仿在世艺术家的个人画风，不使用他人商标。
- 商用前确认 Gemini API 的生成内容使用条款。
