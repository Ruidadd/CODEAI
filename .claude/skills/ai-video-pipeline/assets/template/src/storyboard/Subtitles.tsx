import { useCurrentFrame } from "remotion";

const CJK = /[\u3040-\u30ff\u3400-\u9fff\uff00-\uffef]/;
const SENTENCE_END = /(?<=[。！？；])|(?<=[.!?;])\s+/;
const CLAUSE_END = /(?<=[、，,：:])/;
const TRAILING_PUNCT = /[。．、，,]+$/;

// Pacing limit per subtitle card; longer chunks still wrap visually.
const maxChars = (cjk: boolean, portrait: boolean) =>
  cjk ? (portrait ? 14 : 24) : portrait ? 36 : 64;

const hardWrap = (text: string, limit: number): string[] => {
  const out: string[] = [];
  for (let i = 0; i < text.length; i += limit) {
    out.push(text.slice(i, i + limit));
  }
  return out;
};

export const splitSubtitle = (text: string, portrait: boolean): string[] => {
  const cjk = CJK.test(text);
  const limit = maxChars(cjk, portrait);
  const chunks: string[] = [];
  for (const sentence of text.split(SENTENCE_END)) {
    const trimmed = sentence.trim();
    if (!trimmed) continue;
    if (trimmed.length <= limit) {
      chunks.push(trimmed);
      continue;
    }
    // Greedily pack clauses into chunks that fit the limit.
    let current = "";
    for (const clause of trimmed.split(CLAUSE_END)) {
      if ((current + clause).length > limit && current) {
        chunks.push(current.trim());
        current = "";
      }
      current += clause;
    }
    if (current.trim()) {
      chunks.push(...(current.length > limit * 1.5 ? hardWrap(current.trim(), limit) : [current.trim()]));
    }
  }
  return chunks.map((c) => (cjk ? c.replace(TRAILING_PUNCT, "") : c));
};

type Props = {
  readonly text: string;
  readonly startFrame: number;
  readonly endFrame: number;
  readonly lang: string;
  readonly portrait: boolean;
  readonly unit: number;
};

export const Subtitles: React.FC<Props> = ({ text, startFrame, endFrame, portrait, unit }) => {
  const frame = useCurrentFrame();
  if (frame < startFrame || frame >= endFrame) {
    return null;
  }
  const chunks = splitSubtitle(text, portrait);
  // Give each chunk screen time proportional to its length.
  const weights = chunks.map((c) => Math.max(1, c.replace(/\s/g, "").length));
  const total = weights.reduce((a, b) => a + b, 0);
  const position = ((frame - startFrame) / Math.max(1, endFrame - startFrame)) * total;
  let acc = 0;
  let current = chunks[chunks.length - 1] ?? "";
  for (let i = 0; i < chunks.length; i++) {
    acc += weights[i];
    if (position < acc) {
      current = chunks[i];
      break;
    }
  }

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: portrait ? "18%" : "7%",
        display: "flex",
        justifyContent: "center",
        padding: `0 ${(portrait ? 40 : 60) * unit}px`,
      }}
    >
      <div
        style={{
          maxWidth: portrait ? "94%" : "86%",
          padding: `${12 * unit}px ${28 * unit}px`,
          borderRadius: 12 * unit,
          backgroundColor: "rgba(0, 0, 0, 0.6)",
          color: "white",
          fontSize: (portrait ? 50 : 46) * unit,
          fontWeight: 600,
          lineHeight: 1.4,
          textAlign: "center",
          // Even out line lengths so a wrapped line never ends with one orphan character.
          textWrap: "balance",
        }}
      >
        {current}
      </div>
    </div>
  );
};
