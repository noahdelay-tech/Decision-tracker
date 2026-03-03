/**
 * FlagReviewPage  –  /review/:datasetId
 *
 * Two-panel layout:
 *   Left  – scrollable queue of flag cards for the dataset
 *   Right – full review panel: reasoning callout, context table,
 *           proposed value, action buttons, reviewer field, auto-advance
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  ChevronRight,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ContextTable } from "@/components/ContextTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type {
  DecisionAction,
  Flag,
  FlagProgress,
  FlagWithContext,
} from "@/types/flag";

// ── Visual constants ────────────────────────────────────────────────────────

const SEV = {
  high:   { dot: "bg-red-500",   badge: "bg-red-100 text-red-800",    ring: "ring-red-400",    header: "bg-red-50 border-red-200",    title: "text-red-800"   },
  medium: { dot: "bg-amber-500", badge: "bg-amber-100 text-amber-800", ring: "ring-amber-400",  header: "bg-amber-50 border-amber-200", title: "text-amber-800" },
  low:    { dot: "bg-teal-500",  badge: "bg-teal-100 text-teal-800",   ring: "ring-teal-400",   header: "bg-teal-50 border-teal-200",   title: "text-teal-800"  },
} as const;

const STATUS_PILL: Record<string, string> = {
  pending:    "bg-slate-100 text-slate-600",
  confirmed:  "bg-green-100 text-green-700",
  rejected:   "bg-red-100   text-red-700",
  overridden: "bg-blue-100  text-blue-700",
};

const ACTION_CFG: Record<DecisionAction, { label: string; icon: React.ReactNode; active: string; idle: string }> = {
  confirmed:  { label: "Confirm Fix",    icon: <CheckCircle className="h-4 w-4" />, active: "bg-green-600 text-white border-green-600", idle: "border-green-300 text-green-700 hover:bg-green-50" },
  rejected:   { label: "Reject Flag",   icon: <XCircle     className="h-4 w-4" />, active: "bg-red-600   text-white border-red-600",   idle: "border-red-300   text-red-700   hover:bg-red-50"   },
  overridden: { label: "Override Value", icon: <RefreshCw   className="h-4 w-4" />, active: "bg-blue-600  text-white border-blue-600",  idle: "border-blue-300  text-blue-700  hover:bg-blue-50"  },
};

// ── Left-panel queue card ────────────────────────────────────────────────────

interface QueueCardProps {
  flag: Flag;
  isSelected: boolean;
  onClick: () => void;
}

function QueueCard({ flag, isSelected, onClick }: QueueCardProps) {
  const sev = SEV[flag.severity] ?? SEV.low;
  const ref = useRef<HTMLButtonElement>(null);

  // Scroll into view when newly selected
  useEffect(() => {
    if (isSelected) ref.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [isSelected]);

  return (
    <button
      ref={ref}
      type="button"
      onClick={onClick}
      className={cn(
        "w-full text-left rounded-lg border px-3 py-2.5 transition-all",
        "hover:shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
        isSelected
          ? `border-transparent ring-2 ${sev.ring} bg-white shadow-sm`
          : "border-border bg-white hover:bg-slate-50",
        flag.status !== "pending" && "opacity-60"
      )}
    >
      <div className="flex items-start gap-2">
        {/* Severity dot */}
        <span className={cn("mt-1 h-2 w-2 rounded-full shrink-0", sev.dot)} />

        <div className="min-w-0 flex-1">
          {/* Column + raw value */}
          <p className="text-sm font-semibold text-foreground truncate">
            <span className="font-mono">{flag.column_name}</span>
            <span className="mx-1 text-muted-foreground font-normal">·</span>
            <span className="font-mono text-red-700">{flag.raw_value}</span>
          </p>

          {/* Flag type + row */}
          <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
            {flag.flag_type.replace(/_/g, " ")} · row {flag.row_index}
          </p>

          {/* Badges */}
          <div className="flex gap-1 mt-1.5 flex-wrap">
            <span className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-medium", sev.badge)}>
              {flag.severity}
            </span>
            <span className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-medium", STATUS_PILL[flag.status])}>
              {flag.status}
            </span>
          </div>
        </div>

        {isSelected && <ChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
      </div>
    </button>
  );
}

