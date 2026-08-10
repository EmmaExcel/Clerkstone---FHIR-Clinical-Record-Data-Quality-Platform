"use client";

import Link from "next/link";
import { Table } from "nhsuk-react-components";
import type { QualityRun } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { RunStatusBadge } from "@/components/ui/StatusBadge";

export function RunList({ runs }: { runs: QualityRun[] }) {
  if (runs.length === 0) {
    return <p className="nhsuk-body">No quality runs yet.</p>;
  }

  return (
    <Table.Container>
      <Table caption="Quality runs">
        <Table.Head>
          <Table.Row>
            <Table.Cell>Run</Table.Cell>
            <Table.Cell>Status</Table.Cell>
            <Table.Cell>Ruleset</Table.Cell>
            <Table.Cell>Started</Table.Cell>
            <Table.Cell>Findings</Table.Cell>
            <Table.Cell>
              <span className="clerkstone-sr-only">Actions</span>
            </Table.Cell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {runs.map((run) => {
            const counts = run.counts;
            return (
              <Table.Row key={run.id}>
                <Table.Cell>
                  <code>{shortId(run.id)}</code>
                </Table.Cell>
                <Table.Cell>
                  <RunStatusBadge status={run.status} />
                </Table.Cell>
                <Table.Cell>{run.ruleset_version ?? "—"}</Table.Cell>
                <Table.Cell>{formatDateTime(run.started_at)}</Table.Cell>
                <Table.Cell>
                  {counts
                    ? `${counts.error} / ${counts.warning} / ${counts.info}`
                    : "—"}
                </Table.Cell>
                <Table.Cell>
                  <Link href={`/quality/${run.id}`} className="nhsuk-link">
                    View report
                    <span className="clerkstone-sr-only"> for run {shortId(run.id)}</span>
                  </Link>
                </Table.Cell>
              </Table.Row>
            );
          })}
        </Table.Body>
      </Table>
    </Table.Container>
  );
}

function shortId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}
