# Bradford Council AI Chatbot

An AI-powered conversational assistant that helps Bradford Council residents access and navigate local government services. Citizens can ask questions in plain English and receive accurate, structured guidance — including live data lookups, multi-step flows, and RAG-enhanced answers.

---

## Services Covered

| Service | Capabilities |
|---------|-------------|
| **Bin Collection** | Next collection dates (live lookup), recycling guidance, missed bins, assisted collections, service disruptions |
| **Council Tax** | Band lookup (live), annual charges, payment methods, discounts, exemptions, arrears help, appeals |
| **Benefits Support** | Housing Benefit eligibility, CTR applications, DHP, benefits calculator, change of circumstances, MyInfo account |
| **Blue Badge** | Eligibility wizard, application guidance, renewal reminder flow, parking rules, replacement, misuse reporting |
| **Library Services** | Library finder (by name or postcode), opening hours, membership, catalogue, eBooks, home library service |
| **School Admissions** | Primary/secondary admissions, key dates, appeals, in-year transfers, criteria, admissions process |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · FastAPI · Uvicorn |
| Frontend | React 18 · Tailwind CSS |
| Intent Classification | Token-overlap classifier (bigram scoring over ~800 labelled examples) |
| RAG | Keyword + semantic search → OpenAI `gpt-4o-mini` answer enhancement |
| Embeddings | OpenAI `text-embedding-3-small` · FAISS · auto-cached to `.embedding_cache/` |
| Live Data | Bradford Council website scraping (bin dates, council tax bands) |
| External Links | Turn2Us benefits calculator · GOV.UK Blue Badge portal |

---

## Sharing With Others (ngrok)

Run the chatbot locally and share a public link with up to 10 people:

```bash
# One-time setup — free ngrok account at https://ngrok.com
pip install pyngrok
# Add NGROK_AUTHTOKEN=<your-token> to your .env file

# Then each time you want to share:
python start_public.py
```

The script builds the frontend, starts the backend, opens a public tunnel, and prints a URL like `https://abc123.ngrok-free.app` that anyone can open in their browser. The link stays live as long as the terminal window is open.

---

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# .venv\Scripts\activate.bat       # Windows CMD

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env and add your OpenAI API key

# 4. Install frontend dependencies
cd frontend && npm install && cd ..

# 5. Start backend (terminal 1)
python main.py

# 6. Start frontend (terminal 2)
cd frontend && npm start
```

Backend runs at `http://127.0.0.1:8000` — frontend at `http://localhost:3000`.

---

## Project Structure

