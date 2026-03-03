import type {
  Decision,
  DecisionCreate,
  DecisionUpdate,
  DecisionListResponse,
} from "@/types/decision";
import type {
  DatasetSummary,
  DecisionLogEntry,
  DecisionSubmit,
  FlagListResponse,
  FlagProgress,
  FlagWithContext,
} from "@/types/flag";
import type {
  BriefingResult,
  DetectResult,
  IngestResult,
  StudyCreate,
  StudyDetail,
  StudySummary,
} from "@/types/study";

const BASE = "/api/v1";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function qs(params: Record<string, string | number | undefined>): string {
  const s = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return s ? `?${s}` : "";
}

export const api = {
  studies: {
    list(): Promise<StudySummary[]> {
      return request("/studies/");
    },
    get(id: number): Promise<StudyDetail> {
      return request(`/studies/${id}`);
    },
    create(data: StudyCreate): Promise<StudySummary> {
      return request("/studies/", { method: "POST", body: JSON.stringify(data) });
    },
    generateBriefing(id: number, force = false): Promise<BriefingResult> {
      return request(`/studies/${id}/briefing/generate${force ? "?force=true" : ""}`);
    },
  },

  ingest: {
    upload(file: File, studyId: number): Promise<IngestResult> {
      const form = new FormData();
      form.append("file", file);
      form.append("study_id", String(studyId));
      // Do not use request() — FormData must NOT have Content-Type pre-set;
      // the browser sets it automatically with the multipart boundary.
      return fetch(`${BASE}/ingest/`, { method: "POST", body: form }).then(
        async (res) => {
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail ?? "Upload failed");
          }
          return res.json() as Promise<IngestResult>;
        }
      );
    },
  },

  datasets: {
    list(): Promise<DatasetSummary[]> {
      return request("/datasets/");
    },
    detect(id: number): Promise<DetectResult> {
      return request(`/datasets/${id}/detect`, { method: "POST" });
    },
  },

  flags: {
    list(params?: {
      dataset_id?: number;
      status?: string;
      severity?: string;
      flag_type?: string;
      page?: number;
      page_size?: number;
    }): Promise<FlagListResponse> {
      return request(`/flags/${qs(params ?? {})}`);
    },
    getWithContext(id: number): Promise<FlagWithContext> {
      return request(`/flags/${id}`);
    },
    decide(id: number, data: DecisionSubmit): Promise<{ flag: FlagWithContext["flag"]; decision: FlagWithContext["existing_decision"] }> {
      return request(`/flags/${id}/decide`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    decisionLog(params?: { dataset_id?: number; page?: number; page_size?: number }): Promise<DecisionLogEntry[]> {
      return request(`/flags/decisions/log${qs(params ?? {})}`);
    },
    progress(dataset_id: number): Promise<FlagProgress> {
      return request(`/flags/progress?dataset_id=${dataset_id}`);
    },
  },

  decisions: {
    list(params?: {
      page?: number;
      page_size?: number;
      status?: string;
      category?: string;
      priority?: string;
    }): Promise<DecisionListResponse> {
      const qs = new URLSearchParams(
        Object.entries(params ?? {})
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      ).toString();
      return request(`/decisions/${qs ? `?${qs}` : ""}`);
    },
    get(id: number): Promise<Decision> {
      return request(`/decisions/${id}`);
    },
    create(data: DecisionCreate): Promise<Decision> {
      return request("/decisions/", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    update(id: number, data: DecisionUpdate): Promise<Decision> {
      return request(`/decisions/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },
    delete(id: number): Promise<void> {
      return request(`/decisions/${id}`, { method: "DELETE" });
    },
  },
};
