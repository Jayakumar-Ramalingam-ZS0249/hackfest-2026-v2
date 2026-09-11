import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  AiRecommendation,
  Applicant,
  ApplicationListParams,
  DashboardSummary,
  DecisionRequest,
  HealthStatus,
  ToolCallRecord,
} from '../models/api-models';
import { API_BASE_URL } from './api-config';

/**
 * Thin, typed wrapper around the FastAPI backend. Every AI review and every
 * human decision goes through here — nothing in the UI talks to the backend
 * any other way, so this is the one place the REST contract is spelled out.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  getApplications(params: ApplicationListParams = {}): Observable<Applicant[]> {
    let httpParams = new HttpParams();
    if (params.status) httpParams = httpParams.set('status', params.status);
    if (params.sort_by) httpParams = httpParams.set('sort_by', params.sort_by);
    if (params.order) httpParams = httpParams.set('order', params.order);
    return this.http.get<Applicant[]>(`${API_BASE_URL}/applications`, { params: httpParams });
  }

  getApplication(applicantId: string): Observable<Applicant> {
    return this.http.get<Applicant>(`${API_BASE_URL}/applications/${applicantId}`);
  }

  runAiReview(applicantId: string): Observable<AiRecommendation> {
    return this.http.post<AiRecommendation>(`${API_BASE_URL}/applications/${applicantId}/ai-review`, {});
  }

  submitDecision(applicantId: string, body: DecisionRequest): Observable<Applicant> {
    return this.http.post<Applicant>(`${API_BASE_URL}/applications/${applicantId}/decision`, body);
  }

  getAuditLog(applicantId?: string): Observable<ToolCallRecord[]> {
    let httpParams = new HttpParams();
    if (applicantId) httpParams = httpParams.set('applicant_id', applicantId);
    return this.http.get<ToolCallRecord[]>(`${API_BASE_URL}/audit-log`, { params: httpParams });
  }

  getDashboardSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${API_BASE_URL}/dashboard/summary`);
  }

  getHealth(): Observable<HealthStatus> {
    return this.http.get<HealthStatus>(`${API_BASE_URL}/health`);
  }
}
