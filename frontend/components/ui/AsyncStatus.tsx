"use client";

import { WarningCallout } from "nhsuk-react-components";
import { ApiError, isBackendOffline } from "@/lib/api";
import { BackendOffline } from "./BackendOffline";

/**
 * Accessible async-state primitives used across data pages.
 *
 * - Loading/empty/error states are wrapped in `role="status"` / `aria-live`
 *   regions so screen readers announce async results (WCAG 2.2 AA).
 * - Errors distinguish "backend offline" from a real API failure so the user
 *   always sees an actionable message rather than a stack trace.
 */

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <p className="nhsuk-body" role="status" aria-live="polite">
      {label}
      <span aria-hidden="true">…</span>
    </p>
  );
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <p className="nhsuk-body" role="status" aria-live="polite">
      {children}
    </p>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = error.operationOutcome?.issue
      .map((issue) => issue.diagnostics ?? issue.details?.text ?? issue.code)
      .filter(Boolean)
      .join("; ");
    return detail || error.message;
  }
  if (error instanceof Error) return error.message;
  return String(error);
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  if (isBackendOffline(error)) {
    return <BackendOffline retry={retry} />;
  }
  return (
    <div role="alert" aria-live="assertive">
      <WarningCallout>
        <WarningCallout.Heading headingLevel="h2">Something went wrong</WarningCallout.Heading>
        <p>{errorMessage(error)}</p>
        {retry ? (
          <button type="button" className="nhsuk-button" onClick={retry}>
            Retry
          </button>
        ) : null}
      </WarningCallout>
    </div>
  );
}
