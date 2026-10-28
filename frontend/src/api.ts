/**
 * API client bridging the Manus AI React frontend with the FastAPI backend.
 */

const API_BASE_URL = "http://localhost:8000/api";

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
}

export interface ComparisonRow {
  metric: string;
  first: string;
  second: string;
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
}

/**
 * Searches PubMed and curated literature via FastAPI POST /api/search
 */
export async function searchLiterature(query: string, filterType = "All evidence"): Promise<Paper[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, filter_type: filterType, limit: 10 }),
    });
    if (!res.ok) throw new Error(`Search error: ${res.statusText}`);
    const data = await res.json();
    return data.papers || [];
  } catch (err) {
    console.warn("Backend search unreachable, using local fallback", err);
    return [];
  }
}

/**
 * Generates grounded summary with sentence citations via FastAPI POST /api/summarize
 */
export async function summarizeLiterature(
  paperId?: string,
  abstract?: string,
  depth = "Standard",
  audience = "Researcher"
): Promise<SummarizeResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/summarize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paper_id: paperId,
        abstract: abstract,
        summary_depth: depth,
        audience: audience,
      }),
    });
    if (!res.ok) throw new Error(`Summarize error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend summarize unreachable, using local fallback", err);
    return null;
  }
}

/**
 * Generates methodology comparison matrix via FastAPI POST /api/compare
 */
export async function compareLiterature(paperIds: string[]): Promise<CompareResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paper_ids: paperIds }),
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
export async function sendChatMessage(query: string, selectedPapers: string[] = []): Promise<ChatResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, selected_papers: selectedPapers }),
    });
    if (!res.ok) throw new Error(`Chat error: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend chat unreachable", err);
    return null;
  }
}

/**
 * Lists all initial curated papers
 */
export async function fetchInitialPapers(): Promise<Paper[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/papers`);
    if (!res.ok) throw new Error(`Papers fetch error: ${res.statusText}`);
    const data = await res.json();
    return data.papers || [];
  } catch (err) {
    console.warn("Backend papers fetch unreachable", err);
    return [];
  }
}
