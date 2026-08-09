"use client";

import { Tag } from "nhsuk-react-components";
import classNames from "classnames";
import type { TimelineEntry, TimelineResourceType } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

export const RESOURCE_TYPE_LABELS: Record<TimelineResourceType, string> = {
  Encounter: "Encounter",
  Observation: "Observation",
  Condition: "Condition",
  MedicationRequest: "Medication",
  Procedure: "Procedure",
  AllergyIntolerance: "Allergy",
  DiagnosticReport: "Report",
  Immunization: "Immunisation",
};

const INTERPRETATION_MODIFIERS: Record<string, "red" | "orange" | "green" | "yellow"> = {
  high: "red",
  critical: "red",
  abnormal: "red",
  low: "orange",
  borderline: "yellow",
  normal: "green",
};

export function TimelineEntryItem({ entry }: { entry: TimelineEntry }) {
  const flags = entry.quality_flags ?? [];
  const flagged = flags.length > 0;

  return (
    <li
      className={classNames("clerkstone-timeline__entry", {
        "clerkstone-timeline__entry--flagged": flagged,
      })}
    >
      <div className="clerkstone-timeline__meta">
        <span className="nhsuk-body-s">{formatDateTime(entry.date)}</span>
        <Tag modifier="grey">{RESOURCE_TYPE_LABELS[entry.type] ?? entry.type}</Tag>
        {flagged ? (
          <span>
            <span className="clerkstone-sr-only">Quality flags: </span>
            {flags.map((flag) => (
              <Tag key={flag} modifier="orange" className="nhsuk-u-margin-right-1">
                <span className="clerkstone-severity">
                  <span className="clerkstone-severity__icon" aria-hidden="true">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" focusable="false">
                      <path d="M12 2 1 21h22L12 2zm1 14h-2v2h2v-2zm0-7h-2v5h2V9z" />
                    </svg>
                  </span>
                  {flag}
                </span>
              </Tag>
            ))}
          </span>
        ) : null}
      </div>

      <EntryContent entry={entry} />
    </li>
  );
}

function EntryContent({ entry }: { entry: TimelineEntry }) {
  switch (entry.type) {
    case "Encounter":
      return (
        <div>
          <strong>{entry.display ?? "Encounter"}</strong>
          <span className="nhsuk-body-s">
            {" "}
            {[entry.class, entry.status]
              .filter((value): value is string => Boolean(value))
              .map(capitalize)
              .join(" · ") ||
              (entry.period_start && entry.period_end
                ? `${formatDateTime(entry.period_start)} – ${formatDateTime(entry.period_end)}`
                : "")}
          </span>
        </div>
      );
    case "Observation":
      return (
        <div>
          <strong>{entry.display ?? "Observation"}</strong>
          {entry.value ? <span> — {entry.value}</span> : null}{" "}
          {entry.interpretation ? (
            <Tag modifier={INTERPRETATION_MODIFIERS[entry.interpretation] ?? "grey"}>
              {entry.interpretation}
            </Tag>
          ) : null}{" "}
          {entry.code && !entry.code.resolved ? (
            <Tag modifier="yellow">unresolved code</Tag>
          ) : null}
        </div>
      );
    case "Condition":
      return (
        <div>
          <strong>{entry.display ?? "Condition"}</strong>{" "}
          {entry.clinical_status ? (
            <span className="nhsuk-body-s">({entry.clinical_status})</span>
          ) : null}
        </div>
      );
    case "MedicationRequest":
      return (
        <div>
          <strong>{entry.display ?? "Medication"}</strong>{" "}
          {entry.dosage_text ? <span className="nhsuk-body-s">— {entry.dosage_text}</span> : null}{" "}
          {entry.status ? (
            <span className="nhsuk-body-s">({entry.status})</span>
          ) : null}
        </div>
      );
    default:
      return (
        <div>
          <strong>{entry.display ?? entry.type}</strong>
        </div>
      );
  }
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
