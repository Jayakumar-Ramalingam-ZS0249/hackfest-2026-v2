import { CommonModule } from "@angular/common";
import { Component, Input } from "@angular/core";

export type RobotState = "idle" | "thinking" | "speaking" | "paused" | "error";

type MouthBucket = "closed" | "small" | "medium" | "open" | "wide";

/**
 * Purely presentational robot avatar. It does not talk to any service and
 * does not decide when to "speak" -- it only renders whatever `state` and
 * `audioLevel` it is given. `audioLevel` (0-1) must come from a REAL
 * amplitude reading of the audio actually playing (see
 * AudioPlaybackService); this component just maps that number to a mouth
 * shape. It never animates the mouth on a timer of its own.
 */
@Component({
  selector: "app-robot-speaking-avatar",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./robot-speaking-avatar.component.html",
  styleUrls: ["./robot-speaking-avatar.component.scss"],
})
export class RobotSpeakingAvatarComponent {
  @Input() state: RobotState = "idle";
  @Input() audioLevel = 0;
  @Input() size: "sm" | "md" = "md";

  get mouthBucket(): MouthBucket {
    if (this.state !== "speaking") return "closed";
    const level = this.audioLevel;
    if (level < 0.08) return "closed";
    if (level < 0.28) return "small";
    if (level < 0.5) return "medium";
    if (level < 0.75) return "open";
    return "wide";
  }

  get stateLabel(): string {
    switch (this.state) {
      case "thinking":
        return "Thinking…";
      case "speaking":
        return "Speaking";
      case "paused":
        return "Paused";
      case "error":
        return "Voice unavailable";
      default:
        return "Idle";
    }
  }
}
