import { CommonModule } from "@angular/common";
import { Component, OnInit } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { RouterLink } from "@angular/router";

import {
  AttentionItem,
  DashboardOverview,
  DashboardOverviewFilters,
  FaxService,
} from "../../services/fax.service";

type DatePreset = "today" | "yesterday" | "last7" | "last30" | "this_month" | "last_month" | "this_quarter" | "custom";

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: "./dashboard.component.html",
  styleUrls: ["./dashboard.component.scss"],
})
export class DashboardComponent implements OnInit {
  overview: DashboardOverview | null = null;
  providers: string[] = [];
  loading = true;
  error = "";
  lastUpdated: Date | null = null;
  filtersOpen = false;
  exporting = false;

  datePreset: DatePreset = "this_month";
  customFrom = "";
  customTo = "";
  statusFilter = "all";
  confidenceFilter = "all";
  insuranceFilter = "all";

  constructor(private faxService: FaxService) {}

  ngOnInit(): void {
    this.faxService.getInsuranceProviders().subscribe({ next: (p) => (this.providers = p), error: () => {} });
    this.refresh();
  }

  // Local-calendar date formatting -- deliberately not toISOString(), which
  // converts to UTC first and can shift the boundary day depending on the
  // viewer's timezone.
  private formatLocalDate(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  private computeRange(): { from: string | null; to: string | null } {
    const today = new Date();
    const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const todayStart = startOfDay(today);

    switch (this.datePreset) {
      case "today":
        return { from: this.formatLocalDate(todayStart), to: this.formatLocalDate(todayStart) };
      case "yesterday": {
        const d = new Date(todayStart);
        d.setDate(d.getDate() - 1);
        return { from: this.formatLocalDate(d), to: this.formatLocalDate(d) };
      }
      case "last7": {
        const from = new Date(todayStart);
        from.setDate(from.getDate() - 6);
        return { from: this.formatLocalDate(from), to: this.formatLocalDate(todayStart) };
      }
      case "last30": {
        const from = new Date(todayStart);
        from.setDate(from.getDate() - 29);
        return { from: this.formatLocalDate(from), to: this.formatLocalDate(todayStart) };
      }
      case "this_month": {
        const from = new Date(today.getFullYear(), today.getMonth(), 1);
        return { from: this.formatLocalDate(from), to: this.formatLocalDate(todayStart) };
      }
      case "last_month": {
        const from = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const to = new Date(today.getFullYear(), today.getMonth(), 0);
        return { from: this.formatLocalDate(from), to: this.formatLocalDate(to) };
      }
      case "this_quarter": {
        const quarterStartMonth = Math.floor(today.getMonth() / 3) * 3;
        const from = new Date(today.getFullYear(), quarterStartMonth, 1);
        return { from: this.formatLocalDate(from), to: this.formatLocalDate(todayStart) };
      }
      case "custom":
        return { from: this.customFrom || null, to: this.customTo || null };
      default:
        return { from: null, to: null };
    }
  }

  private currentFilters(): DashboardOverviewFilters {
    const range = this.computeRange();
    return {
      from: range.from,
      to: range.to,
      status: this.statusFilter,
      confidence: this.confidenceFilter,
      insurance: this.insuranceFilter,
    };
  }

  applyFilters(): void {
    this.filtersOpen = false;
    this.refresh();
  }

  resetFilters(): void {
    this.datePreset = "this_month";
    this.customFrom = "";
    this.customTo = "";
    this.statusFilter = "all";
    this.confidenceFilter = "all";
    this.insuranceFilter = "all";
    this.refresh();
  }

  toggleFilters(): void {
    this.filtersOpen = !this.filtersOpen;
  }

  refresh(): void {
    this.loading = true;
    this.error = "";
    this.faxService.getDashboardOverview(this.currentFilters()).subscribe({
      next: (res) => {
        this.overview = res.data;
        this.loading = false;
        this.lastUpdated = new Date();
      },
      error: () => {
        this.error = "Unable to load the dashboard. Is the backend running on port 8000?";
        this.loading = false;
      },
    });
  }

  exportCsv(): void {
    this.exporting = true;
    this.faxService.exportDashboard(this.currentFilters()).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `claims_export_${this.formatLocalDate(new Date())}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.exporting = false;
      },
      error: () => {
        this.exporting = false;
      },
    });
  }

  formatCurrency(value: number | undefined | null): string {
    if (value === undefined || value === null) return "—";
    return "₹" + value.toLocaleString("en-IN", { maximumFractionDigits: 0 });
  }

  trendMax(): number {
    if (!this.overview?.trends?.length) return 1;
    return Math.max(1, ...this.overview.trends.map((t) => t.submitted));
  }

  barHeight(value: number): string {
    return `${Math.round((value / this.trendMax()) * 100)}%`;
  }

  trendDayLabel(iso: string): string {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  priorityClass(priority: AttentionItem["priority"]): string {
    return priority === "HIGH" ? "priority-high" : priority === "MEDIUM" ? "priority-medium" : "priority-low";
  }

  relativeTime(iso: string | null | undefined): string {
    if (!iso) return "—";
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return "—";
    const diffMinutes = Math.round((Date.now() - then) / 60000);
    if (diffMinutes < 1) return "just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const hours = Math.round(diffMinutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.round(hours / 24)}d ago`;
  }
}
