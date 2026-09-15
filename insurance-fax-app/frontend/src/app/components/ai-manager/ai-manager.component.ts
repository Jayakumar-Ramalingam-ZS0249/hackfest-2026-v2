import { CommonModule } from "@angular/common";
import { Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges } from "@angular/core";
import { FormsModule } from "@angular/forms";

import { ChatMessageHistory, ChatSource, FaxRecord, FaxService } from "../../services/fax.service";
import { VoiceService } from "../../services/voice.service";
import { AudioPlaybackService, PlaybackEvent } from "../../services/audio-playback.service";
import { RobotSpeakingAvatarComponent, RobotState } from "../robot-speaking-avatar/robot-speaking-avatar.component";
import { FIELD_LABELS } from "../../shared/field-labels";

export interface SourceRequestedEvent {
  page: number | null;
  sourceText: string | null;
}

type AiStatus = "checking" | "online" | "offline";

/**
 * Floating "AI Claim Manager" assistant -- a professional human-manager
 * avatar in the bottom-right corner that opens a chat panel grounded in
 * whatever claim/document the parent screen currently has selected. All
 * chat/voice state lives here so AppComponent doesn't have to own it.
 */
@Component({
  selector: "app-ai-manager",
  standalone: true,
  imports: [CommonModule, FormsModule, RobotSpeakingAvatarComponent],
  templateUrl: "./ai-manager.component.html",
  styleUrls: ["./ai-manager.component.scss"],
})
export class AiManagerComponent implements OnChanges, OnInit, OnDestroy {
  @Input() claim: FaxRecord | null = null;
  @Output() sourceRequested = new EventEmitter<SourceRequestedEvent>();

  fieldLabels = FIELD_LABELS;

  isOpen = false;
  isMinimized = false;

  chatMessages: ChatMessageHistory[] = [];
  chatInput = "";
  isSendingChat = false;
  chatError = "";
  quickActions: string[] = [];
  pendingClarificationOptions: string[] = [];
  private conversationId: string | undefined;

  voiceEnabled = false;
  isListening = false;
  readonly sttSupported: boolean;

  // Robot avatar state -- driven only by real playback events/amplitude
  // from AudioPlaybackService, never by a timer of its own.
  robotState: RobotState = "idle";
  robotAudioLevel = 0;
  private currentlySpokenMessageId: string | null = null;
  private audioCache = new Map<string, Blob>();
  ttsFailedMessageIds = new Set<string>();

  aiStatus: AiStatus = "checking";
  aiProviderLabel = "";

  constructor(
    private faxService: FaxService,
    private voiceService: VoiceService,
    private audioPlayback: AudioPlaybackService,
  ) {
    this.sttSupported = this.voiceService.isRecognitionSupported();
  }

  /** True only while real audio for an AI response is actually playing. */
  get isSpeaking(): boolean {
    return this.robotState === "speaking";
  }

  ngOnInit(): void {
    this.checkAiStatus();
  }

  ngOnDestroy(): void {
    this.audioPlayback.stop();
    this.voiceService.stopListening();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes["claim"]) return;

    this.audioPlayback.stop();
    this.robotState = "idle";
    this.robotAudioLevel = 0;
    this.currentlySpokenMessageId = null;
    this.audioCache.clear();
    this.ttsFailedMessageIds.clear();
    this.chatMessages = [];
    this.chatError = "";
    this.pendingClarificationOptions = [];
    this.conversationId = undefined;

