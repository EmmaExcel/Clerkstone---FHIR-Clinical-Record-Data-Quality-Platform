"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Table } from "nhsuk-react-components";
import { getAuditEvents } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, LoadingState } from "@/components/ui/AsyncStatus";
import { PaginationControls } from "@/components/ui/PaginationControls";
import { AuditOutcomeBadge } from "@/components/ui/StatusBadge";
import { formatDateTime, humanizeAction } from "@/lib/utils";

const PAGE_SIZE = 25;

export default function AdminPage() {
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ["audit-events", page],

    queryFn: () => getAuditEvents({ _count: PAGE_SIZE, _page: page - 1 }),
  });

  const events = query.data?.events ?? [];
  const total = query.data?.total ?? events.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader title="Audit log" caption="Clerkstone · admin" />

      <p className="nhsuk-body">
        Append-only, hash-chained audit trail covering reads as well as writes. Each event records
        the actor, role, action and outcome, with a correlation ID for tracing.
      </p>

      {query.isPending ? (
        <LoadingState label="Loading audit events" />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => query.refetch()} />
      ) : events.length === 0 ? (
        <p className="nhsuk-body" role="status" aria-live="polite">
          No audit events recorded yet.
        </p>
      ) : (
        <>
          <Table.Container>
            <Table caption="Audit events">
              <Table.Head>
                <Table.Row>
                  <Table.Cell>Time</Table.Cell>
                  <Table.Cell>Actor</Table.Cell>
                  <Table.Cell>Role</Table.Cell>
                  <Table.Cell>Action</Table.Cell>
                  <Table.Cell>Resource</Table.Cell>
                  <Table.Cell>Outcome</Table.Cell>
                  <Table.Cell>Request ID</Table.Cell>
                </Table.Row>
              </Table.Head>
              <Table.Body>
                {events.map((event) => (
                  <Table.Row key={event.id}>
                    <Table.Cell>{formatDateTime(event.occurred_at)}</Table.Cell>
                    <Table.Cell>{event.actor}</Table.Cell>
                    <Table.Cell>{event.actor_role}</Table.Cell>
                    <Table.Cell>{humanizeAction(event.action)}</Table.Cell>
                    <Table.Cell>
                      {event.resource_type ? (
                        <code>
                          {event.resource_type}
                          {event.resource_id ? ` ${event.resource_id}` : ""}
                        </code>
                      ) : (
                        "—"
                      )}
                    </Table.Cell>
                    <Table.Cell>
                      <AuditOutcomeBadge outcome={event.outcome} />
                    </Table.Cell>
                    <Table.Cell>
                      <code title={event.request_id}>{shortId(event.request_id)}</code>
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          </Table.Container>
          <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}

function shortId(id: string): string {
  return id.length > 12 ? `${id.slice(0, 12)}…` : id;
}
