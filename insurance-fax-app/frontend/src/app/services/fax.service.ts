import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";

// Point this at wherever the FastAPI backend is actually running.
// In production, move this into an environment.ts file.
const API_BASE = "http://localhost:8000/api";

export type FieldStatus = "auto_fill" | "needs_review" | "not_found";
export type FieldValidationStatus = "verified" | "review_required" | "unverified" | "conflict" | "not_found";
export type VerificationStatus = "VERIFIED" | "UNVERIFIED" | "NOT_APPLICABLE";

export interface FieldConflict {
  page: number;
  value: string;
}

export interface FieldResult {
  value: string | null;
  confidence: number;
  status: FieldStatus;
  sourceText?: string | null;
  validationStatus?: FieldValidationStatus;
  page?: number | null;
  verificationStatus?: VerificationStatus;
  conflicts?: FieldConflict[];
  managerVerified?: boolean;
}

export interface DocumentAnalysis {
  documentType: string;
  matchScore: number;
  status: "valid" | "review_required" | "invalid";
  validationMessage: string;
  summary: string;
  reasons?: string[];
  needsOcr?: boolean;
  ocrUsed?: boolean;
  ocrAvailable?: boolean;
}

export interface EligibilityResult {
  found: boolean;
  client: string | null;
  client_code?: string;
  plan: string | null;
  plan_code?: string;
  group_no: string | null;
  eligibility_status: string;
  eligibility_start_date?: string;
  eligibility_end_date?: string;
}

export interface FaxRecord {
  id: string;
  filename: string;
  received_at: string;
  raw_text: string;
  pages?: string[];
  fields: Record<string, FieldResult>;
  eligibility: EligibilityResult;
  document: DocumentAnalysis;
  overall_confidence: number;
  needs_review_count: number;
  status: "auto_filled" | "needs_review" | "resolved" | "invalid";
  provenance: { tool: string; run_id: string; timestamp: string }[];
  extractionSource?: "ai" | "gemini" | "rule_based" | null;
  aiError?: string | null;
}

export type QueueFilter = "all" | "needs_review" | "resolved" | "invalid" | "queued" | "deleted";

export interface FaxSummary {
  id: string;
  filename: string;
  received_at: string;
  status: string;
  overall_confidence: number;
  needs_review_count: number;
  matchScore?: number;
  deleted?: boolean;
  patientName?: string | null;
}

export interface ChatSource {
  field: string | null;
  page: number | null;
  sourceText: string | null;
}

export interface ChatResponse {
  success: boolean;
  answer: string;
  sources: ChatSource[];
  conversationId: string;
  clarificationOptions?: string[];
}

export interface ChatMessageHistory {
  id: string;
  question: string;
  answer: string;
  sources: ChatSource[];
  createdAt: string;
  clarificationOptions?: string[];
}

export interface DiscoveryAssessment {
  id: string;
  process_name: string;
  domain: string;
  whitelist: string[];
  human_actors: number;
  manual_touchpoints: number;
  agent_suitability_score: number;
  recommended_agents: string[];
  rejected_agents: string[];
  current_state: string;
  future_state: string;
  roadmap: string[];
  assessment_source: string;
}

export interface AgentOutput {
  name: string;
  output: string;
  reasoning: string;
}

export interface PolicyAgentResult {
  exception_flagged: boolean;
  reason: string;
  reasoning: string;
}

export interface AgentSimulationResult {
  agents: AgentOutput[];
  policy_agent: PolicyAgentResult;
  final_status: string;
  skipped_ai_call: boolean;
  reasoning_per_agent: Record<string, string>;
  fax_id: string;
  assessment_id: string;
}

export interface RoiRequest {
  annual_volume: number;
  mins_per_request: number;
  automation_pct: number;
  cost_per_hour: number;
}

export interface RoiResult {
  current_hours: number;
  future_hours: number;
  saved_hours: number;
  annual_savings: number;
}

export interface RevenueRequest {
  touchpoints: number;
  agent_count: number;
  domain: string;
}

export interface RevenueResult {
  assessment: number;
  architecture: number;
  implementation: number;
  governance: number;
  managed: number;
  total: number;
  domain: string;
}

