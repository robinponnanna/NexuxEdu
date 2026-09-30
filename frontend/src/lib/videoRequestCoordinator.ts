import {
  VideoGenerationRequest,
  VideoJobResponse,
  requestVideoGeneration,
} from "./api";

// In-memory guard to prevent duplicate video generation requests
const activeRequests = new Set<string>();
const responseCache = new Map<string, VideoJobResponse>();

/**
 * Generates a stable request key for deduplication.
 * Keyed by: student + subject + module + topic/lesson
 */
export function buildVideoRequestKey(params: {
  student_id?: number | string | null;
  subject_id?: number | null;
  module_id?: number | null;
  lesson_id?: number | null;
  topic_key?: string | null;
  topic?: string | null;
  co_code?: string | null;
}): string {
  const sid = params.student_id != null ? String(params.student_id) : "std";
  const subId = params.subject_id != null ? String(params.subject_id) : "0";
  const modId = params.module_id != null ? String(params.module_id) : "0";
  const lesId = params.lesson_id != null ? String(params.lesson_id) : "0";
  const tKey = (params.topic_key || params.topic || params.co_code || "main").trim().toLowerCase();
  return `${sid}:${subId}:${modId}:${lesId}:${tKey}`;
}

export function isVideoRequestInProgress(key: string): boolean {
  return activeRequests.has(key);
}

export function getCachedVideoJobResponse(key: string): VideoJobResponse | undefined {
  return responseCache.get(key);
}

/**
 * Initiates video generation with duplicate request protection.
 * If a request for the exact same key is currently running, returns the ongoing promise or cached response.
 */
export async function ensureVideoGenerationSafely(
  token: string,
  params: VideoGenerationRequest & { student_id?: number | string | null }
): Promise<VideoJobResponse | null> {
  const key = buildVideoRequestKey(params);

  // If already in flight, prevent duplicate network invocation
  if (activeRequests.has(key)) {
    return responseCache.get(key) || null;
  }

  activeRequests.add(key);
  try {
    const res = await requestVideoGeneration(token, params);
    responseCache.set(key, res);
    return res;
  } catch (err) {
    console.warn(`[videoRequestCoordinator] Request failed for ${key}:`, err);
    throw err;
  } finally {
    activeRequests.delete(key);
  }
}
