import { Component, computed, input } from '@angular/core';

export interface StatusChartDatum {
  key: string;
  label: string;
  value: number;
  colorVar: 'neutral' | 'good' | 'warning' | 'critical';
}

/**
 * Horizontal bar list for "claims by status". Each row already carries its
 * own text label and numeric value, so identity is never color-alone and no
 * separate legend is needed — the direct label *is* the legend here.
 */
@Component({
  selector: 'app-status-bar-chart',
  standalone: true,
  templateUrl: './status-bar-chart.html',
  styleUrl: './status-bar-chart.scss',
})
export class StatusBarChart {
  readonly data = input.required<StatusChartDatum[]>();

  readonly maxValue = computed(() => Math.max(1, ...this.data().map((d) => d.value)));
  readonly total = computed(() => this.data().reduce((sum, d) => sum + d.value, 0));

  widthFor(value: number): number {
    return this.maxValue() === 0 ? 0 : (value / this.maxValue()) * 100;
  }
}
