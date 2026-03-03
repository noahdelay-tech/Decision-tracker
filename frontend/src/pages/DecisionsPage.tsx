import { useEffect, useState, useCallback } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { Decision, DecisionCreate } from "@/types/decision";
import { DecisionCard } from "@/components/DecisionCard";
import { DecisionForm } from "@/components/DecisionForm";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type FilterStatus = "all" | "pending" | "in_review" | "decided" | "cancelled";
type FilterPriority = "all" | "low" | "medium" | "high" | "critical";

export function DecisionsPage() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("all");
  const [filterPriority, setFilterPriority] = useState<FilterPriority>("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Decision | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.decisions.list({
        status: filterStatus !== "all" ? filterStatus : undefined,
        priority: filterPriority !== "all" ? filterPriority : undefined,
        page_size: 100,
      });
      setDecisions(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load decisions");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterPriority]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(data: DecisionCreate) {
    await api.decisions.create(data);
    setDialogOpen(false);
    load();
  }

  async function handleUpdate(data: DecisionCreate) {
    if (!editing) return;
    await api.decisions.update(editing.id, data);
    setEditing(null);
    load();
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this decision?")) return;
    await api.decisions.delete(id);
    load();
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Decision Tracker</h1>
            <p className="text-sm text-muted-foreground">{total} decisions total</p>
          </div>
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            New Decision
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-4">
        {/* Filters */}
        <div className="flex flex-wrap gap-2 items-center">
          <Select value={filterStatus} onValueChange={(v) => setFilterStatus(v as FilterStatus)}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="in_review">In Review</SelectItem>
              <SelectItem value="decided">Decided</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filterPriority} onValueChange={(v) => setFilterPriority(v as FilterPriority)}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All priorities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="ghost" size="icon" onClick={load} title="Refresh">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Content */}
        {error && (
          <div className="rounded-md bg-destructive/10 text-destructive p-4 text-sm">{error}</div>
        )}
        {!loading && decisions.length === 0 && !error && (
          <div className="text-center py-16 text-muted-foreground">
            <p className="text-lg font-medium">No decisions yet</p>
            <p className="text-sm mt-1">Click "New Decision" to get started.</p>
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {decisions.map((d) => (
            <DecisionCard
              key={d.id}
              decision={d}
              onEdit={(dec) => setEditing(dec)}
              onDelete={handleDelete}
            />
          ))}
        </div>
      </main>

      {/* Create dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>New Decision</DialogTitle>
          </DialogHeader>
          <DecisionForm
            onSubmit={handleCreate}
            onCancel={() => setDialogOpen(false)}
            submitLabel="Create"
          />
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Decision</DialogTitle>
          </DialogHeader>
          {editing && (
            <DecisionForm
              initial={editing}
              onSubmit={handleUpdate}
              onCancel={() => setEditing(null)}
              submitLabel="Update"
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
