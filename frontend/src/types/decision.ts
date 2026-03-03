export type DecisionStatus = "pending" | "decided" | "in_review" | "cancelled";
export type DecisionPriority = "low" | "medium" | "high" | "critical";

export interface Decision {
  id: number;
  title: string;
  description: string | null;
  status: DecisionStatus;
  category: string | null;
  priority: DecisionPriority;
  outcome: string | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DecisionCreate {
  title: string;
  description?: string;
  status?: DecisionStatus;
  category?: string;
  priority?: DecisionPriority;
  outcome?: string;
  decided_at?: string;
}

export interface DecisionUpdate extends Partial<DecisionCreate> {}

export interface DecisionListResponse {
  items: Decision[];
  total: number;
  page: number;
  page_size: number;
}
