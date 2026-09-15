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

export interface FaxSummary {
  id: string;
  filename: string;
  received_at: string;
  status: string;
  overall_confidence: number;
  needs_review_count: number;
  matchScore?: number;
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

export interface HealthStatus {
  status: string;
  aiProvider: string;
}

export interface DashboardStatistics {
  totalClaims: number;
  resolved: number;
  needsReview: number;
  invalidDocuments: number;
  autoFilled: number;
  averageConfidence: number;
}

@Injectable({ providedIn: "root" })
export class FaxService {
  constructor(private http: HttpClient) {}

  uploadFax(file: File): Observable<FaxRecord> {
    const formData = new FormData();
    formData.append("file", file);
    return this.http.post<FaxRecord>(`${API_BASE}/faxes/upload`, formData);
  }

  listFaxes(): Observable<FaxSummary[]> {
    return this.http.get<FaxSummary[]>(`${API_BASE}/faxes`);
  }

  getFax(id: string): Observable<FaxRecord> {
    return this.http.get<FaxRecord>(`${API_BASE}/faxes/${id}`);
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

  getHealth(): Observable<HealthStatus> {
    return this.http.get<HealthStatus>(`${API_BASE}/health`);
  }
}
