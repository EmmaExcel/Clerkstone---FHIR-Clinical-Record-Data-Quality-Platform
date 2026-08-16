"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Select, TextInput } from "nhsuk-react-components";
import { searchPatients, type PatientListItem } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { PaginationControls } from "@/components/ui/PaginationControls";
import { ErrorState, LoadingState } from "@/components/ui/AsyncStatus";
import { formatDate, formatNhsNumber, fullName } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function PatientsPage() {
  const [family, setFamily] = useState("");
  const [debouncedFamily, setDebouncedFamily] = useState("");
  const [gender, setGender] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedFamily(family);
      setPage(1);
    }, 300);
    return () => clearTimeout(handle);
  }, [family]);

  const query = useQuery({
    queryKey: ["patients", debouncedFamily, gender, page],
    queryFn: () =>
      searchPatients({
        family: debouncedFamily.trim() || undefined,
        gender: gender || undefined,
        _count: PAGE_SIZE,
        _page: page - 1,
      }),
  });

  const patients = query.data?.patients ?? [];
  const total = query.data?.total ?? patients.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader title="Patient search" caption="Clerkstone" />

      <TextInput
        id="patient-search"
        name="family"
        label="Search patients"
        hint="Search by family name. Results appear as you type."
        width="20"
        value={family}
        onChange={(event) => setFamily(event.target.value)}
        autoComplete="off"
      />

      <Select
        label="Gender"
        id="patient-gender"
        value={gender}
        onChange={(event) => {
          setGender(event.target.value);
          setPage(1);
        }}
      >
        <Select.Option value="">All genders</Select.Option>
        <Select.Option value="female">Female</Select.Option>
        <Select.Option value="male">Male</Select.Option>
        <Select.Option value="other">Other</Select.Option>
        <Select.Option value="unknown">Unknown</Select.Option>
      </Select>

      <PatientResults
        patients={patients}
        total={total}
        page={page}
        totalPages={totalPages}
        isPending={query.isPending}
        isError={query.isError}
        error={query.error}
        onRetry={() => query.refetch()}
        onPageChange={setPage}
      />
    </div>
  );
}

function PatientResults({
  patients,
  total,
  page,
  totalPages,
  isPending,
  isError,
  error,
  onRetry,
  onPageChange,
}: {
  patients: PatientListItem[];
  total: number;
  page: number;
  totalPages: number;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  onPageChange: (page: number) => void;
}) {
  const [activeIndex, setActiveIndex] = useState(-1);
  const linkRefs = useRef<(HTMLAnchorElement | null)[]>([]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLUListElement>) => {
    if (patients.length === 0) return;
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        moveFocus((activeIndex + 1 + patients.length) % patients.length);
        break;
      case "ArrowUp":
        event.preventDefault();
        moveFocus((activeIndex - 1 + patients.length) % patients.length);
        break;
      case "Home":
        event.preventDefault();
        moveFocus(0);
        break;
      case "End":
        event.preventDefault();
        moveFocus(patients.length - 1);
        break;
      default:
        break;
    }
  };

  const moveFocus = (index: number) => {
    setActiveIndex(index);
    linkRefs.current[index]?.focus();
  };

  if (isPending) {
    return <LoadingState label="Searching patients" />;
  }
  if (isError) {
    return <ErrorState error={error} retry={onRetry} />;
  }
  if (patients.length === 0) {
    return (
      <p className="nhsuk-body" role="status" aria-live="polite">
        No patients found. Try a different name or gender.
      </p>
    );
  }

  return (
    <div className="nhsuk-u-margin-top-4">
      <p className="nhsuk-body-s" role="status" aria-live="polite">
        {total} patient{total === 1 ? "" : "s"} found. Use the Tab key or arrow keys to move
        through results.
      </p>
      <ul className="nhsuk-list clerkstone-search-results" onKeyDown={onKeyDown}>
        {patients.map((patient, index) => (
          <li key={patient.id}>
            <Link
              href={`/patients/${patient.id}`}
              ref={(element) => {
                linkRefs.current[index] = element;
              }}
              className="nhsuk-link clerkstone-search-result"
              onFocus={() => setActiveIndex(index)}
            >
              <strong>{fullName(patient)}</strong>
              <span className="nhsuk-body-s"> — {formatNhsNumber(patient.nhs_number)}</span>
              {patient.birth_date ? (
                <span className="nhsuk-body-s"> · born {formatDate(patient.birth_date)}</span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
      <PaginationControls page={page} totalPages={totalPages} onPageChange={onPageChange} />
    </div>
  );
}