```
AI Agent/
├── main.py                          Entry point — starts FastAPI via Uvicorn
├── requirements.txt                 Python dependencies
├── .env                             Secret keys (not committed)
├── .env.example                     Safe template — copy to .env
│
├── backend/
│   ├── api.py                       FastAPI app, /chat endpoint, CORS, startup cache build
│   ├── chat_config.py               SERVICE_OPTIONS, INTENT_GROUPS, INTENT_LABELS, thresholds
│   ├── chat_helpers.py              normalize_text, menu text helpers
│   ├── dialogue_manager.py          Loads and runs structured JSON dialogue flows
│   ├── intent_classifier.py         Token-overlap bigram intent classifier
│   ├── openai_client.py             OpenAI client initialisation (reads OPENAI_API_KEY)
│   ├── rag_service.py               FAQ retrieval: keyword match → embedding re-rank
│   │
│   ├── core/
│   │   └── session_manager.py       Per-session state dict + JSONL chat log writer
│   │
│   ├── council_connectors/          Live data — web scraping
│   │   ├── bin_connector.py         Bradford Council bin date scraper (multi-step form)
│   │   ├── bin_http.py              HTTP session helpers for bin connector
│   │   ├── bin_local.py             Local bin schedule fallback + postcode normaliser
│   │   ├── bin_lookup.py            Orchestrates bin date lookup flow
│   │   ├── bin_parsers.py           HTML parsers for bin schedule pages
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
│   │   ├── blue_badge_handler.py    Blue Badge renewal reminder + eligibility wizard
│   │   ├── library_handler.py       Library finder flow (name / postcode / filters)
│   │   └── school_handler.py        School finder flow
│   │
│   ├── llm/                         LLM integration
│   │   ├── prompts.py               Service-specific prompt templates for gpt-4o-mini
│   │   └── response_enhancer.py     Enhances RAG answers with LLM paraphrasing
│   │
│   ├── services/
│   │   ├── chat_engine.py           Main router — ties all handlers together
│   │   ├── bin_guidance_service.py  Recycling guidance lookup
│   │   └── paraphrase_service.py    OpenAI-based answer paraphrasing
│   │
│   └── utils/
│       ├── benefits_formatter.py    Formats benefits answers as HTML cards
│       ├── bin_formatter.py         Formats bin schedule HTML cards
│       ├── council_tax_formatter.py Formats council tax HTML cards
│       ├── library_formatter.py     Formats library info HTML cards
│       ├── school_formatter.py      Formats school info HTML cards
│       ├── postcode_distance.py     Postcode → lat/lng distance sorting
│       └── response_builder.py      Builds reply dicts returned to frontend
│
├── frontend/
│   ├── public/                      Static assets (favicon, index.html, robots.txt)
│   └── src/
│       ├── App.js                   Root component
│       └── components/
│           └── ChatModal.jsx        Chat UI (bubbles, input, option cards)
│
├── datasets/                        Training data + FAQ content
│   ├── bin_collection/              bin_intents.json · bin_faq.json · bin_dialogue.json
│   │                                bin_recycling_guidance.json · bin_lookup.json · eval_set.jsonl
│   ├── council_tax/                 council_tax_intents.json · council_tax_faq.json
│   │                                council_tax_dialogue.json · council_tax_lookup.json · eval_set.jsonl
│   ├── benefits_support/            benefits_intents.json · benefits_faq.json
│   │                                benefits_dialogue.json · eval_set.jsonl
│   ├── blue_Badge/                  blue_badge_intents.json · blue_badge_faq.json · eval_set.jsonl
│   ├── libraries/                   library_intents.json · library_faq.json
│   │                                libraries_list.json · eval_set.jsonl
│   └── school_admissions/           school_admissions_intents.json · school_admissions_faq.json
│                                    schools_list.json · eval_set.jsonl
│
├── scripts/
│   ├── train_model.py               Retrains intent classifier from datasets/
│   ├── evaluate_intent_model.py     Full evaluation suite → evaluation/ folder
│   └── generate_eval_charts.py      Generates poster-ready PNG charts
│
├── models/                          Auto-generated (run scripts/train_model.py)
│   └── intent_classifier.joblib
│
├── evaluation/                      Auto-generated (run scripts/evaluate_intent_model.py)
│   ├── evaluation_report.html · classification_report.txt
│   ├── per_intent_summary.csv · per_service_summary.csv
│   └── confusion_matrix.png · per_intent_accuracy.png · confidence_histogram.png
│
├── .embedding_cache/                Auto-generated FAISS caches (one per service)
├── chat_logs/                       Auto-generated per-session JSONL logs
└── docs/
    ├── PROJECT_OVERVIEW.txt         Architecture and design documentation
    ├── COMMANDS.txt                 All dev commands in one place
    └── evaluation/
        ├── evaluation_results.md    Full evaluation write-up (22 scenarios)
        ├── evaluation_poster.md     Compact evaluation tables for poster
        ├── eval_by_service.png      Stacked bar chart by service
        ├── eval_metrics.png         Horizontal bar — key metrics
        └── eval_scenarios.png       Colour-coded scenario grid
```

---

## Evaluation Results

Intent classifier accuracy on held-out eval sets (328 examples, 61 intents):

| Metric | Score |
|--------|-------|
| Top-1 Accuracy | **95.1%** |
| Macro F1 | 0.94 |
| Weighted F1 | 0.95 |

End-to-end chatbot evaluation (22 manual test scenarios):

| Metric | Score |
|--------|-------|
| Overall Pass Rate | 77% (17/22) |
| Intent Classification | 86% |
| Service Routing | 91% |
| RAG Answer Accuracy | 89% |
| Multi-turn Flow Completion | 71% |

Run `python scripts/generate_eval_charts.py` to regenerate visual charts.

---

## Environment Variables

```
OPENAI_API_KEY=sk-...   Required for RAG enhancement and embeddings
```

Copy `.env.example` to `.env` and add your key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
