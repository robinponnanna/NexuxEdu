"use client";

import React from "react";
import { ArrowRight, CheckCircle2, AlertCircle, Layers } from "lucide-react";

interface DiagramNode {
  id: string;
  label: string;
}

interface DiagramEdge {
  from: string;
  to: string;
  label?: string;
}

interface DiagramData {
  type?: string;
  nodes?: DiagramNode[];
  edges?: DiagramEdge[];
  diagram_title?: string;
  ascii_diagram?: string;
  highlights?: string[];
  columns?: string[];
  rows?: (string | number)[][];
}

interface DiagramRendererProps {
  data?: DiagramData | null;
  visualType?: string;
}

export const DiagramRenderer: React.FC<DiagramRendererProps> = ({ data, visualType }) => {
  if (!data && !visualType) {
    return null;
  }

  // Case 1: Table format
  if (data?.columns && data?.rows) {
    return (
      <div style={{ width: "100%", margin: "14px 0", overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            background: "var(--surface-elevated)",
            borderRadius: "8px",
            overflow: "hidden",
            border: "1px solid var(--surface-border)",
            fontSize: "0.84rem",
          }}
        >
          <thead>
            <tr style={{ background: "var(--surface-card)", borderBottom: "1px solid var(--surface-border)" }}>
              {data.columns.map((col, idx) => (
                <th
                  key={idx}
                  style={{
                    padding: "10px 14px",
                    textAlign: "left",
                    fontWeight: 700,
                    color: "var(--text-main)",
                    fontSize: "0.78rem",
                    letterSpacing: "0.03em",
                    textTransform: "uppercase",
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, rIdx) => (
              <tr
                key={rIdx}
                style={{
                  borderBottom: rIdx < data.rows!.length - 1 ? "1px solid var(--surface-border-subtle)" : "none",
                }}
              >
                {row.map((cell, cIdx) => (
                  <td
                    key={cIdx}
                    style={{
                      padding: "9px 14px",
                      color: cIdx === 0 ? "var(--text-main)" : "var(--text-muted)",
                      fontWeight: cIdx === 0 ? 600 : 400,
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Case 2: Flow diagram with structured nodes & edges
  if (data?.nodes && data.nodes.length > 0) {
    return (
      <div
        style={{
          background: "var(--surface-elevated)",
          border: "1px solid var(--surface-border)",
          borderRadius: "10px",
          padding: "20px",
          margin: "14px 0",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        {data.diagram_title && (
          <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-main)", display: "flex", alignItems: "center", gap: "6px" }}>
            <Layers size={15} color="var(--color-student)" />
            <span>{data.diagram_title}</span>
          </div>
        )}

        {/* Node Flow Representation */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "center",
            gap: "12px",
            padding: "10px 0",
          }}
        >
          {data.nodes.map((node, index) => {
            const isLast = index === data.nodes!.length - 1;
            const matchingEdge = data.edges?.find((e) => e.from === node.id);

            return (
              <React.Fragment key={node.id}>
                {/* Node Box */}
                <div
                  style={{
                    background: "var(--surface-card)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "8px",
                    padding: "10px 16px",
                    boxShadow: "var(--shadow-sm)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    minWidth: "160px",
                    maxWidth: "240px",
                    textAlign: "center",
                    position: "relative",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.68rem",
                      fontWeight: 700,
                      color: "var(--color-student)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      marginBottom: "4px",
                    }}
                  >
                    Step {index + 1}
                  </span>
                  <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-main)", lineHeight: 1.3 }}>
                    {node.label}
                  </span>
                </div>

                {/* Arrow Connector */}
                {!isLast && (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      color: "var(--text-dim)",
                      padding: "0 4px",
                    }}
                  >
                    <ArrowRight size={18} color="var(--color-student)" />
                    {matchingEdge?.label && (
                      <span style={{ fontSize: "0.68rem", color: "var(--text-dim)", marginTop: "2px" }}>
                        {matchingEdge.label}
                      </span>
                    )}
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    );
  }

  // Case 3: ASCII Diagram or Structured Visual Text
  if (data?.ascii_diagram) {
    return (
      <div
        style={{
          background: "#0F172A",
          color: "#E2E8F0",
          borderRadius: "8px",
          padding: "16px 18px",
          margin: "14px 0",
          fontFamily: "var(--font-mono)",
          fontSize: "0.78rem",
          lineHeight: 1.45,
          overflowX: "auto",
          boxShadow: "var(--shadow-sm)",
          border: "1px solid #334155",
        }}
      >
        {data.diagram_title && (
          <div style={{ color: "#93C5FD", fontWeight: 700, marginBottom: "10px", fontSize: "0.82rem" }}>
            // {data.diagram_title}
          </div>
        )}
        <pre style={{ margin: 0, fontFamily: "inherit", whiteSpace: "pre" }}>
          {data.ascii_diagram}
        </pre>
        {data.highlights && data.highlights.length > 0 && (
          <div style={{ marginTop: "12px", paddingTop: "10px", borderTop: "1px solid #334155" }}>
            {data.highlights.map((h, i) => (
              <div key={i} style={{ color: "#FDE68A", fontSize: "0.74rem", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>•</span>
                <span>{h}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return null;
};
