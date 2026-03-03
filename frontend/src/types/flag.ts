export type FlagSeverity = "low" | "medium" | "high";
export type FlagStatus = "pending" | "confirmed" | "rejected" | "overridden";
export type DecisionAction = "confirmed" | "rejected" | "overridden";

export interface Flag {
  id: number;
  dataset_id: number;
  row_index: number;
  column_name: string;
  raw_value: string;
  proposed_value: string | null;
  flag_type: string;
  severity: FlagSeverity;
  biological_reasoning: string;
  status: FlagStatus;
  created_at: string;
}

export interface ContextRow {
  row_index: number;
  data: Record<string, unknown>;
  is_flagged: boolean;
}

export interface ReviewDecision {
  id: number;
  flag_id: number;
  reviewer_name: string;
  action: DecisionAction;
  override_value: string | null;
  notes: string | null;
  decided_at: string;
}

export interface FlagWithContext {
  flag: Flag;
  context_rows: ContextRow[];
  existing_decision: ReviewDecision | null;
}

export interface FlagListResponse {
  items: Flag[];
  total: number;
  page: number;
  page_size: number;
}

export interface DecisionSubmit {
  reviewer_name: string;
  action: DecisionAction;
  override_value?: string;
  notes?: string;
}

export interface DecisionLogEntry {
  id: number;
  flag_id: number;
  dataset_id: number;
  column_name: string;
  raw_value: string;
  proposed_value: string | null;
  flag_type: string;
  severity: FlagSeverity;
  reviewer_name: string;
  action: DecisionAction;
  override_value: string | null;
  notes: string | null;
  decided_at: string;
}

export interface DatasetSummary {
  id: number;
  study_id: number;
  filename: string;
  upload_status: string;
  row_count: number | null;
  column_count: number | null;
  created_at: string;
}

export interface FlagProgress {
  dataset_id: number;
  total: number;
  pending: number;
  decided: number;
  percent_complete: number;
  by_status: Record<string, number>;
}
