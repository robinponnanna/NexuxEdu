"use client";

import React, { useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";
import {
  SubjectMarksDetailResponse,
  ModuleLearningMaterialResponse,
  AcademicExplainResponse,
  getSubjectMarksDetail,
  getModuleLearningMaterials,
} from "@/lib/api";
import { AcademicOverview } from "./AcademicOverview";
import { SubjectDetailView } from "./SubjectDetailView";
import { MaterialReader } from "./MaterialReader";
import { MicroLessonPlayer } from "./MicroLessonPlayer";

interface AcademicSupportContainerProps {
  token: string;
  onOpenChatWithQuery?: (initialQuery: string) => void;
}

export const AcademicSupportContainer: React.FC<AcademicSupportContainerProps> = ({
  token,
  onOpenChatWithQuery,
}) => {
  const [viewState, setViewState] = useState<"overview" | "subject_detail" | "material_reader">("overview");

  // Subject Detail State
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | null>(null);
  const [subjectDetail, setSubjectDetail] = useState<SubjectMarksDetailResponse | null>(null);
  const [isLoadingSubject, setIsLoadingSubject] = useState<boolean>(false);
  const [subjectError, setSubjectError] = useState<string | null>(null);

  // Material Reader State
  const [materialData, setMaterialData] = useState<ModuleLearningMaterialResponse | null>(null);
  const [isLoadingMaterial, setIsLoadingMaterial] = useState<boolean>(false);
  const [materialError, setMaterialError] = useState<string | null>(null);

  // Micro-Lesson Player State
  const [activeLessonResponse, setActiveLessonResponse] = useState<AcademicExplainResponse | null>(null);
  const [isLessonPlayerOpen, setIsLessonPlayerOpen] = useState<boolean>(false);

  // 1. Open Subject Detail
  const handleSelectSubject = async (subjectId: number) => {
    if (isLoadingSubject) return;
    setSelectedSubjectId(subjectId);
    setIsLoadingSubject(true);
    setSubjectError(null);

    try {
      const detail = await getSubjectMarksDetail(token, subjectId);
      setSubjectDetail(detail);
      setViewState("subject_detail");
    } catch (err: any) {
      console.error("Failed to load subject detail:", err);
      setSubjectError(err.message || "Failed to load detailed subject performance.");
    } finally {
      setIsLoadingSubject(false);
    }
  };

  // 2. Open Material Reader for a specific module
  const handleStudyModule = async (moduleId: number) => {
    if (isLoadingMaterial) return;
    setIsLoadingMaterial(true);
    setMaterialError(null);

    try {
      const mat = await getModuleLearningMaterials(token, moduleId);
      setMaterialData(mat);
      setViewState("material_reader");
    } catch (err: any) {
      console.error("Failed to load module learning materials:", err);
      setMaterialError(err.message || "Unable to retrieve course notes for this module.");
    } finally {
      setIsLoadingMaterial(false);
    }
  };

  // 3. Open Micro-Lesson Modal
  const handleOpenMicroLesson = (response: AcademicExplainResponse) => {
    setActiveLessonResponse(response);
    setIsLessonPlayerOpen(true);
  };

  // 4. Back Navigation Handlers
  const handleBackToOverview = () => {
    setViewState("overview");
    setSubjectDetail(null);
    setSelectedSubjectId(null);
    setSubjectError(null);
  };

  const handleBackToSubject = () => {
    setViewState("subject_detail");
    setMaterialData(null);
    setMaterialError(null);
  };

  const handleAskFollowup = (topicTitle: string) => {
    if (onOpenChatWithQuery) {
      onOpenChatWithQuery(`Can you explain the key concepts of ${topicTitle} in more detail?`);
    }
  };

  return (
    <div style={{ width: "100%" }}>
      {/* Loading Overlay when switching views */}
      {(isLoadingSubject || isLoadingMaterial) && (
        <div
          style={{
            background: "var(--surface-card)",
            border: "1px solid var(--surface-border)",
            borderRadius: "10px",
            padding: "40px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "12px",
            color: "var(--text-dim)",
            marginBottom: "20px",
          }}
        >
          <Loader2 size={24} color="var(--color-student)" className="animate-spin" />
          <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>
            {isLoadingSubject ? "Loading Course Breakdown & Assessment Marks..." : "Loading Course Notes & Learning Materials..."}
          </span>
        </div>
      )}

      {/* Error Message */}
      {(subjectError || materialError) && (
        <div
          style={{
            background: "#FEF2F2",
            border: "1px solid #FECACA",
            borderRadius: "8px",
            padding: "14px 18px",
            marginBottom: "20px",
            color: "var(--color-danger)",
            fontSize: "0.85rem",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <AlertCircle size={18} />
          <span>{subjectError || materialError}</span>
        </div>
      )}

      {/* VIEW: Academic Overview */}
      {viewState === "overview" && (
        <AcademicOverview
          token={token}
          onSelectSubject={handleSelectSubject}
        />
      )}

      {/* VIEW: Subject Detail */}
      {viewState === "subject_detail" && subjectDetail && (
        <SubjectDetailView
          detail={subjectDetail}
          onBack={handleBackToOverview}
          onStudyModule={handleStudyModule}
        />
      )}

      {/* VIEW: Material Reader */}
      {viewState === "material_reader" && materialData && (
        <MaterialReader
          materialData={materialData}
          token={token}
          onBack={handleBackToSubject}
          onOpenMicroLesson={handleOpenMicroLesson}
        />
      )}

      {/* MODAL: Micro-Lesson Video-Like Player */}
      {activeLessonResponse && (
        <MicroLessonPlayer
          lesson={activeLessonResponse.lesson}
          generation={activeLessonResponse.generation}
          isOpen={isLessonPlayerOpen}
          onClose={() => setIsLessonPlayerOpen(false)}
          onAskFollowup={handleAskFollowup}
        />
      )}
    </div>
  );
};
