"use client";

import { WarningCallout } from "nhsuk-react-components";
import { getApiBaseUrl } from "@/lib/api";

export function BackendOffline({ retry }: { retry?: () => void }) {
  return (
    <WarningCallout>
      <WarningCallout.Heading headingLevel="h2">Backend offline</WarningCallout.Heading>
      <p>
        The Clerkstone API could not be reached at{" "}
        <code>{getApiBaseUrl()}</code>. Start the backend (see the repo README) and then retry.
      </p>
      {retry ? (
        <button type="button" className="nhsuk-button" onClick={retry}>
          Retry
        </button>
      ) : null}
    </WarningCallout>
  );
}
