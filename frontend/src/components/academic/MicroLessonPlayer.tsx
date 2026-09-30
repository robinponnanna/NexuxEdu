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
  Video,
  Tv,
  Film,
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";
import {
  MicroLessonPayload,
  MicroLessonScene,
  GenerationMetadata,
  YouTubeResource,
  FrontendVideoState,
  FrontendYouTubeState,
  resolveMediaUrl,
  requestVideoGeneration,
  getVideoJobStatus,
  getVideoByLesson,
} from "@/lib/api";
import { ensureVideoGenerationSafely } from "@/lib/videoRequestCoordinator";
import { DiagramRenderer } from "./DiagramRenderer";

type PlayerMode = "interactive" | "video" | "lecture";

interface MicroLessonPlayerProps {
  lesson: MicroLessonPayload;
  generation?: GenerationMetadata;
  token?: string;
  isOpen: boolean;
  onClose: () => void;
  onAskFollowup?: (topic: string) => void;
}

export const MicroLessonPlayer: React.FC<MicroLessonPlayerProps> = ({
  lesson,
  generation,
  token,
  isOpen,
  onClose,
  onAskFollowup,
}) => {
  // Mode selection: "interactive" (default), "video", "lecture"
  const [activeMode, setActiveMode] = useState<PlayerMode>("interactive");

  // Interactive Scene State
  const [currentSceneIndex, setCurrentSceneIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [sceneElapsedSeconds, setSceneElapsedSeconds] = useState<number>(0);

  // Video State Machine (NO_VIDEO | QUEUED | GENERATING | READY | FAILED_RETRY)
  const [videoState, setVideoState] = useState<FrontendVideoState>("NO_VIDEO");
  const [videoUrl, setVideoUrl] = useState<string | null>(lesson.video_url || null);
  const [videoProgress, setVideoProgress] = useState<number>(0);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // YouTube State Machine (EMBEDDED_VIDEO | SEARCH_FALLBACK | UNAVAILABLE)
  const [youtubeState, setYoutubeState] = useState<FrontendYouTubeState>("UNAVAILABLE");
  const [iframeError, setIframeError] = useState<boolean>(false);

  const videoElementRef = useRef<HTMLVideoElement | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const scenes = lesson.scenes || [];
  const currentScene: MicroLessonScene | undefined = scenes[currentSceneIndex];
  const totalScenes = scenes.length;

  // Calculate total duration and cumulative elapsed time
  const calculatedScenesDuration = scenes.reduce((acc, s) => acc + (s.duration_seconds || 10), 0);
  const totalDuration = calculatedScenesDuration > 0 ? calculatedScenesDuration : (lesson.duration_seconds || 180);

  const previousScenesDuration = scenes
    .slice(0, currentSceneIndex)
    .reduce((acc, s) => acc + (s.duration_seconds || 10), 0);
  const totalElapsed = Math.min(totalDuration, previousScenesDuration + sceneElapsedSeconds);

  const currentSceneDuration = currentScene?.duration_seconds || 10;

  // Resolve YouTube fallback query and URL
  const yt: YouTubeResource | null | undefined = lesson.youtube_resource;
  const resolvedSearchQuery =
    yt?.search_query ||
    `${lesson.subject_code || "Computer Science"} ${lesson.co_code || ""} ${lesson.topic || lesson.title} lecture`.trim();
  const resolvedSearchUrl =
    yt?.search_url ||
    `https://www.youtube.com/results?search_query=${encodeURIComponent(resolvedSearchQuery)}`;

  // Synchronize state when modal opens or lesson changes
  useEffect(() => {
    if (isOpen) {
      setActiveMode("interactive");
      setCurrentSceneIndex(0);
      setSceneElapsedSeconds(0);
      setIsPlaying(true);
      setIframeError(false);
      setActiveJobId(null);

      // Determine initial Video state
      if (lesson.video_url && (lesson.video_status === "ready" || lesson.video_status === "completed")) {
        setVideoState("READY");
        setVideoUrl(lesson.video_url);
        setVideoProgress(100);
        setVideoError(null);
      } else if (lesson.video_status === "queued") {
        setVideoState("QUEUED");
        setVideoProgress(15);
        setVideoError(null);
      } else if (
        lesson.video_status === "rendering" ||
        lesson.video_status === "audio_generating" ||
        lesson.video_status === "video_rendering"
      ) {
        setVideoState("GENERATING");
        setVideoProgress(40);
        setVideoError(null);
      } else if (lesson.video_status === "failed") {
        setVideoState("FAILED_RETRY");
        setVideoError("Video generation encountered an error. You can click retry anytime.");
      } else {
        setVideoState("NO_VIDEO");
        setVideoUrl(null);
        setVideoProgress(0);
        setVideoError(null);
      }

      // Determine initial YouTube state
      if (yt && yt.video_id && yt.is_embeddable !== false) {
        setYoutubeState("EMBEDDED_VIDEO");
      } else if (yt && (yt.search_url || yt.search_query || yt.is_embeddable === false)) {
        setYoutubeState("SEARCH_FALLBACK");
      } else if (lesson.title || lesson.topic) {
        setYoutubeState("SEARCH_FALLBACK");
      } else {
        setYoutubeState("UNAVAILABLE");
      }

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          onClose();
        }
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => {
        window.removeEventListener("keydown", handleKeyDown);
        if (timerRef.current) clearInterval(timerRef.current);
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      };
    } else {
      setIsPlaying(false);
      if (timerRef.current) clearInterval(timerRef.current);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    }
  }, [isOpen, lesson, onClose]);

  // Main playback timer effect for interactive mode
  useEffect(() => {
    if (!isOpen || !isPlaying || totalScenes === 0 || activeMode !== "interactive") {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(() => {
      setSceneElapsedSeconds((prev) => {
        if (prev + 1 >= currentSceneDuration) {
          if (currentSceneIndex + 1 < totalScenes) {
            setCurrentSceneIndex((idx) => idx + 1);
            return 0;
          } else {
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
  }, [isOpen, isPlaying, currentSceneIndex, totalScenes, currentSceneDuration, activeMode]);

  // Resilient Polling Worker for QUEUED or GENERATING Video state
  useEffect(() => {
    if (!isOpen || !token || (videoState !== "QUEUED" && videoState !== "GENERATING")) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    let isMounted = true;
    pollIntervalRef.current = setInterval(async () => {
      try {
        if (activeJobId) {
          const statusRes = await getVideoJobStatus(token, activeJobId);
          if (!isMounted) return;

          setVideoProgress(statusRes.progress_pct || 50);

          if ((statusRes.status === "completed" || statusRes.status === "ready") && statusRes.video_url) {
            setVideoUrl(statusRes.video_url);
            setVideoState("READY");
            setVideoProgress(100);
            setVideoError(null);
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          } else if (statusRes.status === "failed") {
            setVideoState("FAILED_RETRY");
            setVideoError(statusRes.error_message || "Video rendering failed. Click retry to regenerate.");
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          }
        } else if (lesson.id) {
          const statusRes = await getVideoByLesson(token, lesson.id);
          if (!isMounted) return;

          if ((statusRes.status === "completed" || statusRes.status === "ready") && statusRes.video_url) {
            setVideoUrl(statusRes.video_url);
            setVideoState("READY");
            setVideoProgress(100);
            setVideoError(null);
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          } else if (statusRes.status === "failed") {
            setVideoState("FAILED_RETRY");
            setVideoError(statusRes.error_message || "Video rendering failed. Click retry to regenerate.");
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          }
        }
      } catch (err: any) {
        if (!isMounted) return;
        console.warn("[MicroLessonPlayer] Video poll check notice:", err.message);
      }
    }, 2000);

    return () => {
      isMounted = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [isOpen, token, videoState, activeJobId, lesson.id]);

  // Video Generation / Retry Trigger
  const handleStartOrRetryVideoGeneration = async () => {
    if (!token) return;
    setVideoState("GENERATING");
    setVideoError(null);
    setVideoProgress(15);

    try {
      const job = await ensureVideoGenerationSafely(token, {
        lesson_id: lesson.id,
        topic_key: lesson.topic_key,
        subject_id: lesson.subject_id,
        module_id: lesson.module_id,
        topic: lesson.topic || lesson.title,
        co_code: lesson.co_code,
        lesson_payload: lesson,
      });

      if (job) {
        setActiveJobId(job.job_id);
        if ((job.status === "completed" || job.status === "ready") && job.video_url) {
          setVideoUrl(job.video_url);
          setVideoState("READY");
          setVideoProgress(100);
        } else if (job.status === "failed") {
          setVideoState("FAILED_RETRY");
          setVideoError(job.error_message || "Video generation failed. Click Retry to try again.");
        } else {
          setVideoState("GENERATING");
          setVideoProgress(job.progress_pct || 25);
        }
      }
    } catch (err: any) {
      setVideoState("FAILED_RETRY");
      setVideoError(err.message || "Could not initiate video generation. Please click retry.");
    }
  };

  // Browser HTML5 Video Player Error Recovery
  const handleVideoPlayerError = () => {
    console.warn("[MicroLessonPlayer] HTML5 video element playback error with URL:", videoUrl);
    setVideoState("GENERATING");
    setVideoError("Video stream unavailable or corrupted on disk. Automatically regenerating fresh MP4...");
    setVideoProgress(20);
    handleStartOrRetryVideoGeneration();
  };

  // YouTube IFrame Error Handler
  const handleYouTubeIframeError = () => {
    console.warn("[MicroLessonPlayer] YouTube iframe failed to load. Switching to search fallback.");
    setIframeError(true);
    setYoutubeState("SEARCH_FALLBACK");
  };

  // Jump to specific scene second inside the video player
  const handleSeekVideoToScene = (targetSeconds: number) => {
    if (videoElementRef.current) {
      videoElementRef.current.currentTime = targetSeconds;
      videoElementRef.current.play().catch(() => {});
    }
  };

  // Interactive navigation handlers
  const handleTogglePlay = () => {
    if (!isPlaying && currentSceneIndex === totalScenes - 1 && sceneElapsedSeconds >= currentSceneDuration) {
      setCurrentSceneIndex(0);
      setSceneElapsedSeconds(0);
    }
    setIsPlaying(!isPlaying);
  };

  const handlePrevScene = () => {
    if (currentSceneIndex > 0) {
      setCurrentSceneIndex((idx) => idx - 1);
      setSceneElapsedSeconds(0);
      setIsPlaying(true);
    }
  };

  const handleNextScene = () => {
    if (currentSceneIndex < totalScenes - 1) {
      setCurrentSceneIndex((idx) => idx + 1);
      setSceneElapsedSeconds(0);
      setIsPlaying(true);
    }
  };

  const handleSeekScene = (targetIndex: number) => {
    if (targetIndex >= 0 && targetIndex < totalScenes) {
      setCurrentSceneIndex(targetIndex);
      setSceneElapsedSeconds(0);
      setIsPlaying(true);
    }
  };

  const handleReplay = () => {
    setCurrentSceneIndex(0);
    setSceneElapsedSeconds(0);
    setIsPlaying(true);
  };

  if (!isOpen) return null;

  const sceneType = currentScene?.type || currentScene?.visual_type || "concept";

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(11, 15, 23, 0.85)",
        backdropFilter: "blur(8px)",
        zIndex: 9999,
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
          border: "1px solid var(--surface-border)",
          borderRadius: "14px",
          boxShadow: "var(--shadow-lg)",
          width: "100%",
          maxWidth: "880px",
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          animation: "fadeIn 0.2s ease",
        }}
      >
        {/* ================= PLAYER TOP HEADER & MODE CONTROLS ================= */}
        <div
          style={{
            padding: "16px 22px",
            borderBottom: "1px solid var(--surface-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--surface-elevated)",
            flexWrap: "wrap",
            gap: "12px",
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
                  fontSize: "1.02rem",
                  fontWeight: 700,
                  color: "var(--text-main)",
                  marginTop: "2px",
                }}
              >
                {lesson.title}
              </h2>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {/* Mode Switcher Tabs */}
            <div
              style={{
                display: "flex",
                background: "var(--surface-dark)",
                padding: "3px",
                borderRadius: "8px",
                border: "1px solid var(--surface-border)",
                gap: "2px",
              }}
            >
              {/* Tab 1: Interactive Lesson */}
              <button
                type="button"
                onClick={() => setActiveMode("interactive")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  border: "none",
                  cursor: "pointer",
                  background: activeMode === "interactive" ? "var(--color-primary)" : "transparent",
                  color: activeMode === "interactive" ? "#FFFFFF" : "var(--text-dim)",
                  transition: "all 0.15s ease",
                }}
              >
                <Lightbulb size={14} />
                <span>Interactive</span>
              </button>

              {/* Tab 2: Watch Video */}
              <button
                type="button"
                onClick={() => {
                  setActiveMode("video");
                  if (videoState === "NO_VIDEO" && token) {
                    handleStartOrRetryVideoGeneration();
                  }
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  border: "none",
                  cursor: "pointer",
                  background: activeMode === "video" ? "var(--color-primary)" : "transparent",
                  color: activeMode === "video" ? "#FFFFFF" : "var(--text-dim)",
                  transition: "all 0.15s ease",
                }}
              >
                <Video size={14} />
                <span>Watch Video</span>
                {videoState === "READY" && (
                  <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10B981" }} />
                )}
                {(videoState === "GENERATING" || videoState === "QUEUED") && (
                  <Loader2 size={10} className="animate-spin" color="var(--color-student)" />
                )}
              </button>

              {/* Tab 3: Related Lecture (Always available) */}
              <button
                type="button"
                onClick={() => setActiveMode("lecture")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  border: "none",
                  cursor: "pointer",
                  background: activeMode === "lecture" ? "var(--color-primary)" : "transparent",
                  color: activeMode === "lecture" ? "#FFFFFF" : "var(--text-dim)",
                  transition: "all 0.15s ease",
                }}
              >
                <Tv size={14} />
                <span>Related Lecture</span>
              </button>
            </div>

            {/* Close Button */}
            <button
              type="button"
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

        {/* ================= MODE 1: INTERACTIVE LESSON ================= */}
        {activeMode === "interactive" && (
          <>
            <div
              style={{
                flex: 1,
                padding: "24px 28px",
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
                  {/* Scene Header */}
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
                      fontSize: "1.25rem",
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
                        fontSize: "0.90rem",
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

                  {/* Visual Component / Diagram / Table / Code */}
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
                        marginTop: "16px",
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

            {/* Playback Controls Bar */}
            <div
              style={{
                padding: "16px 22px",
                background: "var(--surface-elevated)",
                borderTop: "1px solid var(--surface-border)",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              {/* Progress Track */}
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

              {/* Control Buttons */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={handleTogglePlay}
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "50%",
                      background: "var(--color-primary)",
                      color: "#FFFFFF",
                      border: "none",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                    title={isPlaying ? "Pause" : "Play"}
                  >
                    {isPlaying ? <Pause size={16} /> : <Play size={16} style={{ marginLeft: "2px" }} />}
                  </button>

                  <button
                    type="button"
                    onClick={handleReplay}
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      color: "var(--text-muted)",
                      borderRadius: "6px",
                      padding: "6px 10px",
                      fontSize: "0.78rem",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                    title="Restart Micro-Lesson"
                  >
                    <RotateCcw size={13} />
                    <span>Restart</span>
                  </button>

                  <div style={{ fontSize: "0.78rem", color: "var(--text-dim)", marginLeft: "6px" }}>
                    {Math.floor(totalElapsed / 60)}:{String(Math.floor(totalElapsed % 60)).padStart(2, "0")} /{" "}
                    {Math.floor(totalDuration / 60)}:{String(Math.floor(totalDuration % 60)).padStart(2, "0")}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={handlePrevScene}
                    disabled={currentSceneIndex === 0}
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      color: currentSceneIndex === 0 ? "var(--text-dim)" : "var(--text-main)",
                      borderRadius: "6px",
                      padding: "6px 12px",
                      fontSize: "0.80rem",
                      cursor: currentSceneIndex === 0 ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      opacity: currentSceneIndex === 0 ? 0.5 : 1,
                    }}
                  >
                    <ChevronLeft size={14} />
                    <span>Previous</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleNextScene}
                    disabled={currentSceneIndex === totalScenes - 1}
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      color: currentSceneIndex === totalScenes - 1 ? "var(--text-dim)" : "var(--text-main)",
                      borderRadius: "6px",
                      padding: "6px 12px",
                      fontSize: "0.80rem",
                      cursor: currentSceneIndex === totalScenes - 1 ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      opacity: currentSceneIndex === totalScenes - 1 ? 0.5 : 1,
                    }}
                  >
                    <span>Next</span>
                    <ChevronRight size={14} />
                  </button>

                  {onAskFollowup && (
                    <button
                      type="button"
                      onClick={() => onAskFollowup(lesson.topic || lesson.title)}
                      style={{
                        background: "var(--surface-card)",
                        border: "1px solid var(--surface-border)",
                        color: "var(--color-student)",
                        borderRadius: "6px",
                        padding: "6px 12px",
                        fontSize: "0.80rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        marginLeft: "6px",
                      }}
                    >
                      <MessageSquare size={14} />
                      <span>Ask AI Tutor</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {/* ================= MODE 2: WATCH VIDEO STATE MACHINE ================= */}
        {activeMode === "video" && (
          <div
            style={{
              padding: "24px 28px",
              background: "var(--surface-dark)",
              minHeight: "440px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            {videoState === "READY" && videoUrl ? (
              <div>
                {/* Video Info Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ background: "#10B981", color: "#FFFFFF", padding: "3px 8px", borderRadius: "4px", fontSize: "0.72rem", fontWeight: 700 }}>
                      720p HD MP4
                    </span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                      Authoritative AI Narrated Micro-Lesson • Synchronized Visuals
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <button
                      type="button"
                      onClick={handleStartOrRetryVideoGeneration}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--text-dim)",
                        fontSize: "0.74rem",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                      title="Regenerate video from current notes"
                    >
                      <RefreshCw size={12} />
                      <span>Regenerate</span>
                    </button>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                      Duration: {totalDuration}s
                    </span>
                  </div>
                </div>

                {/* HTML5 Video Element with Error Recovery */}
                <div
                  style={{
                    width: "100%",
                    borderRadius: "10px",
                    overflow: "hidden",
                    background: "#000000",
                    border: "1px solid var(--surface-border)",
                    boxShadow: "var(--shadow-md)",
                  }}
                >
                  <video
                    ref={videoElementRef}
                    controls
                    autoPlay
                    playsInline
                    onError={handleVideoPlayerError}
                    style={{ width: "100%", maxHeight: "380px", display: "block" }}
                    src={resolveMediaUrl(videoUrl)}
                  >
                    Your browser does not support HTML5 video playback.
                  </video>
                </div>

                {/* Scene Jump Bookmarks */}
                <div style={{ marginTop: "16px" }}>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", marginBottom: "8px" }}>
                    Jump to Scene Chapter:
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {scenes.map((sc, idx) => {
                      const startSec = scenes.slice(0, idx).reduce((acc, s) => acc + (s.duration_seconds || 10), 0);
                      return (
                        <button
                          key={sc.scene_id || idx}
                          type="button"
                          onClick={() => handleSeekVideoToScene(startSec)}
                          style={{
                            background: "var(--surface-elevated)",
                            border: "1px solid var(--surface-border)",
                            borderRadius: "6px",
                            padding: "5px 10px",
                            fontSize: "0.74rem",
                            color: "var(--text-main)",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--color-primary)")}
                          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--surface-border)")}
                        >
                          <Clock size={11} color="var(--color-student)" />
                          <span>Scene {idx + 1}: {sc.title.slice(0, 24)}...</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : videoState === "GENERATING" || videoState === "QUEUED" ? (
              <div style={{ textAlign: "center", padding: "60px 20px" }}>
                <Loader2 size={38} color="var(--color-student)" className="animate-spin" style={{ margin: "0 auto 16px auto" }} />
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)", marginBottom: "8px" }}>
                  {videoState === "QUEUED" ? "Queued for Generation..." : "Creating Your Personalized Lesson Video..."}
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", maxWidth: "440px", margin: "0 auto 20px auto" }}>
                  Synthesizing neural audio narration and composing high-definition video frames. This may take a few moments.
                </p>

                {/* Progress bar */}
                <div style={{ width: "100%", maxWidth: "340px", height: "8px", background: "var(--surface-border)", borderRadius: "4px", margin: "0 auto 12px auto", overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${Math.max(10, videoProgress)}%`, background: "var(--color-primary)", transition: "width 0.4s ease" }} />
                </div>
                <div style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                  {videoProgress > 0 ? `${videoProgress}% complete` : "Initiating video worker..."}
                </div>

                <div style={{ marginTop: "24px" }}>
                  <button
                    type="button"
                    onClick={() => setActiveMode("interactive")}
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      borderRadius: "6px",
                      padding: "8px 16px",
                      fontSize: "0.82rem",
                      color: "var(--color-student)",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Continue Learning in Interactive Mode →
                  </button>
                </div>
              </div>
            ) : videoState === "FAILED_RETRY" ? (
              <div style={{ textAlign: "center", padding: "50px 20px" }}>
                <AlertTriangle size={42} color="var(--color-danger)" style={{ margin: "0 auto 14px auto" }} />
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)", marginBottom: "8px" }}>
                  Video Generation Notice
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", maxWidth: "450px", margin: "0 auto 16px auto" }}>
                  {videoError || "Video rendering encountered a temporary delay. You can retry anytime."}
                </p>

                <div style={{ display: "flex", justifyContent: "center", gap: "10px", marginTop: "20px" }}>
                  <button
                    type="button"
                    onClick={handleStartOrRetryVideoGeneration}
                    style={{
                      background: "var(--color-primary)",
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: "8px",
                      padding: "10px 20px",
                      fontSize: "0.88rem",
                      fontWeight: 700,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <RefreshCw size={16} />
                    <span>Retry Video Generation</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveMode("interactive")}
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      color: "var(--text-main)",
                      borderRadius: "8px",
                      padding: "10px 16px",
                      fontSize: "0.88rem",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Return to Interactive
                  </button>
                </div>
              </div>
            ) : (
              /* NO_VIDEO initial state */
              <div style={{ textAlign: "center", padding: "50px 20px" }}>
                <Film size={42} color="var(--text-dim)" style={{ margin: "0 auto 14px auto" }} />
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)", marginBottom: "8px" }}>
                  Narrated Video Ready to Generate
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", maxWidth: "460px", margin: "0 auto 20px auto" }}>
                  Create an MP4 with neural voiceover and synchronized diagrams generated from your highlighted notes.
                </p>

                <div style={{ display: "flex", justifyContent: "center", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={handleStartOrRetryVideoGeneration}
                    style={{
                      background: "var(--color-primary)",
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: "8px",
                      padding: "10px 20px",
                      fontSize: "0.88rem",
                      fontWeight: 700,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <Video size={16} />
                    <span>Generate Narrated MP4</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveMode("interactive")}
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      color: "var(--text-main)",
                      borderRadius: "8px",
                      padding: "10px 16px",
                      fontSize: "0.88rem",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Return to Interactive
                  </button>
                </div>
              </div>
            )}

            {/* Video Footer */}
            <div style={{ paddingTop: "14px", borderTop: "1px solid var(--surface-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => setActiveMode("interactive")}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--color-student)",
                  fontSize: "0.80rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                ← Switch back to Interactive Lesson
              </button>

              {onAskFollowup && (
                <button
                  type="button"
                  onClick={() => onAskFollowup(lesson.topic || lesson.title)}
                  style={{
                    background: "var(--surface-card)",
                    border: "1px solid var(--surface-border)",
                    color: "var(--color-student)",
                    borderRadius: "6px",
                    padding: "6px 12px",
                    fontSize: "0.80rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <MessageSquare size={14} />
                  <span>Ask AI Tutor</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* ================= MODE 3: RELATED LECTURE (YOUTUBE STATE MACHINE) ================= */}
        {activeMode === "lecture" && (
          <div
            style={{
              padding: "24px 28px",
              background: "var(--surface-dark)",
              minHeight: "440px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            {youtubeState === "EMBEDDED_VIDEO" && yt?.video_id && !iframeError ? (
              <div>
                {/* Lecture Disclaimer Banner */}
                <div
                  style={{
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    marginBottom: "14px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: "8px",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--color-student)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                      Supplementary University Lecture • Curated Resource
                    </div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--text-main)", marginTop: "2px" }}>
                      {yt.title}
                    </div>
                    <div style={{ fontSize: "0.76rem", color: "var(--text-dim)", marginTop: "2px" }}>
                      Channel: <strong>{yt.channel || "Academic Provider"}</strong>
                      {yt.start_seconds != null && yt.end_seconds != null
                        ? ` • Recommended chapter: ${yt.start_seconds}s to ${yt.end_seconds}s`
                        : ""}
                    </div>
                  </div>

                  <a
                    href={`https://www.youtube.com/watch?v=${yt.video_id}&t=${yt.start_seconds || 0}s`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      borderRadius: "6px",
                      padding: "6px 10px",
                      fontSize: "0.76rem",
                      color: "var(--text-main)",
                      textDecoration: "none",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      fontWeight: 600,
                    }}
                  >
                    <span>Watch on YouTube</span>
                    <ExternalLink size={12} />
                  </a>
                </div>

                {/* YouTube IFrame Embed with Failure Fallback */}
                <div
                  style={{
                    width: "100%",
                    borderRadius: "10px",
                    overflow: "hidden",
                    background: "#000000",
                    border: "1px solid var(--surface-border)",
                    aspectRatio: "16 / 9",
                    maxHeight: "360px",
                  }}
                >
                  <iframe
                    width="100%"
                    height="100%"
                    src={`https://www.youtube-nocookie.com/embed/${yt.video_id}?autoplay=1&start=${yt.start_seconds || 0}&end=${yt.end_seconds || 600}&rel=0`}
                    title={yt.title}
                    onError={handleYouTubeIframeError}
                    frameBorder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                    style={{ border: "none" }}
                  />
                </div>

                {yt.description && (
                  <div style={{ marginTop: "12px", fontSize: "0.80rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    {yt.description}
                  </div>
                )}
              </div>
            ) : youtubeState === "SEARCH_FALLBACK" || iframeError ? (
              <div style={{ padding: "10px 0" }}>
                {/* Search Fallback Card */}
                <div
                  style={{
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "10px",
                    padding: "24px 28px",
                    marginBottom: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
                    <div
                      style={{
                        width: "36px",
                        height: "36px",
                        borderRadius: "8px",
                        background: "#FEF2F2",
                        color: "#DC2626",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Tv size={18} />
                    </div>
                    <div>
                      <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--color-student)", textTransform: "uppercase" }}>
                        Related University Lecture Discovery
                      </div>
                      <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
                        {yt?.title || `${lesson.topic || lesson.title} Lecture Reference`}
                      </h3>
                    </div>
                  </div>

                  <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.6, marginBottom: "16px" }}>
                    An authoritative search query has been generated for this exact course outcome to discover university lectures, walkthroughs, and problem-solving sessions.
                  </p>

                  <div
                    style={{
                      background: "var(--surface-dark)",
                      border: "1px solid var(--surface-border)",
                      borderRadius: "8px",
                      padding: "12px 16px",
                      marginBottom: "18px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px",
                      flexWrap: "wrap",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 600 }}>
                        Academic Search Query
                      </div>
                      <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--text-main)", marginTop: "2px" }}>
                        &ldquo;{resolvedSearchQuery}&rdquo;
                      </div>
                      {yt?.channel && (
                        <div style={{ fontSize: "0.74rem", color: "var(--text-dim)", marginTop: "2px" }}>
                          Suggested channel: <strong>{yt.channel}</strong>
                        </div>
                      )}
                    </div>

                    <a
                      href={resolvedSearchUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        background: "#DC2626",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: "8px",
                        padding: "9px 16px",
                        fontSize: "0.82rem",
                        fontWeight: 700,
                        textDecoration: "none",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        boxShadow: "var(--shadow-sm)",
                      }}
                    >
                      <Search size={14} />
                      <span>Search on YouTube</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>

                  <div style={{ fontSize: "0.76rem", color: "var(--text-dim)" }}>
                    Opens YouTube in a new tab with academic parameters pre-configured.
                  </div>
                </div>
              </div>
            ) : (
              /* UNAVAILABLE state */
              <div style={{ textAlign: "center", padding: "60px 20px" }}>
                <Tv size={40} color="var(--text-dim)" style={{ margin: "0 auto 14px auto" }} />
                <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-main)", marginBottom: "8px" }}>
                  Related Lecture Reference
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", maxWidth: "440px", margin: "0 auto 20px auto" }}>
                  Related lecture resources are currently unavailable for this specific topic context.
                </p>
                <button
                  type="button"
                  onClick={() => setActiveMode("interactive")}
                  style={{
                    background: "var(--surface-card)",
                    border: "1px solid var(--surface-border)",
                    color: "var(--color-student)",
                    borderRadius: "6px",
                    padding: "8px 16px",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Return to Interactive Lesson
                </button>
              </div>
            )}

            {/* Lecture Footer */}
            <div style={{ paddingTop: "14px", borderTop: "1px solid var(--surface-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => setActiveMode("interactive")}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--color-student)",
                  fontSize: "0.80rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                ← Return to Interactive Micro-Lesson
              </button>

              <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                Supplementary Academic Resource · YouTube
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
