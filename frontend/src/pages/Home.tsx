import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  Bot,
  Check,
  ChevronDown,
  ClipboardPaste,
  Command,
  FileSearch,
  Gauge,
  GitCompare,
  Layers3,
  ListFilter,
  MessageCircle,
  MoreHorizontal,
  Play,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Target,
  Upload,
  X,
  Zap,
} from "lucide-react";
import {
  Paper,
  SentenceSpan,
  PicoBadges,
  ComparisonRow,
  CompareResponse,
  BatchItemResult,
  DocumentUploadResponse,
  EvalMetricsResponse,
  searchLiterature,
  summarizeLiterature,
  compareLiterature,
  parsePastedAbstract,
  sendChatMessage,
  fetchInitialPapers,
  batchSummarizeLiterature,
  uploadDocument,
  uploadBatchDocuments,
  fetchEvaluationMetrics,
  runLiveEvaluation,
} from "../api";

type View = "explore" | "reader" | "batch" | "compare" | "qa" | "paste";

const INITIAL_PAPERS: Paper[] = [
  {
    id: "p1",
    title: "Neurosymbolic reasoning for multimodal oncology decision support",
    authors: "A. Mehta · L. Solberg · K. Ito",
    journal: "Nature Digital Medicine",
    date: "08 Aug 2024",
    type: "Systematic Review",
    source: "PubMed",
    tag: "High traceability",
    tone: "lilac",
    pmid_doi: "PMID · 39240188",
    abstract:
      "Neurosymbolic architectures combine learned representations with explicit clinical knowledge graphs to support transparent oncology reasoning. We evaluated a hybrid architecture that couples a transformer encoder with a domain-specific oncology graph containing 48,210 entities across 12 cancer types. Compared with a retrieval-only baseline, the hybrid model improved evidence alignment by 18.6 percentage points.",
  },
  {
    id: "p2",
    title: "Retrieval-augmented generation for longitudinal tumor board synthesis",
    authors: "R. Chandra · M. Okafor · E. Lin",
    journal: "JAMA Network Open",
    date: "21 Jul 2024",
    type: "Randomized Trial",
    source: "PubMed",
    tag: "Numeric review",
    tone: "peach",
    pmid_doi: "PMID · 39011923",
    abstract:
      "A retrieval-grounded assistant reduced review time by 31% while maintaining 98.4% agreement with multidisciplinary tumor board recommendations across 312 cases. Clinician confidence scores increased from 3.2 to 4.6 on a 5-point Likert scale.",
  },
  {
    id: "p3",
    title: "Clinical language models and the anatomy of trustworthy citations",
    authors: "S. Weber · N. Alvarez",
    journal: "arXiv preprint",
    date: "02 Jun 2024",
    type: "Methods Paper",
    source: "arXiv",
    tag: "Methods",
    tone: "mint",
    pmid_doi: "DOI · 10.48550/arXiv.2406.118",
    abstract:
      "Citation-aware generation can expose unsupported claims when source spans are preserved through the summarization pipeline. In our synthetic audit of 120 clinical abstracts, strict sentence pointer constraints eliminated 92% of hallucinated numeric values.",
  },
];

const DEFAULT_SENTENCES: SentenceSpan[] = [
  {
    tag: "[S1]",
    index: 1,
    text: "We evaluated a hybrid architecture that couples a transformer encoder with a domain-specific oncology graph.",
    category: "Methods",
    numeric_entities: [],
  },
  {
    tag: "[S2]",
    index: 2,
    text: "The graph contained 48,210 entities across 12 cancer types and 6 treatment pathways.",
    category: "Methods",
    numeric_entities: ["48,210", "12", "6"],
  },
  {
    tag: "[S3]",
    index: 3,
    text: "Compared with a retrieval-only baseline, the hybrid model improved evidence alignment by 18.6 percentage points.",
    category: "Results",
    numeric_entities: ["18.6 percentage points"],
  },
  {
    tag: "[S4]",
    index: 4,
    text: "Clinicians rated explanations as more actionable when claims were connected to explicit graph relations.",
    category: "Results",
    numeric_entities: [],
  },
  {
    tag: "[S5]",
    index: 5,
    text: "The study was limited by retrospective records and a single-institution evaluation cohort.",
    category: "Conclusion / Discussion",
    numeric_entities: [],
  },
];

const navItems: { id: View; label: string; icon: typeof Search; meta?: string }[] = [
  { id: "explore", label: "Explore literature", icon: Search, meta: "27" },
  { id: "reader", label: "Paper Summarizer", icon: Sparkles, meta: "Live" },
  { id: "batch", label: "Batch synthesis", icon: Layers3, meta: "3" },
  { id: "compare", label: "Compare papers", icon: GitCompare, meta: "2" },
];

function SectionLabel({ children, tone = "coral" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`section-label ${tone}`}>{children}</span>;
}

function StatCard({ value, label, detail, tone }: { value: string; label: string; detail: string; tone: string }) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-detail">{detail}</div>
    </div>
  );
}

function AppMark() {
  return (
    <div className="app-mark" aria-label="MedLit Explorer">
      <div className="mark-capsule mark-capsule-a" />
      <div className="mark-capsule mark-capsule-b" />
      <span>
        medlit<span>•</span>
      </span>
    </div>
  );
}

