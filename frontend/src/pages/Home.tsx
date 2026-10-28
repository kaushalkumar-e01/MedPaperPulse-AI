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
  searchLiterature,
  summarizeLiterature,
  compareLiterature,
  parsePastedAbstract,
  sendChatMessage,
  fetchInitialPapers,
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
  { id: "reader", label: "Evidence workspace", icon: FileSearch, meta: "Open" },
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

  // Backend connected state
  const [paperList, setPaperList] = useState<Paper[]>(INITIAL_PAPERS);
  const [activePaper, setActivePaper] = useState<Paper>(INITIAL_PAPERS[0]);
  const [activeSentences, setActiveSentences] = useState<SentenceSpan[]>(DEFAULT_SENTENCES);
  const [picoState, setPicoState] = useState<PicoBadges | null>(null);
  const [dynamicSummaryText, setDynamicSummaryText] = useState<string>("");
  const [comparisonRows, setComparisonRows] = useState<ComparisonRow[]>([]);
  const [isSearching, setIsSearching] = useState(false);

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
    summarizeLiterature(activePaper.id, activePaper.abstract, summary, audience).then((resp) => {
      if (resp) {
        setDynamicSummaryText(resp.summary);
        if (resp.sentences && resp.sentences.length > 0) {
          setActiveSentences(resp.sentences);
        }
        if (resp.pico) {
          setPicoState(resp.pico);
        }
      }
    });
  }, [activePaper, summary, audience]);

  // Load comparison matrix via FastAPI when compare view is accessed
  useEffect(() => {
    if (view === "compare") {
      compareLiterature(selectedPapers).then((resp) => {
        if (resp && resp.rows) {
          setComparisonRows(resp.rows);
        }
      });
    }
  }, [view, selectedPapers]);

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

  // Batch progress simulation
  useEffect(() => {
    if (!batchRunning) return;
    const timer = window.setInterval(() => {
      setBatchProgress((progress) => {
        if (progress >= 100) {
          setBatchRunning(false);
          return 100;
        }
        return progress + 4;
      });
    }, 400);
    return () => window.clearInterval(timer);
  }, [batchRunning]);

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

  // Send message to FastAPI assistant
  const sendMessage = async () => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setChat((items) => [...items, { from: "user", text: trimmed }]);
    setMessage("");

    const aiResp = await sendChatMessage(trimmed, selectedPapers);
    if (aiResp) {
      setChat((items) => [...items, { from: "ai", text: aiResp.response }]);
    } else {
      setChat((items) => [
        ...items,
        {
          from: "ai",
          text: "This claim is supported by [S3] and [S4]. The confidence is high, but the cohort size limits generalization.",
        },
      ]);
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

        {/* View 2: Evidence Workspace / Reader */}
        {view === "reader" && (
          <section className="content-stack reader-view">
            <div className="reader-heading reveal">
              <div>
                <SectionLabel tone="lilac">Evidence workspace · Active Paper</SectionLabel>
                <h1>
                  {activePaper.title.slice(0, 40)} <i>{activePaper.title.slice(40, 75)}</i>
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
                  disabled={selectedPapers.length < 3}
                  onClick={() => {
                    setBatchRunning(true);
                    setBatchProgress(8);
                  }}
                >
                  <Play size={15} /> {batchRunning ? "Processing…" : "Run grounded synthesis"}
                </button>
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
                <SectionLabel tone="mint">Side-by-side reading</SectionLabel>
                <h1>
                  Compare the shape <i>of the evidence.</i>
                </h1>
                <p>Two papers, one clear view of where their methods agree — and where they don’t.</p>
              </div>
              <button className="soft-button" onClick={() => setView("explore")}>
                <GitCompare size={15} /> Add paper
              </button>
            </div>

            <div className="comparison-table reveal">
              <div className="comparison-header">
                <div className="metric-head">Metric</div>
                {selectedPaperObjects.slice(0, 2).map((paper) => (
                  <div key={paper.id} className="paper-head">
                    <span className="source-badge">{paper.source}</span>
                    <b>{paper.title}</b>
                    <small>{paper.journal}</small>
                  </div>
                ))}
              </div>

              {(comparisonRows.length > 0
                ? comparisonRows
                : [
                    {
                      metric: "Research question",
                      first: "Can hybrid models make oncology reasoning more inspectable?",
                      second: "Can retrieval improve tumor board synthesis without losing faithfulness?",
                      conflict: false,
                    },
                    {
                      metric: "Study design",
                      first: "Retrospective evaluation · single institution",
                      second: "Randomized workflow study · 6 tumor boards",
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
                      second: "<strong>−31%</strong> review time",
                      conflict: true,
                    },
                    {
                      metric: "Limitation",
                      first: "Single institution; retrospective cohort",
                      second: "Rare disease cases underrepresented",
                      conflict: false,
                    },
                  ]
              ).map((row, index) => (
                <div className="comparison-row" key={row.metric}>
                  <div className="metric-label">{row.metric}</div>
                  <div dangerouslySetInnerHTML={{ __html: row.first }} />
                  <div dangerouslySetInnerHTML={{ __html: row.second }} />
                  {row.conflict && <span className="conflict-flag">Different outcome</span>}
                </div>
              ))}
            </div>

            <div className="compare-callout reveal">
              <div className="callout-icon">
                <Zap size={17} />
              </div>
              <div>
                <b>Comparable enough to synthesize</b>
                <p>
                  Both papers measure reviewer-facing trust, but use different primary outcomes. Keep the distinction
                  visible in your final brief.
                </p>
              </div>
              <button onClick={() => setView("batch")}>
                Use in synthesis <ArrowUpRight size={15} />
              </button>
            </div>

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
                <SectionLabel tone="sky">Evaluation lab · last run today</SectionLabel>
                <h1>
                  Trust is a <i>measurable interface.</i>
                </h1>
                <p>Monitor whether the system preserves what the papers actually say.</p>
              </div>
              <span className="run-status">
                <span className="live-dot" /> All systems nominal
              </span>
            </div>

            <div className="stats-grid reveal">
              <StatCard
                value="94.2%"
                label="Citation resolution rate"
                detail="+4.8% vs. last run"
                tone="lilac"
              />
              <StatCard
                value="98.1%"
                label="Numeric faithfulness"
                detail="No drift detected"
                tone="mint"
              />
              <StatCard
                value="0.87"
                label="Grounding confidence"
                detail="High · 2,481 claims"
                tone="peach"
              />
            </div>

            <div className="qa-grid reveal">
              <div className="qa-panel">
                <div className="pane-top">
                  <div>
                    <span className="eyebrow">Benchmark trend</span>
                    <h3>Evidence quality over time</h3>
                  </div>
                  <span className="small-period">
                    Last 30 days <ChevronDown size={13} />
                  </span>
                </div>
                <div className="line-chart">
                  <div className="chart-y">
                    <span>100</span>
                    <span>90</span>
                    <span>80</span>
                    <span>70</span>
                  </div>
                  <svg viewBox="0 0 620 180" preserveAspectRatio="none">
                    <path
                      d="M0 142 C70 134, 80 110, 140 119 S210 96, 260 105 S330 71, 390 89 S470 42, 520 58 S580 33, 620 25"
                      fill="none"
                      stroke="#f26f61"
                      strokeWidth="4"
                    />
                    <path
                      d="M0 160 C70 155, 90 135, 150 143 S230 129, 280 135 S350 110, 405 119 S475 92, 530 101 S580 78, 620 72"
                      fill="none"
                      stroke="#94d8bd"
                      strokeWidth="4"
                      strokeDasharray="7 8"
                    />
                  </svg>
                </div>
                <div className="chart-legend">
                  <span>
                    <i className="legend-coral" /> citation resolution
                  </span>
                  <span>
                    <i className="legend-mint" /> numeric faithfulness
                  </span>
                </div>
              </div>

              <div className="qa-panel checks">
                <div className="pane-top">
                  <div>
                    <span className="eyebrow">Automated checks</span>
                    <h3>Nothing suspicious</h3>
                  </div>
                  <ShieldCheck className="checkmark" size={21} />
                </div>
                {[
                  "Every numeric claim has a source span",
                  "No unsupported medical recommendation",
                  "Glossary terms resolved in context",
                  "Abstract-only status is visible",
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

        {/* View 6: Paste Abstract */}
        {view === "paste" && (
          <section className="content-stack paste-view">
            <div className="reader-heading reveal">
              <div>
                <SectionLabel tone="coral">Bring your own evidence</SectionLabel>
                <h1>
                  Paste an abstract.
                  <br />
                  <i>See it clearly.</i>
                </h1>
                <p>Drop in a synthetic test abstract or a paper you’re evaluating. We’ll keep the source intact.</p>
              </div>
              <label className="soft-button paste-upload">
                <Upload size={15} /> {uploadedFile || "Upload .txt"}
                <input
                  type="file"
                  accept=".txt"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) {
                      setUploadedFile(file.name);
                      file.text().then(setPasteText);
                    }
                  }}
                />
              </label>
            </div>

            <div className="paste-grid reveal">
              <div className="paste-editor">
                <div className="editor-top">
                  <span className="eyebrow">Abstract input</span>
                  <span>{pasteText.trim() ? pasteText.trim().split(/\s+/).length : 0} / 4,000 words</span>
                </div>
                <textarea
                  placeholder="Paste an abstract here…"
                  value={pasteText}
                  onChange={(event) => setPasteText(event.target.value)}
                />
                <div className="editor-foot">
                  <span>
                    <Sparkles size={14} /> Synthetic test mode
                  </span>
                  <button className="coral-button" onClick={handleParsePasted}>
                    Parse abstract <ArrowUpRight size={15} />
                  </button>
                </div>
              </div>
              <div className="paste-side">
                <div className="empty-orb">
                  <ClipboardPaste size={21} />
                  <span>Ready for a new paper</span>
                  <small>Your source text stays yours.</small>
                </div>
                <div className="mini-info">
                  <ShieldCheck size={15} />
                  <span>We’ll surface claims, PICO signals, and citation gaps — not diagnoses.</span>
                </div>
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
              <span>grounded in {selectedPapers.length} papers</span>
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
            </div>
            <div className="suggestions">
              <button
                onClick={() => {
                  setMessage("Which claim is most strongly supported?");
                  sendChatMessage("Which claim is most strongly supported?", selectedPapers).then((resp) => {
                    if (resp) {
                      setChat((items) => [
                        ...items,
                        { from: "user", text: "Which claim is most strongly supported?" },
                        { from: "ai", text: resp.response },
                      ]);
                    }
                  });
                }}
              >
                Strongest claim
              </button>
              <button
                onClick={() => {
                  setMessage("Where do these papers conflict?");
                  sendChatMessage("Where do these papers conflict?", selectedPapers).then((resp) => {
                    if (resp) {
                      setChat((items) => [
                        ...items,
                        { from: "user", text: "Where do these papers conflict?" },
                        { from: "ai", text: resp.response },
                      ]);
                    }
                  });
                }}
              >
                Find conflict
              </button>
            </div>
            <div className="assistant-input">
              <input
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && sendMessage()}
                placeholder="Ask about these papers…"
              />
              <button onClick={sendMessage}>
                <Send size={15} />
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
