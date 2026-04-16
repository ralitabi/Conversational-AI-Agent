# System Evaluation — Bradford Council Chatbot

---

### Key Metrics  *(n = 22 test scenarios, April 2026)*

| | |
|---|---|
| **Overall Pass Rate** | **77%** (17/22) |
| Intent Classification | 86% (19/22) |
| Multi-turn Flow Completion | 71% (5/7) |
| RAG Answer Accuracy | 89% (8/9) |
| Service Routing | 91% (20/22) |

---

### Results by Service

| Service | Tests | ✅ Pass | ⚠️ Partial | ❌ Fail | Rate |
|---------|:-----:|:------:|:---------:|:------:|:----:|
| Council Tax | 2 | 2 | 0 | 0 | 100% |
| Bin Collection | 4 | 3 | 1 | 0 | 75% |
| Benefits Support | 6 | 4 | 0 | 2 | 67% |
| Library Services | 9 | 7 | 1 | 1 | 78% |
| **Overall** | **22** | **17** | **2** | **3** | **77%** |

---

### Test Scenarios at a Glance

| # | Service | Query | Outcome |
|---|---------|-------|---------|
| 1 | Library | How do I join? | ✅ Correct answer + steps |
| 2 | Library | Can I search books online? | ✅ Catalogue link + steps |
| 3 | Library | Opening hours? | ⚠️ No data (since fixed) |
| 4 | Library | Find library near BD1 1HY | ✅ 6 libraries returned |
| 5 | Library | Find library in Bingley | ✅ Full library card shown |
| 6 | Library | Select result → pick "1" | ❌ Intent misfired (fixed) |
| 7 | Library | Home Library Service? | ✅ Correct with contact |
| 8 | Library | eBooks available? | ✅ BorrowBox guidance |
| 9 | Library | Library finder + postcode skip | ✅ List shown correctly |
| 10 | Bin | What bin for cardboard? | ✅ Blue bin identified |
| 11 | Bin | When is my bin collected? | ✅ Prompted for postcode |
| 12 | Bin | Postcode entered directly | ⚠️ Extra confirmation step |
| 13 | Bin | Service disruption query | ✅ Correct intent routing |
| 14 | Council Tax | How does council tax work? | ✅ Bradford-specific info |
| 15 | Council Tax | What is my CT band? + postcode | ✅ Address list returned |
| 16 | Benefits | Can I get housing benefit? (5-turn) | ✅ Full flow completed |
| 17 | Benefits | Benefits flow: pensioner + private rent | ✅ Correct eligibility result |
| 18 | Benefits | "benefits calculator" inside service | ✅ Flow started correctly |
| 19 | Benefits | Full calculator flow to result | ✅ Correct benefit overview |
| 20 | Benefits | "benefits calculator" at root menu | ❌ Menu re-shown |
| 21 | Benefits | "benefits" at root menu | ❌ Partial match not accepted |
| 22 | Benefits | Out-of-order inputs at root | ✅ Consistent rejection |

---

### Failure Analysis

| Root Cause | Count | Resolution |
|------------|:-----:|-----------|
| Exact service name required at root menu | 2 | Known design decision |
| Routing bug after library result selection | 1 | Fixed post-test |
| Missing FAQ data (library hours) | 1 | FAQ entry added |

---

> **Methodology:** Manual black-box testing via the chat interface. Each scenario was tested end-to-end. Pass = fully correct response. Partial = response reached but incomplete/inaccurate. Fail = wrong intent, error, or no useful response.
