/**
 * Simplified FHIRPath → JSON Pointer resolver.
 *
 * This is intentionally a *minimal* resolver for the subset of FHIRPath used by
 * Clerkstone quality rules: dot navigation, `[n]` array indexing and `[*]`
 * wildcards. It turns an expression like `Encounter.period.end` into the set of
 * JSON Pointers (RFC 6901) that locate the offending element(s) in the raw FHIR
 * resource, so the resource viewer can highlight them.
 *
 * It does NOT implement the full FHIRPath spec (no `where()`, `select()`,
 * unions, functions, etc.). Unsupported constructs degrade to "no match"
 * rather than a misleading highlight.
 */

export type PathSegment = string | number;

interface Token {
  key: string;
  index: number | null; // null = whole property; number = array index; -1 = wildcard
}

const FHIR_RESOURCE_TYPES = new Set([
  "Patient",
  "Encounter",
  "Observation",
  "Condition",
  "MedicationRequest",
  "Procedure",
  "AllergyIntolerance",
  "DiagnosticReport",
  "Immunization",
  "Organization",
  "Practitioner",
  "PractitionerRole",
  "Provenance",
  "Bundle",
]);

function tokenize(expression: string): Token[] {
  const parts = expression.split(".").map((p) => p.trim()).filter(Boolean);
  return parts.map((part) => {
    const match = part.match(/^(?<key>[^[\]]+)(?<brackets>\[[^\]]*\])?$/);
    if (!match?.groups) {
      return { key: part, index: null };
    }
    const key = match.groups.key.trim();
    const bracket = match.groups.brackets;
    if (!bracket) return { key, index: null };
    const inner = bracket.slice(1, -1).trim();
    if (inner === "*") return { key, index: -1 };
    const numeric = Number.parseInt(inner, 10);
    return { key, index: Number.isNaN(numeric) ? null : numeric };
  });
}

function isValue(value: unknown): value is Record<string, unknown> | unknown[] {
  return typeof value === "object" && value !== null;
}

function walk(
  node: unknown,
  tokens: Token[],
  depth: number,
  pointer: string,
  out: string[],
): void {
  if (depth >= tokens.length) {
    out.push(pointer);
    return;
  }

  const token = tokens[depth];

  if (!isValue(node)) return;

  if (Array.isArray(node)) {
    if (token.index === -1) {
      node.forEach((_, i) => walk(node[i], tokens, depth + 1, `${pointer}/${encodeSegment(i)}`, out));
    } else if (token.index !== null) {
      walk(node[token.index], tokens, depth + 1, `${pointer}/${encodeSegment(token.index)}`, out);
    }
    return;
  }

  if (!(token.key in node)) return;
  const child = node[token.key];

  if (token.index === -1 && Array.isArray(child)) {
    child.forEach((_, i) => walk(child[i], tokens, depth + 1, `${pointer}/${encodeSegment(token.key)}/${encodeSegment(i)}`, out));
    return;
  }
  if (token.index !== null && Array.isArray(child)) {
    walk(child[token.index], tokens, depth + 1, `${pointer}/${encodeSegment(token.key)}/${encodeSegment(token.index)}`, out);
    return;
  }
  walk(child, tokens, depth + 1, `${pointer}/${encodeSegment(token.key)}`, out);
}

/** RFC 6901 JSON Pointer segment escaping. */
export function encodeSegment(segment: PathSegment): string {
  return String(segment).replace(/~/g, "~0").replace(/\//g, "~1");
}

export function joinPointer(segments: PathSegment[]): string {
  return segments.length === 0 ? "" : `/${segments.map(encodeSegment).join("/")}`;
}

/**
 * Resolve a FHIRPath expression against a parsed FHIR resource, returning the
 * JSON Pointers of every matching element (empty array when nothing matches).
 */
export function resolveFhirPath(root: unknown, expression: string): string[] {
  if (!expression || !isValue(root)) return [];

  const tokens = tokenize(expression);
  if (tokens.length === 0) return [];

  const first = tokens[0];
  if (FHIR_RESOURCE_TYPES.has(first.key)) {
    tokens.shift();
  }
  if (tokens.length === 0) return [];

  const out: string[] = [];
  walk(root, tokens, 0, "", out);
  return out;
}
