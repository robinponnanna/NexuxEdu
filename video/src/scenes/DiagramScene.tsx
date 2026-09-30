import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { SceneData } from "../compositions/MicroLessonComposition";

interface SceneProps {
  scene: SceneData;
  lessonTitle: string;
  sceneIndex: number;
  totalScenes: number;
}

export const DiagramScene: React.FC<SceneProps> = ({ scene, lessonTitle, sceneIndex, totalScenes }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const progressPct = (frame / durationInFrames) * 100;
  const visualData = scene.visual_data || {};
  const vType = scene.visual_type || scene.type;

  return (
    <div style={{ opacity, width: "100%", height: "100%", padding: "28px 40px", boxSizing: "border-box", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #334155", paddingBottom: "12px", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ background: "#0284C7", color: "#FFFFFF", padding: "4px 10px", borderRadius: "6px", fontSize: "14px", fontWeight: 700 }}>AI MICRO-LESSON</span>
            <span style={{ color: "#94A3B8", fontSize: "16px" }}>{lessonTitle}</span>
          </div>
          <span style={{ color: "#94A3B8", fontSize: "16px" }}>Scene {sceneIndex + 1} of {totalScenes}</span>
        </div>

        <span style={{ color: "#38BDF8", fontSize: "14px", fontWeight: 700, textTransform: "uppercase" }}>TECHNICAL VISUALIZATION • {vType?.toUpperCase()}</span>
        <h1 style={{ fontSize: "30px", color: "#F8FAFC", margin: "6px 0 16px 0" }}>{scene.title}</h1>

        <div style={{ background: "#1E293B", border: "1px solid #334155", borderRadius: "12px", padding: "20px", color: "#E2E8F0" }}>
          {vType === "table" && visualData.columns ? (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "18px" }}>
              <thead>
                <tr style={{ background: "#334155", textAlign: "left" }}>
                  {visualData.columns.map((col: string, i: number) => (
                    <th key={i} style={{ padding: "10px 14px", color: "#F8FAFC", fontWeight: 700 }}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(visualData.rows || []).map((row: any[], rIdx: number) => (
                  <tr key={rIdx} style={{ background: rIdx % 2 === 0 ? "#1E293B" : "#243248" }}>
                    {row.map((cell: any, cIdx: number) => (
                      <td key={cIdx} style={{ padding: "10px 14px", color: cIdx === 0 ? "#38BDF8" : "#CBD5E1" }}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : vType === "code" && visualData.code_snippet ? (
            <pre style={{ margin: 0, fontFamily: "monospace", fontSize: "17px", color: "#34D399", lineHeight: 1.5 }}>
              {visualData.code_snippet}
            </pre>
          ) : (
            <pre style={{ margin: 0, fontFamily: "monospace", fontSize: "16px", color: "#E2E8F0", lineHeight: 1.4 }}>
              {visualData.ascii_diagram || scene.body || scene.narration}
            </pre>
          )}
        </div>
      </div>

      <div>
        {scene.key_takeaway && (
          <div style={{ background: "#1E3A8A", border: "1px solid #3B82F6", borderRadius: "10px", padding: "12px 20px", marginBottom: "16px" }}>
            <div style={{ color: "#60A5FA", fontSize: "12px", fontWeight: 700, textTransform: "uppercase" }}>Core Takeaway</div>
            <div style={{ color: "#FFFFFF", fontSize: "17px", fontWeight: 600, marginTop: "4px" }}>{scene.key_takeaway}</div>
          </div>
        )}
        <div style={{ height: "6px", background: "#334155", borderRadius: "3px", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${progressPct}%`, background: "#0284C7" }} />
        </div>
      </div>
    </div>
  );
};