export interface UploadStatus {
  stage: string;
  label: string;
  percent: number;
  done: boolean;
  error: string | null;
  result: FaxRecord | null;
}

export interface HealthStatus {
  status: string;
  aiProvider: string;
}

export interface GovernancePolicy {
  invalidMatchThreshold: number;
  reviewMatchThreshold: number;
  lowConfidenceThreshold: number;
  aiProvider: string;
  aiConfigured: boolean;
}

export interface DashboardStatistics {
  totalClaims: number;
  resolved: number;
  needsReview: number;
  invalidDocuments: number;
  autoFilled: number;
  deleted: number;
  averageConfidence: number;
}

export interface DashboardOverviewFilters {
  from?: string | null;
  to?: string | null;
  status?: string;
  confidence?: string;
  insurance?: string;
}

export interface DashboardFinancial {
  available: boolean;
  currency?: string;
  totalClaimValue?: number;
  approvedValue?: number;
  pendingValue?: number;
  rejectedValue?: number;
}

export interface StatusDistributionEntry {
  status: string;
  count: number;
  percentage: number;
}

export interface DocumentAnalytics {
  uploaded: number;
  processed: number;
  ocrRequired: number;
  ocrCompleted: number;
  invalid: number;
}

export interface QualityAnalytics {
  highConfidenceFields: number;
  mediumConfidenceFields: number;
  lowConfidenceFields: number;
  documentsRequiringReview: number;
  ocrDocuments: number;
  validationFailures: number;
  sourceMappingSuccessRate: number;
}

export interface InsuranceProviderStat {
  provider: string;
  claims: number;
  totalValue: number;
  approved: number;
  pending: number;
}

export interface TrendPoint {
  date: string;
  submitted: number;
  resolved: number;
  needsReview: number;
  invalid: number;
  queued: number;
}

export interface RecentActivityEntry {
  timestamp: string;
  claimId: string;
  patient: string | null;
  action: string;
  status: string | null;
  user: string;
}

export interface AttentionItem {
  claimId: string;
  filename: string;
  reason: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  issueCount: number;
  lastUpdated: string;
  matchScore: number;
}

export interface DashboardOverview {
  summary: {
    totalClaims: number;
    pendingReview: number;
    queued: number;
    resolved: number;
    invalid: number;
  };
  financial: DashboardFinancial;
  statusDistribution: StatusDistributionEntry[];
  documentAnalytics: DocumentAnalytics;
  quality: QualityAnalytics;
  insuranceProviders: InsuranceProviderStat[];
  trends: TrendPoint[];
  recentActivity: RecentActivityEntry[];
  attentionRequired: AttentionItem[];
}

@Injectable({ providedIn: "root" })
export class FaxService {
  constructor(private http: HttpClient) {}

  listFaxes(status: QueueFilter = "all"): Observable<FaxSummary[]> {
    return this.http.get<FaxSummary[]>(`${API_BASE}/faxes`, { params: { status } });
  }

  /** Starts background processing and returns immediately with a job id --
   * poll getUploadStatus() for real per-stage progress instead of one long wait. */
  startUpload(file: File): Observable<{ jobId: string }> {
    const formData = new FormData();
    formData.append("file", file);
    return this.http.post<{ jobId: string }>(`${API_BASE}/faxes/upload-async`, formData);
  }

  getUploadStatus(jobId: string): Observable<UploadStatus> {
    return this.http.get<UploadStatus>(`${API_BASE}/faxes/upload-status/${jobId}`);
  }

  getFax(id: string): Observable<FaxRecord> {
    return this.http.get<FaxRecord>(`${API_BASE}/faxes/${id}`);
  }

