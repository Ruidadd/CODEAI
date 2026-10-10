# storyboard.json 格式

`build_assets.py` 读取它生成素材，Remotion 模板读取它产出的 `manifest.json`。完整示例见 `assets/storyboard.example.json`。

## 顶层字段

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `id` | ✓ | | 素材目录名，输出到 `public/<id>/`。只用小写字母、数字、连字符 |
| `scenes` | ✓ | | 场景数组，按播放顺序 |
| `title` | | `id` | 作品标题（仅记录用） |
| `lang` | | 自动判断 | `zh` / `ja` / `en`，决定默认声音、发音词典、字幕字体 |
| `fps` | | 30 | |
| `width` / `height` | | 1920 / 1080 | 竖屏用 1080 / 1920。生图比例自动取最接近的 |
| `style` | | 无 | `gemini-media/styles.json` 里的预设名，整片统一 |
| `voice` | | 按语言默认 | Gemini 预置声音名 |
| `voiceStyle` | | 无 | 语气说明，和旁白用同一语言 |
| `pronunciation` | | 无 | 本项目的额外发音词典 JSON（相对 storyboard 的路径） |
| `headPadSec` / `tailPadSec` | | 0.4 / 0.6 | 每个场景旁白前后留白（秒） |
| `bgm` | | null | 背景音乐，相对 Remotion `public/` 的路径，如 `bgm/calm.mp3` |
| `bgmVolume` | | 0.12 | 背景音乐音量 0–1 |

## 场景字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | ✓ | 唯一，如 `s01`。用于文件名和 `--only` |
| `narration` | ✓ | 旁白原文（TTS 前会套用发音词典，字幕保持原文） |
| `imagePrompt` | ✓ | 英文画面描述：主体 → 构图 → 环境。不写风格、不要求画文字 |
| `title` | | 画面左上角的标题卡，留空则不显示 |
| `subtitle` | | 字幕文本，默认等于 `narration` |
| `refs` | | 参考图路径数组（相对 storyboard），用于角色/产品一致 |
| `minSec` | | 场景最短时长，旁白很短时用来留出画面停留 |
| `style` / `voice` / `voiceStyle` / `lang` | | 覆盖顶层设置（一般不需要） |

## 写分镜的经验值

| 语言 | 语速（估算） | 每个场景旁白长度（8–15 秒） |
|---|---|---|
| 日文 | 约 7 字/秒 | 55–100 字 |
| 中文 | 约 4.5 字/秒 | 35–70 字 |
| 英文 | 约 2.6 词/秒 | 20–40 词 |

- 一个场景只讲一个要点，一张图。
- 标题卡控制在 16 个汉字/假名以内，横屏一行放得下。
- 1 分钟视频大约 5–7 个场景；第一个场景 3 秒内要抓住注意力。
- 结尾场景放行动号召（官网、联系方式），文字由标题卡显示，不要让模型画。

## manifest.json（自动生成，不要手改）

`build_assets.py` 写入 `public/<id>/manifest.json`，包含每个场景的 `from`、`durationInFrames`、`audioStartFrame`、`audioSec` 和素材路径。场景时长 = max(`minSec`, 前留白 + 旁白时长 + 后留白)。要调整节奏，改 storyboard 后重新运行脚本（缓存会跳过没变的素材）。
