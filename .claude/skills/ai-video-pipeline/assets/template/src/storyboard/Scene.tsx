import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Subtitles } from "./Subtitles";
import { fontFamilyFor, type SceneData } from "./types";

const FADE_FRAMES = 12;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

type Props = {
  readonly scene: SceneData;
  readonly index: number;
  readonly lang: string;
};

export const Scene: React.FC<Props> = ({ scene, index, lang }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  // Sizes are authored for a 1080px short side and scale to any resolution.
  const unit = Math.min(width, height) / 1080;
  const duration = scene.durationInFrames;

  // Slow Ken Burns move; alternate the pan direction so cuts feel varied.
  const progress = frame / duration;
  const direction = index % 2 === 0 ? 1 : -1;
  const scale = interpolate(progress, [0, 1], [1.04, 1.12]);
  const panX = interpolate(progress, [0, 1], [-1.5 * direction, 1.5 * direction]);
  const opacity = interpolate(
    frame,
    [0, FADE_FRAMES, duration - FADE_FRAMES, duration],
    [0, 1, 1, 0],
    clamp,
  );

  const titleIn = spring({ frame: frame - 6, fps, config: { damping: 200 } });

  return (
    <AbsoluteFill style={{ fontFamily: fontFamilyFor(lang) }}>
      <AbsoluteFill style={{ opacity, overflow: "hidden" }}>
        <Img
          src={staticFile(scene.image)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale}) translateX(${panX}%)`,
          }}
        />
      </AbsoluteFill>

      {scene.title ? (
        <div
          style={{
            position: "absolute",
            top: 64 * unit,
            left: 72 * unit,
            maxWidth: width - 144 * unit,
            padding: `${18 * unit}px ${32 * unit}px`,
            borderRadius: 14 * unit,
            backgroundColor: "rgba(10, 20, 40, 0.72)",
            color: "white",
            fontSize: 64 * unit,
            fontWeight: 700,
            lineHeight: 1.25,
            opacity: titleIn * opacity,
            transform: `translateY(${(1 - titleIn) * -30 * unit}px)`,
          }}
        >
          {scene.title}
        </div>
      ) : null}

      <Subtitles
        text={scene.subtitle}
        startFrame={scene.audioStartFrame}
        endFrame={scene.audioStartFrame + Math.ceil(scene.audioSec * fps)}
        lang={lang}
        portrait={height > width}
        unit={unit}
      />

      <Audio
        name={`${scene.id} voice`}
        src={staticFile(scene.audio)}
        from={scene.audioStartFrame}
        premountFor={fps}
      />
    </AbsoluteFill>
  );
};
