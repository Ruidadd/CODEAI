// Shape of public/<id>/manifest.json, written by build_assets.py.

export type SceneData = {
  readonly id: string;
  readonly title?: string | null;
  readonly subtitle: string;
  readonly image: string;
  readonly audio: string;
  readonly audioSec: number;
  readonly from: number;
  readonly durationInFrames: number;
  readonly audioStartFrame: number;
};

export type Manifest = {
  readonly id: string;
  readonly title: string;
  readonly lang: string;
  readonly fps: number;
  readonly width: number;
  readonly height: number;
  readonly bgm?: string | null;
  readonly bgmVolume: number;
  readonly placeholder: boolean;
  readonly totalFrames: number;
  readonly scenes: SceneData[];
};

// Japanese and Chinese share code points but use different glyph shapes,
// so the font order depends on the language.
const FONT_STACKS: Record<string, string> = {
  ja: '"Noto Sans JP", "Noto Sans CJK JP", "Hiragino Sans", "Yu Gothic", Meiryo, IPAGothic, sans-serif',
  zh: '"Noto Sans SC", "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "WenQuanYi Zen Hei", sans-serif',
  en: 'Inter, "Helvetica Neue", Arial, sans-serif',
};

export const fontFamilyFor = (lang: string): string => FONT_STACKS[lang] ?? FONT_STACKS.en;
