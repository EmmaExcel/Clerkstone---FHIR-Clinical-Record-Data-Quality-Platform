"use client";

import { encodeSegment, type PathSegment } from "./fhirpath";

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function childPointer(parent: string, segment: PathSegment): string {
  return `${parent}/${encodeSegment(segment)}`;
}

/**
 * Pretty-printed FHIR JSON tree. Nodes whose JSON Pointer appears in
 * `highlighted` (computed from a FHIRPath expression) are visually flagged —
 * with a background + left border AND screen-reader text, so the highlight is
 * never conveyed by colour alone.
 */
export function JsonTree({ data, highlighted }: { data: unknown; highlighted: Set<string> }) {
  return (
    <div
      className="clerkstone-json-tree"
      role="region"
      aria-label="FHIR resource, pretty-printed JSON"
      tabIndex={0}
    >
      <JsonNode value={data} pointer="" highlighted={highlighted} />
    </div>
  );
}

function matchClass(isMatch: boolean): string {
  return isMatch ? "clerkstone-json-node--match" : "";
}

function JsonNode({
  value,
  pointer,
  highlighted,
}: {
  value: unknown;
  pointer: string;
  highlighted: Set<string>;
}) {
  const isMatch = highlighted.has(pointer);

  if (isPlainObject(value)) {
    const keys = Object.keys(value);
    if (keys.length === 0) {
      return <span className="clerkstone-json-punct">{"{}"}</span>;
    }
    return (
      <>
        <span className={`clerkstone-json-punct ${matchClass(isMatch)}`}>{"{"}</span>
        <div className={`clerkstone-json-indent ${matchClass(isMatch)}`}>
          {keys.map((key, index) => (
            <div key={key}>
              <span className="clerkstone-json-key">{JSON.stringify(key)}</span>
              <span className="clerkstone-json-punct">{": "}</span>
              <JsonNode
                value={value[key]}
                pointer={childPointer(pointer, key)}
                highlighted={highlighted}
              />
              {index < keys.length - 1 ? <span className="clerkstone-json-punct">{","}</span> : null}
            </div>
          ))}
        </div>
        <span className={`clerkstone-json-punct ${matchClass(isMatch)}`}>{"}"}</span>
      </>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="clerkstone-json-punct">{"[]"}</span>;
    }
    return (
      <>
        <span className={`clerkstone-json-punct ${matchClass(isMatch)}`}>{"["}</span>
        <div className={`clerkstone-json-indent ${matchClass(isMatch)}`}>
          {value.map((item, index) => (
            <div key={index}>
              <JsonNode
                value={item}
                pointer={childPointer(pointer, index)}
                highlighted={highlighted}
              />
              {index < value.length - 1 ? <span className="clerkstone-json-punct">{","}</span> : null}
            </div>
          ))}
        </div>
        <span className={`clerkstone-json-punct ${matchClass(isMatch)}`}>{"]"}</span>
      </>
    );
  }

  return (
    <Scalar value={value} isMatch={isMatch} />
  );
}

function Scalar({ value, isMatch }: { value: unknown; isMatch: boolean }) {
  const className =
    value === null
      ? "clerkstone-json-null"
      : typeof value === "string"
        ? "clerkstone-json-string"
        : typeof value === "number"
          ? "clerkstone-json-number"
          : typeof value === "boolean"
            ? "clerkstone-json-boolean"
            : "clerkstone-json-string";

  const rendered = value === null ? "null" : JSON.stringify(value);

  return (
    <span
      className={`${className} ${matchClass(isMatch)}`}
      title={isMatch ? "Matches the FHIRPath expression" : undefined}
    >
      {rendered}
      {isMatch ? <span className="clerkstone-sr-only"> (matches FHIRPath expression)</span> : null}
    </span>
  );
}
