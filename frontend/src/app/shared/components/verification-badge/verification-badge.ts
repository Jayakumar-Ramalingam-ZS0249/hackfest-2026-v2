import { Component, input } from '@angular/core';

/**
 * Green check / red cross badge used for Aadhar and PAN verification status
 * on the applicant detail page. The verified/failed state is always paired
 * with a visible text label — never conveyed by color or icon alone.
 */
@Component({
  selector: 'app-verification-badge',
  standalone: true,
  templateUrl: './verification-badge.html',
  styleUrl: './verification-badge.scss',
})
export class VerificationBadge {
  readonly label = input.required<string>();
  readonly verified = input.required<boolean>();
}
