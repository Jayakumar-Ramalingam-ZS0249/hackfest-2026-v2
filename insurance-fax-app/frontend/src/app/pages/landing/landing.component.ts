import { CommonModule } from "@angular/common";
import { Component } from "@angular/core";
import { RouterLink } from "@angular/router";

/**
 * Plain public splash screen at "/" -- shown with no header/sidebar chrome
 * (see AppComponent.hideShell). Purely an entry point: brand + a single
 * CTA into the real application at /dashboard, which is where the actual
 * auth guard and app shell take over.
 */
@Component({
  selector: "app-landing",
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: "./landing.component.html",
  styleUrls: ["./landing.component.scss"],
})
export class LandingComponent {}
