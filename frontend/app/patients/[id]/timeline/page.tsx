"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { BackLink } from "nhsuk-react-components";
import { getPatientTimeline } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, LoadingState } from "@/components/ui/AsyncStatus";
import { Timeline } from "@/components/clinical-timeline";
import { formatNhsNumber, fullName } from "@/lib/utils";

export default function PatientTimelinePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const query = useQuery({
    queryKey: ["patient-timeline", id],
    queryFn: () => getPatientTimeline(id),
    enabled: Boolean(id),
  });

  if (query.isPending) {
    return (
      <div>
        <BackLink href={`/patients/${id}`}>Back to patient summary</BackLink>
        <LoadingState label="Loading clinical timeline" />
      </div>
    );
  }

  if (query.isError) {
    return <ErrorState error={query.error} retry={() => query.refetch()} />;
  }

  const patient = query.data.patient;
  const entries = query.data.entries ?? [];

  return (
    <div>
      <BackLink href={`/patients/${id}`}>Back to patient summary</BackLink>
      <PageHeader
        title="Clinical timeline"
        caption={`${fullName(patient)} · ${formatNhsNumber(patient.nhs_number)}`}
      />

      <Timeline entries={entries} />
    </div>
  );
}
