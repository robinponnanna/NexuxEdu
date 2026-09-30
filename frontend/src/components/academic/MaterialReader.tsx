"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Layers,
  FileText,
  AlertCircle,
  HelpCircle,
  CheckCircle,
  ArrowLeft,
  Loader2,
  Video,
} from "lucide-react";
import {
  ModuleLearningMaterialResponse,
  LearningMaterialDetail,
  MaterialPageDetail,
  AcademicExplainResponse,
  explainAcademicConcept,
} from "@/lib/api";
import { ensureVideoGenerationSafely } from "@/lib/videoRequestCoordinator";

interface MaterialReaderProps {
  materialData: ModuleLearningMaterialResponse;
  token: string;
  isWeakModule?: boolean;
  onBack: () => void;
  onOpenMicroLesson: (response: AcademicExplainResponse) => void;
}

export const MaterialReader: React.FC<MaterialReaderProps> = ({
  materialData,
  token,
  isWeakModule = false,
  onBack,
  onOpenMicroLesson,
}) => {
  const materials = materialData.materials || [];
  const [selectedMaterialIndex, setSelectedMaterialIndex] = useState<number>(0);
  const [currentPageIndex, setCurrentPageIndex] = useState<number>(0);

  // Selection state
  const [selectedText, setSelectedText] = useState<string>("");
  const [floatingToolbarPos, setFloatingToolbarPos] = useState<{ top: number; left: number } | null>(null);
  const [isExplaining, setIsExplaining] = useState<boolean>(false);
  const [explainError, setExplainError] = useState<string | null>(null);

  const activeMaterial: LearningMaterialDetail | undefined = materials[selectedMaterialIndex];
  const pages = activeMaterial?.pages || [];
  const activePage: MaterialPageDetail | undefined = pages[currentPageIndex];

  const contentContainerRef = useRef<HTMLDivElement>(null);

  // Automatic video pre-generation ONLY for weak-area / Needs Support module
  useEffect(() => {
    if (!isWeakModule || !token || !materialData) return;

    const firstLesson = materialData.micro_lessons?.[0];
    const topicName = firstLesson?.topic || firstLesson?.title || materialData.module_title;

    ensureVideoGenerationSafely(token, {
      lesson_id: firstLesson?.id,
      topic_key: firstLesson?.topic_key,
      subject_id: materialData.subject_id,
      module_id: materialData.module_id,
      co_code: materialData.co_code,
      topic: topicName,
      lesson_payload: firstLesson,
    }).catch((err) => {
      console.warn("[MaterialReader] Background weak-area video trigger notice:", err.message);
    });
  }, [isWeakModule, token, materialData]);

  // Parse structured topic names if available
  const topics: string[] = React.useMemo(() => {
    if (!activePage?.structured_json) return [];
    try {
      const parsed = JSON.parse(activePage.structured_json);
      return parsed.topics || [];
    } catch {
      return [];
    }
  }, [activePage]);

  // Handle selection detection safely
  const handleSelectionChange = useCallback(() => {
    if (typeof window === "undefined") return;
    const selection = window.getSelection();

    if (!selection || selection.isCollapsed || !selection.toString().trim()) {
      setSelectedText("");
      setFloatingToolbarPos(null);
      return;
    }

    const text = selection.toString().trim();
    if (text.length < 3) {
      setSelectedText("");
      setFloatingToolbarPos(null);
      return;
    }

    // Verify selection is within contentContainerRef
    const range = selection.getRangeAt(0);
    if (
      contentContainerRef.current &&
      contentContainerRef.current.contains(range.commonAncestorContainer)
    ) {
      const rect = range.getBoundingClientRect();
      const containerRect = contentContainerRef.current.getBoundingClientRect();

      setSelectedText(text);
      setFloatingToolbarPos({
        top: Math.max(10, rect.top - containerRect.top - 42),
        left: Math.max(10, Math.min(containerRect.width - 160, rect.left - containerRect.left + rect.width / 2 - 70)),
      });
      setExplainError(null);
    }
  }, []);

  // Set up and clean up selection event listeners
  useEffect(() => {
    const handleMouseUp = () => {
      setTimeout(handleSelectionChange, 20);
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === "Shift" || e.key === "ArrowLeft" || e.key === "ArrowRight") {
        setTimeout(handleSelectionChange, 20);
      }
    };

    const handleTouchEnd = () => {
      setTimeout(handleSelectionChange, 50);
    };

    document.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("keyup", handleKeyUp);
    document.addEventListener("touchend", handleTouchEnd);

    return () => {
      document.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("keyup", handleKeyUp);
      document.removeEventListener("touchend", handleTouchEnd);
    };
  }, [handleSelectionChange]);

  // Clear selection when changing page or material
  const handlePageChange = (newIndex: number) => {
    setCurrentPageIndex(newIndex);
    setSelectedText("");
    setFloatingToolbarPos(null);
    setExplainError(null);
    if (typeof window !== "undefined") {
      window.getSelection()?.removeAllRanges();
    }
  };

  // Trigger explain request
  const handleExplain = async () => {
    if (!selectedText || isExplaining) return;

    setIsExplaining(true);
    setExplainError(null);

    try {
      const response = await explainAcademicConcept(token, {
        material_id: activeMaterial?.id,
        module_id: materialData.module_id,
        subject_id: materialData.subject_id,
        page_number: activePage?.page_number || currentPageIndex + 1,
        co_code: materialData.co_code,
        selected_text: selectedText,
        topic: topics[0] || activePage?.page_title,
      });

      onOpenMicroLesson(response);
    } catch (err: any) {
      console.error("Failed to generate explanation:", err);
      setExplainError(err.message || "Unable to synthesize explanation for selected text. Please try another passage.");
    } finally {
      setIsExplaining(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Header Bar */}
      <div
        style={{
          background: "var(--surface-card)",
          border: "1px solid var(--surface-border)",
          borderRadius: "10px",
          padding: "18px 24px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <button
            type="button"
            onClick={onBack}
            style={{
              background: "var(--surface-elevated)",
              border: "1px solid var(--surface-border)",
              borderRadius: "8px",
              padding: "8px 12px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "0.82rem",
              fontWeight: 600,
              color: "var(--text-main)",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "var(--surface-elevated)")}
          >
            <ArrowLeft size={16} />
            <span>Back to Subject</span>
          </button>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  padding: "2px 7px",
                  borderRadius: "4px",
                  background: "#F0F9FF",
                  color: "var(--color-student)",
                  border: "1px solid #BAE6FD",
                }}
              >
                {materialData.subject_code} · {materialData.co_code}
              </span>
              <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                Module {materialData.module_number}: {materialData.module_title}
              </span>
              {isWeakModule && (
                <span
                  style={{
                    fontSize: "0.68rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    background: "#FEF2F2",
                    color: "var(--color-danger)",
                    border: "1px solid #FECACA",
                  }}
                >
                  Needs Support Area
                </span>
              )}
            </div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-main)", marginTop: "3px" }}>
              {activeMaterial?.title || "Course Learning Material"}
            </h2>
          </div>
        </div>

        {/* Source Reference & Direct Micro-Lessons Launcher */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {materialData.micro_lessons && materialData.micro_lessons.length > 0 && (
            <button
              type="button"
              onClick={() => {
                const ml = materialData.micro_lessons[0];
                onOpenMicroLesson({
                  status: "success",
                  lesson: ml,
                  generation: {
                    mode: "cache",
                    model: "grounded-microlesson-store",
                    cached: true,
                    latency_ms: 10,
                  },
                });
              }}
              style={{
                background: "var(--color-primary)",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "8px",
                padding: "8px 14px",
                fontSize: "0.80rem",
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <Sparkles size={14} color="#FDE047" />
              <span>Launch Micro-Lesson</span>
            </button>
          )}

          {activeMaterial?.source_reference && (
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-dim)",
                background: "var(--surface-elevated)",
                padding: "6px 12px",
                borderRadius: "6px",
                border: "1px solid var(--surface-border)",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <BookOpen size={14} color="var(--color-student)" />
              <span>{activeMaterial.source_reference}</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Reader Surface */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr",
          gap: "16px",
        }}
      >
        <div
          style={{
            background: "var(--surface-card)",
            border: "1px solid var(--surface-border)",
            borderRadius: "10px",
            boxShadow: "var(--shadow-sm)",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            minHeight: "560px",
          }}
        >
          {/* Reader Sub-Header (Page Navigation & Topics) */}
          <div
            style={{
              padding: "14px 24px",
              background: "var(--surface-elevated)",
              borderBottom: "1px solid var(--surface-border)",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-main)" }}>
                {activePage?.page_title || `Page ${currentPageIndex + 1}`}
              </span>
              {topics.map((t, idx) => (
                <span
                  key={idx}
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: 600,
                    background: "var(--surface-card)",
                    padding: "2px 8px",
                    borderRadius: "12px",
                    color: "var(--text-muted)",
                    border: "1px solid var(--surface-border)",
                  }}
                >
                  {t}
                </span>
              ))}
            </div>

            {/* Page Navigation Controls */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <button
                type="button"
                onClick={() => handlePageChange(currentPageIndex - 1)}
                disabled={currentPageIndex === 0}
                style={{
                  background: "var(--surface-card)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "6px",
                  padding: "5px 10px",
                  cursor: currentPageIndex === 0 ? "not-allowed" : "pointer",
                  color: currentPageIndex === 0 ? "var(--text-dim)" : "var(--text-main)",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "0.78rem",
                  fontWeight: 600,
                }}
              >
                <ChevronLeft size={14} />
                <span>Prev</span>
              </button>

              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>
                Page {currentPageIndex + 1} of {pages.length}
              </span>

              <button
                type="button"
                onClick={() => handlePageChange(currentPageIndex + 1)}
                disabled={currentPageIndex + 1 >= pages.length}
                style={{
                  background: "var(--surface-card)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "6px",
                  padding: "5px 10px",
                  cursor: currentPageIndex + 1 >= pages.length ? "not-allowed" : "pointer",
                  color: currentPageIndex + 1 >= pages.length ? "var(--text-dim)" : "var(--text-main)",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "0.78rem",
                  fontWeight: 600,
                }}
              >
                <span>Next</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>

          {/* Page Academic Text (Real Selectable Content) */}
          <div
            ref={contentContainerRef}
            style={{
              flex: 1,
              padding: "32px 40px",
              position: "relative",
              userSelect: "text",
              WebkitUserSelect: "text",
            }}
          >
            {/* Floating Selection Toolbar */}
            {floatingToolbarPos && selectedText && !isExplaining && (
              <div
                style={{
                  position: "absolute",
                  top: `${floatingToolbarPos.top}px`,
                  left: `${floatingToolbarPos.left}px`,
                  zIndex: 50,
                  animation: "fadeIn 0.15s ease",
                }}
              >
                <button
                  type="button"
                  onClick={handleExplain}
                  style={{
                    background: "var(--color-primary)",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: "20px",
                    padding: "7px 14px",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    boxShadow: "var(--shadow-md)",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    whiteSpace: "nowrap",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.04)")}
                  onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                >
                  <Sparkles size={14} color="#FDE047" />
                  <span>Explain this</span>
                </button>
              </div>
            )}

            {/* In-Flight Explanation Loading Indicator */}
            {isExplaining && (
              <div
                style={{
                  background: "#F8FAFC",
                  border: "1px solid #BAE6FD",
                  borderLeft: "4px solid var(--color-student)",
                  borderRadius: "8px",
                  padding: "14px 18px",
                  marginBottom: "20px",
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  animation: "fadeIn 0.2s ease",
                }}
              >
                <Loader2 size={18} color="var(--color-student)" className="animate-spin" />
                <div>
                  <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-main)" }}>
                    ✨ Understanding concept & preparing your micro-lesson...
                  </div>
                  <div style={{ fontSize: "0.76rem", color: "var(--text-dim)", marginTop: "2px" }}>
                    Retrieving course grounding notes for &ldquo;{selectedText.slice(0, 60)}...&rdquo;
                  </div>
                </div>
              </div>
            )}

            {/* Error Banner if explain fails */}
            {explainError && (
              <div
                style={{
                  background: "#FEF2F2",
                  border: "1px solid #FECACA",
                  borderRadius: "8px",
                  padding: "12px 16px",
                  marginBottom: "18px",
                  color: "var(--color-danger)",
                  fontSize: "0.82rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <AlertCircle size={16} />
                <span>{explainError}</span>
              </div>
            )}

            {/* Formatted Text Content */}
            {activePage?.content_text ? (
              <div
                style={{
                  fontSize: "0.95rem",
                  lineHeight: 1.75,
                  color: "var(--text-main)",
                  whiteSpace: "pre-line",
                  fontFamily: "var(--font-sans)",
                }}
              >
                {activePage.content_text}
              </div>
            ) : (
              <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px 0" }}>
                No textual notes available on this page.
              </div>
            )}

            {/* Bottom Interaction Guide Hint */}
            <div
              style={{
                marginTop: "36px",
                paddingTop: "16px",
                borderTop: "1px solid var(--surface-border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "0.78rem",
                color: "var(--text-dim)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Sparkles size={14} color="var(--color-student)" />
                <span>
                  Tip: Highlight any difficult paragraph or formula above to generate an interactive AI Micro-Lesson.
                </span>
              </div>

              {selectedText && !isExplaining && (
                <button
                  type="button"
                  onClick={handleExplain}
                  style={{
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--surface-border)",
                    color: "var(--color-student)",
                    borderRadius: "6px",
                    padding: "4px 10px",
                    fontWeight: 600,
                    cursor: "pointer",
                    fontSize: "0.76rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                  }}
                >
                  <Sparkles size={12} />
                  <span>Explain Selected Highlight</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