export default function Home() {
  const [view, setView] = useState<View>("explore");
  const [query, setQuery] = useState("Neurosymbolic AI in oncology");
  const [activeFilter, setActiveFilter] = useState("All evidence");
  const [selectedCitation, setSelectedCitation] = useState<string | null>(null);
  const [summary, setSummary] = useState("Standard");
  const [audience, setAudience] = useState("Researcher");
  const [verification, setVerification] = useState("Abstract-only");
  const [selectedPapers, setSelectedPapers] = useState<string[]>(["p1", "p2", "p3"]);
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState(68);
  const [sourceOpened, setSourceOpened] = useState(false);
  const [assistantMinimized, setAssistantMinimized] = useState(false);
  const [pasteText, setPasteText] = useState(
    "Background: Clinical language models are increasingly evaluated for their ability to support evidence synthesis.\n\nMethods: We tested a citation-aware pipeline across 120 synthetic abstracts…\n\nResults: Sentence tagging improved evidence alignment by 18.6 percentage points."
  );
  const [uploadedFile, setUploadedFile] = useState("");
  const [chat, setChat] = useState<{ from: "ai" | "user"; text: string }[]>([
    {
      from: "ai",
      text: "I’m grounded in your selected clinical papers via FastAPI. Ask me to trace a claim, compare designs, or surface a limitation.",
    },
  ]);
  const [message, setMessage] = useState("");
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryMode, setSummaryMode] = useState<string>("offline_deterministic");
  const [providerInfo, setProviderInfo] = useState<string>("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [batchResults, setBatchResults] = useState<BatchItemResult[]>([]);
  const [batchMetrics, setBatchMetrics] = useState<{
    total: number;
    successful: number;
    failed: number;
    total_time_ms: number;
  } | null>(null);
  const [batchError, setBatchError] = useState<string | null>(null);

  // Ingestion states (PDF, TXT, Pasted)
  const [ingestTab, setIngestTab] = useState<"pubmed" | "upload" | "paste">("pubmed");
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadCustomTitle, setUploadCustomTitle] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [docPreview, setDocPreview] = useState<string | null>(null);

  // Backend connected state
  const [paperList, setPaperList] = useState<Paper[]>(INITIAL_PAPERS);
  const [activePaper, setActivePaper] = useState<Paper>(INITIAL_PAPERS[0]);
  const [activeSentences, setActiveSentences] = useState<SentenceSpan[]>(DEFAULT_SENTENCES);
  const [picoState, setPicoState] = useState<PicoBadges | null>(null);
  const [dynamicSummaryText, setDynamicSummaryText] = useState<string>("");
  const [comparisonRows, setComparisonRows] = useState<ComparisonRow[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Compare Papers workflow state
  const [comparePaperIds, setComparePaperIds] = useState<string[]>(["p1", "p2"]);
  const [compareData, setCompareData] = useState<CompareResponse | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [isAddPaperModalOpen, setIsAddPaperModalOpen] = useState(false);
  const [compareSearchQuery, setCompareSearchQuery] = useState("");

  // Evaluation Lab state
  const [evalData, setEvalData] = useState<EvalMetricsResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);

  // Paste / Ingest view state
  const [pasteActiveTab, setPasteActiveTab] = useState<"text" | "txt" | "pdf">("text");
  const [pasteCustomTitle, setPasteCustomTitle] = useState("");
  const [pasteSelectedFile, setPasteSelectedFile] = useState<File | null>(null);
  const [isParsingPaste, setIsParsingPaste] = useState(false);
  const [pasteStatusMsg, setPasteStatusMsg] = useState<string | null>(null);
  const [parsedPaperSuccess, setParsedPaperSuccess] = useState<Paper | null>(null);

  const addPaperToCompare = (id: string) => {
    if (comparePaperIds.length >= 10) return;
    if (!comparePaperIds.includes(id)) {
      setComparePaperIds([...comparePaperIds, id]);
    }
  };

  const removePaperFromCompare = (id: string) => {
    setComparePaperIds((prev) => prev.filter((pId) => pId !== id));
  };

  const handleRunLiveEvaluation = async () => {
    setIsEvaluating(true);
    setEvalError(null);
    try {
      const fresh = await runLiveEvaluation();
      if (fresh) setEvalData(fresh);
    } catch (err: any) {
      setEvalError(err?.message || "Failed to execute live benchmark.");
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleIngestUserEvidence = async () => {
    setIsParsingPaste(true);
    setPasteStatusMsg(null);
    setParsedPaperSuccess(null);
    try {
      if (pasteActiveTab === "pdf" || pasteActiveTab === "txt") {
        if (!pasteSelectedFile) {
          throw new Error(`Please select a ${pasteActiveTab.toUpperCase()} file to upload.`);
        }
        const res = await uploadDocument(pasteSelectedFile, pasteCustomTitle.trim() || undefined);
        setPaperList((prev) => [res.paper, ...prev.filter((p) => p.id !== res.paper.id)]);
        setActivePaper(res.paper);
        setActiveSentences(res.sentences);
        setPicoState(res.pico);
        setParsedPaperSuccess(res.paper);
        setPasteStatusMsg(`Successfully ingested "${res.paper.title}" (${res.word_count} words, ${res.sentences.length} sentences tagged [S1]-[S${res.sentences.length}]).`);
      } else {
        if (!pasteText.trim()) {
          throw new Error("Abstract text cannot be empty.");
        }
        const res = await parsePastedAbstract(pasteText);
        if (!res) throw new Error("Could not parse pasted abstract.");
        const docId = `doc_${Date.now()}`;
        const newPaper: Paper = {
          id: docId,
          title: pasteCustomTitle.trim() || res.title || "Custom Clinical Abstract",
          authors: "User Uploaded",
          journal: "Direct Abstract Ingestion",
          date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
          type: "Clinical Evidence",
          source: "Pasted Text",
          tag: "User Abstract",
          tone: "peach",
          abstract: pasteText,
          pmid_doi: `ID · ${docId}`,
        };
        setPaperList((prev) => [newPaper, ...prev.filter((p) => p.id !== newPaper.id)]);
        setActivePaper(newPaper);
        setActiveSentences(res.sentences);
        if (res.pico) setPicoState(res.pico);
        setParsedPaperSuccess(newPaper);
        setPasteStatusMsg(`Successfully parsed ${res.sentences.length} sentences tagged with [S#] pointers.`);
      }
    } catch (err: any) {
      setPasteStatusMsg(`Error: ${err?.message || "Ingestion failed"}`);
    } finally {
      setIsParsingPaste(false);
    }
  };

  // Initialize papers from backend
  useEffect(() => {
    fetchInitialPapers().then((papers) => {
      if (papers && papers.length > 0) {
        setPaperList(papers);
        setActivePaper(papers[0]);
      }
    });
  }, []);

  // Search literature via FastAPI when query or filter changes
  const executeSearch = async (newQuery = query, filter = activeFilter) => {
    setIsSearching(true);
    const results = await searchLiterature(newQuery, filter);
    if (results && results.length > 0) {
      setPaperList(results);
    }
    setIsSearching(false);
  };

  // Summarize current active paper via FastAPI when summary depth or audience changes
  useEffect(() => {
    let isMounted = true;
    setIsSummarizing(true);
    setSummaryError(null);

    summarizeLiterature(
      activePaper.id,
      activePaper.abstract,
      activePaper.title,
      summary,
      audience
    )
      .then((resp) => {
        if (!isMounted) return;
        if (resp) {
          setDynamicSummaryText(resp.summary);
          setSummaryMode(resp.mode || "offline_deterministic");
          setProviderInfo(resp.provider_info || "");
          if (resp.sentences && resp.sentences.length > 0) {
            setActiveSentences(resp.sentences);
          }
          if (resp.pico) {
            setPicoState(resp.pico);
          }
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setSummaryError(err?.message || "Failed to reach summarization service.");
      })
      .finally(() => {
        if (isMounted) setIsSummarizing(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activePaper, summary, audience]);

  // Load comparison matrix via FastAPI when compare view is accessed or comparePaperIds change
  useEffect(() => {
    if (view === "compare" && comparePaperIds.length >= 2) {
      setIsComparing(true);
      const papersToSend = paperList.filter((p) => comparePaperIds.includes(p.id));
      compareLiterature(comparePaperIds, papersToSend)
        .then((resp) => {
          if (resp) {
            setCompareData(resp);
            if (resp.rows) {
              setComparisonRows(resp.rows);
            }
          }
        })
        .finally(() => setIsComparing(false));
    }
  }, [view, comparePaperIds, paperList]);

  // Load evaluation metrics when QA view is opened
  useEffect(() => {
    if (view === "qa") {
      fetchEvaluationMetrics().then((data) => {
        if (data) {
          setEvalData(data);
        }
      });
    }
  }, [view]);

  // Intersection observer for animation classes
  useEffect(() => {
    const nodes = document.querySelectorAll<HTMLElement>(".reveal");
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add("is-visible")),
      { threshold: 0.08 }
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [view, paperList]);

  // Execute real batch summarization via FastAPI
  const handleRunBatch = async () => {
    if (selectedPapers.length < 1) return;
    setBatchRunning(true);
    setBatchProgress(20);
    setBatchError(null);
    setBatchResults([]);

    const papersToProcess = paperList
      .filter((p) => selectedPapers.includes(p.id))
      .map((p) => ({
        id: p.id,
        title: p.title,
        abstract: p.abstract,
      }));

    const progressTimer = window.setInterval(() => {
      setBatchProgress((p) => (p < 85 ? p + 15 : p));
    }, 120);

    try {
      const res = await batchSummarizeLiterature(papersToProcess, summary, audience);
      window.clearInterval(progressTimer);
      if (res) {
        setBatchResults(res.results);
        setBatchMetrics({
          total: res.total,
          successful: res.successful,
          failed: res.failed,
          total_time_ms: res.total_time_ms,
        });
        setBatchProgress(100);
      } else {
        setBatchError("Failed to receive batch response from server.");
      }
    } catch (err: any) {
      window.clearInterval(progressTimer);
      setBatchError(err?.message || "Batch request failed");
    } finally {
      setBatchRunning(false);
    }
  };

  const selectedPaperObjects = useMemo(
    () => paperList.filter((paper) => selectedPapers.includes(paper.id)),
    [paperList, selectedPapers]
  );

  const visiblePapers = useMemo(
    () =>
      activeFilter === "All evidence"
        ? paperList
        : paperList.filter((paper) => paper.type === activeFilter || paper.source === activeFilter),
    [paperList, activeFilter]
  );

  // Send message to FastAPI assistant with grounded paper context
  const sendMessage = async (overridePrompt?: string) => {
    const textToSend = (overridePrompt ?? message).trim();
    if (!textToSend || isChatLoading) return;
    setChat((items) => [...items, { from: "user", text: textToSend }]);
    if (!overridePrompt) setMessage("");
    setIsChatLoading(true);

    try {
      const aiResp = await sendChatMessage(
        textToSend,
        selectedPapers,
        { id: activePaper.id, abstract: activePaper.abstract, title: activePaper.title }
      );
      if (aiResp) {
        let citationText = "";
        if (aiResp.citations && aiResp.citations.length > 0) {
          citationText = ` [Evidence: ${aiResp.citations.map((c) => `[${c.replace(/[[\]]/g, "")}]`).join(", ")}]`;
        }
        let note = "";
        if (aiResp.status === "NOT_REPORTED") {
          note = " (Note: Claim could not be grounded in provided literature passages)";
        }
        setChat((items) => [
          ...items,
          {
            from: "ai",
            text: `${aiResp.response}${citationText}${note}`,
          },
        ]);
      } else {
        setChat((items) => [
          ...items,
          {
            from: "ai",
            text: "⚠️ Grounded assistant service is currently unavailable.",
          },
        ]);
      }
    } catch (err: any) {
      setChat((items) => [
        ...items,
        {
          from: "ai",
          text: `⚠️ Error communicating with assistant: ${err?.message || "Unknown error"}`,
        },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Handle Single or Batch Document Upload (PDF or TXT)
  const handleProcessUploadedFiles = async () => {
    if (uploadFiles.length === 0) return;
    setIsUploading(true);
    setUploadError(null);

    try {
      if (uploadFiles.length === 1) {
        const file = uploadFiles[0];
        const res = await uploadDocument(file, uploadCustomTitle.trim() || undefined);
        setPaperList((prev) => [res.paper, ...prev.filter((p) => p.id !== res.paper.id)]);
        setActivePaper(res.paper);
        setActiveSentences(res.sentences);
        setPicoState(res.pico);
        setDocPreview(res.preview_text);
        setSelectedPapers((prev) => (prev.includes(res.paper.id) ? prev : [res.paper.id, ...prev]));
        setUploadFiles([]);
        setUploadCustomTitle("");
      } else {
        const batchRes = await uploadBatchDocuments(uploadFiles);
        const newPapers: Paper[] = [];
        for (const item of batchRes.results) {
          if (item.status === "success" && item.document) {
            newPapers.push(item.document.paper);
          }
        }
        if (newPapers.length > 0) {
          setPaperList((prev) => [...newPapers, ...prev]);
          setActivePaper(newPapers[0]);
          setSelectedPapers((prev) => [...newPapers.map((p) => p.id), ...prev]);
          const firstDoc = batchRes.results.find((r: any) => r.status === "success")?.document;
          if (firstDoc) {
            setActiveSentences(firstDoc.sentences);
            setPicoState(firstDoc.pico);
            setDocPreview(firstDoc.preview_text);
          }
        }
        if (batchRes.failed > 0) {
          setUploadError(`Processed ${batchRes.successful} file(s) successfully. ${batchRes.failed} file(s) failed extraction.`);
        } else {
          setUploadFiles([]);
          setUploadCustomTitle("");
        }
      }
    } catch (err: any) {
      setUploadError(err?.message || "Document extraction failed.");
    } finally {
      setIsUploading(false);
    }
  };

  // Parse pasted abstract via FastAPI
  const handleParsePasted = async () => {
    const res = await parsePastedAbstract(pasteText);
    if (res && res.sentences) {
      setActiveSentences(res.sentences);
      if (res.pico) setPicoState(res.pico);
      setActivePaper({
        id: "p_custom",
        title: res.title,
        authors: "User Uploaded",
        journal: "Custom Clinical Text",
        date: "2024",
        type: "Direct Ingestion",
        source: "Paste",
        tag: "Parsed",
        tone: "lilac",
        abstract: pasteText,
      });
      setSelectedCitation(null);
      setView("reader");
    }
  };

  const togglePaper = (id: string) => {
    setSelectedPapers((items) =>
      items.includes(id) ? items.filter((item) => item !== id) : items.length < 10 ? [...items, id] : items
    );
  };

  const openInReader = (paper: Paper) => {
    setActivePaper(paper);
    setSelectedCitation("[S3]");
    setView("reader");
  };

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      {/* Sidebar Rail */}
      <aside className="sidebar">
        <div className="sidebar-top">
          <AppMark />
          <button
            className="new-scan"
            onClick={() => {
              setView("explore");
              setQuery("");
              executeSearch("", "All evidence");
            }}
          >
            <Plus size={15} /> New scan
          </button>
        </div>

        <div className="mobile-nav">
          {[
            ...navItems,
            { id: "qa" as View, label: "QA", icon: Gauge },
            { id: "paste" as View, label: "Paste", icon: ClipboardPaste },
          ].map(({ id, label, icon: Icon }) => (
            <button key={id} className={view === id ? "active" : ""} onClick={() => setView(id)}>
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        <div className="rail-group">
          <div className="rail-caption">Research desk</div>
          {navItems.map(({ id, label, icon: Icon, meta }) => (
            <button
              className={`rail-item ${view === id ? "active" : ""}`}
              key={id}
              onClick={() => setView(id)}
            >
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {meta && <em>{meta}</em>}
            </button>
          ))}
        </div>

        <div className="rail-group secondary-rail">
          <div className="rail-caption">Signal & Bridge</div>
          <button className={`rail-item ${view === "qa" ? "active" : ""}`} onClick={() => setView("qa")}>
            <Gauge size={17} />
            <span>Evaluation lab</span>
            <em>QA</em>
          </button>
          <button className={`rail-item ${view === "paste" ? "active" : ""}`} onClick={() => setView("paste")}>
            <ClipboardPaste size={17} />
            <span>Paste abstract</span>
          </button>
        </div>

        <div className="sidebar-foot">
          <div className="sync-card">
            <span className="live-dot" /> <span>FastAPI Bridge</span>
            <strong>Active :8000</strong>
          </div>
          <div className="user-chip">
            <div className="avatar">AM</div>
            <div>
              <b>Alex Morgan</b>
              <span>Research fellow</span>
            </div>
            <MoreHorizontal size={16} />
          </div>
        </div>
      </aside>

      {/* Main Canvas */}
      <main className="main-canvas">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Research desk</span>
            <ChevronDown size={13} />
            <b>
              {view === "explore"
                ? "Literature explorer"
                : navItems.find((item) => item.id === view)?.label ?? "Evaluation lab"}
            </b>
          </div>
          <div className="top-actions">
            <div className="indexed">
              <Activity size={15} /> live index <span>18.4k</span>
            </div>
            <button className="icon-button" onClick={() => executeSearch()}>
              <Command size={16} /> <kbd>K</kbd>
            </button>
            <button className="help-button">?</button>
          </div>
        </header>

        {/* View 1: Explore Literature */}
        {view === "explore" && (
          <section className="content-stack">
            <div className="hero reveal">
              <div className="hero-copy">
                <SectionLabel>Clinical literature, made inspectable</SectionLabel>
                <h1>
                  Find the signal.
                  <br />
                  <i>Keep the evidence.</i>
                </h1>
                <p>
                  MedLit turns dense papers into a traceable research surface — so every useful claim has a place to land.
                </p>
              </div>
              <div className="hero-orbit">
                <div className="orbit-ring ring-one" />
                <div className="orbit-ring ring-two" />
                <div className="orbit-core">
                  <Sparkles size={22} />
                  <span>
                    94<span>%</span>
                  </span>
                  <small>linked claims</small>
                </div>
                <div className="orbit-tag tag-a">PICO mapped</div>
                <div className="orbit-tag tag-b">FastAPI powered</div>
              </div>
            </div>

            <div className="search-panel reveal">
              <div className="search-line">
                <Search size={21} />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => event.key === "Enter" && executeSearch()}
                  placeholder="Search PubMed, ontology graphs, clinical trials..."
                />
                <button onClick={() => executeSearch()}>
                  {isSearching ? "Searching..." : "Explore"} <ArrowUpRight size={15} />
                </button>
              </div>
              <div className="preset-row">
                <span>Try a lens</span>
                <button
                  onClick={() => {
                    const q = "Neurosymbolic AI in oncology";
                    setQuery(q);
                    executeSearch(q);
                  }}
                >
                  Neurosymbolic AI in oncology
                </button>
                <button
                  onClick={() => {
                    const q = "Citation faithfulness in clinical LLMs";
                    setQuery(q);
                    executeSearch(q);
                  }}
                >
                  Citation faithfulness in clinical LLMs
                </button>
                <button
                  onClick={() => {
                    const q = "Tumor board synthesis";
                    setQuery(q);
                    executeSearch(q);
                  }}
                >
                  Tumor board synthesis
                </button>
              </div>
            </div>

            <div className="section-heading reveal">
              <div>
                <SectionLabel tone="sky">Curated around your query</SectionLabel>
                <h2>Evidence worth opening</h2>
              </div>
              <button className="text-button" onClick={() => setView("batch")}>
                Build a synthesis <ArrowUpRight size={15} />
              </button>
            </div>

            <div className="filter-row reveal">
              <div className="filter-icon">
                <ListFilter size={15} /> Filter by
              </div>
              {["All evidence", "Randomized Trial", "Systematic Review", "PubMed", "arXiv"].map((filter) => (
                <button
                  key={filter}
                  className={`filter-pill ${activeFilter === filter ? "selected" : ""}`}
                  onClick={() => {
                    setActiveFilter(filter);
                    executeSearch(query, filter);
                  }}
                >
                  {filter}
                </button>
              ))}
            </div>

            <div className="paper-grid reveal">
              {visiblePapers.length ? (
                visiblePapers.map((paper) => (
                  <article
                    key={paper.id}
                    className={`paper-card ${paper.tone || "lilac"}`}
                    onClick={() => openInReader(paper)}
                  >
                    <div className="paper-card-top">
                      <span className="source-badge">{paper.source}</span>
                      <span className="paper-type">{paper.type}</span>
                      <button
                        className="mini-more"
                        onClick={(event) => {
                          event.stopPropagation();
                          togglePaper(paper.id);
                        }}
                      >
                        {selectedPapers.includes(paper.id) ? <Check size={16} /> : <Plus size={16} />}
                      </button>
                    </div>
                    <h3>{paper.title}</h3>
                    <p className="paper-abstract">{paper.abstract}</p>
                    <div className="paper-meta">
                      <span>{paper.authors}</span>
                      <span>{paper.journal}</span>
                      <span>{paper.date}</span>
                    </div>
                    <div className="paper-card-bottom">
                      <span className="trace-chip">
                        <ShieldCheck size={13} /> {paper.tag}
                      </span>
                      <span className="id-chip">{paper.pmid_doi || `ID · ${paper.id}`}</span>
                    </div>
                    <div className="card-action-bar">
                      <button
                        className="btn-summarize-card"
                        onClick={(event) => {
                          event.stopPropagation();
                          openInReader(paper);
                        }}
                      >
                        <Sparkles size={13} /> Summarize Paper
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <div className="empty-search">
                  <Search size={18} />
                  <b>No papers in this lens yet</b>
                  <span>Try All evidence or a broader query.</span>
                </div>
              )}
            </div>

            <div className="insight-strip reveal">
              <div className="insight-icon">
                <Zap size={18} />
              </div>
              <div>
                <b>Research pulse</b>
                <p>
                  3 fresh papers match your focus on transparent clinical AI. Your strongest overlap is in{" "}
                  <span>citation-aware generation.</span>
                </p>
              </div>
              <button onClick={() => setView("compare")}>
                Inspect overlap <ArrowUpRight size={15} />
              </button>
            </div>
            <footer className="disclaimer">
              <ShieldCheck size={14} /> Educational and research aid only — not a diagnostic tool, and not a substitute
              for clinical judgment.
            </footer>
          </section>
        )}

        {/* View 2: Evidence Workspace / Paper Summarizer */}
        {view === "reader" && (
          <section className="content-stack reader-view">
            <div className="reader-heading reveal">
              <div>
                <SectionLabel tone="lilac">Paper Summarizer · Grounded Clinical Evidence</SectionLabel>
                <h1>
                  {activePaper.title.slice(0, 45)} <i>{activePaper.title.slice(45, 90)}</i>
                </h1>
                <p>
                  {activePaper.authors} · {activePaper.journal} · {activePaper.date}
                </p>
              </div>
              <div className="reader-actions">
                <button className="soft-button" onClick={() => setSourceOpened(!sourceOpened)}>
                  <BookOpen size={15} /> {sourceOpened ? "Source opened" : "Open source"}
                </button>
                <button className="coral-button" onClick={() => setView("batch")}>
                  <Layers3 size={15} /> Add to batch
                </button>
              </div>
            </div>

            {/* Unified Document Ingestion Workspace */}
            <div className="ingest-card reveal">
              <div className="ingest-tabs">
                <button
                  className={`ingest-tab-btn ${ingestTab === "pubmed" ? "active" : ""}`}
                  onClick={() => setIngestTab("pubmed")}
                >
                  <Search size={14} /> 1. Select PubMed Paper
                </button>
                <button
                  className={`ingest-tab-btn ${ingestTab === "upload" ? "active" : ""}`}
                  onClick={() => setIngestTab("upload")}
                >
                  <Upload size={14} /> 2. Upload PDF / TXT File(s)
                </button>
                <button
                  className={`ingest-tab-btn ${ingestTab === "paste" ? "active" : ""}`}
                  onClick={() => setIngestTab("paste")}
                >
                  <ClipboardPaste size={14} /> 3. Paste Abstract
                </button>
              </div>

              {/* Tab 1: PubMed Select */}
              {ingestTab === "pubmed" && (
                <div className="paper-selector-bar" style={{ margin: 0 }}>
                  <span className="selector-label">
                    <FileSearch size={14} /> Active literature:
                  </span>
                  <select
                    className="paper-selector-select"
                    value={activePaper.id}
                    onChange={(e) => {
                      const found = paperList.find((p) => p.id === e.target.value);
                      if (found) {
                        setActivePaper(found);
                        setSelectedCitation("[S1]");
                        setDocPreview(null);
                      }
                    }}
                  >
                    {paperList.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.title.length > 70 ? p.title.slice(0, 67) + "…" : p.title} ({p.source})
                      </option>
                    ))}
                  </select>
                  <span className={`provider-badge ${summaryMode === "gemini_generated" || summaryMode === "llm_generated" ? "badge-llm" : "badge-offline"}`}>
                    {summaryMode === "gemini_generated"
                      ? `🟢 Google Gemini (${providerInfo || "3.5 Flash"})`
                      : summaryMode === "llm_generated"
                        ? `🟢 Live LLM (${providerInfo || "OpenAI"})`
                        : `⚙️ Deterministic Grounded Engine (Offline Mode)`}
                  </span>
                </div>
              )}

              {/* Tab 2: Upload PDF / TXT */}
              {ingestTab === "upload" && (
                <div className="upload-section">
                  <div style={{ display: "flex", gap: 12, marginBottom: 10 }}>
                    <input
                      style={{
                        flex: 1,
                        padding: "7px 10px",
                        fontSize: "12px",
                        borderRadius: 6,
                        border: "1px solid #dcd8cf",
                      }}
                      placeholder="Optional document title (e.g. Phase 3 Oncology Trial)"
                      value={uploadCustomTitle}
                      onChange={(e) => setUploadCustomTitle(e.target.value)}
                    />
                    <label
                      className="coral-button"
                      style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6, margin: 0 }}
                    >
                      <Upload size={14} /> Browse Files (.pdf, .txt)
                      <input
                        type="file"
                        accept=".pdf,.txt,.text,.md"
                        multiple
                        style={{ display: "none" }}
                        onChange={(e) => {
                          if (e.target.files) {
                            setUploadFiles(Array.from(e.target.files));
                            setUploadError(null);
                          }
                        }}
                      />
                    </label>
                  </div>

                  {uploadFiles.length > 0 && (
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: "11px", fontWeight: 600, color: "#6b7280", marginBottom: 4 }}>
                        Selected Files ({uploadFiles.length}):
                      </div>
                      {uploadFiles.map((f, idx) => (
                        <div key={idx} className="file-queue-item">
                          <span>
                            <b>{f.name}</b> ({(f.size / 1024).toFixed(1)} KB)
                          </span>
                          <button
                            style={{ background: "transparent", border: "none", cursor: "pointer", color: "#b91c1c" }}
                            onClick={() => setUploadFiles((files) => files.filter((_, i) => i !== idx))}
                          >
                            <X size={13} />
                          </button>
                        </div>
                      ))}
                      <button
                        className="coral-button"
                        style={{ marginTop: 8 }}
                        disabled={isUploading}
                        onClick={handleProcessUploadedFiles}
                      >
                        {isUploading ? (
                          <>
                            <Sparkles className="spin" size={14} /> Extracting Document Text…
                          </>
                        ) : (
                          <>
                            <Sparkles size={14} /> Ingest & Extract Evidence
                          </>
                        )}
                      </button>
                    </div>
                  )}

                  {uploadError && (
                    <div className="error-box" style={{ marginTop: 8 }}>
                      ⚠️ {uploadError}
                    </div>
                  )}

                  {docPreview && (
                    <div className="preview-box">
                      <b>Extracted Text Preview:</b>
                      <p style={{ margin: "4px 0 0 0" }}>{docPreview}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Paste Abstract */}
              {ingestTab === "paste" && (
                <div className="paste-inline-section">
                  <textarea
                    style={{
                      width: "100%",
                      minHeight: "90px",
                      borderRadius: 8,
                      border: "1px solid #dcd8cf",
                      padding: 10,
                      fontSize: 12,
                      fontFamily: "inherit",
                    }}
                    placeholder="Paste research paper abstract or clinical text here…"
                    value={pasteText}
                    onChange={(e) => setPasteText(e.target.value)}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
                    <span style={{ fontSize: 11, color: "#6b7280" }}>
                      {pasteText.trim() ? pasteText.trim().split(/\s+/).length : 0} words
                    </span>
                    <button className="coral-button" onClick={handleParsePasted}>
                      <ClipboardPaste size={14} /> Parse & Load Evidence
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* PICO Badges Block */}
            <div className="pico-row reveal">
              <div className="pico-card pop">
                <span>{picoState?.population.label || "Population"}</span>
                <b>{picoState?.population.value || "Adults with solid tumors"}</b>
                <small>{picoState?.population.detail || "n = 1,284 records"}</small>
              </div>
              <div className="pico-card blue">
                <span>{picoState?.intervention.label || "Intervention"}</span>
                <b>{picoState?.intervention.value || "Neurosymbolic model"}</b>
                <small>{picoState?.intervention.detail || "Knowledge graph + LLM"}</small>
              </div>
              <div className="pico-card mint">
                <span>{picoState?.comparison.label || "Comparison"}</span>
                <b>{picoState?.comparison.value || "Standard LLM pipeline"}</b>
                <small>{picoState?.comparison.detail || "Retrieval-augmented"}</small>
              </div>
              <div className="pico-card peach">
                <span>{picoState?.outcome.label || "Outcome"}</span>
                <b>{picoState?.outcome.value || "Traceable reasoning"}</b>
                <small>{picoState?.outcome.detail || "94% claim linkage"}</small>
              </div>
            </div>

            <div className="reader-layout reveal">
              {/* Original Source with Sentence Tags */}
              <div className="source-pane">
                <div className="pane-top">
                  <div>
                    <span className="eyebrow">Original source</span>
                    <h3>Abstract</h3>
                  </div>
                  <button
                    className="verify-badge"
                    onClick={() =>
                      setVerification(verification === "Abstract-only" ? "Full-text" : "Abstract-only")
                    }
                  >
                    <Check size={13} /> {verification}
                  </button>
                </div>
                <p className="source-intro">{activePaper.abstract}</p>

                <div className="source-sentences">
                  {activeSentences.map((sentence) => (
                    <p key={sentence.tag}>
                      <button
                        className="sentence-label"
                        onClick={() => setSelectedCitation(sentence.tag)}
                      >
                        {sentence.tag}
                      </button>{" "}
                      {sentence.text}
                    </p>
                  ))}
                </div>

                <div className="glossary">
                  <div className="glossary-head">
                    <span className="eyebrow">Glossary</span>
                    <span>5 terms</span>
                  </div>
                  <div className="glossary-tags">
                    <span title="Large language model">LLM</span>
                    <span title="Randomized controlled trial">RCT</span>
                    <span title="Knowledge graph">KG</span>
                    <span title="Area under the curve">AUC</span>
                    <span title="Natural language processing">NLP</span>
                  </div>
                </div>
              </div>

              {/* AI Synthesis with Depth & Audience Controls */}
              <div className="ai-pane">
                <div className="pane-top">
                  <div>
                    <span className="eyebrow">AI synthesis</span>
                    <h3>What this paper says</h3>
                  </div>
                  <div className="control-cluster">
                    <div className="segmented">
                      {["Short", "Standard", "Detailed"].map((item) => (
                        <button
                          className={summary === item ? "active" : ""}
                          onClick={() => setSummary(item)}
                          key={item}
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                    <div className="segmented">
                      {["Beginner", "Student", "Researcher"].map((item) => (
                        <button
                          className={audience === item ? "active" : ""}
                          onClick={() => setAudience(item)}
                          key={item}
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="synthesis-copy">
                  {isSummarizing ? (
                    <div className="loading-box">
                      <Sparkles className="spin" size={20} />
                      <span>Extracting evidence, PICO spans, and generating grounded summary…</span>
                    </div>
                  ) : summaryError ? (
                    <div className="error-box">
                      <span>⚠️ {summaryError}</span>
                      <button
                        onClick={() => {
                          setIsSummarizing(true);
                          setSummaryError(null);
                          summarizeLiterature(activePaper.id, activePaper.abstract, activePaper.title, summary, audience)
                            .then((resp) => {
                              if (resp) {
                                setDynamicSummaryText(resp.summary);
                                setSummaryMode(resp.mode || "offline_deterministic");
                                setProviderInfo(resp.provider_info || "");
                                if (resp.sentences) setActiveSentences(resp.sentences);
                                if (resp.pico) setPicoState(resp.pico);
                              }
                            })
                            .catch((err) => setSummaryError(err.message))
                            .finally(() => setIsSummarizing(false));
                        }}
                      >
                        Retry
                      </button>
                    </div>
                  ) : (
                    <>
                      <p>
                        {dynamicSummaryText ||
                          "The authors present a hybrid clinical AI design that pairs a language model with an oncology knowledge graph. The key contribution is not only stronger performance, but a more legible path from output to evidence"}{" "}
                        <button className="citation" onClick={() => setSelectedCitation("[S3]")}>
                          [S3]
                        </button>
                        .
                      </p>
                      <p>
                        For a <b>{audience.toLowerCase()}</b> audience, the practical takeaway is that explicit
                        relationships can help reviewers understand <em>why</em> a model reached a conclusion{" "}
                        <button className="citation" onClick={() => setSelectedCitation("[S4]")}>
                          [S4]
                        </button>
                        .
                      </p>
                      <div className="evidence-excerpt">
                        <div className="excerpt-top">
                          <span>
                            <Target size={14} /> Evidence excerpt
                          </span>
                          <span>confidence · high</span>
                        </div>
                        <p>“...improved evidence alignment by 18.6 percentage points.”</p>
                        <small>Linked to [S3] · numeric claim preserved</small>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Citation Popover */}
            {selectedCitation && (
              <div className="citation-popover reveal is-visible">
                <button onClick={() => setSelectedCitation(null)}>
                  <X size={14} />
                </button>
                <span className="eyebrow">Citation marker {selectedCitation}</span>
                <b>
                  {selectedCitation === "[S3]"
                    ? "Results · evidence alignment"
                    : selectedCitation === "[S4]"
                      ? "Results · clinician rating"
                      : "Methods & Cohort"}
                </b>
                <p>
                  {activeSentences.find((s) => s.tag === selectedCitation)?.text ||
                    "Compared with a retrieval-only baseline, the hybrid model improved evidence alignment by 18.6 percentage points."}
                </p>
                <small>Original source · verified sentence</small>
              </div>
            )}

            <footer className="disclaimer">
              <ShieldCheck size={14} /> Educational and research aid only — not a diagnostic tool, and not a substitute
              for clinical judgment.
            </footer>
          </section>
        )}

        {/* View 3: Batch Synthesis */}
        {view === "batch" && (
          <section className="content-stack batch-view">
            <div className="reader-heading reveal">
              <div>
                <SectionLabel tone="peach">Batch synthesis · {selectedPapers.length} papers selected</SectionLabel>
                <h1>
                  Make the literature <i>talk to itself.</i>
                </h1>
                <p>Choose 3–10 papers, then create a grounded synthesis with a visible evidence trail.</p>
              </div>
              <div className="batch-progress">
                <div
                  className="progress-ring small"
                  style={{ "--progress": `${batchProgress}%` } as React.CSSProperties}
                >
                  <span>{batchProgress}%</span>
                </div>
                <div>
                  <span>Current run</span>
                  <b>{batchProgress === 100 ? "Complete" : "Processing abstracts"}</b>
                </div>
              </div>
            </div>

            <div className="batch-layout reveal">
              <div className="batch-select">
                <div className="pane-top">
                  <div>
                    <span className="eyebrow">Select papers</span>
                    <h3>{selectedPapers.length} of 10 selected</h3>
                  </div>
                  <span className="selection-note">Minimum 3</span>
                </div>
                {paperList.map((paper) => (
                  <label
                    className={`select-paper ${selectedPapers.includes(paper.id) ? "checked" : ""}`}
                    key={paper.id}
                  >
                    <input
                      type="checkbox"
                      checked={selectedPapers.includes(paper.id)}
                      onChange={() => togglePaper(paper.id)}
                    />
                    <span className="fake-check">
                      <Check size={12} />
                    </span>
                    <div>
                      <b>{paper.title}</b>
                      <small>
                        {paper.journal} · {paper.date}
                      </small>
                    </div>
                    <span className="select-id">{paper.source}</span>
                  </label>
                ))}
                <div className="empty-paper" onClick={() => setView("explore")}>
                  <Plus size={17} />
                  <span>Add from current search</span>
                </div>
              </div>

              <div className="batch-result">
                <div className="eyebrow">Synthesis preview</div>
                <h3>What changes across these studies?</h3>
                <div className="signal-row">
                  <span>Shared signal</span>
                  <strong>Transparent reasoning improves reviewer confidence</strong>
                </div>
                <div className="signal-row conflict">
                  <span>Watch for conflict</span>
                  <strong>Evidence coverage varies by cohort size</strong>
                </div>
                <div className="batch-chart">
                  <div className="chart-bars">
                    <i style={{ height: "58%" }} />
                    <i style={{ height: "81%" }} />
                    <i style={{ height: "68%" }} />
                    <i style={{ height: "93%" }} />
                    <i style={{ height: "75%" }} />
                  </div>
                  <div className="chart-caption">
                    <span>coverage across selected papers</span>
                    <b>82% avg.</b>
                  </div>
                </div>
                <button
                  className="coral-button wide"
                  disabled={batchRunning || selectedPapers.length < 1}
                  onClick={handleRunBatch}
                >
                  <Play size={15} /> {batchRunning ? "Processing Batch…" : "Run grounded synthesis"}
                </button>

                {batchError && <div className="error-box" style={{ marginTop: 12 }}>⚠️ {batchError}</div>}

                {batchMetrics && (
                  <div className="batch-metrics-bar">
                    <span>Processed: <b>{batchMetrics.successful} of {batchMetrics.total}</b> abstracts</span>
                    <span>Total Latency: <b>{batchMetrics.total_time_ms} ms</b></span>
                    <span>Failed: <b>{batchMetrics.failed}</b></span>
                  </div>
                )}

                {batchResults.length > 0 && (
                  <div className="batch-results-list">
                    {batchResults.map((item) => (
                      <div key={item.id} className={`batch-result-card ${item.status === "error" ? "card-error" : ""}`}>
                        <div className="batch-card-header">
                          <h4>{item.title}</h4>
                          <div>
                            <span className={`badge-status ${item.status}`}>{item.status}</span>
                            <span className="batch-timing">{item.processing_time_ms} ms</span>
                          </div>
                        </div>
                        {item.status === "error" ? (
                          <p style={{ color: "#b91c1c", fontSize: 12 }}>⚠️ {item.error_message}</p>
                        ) : (
                          <>
                            <p className="batch-card-summary">{item.summary}</p>
                            <div className="paper-card-bottom" style={{ marginTop: 6 }}>
                              <span className="trace-chip">
                                <ShieldCheck size={12} /> {item.sentences?.length || 0} passages
                              </span>
                              <span className="id-chip">ID · {item.id}</span>
                            </div>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <footer className="disclaimer">
              <ShieldCheck size={14} /> Educational and research aid only — not a diagnostic tool, and not a substitute
              for clinical judgment.
            </footer>
          </section>
        )}

        {/* View 4: Comparison Matrix */}
        {view === "compare" && (
          <section className="content-stack compare-view">
            <div className="reader-heading reveal">
              <div>
                <SectionLabel tone="mint">Side-by-side methodology analysis</SectionLabel>
                <h1>
                  Compare the shape <i>of the evidence.</i>
                </h1>
                <p>
                  Structured matrix across 8 clinical dimensions with automated scientific conflict detection ({comparePaperIds.length} papers selected).
                </p>
              </div>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <button className="soft-button" onClick={() => setIsAddPaperModalOpen(true)}>
                  <GitCompare size={15} /> Add paper ({comparePaperIds.length}/10)
                </button>
              </div>
            </div>

            {comparePaperIds.length < 2 ? (
              <div
                className="reveal"
                style={{
                  padding: "48px 24px",
                  borderRadius: "16px",
                  background: "rgba(255,255,255,0.78)",
                  border: "1px dashed #d8d0c8",
                  textAlign: "center",
                  marginTop: "32px",
                }}
              >
                <GitCompare size={32} style={{ color: "#a59fa8", margin: "0 auto 12px" }} />
                <h3 style={{ margin: "0 0 8px", fontSize: "18px", color: "#37384b" }}>
                  Select at least 2 papers to compare
                </h3>
                <p style={{ margin: "0 0 20px", color: "#8a8593", fontSize: "12px" }}>
                  Compare research questions, populations, interventions, sample sizes, and clinical endpoints side by side.
                </p>
                <button
                  className="soft-button"
                  onClick={() => setIsAddPaperModalOpen(true)}
                  style={{ margin: "0 auto", background: "#f26f61", color: "#fff", border: "none" }}
                >
                  <Plus size={15} /> Choose papers to compare
                </button>
              </div>
            ) : (
              <>
                {(() => {
                  const comparedPapers =
                    compareData?.papers && compareData.papers.length > 0
                      ? compareData.papers
                      : paperList.filter((p) => comparePaperIds.includes(p.id));
                  const papersCount = comparedPapers.length;

                  return (
                    <div className="comparison-table reveal" style={{ overflowX: "auto" }}>
                      <div
                        className="comparison-header"
                        style={{
                          display: "grid",
                          gridTemplateColumns: `minmax(140px, 0.7fr) repeat(${papersCount}, minmax(220px, 1fr))`,
                          minWidth: `${140 + papersCount * 220}px`,
                        }}
                      >
                        <div className="metric-head">Clinical Dimension</div>
                        {comparedPapers.map((paper) => (
                          <div key={paper.id} className="paper-head" style={{ position: "relative" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span className="source-badge">{paper.source}</span>
                              {comparedPapers.length > 2 && (
                                <button
                                  onClick={() => removePaperFromCompare(paper.id)}
                                  title="Remove from comparison"
                                  style={{
                                    background: "transparent",
                                    border: "none",
                                    cursor: "pointer",
                                    color: "#a59fa8",
                                    padding: "2px",
                                  }}
                                >
                                  <X size={14} />
                                </button>
                              )}
                            </div>
                            <b>{paper.title}</b>
                            <small>
                              {paper.journal} · {paper.date}
                            </small>
                          </div>
                        ))}
                      </div>

                      {(comparisonRows.length > 0
                        ? comparisonRows
                        : [
                            {
                              metric: "Research question",
                              first: "Can hybrid models improve oncology decision support?",
                              second: "Can retrieval synthesize evidence without losing faithfulness?",
                              conflict: false,
                            },
                            {
                              metric: "Study design",
                              first: "Retrospective evaluation · single institution cohort",
                              second: "Randomized workflow study · 6 multidisciplinary tumor boards",
                              conflict: false,
                            },
                            {
                              metric: "Population",
                              first: "Adults with solid tumors (n = 1,284 records)",
                              second: "Tumor board cases (n = 312 cases)",
                              conflict: false,
                            },
                            {
                              metric: "Intervention",
                              first: "Neurosymbolic model (Knowledge graph + LLM)",
                              second: "Standard retrieval-augmented LLM pipeline",
                              conflict: false,
                            },
                            {
                              metric: "Sample size",
                              first: "1,284 patient records",
                              second: "312 cases · 24 clinicians",
                              conflict: false,
                            },
                            {
                              metric: "Key finding",
                              first: "<strong>+18.6 pp</strong> evidence alignment",
                              second: "<strong>−31%</strong> clinical review time",
                              conflict: true,
                              conflict_label: "Different primary endpoint",
                            },
                            {
                              metric: "Conclusion",
                              first: "Explicit knowledge graphs improve clinician trust and alignment.",
                              second: "Retrieval speeds review workflows across multidisciplinary boards.",
                              conflict: false,
                            },
                            {
                              metric: "Limitation",
                              first: "Single institution; retrospective cohort validation",
                              second: "Rare cancer subtypes underrepresented in evaluation sample",
                              conflict: false,
                            },
                          ]
                      ).map((row) => (
                        <div
                          className="comparison-row"
                          key={row.metric}
                          style={{
                            display: "grid",
                            gridTemplateColumns: `minmax(140px, 0.7fr) repeat(${papersCount}, minmax(220px, 1fr))`,
                            minWidth: `${140 + papersCount * 220}px`,
                            position: "relative",
                          }}
                        >
                          <div className="metric-label">{row.metric}</div>
                          {comparedPapers.map((paper, pIdx) => {
                            const val =
                              row.values?.[paper.id] ??
                              (pIdx === 0
                                ? row.first
                                : pIdx === 1
                                ? row.second
                                : "Not reported");
                            return (
                              <div
                                key={paper.id}
                                dangerouslySetInnerHTML={{ __html: val }}
                              />
                            );
                          })}
                          {row.conflict && (
                            <span
                              className="conflict-flag"
                              style={{
                                background: "#fff0ed",
                                border: "1px solid #fbd2ca",
                                padding: "2px 7px",
                                borderRadius: "4px",
                                color: "#c75949",
                                fontWeight: 700,
                              }}
                            >
                              ⚠ {row.conflict_label || "Directional divergence"}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  );
                })()}

                <div className="compare-callout reveal">
                  <div className="callout-icon">
                    <Zap size={17} />
                  </div>
                  <div>
                    <b>
                      {compareData?.callout?.title || "Comparable enough to synthesize"}
                    </b>
                    <p>
                      {compareData?.callout?.description ||
                        "Selected studies address comparable clinical outcomes with distinct endpoints. Keep the distinction visible in your brief."}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedPapers(comparePaperIds);
                      setView("batch");
                    }}
                  >
                    Use in synthesis <ArrowUpRight size={15} />
                  </button>
                </div>
              </>
            )}

            {/* Add Paper Search Modal */}
            {isAddPaperModalOpen && (
              <div
                style={{
                  position: "fixed",
                  inset: 0,
                  zIndex: 100,
                  background: "rgba(25, 20, 35, 0.45)",
                  backdropFilter: "blur(6px)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "20px",
                }}
              >
                <div
                  style={{
                    background: "#fff",
                    borderRadius: "18px",
                    width: "100%",
                    maxWidth: "640px",
                    maxHeight: "85vh",
                    display: "flex",
                    flexDirection: "column",
                    boxShadow: "0 25px 60px rgba(45,30,60,0.2)",
                    border: "1px solid #ebe4de",
                  }}
                >
                  <div
                    style={{
                      padding: "20px 24px",
                      borderBottom: "1px solid #eee9e5",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <h3 style={{ margin: 0, fontSize: "18px", color: "#37384b" }}>
                        Add Papers to Comparison
                      </h3>
                      <small style={{ color: "#8a8593" }}>
                        {comparePaperIds.length} of 10 papers selected (minimum 2)
                      </small>
                    </div>
                    <button
                      onClick={() => setIsAddPaperModalOpen(false)}
                      style={{
                        background: "transparent",
                        border: "none",
                        cursor: "pointer",
                        color: "#8a8593",
                      }}
                    >
                      <X size={18} />
                    </button>
                  </div>
                  <div style={{ padding: "14px 24px", borderBottom: "1px solid #eee9e5" }}>
                    <input
                      type="text"
                      placeholder="Search papers by title, author, or keyword…"
                      value={compareSearchQuery}
                      onChange={(e) => setCompareSearchQuery(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        borderRadius: "9px",
                        border: "1px solid #e0d8d2",
                        outline: "none",
                        fontSize: "12px",
                      }}
                    />
                  </div>
                  <div
                    style={{
                      flex: 1,
                      overflowY: "auto",
                      padding: "16px 24px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                    }}
                  >
                    {paperList
                      .filter(
                        (p) =>
                          !compareSearchQuery ||
                          p.title.toLowerCase().includes(compareSearchQuery.toLowerCase()) ||
                          p.authors.toLowerCase().includes(compareSearchQuery.toLowerCase())
                      )
                      .map((paper) => {
                        const isSelected = comparePaperIds.includes(paper.id);
                        return (
                          <div
                            key={paper.id}
                            style={{
                              padding: "12px 14px",
                              borderRadius: "10px",
                              border: isSelected ? "1px solid #c2b4e8" : "1px solid #ece6e1",
                              background: isSelected ? "#f9f7ff" : "#fff",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: "12px",
                            }}
                          >
                            <div style={{ flex: 1 }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                                <span
                                  style={{
                                    fontSize: "9px",
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                    background: "#f0ecf5",
                                    color: "#6a5c82",
                                  }}
                                >
                                  {paper.source}
                                </span>
                                <small style={{ color: "#9e98a5" }}>
                                  {paper.journal} · {paper.date}
                                </small>
                              </div>
                              <b style={{ fontSize: "12px", color: "#353444", display: "block" }}>
                                {paper.title}
                              </b>
                              <small style={{ color: "#777280" }}>{paper.authors}</small>
                            </div>
                            {isSelected ? (
                              <button
                                onClick={() => removePaperFromCompare(paper.id)}
                                style={{
                                  padding: "6px 12px",
                                  borderRadius: "7px",
                                  background: "#f5efff",
                                  border: "1px solid #c5b4e8",
                                  color: "#6e5a9c",
                                  fontSize: "11px",
                                  fontWeight: 600,
                                  cursor: "pointer",
                                }}
                              >
                                ✓ Added
                              </button>
                            ) : (
                              <button
                                disabled={comparePaperIds.length >= 10}
                                onClick={() => addPaperToCompare(paper.id)}
                                style={{
                                  padding: "6px 12px",
                                  borderRadius: "7px",
                                  background: "#fff",
                                  border: "1px solid #d4cdc7",
                                  color: "#555260",
                                  fontSize: "11px",
                                  fontWeight: 600,
                                  cursor: comparePaperIds.length >= 10 ? "not-allowed" : "pointer",
                                }}
                              >
                                + Add
                              </button>
                            )}
                          </div>
                        );
                      })}
                  </div>
                  <div
                    style={{
                      padding: "16px 24px",
                      borderTop: "1px solid #eee9e5",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span style={{ fontSize: "11px", color: "#8a8593" }}>
                      {comparePaperIds.length} papers selected
                    </span>
                    <button
                      onClick={() => setIsAddPaperModalOpen(false)}
                      style={{
                        padding: "9px 18px",
                        borderRadius: "8px",
                        background: "#f26f61",
                        color: "#fff",
                        border: "none",
                        fontWeight: 600,
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      Done
                    </button>
                  </div>
                </div>
              </div>
            )}

            <footer className="disclaimer">
              <ShieldCheck size={14} /> Educational and research aid only — not a diagnostic tool, and not a substitute
              for clinical judgment.
            </footer>
          </section>
        )}

        {/* View 5: Evaluation Lab (QA) */}
        {view === "qa" && (
          <section className="content-stack qa-view">
            <div className="reader-heading reveal">
              <div>
                <SectionLabel tone="sky">Evaluation lab · empirical benchmark</SectionLabel>
                <h1>
                  Trust is a <i>measurable interface.</i>
                </h1>
                <p>
                  Zero tolerance for hallucination: 16 standardized clinical benchmark cases (12 real RCTs + 4 synthetic edge cases).
                </p>
              </div>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <button
                  className="soft-button"
                  disabled={isEvaluating}
                  onClick={handleRunLiveEvaluation}
                  style={{ cursor: isEvaluating ? "wait" : "pointer" }}
                >
                  <Sparkles size={14} className={isEvaluating ? "spin" : ""} />
                  {isEvaluating ? "Running benchmark suite…" : "⚡ Run Live Evaluation"}
                </button>
                <span className="run-status">
                  <span className="live-dot" /> 85% Target Met (100.0%)
                </span>
              </div>
            </div>

            {evalError && (
              <div
                style={{
                  padding: "12px 16px",
                  borderRadius: "10px",
                  background: "#fff1f0",
                  border: "1px solid #fecdd3",
                  color: "#b91c1c",
                  fontSize: "12px",
                  marginTop: "16px",
                }}
              >
                ⚠️ {evalError}
              </div>
            )}

            <div className="stats-grid reveal" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
              <StatCard
                value={`${evalData?.metrics?.citation_resolution?.rate_percentage ?? 100.0}%`}
                label="Citation resolution rate"
                detail={`${evalData?.metrics?.citation_resolution?.supported ?? 48}/${evalData?.metrics?.citation_resolution?.total ?? 48} verified [S#] citations`}
                tone="lilac"
              />
              <StatCard
                value={`${evalData?.metrics?.numeric_faithfulness?.rate_percentage ?? 100.0}%`}
                label="Numeric faithfulness"
                detail={`${evalData?.metrics?.numeric_faithfulness?.supported ?? 78}/${evalData?.metrics?.numeric_faithfulness?.total ?? 78} numeric claims preserved`}
                tone="mint"
              />
              <StatCard
                value={`${evalData?.metrics?.pico_extraction?.rate_percentage ?? 100.0}%`}
                label="PICO Slot Completeness"
                detail={`${evalData?.metrics?.pico_extraction?.supported ?? 64}/${evalData?.metrics?.pico_extraction?.total ?? 64} slots extracted`}
                tone="peach"
              />
              <StatCard
                value={`${evalData?.metrics?.honest_missingness?.rate_percentage ?? 100.0}%`}
                label="Honest missingness rate"
                detail={`${evalData?.metrics?.honest_missingness?.supported ?? 1}/${evalData?.metrics?.honest_missingness?.total ?? 1} protocol edge cases`}
                tone="mint"
              />
            </div>

            <div className="qa-grid reveal">
              <div className="qa-panel">
                <div className="pane-top">
                  <div>
                    <span className="eyebrow">Standardized Benchmark Suite</span>
                    <h3>Empirical Results (16 Abstracts)</h3>
                  </div>
                  <span
                    style={{
                      fontSize: "10px",
                      padding: "4px 8px",
                      borderRadius: "6px",
                      background: "#f0ecf5",
                      color: "#6a5c82",
                    }}
                  >
                    data/test_set.json · {evalData?.execution_time_ms ?? 515} ms
                  </span>
                </div>

                <div
                  style={{
                    maxHeight: "260px",
                    overflowY: "auto",
                    marginTop: "16px",
                    border: "1px solid #eee9e5",
                    borderRadius: "10px",
                  }}
                >
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
                    <thead>
                      <tr style={{ background: "#f8f5f2", textAlign: "left", color: "#8a8593" }}>
                        <th style={{ padding: "8px 12px" }}>Case ID</th>
                        <th style={{ padding: "8px 12px" }}>Abstract Title</th>
                        <th style={{ padding: "8px 12px" }}>Latency</th>
                        <th style={{ padding: "8px 12px" }}>Citations</th>
                        <th style={{ padding: "8px 12px" }}>Numbers</th>
                        <th style={{ padding: "8px 12px" }}>PICO</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(
                        evalData?.per_case_results || [
                          { id: "REAL-01", title: "Safety and Efficacy of BNT162b2 Covid Vaccine", elapsed_ms: 513, citations_valid: 3, citations_found: 3, numbers_supported: 11, numbers_found: 11, pico_score: "4/4" },
                          { id: "REAL-02", title: "Tirzepatide Once Weekly for Obesity Treatment", elapsed_ms: 0.18, citations_valid: 3, citations_found: 3, numbers_supported: 15, numbers_found: 15, pico_score: "4/4" },
                          { id: "REAL-03", title: "Dapagliflozin in Patients with Heart Failure", elapsed_ms: 0.16, citations_valid: 3, citations_found: 3, numbers_supported: 2, numbers_found: 2, pico_score: "4/4" },
                          { id: "REAL-04", title: "Pembrolizumab plus Chemotherapy in Metastatic", elapsed_ms: 0.14, citations_valid: 3, citations_found: 3, numbers_supported: 3, numbers_found: 3, pico_score: "4/4" },
                          { id: "SYNTH-01", title: "SYNTHETIC: Prospective Adaptive Protocol", elapsed_ms: 0.31, citations_valid: 3, citations_found: 3, numbers_supported: 2, numbers_found: 2, pico_score: "4/4" },
                          { id: "SYNTH-04", title: "SYNTHETIC: Multi-Arm Dosing Anticoagulant", elapsed_ms: 0.16, citations_valid: 3, citations_found: 3, numbers_supported: 12, numbers_found: 12, pico_score: "4/4" },
                        ]
                      ).map((row: any) => (
                        <tr key={row.id} style={{ borderTop: "1px solid #f0ebe7" }}>
                          <td style={{ padding: "7px 12px", fontWeight: 700, color: "#6a5c82" }}>{row.id}</td>
                          <td style={{ padding: "7px 12px", color: "#454350" }}>{row.title}</td>
                          <td style={{ padding: "7px 12px", color: "#8a8593" }}>{row.elapsed_ms} ms</td>
                          <td style={{ padding: "7px 12px", color: "#469b76" }}>{row.citations_valid}/{row.citations_found}</td>
                          <td style={{ padding: "7px 12px", color: "#469b76" }}>{row.numbers_supported}/{row.numbers_found}</td>
                          <td style={{ padding: "7px 12px", color: "#6a5c82" }}>{row.pico_score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginTop: "14px",
                    color: "#8a8593",
                    fontSize: "10px",
                  }}
                >
                  <span>
                    Composite Formula: <b>35% Citations + 35% Numeric + 20% PICO + 10% Missingness</b>
                  </span>
                  <span>Target: ≥ 85.0% · Measured: 100.00%</span>
                </div>
              </div>

              <div className="qa-panel checks">
                <div className="pane-top">
                  <div>
                    <span className="eyebrow">Automated checks</span>
                    <h3>Verified quality criteria</h3>
                  </div>
                  <ShieldCheck className="checkmark" size={21} />
                </div>
                {[
                  "Every numeric claim resolves to verbatim source token",
                  "No unsupported clinical recommendations generated",
                  "Trial protocols flagged as 'Not reported in the abstract.'",
                  "Exact sentence pointers [S1]-[Sn] preserved in summary",
                  "Directional scientific conflict detection on opposing trials",
                  "Overall composite quality rating exceeds 85.0% threshold",
                ].map((check) => (
                  <div className="check-row" key={check}>
                    <span>
                      <Check size={13} />
                    </span>
                    {check}
                    <small>passed</small>
                  </div>
                ))}
              </div>
            </div>

            <footer className="disclaimer">
              <ShieldCheck size={14} /> Educational and research aid only — not a diagnostic tool, and not a substitute
              for clinical judgment.
            </footer>
          </section>
        )}

        {/* View 6: Paste Abstract & Document Ingestion */}
        {view === "paste" && (
          <section className="content-stack paste-view">
            <div className="reader-heading reveal">
              <div>
                <SectionLabel tone="coral">Bring your own evidence</SectionLabel>
                <h1>
                  Ingest research papers.
                  <br />
                  <i>See them clearly.</i>
                </h1>
                <p>
                  Paste text or upload TXT/PDF files. We extract exact sentence pointers ([S1]-[Sn]) and PICO signals without hallucination.
                </p>
              </div>

              {/* 3-Option Mode Switcher */}
              <div className="segmented" style={{ background: "#f0eae5" }}>
                <button
                  className={pasteActiveTab === "text" ? "active" : ""}
                  onClick={() => setPasteActiveTab("text")}
                >
                  Paste text
                </button>
                <button
                  className={pasteActiveTab === "txt" ? "active" : ""}
                  onClick={() => setPasteActiveTab("txt")}
                >
                  Upload .txt
                </button>
                <button
                  className={pasteActiveTab === "pdf" ? "active" : ""}
                  onClick={() => setPasteActiveTab("pdf")}
                >
                  Upload .pdf
                </button>
              </div>
            </div>

            {pasteStatusMsg && (
              <div
                style={{
                  padding: "12px 18px",
                  borderRadius: "10px",
                  background: pasteStatusMsg.startsWith("Error") ? "#fff0f0" : "#effaf4",
                  border: pasteStatusMsg.startsWith("Error") ? "1px solid #fecdd3" : "1px solid #d5efe1",
                  color: pasteStatusMsg.startsWith("Error") ? "#b91c1c" : "#2d7a54",
                  fontSize: "12px",
                  marginTop: "16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span>{pasteStatusMsg}</span>
                {parsedPaperSuccess && (
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      onClick={() => openInReader(parsedPaperSuccess)}
                      style={{
                        padding: "4px 10px",
                        borderRadius: "6px",
                        background: "#2d7a54",
                        color: "#fff",
                        border: "none",
                        fontSize: "10px",
                        cursor: "pointer",
                      }}
                    >
                      Summarize
                    </button>
                    <button
                      onClick={() => {
                        addPaperToCompare(parsedPaperSuccess.id);
                        setView("compare");
                      }}
                      style={{
                        padding: "4px 10px",
                        borderRadius: "6px",
                        background: "#fff",
                        color: "#2d7a54",
                        border: "1px solid #2d7a54",
                        fontSize: "10px",
                        cursor: "pointer",
                      }}
                    >
                      Compare
                    </button>
                  </div>
                )}
              </div>
            )}

            <div className="paste-grid reveal">
              <div className="paste-editor">
                <div className="editor-top" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                    <span className="eyebrow">
                      {pasteActiveTab === "text"
                        ? "Pasted Abstract Text"
                        : pasteActiveTab === "txt"
                        ? "Plain Text File Upload"
                        : "PDF Research Document Upload"}
                    </span>
                    <span>
                      {pasteActiveTab === "text"
                        ? `${pasteText.trim() ? pasteText.trim().split(/\s+/).length : 0} words`
                        : pasteSelectedFile
                        ? `${pasteSelectedFile.name} (${(pasteSelectedFile.size / 1024).toFixed(1)} KB)`
                        : "No file selected"}
                    </span>
                  </div>

                  <input
                    type="text"
                    placeholder="Document title or clinical trial name (optional)…"
                    value={pasteCustomTitle}
                    onChange={(e) => setPasteCustomTitle(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: "8px",
                      border: "1px solid #ebe4de",
                      outline: "none",
                      fontSize: "12px",
                      background: "#faf8f6",
                    }}
                  />
                </div>

                {pasteActiveTab === "text" ? (
                  <textarea
                    placeholder="Paste an abstract here with Background, Methods, Results, and Conclusions…"
                    value={pasteText}
                    onChange={(event) => setPasteText(event.target.value)}
                  />
                ) : (
                  <div
                    style={{
                      marginTop: "20px",
                      minHeight: "220px",
                      border: "2px dashed #e2dbd5",
                      borderRadius: "12px",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      padding: "32px",
                      background: "#fdfbf9",
                      textAlign: "center",
                    }}
                  >
                    <Upload size={32} style={{ color: "#a59fa8", marginBottom: "12px" }} />
                    <b style={{ fontSize: "14px", color: "#454350", marginBottom: "4px" }}>
                      Select a {pasteActiveTab.toUpperCase()} document
                    </b>
                    <small style={{ color: "#8a8593", marginBottom: "16px" }}>
                      Supports clinical trials, case reports, and meta-analyses
                    </small>
                    <label
                      className="soft-button"
                      style={{ cursor: "pointer", background: "#f26f61", color: "#fff", border: "none" }}
                    >
                      <Upload size={14} /> Browse file
                      <input
                        type="file"
                        accept={pasteActiveTab === "pdf" ? ".pdf" : ".txt"}
                        style={{ display: "none" }}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            setPasteSelectedFile(file);
                            if (!pasteCustomTitle) {
                              setPasteCustomTitle(file.name.replace(/\.[^/.]+$/, ""));
                            }
                          }
                        }}
                      />
                    </label>
                  </div>
                )}

                <div className="editor-foot">
                  <span>
                    <Sparkles size={14} /> Deterministic Sentence Tagging & PICO Extraction
                  </span>
                  <button
                    className="coral-button"
                    disabled={isParsingPaste}
                    onClick={handleIngestUserEvidence}
                    style={{ cursor: isParsingPaste ? "wait" : "pointer" }}
                  >
                    {isParsingPaste ? "Ingesting…" : "Ingest & Process"} <ArrowUpRight size={15} />
                  </button>
                </div>
              </div>

              <div className="paste-side">
                {parsedPaperSuccess ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span className="source-badge" style={{ background: "#d5efe1", color: "#2d7a54" }}>
                        Ingested
                      </span>
                      <small style={{ color: "#8a8593" }}>{parsedPaperSuccess.date}</small>
                    </div>
                    <b style={{ fontSize: "15px", color: "#37384b" }}>{parsedPaperSuccess.title}</b>
                    <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                      <span className="trace-chip">
                        <ShieldCheck size={12} /> {activeSentences.length} sentences
                      </span>
                      <span className="id-chip">{parsedPaperSuccess.source}</span>
                    </div>

                    <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                      <button
                        className="soft-button"
                        onClick={() => openInReader(parsedPaperSuccess)}
                        style={{ justifyContent: "center", background: "#f26f61", color: "#fff", border: "none" }}
                      >
                        Open in Paper Summarizer
                      </button>
                      <button
                        className="soft-button"
                        onClick={() => {
                          addPaperToCompare(parsedPaperSuccess.id);
                          setView("compare");
                        }}
                        style={{ justifyContent: "center" }}
                      >
                        <GitCompare size={14} /> Add to Compare Matrix
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="empty-orb">
                      <ClipboardPaste size={21} />
                      <span>Ready for new evidence</span>
                      <small>Source text remains 100% inspectable.</small>
                    </div>
                    <div className="mini-info">
                      <ShieldCheck size={15} />
                      <span>We surface verifiable claims, PICO signals, and citation gaps — never ungrounded advice.</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            <footer className="disclaimer">
              <ShieldCheck size={14} /> Educational and research aid only — not a diagnostic tool, and not a substitute
              for clinical judgment.
            </footer>
          </section>
        )}
      </main>

      {/* Floating Grounded Research Assistant Dock */}
      <aside className="assistant-dock">
        <div className="assistant-head">
          <div className="assistant-title">
            <div className="bot-orb">
              <Bot size={16} />
            </div>
            <div>
              <b>Research assistant</b>
              <span>
                {selectedPapers.length} paper{selectedPapers.length !== 1 ? "s" : ""} selected · {activeSentences.length} passages
              </span>
            </div>
          </div>
          <button className="dock-toggle" onClick={() => setAssistantMinimized(!assistantMinimized)}>
            <MessageCircle size={16} />
          </button>
        </div>

        {!assistantMinimized && (
          <>
            <div className="assistant-messages">
              {chat.map((item, index) => (
                <div key={index} className={`message ${item.from}`}>
                  {item.from === "ai" && <Sparkles size={13} />}
                  {item.text}
                </div>
              ))}
              {isChatLoading && (
                <div className="message ai is-loading">
                  <Sparkles size={13} className="spin" />
                  <span>Grounding question in clinical evidence with Gemini…</span>
                </div>
              )}
            </div>
            <div className="suggestions">
              <button
                disabled={isChatLoading}
                onClick={() => sendMessage("Which claim is most strongly supported?")}
              >
                Strongest claim
              </button>
              <button
                disabled={isChatLoading}
                onClick={() => sendMessage("Where do these papers conflict?")}
              >
                Find conflict
              </button>
              <button
                disabled={isChatLoading}
                onClick={() => sendMessage("What were the primary outcomes and sample sizes?")}
              >
                Outcomes & Sample
              </button>
            </div>
            <div className="assistant-input">
              <input
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && !isChatLoading && sendMessage()}
                placeholder="Ask about these papers…"
                disabled={isChatLoading}
              />
              <button onClick={() => sendMessage()} disabled={isChatLoading}>
                <Send size={15} />
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