// ── Progress bar ─────────────────────────────────────────────────────────────

function ProgressBar({ progress }: { progress: FlagProgress | null }) {
  if (!progress) return null;
  const pct = progress.percent_complete;
  return (
    <div className="px-4 py-2 bg-white border-b flex items-center gap-3">
      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground shrink-0 tabular-nums">
        {progress.decided} / {progress.total} reviewed
        {pct > 0 && ` (${pct}%)`}
      </span>
    </div>
  );
}

// ── Right-panel empty / loading state ────────────────────────────────────────

function EmptyPanel({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-3">
      <CheckCircle className="h-10 w-10 opacity-20" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export function FlagReviewPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const dsId = Number(datasetId);

  // Queue state
  const [flags, setFlags] = useState<Flag[]>([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState<string | null>(null);

  // Progress
  const [progress, setProgress] = useState<FlagProgress | null>(null);

  // Right-panel state
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<FlagWithContext | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Form state
  const [reviewer, setReviewer] = useState(() => localStorage.getItem("reviewer_name") ?? "");
  const [action, setAction] = useState<DecisionAction>("confirmed");
  const [overrideValue, setOverrideValue] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // ── Load queue + progress ──────────────────────────────────────────────────

  const loadQueue = useCallback(async () => {
    if (!dsId) return;
    setQueueLoading(true);
    setQueueError(null);
    try {
      const [flagRes, prog] = await Promise.all([
        api.flags.list({ dataset_id: dsId, page_size: 200 }),
        api.flags.progress(dsId),
      ]);
      // Sort: pending first, then severity high→medium→low
      const SEV_ORDER: Record<string, number> = { high: 1, medium: 2, low: 3 };
      const sorted = [...flagRes.items].sort((a, b) => {
        if (a.status === "pending" && b.status !== "pending") return -1;
        if (a.status !== "pending" && b.status === "pending") return 1;
        return (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9);
      });
      setFlags(sorted);
      setProgress(prog);
      // Auto-select first pending flag
      const firstPending = sorted.find((f) => f.status === "pending");
      if (firstPending && selectedId === null) setSelectedId(firstPending.id);
    } catch (e) {
      setQueueError(e instanceof Error ? e.message : "Failed to load flags.");
    } finally {
      setQueueLoading(false);
    }
  }, [dsId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { loadQueue(); }, [loadQueue]);

  // ── Load detail when selection changes ────────────────────────────────────

  useEffect(() => {
    if (selectedId === null) { setDetail(null); return; }
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    setSubmitError(null);

    api.flags.getWithContext(selectedId)
      .then((d) => {
        setDetail(d);
        // Pre-select action: override if proposed value exists
        if (d.flag.proposed_value) {
          setAction("overridden");
          setOverrideValue(d.flag.proposed_value);
        } else {
          setAction("confirmed");
          setOverrideValue("");
        }
        setNotes("");
      })
      .catch((e) => setDetailError(e instanceof Error ? e.message : "Failed to load flag."))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  // ── Auto-advance to next pending flag ─────────────────────────────────────

  const advanceToNext = useCallback((afterId: number) => {
    const currentIdx = flags.findIndex((f) => f.id === afterId);
    // Look for the next pending flag after current position, wrapping around
    const rest = [
      ...flags.slice(currentIdx + 1),
      ...flags.slice(0, currentIdx),
    ];
    const next = rest.find((f) => f.status === "pending");
    setSelectedId(next?.id ?? null);
  }, [flags]);

  // ── Submit decision ────────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedId || !detail) return;

    const name = reviewer.trim();
    if (!name) { setSubmitError("Reviewer name is required."); return; }
    if (action === "overridden" && !overrideValue.trim()) {
      setSubmitError("Override value is required.");
      return;
    }

    localStorage.setItem("reviewer_name", name);
    setSubmitting(true);
    setSubmitError(null);

    try {
      await api.flags.decide(selectedId, {
        reviewer_name: name,
        action,
        override_value: action === "overridden" ? overrideValue.trim() : undefined,
        notes: notes.trim() || undefined,
      });

      // Update local flag status immediately
      setFlags((prev) =>
        prev.map((f) =>
          f.id === selectedId ? { ...f, status: action as Flag["status"] } : f
        )
      );

      // Refresh progress counter
      api.flags.progress(dsId).then(setProgress).catch(() => null);

      // Advance to next pending flag
      advanceToNext(selectedId);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  // ── Keyboard navigation ────────────────────────────────────────────────────

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (!flags.length) return;

      const idx = flags.findIndex((f) => f.id === selectedId);
      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        setSelectedId(flags[Math.min(idx + 1, flags.length - 1)].id);
      } else if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        setSelectedId(flags[Math.max(idx - 1, 0)].id);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flags, selectedId]);

  // ── Derived values for right panel ────────────────────────────────────────

  const f = detail?.flag ?? flags.find((x) => x.id === selectedId) ?? null;
  const sevCfg = f ? (SEV[f.severity] ?? SEV.low) : null;
  const pendingCount = flags.filter((x) => x.status === "pending").length;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 56px)" }}>
      {/* ── Progress bar ──────────────────────────────────────────────────── */}
      <ProgressBar progress={progress} />

      <div className="flex flex-1 overflow-hidden">
        {/* ── LEFT: Flag queue ──────────────────────────────────────────── */}
        <aside className="w-72 shrink-0 flex flex-col border-r bg-slate-50">
          {/* Queue header */}
          <div className="px-3 py-2.5 border-b bg-white flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => navigate("/queue")}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back
            </button>
            <span className="text-xs font-medium text-foreground truncate">
              {pendingCount} pending
            </span>
          </div>

          {/* Queue body */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {queueLoading && (
              <div className="flex items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            )}
            {queueError && (
              <p className="text-xs text-destructive p-2">{queueError}</p>
            )}
            {!queueLoading && flags.map((flag) => (
              <QueueCard
                key={flag.id}
                flag={flag}
                isSelected={flag.id === selectedId}
                onClick={() => setSelectedId(flag.id)}
              />
            ))}
            {!queueLoading && flags.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-8">
                No flags in this dataset.
              </p>
            )}
          </div>

          {/* Keyboard hint */}
          <div className="px-3 py-2 border-t bg-white">
            <p className="text-[10px] text-muted-foreground text-center">
              ↑ ↓ or J / K to navigate
            </p>
          </div>
        </aside>

        {/* ── RIGHT: Review panel ───────────────────────────────────────── */}
        <main className="flex-1 flex flex-col overflow-hidden bg-background">
          {!selectedId && !queueLoading && (
            <EmptyPanel message={flags.length === 0 ? "No flags to review." : "Select a flag from the queue."} />
          )}

          {detailLoading && (
            <div className="flex items-center justify-center flex-1 text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">Loading flag…</span>
            </div>
          )}

          {detailError && (
            <div className="p-6">
              <div className="rounded-md bg-destructive/10 text-destructive p-3 text-sm">{detailError}</div>
            </div>
          )}

          {!detailLoading && !detailError && f && sevCfg && (
            <div className="flex flex-col flex-1 overflow-y-auto">
              {/* ── Severity header band ──────────────────────────────────── */}
              <div className={cn("px-6 py-4 border-b shrink-0", sevCfg.header)}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className={cn("text-base font-semibold font-mono", sevCfg.title)}>
                      {f.column_name}
                    </h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Row {f.row_index} · {f.flag_type.replace(/_/g, " ")}
                      {f.status !== "pending" && (
                        <span className={cn("ml-2 rounded-full px-2 py-0.5 text-[10px] font-medium", STATUS_PILL[f.status])}>
                          {f.status}
                        </span>
                      )}
                    </p>
                  </div>
                  <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold shrink-0", sevCfg.badge)}>
                    {f.severity} severity
                  </span>
                </div>
              </div>

              {/* ── Panel body ────────────────────────────────────────────── */}
              <div className="flex-1 px-6 py-5 space-y-6">

                {/* Raw → Proposed value */}
                <div className="flex flex-wrap items-center gap-3 rounded-lg bg-muted/40 px-4 py-3 border">
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-semibold mb-0.5">Raw value</p>
                    <p className="font-mono font-bold text-red-700 text-lg leading-none">{f.raw_value}</p>
                  </div>
                  {f.proposed_value && (
                    <>
                      <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div>
                        <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-semibold mb-0.5">Proposed fix</p>
                        <p className="font-mono font-bold text-green-700 text-lg leading-none">{f.proposed_value}</p>
                      </div>
                    </>
                  )}
                </div>

                {/* Biological reasoning callout */}
                <div className="rounded-lg border-l-4 border-amber-400 bg-amber-50 px-4 py-3">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                      Biological reasoning
                    </p>
                  </div>
                  <p className="text-sm text-amber-900 leading-relaxed">{f.biological_reasoning}</p>
                </div>

                {/* Context table */}
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                    Surrounding context <span className="font-normal normal-case">(±3 rows)</span>
                  </p>
                  <ContextTable
                    rows={detail?.context_rows ?? []}
                    flaggedColumn={f.column_name}
                  />
                </div>

                {/* Existing decision banner */}
                {detail?.existing_decision && (
                  <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                    <strong>Previous decision:</strong>{" "}
                    {detail.existing_decision.action} by {detail.existing_decision.reviewer_name}
                    {detail.existing_decision.override_value && (
                      <span> → <span className="font-mono">"{detail.existing_decision.override_value}"</span></span>
                    )}
                    {detail.existing_decision.notes && (
                      <span className="block mt-0.5 italic text-blue-600">
                        "{detail.existing_decision.notes}"
                      </span>
                    )}
                  </div>
                )}

                {/* ── Decision form ───────────────────────────────────────── */}
                <form onSubmit={handleSubmit} className="space-y-4 border-t pt-5 pb-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Your decision
                  </p>

                  {/* Action buttons */}
                  <div className="flex flex-wrap gap-2">
                    {(["confirmed", "rejected", "overridden"] as DecisionAction[]).map((a) => {
                      const cfg = ACTION_CFG[a];
                      return (
                        <button
                          key={a}
                          type="button"
                          onClick={() => setAction(a)}
                          className={cn(
                            "flex items-center gap-2 rounded-lg border-2 px-4 py-2.5 text-sm font-medium transition-all",
                            action === a ? cfg.active : `bg-white ${cfg.idle}`
                          )}
                        >
                          {cfg.icon}
                          {cfg.label}
                        </button>
                      );
                    })}
                  </div>

                  {/* Override value – only shown when Override is selected */}
                  {action === "overridden" && (
                    <div className="space-y-1">
                      <Label htmlFor="override-val">Corrected value <span className="text-destructive">*</span></Label>
                      <Input
                        id="override-val"
                        value={overrideValue}
                        onChange={(e) => setOverrideValue(e.target.value)}
                        placeholder="Enter the correct value"
                        className="font-mono max-w-xs"
                        required
                      />
                    </div>
                  )}

                  {/* Reviewer name */}
                  <div className="space-y-1">
                    <Label htmlFor="reviewer-name">Reviewer name <span className="text-destructive">*</span></Label>
                    <Input
                      id="reviewer-name"
                      value={reviewer}
                      onChange={(e) => setReviewer(e.target.value)}
                      placeholder="Dr. Jane Smith"
                      className="max-w-xs"
                      required
                    />
                  </div>

                  {/* Notes */}
                  <div className="space-y-1">
                    <Label htmlFor="review-notes">
                      Notes{" "}
                      <span className="text-muted-foreground font-normal">(optional)</span>
                    </Label>
                    <Textarea
                      id="review-notes"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Add justification or additional context…"
                      rows={2}
                      className="max-w-lg resize-none"
                    />
                  </div>

                  {submitError && (
                    <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
                      {submitError}
                    </p>
                  )}

                  <div className="flex items-center gap-3 pt-1">
                    <Button
                      type="submit"
                      disabled={submitting}
                      className={cn(
                        "min-w-32",
                        action === "confirmed"  && "bg-green-600 hover:bg-green-700",
                        action === "rejected"   && "bg-red-600   hover:bg-red-700",
                        action === "overridden" && "bg-blue-600  hover:bg-blue-700"
                      )}
                    >
                      {submitting
                        ? <><Loader2 className="h-4 w-4 animate-spin mr-2" />Saving…</>
                        : <>Submit · {ACTION_CFG[action].label}</>
                      }
                    </Button>
                    {pendingCount > 1 && (
                      <span className="text-xs text-muted-foreground">
                        {pendingCount - 1} more pending after this
                      </span>
                    )}
                  </div>
                </form>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
