import { Tag } from "nhsuk-react-components";

type TagModifier = "white" | "grey" | "green" | "aqua-green" | "blue" | "purple" | "pink" | "red" | "orange" | "yellow";

const REVIEW_STATUS: Record<string, { label: string; modifier: TagModifier }> = {
  open: { label: "Open", modifier: "grey" },
  assigned: { label: "Assigned", modifier: "blue" },
  resolved: { label: "Resolved", modifier: "green" },
  accepted_risk: { label: "Accepted risk", modifier: "yellow" },
};

const RUN_STATUS: Record<string, { label: string; modifier: TagModifier }> = {
  running: { label: "Running", modifier: "blue" },
  complete: { label: "Complete", modifier: "green" },
  failed: { label: "Failed", modifier: "red" },
};

const AUDIT_OUTCOME: Record<string, { label: string; modifier: TagModifier }> = {
  success: { label: "Success", modifier: "green" },
  denied: { label: "Denied", modifier: "red" },
  error: { label: "Error", modifier: "red" },
};

function lookup(table: Record<string, { label: string; modifier: TagModifier }>, status: string) {
  return table[status] ?? { label: status || "Unknown", modifier: "grey" as TagModifier };
}

export function ReviewStatusBadge({ status }: { status: string }) {
  const { label, modifier } = lookup(REVIEW_STATUS, status);
  return <Tag modifier={modifier}>{label}</Tag>;
}

export function RunStatusBadge({ status }: { status: string }) {
  const { label, modifier } = lookup(RUN_STATUS, status);
  return <Tag modifier={modifier}>{label}</Tag>;
}

export function AuditOutcomeBadge({ outcome }: { outcome: string }) {
  const { label, modifier } = lookup(AUDIT_OUTCOME, outcome);
  return <Tag modifier={modifier}>{label}</Tag>;
}
