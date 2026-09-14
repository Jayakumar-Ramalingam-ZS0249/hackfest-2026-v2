import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FaxService, FaxRecord, FaxSummary } from './services/fax.service';

// Human-readable labels for the canonical field keys returned by the API.
const FIELD_LABELS: Record<string, string> = {
  first_name: 'First Name',
  last_name: 'Last Name',
  member_number: 'Member Number',
  dob: 'DOB',
  city: 'City',
  state: 'State',
  drug: 'Prescription',
  physician: 'Physician',
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {
  faxQueue: FaxSummary[] = [];
  activeFax: FaxRecord | null = null;
  isUploading = false;
  errorMessage = '';

  fieldOrder = ['first_name', 'last_name', 'member_number', 'dob', 'city', 'state', 'drug', 'physician'];
  fieldLabels = FIELD_LABELS;

  constructor(private faxService: FaxService) {
    this.refreshQueue();
  }

  refreshQueue() {
    this.faxService.listFaxes().subscribe({
      next: (list) => (this.faxQueue = list),
      error: () => (this.errorMessage = 'Could not reach the backend API. Is it running on port 8000?'),
    });
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    this.isUploading = true;
    this.errorMessage = '';

    this.faxService.uploadFax(file).subscribe({
      next: (record) => {
        this.activeFax = record;
        this.isUploading = false;
        this.refreshQueue();
      },
      error: (err) => {
        this.isUploading = false;
        this.errorMessage = 'Upload failed. Make sure the backend is running and the file is a PDF.';
        console.error(err);
      },
    });
  }

  selectFax(id: string) {
    this.faxService.getFax(id).subscribe((record) => (this.activeFax = record));
  }

  reRunExtraction() {
    // In this MVP, "re-run" just re-selects the same fax since the pipeline
    // is deterministic. In production this would re-upload the original
    // file bytes through the pipeline again.
    if (this.activeFax) this.selectFax(this.activeFax.id);
  }

  approveAndResolve() {
    if (!this.activeFax) return;
    const corrections: Record<string, string> = {};
    for (const key of this.fieldOrder) {
      corrections[key] = this.activeFax.fields[key]?.value ?? '';
    }
    this.faxService
      .submitDecision(this.activeFax.id, true, corrections, 'clinical_admin')
      .subscribe((record) => {
        this.activeFax = record;
        this.refreshQueue();
      });
  }

  confidencePercent(confidence: number): string {
    return `${Math.round(confidence * 100)}%`;
  }

  statusClass(status: string): string {
    return status === 'auto_fill' ? 'field-ok' : 'field-review';
  }

  overallBannerClass(): string {
    if (!this.activeFax) return '';
    return this.activeFax.status === 'needs_review' ? 'banner-review' : 'banner-ok';
  }
}
