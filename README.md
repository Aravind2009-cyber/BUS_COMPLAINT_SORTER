# Bus Complaint Sorter
> **CIT AI-Native Engineering Programme · Semester 1 · Assessment 5 (Capstone Project)**  
> **Domain:** College Transportation Administration

---

## 📌 Project Overview
The **Bus Complaint Sorter** is a console-based Python triage tool designed for college bus operations. It reads raw student complaints, extracts stated route numbers, classifies complaints into operational categories, and elevates critical safety hazards (rash driving, footboard travel, broken doors, brake failures) directly to the Transport Officer.

The tool acts strictly as a **decision-support filter**—it never contacts drivers, never assigns fault, and never makes autonomous disciplinary decisions.

---

## 🏗️ Architecture & Pipeline Flow

```
[complaints.csv] + [routes.csv]
            │
            ▼
    [load_complaints()] & [load_routes()]
            │
            ▼
        [classify()]
            │
            ├──► LLM Call (5-Role System Prompt)
            ├──► Schema Validation (is_valid())
            │       └── Failed? Retry 1x ──► Fallback: 'needs_manual_review'
            │
            └──► Deterministic Python Route Check (verify_route())
                    ├── Route in routes.csv?
                    └── Route integer in raw text?
                            └── No? Route -> null
            │
            ▼
    [write_reports()]
            ├── outputs/results.csv   (All processed complaints)
            ├── outputs/urgent.csv    (Transport Officer Safety Queue)
            └── outputs/summary.txt   (Category counts, route frequency, safety list)
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.15)
- Standard library modules: `csv`, `json`, `os`, `re`, `sys`, `collections`
- Optional: `openai` package for live API calling.

### 2. Setup & Environment
1. Clone the repository and navigate into the folder:
   ```bash
   cd bus-complaint-sorter
   ```
2. (Optional) Configure your LLM API Key:
   ```bash
   cp .env.example .env
   ```
   Add your Gemini or OpenAI API key inside `.env`:
   ```bash
   GEMINI_API_KEY="your_api_key_here"
   ```
   *Note: If no API key is provided, `sorter.py` automatically runs in built-in simulator mode, enabling complete testing and evaluation without an API key or internet access.*

### 3. Run the Sorter
Process all complaints and generate output files:
```bash
python sorter.py
```

### 4. Run the Evaluation Harness
Execute the quantitative 5-complaint benchmark test suite:
```bash
python eval_harness.py
```

---

## 📂 Repository Contents & Deliverables

| Deliverable | File | Description |
| :--- | :--- | :--- |
| **Component 1** | [`specification.md`](specification.md) | One-page pre-code specification: scope, JSON rules, route verification, urgency rubric. |
| **Component 2** | [`sorter.py`](sorter.py) | Main program with 5 required functions, retry logic, route verifier, and report generator. |
| **Component 3** | [`system_prompt.txt`](system_prompt.txt) | 5-Role prompt framework (`[AUTHORITY]`, `[RUBRIC]`, `[CONSTRAINTS]`, `[METADATA]`, `[EXEMPLARS]`). |
| **Component 4** | [`eval_harness.py`](eval_harness.py)<br>[`red_team.md`](red_team.md) | 5-case ground truth eval harness + 3 red-team adversarial attacks (prompt injection, misleading numerals, Tanglish). |
| **Component 5** | [`judgment_framework.md`](judgment_framework.md) | The 3-question governance table and Human Checkpoint architecture. |
| **Component 6** | [`cost_and_latency.md`](cost_and_latency.md) | Daily API call volume, latency profiles, and cost calculations (~₹0.21/day). |
| **Component 7** | [`reflection.md`](reflection.md)<br>[`ai_decision_journal.md`](ai_decision_journal.md) | 400-word engineering reflection and architectural decision journal. |
| **Inputs** | [`routes.csv`](routes.csv)<br>[`complaints.csv`](complaints.csv) | 12 Chennai bus routes and 22 realistic student complaints (safety, vague, Tanglish). |
| **Outputs** | `outputs/` | Contains `results.csv`, `urgent.csv`, and `summary.txt`. |

---

## 🛡️ Key Technical Safeguards

1. **Deterministic Route Extraction:**  
   The LLM is prone to hallucinating route numbers from clock times (e.g. "7:00 AM" $\to$ Route 7) or assuming routes from area names. Python's `verify_route()` function enforces that the route exists in `routes.csv` **AND** appears as an isolated token in the original complaint text. Otherwise, it sets `route = null`.
2. **Resilience & Zero-Crash Guarantee:**  
   Every LLM reply is validated with `is_valid()`. On failure or timeout, the system retries **once**. If the retry also fails, it flags the record as `needs_manual_review` and proceeds. The script never crashes midway through a batch.
3. **Deterministic Counting in Python:**  
   Counting complaints per route and per category is computed strictly in Python via `collections.Counter`. The LLM is never asked to perform arithmetic.
4. **Human-in-the-Loop Governance:**  
   High-risk items are routed directly to `urgent.csv` for human inspection by the Transport Officer. No automated notifications are dispatched to drivers.

---

## 🎓 Showcase Presentation Defense (Line-by-Line Guide)

During the showcase Q&A, faculty may point to any line of code. Key concepts to remember:
- **`try...except json.JSONDecodeError`**: Protects against non-JSON text from the LLM; prevents uncaught exceptions from aborting batch jobs.
- **`re.search(r'\b' + str(route) + r'\b', text)`**: Uses regex word boundaries (`\b`) to ensure number `2` doesn't falsely match inside years like `2026`.
- **`collections.Counter`**: Python standard library hash map that counts frequencies in $O(N)$ deterministic time.
- **Why rude driver is not urgent**: Under the specification rubric, urgency is strictly defined by physical safety and life hazard (speeding, brake failure, door open, footboard travel). Interpersonal issues are classified under `driver` with `urgent: false`.
