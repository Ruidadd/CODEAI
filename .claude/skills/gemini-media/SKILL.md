---
name: gemini-media
description: Generate images (text-to-image, image editing with reference images) and voiceover audio (TTS, single voice or 2-speaker dialog, Chinese/Japanese/English) with the Google Gemini API. Use whenever the user wants Claude to create a picture, illustration, thumbnail, background or character image, edit an existing image, or produce narration/voiceover/speech audio — e.g. 生成图片、画一张插图、做配音、旁白、朗读、画像生成、イラスト作成、ナレーション、音声合成、読み上げ, "generate an image", "text to speech". Also used by the ai-video-pipeline skill for video assets.
---

# Gemini 生图 + 配音

Claude 不能直接生成图像和声音，这个 skill 通过 Gemini API 补上这两块。脚本只依赖 Python 标准库。

## 前置条件

1. 环境变量 `GEMINI_API_KEY`（或 `GOOGLE_API_KEY`）。**绝不要让用户把 key 粘贴到对话或写进仓库文件**；缺 key 时告诉用户在运行环境里配置环境变量。
2. 网络能访问 `generativelanguage.googleapis.com`。云端沙箱里如果报 403 / 无法连接，告诉用户把这个域名加入环境的网络白名单。
3. 模型名会更新。第一次使用或报 "model not found" 时，运行
   `python3 scripts/list_models.py image tts` 确认可用模型，再更新 `config.json` 或用 `--model` 覆盖。

下文路径相对于本 skill 目录（`.claude/skills/gemini-media/`）。

## 生图

```bash
python3 scripts/generate_image.py --prompt "<英文场景描述>" --style corporate-flat --out <路径>.png
```

| 参数 | 说明 |
|---|---|
| `--style` | 风格预设（`--list-styles` 查看）。同一个作品始终用同一个预设 |
| `--aspect` | `16:9` / `9:16` / `1:1` 等，覆盖预设的比例 |
| `--ref 图片` | 参考图，可重复。用于图生图修改、保持角色/产品一致 |
| `--n 3` | 出多张备选（每张一次调用） |
| `--hq` / `--size 2K` | 高质量模型和高分辨率，成本更高，只用于终稿 |
| `--dry-run` | 只打印请求，不调用 API |

工作方式：
- 先读 `references/image-prompting.md`，按"主体 → 构图 → 环境"写提示词，风格交给预设。
- **不要让模型在图里画文字**（中日文常出现乱码）。文字用 Remotion/HTML 叠加。
- 生成后用 Read 工具查看图片，检查是否符合要求、有没有乱码文字或畸形手指，不合格就改提示词重画，再给用户看。
- 返回的格式可能是 JPEG，脚本会自动修正扩展名，以 stdout JSON 里的 `path` 为准。

## 配音

```bash
python3 scripts/tts.py --text "<台词>" --lang ja --voice Kore --style "落ち着いたトーンで読み上げてください" --out <路径>.wav
```

| 参数 | 说明 |
|---|---|
| `--lang zh/ja/en` | 不写则自动判断；决定默认声音和发音词典 |
| `--voice` | 预置声音，见 `references/voices.md` |
| `--style` | 用自然语言描述语气、语速，和正文用同一语言 |
| `--speakers A=Kore,B=Puck` | 两人对话，正文每行以 `A:` / `B:` 开头 |
| `--pron 文件.json` | 额外发音词典 `{"词": "读法"}` |
| `--text-file` | 长文本从文件读取 |

工作方式：
- 正式生成前，先用一句话分别试 2–3 个候选声音，让用户选。
- 缩写、公司名、人名读错时，加进 `pronunciation/<lang>.json`，**不要改字幕原文**。
- 输出是 24 kHz 单声道 WAV；stdout JSON 带 `duration_sec`，用于和画面对齐。
- 一段文本控制在一个场景的长度（约 15–40 秒）。长稿按段落拆开分别生成，失败时只需重做一段。

## 出错处理

| 现象 | 处理 |
|---|---|
| `No API key found` | 让用户配置环境变量，不要索要 key |
| `HTTP 403` / `Cannot reach` | 网络白名单或 key 权限问题，告诉用户具体域名 |
| `HTTP 404 ... model` | 用 `list_models.py` 找当前模型名 |
| `HTTP 429` | 已自动重试 3 次；仍失败说明配额不足，降低并发或稍后再试 |
| `No media in response (finishReason=SAFETY ...)` | 内容被安全策略拦截，改写提示词 |

## 合规提醒

- 不生成真实人物肖像、不克隆真人声音，除非本人同意。
- 生成内容商用前确认 Gemini API 条款；有 AI 生成内容标注要求的平台需按要求标注。