  deleteClaim(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${API_BASE}/claims/${id}`);
  }

  restoreClaim(id: string): Observable<FaxRecord> {
    return this.http.post<FaxRecord>(`${API_BASE}/claims/${id}/restore`, {});
  }

  submitDecision(
    id: string,
    approved: boolean,
    corrections: Record<string, string>,
    reviewer: string,
  ): Observable<FaxRecord> {
    return this.http.post<FaxRecord>(`${API_BASE}/faxes/${id}/decision`, {
      approved,
      corrections,
      reviewer,
    });
  }

  getAuditLog(id: string): Observable<any[]> {
    return this.http.get<any[]>(`${API_BASE}/faxes/${id}/audit-log`);
  }

  reprocessDocument(id: string): Observable<FaxRecord> {
    return this.http.post<FaxRecord>(`${API_BASE}/documents/${id}/reprocess`, {});
  }

  sendChatMessage(claimId: string, message: string, conversationId?: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${API_BASE}/claims/${claimId}/chat`, {
      message,
      conversationId: conversationId ?? null,
    });
  }

  getChatHistory(claimId: string): Observable<ChatMessageHistory[]> {
    return this.http.get<ChatMessageHistory[]>(`${API_BASE}/claims/${claimId}/chat`);
  }

  startNewChat(claimId: string): Observable<{ success: boolean; conversationId: string }> {
    return this.http.post<{ success: boolean; conversationId: string }>(`${API_BASE}/claims/${claimId}/chat/new`, {});
  }

  getQuickActions(claimId: string): Observable<{ actions: string[] }> {
    return this.http.get<{ actions: string[] }>(`${API_BASE}/claims/${claimId}/chat/quick-actions`);
  }

  getDashboardStatistics(): Observable<DashboardStatistics> {
    return this.http.get<DashboardStatistics>(`${API_BASE}/dashboard/statistics`);
  }

  getDashboardOverview(filters: DashboardOverviewFilters): Observable<{ success: boolean; data: DashboardOverview }> {
    const params: Record<string, string> = {};
    if (filters.from) params["from"] = filters.from;
    if (filters.to) params["to"] = filters.to;
    if (filters.status) params["status"] = filters.status;
    if (filters.confidence) params["confidence"] = filters.confidence;
    if (filters.insurance) params["insurance"] = filters.insurance;
    return this.http.get<{ success: boolean; data: DashboardOverview }>(`${API_BASE}/dashboard/overview`, { params });
  }

  getInsuranceProviders(): Observable<string[]> {
    return this.http.get<string[]>(`${API_BASE}/dashboard/providers`);
  }

  exportDashboard(filters: DashboardOverviewFilters): Observable<Blob> {
    const params: Record<string, string> = {};
    if (filters.from) params["from"] = filters.from;
    if (filters.to) params["to"] = filters.to;
    if (filters.status) params["status"] = filters.status;
    if (filters.confidence) params["confidence"] = filters.confidence;
    if (filters.insurance) params["insurance"] = filters.insurance;
    return this.http.get(`${API_BASE}/dashboard/export`, { params, responseType: "blob" });
  }

  // ---- Growth Studio: Discovery / Implementation simulation / ROI / Revenue ----

  runDiscoveryAssessment(processText: string): Observable<DiscoveryAssessment> {
    return this.http.post<DiscoveryAssessment>(`${API_BASE}/discovery/assess`, { process_text: processText });
  }

  getDiscoveryAssessment(assessmentId: string): Observable<DiscoveryAssessment> {
    return this.http.get<DiscoveryAssessment>(`${API_BASE}/discovery/${assessmentId}`);
  }

  runAgentSimulation(faxId: string, assessmentId: string): Observable<AgentSimulationResult> {
    return this.http.post<AgentSimulationResult>(`${API_BASE}/implementation/simulate`, {
      fax_id: faxId,
      assessment_id: assessmentId,
    });
  }

  calculateRoi(payload: RoiRequest): Observable<RoiResult> {
    return this.http.post<RoiResult>(`${API_BASE}/roi/calculate`, payload);
  }

  calculateRevenue(payload: RevenueRequest): Observable<RevenueResult> {
    return this.http.post<RevenueResult>(`${API_BASE}/revenue/calculate`, payload);
  }

  /** Backend TTS -- returns real playable audio bytes for the exact text given. */
  synthesizeSpeech(text: string): Observable<Blob> {
    return this.http.post(`${API_BASE}/ai/tts`, { text }, { responseType: "blob" });
  }

  getHealth(): Observable<HealthStatus> {
    return this.http.get<HealthStatus>(`${API_BASE}/health`);
  }

  getGovernancePolicy(): Observable<GovernancePolicy> {
    return this.http.get<GovernancePolicy>(`${API_BASE}/governance/policy`);
  }
}
