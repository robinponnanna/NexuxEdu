import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { SceneData } from "../compositions/MicroLessonComposition";

interface SceneProps {
  scene: SceneData;
  lessonTitle: string;
  sceneIndex: number;
  totalScenes: number;
}

export const CommonMistakeScene: React.FC<SceneProps> = ({ scene, lessonTitle, sceneIndex, totalScenes }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const progressPct = (frame / durationInFrames) * 100;

  return (
    <div style={{ opacity, width: "100%", height: "100%", padding: "28px 40px", boxSizing: "border-box", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #334155", paddingBottom: "12px", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ background: "#EF4444", color: "#FFFFFF", padding: "4px 10px", borderRadius: "6px", fontSize: "14px", fontWeight: 700 }}>EXAM WARNING</span>
            <span style={{ color: "#94A3B8", fontSize: "16px" }}>{lessonTitle}</span>
          </div>
          <span style={{ color: "#94A3B8", fontSize: "16px" }}>Scene {sceneIndex + 1} of {totalScenes}</span>
        </div>

        <span style={{ color: "#F87171", fontSize: "14px", fontWeight: 700, textTransform: "uppercase" }}>FREQUENT EXAM PITFALL</span>
        <h1 style={{ fontSize: "32px", color: "#F8FAFC", margin: "6px 0 16px 0" }}>{scene.title}</h1>

        <div style={{ background: "#450A0A", border: "1px solid #991B1B", borderRadius: "12px", padding: "24px", color: "#FEE2E2", fontSize: "20px", lineHeight: 1.6 }}>
          {scene.body || scene.narration}
        </div>
      </div>

      <div>
        {scene.key_takeaway && (
          <div style={{ background: "#7F1D1D", border: "1px solid #EF4444", borderRadius: "10px", padding: "14px 20px", marginBottom: "16px" }}>
            <div style={{ color: "#FCA5A5", fontSize: "12px", fontWeight: 700, textTransform: "uppercase" }}>Exam Defense Strategy</div>
            <div style={{ color: "#FFFFFF", fontSize: "18px", fontWeight: 600, marginTop: "4px" }}>{scene.key_takeaway}</div>
          </div>
        )}
        <div style={{ height: "6px", background: "#334155", borderRadius: "3px", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${progressPct}%`, background: "#EF4444" }} />
        </div>
      </div>
    </div>
  );
};
