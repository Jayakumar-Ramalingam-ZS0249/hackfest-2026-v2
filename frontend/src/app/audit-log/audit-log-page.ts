import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, debounceTime, distinctUntilChanged, map, of, switchMap } from 'rxjs';

import { AppCard } from '../shared/components/app-card/app-card';
import { EmptyState } from '../shared/components/empty-state/empty-state';
import { PageHero } from '../shared/components/page-hero/page-hero';
import { Skeleton } from '../shared/components/skeleton/skeleton';
import { ToolCallRecord } from '../shared/models/api-models';
import { ApiService } from '../shared/services/api.service';
import { formatDateTime } from '../shared/services/format.utils';

interface AuditResult {
  records: ToolCallRecord[];
  error: boolean;
}

const AUTOMATED_TOOL_NAMES = new Set([
  'verify_identity',
  'check_fraud_flags',
  'check_policy_compliance',
  'calculate_risk_adjusted_amount',
]);

@Component({
  selector: 'app-audit-log-page',
  standalone: true,
  imports: [PageHero, AppCard, EmptyState, Skeleton, RouterLink],
  templateUrl: './audit-log-page.html',
  styleUrl: './audit-log-page.scss',
})
export class AuditLogPage {
  private readonly api = inject(ApiService);

  protected readonly formatDateTime = formatDateTime;

  readonly applicantIdFilter = signal('');

  private readonly result = toSignal<AuditResult | null>(
    toObservable(this.applicantIdFilter).pipe(
      debounceTime(250),
      distinctUntilChanged(),
      switchMap((applicantId) =>
        this.api.getAuditLog(applicantId.trim() || undefined).pipe(
          map((records): AuditResult => ({ records, error: false })),
          catchError(() => of<AuditResult>({ records: [], error: true })),
        ),
      ),
    ),
    { initialValue: null },
  );

  readonly loading = computed(() => this.result() === null);
  readonly loadError = computed(() => this.result()?.error ?? false);

  // Newest first — an audit log reads naturally most-recent-on-top.
  readonly records = computed(() => [...(this.result()?.records ?? [])].reverse());

  setFilter(value: string): void {
    this.applicantIdFilter.set(value);
  }

  clearFilter(): void {
    this.applicantIdFilter.set('');
  }

  isHumanDecision(record: ToolCallRecord): boolean {
    return !AUTOMATED_TOOL_NAMES.has(record.tool_name);
  }

  formatRecord(value: Record<string, unknown>): string {
    const entries = Object.entries(value);
    if (entries.length === 0) return '—';
    return entries.map(([key, val]) => `${key}: ${this.formatValue(val)}`).join('  ·  ');
  }

  private formatValue(value: unknown): string {
    if (value === null || value === undefined || value === '') return '—';
    if (Array.isArray(value)) {
      return value.length === 0 ? 'none' : value.map((item) => this.formatValue(item)).join('; ');
    }
    if (typeof value === 'number') {
      return Number.isInteger(value) ? value.toString() : value.toFixed(2);
    }
    if (typeof value === 'boolean') return value ? 'yes' : 'no';
    return String(value);
  }
}
