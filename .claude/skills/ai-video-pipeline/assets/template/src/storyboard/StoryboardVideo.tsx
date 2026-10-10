import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Composition,
  Series,
  staticFile,
  useVideoConfig,
} from "remotion";
import { Scene } from "./Scene";
import type { Manifest } from "./types";

type Props = {
  readonly manifestPath: string;
  readonly manifest?: Manifest;
};

// Duration, size and fps all come from the manifest, so re-running
// build_assets.py is enough to retime the video.
const calculateMetadata: CalculateMetadataFunction<Props> = async ({
  props,
  abortSignal,
}) => {
  const response = await fetch(staticFile(props.manifestPath), {
    signal: abortSignal,
  });
  if (!response.ok) {
    throw new Error(
      `Cannot load public/${props.manifestPath}. Run build_assets.py first.`,
    );
  }
  const manifest = (await response.json()) as Manifest;
  return {
    durationInFrames: Math.max(1, manifest.totalFrames),
    fps: manifest.fps,
    width: manifest.width,
    height: manifest.height,
    props: { ...props, manifest },
  };
};

export const StoryboardComposition: React.FC = () => {
  return (
    <Composition
      id="StoryboardVideo"
      component={StoryboardVideo}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ manifestPath: "demo/manifest.json" }}
      calculateMetadata={calculateMetadata}
    />
  );
};

export const StoryboardVideo: React.FC<Props> = ({ manifest }) => {
  const { fps } = useVideoConfig();
  if (!manifest) {
    return null;
  }
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }} lang={manifest.lang}>
      <Series>
        {manifest.scenes.map((scene, index) => (
          <Series.Sequence
            key={scene.id}
            name={scene.id}
            durationInFrames={scene.durationInFrames}
            premountFor={fps}
          >
            <Scene scene={scene} index={index} lang={manifest.lang} />
          </Series.Sequence>
        ))}
      </Series>
      {manifest.bgm ? (
        <Audio
          name="BGM"
          src={staticFile(manifest.bgm)}
          volume={manifest.bgmVolume}
          loop
        />
      ) : null}
    </AbsoluteFill>
  );
};
