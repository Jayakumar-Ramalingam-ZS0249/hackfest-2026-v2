import { Component, input } from '@angular/core';

export type GradientHeadingLevel = 1 | 2 | 3;

/**
 * The blue-to-purple gradient headline treatment used for every page title
 * ("AI Enablement Playbook"-style). Renders the correct heading level for
 * document structure while keeping the visual style identical everywhere.
 */
@Component({
  selector: 'app-gradient-heading',
  standalone: true,
  templateUrl: './gradient-heading.html',
  styleUrl: './gradient-heading.scss',
})
export class GradientHeading {
  readonly level = input<GradientHeadingLevel>(1);
  readonly subtitle = input<string | null>(null);
}
