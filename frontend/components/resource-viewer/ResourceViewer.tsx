"use client";

import { useMemo } from "react";
import { Heading } from "nhsuk-react-components";
import { JsonTree } from "./JsonTree";
import { resolveFhirPath } from "./fhirpath";

export interface ResourceViewerProps {
  resource: unknown;
  /** FHIRPath expressions whose matching elements should be highlighted. */
  expressions?: string[] | null;
  /** Optional heading shown above the JSON. */
  title?: string;
}

/**
 * Pretty-printed FHIR JSON with the offending FHIRPath location highlighted.
 */
export function ResourceViewer({ resource, expressions, title }: ResourceViewerProps) {
  const highlighted = useMemo(() => {
    const pointers = new Set<string>();
    for (const expression of expressions ?? []) {
      for (const pointer of resolveFhirPath(resource, expression)) {
        pointers.add(pointer);
      }
    }
    return pointers;
  }, [resource, expressions]);

  return (
    <section aria-label={title ?? "FHIR resource"}>
      {title ? (
        <Heading headingLevel="h2" size="m">
          {title}
        </Heading>
      ) : null}
      {expressions && expressions.length > 0 ? (
        <p className="nhsuk-body-s">
          Highlighting FHIRPath{" "}
          <code>{expressions.map((expression) => `“${expression}”`).join(", ")}</code>
          {highlighted.size === 0 ? (
            <> — no matching element found in this resource.</>
          ) : (
            <> — the matching element(s) are flagged below.</>
          )}
        </p>
      ) : null}
      <JsonTree data={resource} highlighted={highlighted} />
    </section>
  );
}
