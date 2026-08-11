"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";
import type { Severity } from "@/lib/api";
import { severityLabel } from "@/lib/utils";

const SEVERITY_COLORS: Record<Severity, string> = {
  error: "#d5281b",
  warning: "#ed8b00",
  info: "#005eb8",
};

export interface TopRuleDatum {
  rule_id: string;
  title: string;
  count: number;
  severity: Severity;
}

/**
 * Top-N rules bar chart (Recharts). Bars are coloured by severity with an
 * explicit text legend below, so severity is never conveyed by colour alone.
 */
export function TopRulesChart({ data }: { data: TopRuleDatum[] }) {
  if (data.length === 0) {
    return <p className="nhsuk-body">No findings to chart.</p>;
  }

  return (
    <div>
      <div
        role="img"
        aria-label={`Top ${data.length} rules by finding count: ${data
          .map((datum) => `${datum.rule_id} ${datum.count}`)
          .join(", ")}`}
      >
        <ResponsiveContainer width="100%" height={Math.max(240, data.length * 40)}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ left: 8, right: 32, top: 8, bottom: 8 }}
          >
            <CartesianGrid horizontal={false} strokeDasharray="3 3" />
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="rule_id" width={92} tickLine={false} axisLine={false} />
            <Tooltip content={RuleTooltip} />
            <Bar dataKey="count" name="Findings" isAnimationActive={false}>
              {data.map((datum) => (
                <Cell key={datum.rule_id} fill={SEVERITY_COLORS[datum.severity]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="clerkstone-chart-legend" aria-label="Bar colour legend">
        {(["error", "warning", "info"] as Severity[]).map((severity) => (
          <li key={severity}>
            <span
              className="clerkstone-chart-legend__swatch"
              style={{ background: SEVERITY_COLORS[severity] }}
              aria-hidden="true"
            />
            {severityLabel(severity)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function RuleTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload || payload.length === 0) return null;
  const datum = payload[0].payload as unknown as TopRuleDatum;
  return (
    <div className="nhsuk-card" style={{ padding: "0.75rem", maxWidth: "24rem" }}>
      <p className="nhsuk-body-s" style={{ margin: 0 }}>
        <strong>{datum.rule_id}</strong> — {datum.title}
      </p>
      <p className="nhsuk-body-s" style={{ margin: 0 }}>
        {datum.count} finding{datum.count === 1 ? "" : "s"} · {severityLabel(datum.severity)}
      </p>
    </div>
  );
}
