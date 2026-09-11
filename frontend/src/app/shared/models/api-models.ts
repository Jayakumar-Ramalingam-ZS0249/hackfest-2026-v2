// TypeScript mirrors of the backend's Pydantic schemas (backend/app/models/schemas.py).
// Field names and shapes must stay in lockstep with that file.

export type ClaimStatus = 'pending_review' | 'approved' | 'rejected' | 'needs_human_review';

export type ClaimType =
  | 'Hospitalization'
  | 'Surgery'
  | 'Outpatient'
  | 'Critical Illness'
  | 'Maternity'
  | 'Accident';

export type RecommendationAction = 'approve' | 'reject' | 'escalate';

export type DecisionAction = 'approved' | 'rejected' | 'more_info';

export type AiEngine = 'claude' | 'fallback_rules';

export interface ToolCallRecord {
  id: number;
  applicant_id: string;
  tool_name: string;
  timestamp: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
}

export interface AiRecommendation {
  applicant_id: string;
  recommendation: RecommendationAction;
  approved_amount: number | null;
  rationale: string;
  tool_calls: ToolCallRecord[];
  generated_at: string;
  engine: AiEngine;
}

export interface Applicant {
  applicant_id: string;
  name: string;
  aadhar_number: string;
  aadhar_verified: boolean;
  pan_number: string;
  pan_verified: boolean;
  claim_type: ClaimType;
  claim_amount_requested: number;
  policy_tenure_years: number;
  prior_claims_count: number;
  risk_score: number;
  status: ClaimStatus;
  approved_amount: number | null;
  ai_recommendation: AiRecommendation | null;
  submitted_at: string;
  last_updated: string;
  decided_by: string | null;
  decision_notes: string | null;
}

export interface DecisionRequest {
  decision: DecisionAction;
  decided_by: string;
  notes?: string | null;
  override_amount?: number | null;
}

export interface DashboardSummary {
  total_applications: number;
  total_pending: number;
  total_approved_today: number;
  total_rejected_today: number;
  avg_processing_time_minutes: number;
  total_value_approved: number;
  claims_by_status: Record<string, number>;
}

export interface HealthStatus {
  status: string;
  claude_configured: boolean;
  model: string;
}

export interface ApplicationListParams {
  status?: ClaimStatus;
  sort_by?: 'risk_score' | 'claim_amount_requested' | 'policy_tenure_years' | 'prior_claims_count' | 'last_updated' | 'submitted_at' | 'name';
  order?: 'asc' | 'desc';
}
