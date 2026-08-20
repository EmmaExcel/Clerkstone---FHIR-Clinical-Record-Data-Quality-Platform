import type { Severity } from "@/lib/api";

const SEVERITY_LABELS: Record<Severity, string> = {
  error: "Error",
  warning: "Warning",
  info: "Info",
};

/** Maps a severity to an nhsuk `Tag` modifier (colour is never the only cue). */
const SEVERITY_TAG_MODIFIERS: Record<Severity, "red" | "orange" | "blue"> = {
  error: "red",
  warning: "orange",
  info: "blue",
};

export function isSeverity(value: unknown): value is Severity {
  return value === "error" || value === "warning" || value === "info";
}

export function severityLabel(severity: Severity): string {
  return SEVERITY_LABELS[severity];
}

export function severityTagModifier(severity: Severity): "red" | "orange" | "blue" {
  return SEVERITY_TAG_MODIFIERS[severity];
}

const DATE_TIME_FORMAT = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return DATE_TIME_FORMAT.format(date);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return DATE_FORMAT.format(date);
}

export function formatAge(ageYears: number | null | undefined): string {
  if (ageYears === null || ageYears === undefined) return "Unknown";
  return `${ageYears} years`;
}

export function fullName(item: {
  family_name?: string | null;
  given_names?: string[] | null;
}): string {
  const given = item.given_names?.filter(Boolean).join(" ") ?? "";
  const family = item.family_name?.trim();
  if (given && family) return `${given} ${family}`;
  if (given) return given;
  if (family) return family;
  return "Unknown patient";
}

export function formatNhsNumber(nhsNumber: string | null | undefined): string {
  if (!nhsNumber) return "—";
  const digits = nhsNumber.replace(/\D/g, "");
  if (digits.length !== 10) return nhsNumber;
  return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6, 10)}`;
}

/** Human label for an NHS number verification status. */
export function nhsNumberStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case "verified":
      return "Verified";
    case "unverified":
      return "Unverified";
    case "absent":
      return "Absent";
    default:
      return status ?? "Unknown";
  }
}

export function humanizeAction(action: string): string {
  return action.replace(/[._]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
