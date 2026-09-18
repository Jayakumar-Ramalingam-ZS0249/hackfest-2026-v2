import { CommonModule } from "@angular/common";
import { Component } from "@angular/core";
import { RouterLink } from "@angular/router";

interface ServiceLineStage {
  step: number;
  title: string;
  description: string;
  routerLink: string;
  queryParams?: Record<string, string>;
  linkLabel: string;
}

/**
 * The "Legacy-to-Agent Transformation Factory" service-line funnel,
 * embedded as a Dashboard panel. Card copy is fixed marketing text from
 * the Hackfest deck, but each card is a real link into the matching
 * working feature -- steps 1-3 deep-link into Growth Studio's existing
 * tabs, steps 4-5 open their own dedicated pages.
 */
@Component({
  selector: "app-transformation-funnel",
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: "./transformation-funnel.component.html",
  styleUrls: ["./transformation-funnel.component.scss"],
})
export class TransformationFunnelComponent {
  readonly stages: ServiceLineStage[] = [
    {
      step: 1,
      title: "Agent Discovery Assessment",
      description: "Identify transformation opportunities.",
      routerLink: "/growth-studio",
      queryParams: { tab: "discovery" },
      linkLabel: "Open Discovery →",
    },
    {
      step: 2,
      title: "Agent Blueprinting",
      description: "Design enterprise agent architectures.",
      routerLink: "/growth-studio",
      queryParams: { tab: "architecture" },
      linkLabel: "Open Blueprinting →",
    },
    {
      step: 3,
      title: "Agent Implementation",
      description: "Build and deploy agents.",
      routerLink: "/growth-studio",
      queryParams: { tab: "implementation" },
      linkLabel: "Open Implementation →",
    },
    {
      step: 4,
      title: "Agent Governance Services",
      description: "Manage risk and compliance.",
      routerLink: "/governance",
      linkLabel: "Open Governance →",
    },
    {
      step: 5,
      title: "Managed Agent Operations",
      description: "Operate and optimize agents at scale.",
      routerLink: "/managed-operations",
      linkLabel: "Open Operations →",
    },
  ];
}
