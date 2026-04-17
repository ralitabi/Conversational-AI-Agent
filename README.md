# 🤖 Bradford Council Conversational AI Agent

## 📑 Table of Contents
- [Project Overview](#-project-overview)
- [Objectives](#-objectives)
- [System Architecture](#-system-architecture)
- [Functional Scope](#-functional-scope)
- [Technologies Used](#-technologies-used)
- [Implementation Details](#-implementation-details)
- [Folder Structure](#-folder-structure)
- [Evaluation](#-evaluation)
- [Limitations](#-limitations)
- [Future Work](#-future-work)
- [Reproducibility](#-reproducibility)
- [References](#-references)
- [Author](#-author)

---

## 📌 Project Overview

This project presents the design and development of an AI-driven conversational agent aimed at supporting citizens in accessing local government services provided by Bradford Council.

The system enables users to interact using natural language and receive structured, context-aware responses. It integrates **intent classification, Retrieval-Augmented Generation (RAG), and live data retrieval** to ensure accuracy and usability across six core service areas.

---

## 🎯 Objectives

- Develop an intelligent chatbot for council service queries
- Improve accessibility of public services through conversational AI
- Combine rule-based systems, machine learning, and large language models
- Evaluate performance using real-world scenarios and measurable metrics

---

## 🧠 System Architecture

The system follows a modular, layered architecture:

- **Intent Classification Layer** — Bigram token-overlap similarity model (61 intents, 800+ training examples)
- **Dialogue Manager** — Multi-turn structured conversation flows driven by JSON dialogue definitions
- **RAG Pipeline** — Keyword + semantic retrieval (FAISS) with GPT-4o-mini response enhancement
- **Live Data Layer** — Web scraping connectors for real-time bin dates and council tax band lookups
- **Frontend Interface** — React-based chat UI with mobile-responsive design

---

## 🧩 Functional Scope

Six council service areas are fully supported:

| Service | Capabilities |
|---------|-------------|
| **Bin Collection** | Live collection date lookup, recycling guidance, missed bins, assisted collections |
| **Council Tax** | Band lookup (live), annual charges, payment methods, discounts, exemptions, arrears help |
| **Benefits Support** | Housing Benefit eligibility, CTR applications, DHP, benefits calculator, change of circumstances |
| **Blue Badge** | Eligibility wizard, application guidance, renewal flow, parking rules, replacement |
| **Library Services** | Library finder (name/postcode), opening hours, membership, catalogue, eBooks, home delivery |
| **School Admissions** | Primary/secondary admissions, key dates, appeals, in-year transfers, admissions criteria |

Each service supports both **FAQ retrieval** and **guided multi-turn workflows**.

---

## 🛠️ Technologies Used

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · FastAPI · Uvicorn |
| Frontend | React 18 · Tailwind CSS |
| Intent Classification | Token-overlap bigram classifier (~800 labelled examples, 61 intents) |
| RAG | Keyword + semantic search → OpenAI `gpt-4o-mini` enhancement |
| Embeddings | OpenAI `text-embedding-3-small` · FAISS · auto-cached |
| Live Data | Bradford Council website scraping (bin dates, council tax bands) |
| External Links | Turn2Us benefits calculator · GOV.UK Blue Badge portal |

---

## ⚙️ Implementation Details

Key components and design decisions:

- **Custom intent classifier** using token overlap and bigram scoring — lightweight, no GPU required
- **Vector search with FAISS** for semantic FAQ retrieval, cached at startup for speed
- **LLM-based response enhancement** — GPT-4o-mini reformats verified FAQ answers with bold, links, and phone numbers
- **Session state management** — per-session flow state with multi-turn context preservation
- **Web scraping connectors** — live bin collection dates and council tax band lookups via Bradford Council's public pages
- **Service aliases** — 37 normalised input variants ensure flexible natural language routing
- **Mobile-first UI** — chat panel slides up as a bottom sheet on mobile with full tap-to-call support

---

## 🗂️ Folder Structure

```
AI Agent/
│
├── backend/
│   ├── api.py                       FastAPI app, /chat endpoint, CORS, startup cache
│   ├── chat_config.py               SERVICE_OPTIONS, INTENT_GROUPS, INTENT_LABELS
│   ├── chat_helpers.py              normalize_text, greeting detection, menu helpers
│   ├── dialogue_manager.py          Loads and runs structured JSON dialogue flows
│   ├── intent_classifier.py         Token-overlap bigram intent classifier
│   ├── rag_service.py               FAQ retrieval: keyword match → embedding re-rank
│   │
│   ├── core/
│   │   └── session_manager.py       Per-session state + JSONL chat log writer
│   │
│   ├── council_connectors/          Live data — web scraping
│   │   ├── bin_connector.py         Bradford bin date scraper (multi-step form)
│   │   ├── bin_lookup.py            Orchestrates bin date lookup flow
│   │   ├── council_tax_connector.py VOA band lookup + Bradford charge table
│   │   ├── library_connector.py     Bradford library data (JSON-backed)
│   │   ├── school_connector.py      Bradford school finder (JSON-backed)
│   │   └── benefits_connector.py    Turn2Us link builder + eligibility text
│   │
│   ├── embeddings/                  Vector embedding pipeline
│   │   ├── embedder.py              Calls OpenAI text-embedding-3-small
│   │   ├── embedding_store.py       FAISS index per service, auto-loads from cache
│   │   └── cache_builder.py         Pre-builds all embedding caches at startup
│   │
│   ├── handlers/                    Conversational logic — one file per domain
│   │   ├── intent_handler.py        Intent detection, confidence routing, flow guards
│   │   ├── intent_keyword_matcher.py  Keyword phrase overrides for all 6 services
│   │   ├── dialogue_handler.py      Routes intent → dialogue / live lookup / RAG
│   │   ├── bin_handler.py           Multi-step bin date lookup flow
│   │   ├── council_tax_band_handler.py  Council tax band + payment flow
│   │   ├── benefits_handler.py      Benefits eligibility calculator flow
│   │   ├── blue_badge_handler.py    Blue Badge renewal + eligibility wizard
│   │   ├── library_handler.py       Library finder flow (name / postcode / filters)
│   │   └── school_handler.py        School finder flow
│   │
│   ├── llm/
│   │   ├── prompts.py               Service-specific prompt templates for gpt-4o-mini
│   │   └── response_enhancer.py     Enhances RAG answers with LLM paraphrasing
│   │
│   ├── services/
│   │   ├── chat_engine.py           Main router — ties all handlers together
│   │   └── bin_guidance_service.py  Recycling guidance lookup
│   │
│   └── utils/
│       ├── benefits_formatter.py    Formats benefits answers as HTML cards
│       ├── bin_formatter.py         Formats bin schedule HTML cards
│       ├── council_tax_formatter.py Formats council tax HTML cards
│       ├── library_formatter.py     Formats library info HTML cards
│       ├── school_formatter.py      Formats school info HTML cards
│       └── response_builder.py      Builds reply dicts returned to frontend
│
├── frontend/
│   ├── public/                      Static assets
│   └── src/
│       ├── App.js                   Root component — Bradford Council homepage
│       ├── data/homeData.js         Service tiles, quick actions, starter queries
│       └── components/
│           ├── ChatModal.jsx        Chat UI (bubbles, input, option cards)
│           ├── BenefitsCalculatorCard.jsx
│           └── FeedbackStars.jsx
│
├── datasets/                        Training data + FAQ content (6 services)
├── scripts/                         train_model.py · evaluate_intent_model.py · generate_eval_charts.py
├── models/                          Auto-generated intent_classifier.joblib
├── docs/
│   ├── PROJECT_OVERVIEW.txt
│   ├── COMMANDS.txt
│   └── evaluation/                  evaluation_results.md · charts (PNG)
│
├── main.py                          Entry point — starts FastAPI via Uvicorn
├── start_public.py                  Share via ngrok (up to 10 simultaneous users)
├── requirements.txt
└── .env.example
```

---

## 📊 Evaluation

### Intent Classification (328 examples, 61 intents)

| Metric | Score |
|--------|-------|
| Top-1 Accuracy | **95.1%** |
| Macro F1 | **0.94** |
| Weighted F1 | **0.95** |

### End-to-End Performance (22 manual test scenarios)

| Metric | Score |
|--------|-------|
| **Overall Success Rate** | **91% (20/22)** |
| Intent Detection | 86% |
| Service Routing | 96% |
| RAG Answer Accuracy | 89% |
| Multi-turn Flow Completion | 86% |

### Per-Service Results

| Service | Tests | Pass | Partial | Fail | Pass Rate |
|---------|-------|------|---------|------|-----------|
| Library Services | 9 | 8 | 1 | 0 | **89%** |
| Bin Collection | 4 | 4 | 0 | 0 | **100%** |
| Council Tax | 2 | 2 | 0 | 0 | **100%** |
| Benefits Support | 6 | 6 | 0 | 0 | **100%** |
| Cross-service / Routing | 1 | 1 | 0 | 0 | **100%** |
| **Total** | **22** | **20** | **1** | **0** | **91%** |

### Improvements Applied Post-Initial Evaluation

| Issue | Fix Applied |
|-------|------------|
| "benefits" / "benefits calculator" at root menu not routed | Added 37 service name aliases to SERVICE_OPTIONS |
| Library flow lost after detail card shown | Kept library context active after selection |
| Direct postcode at bin service triggered confirmation step | Auto-detect UK postcodes, skip to lookup |
| Responses took 2–4 seconds | Frontend delays 1–2s → 120–300ms; LLM tokens reduced |

---

## ⚠️ Limitations

- Intent confusion may occur between semantically similar queries across services
- Live data lookups depend on Bradford Council's website structure remaining stable
- LLM enhancement adds ~500ms latency for RAG-enhanced responses
- Session state is in-memory only — not persisted across server restarts
- Ngrok free tier allows up to 10 concurrent users for public sharing

---

## 🔮 Future Work

- Expand training datasets and balance across all 61 intents
- Add persistent session storage (Redis or database-backed)
- Introduce voice interaction support
- Extend coverage to additional council services (parking, planning, housing)
- Deploy to a cloud platform (Railway / Render) for always-on availability
- Add authentication for personalised service lookups

---

## 🧪 Reproducibility

```bash
git clone https://github.com/ralitabi/Conversational-AI-Agent.git
cd Conversational-AI-Agent

# Create and activate virtual environment
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# .venv\Scripts\activate.bat       # Windows CMD

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your OpenAI API key

# Start backend (terminal 1)
python main.py

# Install and start frontend (terminal 2)
cd frontend && npm install && npm start
```

Backend runs at `http://127.0.0.1:8000` — frontend at `http://localhost:3000`.

To share with up to 10 people via a public URL:

```bash
python start_public.py
```

---

## 📚 References

- [Bradford Council](https://www.bradford.gov.uk)
- [OpenAI API](https://platform.openai.com)
- [FAISS — Facebook AI Similarity Search](https://github.com/facebookresearch/faiss)
- [React](https://react.dev)
- [FastAPI](https://fastapi.tiangolo.com)
- [Turn2Us Benefits Calculator](https://www.turn2us.org.uk)
- [GOV.UK Blue Badge](https://www.gov.uk/apply-blue-badge)

---

## 👤 Author

**Raja Ali Tabish**

BSc Computer Science — University of Bradford
