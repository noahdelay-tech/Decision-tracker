import { useEffect, useState } from "react";
import { CheckCircle, XCircle, RefreshCw, Loader2, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { DecisionAction, Flag, FlagWithContext, ReviewDecision } from "@/types/flag";
import { ContextTable } from "@/components/ContextTable";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// ── Visual helpers ────────────────────────────────────────────────────────

const SEVERITY_HEADER: Record<string, string> = {
  high:   "border-red-300 bg-red-50",
  medium: "border-amber-300 bg-amber-50",
  low:    "border-teal-300 bg-teal-50",
};

const SEVERITY_TEXT: Record<string, string> = {
  high:   "text-red-700",
  medium: "text-amber-700",
  low:    "text-teal-700",
};

interface ActionBtnProps {
  action: DecisionAction;
  selected: boolean;
  onClick: () => void;
}
function ActionBtn({ action, selected, onClick }: ActionBtnProps) {
  const cfg: Record<DecisionAction, { label: string; icon: React.ReactNode; active: string; hover: string }> = {
    confirmed: {
      label: "Confirm",
      icon: <CheckCircle className="h-4 w-4" />,
      active: "bg-green-600 text-white border-green-600 shadow-sm",
      hover:  "border-green-300 text-green-700 hover:bg-green-50",
    },
    rejected: {
      label: "Reject",
      icon: <XCircle className="h-4 w-4" />,
      active: "bg-red-600 text-white border-red-600 shadow-sm",
      hover:  "border-red-300 text-red-700 hover:bg-red-50",
    },
    overridden: {
      label: "Override",
      icon: <RefreshCw className="h-4 w-4" />,
      active: "bg-blue-600 text-white border-blue-600 shadow-sm",
      hover:  "border-blue-300 text-blue-700 hover:bg-blue-50",
    },
  };
  const c = cfg[action];
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-lg border-2 px-4 py-2.5 text-sm font-medium transition-all",
        selected ? c.active : `bg-white ${c.hover}`
      )}
    >
      {c.icon}
      {c.label}
    </button>
  );
}

// ── Main dialog ───────────────────────────────────────────────────────────

interface FlagReviewDialogProps {
  flag: Flag | null;
  open: boolean;
  onClose: () => void;
  onDecided: (flagId: number, newStatus: string) => void;
}

