import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';

import { AppCard } from '../shared/components/app-card/app-card';
import { EmptyState } from '../shared/components/empty-state/empty-state';
import { KpiCard } from '../shared/components/kpi-card/kpi-card';
import { PageHero } from '../shared/components/page-hero/page-hero';
import { Skeleton } from '../shared/components/skeleton/skeleton';
import { StatusBarChart, StatusChartDatum } from '../shared/components/status-bar-chart/status-bar-chart';
import { Applicant, DashboardSummary } from '../shared/models/api-models';
import { ApiService } from '../shared/services/api.service';
import { formatCurrencyCompact, formatDurationMinutes } from '../shared/services/format.utils';

interface DashboardData {
  summary: DashboardSummary | null;
  attentionList: Applicant[];
}

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [PageHero, AppCard, KpiCard, StatusBarChart, EmptyState, Skeleton, RouterLink],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage {
  private readonly api = inject(ApiService);

  protected readonly formatCurrencyCompact = formatCurrencyCompact;
  protected readonly formatDurationMinutes = formatDurationMinutes;

  private readonly data = toSignal<DashboardData | null>(
    forkJoin({
      summary: this.api.getDashboardSummary(),
      attentionList: this.api.getApplications({ status: 'needs_human_review' }),
    }).pipe(
      catchError(() => of<DashboardData>({ summary: null, attentionList: [] })),
    ),
    { initialValue: null },
  );

  readonly loading = computed(() => this.data() === null);
  readonly summary = computed(() => this.data()?.summary ?? null);
  readonly attentionList = computed(() => this.data()?.attentionList ?? []);
  readonly loadError = computed(() => this.data() !== null && this.summary() === null);

  readonly statusChartData = computed<StatusChartDatum[]>(() => {
    const byStatus = this.summary()?.claims_by_status ?? {};
    return [
      { key: 'pending_review', label: 'Pending review', value: byStatus['pending_review'] ?? 0, colorVar: 'neutral' },
      { key: 'needs_human_review', label: 'Needs review', value: byStatus['needs_human_review'] ?? 0, colorVar: 'warning' },
      { key: 'approved', label: 'Approved', value: byStatus['approved'] ?? 0, colorVar: 'good' },
      { key: 'rejected', label: 'Rejected', value: byStatus['rejected'] ?? 0, colorVar: 'critical' },
    ];
  });
}
