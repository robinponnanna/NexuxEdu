import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { SceneData } from "../compositions/MicroLessonComposition";

interface SceneProps {
  scene: SceneData;
  lessonTitle: string;
  sceneIndex: number;
  totalScenes: number;
}

export const TakeawayScene: React.FC<SceneProps> = ({ scene, lessonTitle, sceneIndex, totalScenes }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const progressPct = (frame / durationInFrames) * 100;

  return (
    <div style={{ opacity, width: "100%", height: "100%", padding: "28px 40px", boxSizing: "border-box", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #334155", paddingBottom: "12px", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ background: "#10B981", color: "#FFFFFF", padding: "4px 10px", borderRadius: "6px", fontSize: "14px", fontWeight: 700 }}>MASTERY COMPLETE</span>
            <span style={{ color: "#94A3B8", fontSize: "16px" }}>{lessonTitle}</span>
          </div>
          <span style={{ color: "#94A3B8", fontSize: "16px" }}>Scene {sceneIndex + 1} of {totalScenes}</span>
        </div>

        <span style={{ color: "#34D399", fontSize: "14px", fontWeight: 700, textTransform: "uppercase" }}>SUMMARY & KNOWLEDGE CHECK</span>
        <h1 style={{ fontSize: "32px", color: "#F8FAFC", margin: "6px 0 16px 0" }}>{scene.title}</h1>

        <div style={{ background: "#064E3B", border: "1px solid #059669", borderRadius: "12px", padding: "24px", color: "#D1FAE5", fontSize: "20px", lineHeight: 1.6 }}>
          {scene.body || scene.narration}
        </div>
      </div>

      <div>
        {scene.key_takeaway && (
          <div style={{ background: "#065F46", border: "1px solid #10B981", borderRadius: "10px", padding: "14px 20px", marginBottom: "16px" }}>
            <div style={{ color: "#6EE7B7", fontSize: "12px", fontWeight: 700, textTransform: "uppercase" }}>Key Exam Takeaway</div>
            <div style={{ color: "#FFFFFF", fontSize: "18px", fontWeight: 600, marginTop: "4px" }}>{scene.key_takeaway}</div>
          </div>
        )}
        <div style={{ height: "6px", background: "#334155", borderRadius: "3px", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${progressPct}%`, background: "#10B981" }} />
        </div>
      </div>
    </div>
  );
};