export function FlagReviewDialog({ flag, open, onClose, onDecided }: FlagReviewDialogProps) {
  const [detail, setDetail] = useState<FlagWithContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [reviewer, setReviewer] = useState(() => localStorage.getItem("reviewer_name") ?? "");
  const [action, setAction] = useState<DecisionAction>("confirmed");
  const [overrideValue, setOverrideValue] = useState("");
  const [notes, setNotes] = useState("");

  // Load flag detail whenever a new flag is opened
  useEffect(() => {
    if (!flag || !open) return;
    setDetail(null);
    setError(null);
    setLoading(true);

    api.flags.getWithContext(flag.id).then((d) => {
      setDetail(d);
      // Pre-select suggested action: Override if a proposed value exists, else Confirm
      if (d.flag.proposed_value) {
        setAction("overridden");
        setOverrideValue(d.flag.proposed_value);
      } else {
        setAction("confirmed");
        setOverrideValue("");
      }
      setNotes("");
    }).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [flag?.id, open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!flag) return;

    const name = reviewer.trim();
    if (!name) { setError("Reviewer name is required."); return; }
    if (action === "overridden" && !overrideValue.trim()) {
      setError("Override value is required when action is Override.");
      return;
    }

    localStorage.setItem("reviewer_name", name);
    setSubmitting(true);
    setError(null);

    try {
      const resp = await api.flags.decide(flag.id, {
        reviewer_name: name,
        action,
        override_value: action === "overridden" ? overrideValue.trim() : undefined,
        notes: notes.trim() || undefined,
      });
      onDecided(flag.id, resp.flag.status);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const f = detail?.flag ?? flag;
  const existing: ReviewDecision | null = detail?.existing_decision ?? null;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto p-0">
        {/* Severity-coloured header */}
        <div
          className={cn(
            "px-6 pt-5 pb-4 border-b rounded-t-lg",
            f ? SEVERITY_HEADER[f.severity] : "border-border bg-background"
          )}
        >
          <DialogHeader>
            <DialogTitle className={cn("text-base", f ? SEVERITY_TEXT[f.severity] : "")}>
              {f ? (
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-lg">{f.column_name}</span>
                  <span className="text-sm font-normal opacity-70">· Row {f.row_index} · {f.flag_type.replace(/_/g, " ")}</span>
                </span>
              ) : "Flag Review"}
            </DialogTitle>
          </DialogHeader>
        </div>

        <div className="px-6 py-5 space-y-6">
          {loading && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm py-8 justify-center">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading flag details…
            </div>
          )}

          {!loading && f && (
            <>
              {/* Value summary */}
              <div className="flex flex-wrap items-center gap-3 rounded-lg bg-muted/40 px-4 py-3">
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground font-medium">Raw value</p>
                  <p className="font-mono font-bold text-red-700 text-base">{f.raw_value}</p>
                </div>
                {f.proposed_value && (
                  <>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-muted-foreground font-medium">Proposed</p>
                      <p className="font-mono font-bold text-green-700 text-base">{f.proposed_value}</p>
                    </div>
                  </>
                )}
              </div>

              {/* Biological reasoning */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Biological reasoning
                </p>
                <p className="text-sm leading-relaxed text-foreground bg-slate-50 rounded-md p-3 border">
                  {f.biological_reasoning}
                </p>
              </div>

              {/* Context table */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Surrounding context (±3 rows)
                </p>
                <ContextTable rows={detail?.context_rows ?? []} flaggedColumn={f.column_name} />
              </div>

              {/* Existing decision banner */}
              {existing && (
                <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                  <strong>Previous decision:</strong> {existing.action} by {existing.reviewer_name}
                  {existing.override_value && ` → "${existing.override_value}"`}
                  {existing.notes && <span className="block mt-0.5 text-blue-600 italic">"{existing.notes}"</span>}
                </div>
              )}

              {/* Decision form */}
              <form onSubmit={handleSubmit} className="space-y-4 border-t pt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Your decision
                </p>

                {/* Action buttons */}
                <div className="flex flex-wrap gap-2">
                  {(["confirmed", "rejected", "overridden"] as DecisionAction[]).map((a) => (
                    <ActionBtn key={a} action={a} selected={action === a} onClick={() => setAction(a)} />
                  ))}
                </div>

                {/* Override value (only when Override is selected) */}
                {action === "overridden" && (
                  <div className="space-y-1">
                    <Label htmlFor="override">Corrected value *</Label>
                    <Input
                      id="override"
                      value={overrideValue}
                      onChange={(e) => setOverrideValue(e.target.value)}
                      placeholder="Enter the correct value"
                      className="font-mono"
                      required
                    />
                  </div>
                )}

                {/* Reviewer name */}
                <div className="space-y-1">
                  <Label htmlFor="reviewer">Reviewer name *</Label>
                  <Input
                    id="reviewer"
                    value={reviewer}
                    onChange={(e) => setReviewer(e.target.value)}
                    placeholder="Dr. Jane Smith"
                    required
                  />
                </div>

                {/* Notes */}
                <div className="space-y-1">
                  <Label htmlFor="notes">Notes <span className="text-muted-foreground font-normal">(optional)</span></Label>
                  <Textarea
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add any additional context or justification…"
                    rows={2}
                  />
                </div>

                {error && (
                  <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">{error}</p>
                )}

                <div className="flex justify-end gap-2 pt-1">
                  <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={submitting}
                    className={cn(
                      action === "confirmed"  && "bg-green-600 hover:bg-green-700",
                      action === "rejected"   && "bg-red-600   hover:bg-red-700",
                      action === "overridden" && "bg-blue-600  hover:bg-blue-700"
                    )}
                  >
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    {submitting ? "Saving…" : `Submit — ${action}`}
                  </Button>
                </div>
              </form>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
