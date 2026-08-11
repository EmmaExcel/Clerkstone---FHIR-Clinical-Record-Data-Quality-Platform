import type { Severity, SeverityCounts } from "@/lib/api";
import { severityLabel } from "@/lib/utils";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

const ORDER: Severity[] = ["error", "warning", "info"];

/**
 * Accessible severity summary: a value, a text label and a colour for each
 * tier — never colour-only.
 */
export function SeverityStatCards({ counts }: { counts: SeverityCounts }) {
  return (
    <div className="clerkstone-stat-grid">
      {ORDER.map((severity) => (
        <div key={severity} className={`clerkstone-stat clerkstone-stat--${severity}`}>
          <SeverityBadge severity={severity} />
          <p className="clerkstone-stat__value">{counts[severity]}</p>
          <p className="nhsuk-body-s">{severityLabel(severity)} finding{counts[severity] === 1 ? "" : "s"}</p>
        </div>
      ))}
    </div>
  );
}
