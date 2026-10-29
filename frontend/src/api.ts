/**
 * API client bridging the Manus AI React frontend with the FastAPI backend.
 */

const API_BASE_URL = "http://localhost:8000/api";
const getApiBaseUrl = () => {
  if (typeof window !== "undefined") {
    const host = window.location.hostname || "localhost";
    return `${window.location.protocol}//${host}:8000/api`;
  }
  return "http://localhost:8000/api";
};

const API_BASE_URL = getApiBaseUrl();

async function safeFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  try {
    return await fetch(`${API_BASE_URL}${cleanEndpoint}`, options);
  } catch (directErr) {
    // If direct port 8000 connection refused or blocked, fallback to same-origin proxy
    try {
      return await fetch(`/api${cleanEndpoint}`, options);
    } catch {
      throw directErr;
    }
  }
}

export interface Paper {
  id: string;
  title: string;
  authors: string;
  journal: string;
  date: string;
  type: string;
  source: string;
  tag: string;
  tone: string;
  abstract: string;
  pmid_doi?: string;
  url?: string;
}

export interface SentenceSpan {
  tag: string;
  index: number;
  text: string;
  category: string;
  numeric_entities: string[];
}

export interface PicoBadge {
  label: string;
  value: string;
  detail: string;
  style: string;
}

export interface PicoBadges {
  population: PicoBadge;
  intervention: PicoBadge;
  comparison: PicoBadge;
  outcome: PicoBadge;
}

export interface SummarizeResponse {
  paper_id?: string;
  title?: string;
  summary: string;
  sentences: SentenceSpan[];
  pico: PicoBadges;
  preserved_excerpts: Array<{
    tag: string;
    text: string;
    confidence: string;
    category: string;
    numeric_claim: string;
  }>;
  confidence: string;
  mode?: string;
  provider_info?: string;
}

export interface ComparisonRow {
  metric: string;
  first: string;
  second: string;
  values?: Record<string, string>;
  conflict: boolean;
  conflict_label?: string;
}

export interface CompareResponse {
  papers: Paper[];
  rows: ComparisonRow[];
  callout: {
    title: string;
    description: string;
  };
  conflicts?: Array<{
    pair: [string, string];
    status: string;
    reason: string;
  }>;
  status?: string;
}

export interface PasteResponse {
  word_count: number;
  sentences: SentenceSpan[];
  pico: PicoBadges;
  title: string;
}

export interface ChatResponse {
  response: string;
  citations: string[];
  confidence: string;
  is_grounded?: boolean;
  status?: string;
  mode?: string;
}

/**
 * Searches PubMed and curated literature via FastAPI POST /api/search
 */
export async function searchLiterature(query: string, filterType = "All evidence"): Promise<Paper[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/search`, {
    const res = await safeFetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, filter_type: filterType, limit: 10 }),
    });
    if (!res.ok) throw new Error(`Search error: ${res.statusText}`);
    const data = await res.json();
    return data.papers || [];
  } catch (err) {
    console.warn("Backend search unreachable, using fallback", err);
    return [];
  }
}

/**
 * Generates grounded summary with sentence citations via FastAPI POST /api/summarize
 */
export async function summarizeLiterature(
  paperId?: string,
  abstract?: string,
  title?: string,
  depth = "Standard",
  audience = "Researcher"
): Promise<SummarizeResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/summarize`, {
    const res = await safeFetch("/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paper_id: paperId,
        abstract: abstract,
        title: title,
        summary_depth: depth,
        audience: audience,
      }),
    });
    if (!res.ok) throw new Error(`Summarize error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("Backend summarize request failed:", err);
    throw err;
  }
}

/**
 * Generates methodology comparison matrix via FastAPI POST /api/compare
 */
export async function compareLiterature(
  paperIds: string[],
  papers?: Paper[]
): Promise<CompareResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/compare`, {
    const res = await safeFetch("/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paper_ids: paperIds, papers: papers || undefined }),
    });
    if (!res.ok) throw new Error(`Compare error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend compare unreachable", err);
    return null;
  }
}

/**
 * Ingests and tags pasted abstract via FastAPI POST /api/paste
 */
export async function parsePastedAbstract(text: string): Promise<PasteResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/paste`, {
    const res = await safeFetch("/paste", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(`Paste parse error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend paste parse unreachable", err);
    return null;
  }
}

/**
 * Queries grounded research assistant via FastAPI POST /api/chat
 */
export async function sendChatMessage(
  query: string,
  selectedPapers: string[] = [],
  activePaper?: { id: string; abstract?: string; title?: string }
): Promise<ChatResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/chat`, {
    const res = await safeFetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        selected_papers: selectedPapers,
        active_paper_id: activePaper?.id,
        active_paper_abstract: activePaper?.abstract,
      }),
    });
    if (!res.ok) throw new Error(`Chat error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("Backend chat request failed:", err);
    throw err;
  }
}

/**
 * Lists all initial curated papers
 */
export async function fetchInitialPapers(): Promise<Paper[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/papers`);
    const res = await safeFetch("/papers");
    if (!res.ok) throw new Error(`Papers fetch error: ${res.statusText}`);
    const data = await res.json();
    return data.papers || [];
  } catch (err) {
    console.warn("Backend papers fetch unreachable", err);
    return [];
  }
}

