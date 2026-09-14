import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// Point this at wherever the FastAPI backend is actually running.
// In production, move this into an environment.ts file.
const API_BASE = 'http://localhost:8000/api';

export interface FieldResult {
  value: string;
  confidence: number;
  status: 'auto_fill' | 'needs_review';
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
  fields: Record<string, FieldResult>;
  eligibility: EligibilityResult;
  overall_confidence: number;
  needs_review_count: number;
  status: 'auto_filled' | 'needs_review' | 'resolved';
  provenance: { tool: string; run_id: string; timestamp: string }[];
}

export interface FaxSummary {
  id: string;
  filename: string;
  received_at: string;
  status: string;
  overall_confidence: number;
  needs_review_count: number;
}

@Injectable({ providedIn: 'root' })
export class FaxService {
  constructor(private http: HttpClient) {}

  uploadFax(file: File): Observable<FaxRecord> {
    const formData = new FormData();
    formData.append('file', file);
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
    reviewer: string
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
}
