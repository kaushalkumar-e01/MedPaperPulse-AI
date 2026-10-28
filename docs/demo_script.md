# MedPaperPulse-AI (MedLit Explorer) — Clinical Demo Walkthrough Script

**Author**: Person 5 (Evaluation & Documentation)  
**Target Duration**: 4–5 minutes  
**Format**: Screen Recording + Narration Walkthrough  
**Recording Status**: **Script & Checklist Ready (Video recording remains to be performed)**

---

## Demo Overview & Script Flow

| Step | Time | UI View / Action | Narration & Speaking Points | Expected Visible Behavior |
|---|---|---|---|---|
| **1. Problem Statement** | 0:00 - 0:30 | Browser Home (`streamlit run streamlit_app.py`) | *"Clinicians and medical researchers are overwhelmed by thousands of new PubMed abstracts published weekly. Conventional AI summarizers frequently hallucinate numerical endpoints, invent p-values, or overlook scientific uncertainty. MedLit Explorer provides an inspectable, evidence-grounded literature cockpit."* | Brand mark `medlit• Clinical AI` displayed with sync badge. |
| **2. Explore & Search Literature** | 0:30 - 1:00 | "🔍 Explore Literature" View | *"Let's examine how the platform processes recent clinical literature. We navigate to the Literature Explorer to view retrieved PubMed papers, study design badges, and publication metrics."* | Filter pills (RCTs, Meta-analyses, Clinical trials) and paper cards visible. |
| **3. Evidence Workspace & PICO** | 1:00 - 1:45 | "📖 Evidence Workspace" View | *"In the Evidence Workspace, the screen splits into two synchronized panes: source text on the left and structured AI synthesis on the right. Notice how the PICO framework breaks down Population, Intervention, Comparison, and Outcome badges explicitly."* | Two-column layout: sentence-tagged source abstract `[S1]`, `[S2]` on left; PICO badges and structured synthesis on right. |
| **4. Citation Traceability & Inspection** | 1:45 - 2:30 | Click `[S3]` in AI Synthesis | *"Notice this claim: 'Compared with a retrieval baseline, the model improved alignment by 18.6 percentage points'. When we click citation `[S3]`, the system immediately highlights the exact source sentence supporting that quantitative result."* | Interactive highlight triggers on left pane displaying passage `[S3]`. |
| **5. Synthetic Edge Case (Missing Results)** | 2:30 - 3:15 | "📋 Paste Abstract" View -> Paste `SYNTH-01` | *"A major risk in clinical AI is hallucinating results for ongoing trials. Here, we paste `SYNTH-01`, an adaptive trial protocol where enrollment is underway but outcomes are unanalyzed. Notice that instead of inventing mortality figures, the system honestly reports: 'Not reported in the abstract.'"* | PICO outcome and findings explicitly state `"Not reported in the abstract."`. |
| **6. Cross-Paper Comparison Matrix** | 3:15 - 3:45 | "⚖️ Compare Papers" View | *"When synthesizing evidence across multiple studies, the comparison matrix lines up study design, patient sample size, primary endpoints, and hazard ratios side-by-side."* | Multi-paper comparison matrix displaying comparative clinical metrics. |
| **7. Quality & Evaluation Lab** | 3:45 - 4:15 | "🛡️ Evaluation Lab" View | *"Quality cannot be assumed; it must be rigorously measured. In our automated evaluation benchmark across 16 real and synthetic abstracts: Citation Resolution achieved 100%, Numeric Faithfulness reached 100%, and Required-Field Presence reached 100%."* | Evaluation benchmark charts, metric summary, and dual-reviewer rubric displayed. |
| **8. Limitations & Clinical Disclaimer** | 4:15 - 4:45 | Footer / About section | *"MedLit Explorer summarizes abstract-level data and is designed strictly as an educational and research companion. It is not a clinical diagnostic device or treatment recommendation tool."* | Prominent clinical disclaimer visible. |

---

## Pre-Recording Checklist

- [ ] Python environment active with all dependencies installed.
- [ ] Local Streamlit server running: `streamlit run streamlit_app.py --server.port 8501`.
- [ ] Browser window sized to standard 1080p (1920x1080) at 100% zoom.
- [ ] Clean browser session with no extraneous tabs or bookmarks visible.
- [ ] Audio input configured and microphone level checked.
- [ ] Synthetic test abstracts from `data/test_set.json` copied to clipboard for quick paste.

---

## Post-Recording Verification Checklist

- [ ] Audio narration is clear, intelligible, and synchronized with screen actions.
- [ ] Video resolution is sharp (minimum 1080p, 30fps).
- [ ] Citation click interaction (`[S3]`) clearly highlighted the source sentence.
- [ ] Honest missing-information indicator `"Not reported in the abstract."` is prominently demonstrated.
- [ ] Clinical disclaimer is clearly stated.
- [ ] Video duration is within the 4–5 minute limit.
