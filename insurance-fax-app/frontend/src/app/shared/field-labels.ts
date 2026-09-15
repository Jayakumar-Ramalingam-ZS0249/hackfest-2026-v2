// Shared between AppComponent (the field grid) and AiManagerComponent (chat
// source labels) so both display the same human-readable names for the 15
// canonical claim fields the backend extracts.
export const FIELD_LABELS: Record<string, string> = {
  patientName: "Patient Name",
  dateOfBirth: "Date of Birth",
  memberId: "Member ID",
  insuranceCompany: "Insurance Company",
  policyNumber: "Policy Number",
  claimNumber: "Claim Number",
  hospitalName: "Hospital Name",
  doctorName: "Doctor Name",
  diagnosis: "Diagnosis",
  admissionDate: "Admission Date",
  dischargeDate: "Discharge Date",
  claimAmount: "Claim Amount",
  hospitalBillAmount: "Hospital Bill Amount",
  approvedAmount: "Approved Amount",
  deductibleAmount: "Deductible Amount",
};

export const FIELD_ORDER: string[] = [
  "patientName",
  "dateOfBirth",
  "memberId",
  "insuranceCompany",
  "policyNumber",
  "claimNumber",
  "hospitalName",
  "doctorName",
  "diagnosis",
  "admissionDate",
  "dischargeDate",
  "claimAmount",
  "hospitalBillAmount",
  "approvedAmount",
  "deductibleAmount",
];