/**
 * Queries backend health and AI provider configuration
 */
export async function checkBackendHealth(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    const res = await safeFetch("/health");
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export interface BatchItemResult {
  id: string;
  title: string;
  status: "success" | "error";
  error_message?: string;
  summary?: string;
  sentences: SentenceSpan[];
  pico?: PicoBadges;
  processing_time_ms: number;
  mode?: string;
}

export interface BatchSummarizeResponse {
  total: number;
  successful: number;
  failed: number;
  max_batch_size: number;
  total_time_ms: number;
  results: BatchItemResult[];
}

export interface DocumentUploadResponse {
  doc_id: string;
  title: string;
  filename: string;
  doc_type: string;
  word_count: number;
  page_count: number;
  preview_text: string;
  full_text: string;
  paper: Paper;
  sentences: SentenceSpan[];
  pico: PicoBadges;
}

/**
 * Ingests a PDF or plain text document via FastAPI POST /api/upload
 */
export async function uploadDocument(file: File, userTitle?: string): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (userTitle) {
    formData.append("title", userTitle);
  }

  const res = await fetch(`${API_BASE_URL}/upload`, {
  const res = await safeFetch("/upload", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Ingests multiple research documents simultaneously via FastAPI POST /api/upload-batch
 */
export async function uploadBatchDocuments(files: File[]): Promise<any> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const res = await fetch(`${API_BASE_URL}/upload-batch`, {
  const res = await safeFetch("/upload-batch", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Batch upload failed: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Executes a batch summarization across multiple papers in a single atomic request.
 */
export async function batchSummarizeLiterature(
  papers: Array<{ id: string; title?: string; abstract: string }>,
  depth = "Standard",
  audience = "Researcher"
): Promise<BatchSummarizeResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/batch-summarize`, {
    const res = await safeFetch("/batch-summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        papers,
        summary_depth: depth,
        audience,
      }),
    });
    if (!res.ok) throw new Error(`Batch summarize error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("Backend batch summarize request failed:", err);
    throw err;
  }
}

export interface MetricDetail {
  name: string;
  rate_percentage: number;
  supported: number;
  total: number;
  target_percentage: number;
  meets_target: boolean;
  formula: string;
  description: string;
}

export interface EvalCaseResult {
  id: string;
  title: string;
  elapsed_ms: number;
  citations_found: number;
  citations_valid: number;
  numbers_found: number;
  numbers_supported: number;
  pico_score: string;
  mode: string;
}

export interface EvalMetricsResponse {
  dataset_name: string;
  dataset_path: string;
  total_test_cases: number;
  successful_cases: number;
  dataset_breakdown: string;
  execution_time_ms: number;
  composite_quality_score: number;
  meets_85_target: boolean;
  last_run_timestamp: string;
  metrics: {
    citation_resolution: MetricDetail;
    numeric_faithfulness: MetricDetail;
    pico_extraction: MetricDetail;
    honest_missingness: MetricDetail;
  };
  per_case_results: EvalCaseResult[];
}

/**
 * Retrieves latest empirical benchmark evaluation metrics from FastAPI GET /api/eval/metrics
 */
export async function fetchEvaluationMetrics(): Promise<EvalMetricsResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/eval/metrics`);
    const res = await safeFetch("/eval/metrics");
    if (!res.ok) throw new Error(`Eval metrics error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend evaluation metrics unreachable", err);
    return null;
  }
}

/**
 * Triggers a live empirical evaluation test run via FastAPI POST /api/eval/run
 */
export async function runLiveEvaluation(): Promise<EvalMetricsResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/eval/run`, {
    const res = await safeFetch("/eval/run", {
      method: "POST",
    });
    if (!res.ok) throw new Error(`Run eval error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("Failed to run live evaluation:", err);
    throw err;
  }
}
