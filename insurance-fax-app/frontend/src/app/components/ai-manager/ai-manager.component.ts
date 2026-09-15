import { CommonModule } from "@angular/common";
import { Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges } from "@angular/core";
import { FormsModule } from "@angular/forms";

import { ChatMessageHistory, ChatSource, FaxRecord, FaxService } from "../../services/fax.service";
import { VoiceService } from "../../services/voice.service";
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
  imports: [CommonModule, FormsModule],
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
  isSpeaking = false;
  isListening = false;
  readonly speechSupported: boolean;
  readonly sttSupported: boolean;

  aiStatus: AiStatus = "checking";
  aiProviderLabel = "";

  constructor(private faxService: FaxService, private voiceService: VoiceService) {
    this.speechSupported = this.voiceService.isSynthesisSupported();
    this.sttSupported = this.voiceService.isRecognitionSupported();
  }

  ngOnInit(): void {
    this.checkAiStatus();
  }

  ngOnDestroy(): void {
    this.voiceService.stopSpeaking();
    this.voiceService.stopListening();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes["claim"]) return;

    this.voiceService.stopSpeaking();
    this.isSpeaking = false;
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
    this.voiceService.stopSpeaking();
    this.voiceService.stopListening();
    this.isSpeaking = false;
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

    this.isSendingChat = true;
    this.chatError = "";
    this.chatInput = "";
    this.pendingClarificationOptions = [];

    this.faxService.sendChatMessage(this.claim.id, message, this.conversationId).subscribe({
      next: (res) => {
        this.conversationId = res.conversationId;
        this.chatMessages = [
          ...this.chatMessages,
          {
            id: res.conversationId + "-" + this.chatMessages.length,
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
          this.speakResponse(res.answer);
        }
      },
      error: () => {
        this.isSendingChat = false;
        this.chatError = "The AI Claim Manager could not be reached. Please try again.";
      },
    });
  }

  // ---- voice output (TTS) ----

  toggleVoice(): void {
    this.voiceEnabled = !this.voiceEnabled;
    if (!this.voiceEnabled) {
      this.voiceService.stopSpeaking();
      this.isSpeaking = false;
    }
  }

  private speakResponse(text: string): void {
    if (!this.speechSupported) return;
    this.isSpeaking = true;
    this.voiceService.speak(
      text,
      () => (this.isSpeaking = false),
      () => (this.isSpeaking = false)
    );
  }

  stopSpeaking(): void {
    this.voiceService.stopSpeaking();
    this.isSpeaking = false;
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