    const claim = this.claim;
    if (claim && claim.status !== "invalid") {
      this.loadHistory(claim.id);
      this.loadQuickActions(claim.id);
    } else {
      this.quickActions = [];
    }
  }

  private checkAiStatus(): void {
    this.faxService.getHealth().subscribe({
      next: (res) => {
        this.aiStatus = res.aiProvider.startsWith("rule_based") ? "offline" : "online";
        this.aiProviderLabel = res.aiProvider;
      },
      error: () => {
        this.aiStatus = "offline";
        this.aiProviderLabel = "backend unreachable";
      },
    });
  }

  private loadHistory(claimId: string) {
    this.faxService.getChatHistory(claimId).subscribe({
      next: (history) => (this.chatMessages = history),
      error: () => {},
    });
  }

  private loadQuickActions(claimId: string) {
    this.faxService.getQuickActions(claimId).subscribe({
      next: (res) => (this.quickActions = res.actions),
      error: () => (this.quickActions = []),
    });
  }

  // ---- panel open/close ----

  togglePanel(): void {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.isMinimized = false;
      this.checkAiStatus();
    }
  }

  minimize(): void {
    this.isMinimized = true;
  }

  restore(): void {
    this.isMinimized = false;
  }

  close(): void {
    this.isOpen = false;
    this.isMinimized = false;
    this.audioPlayback.stop();
    this.voiceService.stopListening();
    this.robotState = "idle";
    this.robotAudioLevel = 0;
    this.currentlySpokenMessageId = null;
    this.isListening = false;
  }

  newChat(): void {
    if (!this.claim) return;
    this.faxService.startNewChat(this.claim.id).subscribe((res) => {
      this.conversationId = res.conversationId;
      this.chatMessages = [];
      this.pendingClarificationOptions = [];
    });
  }

  // ---- sending questions ----

  useQuickAction(action: string): void {
    this.chatInput = action;
    this.send();
  }

  useClarificationOption(label: string): void {
    this.pendingClarificationOptions = [];
    this.chatInput = `What is the ${label}?`;
    this.send();
  }

  send(): void {
    const message = this.chatInput.trim();
    if (!message || !this.claim || this.isSendingChat) return;

    // Never let a new question overlap with the previous answer's audio.
    this.audioPlayback.stop();
    this.currentlySpokenMessageId = null;
    this.robotAudioLevel = 0;

    this.isSendingChat = true;
    this.robotState = "thinking";
    this.chatError = "";
    this.chatInput = "";
    this.pendingClarificationOptions = [];

    this.faxService.sendChatMessage(this.claim.id, message, this.conversationId).subscribe({
      next: (res) => {
        this.conversationId = res.conversationId;
        const messageId = res.conversationId + "-" + this.chatMessages.length;
        this.chatMessages = [
          ...this.chatMessages,
          {
            id: messageId,
            question: message,
            answer: res.answer,
            sources: res.sources,
            createdAt: new Date().toISOString(),
            clarificationOptions: res.clarificationOptions,
          },
        ];
        this.pendingClarificationOptions = res.clarificationOptions || [];
        this.isSendingChat = false;

        if (this.voiceEnabled) {
          this.speakMessage(messageId, res.answer);
        } else {
          this.robotState = "idle";
        }
      },
      error: () => {
        this.isSendingChat = false;
        this.robotState = "idle";
        this.chatError = "The AI Claim Manager could not be reached. Please try again.";
      },
    });
  }

  // ---- voice output (TTS): backend-synthesized real audio, played through
  // AudioPlaybackService so the robot's mouth is driven by the ACTUAL audio
  // signal (see AudioPlaybackService's doc comment for why browser
  // SpeechSynthesis can't support this). ----

  toggleVoice(): void {
    this.voiceEnabled = !this.voiceEnabled;
    if (!this.voiceEnabled) {
      this.audioPlayback.stop();
      this.robotState = "idle";
      this.robotAudioLevel = 0;
      this.currentlySpokenMessageId = null;
    }
  }

  /** Whether this message's audio is cached and ready for instant replay. */
  hasCachedAudio(messageId: string): boolean {
    return this.audioCache.has(messageId);
  }

  isSpokenMessage(messageId: string): boolean {
    return this.currentlySpokenMessageId === messageId;
  }

  /** User-triggered replay -- reuses cached audio; never re-runs the AI. */
  replay(messageId: string, text: string): void {
    this.ttsFailedMessageIds.delete(messageId);
    this.speakMessage(messageId, text);
  }

  private speakMessage(messageId: string, text: string): void {
    const cached = this.audioCache.get(messageId);
    if (cached) {
      this.playAudio(messageId, cached);
      return;
    }

    this.faxService.synthesizeSpeech(text).subscribe({
      next: (blob) => {
        this.audioCache.set(messageId, blob);
        this.playAudio(messageId, blob);
      },
      error: () => {
        // TTS failing must never hide/undo the already-displayed AI answer.
        this.ttsFailedMessageIds.add(messageId);
        this.robotState = "idle";
      },
    });
  }

  private playAudio(messageId: string, blob: Blob): void {
    this.audioPlayback.play(blob, {
      onEvent: (event: PlaybackEvent) => this.onPlaybackEvent(messageId, event),
      onLevel: (level: number) => (this.robotAudioLevel = level),
    });
  }

  private onPlaybackEvent(messageId: string, event: PlaybackEvent): void {
    switch (event) {
      case "playing":
        this.robotState = "speaking";
        this.currentlySpokenMessageId = messageId;
        break;
      case "waiting":
      case "paused":
        this.robotState = "paused";
        break;
      case "ended":
        this.robotState = "idle";
        this.robotAudioLevel = 0;
        this.currentlySpokenMessageId = null;
        break;
      case "error":
        this.robotState = "idle";
        this.robotAudioLevel = 0;
        this.currentlySpokenMessageId = null;
        this.ttsFailedMessageIds.add(messageId);
        break;
    }
  }

  /** User clicked "Stop Speaking" -- stop audio, cancel the analyser loop,
   * close the mouth, go idle. The AI response text stays visible. */
  stopSpeaking(): void {
    this.audioPlayback.stop();
    this.robotState = "idle";
    this.robotAudioLevel = 0;
    this.currentlySpokenMessageId = null;
  }

  // ---- voice input (STT) ----

  toggleListening(): void {
    if (this.isListening) {
      this.voiceService.stopListening();
      this.isListening = false;
      return;
    }

    if (!this.sttSupported) {
      this.chatError = "Voice input is not supported in this browser. Please type your question instead.";
      return;
    }

    this.isListening = true;
    this.chatError = "";
    this.voiceService.startListening(
      (transcript) => {
        this.chatInput = transcript;
        this.send();
      },
      () => (this.isListening = false),
      (message) => {
        this.isListening = false;
        this.chatError = `Microphone unavailable: ${message}`;
      }
    );
  }

  // ---- source navigation ----

  onSourceClick(source: ChatSource): void {
    this.sourceRequested.emit({ page: source.page, sourceText: source.sourceText });
  }

  chatSourceLabel(source: ChatSource): string {
    const label = source.field ? this.fieldLabels[source.field] || source.field : null;
    const parts = [label, source.page ? `Page ${source.page}` : null].filter(Boolean);
    return parts.join(" — ");
  }
}
