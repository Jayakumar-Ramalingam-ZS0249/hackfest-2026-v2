import { Component, input, output } from '@angular/core';

export type AppButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export type AppButtonSize = 'sm' | 'md' | 'lg';

/**
 * The one button component used everywhere in the app. Solid, fully rounded
 * primary action per the brand theme, with secondary/danger/ghost variants
 * for the rest of the human-in-the-loop controls (Approve / Reject / Request
 * more info).
 */
@Component({
  selector: 'app-button',
  standalone: true,
  templateUrl: './app-button.html',
  styleUrl: './app-button.scss',
})
export class AppButton {
  readonly variant = input<AppButtonVariant>('primary');
  readonly size = input<AppButtonSize>('md');
  readonly disabled = input(false);
  readonly loading = input(false);
  readonly type = input<'button' | 'submit'>('button');
  readonly fullWidth = input(false);

  readonly pressed = output<MouseEvent>();

  handleClick(event: MouseEvent): void {
    if (this.disabled() || this.loading()) return;
    this.pressed.emit(event);
  }
}
