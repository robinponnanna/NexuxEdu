import React from "react";
import { useCurrentFrame, useVideoConfig, Sequence, interpolate } from "remotion";
import { ConceptScene } from "../scenes/ConceptScene";
import { DiagramScene } from "../scenes/DiagramScene";
import { CommonMistakeScene } from "../scenes/CommonMistakeScene";
import { TakeawayScene } from "../scenes/TakeawayScene";

export interface SceneData {
  scene_id: number;
  title: string;
  duration_seconds: number;
  type?: string;
  visual_type?: string;
  narration?: string;
  body?: string;
  visual_data?: any;
  key_takeaway?: string;
}

export interface MicroLessonCompositionProps {
  lesson: {
    title: string;
    subject_code?: string;
    co_code?: string;
    scenes: SceneData[];
  };
}

export const MicroLessonComposition: React.FC<MicroLessonCompositionProps> = ({ lesson }) => {
  const { fps } = useVideoConfig();
  const scenes = lesson.scenes || [];

  let accumulatedFrames = 0;

  return (
    <div style={{ flex: 1, backgroundColor: "#0F172A", width: "100%", height: "100%", color: "#F8FAFC", fontFamily: "sans-serif" }}>
      {scenes.map((scene, idx) => {
        const sceneDurationFrames = Math.max(30, Math.round((scene.duration_seconds || 10) * fps));
        const fromFrame = accumulatedFrames;
        accumulatedFrames += sceneDurationFrames;

        const sceneType = scene.visual_type || scene.type || "concept";

        return (
          <Sequence key={scene.scene_id || idx} from={fromFrame} durationInFrames={sceneDurationFrames}>
            {sceneType === "common_mistake" ? (
              <CommonMistakeScene scene={scene} lessonTitle={lesson.title} sceneIndex={idx} totalScenes={scenes.length} />
            ) : sceneType === "takeaway" ? (
              <TakeawayScene scene={scene} lessonTitle={lesson.title} sceneIndex={idx} totalScenes={scenes.length} />
            ) : sceneType === "diagram" || sceneType === "table" || sceneType === "code" || sceneType === "flowchart" ? (
              <DiagramScene scene={scene} lessonTitle={lesson.title} sceneIndex={idx} totalScenes={scenes.length} />
            ) : (
              <ConceptScene scene={scene} lessonTitle={lesson.title} sceneIndex={idx} totalScenes={scenes.length} />
            )}
          </Sequence>
        );
      })}
    </div>
  );
};
