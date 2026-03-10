/**
 * TypeScript interfaces matching the backend Pydantic schemas.
 * Source of truth: backend/schemas/review.py
 */

// ---------------------------------------------------------------------------
// File types
// ---------------------------------------------------------------------------

export interface FileUploadResponse {
  file_id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
}

export interface FileInfo {
  file_id: string;
  review_id: string | null;
  filename: string;
  file_type: string;
  size_bytes: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Review request/response types
// ---------------------------------------------------------------------------

export interface StartReviewRequest {
  file_ids: string[];
  journal_name: string;
  domain_general: string;
  domain_specific: string;
  llm_provider?: string | null;
  llm_model?: string | null;
}

export interface StartReviewResponse {
  review_id: string;
  status: string;
  message: string;
}

export interface ReviewSummary {
  review_id: string;
  status: string;
  paper_title: string | null;
  journal_name: string | null;
  domain_general: string | null;
  domain_specific: string | null;
  llm_provider: string | null;
  llm_model: string | null;
  recommendation: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ReviewListResponse {
  reviews: ReviewSummary[];
  total: number;
}

// ---------------------------------------------------------------------------
// Review status types
// ---------------------------------------------------------------------------

export interface AgentStatus {
  name: string;
  status: string;
  progress_percent: number;
  current_task: string | null;
}

export interface ReviewStatusResponse {
  review_id: string;
  status: string;
  current_step: string;
  progress_percent: number;
  agent_statuses: Record<string, AgentStatus>;
  estimated_time_remaining: number | null;
}

// ---------------------------------------------------------------------------
// Desk check types
// ---------------------------------------------------------------------------

export interface DeskCheckResult {
  passed: boolean;
  scope_check: Record<string, unknown>;
  formatting_check: Record<string, unknown>;
  formatting_confidence: number;
  issues: string[];
}

// ---------------------------------------------------------------------------
// Report types
// ---------------------------------------------------------------------------

export interface ReviewScore {
  category: string;
  score: number;
  reviewer_scores: Record<string, number>;
}

export interface ReviewerReport {
  reviewer_type: string;
  scores: Record<string, number>;
  feedback: Record<string, string>;
  evidence: Record<string, unknown>[];
  recommendation: string;
  strengths: string[];
  weaknesses: string[];
}

export interface ReviewReport {
  review_id: string;
  recommendation: string;
  confidence: string;
  key_strengths: string[];
  key_weaknesses: string[];
  scores: ReviewScore[];
  detailed_feedback: Record<string, string>;
  suggested_improvements: string[];
  individual_reviews: ReviewerReport[];
  desk_check: DeskCheckResult | null;
  created_at: string;
}

export interface ReviewReportResponse {
  review_id: string;
  status: string;
  report: ReviewReport;
}

// ---------------------------------------------------------------------------
// Feedback types
// ---------------------------------------------------------------------------

export interface FeedbackRequest {
  rating: number;
  category_ratings?: Record<string, number> | null;
  comments?: string | null;
}

// ---------------------------------------------------------------------------
// Settings types
// ---------------------------------------------------------------------------

export interface SettingsResponse {
  llm: Record<string, unknown>;
  mcp: Record<string, unknown>;
  apis: Record<string, unknown>;
  agents: Record<string, unknown>;
}

export interface SettingsUpdateRequest {
  llm?: Record<string, unknown>;
  mcp?: Record<string, unknown>;
  apis?: Record<string, unknown>;
  agents?: Record<string, unknown>;
}

export interface TestConnectionRequest {
  provider: string;
  model: string;
  api_key?: string | null;
}

export interface TestConnectionResponse {
  success: boolean;
  latency_ms: number | null;
  model_info: string | null;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Chat types
// ---------------------------------------------------------------------------

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatEvent {
  type: "token" | "complete" | "error";
  content?: string;
  message?: string;
}

// ---------------------------------------------------------------------------
// Metrics types
// ---------------------------------------------------------------------------

export interface MetricsDashboard {
  total_reviews: number;
  completed_reviews: number;
  failed_reviews: number;
  in_progress_reviews: number;
  completion_rate: number;
  avg_review_duration_ms: number | null;
  total_llm_cost_usd: number;
}

// ---------------------------------------------------------------------------
// WebSocket event types
// ---------------------------------------------------------------------------

export interface ReviewEvent {
  type: "progress" | "step_complete" | "complete" | "error" | "info";
  step?: string;
  agent?: string;
  progress?: number;
  message?: string;
  result?: Record<string, unknown>;
  report_id?: string;
}
