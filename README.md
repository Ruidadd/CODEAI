# CODEAI
TRIAL FOR VIDE CODING

## Claude Code Skills：Claude × Gemini 视频制作

`.claude/skills/` 下的 skill 在 Claude Code 打开本仓库时自动加载。Claude 负责脚本、分镜、代码和成片检查，Gemini 负责生图和配音，Remotion 负责合成。

| Skill | 来源 | 作用 |
|---|---|---|
| `ai-video-pipeline` | 自制 | 主题 → 分镜 → 素材 → Remotion 合成 → QA 截图自检 → MP4 |
| `gemini-media` | 自制 | Gemini 生图（文生图、参考图编辑、风格预设）和 TTS 配音（中/日/英，单人/双人对话，发音词典） |
| `remotion-*`（12 个） | [remotion-dev/skills](https://github.com/remotion-dev/skills) 官方，固定在 commit `32b241b`（v4.0.534） | Remotion 写法、动画、字幕、渲染等最佳实践 |

### 快速开始

1. **配置 API key**：把 `GEMINI_API_KEY` 设为运行环境的环境变量（Claude Code 云环境：环境设置 → 环境变量）。不要写进仓库文件，也不要贴进对话。
2. **在 Claude Code 里直接说需求**，例如：
   - 「做一个 1 分钟的日语公司介绍视频，横屏，扁平商务风」
   - 「把这段脚本做成竖屏短视频，中文配音」
   - 「画一张等距 3D 风格的 SDV 概念图」
3. 没有 key 时，流水线可以用占位素材（`--placeholder`）先看节奏和版式。

### 目录

```
.claude/skills/
├── ai-video-pipeline/
│   ├── SKILL.md                       # 工作流程（Claude 读这个）
│   ├── scripts/build_assets.py        # storyboard.json → 图片 + 配音 + manifest.json（带缓存）
│   ├── assets/storyboard.example.json
│   ├── assets/template/               # Remotion 模板：StoryboardVideo、Scene、Subtitles、qa-stills.mjs
│   └── references/storyboard-format.md
├── gemini-media/
│   ├── SKILL.md
│   ├── config.json                    # 模型名（会更新，用 list_models.py 确认）
│   ├── styles.json                    # 画风预设：corporate-flat / isometric-tech / photo-real / anime-soft / whiteboard / vertical-short
│   ├── pronunciation/{zh,ja,en}.json  # 发音词典（只影响配音，不影响字幕）
│   ├── scripts/                       # generate_image.py / tts.py / list_models.py（仅依赖 Python 标准库）
│   └── references/                    # 声音一览、提示词指南
└── remotion-*/                        # Remotion 官方 skills（原样复制，未修改）
```

### 推荐另外安装（用户级插件）

- 开发工作流 [obra/superpowers](https://github.com/obra/superpowers)：`/plugin install superpowers@claude-plugins-official`
- Anthropic 官方文档类 skills（Word/PDF/PPT/Excel）：`/plugin marketplace add anthropics/skills`，然后 `/plugin install document-skills@anthropic-agent-skills`
- 需要 ElevenLabs、本地 TTS、AI 视频片段等更多能力时，可参考 [digitalsamba/claude-code-video-toolkit](https://github.com/digitalsamba/claude-code-video-toolkit)（MIT）

### 更新 Remotion skills

```bash
git clone --depth 1 https://github.com/remotion-dev/skills.git /tmp/remotion-skills
cp -r /tmp/remotion-skills/skills/* .claude/skills/
```

更新后检查 diff，并更新上表里的 commit。

### 许可与合规

- **Remotion**：个人、3 人以下的公司、非营利组织免费；**4 人以上的公司商用需要购买 [Company License](https://www.remotion.dev/license)**。评估试用阶段免费。
- **Gemini API**：生成内容商用前确认 Google 的条款；不生成真实人物肖像，不模仿真人声音。
- 投放平台要求标注 AI 生成内容的，按平台规则标注。
