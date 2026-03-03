import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Upload,
  RefreshCw,
  Sparkles,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
} from "lucide-react";
import { api } from "@/lib/api";
import type { DatasetInStudy, StudyDetail } from "@/types/study";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusIcon(status: string) {
  if (status === "complete") return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />;
  if (status === "error") return <AlertTriangle className="h-3.5 w-3.5 text-red-500" />;
  return <Clock className="h-3.5 w-3.5 text-amber-500" />;
}

function statusLabel(status: string) {
  if (status === "complete") return "complete";
  if (status === "error") return "error";
  return "processing";
}

// ── Dataset row ───────────────────────────────────────────────────────────────

function DatasetRow({
  dataset,
  onReview,
}: {
  dataset: DatasetInStudy;
  onReview: (id: number) => void;
}) {
  const allResolved =
    dataset.flag_count > 0 && dataset.pending_count === 0;

  function downloadAudit() {
    window.open(`/api/v1/datasets/${dataset.id}/export/audit`, "_blank");
  }

  return (
    <div className="flex items-center justify-between py-3 px-4 rounded-lg border bg-white hover:bg-slate-50 transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        {statusIcon(dataset.upload_status)}
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-800 truncate">{dataset.filename}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {dataset.row_count != null ? `${dataset.row_count} rows` : "—"} ·{" "}
            {new Date(dataset.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0 ml-3">
        <div className="text-right hidden sm:block">
          <p className="text-xs text-muted-foreground">
            {dataset.flag_count} flag{dataset.flag_count !== 1 ? "s" : ""}
          </p>
          {dataset.pending_count > 0 && (
            <p className="text-xs font-medium text-amber-600">
              {dataset.pending_count} pending
            </p>
          )}
        </div>
        <Badge variant="outline" className="text-[10px] capitalize">
          {statusLabel(dataset.upload_status)}
        </Badge>
        {allResolved && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs gap-1 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
            onClick={downloadAudit}
            title="Download audit trail CSV"
          >
            <Download className="h-3 w-3" />
            Audit Trail
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          className="h-7 text-xs gap-1"
          onClick={() => onReview(dataset.id)}
          title="Open review queue"
        >
          Review
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

// ── Upload dropzone ───────────────────────────────────────────────────────────

interface UploadZoneProps {
  studyId: number;
  onUploaded: () => void;
}

function UploadZone({ studyId, onUploaded }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function processFile(file: File) {
    setUploading(true);
    setUploadError(null);
    setUploadMsg(null);
    try {
      const result = await api.ingest.upload(file, studyId);
      setUploadMsg(`Uploaded ${result.filename} (${result.row_count} rows). Running detection…`);
      // Auto-trigger detect
      await api.datasets.detect(result.dataset_id);
      setUploadMsg(`Done — ${result.filename} processed.`);
      onUploaded();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    processFile(files[0]);
  }

  return (
    <div
      className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
        dragging
          ? "border-blue-400 bg-blue-50"
          : "border-slate-200 bg-slate-50 hover:border-slate-300"
      }`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !uploading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <Upload
        className={`h-8 w-8 mx-auto mb-2 ${uploading ? "animate-bounce text-blue-400" : "text-slate-400"}`}
      />
      {uploading ? (
        <p className="text-sm text-blue-600 font-medium">Uploading…</p>
      ) : (
        <>
          <p className="text-sm font-medium text-slate-700">
            Drop a CSV or XLSX file here
          </p>
          <p className="text-xs text-muted-foreground mt-1">or click to browse</p>
        </>
      )}
      {uploadMsg && (
        <p className="text-xs text-emerald-600 mt-2 font-medium">{uploadMsg}</p>
      )}
      {uploadError && (
        <p className="text-xs text-destructive mt-2">{uploadError}</p>
      )}
    </div>
  );
}

// ── Briefing panel ────────────────────────────────────────────────────────────

function BriefingPanel({ studyId }: { studyId: number }) {
  const [text, setText] = useState<string | null>(null);
  const [patternCount, setPatternCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate(force = false) {
    setLoading(true);
    setError(null);
    try {
      const result = await api.studies.generateBriefing(studyId, force);
      setText(result.briefing_text);
      setPatternCount(result.pattern_count);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate briefing.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Study Briefing</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            AI-generated onboarding summary for new data managers.
          </p>
        </div>
        <div className="flex gap-2">
          {text && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={() => generate(true)}
              disabled={loading}
              title="Regenerate briefing"
            >
              <RefreshCw className={`h-3 w-3 mr-1 ${loading ? "animate-spin" : ""}`} />
              Regenerate
            </Button>
          )}
          <Button
            size="sm"
            className="h-7 text-xs gap-1.5"
            onClick={() => generate(false)}
            disabled={loading}
          >
            <Sparkles className="h-3.5 w-3.5" />
            {loading ? "Generating…" : text ? "Cached" : "Generate Briefing"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive p-3 text-sm">{error}</div>
      )}

      {text ? (
        <div className="rounded-lg border bg-white">
          {patternCount != null && (
            <div className="px-4 py-2 border-b bg-slate-50 rounded-t-lg">
              <span className="text-xs text-muted-foreground">
                Generated from{" "}
                <span className="font-medium text-slate-700">{patternCount}</span>{" "}
                historical pattern{patternCount !== 1 ? "s" : ""}
              </span>
            </div>
          )}
          <pre className="p-4 text-sm text-slate-800 whitespace-pre-wrap font-mono leading-relaxed overflow-auto max-h-[520px]">
            {text}
          </pre>
        </div>
      ) : (
        !loading && (
          <div className="rounded-lg border border-dashed bg-slate-50 p-8 text-center text-muted-foreground">
            <Sparkles className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm font-medium">No briefing generated yet</p>
            <p className="text-xs mt-1">
              Click "Generate Briefing" to create an AI-powered study summary.
            </p>
          </div>
        )
      )}
    </div>
  );
}

// ── Study detail page ─────────────────────────────────────────────────────────

export function StudyDetailPage() {
  const { studyId } = useParams<{ studyId: string }>();
  const navigate = useNavigate();
  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!studyId) return;
    setLoading(true);
    setError(null);
    try {
      setStudy(await api.studies.get(Number(studyId)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load study.");
    } finally {
      setLoading(false);
    }
  }, [studyId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-lg bg-slate-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || !study) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="rounded-md bg-destructive/10 text-destructive p-4 text-sm">
          {error ?? "Study not found."}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <button
          className="hover:text-slate-700 transition-colors"
          onClick={() => navigate("/")}
        >
          Dashboard
        </button>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700 font-medium">{study.name}</span>
      </nav>

      {/* Study metadata */}
      <Card className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">{study.name}</h1>
            <div className="flex flex-wrap gap-3 mt-2 text-xs text-muted-foreground">
              <span>
                <span className="font-medium text-slate-600">Sponsor</span>{" "}
                {study.sponsor_id}
              </span>
              <span>·</span>
              <span>
                <span className="font-medium text-slate-600">Type</span>{" "}
                {study.study_type}
              </span>
              <span>·</span>
              <span>
                <span className="font-medium text-slate-600">Species</span>{" "}
                {study.species}
              </span>
              <span>·</span>
              <span>
                Created {new Date(study.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 shrink-0"
            onClick={load}
            title="Refresh"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </Card>

      {/* Datasets */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-800">
          Datasets{" "}
          <span className="text-muted-foreground font-normal">
            ({study.datasets.length})
          </span>
        </h2>

        {study.datasets.length === 0 ? (
          <p className="text-sm text-muted-foreground py-2">
            No datasets uploaded yet. Use the dropzone below to add one.
          </p>
        ) : (
          <div className="space-y-2">
            {study.datasets.map((d) => (
              <DatasetRow
                key={d.id}
                dataset={d}
                onReview={(id) => navigate(`/review/${id}`)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Upload */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-800">Upload Dataset</h2>
        <UploadZone studyId={study.id} onUploaded={load} />
      </div>

      {/* Briefing panel */}
      <Card className="p-4">
        <BriefingPanel studyId={study.id} />
      </Card>
    </div>
  );
}
