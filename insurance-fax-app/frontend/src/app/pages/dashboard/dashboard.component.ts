import { CommonModule } from "@angular/common";
import { Component } from "@angular/core";

import { TransformationFunnelComponent } from "../../components/transformation-funnel/transformation-funnel.component";

/**
 * Dashboard shows only the Transformation Factory funnel -- a navigational
 * entry point into Growth Studio / Governance / Managed Operations, not a
 * claims-data view. No data fetching happens here.
 */
@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [CommonModule, TransformationFunnelComponent],
  templateUrl: "./dashboard.component.html",
  styleUrls: ["./dashboard.component.scss"],
})
export class DashboardComponent {}
