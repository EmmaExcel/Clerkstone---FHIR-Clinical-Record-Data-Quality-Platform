"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, WarningCallout } from "nhsuk-react-components";
import { getQualityRuns, startQualityRun } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, LoadingState } from "@/components/ui/AsyncStatus";
import { RunList } from "@/components/quality-dashboard";
import { PaginationControls } from "@/components/ui/PaginationControls";

const PAGE_SIZE = 20;

export default function QualityPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const runsQuery = useQuery({
    queryKey: ["quality-runs", page],

    queryFn: () => getQualityRuns({ _count: PAGE_SIZE, _page: page - 1 }),
  });

  const startMutation = useMutation({
    mutationFn: () => startQualityRun(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quality-runs"] });
    },
  });

  const runs = runsQuery.data?.runs ?? [];
  const total = runsQuery.data?.total ?? runs.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader title="Quality dashboard" caption="Clerkstone" />

      <p className="nhsuk-body">
        Run the data-quality rule engine over the stored records, then drill from any finding to the
        exact FHIR element that caused it.
      </p>

      <div className="nhsuk-u-margin-bottom-4">
        <Button onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
          {startMutation.isPending ? "Starting run…" : "Start quality run"}
        </Button>
        {startMutation.isSuccess ? (
          <p className="nhsuk-body-s" role="status" aria-live="polite">
            Quality run started. Refresh the list to see it complete.
          </p>
        ) : null}
        {startMutation.isError ? (
          <div role="alert" aria-live="assertive">
            <WarningCallout>
              <WarningCallout.Heading headingLevel="h2">Could not start run</WarningCallout.Heading>
              <p>{errorMessage(startMutation.error)}</p>
            </WarningCallout>
          </div>
        ) : null}
      </div>

      {runsQuery.isPending ? (
        <LoadingState label="Loading quality runs" />
      ) : runsQuery.isError ? (
        <ErrorState error={runsQuery.error} retry={() => runsQuery.refetch()} />
      ) : (
        <>
          <RunList runs={runs} />
          <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}
