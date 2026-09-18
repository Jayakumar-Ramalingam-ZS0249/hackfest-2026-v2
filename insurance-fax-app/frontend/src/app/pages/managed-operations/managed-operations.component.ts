import { CommonModule } from "@angular/common";
import { Component, OnInit } from "@angular/core";
import { RouterLink } from "@angular/router";

import { DashboardOverview, FaxService } from "../../services/fax.service";

/**
 * Managed Agent Operations -- stage 5 of the Transformation Factory funnel.
 * Deliberately lean: system health + throughput are live reads of the same
 * data the main Dashboard already computes, framed for "operate at scale"
 * rather than re-implementing the Dashboard's deeper drill-down (trend
 * chart, provider table, filters) -- this links out to that instead.
 */
@Component({
  selector: "app-managed-operations",
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: "./managed-operations.component.html",
  styleUrls: ["./managed-operations.component.scss"],
})
export class ManagedOperationsComponent implements OnInit {
  loading = true;
  error = "";
  overview: DashboardOverview | null = null;
  backendConnected: boolean | null = null;
  aiProviderLabel = "checking…";

  constructor(private faxService: FaxService) {}

  ngOnInit(): void {
    this.faxService.getHealth().subscribe({
      next: (h) => {
        this.backendConnected = true;
        this.aiProviderLabel = h.aiProvider;
      },
      error: () => {
        this.backendConnected = false;
        this.aiProviderLabel = "unavailable";
      },
    });
    this.faxService.getDashboardOverview({}).subscribe({
      next: (res) => {
        this.overview = res.data;
        this.loading = false;
      },
      error: () => {
        this.error = "Could not load operations data. Is the backend running on port 8000?";
        this.loading = false;
      },
    });
  }

  get confidenceFieldTotal(): number {
    if (!this.overview) return 0;
    const q = this.overview.quality;
    return q.highConfidenceFields + q.mediumConfidenceFields + q.lowConfidenceFields;
  }

  confidencePct(count: number): number {
    const total = this.confidenceFieldTotal;
    return total ? Math.round((count / total) * 100) : 0;
  }
}
