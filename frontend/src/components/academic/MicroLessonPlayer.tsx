"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  X,
  Sparkles,
  BookOpen,
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  FileText,
  Clock,
  MessageSquare,
  ShieldCheck,
} from "lucide-react";
import { MicroLessonPayload, MicroLessonScene, GenerationMetadata } from "@/lib/api";
import { DiagramRenderer } from "./DiagramRenderer";

interface MicroLessonPlayerProps {
  lesson: MicroLessonPayload;
  generation?: GenerationMetadata;
  isOpen: boolean;
  onClose: () => void;
  onAskFollowup?: (topic: string) => void;
}

export const MicroLessonPlayer: React.FC<MicroLessonPlayerProps> = ({
  lesson,
  generation,
  isOpen,
  onClose,
  onAskFollowup,
}) => {
  const [currentSceneIndex, setCurrentSceneIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [sceneElapsedSeconds, setSceneElapsedSeconds] = useState<number>(0);

  const scenes = lesson.scenes || [];
  const currentScene: MicroLessonScene | undefined = scenes[currentSceneIndex];
  const totalScenes = scenes.length;

  // Calculate total duration and cumulative elapsed time
  const calculatedScenesDuration = scenes.reduce((acc, s) => acc + (s.duration_seconds || 10), 0);
  const totalDuration = calculatedScenesDuration > 0 ? calculatedScenesDuration : (lesson.duration_seconds || 180);
  
  // Calculate cumulative elapsed time across previous scenes + current scene elapsed
  const previousScenesDuration = scenes
    .slice(0, currentSceneIndex)
    .reduce((acc, s) => acc + (s.duration_seconds || 10), 0);
  const totalElapsed = Math.min(totalDuration, previousScenesDuration + sceneElapsedSeconds);

  // Timer reference for cleanup safety
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const currentSceneDuration = currentScene?.duration_seconds || 10;

  // Reset state and attach keyboard listener when a new lesson opens
  useEffect(() => {
    if (isOpen) {
      setCurrentSceneIndex(0);
      setSceneElapsedSeconds(0);
      setIsPlaying(true);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          onClose();
        }
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => {
        window.removeEventListener("keydown", handleKeyDown);
      };
    } else {
      setIsPlaying(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, [isOpen, lesson, onClose]);

  // Main playback timer effect
  useEffect(() => {
    if (!isOpen || !isPlaying || totalScenes === 0) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(() => {
      setSceneElapsedSeconds((prev) => {
        if (prev + 1 >= currentSceneDuration) {
          // Transition to next scene or finish
          if (currentSceneIndex + 1 < totalScenes) {
            setCurrentSceneIndex((idx) => idx + 1);
            return 0;
          } else {
            // End of lesson
            setIsPlaying(false);
            return currentSceneDuration;
          }
        }
        return prev + 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isOpen, isPlaying, currentSceneIndex, totalScenes, currentSceneDuration]);

  // Navigation handlers
  const handleTogglePlay = () => {
    if (!isPlaying && currentSceneIndex === totalScenes - 1 && sceneElapsedSeconds >= currentSceneDuration) {
      // If at end, restart from beginning
      setCurrentSceneIndex(0);
      setSceneElapsedSeconds(0);
    }
    setIsPlaying(!isPlaying);
  };

  const handlePrevScene = () => {
    if (currentSceneIndex > 0) {
      setCurrentSceneIndex((idx) => idx - 1);
      setSceneElapsedSeconds(0);
    }
  };

  const handleNextScene = () => {
    if (currentSceneIndex + 1 < totalScenes) {
      setCurrentSceneIndex((idx) => idx + 1);
      setSceneElapsedSeconds(0);
    }
  };

  const handleRestart = () => {
    setCurrentSceneIndex(0);
    setSceneElapsedSeconds(0);
    setIsPlaying(true);
  };

  const handleSeekScene = (index: number) => {
    setCurrentSceneIndex(index);
    setSceneElapsedSeconds(0);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  if (!isOpen) return null;

  const sceneType = currentScene?.type || currentScene?.visual_type || "concept";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(6px)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: "var(--surface-card)",
          borderRadius: "14px",
          border: "1px solid var(--surface-border)",
          boxShadow: "var(--shadow-lg)",
          width: "100%",
          maxWidth: "860px",
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          animation: "fadeIn 0.2s ease",
        }}
      >
        {/* ================= PLAYER HEADER ================= */}
        <div
          style={{
            padding: "16px 22px",
            borderBottom: "1px solid var(--surface-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--surface-elevated)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "var(--color-primary)",
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Sparkles size={16} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span
                  style={{
                    fontSize: "0.68rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: "var(--color-student)",
                    background: "var(--surface-card)",
                    padding: "2px 7px",
                    borderRadius: "4px",
                    border: "1px solid var(--surface-border)",
                  }}
                >
                  AI Micro-Lesson
                </span>
                {generation && (
                  <span
                    style={{
                      fontSize: "0.68rem",
                      fontWeight: 600,
                      color: "var(--text-dim)",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <ShieldCheck size={12} color="var(--color-success)" />
                    {generation.mode === "cache"
                      ? "Course-Grounded (Cached)"
                      : "Synthesized from Syllabus Notes"}
                  </span>
                )}
              </div>
              <h2
                style={{
                  fontSize: "1.05rem",
                  fontWeight: 700,
                  color: "var(--text-main)",
                  marginTop: "2px",
                }}
              >
                {lesson.title}
              </h2>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={onClose}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-dim)",
                cursor: "pointer",
                padding: "6px",
                borderRadius: "6px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-main)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-dim)")}
              aria-label="Close Micro-Lesson Player"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* ================= STAGE / SCENE CONTENT ================= */}
        <div
          style={{
            flex: 1,
            padding: "28px 32px",
            overflowY: "auto",
            minHeight: "340px",
            background: "var(--surface-dark)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          {currentScene ? (
            <div>
              {/* Scene Label & Title */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span
                    style={{
                      fontSize: "0.72rem",
                      fontWeight: 700,
                      color: "var(--text-dim)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    Scene {currentSceneIndex + 1} of {totalScenes}
                  </span>
                  <span style={{ color: "var(--surface-border)" }}>•</span>
                  <span
                    style={{
                      fontSize: "0.72rem",
                      fontWeight: 600,
                      color:
                        sceneType === "common_mistake"
                          ? "var(--color-danger)"
                          : sceneType === "takeaway"
                          ? "var(--color-success)"
                          : "var(--color-student)",
                      textTransform: "uppercase",
                    }}
                  >
                    {sceneType.replace("_", " ")}
                  </span>
                </div>

                <div
                  style={{
                    fontSize: "0.72rem",
                    color: "var(--text-dim)",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <Clock size={12} />
                  <span>
                    {sceneElapsedSeconds}s / {currentSceneDuration}s
                  </span>
                </div>
              </div>

              <h3
                style={{
                  fontSize: "1.3rem",
                  fontWeight: 700,
                  color: "var(--text-main)",
                  marginBottom: "14px",
                  letterSpacing: "-0.01em",
                }}
              >
                {currentScene.title}
              </h3>

              {/* Narration Quote */}
              {currentScene.narration && (
                <div
                  style={{
                    background: "var(--surface-elevated)",
                    borderLeft: "3px solid var(--color-student)",
                    padding: "12px 16px",
                    borderRadius: "0 8px 8px 0",
                    fontSize: "0.92rem",
                    color: "var(--text-main)",
                    lineHeight: 1.5,
                    marginBottom: "16px",
                    fontStyle: "italic",
                  }}
                >
                  &ldquo;{currentScene.narration}&rdquo;
                </div>
              )}

              {/* Body Text */}
              {currentScene.body && (
                <div
                  style={{
                    fontSize: "0.88rem",
                    color: "var(--text-muted)",
                    lineHeight: 1.6,
                    whiteSpace: "pre-line",
                    marginBottom: "16px",
                  }}
                >
                  {currentScene.body}
                </div>
              )}

              {/* Visual Component / Diagram / Table */}
              {(currentScene.diagram || currentScene.visual_data) && (
                <DiagramRenderer
                  data={currentScene.diagram || currentScene.visual_data}
                  visualType={currentScene.visual_type || currentScene.type}
                />
              )}

              {/* Key Takeaway Callout */}
              {currentScene.key_takeaway && (
                <div
                  style={{
                    marginTop: "18px",
                    background:
                      sceneType === "common_mistake"
                        ? "#FEF2F2"
                        : sceneType === "takeaway"
                        ? "#F0FDF4"
                        : "var(--surface-elevated)",
                    border: "1px solid",
                    borderColor:
                      sceneType === "common_mistake"
                        ? "#FECACA"
                        : sceneType === "takeaway"
                        ? "#BBF7D0"
                        : "var(--surface-border)",
                    borderRadius: "8px",
                    padding: "12px 16px",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "10px",
                  }}
                >
                  {sceneType === "common_mistake" ? (
                    <AlertTriangle size={17} color="var(--color-danger)" style={{ marginTop: "2px", flexShrink: 0 }} />
                  ) : (
                    <Lightbulb size={17} color="var(--color-student)" style={{ marginTop: "2px", flexShrink: 0 }} />
                  )}
                  <div>
                    <div
                      style={{
                        fontSize: "0.74rem",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        color:
                          sceneType === "common_mistake"
                            ? "var(--color-danger)"
                            : "var(--color-student)",
                        marginBottom: "2px",
                      }}
                    >
                      {sceneType === "common_mistake" ? "Exam Pitfall Alert" : "Core Takeaway"}
                    </div>
                    <div
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        color: "var(--text-main)",
                        lineHeight: 1.4,
                      }}
                    >
                      {currentScene.key_takeaway}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px 0" }}>
              No scene content available.
            </div>
          )}
        </div>

        {/* ================= PLAYBACK CONTROLS & TIMELINE ================= */}
        <div
          style={{
            padding: "18px 24px",
            background: "var(--surface-elevated)",
            borderTop: "1px solid var(--surface-border)",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          {/* Segmented Scene Progress Bar */}
          <div style={{ display: "flex", gap: "6px", width: "100%" }}>
            {scenes.map((s, idx) => {
              const isPast = idx < currentSceneIndex;
              const isCurrent = idx === currentSceneIndex;
              const sceneDur = s.duration_seconds || 10;
              const fillPct = isPast ? 100 : isCurrent ? (sceneElapsedSeconds / sceneDur) * 100 : 0;

              return (
                <div
                  key={s.scene_id || idx}
                  onClick={() => handleSeekScene(idx)}
                  style={{
                    flex: 1,
                    height: "6px",
                    background: "var(--surface-border)",
                    borderRadius: "3px",
                    overflow: "hidden",
                    cursor: "pointer",
                    position: "relative",
                  }}
                  title={`Scene ${idx + 1}: ${s.title}`}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${fillPct}%`,
                      background: "var(--color-primary)",
                      transition: isCurrent ? "width 0.3s linear" : "none",
                    }}
                  />
                </div>
              );
            })}
          </div>

          {/* Controls Bottom Row */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            {/* Left: Playback Buttons */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <button
                onClick={handlePrevScene}
                disabled={currentSceneIndex === 0}
                style={{
                  background: "var(--surface-card)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "6px",
                  padding: "7px 10px",
                  cursor: currentSceneIndex === 0 ? "not-allowed" : "pointer",
                  color: currentSceneIndex === 0 ? "var(--text-dim)" : "var(--text-main)",
                  display: "flex",
                  alignItems: "center",
                }}
                aria-label="Previous Scene"
              >
                <ChevronLeft size={16} />
              </button>

              <button
                onClick={handleTogglePlay}
                style={{
                  background: "var(--color-primary)",
                  border: "none",
                  borderRadius: "6px",
                  padding: "7px 16px",
                  color: "#FFFFFF",
                  fontWeight: 600,
                  fontSize: "0.85rem",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                {isPlaying ? <Pause size={15} /> : <Play size={15} />}
                <span>{isPlaying ? "Pause" : "Play"}</span>
              </button>

              <button
                onClick={handleNextScene}
                disabled={currentSceneIndex + 1 >= totalScenes}
                style={{
                  background: "var(--surface-card)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "6px",
                  padding: "7px 10px",
                  cursor: currentSceneIndex + 1 >= totalScenes ? "not-allowed" : "pointer",
                  color: currentSceneIndex + 1 >= totalScenes ? "var(--text-dim)" : "var(--text-main)",
                  display: "flex",
                  alignItems: "center",
                }}
                aria-label="Next Scene"
              >
                <ChevronRight size={16} />
              </button>

              <button
                onClick={handleRestart}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-dim)",
                  cursor: "pointer",
                  padding: "7px",
                  display: "flex",
                  alignItems: "center",
                }}
                title="Restart Lesson"
                aria-label="Restart Lesson"
              >
                <RotateCcw size={15} />
              </button>

              <span
                className="font-mono"
                style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginLeft: "6px" }}
              >
                {formatTime(totalElapsed)} / {formatTime(totalDuration)}
              </span>
            </div>

            {/* Right: Sources & Follow-up in AI */}
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {lesson.sources && lesson.sources.length > 0 && (
                <div
                  style={{
                    fontSize: "0.72rem",
                    color: "var(--text-dim)",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                    background: "var(--surface-card)",
                    padding: "4px 8px",
                    borderRadius: "5px",
                    border: "1px solid var(--surface-border)",
                  }}
                  title={lesson.sources.map((s) => `${s.subject_code} ${s.co_code || ""}: ${s.title} (p.${s.page_number})`).join(", ")}
                >
                  <BookOpen size={12} color="var(--color-student)" />
                  <span>
                    Source: {lesson.sources[0].subject_code} {lesson.sources[0].co_code ? `· ${lesson.sources[0].co_code}` : ""} (p.{lesson.sources[0].page_number})
                  </span>
                </div>
              )}

              {onAskFollowup && (
                <button
                  type="button"
                  onClick={() => onAskFollowup(lesson.title)}
                  style={{
                    background: "var(--surface-card)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "6px",
                    padding: "6px 12px",
                    fontSize: "0.78rem",
                    fontWeight: 600,
                    color: "var(--text-main)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                  }}
                >
                  <MessageSquare size={13} color="var(--color-primary)" />
                  <span>Ask Follow-up</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
