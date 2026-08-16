"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { BackLink, Col, Heading, Row, Select } from "nhsuk-react-components";
import { getQualityRun, getQualityRunFindings, type Severity } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, LoadingState } from "@/components/ui/AsyncStatus";
import { PaginationControls } from "@/components/ui/PaginationControls";
import {
  FindingsTable,
  RunSummary,
  SeverityDonut,
  SeverityStatCards,
  TopRulesChart,
  type TopRuleDatum,
} from "@/components/quality-dashboard";

const PAGE_SIZE = 20;
const CHART_PAGE_SIZE = 200;

export default function QualityRunPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;

  const [severity, setSeverity] = useState<Severity | "">("");
  const [page, setPage] = useState(1);

  const runQuery = useQuery({
    queryKey: ["quality-run", runId],
    queryFn: () => getQualityRun(runId),
    enabled: Boolean(runId),
  });

  const findingsQuery = useQuery({
    queryKey: ["quality-run-findings", runId, severity, page],
    queryFn: () =>
      getQualityRunFindings(runId, {
        severity: severity || undefined,
        _count: PAGE_SIZE,
        _page: page,
      }),
    enabled: Boolean(runId),
  });

  const chartQuery = useQuery({
    queryKey: ["quality-run-top-rules", runId],
    queryFn: () => getQualityRunFindings(runId, { _count: CHART_PAGE_SIZE }),
    enabled: Boolean(runId),
  });

  const topRules = useMemo<TopRuleDatum[]>(() => {
    const findings = chartQuery.data?.findings ?? [];
    const counts = new Map<string, TopRuleDatum>();
    for (const finding of findings) {
      const existing = counts.get(finding.rule_id);
      if (existing) {
        existing.count += 1;
      } else {
        counts.set(finding.rule_id, {
          rule_id: finding.rule_id,
          title: finding.title,
          count: 1,
          severity: finding.severity,
        });
      }
    }
    return [...counts.values()].sort((a, b) => b.count - a.count).slice(0, 10);
  }, [chartQuery.data]);

  if (runQuery.isPending) {
    return (
      <div>
        <BackLink href="/quality">Back to quality dashboard</BackLink>
        <LoadingState label="Loading quality run" />
      </div>
    );
  }

  if (runQuery.isError) {
    return <ErrorState error={runQuery.error} retry={() => runQuery.refetch()} />;
  }

  const run = runQuery.data;
  const counts = run.counts ?? findingsQuery.data?.summary ?? { error: 0, warning: 0, info: 0 };
  const findings = findingsQuery.data?.findings ?? [];
  const findingsTotal = findingsQuery.data?.page?.total ?? findings.length;
  const totalPages = Math.max(1, Math.ceil(findingsTotal / PAGE_SIZE));

  return (
    <div>
      <BackLink href="/quality">Back to quality dashboard</BackLink>
      <PageHeader title="Quality run report" caption={`Run ${run.id}`} />

      <RunSummary run={run} />

      <Heading headingLevel="h2" size="l">
        Severity breakdown
      </Heading>
      <Row>
        <Col width="one-half">
          <SeverityStatCards counts={counts} />
        </Col>
        <Col width="one-half">
          <SeverityDonut counts={counts} />
        </Col>
      </Row>

      <Heading headingLevel="h2" size="l">
        Top rules
      </Heading>
      {chartQuery.isPending ? (
        <LoadingState label="Computing top rules" />
      ) : chartQuery.isError ? (
        <ErrorState error={chartQuery.error} retry={() => chartQuery.refetch()} />
      ) : (
        <TopRulesChart data={topRules} />
      )}

      <Heading headingLevel="h2" size="l">
        Findings
      </Heading>
      <Select
        label="Filter by severity"
        id="findings-severity"
        value={severity}
        onChange={(event) => {
          setSeverity(event.target.value as Severity | "");
          setPage(1);
        }}
      >
        <Select.Option value="">All severities</Select.Option>
        <Select.Option value="error">Error</Select.Option>
        <Select.Option value="warning">Warning</Select.Option>
        <Select.Option value="info">Info</Select.Option>
      </Select>

      {findingsQuery.isPending ? (
        <LoadingState label="Loading findings" />
      ) : findingsQuery.isError ? (
        <ErrorState error={findingsQuery.error} retry={() => findingsQuery.refetch()} />
      ) : (
        <>
          <FindingsTable findings={findings} />
          <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
