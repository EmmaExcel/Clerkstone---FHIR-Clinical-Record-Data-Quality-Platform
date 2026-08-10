"use client";

import { Checkboxes } from "nhsuk-react-components";
import type { TimelineResourceType } from "@/lib/api";
import { RESOURCE_TYPE_LABELS } from "./TimelineEntry";

export const FILTERABLE_TYPES: TimelineResourceType[] = [
  "Encounter",
  "Observation",
  "Condition",
  "MedicationRequest",
  "Procedure",
  "AllergyIntolerance",
  "DiagnosticReport",
  "Immunization",
];

export interface TimelineFilterProps {
  selected: ReadonlySet<string>;
  onChange: (next: Set<string>) => void;
  /** Types to offer in the filter; defaults to all filterable types. */
  types?: TimelineResourceType[];
}

/**
 * Resource-type filter for the clinical timeline. Filtering "Encounter" off
 * flattens the timeline (see Timeline); other types toggle individual rows.
 */
export function TimelineFilter({ selected, onChange, types = FILTERABLE_TYPES }: TimelineFilterProps) {
  const toggle = (type: string) => {
    const next = new Set(selected);
    if (next.has(type)) {
      next.delete(type);
    } else {
      next.add(type);
    }
    onChange(next);
  };

  return (
    <Checkboxes legend="Filter by resource type" idPrefix="timeline-filter">
      {types.map((type) => (
        <Checkboxes.Item
          key={type}
          value={type}
          checked={selected.has(type)}
          onChange={() => toggle(type)}
        >
          {RESOURCE_TYPE_LABELS[type]}
        </Checkboxes.Item>
      ))}
    </Checkboxes>
  );
}
