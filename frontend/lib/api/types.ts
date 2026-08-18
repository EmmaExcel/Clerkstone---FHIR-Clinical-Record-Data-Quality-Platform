

export type Severity = "error" | "warning" | "info";

export interface SeverityCounts {
  error: number;
  warning: number;
  info: number;
}

export type NhsNumberStatus = "verified" | "unverified" | "absent";

export type ReviewStatus = "open" | "assigned" | "resolved" | "accepted_risk";

export type QualityRunStatus = "running" | "complete" | "failed";

export type AuditOutcome = "success" | "denied" | "error";

export interface OperationOutcomeCoding {
  system?: string | null;
  code?: string | null;
  display?: string | null;
}

export interface OperationOutcomeDetails {
  text?: string | null;
  coding?: OperationOutcomeCoding[] | null;
}

export interface OperationOutcomeIssue {
  severity: string;
  code: string;
  expression?: string[] | null;
  details?: OperationOutcomeDetails | null;
  diagnostics?: string | null;
}

export interface OperationOutcome {
  resourceType: "OperationOutcome";
  issue: OperationOutcomeIssue[];
}

export interface HealthResponse {
  status: string;
  service?: string | null;
  version?: string | null;
}

export interface ReadinessResponse {
  status: "ready" | "not_ready";
  checks?: Record<string, boolean | string> | null;
}

export interface PatientDemographics {
  id: string;
  nhs_number?: string | null;
  nhs_number_status?: NhsNumberStatus | null;
  family_name?: string | null;
  given_names?: string[] | null;
  birth_date?: string | null;
  age_years?: number | null;
  gender?: string | null;
  postcode?: string | null;
  deceased?: boolean | null;
}

export interface PatientListItem {
  id: string;
  nhs_number?: string | null;
  nhs_number_status?: NhsNumberStatus | null;
  family_name?: string | null;
  given_names?: string[] | null;
  birth_date?: string | null;
  age_years?: number | null;
  gender?: string | null;
  postcode?: string | null;
  deceased?: boolean | null;
}

export interface ResourceCounts {
  encounters: number;
  observations: number;
  conditions: number;
  medications: number;
}

export interface PatientSummary {
  patient: PatientDemographics;
  counts?: ResourceCounts | null;
  synthetic_data_notice?: string | null;
}

export interface PageInfo {
  count: number;
  total?: number | null;
  offset?: number | null;
  next?: string | null;
}

export interface PatientSearchResponse {
  total?: number | null;
  page?: PageInfo | null;
  patients?: PatientListItem[] | null;
}

export type TimelineResourceType =
  | "Encounter"
  | "Observation"
  | "Condition"
  | "MedicationRequest"
  | "Procedure"
  | "AllergyIntolerance"
  | "DiagnosticReport"
  | "Immunization";

export interface CodeSummary {
  system?: string | null;
  value?: string | null;
  display?: string | null;
  resolved?: boolean | null;
}

export interface TimelineEntry {
  type: TimelineResourceType;
  id: string;
  /** ISO-8601 timestamp of the entry's effective moment. */
  date: string;
  display?: string | null;
  /** Rule IDs of quality findings attached to this resource, if any. */
  quality_flags?: string[] | null;
  class?: string | null;
  status?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  value?: string | null;
  interpretation?: string | null;
  code?: CodeSummary | null;
  clinical_status?: string | null;
  dosage_text?: string | null;
}

export interface TimelineResponse {
  patient: PatientDemographics;
  synthetic_data_notice?: string | null;
  range?: { from?: string | null; to?: string | null } | null;
  entries?: TimelineEntry[] | null;
  counts?: ResourceCounts | null;
  page?: PageInfo | null;
}

export type QualityRuleCategory =
  | "required"
  | "identifier"
  | "referential"
  | "temporal"
  | "physiological"
  | "terminology"
  | "structural"
  | "duplication"
  | "cohort";

export interface QualityRule {
  id: string;
  category: string;
  severity: Severity;
  title: string;
  description: string;
  fhirpath: string;
  enabled: boolean;
}

export interface QualityRun {
  id: string;
  ruleset_version?: string | null;
  triggered_by?: string | null;
  scope?: unknown;
  started_at?: string | null;
  finished_at?: string | null;
  status: QualityRunStatus;
  counts?: SeverityCounts | null;
}

export interface QualityRunListResponse {
  total?: number | null;
  page?: PageInfo | null;
  runs?: QualityRun[] | null;
}

export interface FindingResourceRef {
  type: string;
  logical_id: string;
  url: string;
}

export interface QualityFinding {
  id: string;
  rule_id: string;
  severity: Severity;
  title: string;
  resource?: FindingResourceRef | null;
  patient_id?: string | null;
  expression?: string[] | null;
  message: string;
  context?: Record<string, unknown> | null;
  review_status: ReviewStatus;
  suggested_action?: string | null;
}

export interface FindingsResponse {
  run_id: string;
  ruleset_version?: string | null;
  summary?: SeverityCounts | null;
  findings?: QualityFinding[] | null;
  page?: PageInfo | null;
}

export interface AuditEvent {
  id: string;
  occurred_at: string;
  actor: string;
  actor_role: string;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  outcome: AuditOutcome;
  reason?: string | null;
  request_id: string;
}

export interface AuditEventsResponse {
  total?: number | null;
  page?: PageInfo | null;
  events?: AuditEvent[] | null;
}
