import { CommonModule } from "@angular/common";
import { Component, OnInit } from "@angular/core";
import { RouterLink } from "@angular/router";

import { DashboardOverview, FaxService, GovernancePolicy, StatusDistributionEntry } from "../../services/fax.service";

interface DecisionSplitEntry extends StatusDistributionEntry {
  governanceLabel: string;
  cssClass: string;
}

const GOVERNANCE_LABELS: Record<string, { label: string; cssClass: string }> = {
  Queued: { label: "Agent Decided — Straight-Through", cssClass: "primary" },
  "Needs Review": { label: "Human Required — Pending Review", cssClass: "amber" },
  Resolved: { label: "Human Reviewed — Finalized", cssClass: "green" },
  Invalid: { label: "Agent Rejected — Data Quality", cssClass: "red" },
};

/**
 * Agent Governance Services -- stage 4 of the Transformation Factory
 * funnel. Every number here is a live read of the same policy thresholds
 * and claim data the extraction pipeline and dashboard already use --
 * there is no separate governance dataset to keep in sync.
 */
@Component({
  selector: "app-governance",
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: "./governance.component.html",
  styleUrls: ["./governance.component.scss"],
})
export class GovernanceComponent implements OnInit {
  loading = true;
  error = "";
  policy: GovernancePolicy | null = null;
  overview: DashboardOverview | null = null;

  constructor(private faxService: FaxService) {}

  ngOnInit(): void {
    this.faxService.getGovernancePolicy().subscribe({
      next: (p) => (this.policy = p),
      error: () => {},
    });
    this.faxService.getDashboardOverview({}).subscribe({
      next: (res) => {
        this.overview = res.data;
        this.loading = false;
      },
      error: () => {
        this.error = "Could not load governance data. Is the backend running on port 8000?";
        this.loading = false;
      },
    });
  }

  get decisionSplit(): DecisionSplitEntry[] {
    if (!this.overview) return [];
    return this.overview.statusDistribution.map((s) => ({
      ...s,
      governanceLabel: GOVERNANCE_LABELS[s.status]?.label ?? s.status,
      cssClass: GOVERNANCE_LABELS[s.status]?.cssClass ?? "",
    }));
  }

  get recentActivity() {
    return this.overview?.recentActivity.slice(0, 8) ?? [];
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
