import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Download } from "lucide-react";
import { api } from "@/lib/api";
import type { DatasetSummary, DecisionLogEntry } from "@/types/flag";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

// ── Visual helpers ────────────────────────────────────────────────────────

const ACTION_STYLES: Record<string, string> = {
  confirmed:  "bg-green-100 text-green-800",
  rejected:   "bg-red-100 text-red-800",
  overridden: "bg-blue-100 text-blue-800",
};

const SEVERITY_DOT: Record<string, string> = {
  high:   "bg-red-500",
  medium: "bg-amber-500",
  low:    "bg-teal-500",
};

function fmt(iso: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

// ── CSV export ────────────────────────────────────────────────────────────

function exportCSV(entries: DecisionLogEntry[]) {
  const cols: (keyof DecisionLogEntry)[] = [
    "decided_at", "flag_id", "dataset_id", "column_name", "raw_value",
    "proposed_value", "override_value", "flag_type", "severity",
    "action", "reviewer_name", "notes",
  ];
  const header = cols.join(",");
  const rows = entries.map((e) =>
    cols.map((c) => {
      const v = e[c] ?? "";
      return `"${String(v).replace(/"/g, '""')}"`;
    }).join(",")
  );
  const blob = new Blob([header + "\n" + rows.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `decision_log_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Page ──────────────────────────────────────────────────────────────────

export function DecisionLogPage() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [entries, setEntries] = useState<DecisionLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [datasetFilter, setDatasetFilter] = useState<string>("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dsRes, logRes] = await Promise.all([
        api.datasets.list(),
        api.flags.decisionLog({
          dataset_id: datasetFilter !== "all" ? Number(datasetFilter) : undefined,
          page_size: 500,
        }),
      ]);
      setDatasets(dsRes);
      setEntries(logRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load decision log.");
    } finally {
      setLoading(false);
    }
  }, [datasetFilter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mr-2">
          Audit log
        </h2>

        <Select value={datasetFilter} onValueChange={setDatasetFilter}>
          <SelectTrigger className="w-52 h-8 text-xs">
            <SelectValue placeholder="All datasets" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All datasets</SelectItem>
            {datasets.map((d) => (
              <SelectItem key={d.id} value={String(d.id)}>
                {d.filename}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button variant="ghost" size="sm" onClick={load} className="h-8 px-2">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>

        <Button
          variant="outline"
          size="sm"
          className="h-8 ml-auto gap-1.5 text-xs"
          onClick={() => exportCSV(entries)}
          disabled={entries.length === 0}
        >
          <Download className="h-3 w-3" />
          Export CSV
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive p-3 text-sm">{error}</div>
      )}

      {/* Table */}
      {!loading && entries.length === 0 && !error && (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg font-medium">No decisions recorded yet</p>
          <p className="text-sm mt-1">Review flags in the queue to populate this log.</p>
        </div>
      )}

      {entries.length > 0 && (
        <div className="rounded-lg border overflow-hidden">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="bg-muted/50">
              <tr>
                {["Decided at", "Column", "Raw → Final", "Type", "Sev.", "Action", "Reviewer", "Notes"].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-background">
              {entries.map((e) => (
                <tr key={e.id} className="hover:bg-muted/20 transition-colors">
                  {/* Decided at */}
                  <td className="px-3 py-2.5 whitespace-nowrap text-muted-foreground text-xs tabular-nums">
                    {fmt(e.decided_at)}
                  </td>

                  {/* Column */}
                  <td className="px-3 py-2.5 font-medium whitespace-nowrap">{e.column_name}</td>

                  {/* Raw → final */}
                  <td className="px-3 py-2.5 font-mono text-xs whitespace-nowrap">
                    <span className="text-red-700">{e.raw_value}</span>
                    {(e.override_value ?? e.proposed_value) && (
                      <>
                        <span className="mx-1 text-muted-foreground">→</span>
                        <span className="text-green-700">{e.override_value ?? e.proposed_value}</span>
                      </>
                    )}
                  </td>

                  {/* Flag type */}
                  <td className="px-3 py-2.5 text-muted-foreground text-xs whitespace-nowrap">
                    {e.flag_type.replace(/_/g, " ")}
                  </td>

                  {/* Severity */}
                  <td className="px-3 py-2.5">
                    <span className="flex items-center gap-1.5">
                      <span className={cn("h-2 w-2 rounded-full", SEVERITY_DOT[e.severity])} />
                      <span className="text-xs capitalize">{e.severity}</span>
                    </span>
                  </td>

                  {/* Action */}
                  <td className="px-3 py-2.5">
                    <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium", ACTION_STYLES[e.action])}>
                      {e.action}
                    </span>
                  </td>

                  {/* Reviewer */}
                  <td className="px-3 py-2.5 whitespace-nowrap text-xs">{e.reviewer_name}</td>

                  {/* Notes */}
                  <td className="px-3 py-2.5 max-w-xs">
                    {e.notes ? (
                      <span className="text-xs text-muted-foreground line-clamp-1">{e.notes}</span>
                    ) : (
                      <span className="text-muted-foreground/40 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-3 py-2 bg-muted/30 border-t text-xs text-muted-foreground">
            {entries.length} decision{entries.length !== 1 ? "s" : ""} total
          </div>
        </div>
      )}
    </div>
  );
}
