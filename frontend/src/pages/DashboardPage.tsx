import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Database, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { StudyCreate, StudySummary } from "@/types/study";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const STUDY_TYPES = ["xenograft", "PK", "toxicology", "other"] as const;

// ── New Study modal ───────────────────────────────────────────────────────────

interface NewStudyModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (study: StudySummary) => void;
}

function NewStudyModal({ open, onClose, onCreated }: NewStudyModalProps) {
  const [form, setForm] = useState<StudyCreate>({
    name: "",
    sponsor_id: "",
    study_type: "toxicology",
    species: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setForm({ name: "", sponsor_id: "", study_type: "toxicology", species: "" });
    setError(null);
    setSaving(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.sponsor_id.trim() || !form.species.trim()) {
      setError("All fields are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await api.studies.create(form);
      reset();
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create study.");
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { reset(); onClose(); } }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New Study</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-1">
          <div className="space-y-1.5">
            <Label htmlFor="name">Study name</Label>
            <Input
              id="name"
              placeholder="e.g. GLP Tox – Compound X"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="sponsor">Sponsor ID</Label>
            <Input
              id="sponsor"
              placeholder="e.g. ACME-PHARMA"
              value={form.sponsor_id}
              onChange={(e) => setForm((f) => ({ ...f, sponsor_id: e.target.value }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="study_type">Study type</Label>
            <Select
              value={form.study_type}
              onValueChange={(v) => setForm((f) => ({ ...f, study_type: v }))}
            >
              <SelectTrigger id="study_type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STUDY_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="species">Species</Label>
            <Input
              id="species"
              placeholder="e.g. Sprague-Dawley rat"
              value={form.species}
              onChange={(e) => setForm((f) => ({ ...f, species: e.target.value }))}
            />
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="ghost"
              onClick={() => { reset(); onClose(); }}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Creating…" : "Create Study"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Study card ────────────────────────────────────────────────────────────────

function StudyCard({ study, onClick }: { study: StudySummary; onClick: () => void }) {
  return (
    <Card
      className="p-4 cursor-pointer hover:shadow-md transition-shadow border hover:border-slate-300"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-slate-900 truncate">{study.name}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {study.sponsor_id} · {study.study_type} · {study.species}
          </p>
        </div>
        <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0 mt-0.5">
          <Database className="h-3.5 w-3.5" />
          {study.dataset_count}
        </span>
      </div>
      <p className="text-[11px] text-muted-foreground mt-3">
        Created {new Date(study.created_at).toLocaleDateString()}
      </p>
    </Card>
  );
}

// ── Dashboard page ────────────────────────────────────────────────────────────

export function DashboardPage() {
  const navigate = useNavigate();
  const [studies, setStudies] = useState<StudySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewStudy, setShowNewStudy] = useState(false);

  async function loadStudies() {
    setLoading(true);
    setError(null);
    try {
      setStudies(await api.studies.list());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load studies.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadStudies(); }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Studies</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Select a study to review its datasets and generate a briefing.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={loadStudies} className="h-8 px-2" title="Refresh">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </Button>
          <Button size="sm" onClick={() => setShowNewStudy(true)} className="gap-1.5">
            <Plus className="h-4 w-4" />
            New Study
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive p-3 text-sm">{error}</div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-lg bg-slate-100 animate-pulse" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && studies.length === 0 && !error && (
        <div className="text-center py-20 text-muted-foreground border border-dashed rounded-xl">
          <Database className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium">No studies yet</p>
          <p className="text-sm mt-1">Click "New Study" to create your first one.</p>
        </div>
      )}

      {/* Study grid */}
      {!loading && studies.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {studies.map((s) => (
            <StudyCard
              key={s.id}
              study={s}
              onClick={() => navigate(`/studies/${s.id}`)}
            />
          ))}
        </div>
      )}

      <NewStudyModal
        open={showNewStudy}
        onClose={() => setShowNewStudy(false)}
        onCreated={(s) => {
          setStudies((prev) => [s, ...prev]);
          setShowNewStudy(false);
          navigate(`/studies/${s.id}`);
        }}
      />
    </div>
  );
}
