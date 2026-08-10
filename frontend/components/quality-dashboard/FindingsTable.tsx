"use client";

import { Fragment, useState } from "react";
import { Button, Table } from "nhsuk-react-components";
import type { QualityFinding } from "@/lib/api";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { ReviewStatusBadge } from "@/components/ui/StatusBadge";
import { FindingDetail } from "./FindingDetail";

export function FindingsTable({ findings }: { findings: QualityFinding[] }) {
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((previous) => {
      const next = new Set(previous);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (findings.length === 0) {
    return <p className="nhsuk-body">No findings match the current filters.</p>;
  }

  return (
    <Table.Container>
      <Table caption="Quality findings">
        <Table.Head>
          <Table.Row>
            <Table.Cell>Severity</Table.Cell>
            <Table.Cell>Rule</Table.Cell>
            <Table.Cell>Title</Table.Cell>
            <Table.Cell>Resource</Table.Cell>
            <Table.Cell>Review</Table.Cell>
            <Table.Cell>
              <span className="clerkstone-sr-only">Actions</span>
            </Table.Cell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {findings.map((finding) => {
            const isOpen = expanded.has(finding.id);
            return (
              <Fragment key={finding.id}>
                <Table.Row>
                  <Table.Cell>
                    <SeverityBadge severity={finding.severity} />
                  </Table.Cell>
                  <Table.Cell>{finding.rule_id}</Table.Cell>
                  <Table.Cell>{finding.title}</Table.Cell>
                  <Table.Cell>
                    {finding.resource ? (
                      <code>
                        {finding.resource.type}/{finding.resource.logical_id}
                      </code>
                    ) : (
                      "—"
                    )}
                  </Table.Cell>
                  <Table.Cell>
                    <ReviewStatusBadge status={finding.review_status} />
                  </Table.Cell>
                  <Table.Cell>
                    <Button
                      secondary
                      small
                      onClick={() => toggle(finding.id)}
                      aria-expanded={isOpen}
                      aria-controls={`finding-detail-${finding.id}`}
                    >
                      {isOpen ? "Hide" : "View"}
                    </Button>
                  </Table.Cell>
                </Table.Row>
                {isOpen ? (
                  <Table.Row>
                    <Table.Cell colSpan={6} id={`finding-detail-${finding.id}`}>
                      <FindingDetail finding={finding} />
                    </Table.Cell>
                  </Table.Row>
                ) : null}
              </Fragment>
            );
          })}
        </Table.Body>
      </Table>
    </Table.Container>
  );
}
