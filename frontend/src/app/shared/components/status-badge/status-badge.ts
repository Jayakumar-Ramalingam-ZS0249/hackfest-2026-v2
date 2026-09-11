import { Component, computed, input } from '@angular/core';
import { ClaimStatus } from '../../models/api-models';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  templateUrl: './status-badge.html',
  styleUrl: './status-badge.scss',
})
export class StatusBadge {
  readonly status = input.required<ClaimStatus>();

  readonly label = computed(() => STATUS_LABELS[this.status()] ?? this.status());
}

const STATUS_LABELS: Record<ClaimStatus, string> = {
  pending_review: 'Pending review',
  approved: 'Approved',
  rejected: 'Rejected',
  needs_human_review: 'Needs review',
};
