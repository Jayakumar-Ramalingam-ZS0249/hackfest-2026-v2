import { Component } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { FaxService, FaxRecord, FaxSummary, FieldResult } from "./services/fax.service";
import { AiManagerComponent, SourceRequestedEvent } from "./components/ai-manager/ai-manager.component";
import { FIELD_LABELS, FIELD_ORDER } from "./shared/field-labels";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [CommonModule, FormsModule, AiManagerComponent],
  templateUrl: "./app.component.html",
  styleUrls: ["./app.component.scss"],
})
export class AppComponent {
  faxQueue: FaxSummary[] = [];
  activeFax: FaxRecord | null = null;
  isUploading = false;
  errorMessage = "";

  // Low-match documents ("review_required") show a gate modal separate from
  // the hard "invalid" rejection -- the manager must explicitly choose to
  // review anyway before the extracted data panel is shown.
  reviewAcknowledged = false;

  // Source reference navigation: clicking "View Source" on a field (or a
  // source chip inside the AI Claim Manager chat) scrolls the raw-text panel
  // to, and highlights, the exact snippet the value came from.
  activeSourceText: string | null = null;

  fieldOrder = FIELD_ORDER;
  fieldLabels = FIELD_LABELS;

  // Real backend/AI health -- never hardcoded "Connected"/"Ready" text.
  backendConnected: boolean | null = null;
  aiProviderLabel = "checking…";

  constructor(private faxService: FaxService) {
    this.refreshQueue();
    this.checkHealth();
  }

  private checkHealth() {
    this.faxService.getHealth().subscribe({
      next: (res) => {
        this.backendConnected = true;
        this.aiProviderLabel = res.aiProvider;
      },
      error: () => {
        this.backendConnected = false;
        this.aiProviderLabel = "unavailable";
      },
    });
  }

  refreshQueue() {
    this.faxService.listFaxes().subscribe({
      next: (list) => (this.faxQueue = list),
      error: () =>
        (this.errorMessage =
          "Could not reach the backend API. Is it running on port 8000?"),
    });
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    this.isUploading = true;
    this.errorMessage = "";

    this.faxService.uploadFax(file).subscribe({
      next: (record) => {
        this.setActiveFax(record);
        this.isUploading = false;
        this.refreshQueue();
      },
      error: (err) => {
        this.isUploading = false;
        this.errorMessage =
          "Upload failed. Make sure the backend is running and the file is a PDF.";
        console.error(err);
      },
    });
  }

  selectFax(id: string) {
    this.faxService.getFax(id).subscribe((record) => this.setActiveFax(record));
  }

  private setActiveFax(record: FaxRecord) {
    this.activeFax = record;
    this.reviewAcknowledged = false;
    this.activeSourceText = null;
  }

  reRunExtraction() {
    if (this.activeFax) this.selectFax(this.activeFax.id);
  }

  reprocessWithAi() {
    if (!this.activeFax) return;
    this.faxService.reprocessDocument(this.activeFax.id).subscribe((record) => this.setActiveFax(record));
  }

  proceedWithReview() {
    this.reviewAcknowledged = true;
  }

  approveAndResolve() {
    if (!this.activeFax) return;
    const corrections: Record<string, string> = {};
    for (const key of this.fieldOrder) {
      corrections[key] = this.activeFax.fields[key]?.value ?? "";
    }
    this.faxService
      .submitDecision(this.activeFax.id, true, corrections, "clinical_admin")
      .subscribe((record) => {
        this.activeFax = record;
        this.refreshQueue();
      });
  }

  confidencePercent(confidence: number): string {
    return `${Math.round(confidence * 100)}%`;
  }

  statusClass(status: string): string {
    if (!status || status === "not_found") return "field-review";
    return status === "auto_fill" ? "field-ok" : "field-review";
  }

  overallBannerClass(): string {
    if (!this.activeFax) return "";
    if (this.activeFax.status === "invalid") return "banner-review";
    return this.activeFax.status === "needs_review"
      ? "banner-review"
      : "banner-ok";
  }

  documentStatusLabel(): string {
    if (!this.activeFax) return "No document";
    return this.activeFax.document?.status || "review_required";
  }

  fieldValue(field: any): string {
    return field?.value ?? "Not Found";
  }

  hasConflict(field: FieldResult | undefined): boolean {
    return !!field?.conflicts && field.conflicts.length > 0;
  }

  isUnverified(field: FieldResult | undefined): boolean {
    return field?.verificationStatus === "UNVERIFIED";
  }

  viewSource(field: FieldResult | undefined) {
    this.highlightSource(field?.sourceText ?? null);
  }

  onAiSourceRequested(event: SourceRequestedEvent) {
    this.highlightSource(event.sourceText);
  }

  private highlightSource(sourceText: string | null) {
    if (!sourceText) return;
    this.activeSourceText = sourceText;
    setTimeout(() => {
      const el = document.getElementById("source-highlight");
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 0);
  }

  // Splits raw_text into [before, match, after] around activeSourceText so
  // the template can render the middle part highlighted. Falls back to the
  // whole text as "before" when there is no active source or no match.
  get rawTextSegments(): { before: string; match: string; after: string } {
    const text = this.activeFax?.raw_text || "";
    if (!this.activeSourceText) return { before: text, match: "", after: "" };

    const index = text.indexOf(this.activeSourceText);
    if (index === -1) return { before: text, match: "", after: "" };

    return {
      before: text.slice(0, index),
      match: text.slice(index, index + this.activeSourceText.length),
      after: text.slice(index + this.activeSourceText.length),
    };
  }
}
