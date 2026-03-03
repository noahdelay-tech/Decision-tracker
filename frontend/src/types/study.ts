export interface StudySummary {
  id: number;
  name: string;
  sponsor_id: string;
  study_type: string;
  species: string;
  dataset_count: number;
  created_at: string;
}

export interface DatasetInStudy {
  id: number;
  filename: string;
  upload_status: string;
  row_count: number | null;
  flag_count: number;
  pending_count: number;
  created_at: string;
}

export interface StudyDetail extends StudySummary {
  datasets: DatasetInStudy[];
}

export interface StudyCreate {
  name: string;
  sponsor_id: string;
  study_type: string;
  species: string;
}

export interface DetectResult {
  dataset_id: number;
  status: string;
  flag_count: number;
  pending_count: number;
}

export interface IngestResult {
  dataset_id: number;
  study_id: number;
  filename: string;
  row_count: number;
  column_mappings: Record<string, string>;
  unmapped_columns: string[];
}

export interface BriefingResult {
  briefing_text: string;
  pattern_count: number;
}
