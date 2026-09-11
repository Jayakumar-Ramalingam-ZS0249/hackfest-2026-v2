import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AppButton } from '../shared/components/app-button/app-button';
import { AppCard } from '../shared/components/app-card/app-card';
import { EmptyState } from '../shared/components/empty-state/empty-state';
import { PageHero } from '../shared/components/page-hero/page-hero';
import { Skeleton } from '../shared/components/skeleton/skeleton';
import { StatusBadge } from '../shared/components/status-badge/status-badge';
import { VerificationBadge } from '../shared/components/verification-badge/verification-badge';
import { Applicant, DecisionAction } from '../shared/models/api-models';
import { ApiService } from '../shared/services/api.service';
import {
  formatCurrency,
  formatDateTime,
  formatPercent,
  formatRelativeTime,
  formatTitleCase,
} from '../shared/services/format.utils';

@Component({
  selector: 'app-applicant-detail-page',
  standalone: true,
  imports: [PageHero, AppCard, AppButton, StatusBadge, VerificationBadge, EmptyState, Skeleton, RouterLink],
  templateUrl: './applicant-detail-page.html',
  styleUrl: './applicant-detail-page.scss',
})
export class ApplicantDetailPage {
  private readonly api = inject(ApiService);

  // Bound automatically from the `:id` route param via withComponentInputBinding().
  readonly id = input.required<string>();

  protected readonly formatCurrency = formatCurrency;
  protected readonly formatPercent = formatPercent;
  protected readonly formatDateTime = formatDateTime;
  protected readonly formatRelativeTime = formatRelativeTime;
  protected readonly formatTitleCase = formatTitleCase;

  readonly applicant = signal<Applicant | null>(null);
  readonly loading = signal(true);
  readonly notFound = signal(false);
  readonly loadError = signal<string | null>(null);

  readonly reviewRunning = signal(false);
  readonly reviewError = signal<string | null>(null);

  readonly decisionSubmitting = signal<DecisionAction | null>(null);
  readonly decisionError = signal<string | null>(null);
  readonly reviewerName = signal('');
  readonly decisionNotes = signal('');

  readonly isFinalized = computed(() => {
    const status = this.applicant()?.status;
    return status === 'approved' || status === 'rejected';
  });

  readonly canSubmitDecision = computed(() => this.reviewerName().trim().length > 0);

  readonly amountComparison = computed(() => {
    const applicant = this.applicant();
    const rec = applicant?.ai_recommendation;
    if (!applicant || !rec) return null;
    if (rec.approved_amount === null) return null;
    return {
      requested: applicant.claim_amount_requested,
      approved: rec.approved_amount,
      reduced: rec.approved_amount < applicant.claim_amount_requested,
      reductionPercent:
        applicant.claim_amount_requested > 0
          ? 1 - rec.approved_amount / applicant.claim_amount_requested
          : 0,
    };
  });

  readonly toolNamesUsed = computed(() => {
    const rec = this.applicant()?.ai_recommendation;
    if (!rec) return [] as string[];
    const seen = new Set<string>();
    const ordered: string[] = [];
    for (const call of rec.tool_calls) {
      if (!seen.has(call.tool_name)) {
        seen.add(call.tool_name);
        ordered.push(call.tool_name);
      }
    }
    return ordered;
  });

  constructor() {
    effect(() => {
      const id = this.id();
      this.fetchApplicant(id);
    });
  }

  private fetchApplicant(applicantId: string): void {
    this.loading.set(true);
    this.loadError.set(null);
    this.notFound.set(false);

    this.api.getApplication(applicantId).subscribe({
      next: (applicant) => {
        this.applicant.set(applicant);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        const status = (err as { status?: number } | null)?.status;
        this.notFound.set(status === 404);
        this.loadError.set(
          status === 404
            ? `No applicant found with ID "${applicantId}".`
            : 'Could not reach the Claims Copilot API. Make sure the backend is running on http://localhost:8000.',
        );
        this.loading.set(false);
      },
    });
  }

  runReview(): void {
    const applicant = this.applicant();
    if (!applicant || this.reviewRunning()) return;

    this.reviewRunning.set(true);
    this.reviewError.set(null);

    this.api.runAiReview(applicant.applicant_id).subscribe({
      next: (recommendation) => {
        this.applicant.update((current) => (current ? { ...current, ai_recommendation: recommendation } : current));
        this.reviewRunning.set(false);
      },
      error: () => {
        this.reviewError.set(
          'The AI review could not complete right now. You can try again, or record a manual decision below — nothing here depends on the AI to keep working.',
        );
        this.reviewRunning.set(false);
      },
    });
  }

  submitDecision(decision: DecisionAction): void {
    const applicant = this.applicant();
    if (!applicant || this.decisionSubmitting() || !this.canSubmitDecision()) return;

    this.decisionSubmitting.set(decision);
    this.decisionError.set(null);

    this.api
      .submitDecision(applicant.applicant_id, {
        decision,
        decided_by: this.reviewerName().trim(),
        notes: this.decisionNotes().trim() || null,
      })
      .subscribe({
        next: (updated) => {
          this.applicant.set(updated);
          this.decisionSubmitting.set(null);
        },
        error: () => {
          this.decisionError.set('Could not record your decision. Please try again.');
          this.decisionSubmitting.set(null);
        },
      });
  }
}
