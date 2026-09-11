import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, map, of, switchMap } from 'rxjs';

import { AppButton } from '../shared/components/app-button/app-button';
import { AppCard } from '../shared/components/app-card/app-card';
import { EmptyState } from '../shared/components/empty-state/empty-state';
import { PageHero } from '../shared/components/page-hero/page-hero';
import { Skeleton } from '../shared/components/skeleton/skeleton';
import { StatusBadge } from '../shared/components/status-badge/status-badge';
import { AiRecommendation, Applicant, ApplicationListParams, ClaimStatus } from '../shared/models/api-models';
import { ApiService } from '../shared/services/api.service';
import { formatCurrencyCompact } from '../shared/services/format.utils';

type StatusFilter = ClaimStatus | 'all';
type SortField =
  | 'risk_score'
  | 'claim_amount_requested'
  | 'policy_tenure_years'
  | 'prior_claims_count'
  | 'last_updated';

interface FilterState {
  status: StatusFilter;
  sortBy: SortField;
  order: 'asc' | 'desc';
}

interface QueryResult {
  list: Applicant[];
  error: boolean;
}

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'pending_review', label: 'Pending review' },
  { value: 'needs_human_review', label: 'Needs review' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
];

const SORT_FIELDS: { value: SortField; label: string }[] = [
  { value: 'risk_score', label: 'Risk score' },
  { value: 'claim_amount_requested', label: 'Amount requested' },
  { value: 'policy_tenure_years', label: 'Policy tenure' },
  { value: 'prior_claims_count', label: 'Prior claims' },
  { value: 'last_updated', label: 'Last updated' },
];

@Component({
  selector: 'app-applications-page',
  standalone: true,
  imports: [PageHero, AppCard, AppButton, StatusBadge, EmptyState, Skeleton, RouterLink],
  templateUrl: './applications-page.html',
  styleUrl: './applications-page.scss',
})
export class ApplicationsPage {
  private readonly api = inject(ApiService);

  protected readonly statusFilters = STATUS_FILTERS;
  protected readonly sortFields = SORT_FIELDS;
  protected readonly formatCurrencyCompact = formatCurrencyCompact;

  private readonly filters = signal<FilterState>({ status: 'all', sortBy: 'risk_score', order: 'desc' });

  private readonly result = toSignal<QueryResult | null>(
    toObservable(this.filters).pipe(
      switchMap((state) => {
        const params: ApplicationListParams = {
          status: state.status === 'all' ? undefined : state.status,
          sort_by: state.sortBy,
          order: state.order,
        };
        return this.api.getApplications(params).pipe(
          map((list): QueryResult => ({ list, error: false })),
          catchError(() => of<QueryResult>({ list: [], error: true })),
        );
      }),
    ),
    { initialValue: null },
  );

  readonly loading = computed(() => this.result() === null);
  readonly loadError = computed(() => this.result()?.error ?? false);

  private readonly reviewingIds = signal<ReadonlySet<string>>(new Set());
  private readonly localRecommendations = signal<ReadonlyMap<string, AiRecommendation>>(new Map());
  readonly reviewError = signal<string | null>(null);

  readonly rows = computed(() => {
    const overlays = this.localRecommendations();
    return (this.result()?.list ?? []).map((applicant) => {
      const overlay = overlays.get(applicant.applicant_id);
      return overlay ? { ...applicant, ai_recommendation: overlay } : applicant;
    });
  });

  readonly statusFilter = computed(() => this.filters().status);
  readonly sortBy = computed(() => this.filters().sortBy);
  readonly order = computed(() => this.filters().order);

  setStatusFilter(status: StatusFilter): void {
    this.filters.update((state) => ({ ...state, status }));
  }

  setSortBy(sortBy: string): void {
    this.filters.update((state) => ({ ...state, sortBy: sortBy as SortField }));
  }

  toggleOrder(): void {
    this.filters.update((state) => ({ ...state, order: state.order === 'asc' ? 'desc' : 'asc' }));
  }

  isReviewing(applicantId: string): boolean {
    return this.reviewingIds().has(applicantId);
  }

  riskSeverity(score: number): 'good' | 'warning' | 'critical' {
    if (score >= 0.7) return 'critical';
    if (score >= 0.4) return 'warning';
    return 'good';
  }

  runReview(applicant: Applicant, event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    if (this.isReviewing(applicant.applicant_id)) return;

    this.reviewError.set(null);
    this.reviewingIds.update((set) => new Set(set).add(applicant.applicant_id));

    this.api.runAiReview(applicant.applicant_id).subscribe({
      next: (recommendation) => {
        this.localRecommendations.update((map) => {
          const next = new Map(map);
          next.set(applicant.applicant_id, recommendation);
          return next;
        });
        this.stopReviewing(applicant.applicant_id);
      },
      error: () => {
        this.reviewError.set(`The AI review could not complete for ${applicant.name}. Please try again.`);
        this.stopReviewing(applicant.applicant_id);
      },
    });
  }

  private stopReviewing(applicantId: string): void {
    this.reviewingIds.update((set) => {
      const next = new Set(set);
      next.delete(applicantId);
      return next;
    });
  }
}
