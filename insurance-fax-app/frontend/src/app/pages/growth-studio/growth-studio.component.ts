import { CommonModule } from "@angular/common";
import { Component, OnInit } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { RouterLink } from "@angular/router";

import {
  AgentSimulationResult,
  DiscoveryAssessment,
  FaxRecord,
  FaxService,
  FaxSummary,
  RevenueResult,
  RoiResult,
} from "../../services/fax.service";

type StudioTab = "discovery" | "architecture" | "implementation" | "impact" | "revenue";
type StepState = "done" | "current" | "pending";

const TAB_ORDER: StudioTab[] = ["discovery", "architecture", "implementation", "impact", "revenue"];
const TAB_LABELS: Record<StudioTab, string> = {
  discovery: "Discovery",
  architecture: "Architecture",
  implementation: "Implementation",
  impact: "Business Impact",
  revenue: "Revenue",
};
const TAB_SHORT_LABELS: Record<StudioTab, string> = {
  discovery: "Discovery",
  architecture: "Architecture",
  implementation: "Simulate",
  impact: "ROI",
  revenue: "Revenue",
};

/**
 * Growth Studio -- process-modernization assessment tooling (Discovery,
 * Architecture, Implementation simulation, ROI, Revenue), additive to the
 * existing claim-intake workflow. The Implementation tab never re-runs
 * OCR/extraction itself: it reuses the exact same uploaded-fax records the
 * Fax Intake pipeline already produced, and links out to the full
 * Patient Information / Received Document view for detail.
 */
@Component({
  selector: "app-growth-studio",
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: "./growth-studio.component.html",
  styleUrls: ["./growth-studio.component.scss"],
})
export class GrowthStudioComponent implements OnInit {
  tabOrder = TAB_ORDER;
  tabLabels = TAB_LABELS;
  tabShortLabels = TAB_SHORT_LABELS;
  activeTab: StudioTab = "discovery";

  // ---- Discovery ----
  processText = "";
  discoveryLoading = false;
  discoveryError = "";
  assessment: DiscoveryAssessment | null = null;

  // ---- Implementation ----
  faxOptions: FaxSummary[] = [];
  selectedFaxId = "";
  selectedFax: FaxRecord | null = null;
  faxLoadError = "";
  simulationLoading = false;
  simulationError = "";
  simulationResult: AgentSimulationResult | null = null;

  // ---- Business Impact (ROI) ----
  roiForm = { annual_volume: 200000, mins_per_request: 12, automation_pct: 0.75, cost_per_hour: 25 };
  roiLoading = false;
  roiError = "";
  roiResult: RoiResult | null = null;

  // ---- Revenue ----
  revenueForm = { touchpoints: 0, agent_count: 0, domain: "general" };
  revenueEditable = false;
  revenueLoading = false;
  revenueError = "";
  revenueResult: RevenueResult | null = null;

  constructor(private faxService: FaxService) {}

  ngOnInit(): void {
    this.loadFaxOptions();
  }

  setTab(tab: StudioTab): void {
    this.activeTab = tab;
  }

  /** Drives the pipeline stepper -- purely a visual read of state that
   * already exists (assessment / simulationResult / roiResult /
   * revenueResult), so it can never drift from what's actually happened. */
  stepState(tab: StudioTab): StepState {
    if (tab === this.activeTab) return "current";
    const done: Record<StudioTab, boolean> = {
      discovery: !!this.assessment,
      architecture: !!this.assessment,
      implementation: !!this.simulationResult,
      impact: !!this.roiResult,
      revenue: !!this.revenueResult,
    };
    return done[tab] ? "done" : "pending";
  }

  get completedStepCount(): number {
    return this.tabOrder.filter((t) => this.stepState(t) === "done").length;
  }

  // ---- Discovery ----

  runDiscovery(): void {
    const text = this.processText.trim();
    if (!text) {
      this.discoveryError = "Please paste or describe at least one step of the process.";
      return;
    }
    this.discoveryLoading = true;
    this.discoveryError = "";
    this.faxService.runDiscoveryAssessment(text).subscribe({
      next: (result) => {
        this.assessment = result;
        this.discoveryLoading = false;
        // Keep the Revenue tab's inputs in sync with the latest assessment
        // unless the manager has explicitly chosen to override them.
        if (!this.revenueEditable) {
          this.revenueForm = {
            touchpoints: result.manual_touchpoints,
            agent_count: result.recommended_agents.length,
            domain: result.domain,
          };
        }
      },
      error: () => {
        this.discoveryLoading = false;
        this.discoveryError = "Could not run the discovery assessment. Please try again.";
      },
    });
  }

  get isAiDrafted(): boolean {
    return !!this.assessment && this.assessment.assessment_source !== "rule_based";
  }

  onProcessFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    file.text().then((text) => (this.processText = text));
    input.value = "";
  }

  // ---- Implementation ----

  private loadFaxOptions(): void {
    this.faxService.listFaxes("all").subscribe({
      next: (list) => (this.faxOptions = list.filter((f) => !f.deleted)),
      error: () => (this.faxLoadError = "Could not load the list of processed faxes."),
    });
  }

  onSelectFax(faxId: string): void {
    this.selectedFaxId = faxId;
    this.simulationResult = null;
    this.simulationError = "";
    if (!faxId) {
      this.selectedFax = null;
      return;
    }
    this.faxService.getFax(faxId).subscribe({
      next: (record) => (this.selectedFax = record),
      error: () => (this.faxLoadError = "Could not load that fax record."),
    });
  }

  get canRunSimulation(): boolean {
    return !!this.assessment && !!this.selectedFax && !this.simulationLoading;
  }

  runSimulation(): void {
    if (!this.assessment || !this.selectedFax) return;
    this.simulationLoading = true;
    this.simulationError = "";
    this.faxService.runAgentSimulation(this.selectedFax.id, this.assessment.id).subscribe({
      next: (result) => {
        this.simulationResult = result;
        this.simulationLoading = false;
      },
      error: () => {
        this.simulationLoading = false;
        this.simulationError = "Could not run the agent simulation. Please try again.";
      },
    });
  }

  statusBadgeClass(status: string): string {
    if (status === "Auto-Approved") return "badge-green";
    if (status === "Human Review Required") return "badge-amber";
    return "badge-red";
  }

  // ---- Business Impact (ROI) ----

  calculateRoi(): void {
    this.roiLoading = true;
    this.roiError = "";
    this.faxService.calculateRoi(this.roiForm).subscribe({
      next: (result) => {
        this.roiResult = result;
        this.roiLoading = false;
      },
      error: () => {
        this.roiLoading = false;
        this.roiError = "Could not calculate ROI. Check the values entered and try again.";
      },
    });
  }

  formatCurrency(value: number | undefined | null): string {
    if (value === undefined || value === null) return "—";
    return "₹" + value.toLocaleString("en-IN", { maximumFractionDigits: 0 });
  }

  // ---- Revenue ----

  toggleRevenueEditable(): void {
    this.revenueEditable = !this.revenueEditable;
  }

  calculateRevenue(): void {
    this.revenueLoading = true;
    this.revenueError = "";
    this.faxService.calculateRevenue(this.revenueForm).subscribe({
      next: (result) => {
        this.revenueResult = result;
        this.revenueLoading = false;
      },
      error: () => {
        this.revenueLoading = false;
        this.revenueError = "Could not calculate the revenue opportunity. Please try again.";
      },
    });
  }
}
