"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { BackLink, SummaryList } from "nhsuk-react-components";
import { getPatient, type ResourceCounts } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, LoadingState } from "@/components/ui/AsyncStatus";
import { formatAge, formatDate, formatNhsNumber, fullName, nhsNumberStatusLabel } from "@/lib/utils";

const COUNT_ITEMS: Array<{ key: keyof ResourceCounts; label: string }> = [
  { key: "encounters", label: "Encounters" },
  { key: "observations", label: "Observations" },
  { key: "conditions", label: "Conditions" },
  { key: "medications", label: "Medications" },
];

export default function PatientPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const query = useQuery({
    queryKey: ["patient", id],
    queryFn: () => getPatient(id),
    enabled: Boolean(id),
  });

  if (query.isPending) {
    return (
      <div>
        <BackLink href="/patients">Back to patient search</BackLink>
        <LoadingState label="Loading patient" />
      </div>
    );
  }

  if (query.isError) {
    return <ErrorState error={query.error} retry={() => query.refetch()} />;
  }

  const { patient, counts } = query.data;

  return (
    <div>
      <BackLink href="/patients">Back to patient search</BackLink>
      <PageHeader
        title={fullName(patient)}
        caption={`NHS number ${formatNhsNumber(patient.nhs_number)}`}
      />

      <SummaryList>
        <SummaryList.Row>
          <SummaryList.Key>NHS number</SummaryList.Key>
          <SummaryList.Value>{formatNhsNumber(patient.nhs_number)}</SummaryList.Value>
        </SummaryList.Row>
        <SummaryList.Row>
          <SummaryList.Key>NHS number status</SummaryList.Key>
          <SummaryList.Value>{nhsNumberStatusLabel(patient.nhs_number_status)}</SummaryList.Value>
        </SummaryList.Row>
        <SummaryList.Row>
          <SummaryList.Key>Date of birth</SummaryList.Key>
          <SummaryList.Value>{formatDate(patient.birth_date)}</SummaryList.Value>
        </SummaryList.Row>
        <SummaryList.Row>
          <SummaryList.Key>Age</SummaryList.Key>
          <SummaryList.Value>{formatAge(patient.age_years)}</SummaryList.Value>
        </SummaryList.Row>
        <SummaryList.Row>
          <SummaryList.Key>Gender</SummaryList.Key>
          <SummaryList.Value>{patient.gender ?? "—"}</SummaryList.Value>
        </SummaryList.Row>
        <SummaryList.Row>
          <SummaryList.Key>Postcode (outward only)</SummaryList.Key>
          <SummaryList.Value>{patient.postcode ?? "—"}</SummaryList.Value>
        </SummaryList.Row>
        <SummaryList.Row>
          <SummaryList.Key>Deceased</SummaryList.Key>
          <SummaryList.Value>{patient.deceased ? "Yes" : "No"}</SummaryList.Value>
        </SummaryList.Row>
      </SummaryList>

      <h2 className="nhsuk-heading-l">Record counts</h2>
      <div className="clerkstone-stat-grid">
        {COUNT_ITEMS.map((item) => (
          <div key={item.key} className="clerkstone-stat">
            <p className="clerkstone-stat__value">{counts?.[item.key] ?? 0}</p>
            <p className="nhsuk-body-s">{item.label}</p>
          </div>
        ))}
      </div>

      <div className="nhsuk-u-margin-top-4">
        <Link href={`/patients/${id}/timeline`} className="nhsuk-button">
          View clinical timeline
        </Link>
      </div>
    </div>
  );
}
