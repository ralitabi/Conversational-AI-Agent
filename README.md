# Bradford Council Conversational AI Agent

## Table of Contents
- [Project Overview](#project-overview)
- [Objectives](#objectives)
- [System Architecture](#system-architecture)
- [Architecture Diagram](#architecture-diagram)
- [Functional Scope](#functional-scope)
- [Technologies Used](#technologies-used)
- [Implementation Details](#implementation-details)
- [Folder Structure](#folder-structure)
- [Evaluation](#evaluation)
- [Limitations](#limitations)
- [Future Work](#future-work)
- [Reproducibility](#reproducibility)
- [References](#references)
- [Author](#author)

---

## Project Overview

This project presents the design and development of an AI-driven conversational agent aimed at supporting citizens in accessing local government services provided by Bradford Council.

The system enables users to interact using natural language and receive structured, context-aware responses. It integrates **intent classification, Retrieval-Augmented Generation (RAG), and live data retrieval** to ensure accuracy and usability across six core service areas.

---

## Objectives

- Develop an intelligent chatbot for council service queries
- Improve accessibility of public services through conversational AI
- Combine rule-based systems, machine learning, and large language models
- Evaluate performance using real-world scenarios and measurable metrics

---

## System Architecture

The system follows a modular layered architecture:

- **Intent Classification Layer** — Token-overlap bigram similarity model
- **Dialogue Management Layer** — Multi-turn structured conversation flows
- **Retrieval-Augmented Generation (RAG) Layer** — Semantic and keyword retrieval with LLM enhancement
- **Live Data Integration Layer** — Web scraping for real-time information
- **Frontend User Interface** — React-based mobile-responsive chat UI

---

## Architecture Diagram

<div align="center">

```
                    User Input
                        │
                        ▼
            Frontend (React Interface)
                        │
                        ▼
               FastAPI Backend
                        │
                        ▼
           Intent Classification
        (Token-based similarity model)
                        │
                        ▼
        ┌───────────────────────────────┐
        │         Routing Layer         │
        ├───────────────┬───────────────┤
        │ Dialogue Flow │  RAG System   │
        │  (JSON Logic) │ (FAISS + LLM) │
        └───────────────┴───────────────┘
                        │
                        ▼
           Live Data Connectors
              (Web Scraping)
                        │
                        ▼
        Response Enhancement (LLM)
                        │
                        ▼
        Structured Response Output
                        │
                        ▼
          Frontend Display to User
```

</div>

---

## Functional Scope

The system supports the following services:

| Service | Capabilities |
|---------|-------------|
| **Bin Collection** | Live collection dates, recycling guidance, missed bins, assisted collections |
| **Council Tax** | Band lookup, annual charges, payment methods, discounts, exemptions |
| **Benefits Support** | Housing Benefit eligibility, CTR applications, benefits calculator |
| **Blue Badge** | Eligibility wizard, application guidance, renewal flow, parking rules |
| **Library Services** | Library finder, opening hours, membership, catalogue, eBooks |
| **School Admissions** | Primary/secondary admissions, key dates, appeals, in-year transfers |

Each service includes FAQ-based responses and guided multi-step workflows.

---

## Technologies Used

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | React 18, Tailwind CSS |
| AI Models | OpenAI gpt-4o-mini |
| Embeddings | text-embedding-3-small, FAISS |
| Data Sources | Bradford Council, Turn2Us, GOV.UK |

---

## Implementation Details

The system integrates multiple components:

- Intent classification using token-overlap bigram similarity (61 intents, 800+ training examples)
- Semantic retrieval using FAISS vector embeddings, cached at startup for fast responses
- Retrieval-Augmented Generation — GPT-4o-mini reformats verified FAQ answers with bold, links, and phone numbers
- Session-based dialogue management with multi-turn context preservation
- Web scraping connectors for live bin dates and council tax band lookups
- Mobile-responsive UI with tap-to-call phone links and clickable URLs

---

## Folder Structure

```
AI-Agent/
│
├── backend/                 # Core backend logic and API
│   ├── handlers/            # Service-specific conversation logic
│   ├── council_connectors/  # Web scraping for live data
│   ├── embeddings/          # FAISS vector pipeline
│   ├── llm/                 # Prompt templates and LLM enhancement
│   ├── services/            # Main chat engine and routing
│   └── utils/               # Formatters and response builders
│
├── frontend/                # React user interface
│   ├── src/                 # Components, data, styles
│   └── public/              # Static assets
│
├── datasets/                # Training data and FAQ content
├── models/                  # Trained intent classifier
├── docs/                    # Project docs and evaluation reports
├── scripts/                 # Training and evaluation scripts
│
├── main.py                  # Application entry point
├── start_public.py          # Share publicly via ngrok
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variable template
```

---

## Evaluation

### Intent Classification (328 examples, 61 intents)

| Metric | Score |
|--------|-------|
| Accuracy | **95.1%** |
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
| Bin Collection | 4 | 4 | 0 | 0 | **100%** |
| Council Tax | 2 | 2 | 0 | 0 | **100%** |
| Benefits Support | 6 | 6 | 0 | 0 | **100%** |
| Library Services | 9 | 8 | 1 | 0 | **89%** |
| Cross-service / Routing | 1 | 1 | 0 | 0 | **100%** |
| **Total** | **22** | **21** | **1** | **0** | **91%** |

---

## Limitations

- Confusion may occur between semantically similar queries across services
- Live data lookups depend on Bradford Council's website structure remaining stable
- LLM enhancement adds latency for RAG-enhanced responses
- Session state is in-memory only — not persisted across server restarts

---

## Future Work

- Expand training datasets and balance coverage across all 61 intents
- Add persistent session storage for cross-session memory
- Introduce voice-based interaction support
- Extend system to additional council services (parking, planning, housing)
- Deploy to a cloud platform for always-on public availability

---

## Reproducibility

```bash
git clone https://github.com/ralitabi/Conversational-AI-Agent.git
cd Conversational-AI-Agent

python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# .venv\Scripts\activate.bat       # Windows CMD

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key to .env

python main.py
```

In a second terminal:

```bash
cd frontend
npm install
npm start
```

Backend runs at `http://127.0.0.1:8000` — frontend at `http://localhost:3000`.

To share with others via a public URL:

```bash
python start_public.py
```

---

## References

- [Bradford Council](https://www.bradford.gov.uk)
- [OpenAI](https://platform.openai.com)
- [FAISS](https://github.com/facebookresearch/faiss)
- [React](https://react.dev)
- [FastAPI](https://fastapi.tiangolo.com)
- [Turn2Us](https://www.turn2us.org.uk)
- [GOV.UK Blue Badge](https://www.gov.uk/apply-blue-badge)

---

## Author

**Raja Ali Tabish**  
BSc Computer Science — University of Bradford
