"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { SeverityCounts } from "@/lib/api";
import { severityLabel } from "@/lib/utils";

const SEVERITY_COLORS: Record<string, string> = {
  error: "#d5281b",
  warning: "#ed8b00",
  info: "#005eb8",
};

interface Datum {
  name: string;
  value: number;
  severity: "error" | "warning" | "info";
}

/**
 * Severity donut (Recharts). The chart is decorative; the underlying counts are
 * always available as text via {@link SeverityStatCards}, so colour is never
 * the only encoding of severity.
 */
export function SeverityDonut({ counts }: { counts: SeverityCounts }) {
  const data: Datum[] = (
    [
      { severity: "error", value: counts.error },
      { severity: "warning", value: counts.warning },
      { severity: "info", value: counts.info },
    ] as const
  ).map((d) => ({ ...d, name: severityLabel(d.severity) }));

  const total = counts.error + counts.warning + counts.info;

  if (total === 0) {
    return <p className="nhsuk-body">No findings recorded for this run.</p>;
  }

  return (
    <div
      role="img"
      aria-label={`Severity breakdown: ${counts.error} errors, ${counts.warning} warnings, ${counts.info} informational`}
    >
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            stroke="none"
            isAnimationActive={false}
          >
            {data.map((datum) => (
              <Cell key={datum.severity} fill={SEVERITY_COLORS[datum.severity]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend verticalAlign="bottom" height={36} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
