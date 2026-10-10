---
name: ai-video-pipeline
description: End-to-end narrated video production — script and storyboard by Claude, images and voiceover by Gemini (gemini-media skill), assembly in Remotion with Ken Burns motion, title cards, timed subtitles and BGM, then self-check via rendered stills. Use when the user wants to make a video, explainer, promo, training video, product intro or short (TikTok/Reels/Shorts) from a topic or script, e.g. 做视频、做一个宣传片、培训视频、短视频、動画を作って、紹介動画、解説動画、ショート動画.
---

# AI 视频流水线：Claude × Gemini × Remotion

分工：**Claude** 写脚本和分镜、写代码、检查成片；**Gemini** 生成插图和配音（通过 `gemini-media` skill）；**Remotion** 负责合成动画、字幕和音画对齐。

```
需求 → storyboard.json → 用户确认 → build_assets.py（Gemini 出图和配音、测时长）
     → Remotion 模板读取 manifest → QA 截图自检 → 用户预览 → 渲染 MP4
```

下文命令都在视频项目目录里执行，先设置：

```bash
SKILL="$(git rev-parse --show-toplevel)/.claude/skills/ai-video-pipeline"
```

Remotion 本身的写法遵循 `remotion-best-practices` 系列 skill。

## 1. 明确需求

只问缺失的信息，能推断就不问：用途和受众、语言（中/日/英）、时长、横屏或竖屏、画面风格（`python3 $SKILL/../gemini-media/scripts/generate_image.py --list-styles` 列出预设）。

## 2. 写分镜

按 `references/storyboard-format.md` 写 `storyboard.json`，放在视频项目根目录。参考 `assets/storyboard.example.json`。

要点：每个场景一个要点、一张图；`imagePrompt` 用英文，**不要求模型画文字**；旁白长度按语速表控制。

**生成素材要花钱。先把分镜（场景数、每场景标题 + 旁白 + 画面描述）给用户确认，再调用 API。**

## 3. 准备 Remotion 项目

已有项目就跳过新建。推荐把视频项目放在仓库的 `videos/<name>/` 下。

```bash
cd videos
npx create-video@latest --yes --blank --no-tailwind <name>
cd <name>
rm -rf .git   # create-video 会 git init；在已有仓库里要删掉这个嵌套仓库
npx remotion add @remotion/media @remotion/bundler @remotion/renderer
cp -r $SKILL/assets/template/src/storyboard src/
mkdir -p scripts && cp $SKILL/assets/template/scripts/qa-stills.mjs scripts/
```

在 `src/Root.tsx` 注册（保留已有的 composition）：

```tsx
import { StoryboardComposition } from "./storyboard/StoryboardVideo";
// ...
<StoryboardComposition />
```

把 `src/storyboard/StoryboardVideo.tsx` 里 `defaultProps` 的 `manifestPath` 改成 `"<storyboard id>/manifest.json"`。确认 `out/` 在 `.gitignore` 里。

## 4. 生成素材

```bash
python3 $SKILL/scripts/build_assets.py storyboard.json --project .
```

- 没有 `GEMINI_API_KEY`，或想先低成本看节奏和版式：加 `--placeholder`（渐变色占位图 + 按字数估算时长的静音）。
- 只重做某几个场景：`--only s02,s05`；强制重做：`--force`。没改动的场景会走缓存。
- 终稿想要更高画质：`--hq-images`。
- 输出 `public/<id>/`：每个场景的图片、WAV、`manifest.json`。stdout 的 `qaFrames` 是每个场景的中间帧号。

## 5. 自检（交给用户之前必须做）

```bash
node scripts/qa-stills.mjs <id>/manifest.json out/qa
```

用 Read 工具逐张查看 `out/qa/*.png`，检查：
- 生成图：有没有乱码文字、畸形手指、和旁白不符、风格不统一
- 标题卡和字幕：有没有遮挡画面主体、折行是否难看、有没有超出画面
- 竖屏：主体在上 2/3，底部字幕区干净

有问题就改 storyboard（提示词、标题长度）后用 `--only` 重做。再用一句话试听配音时长和读音（`manifest.json` 的 `audioSec`），读错就加发音词典。

## 6. 预览与渲染

- 预览：`npx remotion studio`（用户能在浏览器里实时看并拖动时间线）。
- **只在用户明确要求时渲染**：
  ```bash
  npx remotion render StoryboardVideo out/<id>.mp4 --props='{"manifestPath":"<id>/manifest.json"}'
  ```
- 沙箱里下载浏览器失败时，加 `--browser-executable=<已安装的 Chromium>`（qa-stills 用环境变量 `REMOTION_BROWSER_EXECUTABLE`）。Claude Code 云环境里是 `/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell`。
- 渲染后用 `ffprobe` 确认时长、有音轨，再交付。

## 扩展

模板只覆盖"图片 + 旁白 + 标题 + 字幕"。需要更多效果时改 `src/storyboard/` 里的组件，写法查 `remotion-markup`：转场（`transitions.md`）、Logo 和片尾（`images.md`）、文字动画（`text-highlights.md`）、音效（`sfx.md`）。品牌字体用 `@remotion/google-fonts`（`google-fonts.md`）；默认用系统中文/日文字体。

## 许可与合规（交付前提醒用户）

- **Remotion**：个人、3 人以下公司、非营利组织免费；**4 人以上的公司商用需要购买 Remotion Company License**（https://www.remotion.dev/license）。
- **Gemini**：确认 API 条款允许生成内容商用；不生成真实人物肖像、不模仿真人声音。
- 投放平台要求标注 AI 生成内容的，按要求标注。
