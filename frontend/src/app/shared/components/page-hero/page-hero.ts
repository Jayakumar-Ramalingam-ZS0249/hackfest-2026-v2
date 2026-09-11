import { Component, input } from '@angular/core';
import { GradientHeading } from '../gradient-heading/gradient-heading';

/**
 * The soft gradient hero band used at the top of every page, so the brand
 * treatment (gradient background + gradient headline) stays identical across
 * the whole app rather than being reinvented per screen.
 */
@Component({
  selector: 'app-page-hero',
  standalone: true,
  imports: [GradientHeading],
  templateUrl: './page-hero.html',
  styleUrl: './page-hero.scss',
})
export class PageHero {
  readonly eyebrow = input<string | null>(null);
  readonly title = input.required<string>();
  readonly subtitle = input<string | null>(null);
}
