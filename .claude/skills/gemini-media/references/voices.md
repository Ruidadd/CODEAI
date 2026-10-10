# Gemini TTS 声音一览 / ボイス一覧

所有预置声音都支持中文、日文、英文等多语言，语言由文本自动判断。下表的特征是 Google 官方的一词描述，**实际听感请先用短句试听**（同一句话用 2–3 个候选声音各生成一次，让用户挑）。

| Voice | 特征 | Voice | 特征 |
|---|---|---|---|
| Zephyr | Bright 明亮 | Puck | Upbeat 轻快 |
| Charon | Informative 讲解型 | Kore | Firm 坚定 |
| Fenrir | Excitable 兴奋 | Leda | Youthful 年轻 |
| Orus | Firm 坚定 | Aoede | Breezy 轻松 |
| Callirrhoe | Easy-going 随和 | Autonoe | Bright 明亮 |
| Enceladus | Breathy 气声 | Iapetus | Clear 清晰 |
| Umbriel | Easy-going 随和 | Algieba | Smooth 顺滑 |
| Despina | Smooth 顺滑 | Erinome | Clear 清晰 |
| Algenib | Gravelly 沙哑 | Rasalgethi | Informative 讲解型 |
| Laomedeia | Upbeat 轻快 | Achernar | Soft 柔和 |
| Alnilam | Firm 坚定 | Schedar | Even 平稳 |
| Gacrux | Mature 成熟 | Pulcherrima | Forward 有冲劲 |
| Achird | Friendly 友好 | Zubenelgenubi | Casual 随意 |
| Vindemiatrix | Gentle 温和 | Sadachbia | Lively 活泼 |
| Sadaltager | Knowledgeable 博学 | Sulafat | Warm 温暖 |

## 按用途推荐

| 用途 | 候选 |
|---|---|
| 公司介绍、产品讲解（稳重） | Charon, Kore, Iapetus, Schedar |
| 培训课件、操作说明（亲切） | Achird, Vindemiatrix, Sulafat |
| 社交短视频（有活力） | Puck, Sadachbia, Laomedeia |
| 对话形式（2 人） | 一个稳重 + 一个轻快，例如 Kore + Puck |

## 控制语气

`--style` 用自然语言描述即可，写成与正文同语言效果最稳定：

- 中文：`用沉稳、专业的语气，语速稍慢地朗读`
- 日文：`落ち着いた、信頼感のあるトーンで、ややゆっくり読み上げてください`
- 英文：`Read in a warm, confident tone at a relaxed pace`

## 发音纠正

模型偶尔读错缩写、人名、公司名、多音字。不要改字幕，改发音词典：

- 通用词典：`pronunciation/{zh,ja,en}.json`（项目级共享）
- 单个项目：`--pron my-terms.json`

日文写成片假名/平假名读法；中文多音字可替换为同音字，英文缩写写成带空格的字母（`A P I`）。

## 输出格式

Gemini 返回 24 kHz、16-bit、单声道 PCM，`tts.py` 自动封装成 WAV。Remotion 可直接使用 WAV；如需 MP3：`ffmpeg -i in.wav -b:a 192k out.mp3`。
