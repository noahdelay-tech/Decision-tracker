// ── Pattern Library ───────────────────────────────────────────────────────

export interface Pattern {
  id: number;
  sponsor_id: string;
  study_type: string;
  flag_type: string;
  sample_count: number;
  dominant_action: "confirmed" | "rejected" | "overridden";
  confidence: number;        // 0–1
  action_distribution: Record<string, number> | null;
  common_override_values: string[] | null;
  rule_text: string;
  last_rebuilt_at: string;
}

export interface PatternRebuildResponse {
  patterns_created: number;
  patterns: Pattern[];
  rebuilt_at: string;
}

// ── Study Briefing ────────────────────────────────────────────────────────

export interface Briefing {
  id: number;
  study_id: number;
  briefing_text: string;    // markdown
  model_used: string;       // "anthropic/…" | "openai/…" | "template"
  pattern_count: number;
  generated_at: string;
}

// ── Audit / 21 CFR Part 11 export ────────────────────────────────────────

export interface AuditExportRecord {
  id: number;
  study_id: number;
  export_ref: string;       // UUID4
  exported_by: string;
  exported_at: string;
  record_count: number;
  content_hash: string;     // SHA-256 hex
  export_format: "json" | "csv";
  system_version: string;
  reason: string;
}

export interface ExportRequest {
  exported_by: string;
  reason?: string;
  export_format?: "json" | "csv";
}

export interface ExportPayloadMetadata {
  export_ref: string;
  study_id: number;
  study_name: string;
  sponsor_id: string;
  study_type: string;
  species: string;
  exported_by: string;
  exported_at: string;
  record_count: number;
  system_version: string;
  reason: string;
  content_hash: string;
}

export interface ExportPayloadRecord {
  decision_id: number;
  flag_id: number;
  dataset_id: number;
  dataset_filename: string;
  study_id: number;
  study_name: string;
  sponsor_id: string;
  study_type: string;
  species: string;
  row_index: number;
  column_name: string;
  raw_value: string;
  proposed_value: string | null;
  flag_type: string;
  severity: string;
  biological_reasoning: string;
  flag_status: string;
  reviewer_name: string;
  action: string;
  override_value: string | null;
  notes: string | null;
  decided_at: string;
  flag_created_at: string;
}

export interface ExportPayload {
  export_metadata: ExportPayloadMetadata;
  records: ExportPayloadRecord[];
}

export interface ExportResponse {
  export: AuditExportRecord;
  payload: ExportPayload;
}
