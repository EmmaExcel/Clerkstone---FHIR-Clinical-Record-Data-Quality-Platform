import { apiFetch, buildQueryString } from "./client";
import type {
  AuditEventsResponse,
  FindingsResponse,
  HealthResponse,
  OperationOutcome,
  PatientSearchResponse,
  PatientSummary,
  QualityFinding,
  QualityRule,
  QualityRun,
  QualityRunListResponse,
  ReadinessResponse,
  ReviewStatus,
  Severity,
  TimelineResponse,
} from "./types";

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

export function getReady(): Promise<ReadinessResponse> {
  return apiFetch<ReadinessResponse>("/ready");
}

export interface PatientSearchParams {
  family?: string;
  birthdate?: string;
  gender?: string;
  _count?: number;
  _page?: number;
}

export function searchPatients(params: PatientSearchParams = {}): Promise<PatientSearchResponse> {
  return apiFetch<PatientSearchResponse>(`/patients${buildQueryString(params)}`);
}

export function getPatient(id: string): Promise<PatientSummary> {
  return apiFetch<PatientSummary>(`/patients/${encodeURIComponent(id)}`);
}

export interface TimelineParams {
  from?: string;
  _count?: number;
}

export function getPatientTimeline(id: string, params: TimelineParams = {}): Promise<TimelineResponse> {
  return apiFetch<TimelineResponse>(`/patients/${encodeURIComponent(id)}/timeline${buildQueryString(params)}`);
}

export interface ObservationsParams {
  code?: string;
  date?: string;
  _count?: number;
}

export function getPatientObservations(id: string, params: ObservationsParams = {}): Promise<unknown> {
  return apiFetch(`/patients/${encodeURIComponent(id)}/observations${buildQueryString(params)}`);
}

export function getPatientConditions(id: string): Promise<unknown> {
  return apiFetch(`/patients/${encodeURIComponent(id)}/conditions`);
}

export function getPatientMedications(id: string): Promise<unknown> {
  return apiFetch(`/patients/${encodeURIComponent(id)}/medications`);
}

export function getFhirResource(resourceType: string, id: string): Promise<unknown> {
  return apiFetch(`/fhir/${encodeURIComponent(resourceType)}/${encodeURIComponent(id)}`);
}

export function getQualityRules(): Promise<QualityRule[]> {
  return apiFetch<QualityRule[]>("/quality/rules");
}

export function startQualityRun(scope?: unknown): Promise<QualityRun> {
  return apiFetch<QualityRun>("/quality/runs", { method: "POST", body: scope ?? {} });
}

export function getQualityRuns(params: { _count?: number; _page?: number } = {}): Promise<QualityRunListResponse> {
  return apiFetch<QualityRunListResponse>(`/quality/runs${buildQueryString(params)}`);
}

export function getQualityRun(id: string): Promise<QualityRun> {
  return apiFetch<QualityRun>(`/quality/runs/${encodeURIComponent(id)}`);
}

export interface FindingsParams {
  severity?: Severity;
  rule?: string;
  patient?: string;
  review_status?: ReviewStatus;
  _count?: number;
  _page?: number;
}

export function getQualityRunFindings(id: string, params: FindingsParams = {}): Promise<FindingsResponse> {
  return apiFetch<FindingsResponse>(
    `/quality/runs/${encodeURIComponent(id)}/findings${buildQueryString(params)}`,
  );
}

export function assignFinding(id: string, assignee?: string): Promise<QualityFinding> {
  return apiFetch<QualityFinding>(`/quality/findings/${encodeURIComponent(id)}/assign`, {
    method: "POST",
    body: assignee ? { assigned_to: assignee } : {},
  });
}

export interface ResolveFindingBody {
  resolution: string;
  status?: ReviewStatus;
}

export function resolveFinding(id: string, body: ResolveFindingBody): Promise<QualityFinding> {
  return apiFetch<QualityFinding>(`/quality/findings/${encodeURIComponent(id)}/resolve`, {
    method: "POST",
    body,
  });
}

export interface AuditParams {
  action?: string;
  actor?: string;
  _count?: number;
  _page?: number;
}

export function getAuditEvents(params: AuditParams = {}): Promise<AuditEventsResponse> {
  return apiFetch<AuditEventsResponse>(`/audit/events${buildQueryString(params)}`);
}

export type { OperationOutcome };
