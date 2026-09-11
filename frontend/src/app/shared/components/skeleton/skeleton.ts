import { Component, input } from '@angular/core';

/**
 * A single shimmering placeholder block. Compose several to build a skeleton
 * layout that roughly matches the shape of the content it's standing in for.
 */
@Component({
  selector: 'app-skeleton',
  standalone: true,
  templateUrl: './skeleton.html',
  styleUrl: './skeleton.scss',
})
export class Skeleton {
  readonly width = input('100%');
  readonly height = input('16px');
  readonly radius = input('8px');
}
