import { Tag } from "nhsuk-react-components";
import type { Severity } from "@/lib/api";
import { severityLabel, severityTagModifier } from "@/lib/utils";

/**
 * Severity indicator that is never colour-only: it always renders an icon,
 * a text label ("Error" / "Warning" / "Info") and a colour. The icon is
 * decorative (aria-hidden) because the text carries the meaning.
 */
export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  return (
    <Tag modifier={severityTagModifier(severity)} className={className}>
      <span className="clerkstone-severity">
        <span className="clerkstone-severity__icon" aria-hidden="true">
          <SeverityIcon severity={severity} />
        </span>
        {severityLabel(severity)}
      </span>
    </Tag>
  );
}

function SeverityIcon({ severity }: { severity: Severity }) {
  if (severity === "info") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" focusable="false" aria-hidden="true">
        <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
      </svg>
    );
  }
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" focusable="false" aria-hidden="true">
      <path d="M12 2 1 21h22L12 2zm1 14h-2v2h2v-2zm0-7h-2v5h2V9z" />
    </svg>
  );
}
