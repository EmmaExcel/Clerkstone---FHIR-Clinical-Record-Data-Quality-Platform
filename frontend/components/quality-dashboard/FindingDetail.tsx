"use client";

import { useQuery } from "@tanstack/react-query";
import { InsetText, SummaryList } from "nhsuk-react-components";
import type { QualityFinding } from "@/lib/api";
import { getFhirResource } from "@/lib/api";
import { ResourceViewer } from "@/components/resource-viewer";
import { ErrorState, LoadingState } from "@/components/ui/AsyncStatus";
import { ReviewStatusBadge } from "@/components/ui/StatusBadge";

export function FindingDetail({ finding }: { finding: QualityFinding }) {
  const resource = finding.resource;

  const resourceQuery = useQuery({
    queryKey: ["fhir-resource", resource?.type, resource?.logical_id],
    queryFn: () => getFhirResource(resource!.type, resource!.logical_id),
    enabled: Boolean(resource),
  });

  return (
    <div className="nhsuk-u-padding-top-2 nhsuk-u-padding-bottom-2">
      <p className="nhsuk-body">
        <strong>{finding.message}</strong>
      </p>

      {finding.suggested_action ? (
        <InsetText>
          <strong>Suggested action:</strong> {finding.suggested_action}
        </InsetText>
      ) : null}

      <SummaryList>
        <SummaryList.Row>
          <SummaryList.Key>Rule</SummaryList.Key>
          <SummaryList.Value>{finding.rule_id}</SummaryList.Value>
        </SummaryList.Row>
        <SummaryList.Row>
          <SummaryList.Key>Review status</SummaryList.Key>
          <SummaryList.Value>
            <ReviewStatusBadge status={finding.review_status} />
          </SummaryList.Value>
        </SummaryList.Row>
        {finding.expression && finding.expression.length > 0 ? (
          <SummaryList.Row>
            <SummaryList.Key>FHIRPath</SummaryList.Key>
            <SummaryList.Value>
              <code>{finding.expression.join(", ")}</code>
            </SummaryList.Value>
          </SummaryList.Row>
        ) : null}
        {resource ? (
          <SummaryList.Row>
            <SummaryList.Key>Resource</SummaryList.Key>
            <SummaryList.Value>
              {resource.type} <code>{resource.logical_id}</code>
            </SummaryList.Value>
          </SummaryList.Row>
        ) : null}
      </SummaryList>

      {resource ? (
        <div className="nhsuk-u-margin-top-4">
          {resourceQuery.isLoading ? (
            <LoadingState label="Loading resource" />
          ) : resourceQuery.isError ? (
            <ErrorState error={resourceQuery.error} />
          ) : resourceQuery.data !== undefined ? (
            <ResourceViewer
              resource={resourceQuery.data}
              expressions={finding.expression}
              title={`${resource.type} ${resource.logical_id}`}
            />
          ) : null}
        </div>
      ) : (
        <p className="nhsuk-body-s">
          This finding does not reference a single FHIR resource, so no resource viewer is shown.
        </p>
      )}
    </div>
  );
}
