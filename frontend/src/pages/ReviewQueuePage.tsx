import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, LayoutPanelLeft } from "lucide-react";
import { api } from "@/lib/api";
import type { DatasetSummary, Flag } from "@/types/flag";
import { FlagCard } from "@/components/FlagCard";
import { FlagReviewDialog } from "@/components/FlagReviewDialog";
import { FlagStats } from "@/components/FlagStats";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type SeverityFilter = "all" | "high" | "medium" | "low";
type StatusFilter   = "all" | "pending" | "confirmed" | "rejected" | "overridden";

interface ReviewQueuePageProps {
  onPendingCountChange: (n: number) => void;
}

export function ReviewQueuePage({ onPendingCountChange }: ReviewQueuePageProps) {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [flags, setFlags] = useState<Flag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [datasetFilter, setDatasetFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");

  const [reviewFlag, setReviewFlag] = useState<Flag | null>(null);

  const loadFlags = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dsRes, flagRes] = await Promise.all([
        api.datasets.list(),
        api.flags.list({
          dataset_id: datasetFilter !== "all" ? Number(datasetFilter) : undefined,
          severity:   severityFilter !== "all" ? severityFilter : undefined,
          status:     statusFilter   !== "all" ? statusFilter   : undefined,
          page_size:  200,
        }),
      ]);
      setDatasets(dsRes);
      setFlags(flagRes.items);
      const pending = flagRes.items.filter((f) => f.status === "pending").length;
      onPendingCountChange(pending);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load flags.");
    } finally {
      setLoading(false);
    }
  }, [datasetFilter, severityFilter, statusFilter, onPendingCountChange]);

  useEffect(() => { loadFlags(); }, [loadFlags]);

  function handleDecided(flagId: number, newStatus: string) {
    setFlags((prev) =>
      prev.map((f) => (f.id === flagId ? { ...f, status: newStatus as Flag["status"] } : f))
    );
    const pending = flags.filter((f) =>
      f.id === flagId ? newStatus === "pending" : f.status === "pending"
    ).length;
    onPendingCountChange(pending);
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-5">
      {/* Stats */}
      <FlagStats flags={flags} />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Dataset picker */}
        <Select value={datasetFilter} onValueChange={setDatasetFilter}>
          <SelectTrigger className="w-52 h-8 text-xs">
            <SelectValue placeholder="All datasets" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All datasets</SelectItem>
            {datasets.map((d) => (
              <SelectItem key={d.id} value={String(d.id)}>
                {d.filename} ({d.row_count ?? "?"} rows)
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Severity */}
        <Select value={severityFilter} onValueChange={(v) => setSeverityFilter(v as SeverityFilter)}>
          <SelectTrigger className="w-32 h-8 text-xs">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All severities</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>

        {/* Status */}
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <SelectTrigger className="w-36 h-8 text-xs">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="confirmed">Confirmed</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="overridden">Overridden</SelectItem>
          </SelectContent>
        </Select>

        {/* Open full two-panel review for the selected dataset */}
        {datasetFilter !== "all" && (
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() => navigate(`/review/${datasetFilter}`)}
          >
            <LayoutPanelLeft className="h-3.5 w-3.5" />
            Full Review
          </Button>
        )}

        <Button variant="ghost" size="sm" onClick={loadFlags} className="h-8 px-2" title="Refresh">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>

        {!loading && (
          <span className="text-xs text-muted-foreground ml-auto">
            {flags.length} flag{flags.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive p-3 text-sm">{error}</div>
      )}

      {/* Empty state */}
      {!loading && flags.length === 0 && !error && (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg font-medium">
            {statusFilter === "pending" ? "No pending flags 🎉" : "No flags match these filters"}
          </p>
          <p className="text-sm mt-1">
            {statusFilter === "pending"
              ? "All flags in this dataset have been reviewed."
              : "Try adjusting the filters above."}
          </p>
        </div>
      )}

      {/* Flag grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {flags.map((f) => (
          <FlagCard key={f.id} flag={f} onReview={setReviewFlag} />
        ))}
      </div>

      {/* Review dialog */}
      <FlagReviewDialog
        flag={reviewFlag}
        open={reviewFlag !== null}
        onClose={() => setReviewFlag(null)}
        onDecided={handleDecided}
      />
    </div>
  );
}
