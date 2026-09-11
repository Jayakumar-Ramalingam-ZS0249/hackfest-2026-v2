import { Component, computed, input } from '@angular/core';
import { AppCard } from '../app-card/app-card';

export type KpiAccent = 'blue' | 'green' | 'amber' | 'purple';

/**
 * Dashboard stat tile: label (sentence case), a large value, and an optional
 * hint line. Value is passed in already formatted — this component is purely
 * presentational.
 */
@Component({
  selector: 'app-kpi-card',
  standalone: true,
  imports: [AppCard],
  templateUrl: './kpi-card.html',
  styleUrl: './kpi-card.scss',
})
export class KpiCard {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
  readonly hint = input<string | null>(null);
  readonly accent = input<KpiAccent>('blue');

  readonly hostClass = computed(() => `kpi-card kpi-card--${this.accent()}`);
}
