import { SummaryList } from "nhsuk-react-components";
import type { QualityRun } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { RunStatusBadge } from "@/components/ui/StatusBadge";

export function RunSummary({ run }: { run: QualityRun }) {
  const counts = run.counts;
  return (
    <SummaryList>
      <SummaryList.Row>
        <SummaryList.Key>Status</SummaryList.Key>
        <SummaryList.Value>
          <RunStatusBadge status={run.status} />
        </SummaryList.Value>
      </SummaryList.Row>
      <SummaryList.Row>
        <SummaryList.Key>Ruleset version</SummaryList.Key>
        <SummaryList.Value>{run.ruleset_version ?? "—"}</SummaryList.Value>
      </SummaryList.Row>
      <SummaryList.Row>
        <SummaryList.Key>Triggered by</SummaryList.Key>
        <SummaryList.Value>{run.triggered_by ?? "—"}</SummaryList.Value>
      </SummaryList.Row>
      <SummaryList.Row>
        <SummaryList.Key>Started</SummaryList.Key>
        <SummaryList.Value>{formatDateTime(run.started_at)}</SummaryList.Value>
      </SummaryList.Row>
      <SummaryList.Row>
        <SummaryList.Key>Finished</SummaryList.Key>
        <SummaryList.Value>{run.finished_at ? formatDateTime(run.finished_at) : "—"}</SummaryList.Value>
      </SummaryList.Row>
      <SummaryList.Row>
        <SummaryList.Key>Findings</SummaryList.Key>
        <SummaryList.Value>
          {counts
            ? `${counts.error} error, ${counts.warning} warning, ${counts.info} info`
            : "—"}
        </SummaryList.Value>
      </SummaryList.Row>
    </SummaryList>
  );
}
