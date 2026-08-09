"use client";

import { useMemo, useState } from "react";
import { Heading, Tag } from "nhsuk-react-components";
import type { TimelineEntry } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { TimelineEntryItem } from "./TimelineEntry";
import { TimelineFilter, FILTERABLE_TYPES } from "./TimelineFilter";

interface Group {
  encounter: TimelineEntry | null;
  entries: TimelineEntry[];
}

function byDate(a: TimelineEntry, b: TimelineEntry): number {
  const ta = new Date(a.date).getTime();
  const tb = new Date(b.date).getTime();
  return (Number.isNaN(ta) ? 0 : ta) - (Number.isNaN(tb) ? 0 : tb);
}

function groupByEncounter(entries: TimelineEntry[]): Group[] {
  const groups: Group[] = [];
  let current: Group = { encounter: null, entries: [] };
  for (const entry of entries) {
    if (entry.type === "Encounter") {
      if (current.encounter || current.entries.length > 0) groups.push(current);
      current = { encounter: entry, entries: [] };
    } else {
      current.entries.push(entry);
    }
  }
  if (current.encounter || current.entries.length > 0) groups.push(current);
  return groups;
}

export function Timeline({ entries }: { entries: TimelineEntry[] }) {
  const availableTypes = useMemo(
    () => FILTERABLE_TYPES.filter((type) => entries.some((entry) => entry.type === type)),
    [entries],
  );

  const [selected, setSelected] = useState<Set<string>>(() => new Set(entries.map((entry) => entry.type)));

  const showEncounters = selected.has("Encounter");

  const visible = useMemo(
    () => [...entries].sort(byDate).filter((entry) => selected.has(entry.type)),
    [entries, selected],
  );

  const groups = useMemo(
    () => (showEncounters ? groupByEncounter(visible) : null),
    [visible, showEncounters],
  );

  if (entries.length === 0) {
    return <p className="nhsuk-body">No clinical data recorded for this patient.</p>;
  }

  return (
    <div>
      {availableTypes.length > 0 ? (
        <TimelineFilter selected={selected} onChange={setSelected} types={availableTypes} />
      ) : null}

      <div aria-live="polite">
        {groups ? (
          groups.map((group, index) => (
            <EncounterGroup key={group.encounter?.id ?? `unattributed-${index}`} group={group} />
          ))
        ) : (
          <ul className="nhsuk-list">
            {visible.map((entry) => (
              <TimelineEntryItem key={entry.id} entry={entry} />
            ))}
          </ul>
        )}
        {visible.length === 0 ? (
          <p className="nhsuk-body" role="status">
            No entries match the selected resource types.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function EncounterGroup({ group }: { group: Group }) {
  if (group.encounter) {
    const encounter = group.encounter;
    const flags = encounter.quality_flags ?? [];
    return (
      <section
        className="clerkstone-timeline__group"
        aria-label={`${encounter.display ?? "Encounter"} — ${formatDateTime(encounter.date)}`}
      >
        <Heading headingLevel="h3" size="m">
          {encounter.display ?? "Encounter"}
        </Heading>
        <p className="nhsuk-body-s">
          {formatDateTime(encounter.date)}
          {encounter.class ? ` · ${capitalize(encounter.class)}` : ""}
          {encounter.status ? ` · ${capitalize(encounter.status)}` : ""}
        </p>
        {flags.length > 0 ? (
          <p>
            <span className="clerkstone-sr-only">Quality flags: </span>
            {flags.map((flag) => (
              <Tag key={flag} modifier="orange" className="nhsuk-u-margin-right-1">
                {flag}
              </Tag>
            ))}
          </p>
        ) : null}
        <ul className="nhsuk-list">
          {group.entries.map((entry) => (
            <TimelineEntryItem key={entry.id} entry={entry} />
          ))}
        </ul>
      </section>
    );
  }

  return (
    <section className="clerkstone-timeline__group" aria-label="Unattributed records">
      <Heading headingLevel="h3" size="m">
        Unattributed records
      </Heading>
      <ul className="nhsuk-list">
        {group.entries.map((entry) => (
          <TimelineEntryItem key={entry.id} entry={entry} />
        ))}
      </ul>
    </section>
  );
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
