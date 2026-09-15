import { CommonModule } from "@angular/common";
import { Component, OnDestroy, OnInit } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import { Subscription, interval } from "rxjs";
import { switchMap, takeWhile } from "rxjs/operators";

import { AiManagerComponent, SourceRequestedEvent } from "../../components/ai-manager/ai-manager.component";
import { FaxRecord, FaxService, FaxSummary, FieldResult, QueueFilter } from "../../services/fax.service";
import { FIELD_LABELS, FIELD_ORDER } from "../../shared/field-labels";

const SCRAMBLE_CHARS = "0123456789ABCDEF";
const SCRAMBLE_LENGTH = 40;

const FILTER_TITLES: Record<QueueFilter, string> = {
  all: "Fax Intake",
  needs_review: "Needs Review",
  resolved: "Resolved",
  queued: "Queued",
  invalid: "Failed",
  deleted: "Deleted",
};

@Component({
  selector: "app-claim-queue",
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, AiManagerComponent],
  templateUrl: "./claim-queue.component.html",
  styleUrls: ["./claim-queue.component.scss"],
})
export class ClaimQueueComponent implements OnInit, OnDestroy {
  filter: QueueFilter = "all";
  filterTitle = "Fax Intake";
  isDeletedView = false;

  faxQueue: FaxSummary[] = [];
  activeFax: FaxRecord | null = null;
  isUploading = false;
  errorMessage = "";

  // Real upload progress -- stage/percent come straight from the backend
  // pipeline (see UploadStatus), never simulated on a timer.
  uploadStage = "";
  uploadLabel = "";
  uploadPercent = 0;

  // Purely decorative "scanning data" flourish alongside the real progress
  // above -- random hex digits, never presented as an actual measured value.
  scrambleDigits: string[] = [];

  reviewAcknowledged = false;
  activeSourceText: string | null = null;

  fieldOrder = FIELD_ORDER;
  fieldLabels = FIELD_LABELS;

  private routeSub?: Subscription;
  private uploadPollSub?: Subscription;
  private scrambleIntervalId?: ReturnType<typeof setInterval>;

  constructor(private faxService: FaxService, private route: ActivatedRoute, private router: Router) {}

  ngOnInit(): void {
    this.routeSub = this.route.paramMap.subscribe((params) => {
      this.filter = (params.get("filter") as QueueFilter) || "all";
      this.filterTitle = FILTER_TITLES[this.filter] || "Fax Intake";
      this.isDeletedView = this.filter === "deleted";
      this.refreshQueue();

      const id = params.get("id");
      if (id) {
        this.loadFax(id);
      } else {
        this.activeFax = null;
      }
    });
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
    this.uploadPollSub?.unsubscribe();
    this.stopScrambleAnimation();
  }

  refreshQueue(): void {
    this.faxService.listFaxes(this.filter).subscribe({
      next: (list) => (this.faxQueue = list),
      error: () => (this.errorMessage = "Could not reach the backend API. Is it running on port 8000?"),
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    this.isUploading = true;
    this.errorMessage = "";
    this.uploadStage = "uploading";
    this.uploadLabel = "Uploading document…";
    this.uploadPercent = 2;
    this.startScrambleAnimation();

    this.faxService.startUpload(file).subscribe({
      next: ({ jobId }) => this.pollUploadStatus(jobId),
      error: (err) => {
        this.finishUploading();
        this.errorMessage = "Upload failed. Make sure the backend is running and the file is a PDF.";
        console.error(err);
      },
    });

    // Let the same <input type=file> be used again for a second upload.
    input.value = "";
  }

  private pollUploadStatus(jobId: string): void {
    this.uploadPollSub?.unsubscribe();
    this.uploadPollSub = interval(400)
      .pipe(
        switchMap(() => this.faxService.getUploadStatus(jobId)),
        takeWhile((status) => !status.done, true),
      )
      .subscribe({
        next: (status) => {
          this.uploadStage = status.stage;
          this.uploadLabel = status.label;
          this.uploadPercent = status.percent;

          if (!status.done) return;

          this.finishUploading();
          if (status.error) {
            this.errorMessage = status.error;
            return;
          }
          if (status.result) {
            // A fresh upload always lands in the "all" view so the manager
            // sees the result immediately, regardless of which filter they
            // were on.
            this.router.navigate(["/queue", "all", status.result.id]);
          }
        },
        error: () => {
          this.finishUploading();
          this.errorMessage = "Lost connection while checking upload progress.";
        },
      });
  }

  private finishUploading(): void {
    this.isUploading = false;
    this.uploadPollSub?.unsubscribe();
    this.uploadPollSub = undefined;
    this.stopScrambleAnimation();
  }

  private startScrambleAnimation(): void {
    this.scrambleDigits = Array.from(
      { length: SCRAMBLE_LENGTH },
      () => SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)],
    );
    this.scrambleIntervalId = setInterval(() => {
      this.scrambleDigits = this.scrambleDigits.map((d) =>
        Math.random() < 0.4 ? SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)] : d,
      );
    }, 90);
  }

  private stopScrambleAnimation(): void {
    if (this.scrambleIntervalId) {
      clearInterval(this.scrambleIntervalId);
      this.scrambleIntervalId = undefined;
    }
    this.scrambleDigits = [];
  }

  selectFax(id: string): void {
    this.router.navigate(["/queue", this.filter, id]);
  }

  private loadFax(id: string): void {
    this.faxService.getFax(id).subscribe((record) => this.setActiveFax(record));
  }

  private setActiveFax(record: FaxRecord): void {
    this.activeFax = record;
    this.reviewAcknowledged = false;
    this.activeSourceText = null;
  }

  closeActiveDocument(): void {
    this.activeFax = null;
    this.router.navigate(["/queue", this.filter]);
  }

  reprocessWithAi(): void {
    if (!this.activeFax) return;
    this.faxService.reprocessDocument(this.activeFax.id).subscribe((record) => this.setActiveFax(record));
  }

  proceedWithReview(): void {
    this.reviewAcknowledged = true;
  }

  approveAndResolve(): void {
    if (!this.activeFax) return;
    const corrections: Record<string, string> = {};
    for (const key of this.fieldOrder) {
      corrections[key] = this.activeFax.fields[key]?.value ?? "";
    }
    this.faxService.submitDecision(this.activeFax.id, true, corrections, "clinical_admin").subscribe((record) => {
      this.activeFax = record;
      this.refreshQueue();
    });
  }

  deleteFax(id: string, event: Event): void {
    event.stopPropagation();
    if (!confirm("Delete this document? It can be restored later from the Deleted view.")) return;

    this.faxService.deleteClaim(id).subscribe(() => {
      if (this.activeFax?.id === id) this.closeActiveDocument();
      this.refreshQueue();
    });
  }

  restoreFax(id: string, event: Event): void {
    event.stopPropagation();
    this.faxService.restoreClaim(id).subscribe(() => this.refreshQueue());
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
    return this.activeFax.status === "needs_review" ? "banner-review" : "banner-ok";
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

  viewSource(field: FieldResult | undefined): void {
    this.highlightSource(field?.sourceText ?? null);
  }

  onAiSourceRequested(event: SourceRequestedEvent): void {
    this.highlightSource(event.sourceText);
  }

  private highlightSource(sourceText: string | null): void {
    if (!sourceText) return;
    this.activeSourceText = sourceText;
    setTimeout(() => {
      const el = document.getElementById("source-highlight");
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 0);
  }

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
