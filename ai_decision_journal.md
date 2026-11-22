# AI Decision Journal
**Project:** CIT Bus Complaint Sorter · Assessment 5  
**Course:** CIT AI-Native Engineering Programme · Semester 1

---

## Entry 1: Route Verification Division of Labor
- **Date:** 2026-11-10
- **Context:** Deciding whether the LLM should validate routes against `routes.csv` or whether Python should verify it.
- **Alternative Considered:** Including the full list of 12 routes in the LLM prompt and instructing the LLM to only select valid routes.
- **Decision:** Let the LLM extract the raw stated route integer, and enforce a strict 2-step verification in Python:
  1. `route in routes_dict`
  2. `re.search(r'\b' + str(route) + r'\b', complaint_text)`
- **Rationale:** LLMs can hallucinate plausible route numbers based on locality names (e.g., seeing "Velachery" and guessing Route 2, even if the student never stated a route). A deterministic check prevents hallucination and guarantees verifiable data provenance.

---

## Entry 2: Prompt Framework Architecture
- **Date:** 2026-11-12
- **Context:** Selecting the structural methodology for `system_prompt.txt`.
- **Alternative Considered:** Freeform zero-shot instruction prompt.
- **Decision:** Adopted the 5-Role Framework (`[AUTHORITY]`, `[RUBRIC]`, `[CONSTRAINTS]`, `[METADATA]`, `[EXEMPLARS]`).
- **Rationale:** The 5-role framework creates unambiguous role boundaries, provides concrete negative and positive few-shot exemplars (including Tanglish and vague edge cases), and explicitly forces raw JSON without markdown syntax.

---

## Entry 3: Urgency Rubric Thresholding (Rude Driver vs Reckless Driver)
- **Date:** 2026-11-14
- **Context:** How to classify interpersonal driver complaints (e.g., shouting at students or rude behavior).
- **Alternative Considered:** Classifying all driver-related complaints as `urgent: true`.
- **Decision:** Strictly split interpersonal complaints (`urgent: false`) from physical safety risks (`urgent: true`).
- **Rationale:** While rudeness is unprofessional, overcrowding the Transport Officer's urgent queue with non-safety issues dilutes attention from life-safety risks (e.g., brake failures or phone usage while driving).

---

## Entry 4: Resilience and Fallback Protocol
- **Date:** 2026-11-16
- **Context:** Handling API timeouts, JSON formatting errors, and rate limits during batch runs.
- **Alternative Considered:** Letting Python raise an exception and crashing the script.
- **Decision:** Implement a 1-retry mechanism followed by a deterministic fallback record:
  `category: "needs_manual_review", urgent: false, route: null, summary: "Manual review required"`.
- **Rationale:** A production batch processing tool must never abort halfway through a 50-complaint batch. The fallback pattern ensures 100% data preservation and creates an explicit manual review queue.

---

## Entry 5: Aggregation and Reporting Responsibility
- **Date:** 2026-11-18
- **Context:** Deciding how category and route counts in `summary.txt` should be calculated.
- **Alternative Considered:** Passing all complaints to an LLM at once and asking it to write the summary report.
- **Decision:** Aggregations and frequency sorting are handled completely in Python using `collections.Counter` and list sorting.
- **Rationale:** Counting with LLMs is notoriously inaccurate, consumes unnecessary tokens, and introduces non-deterministic outputs. Python performs $O(N)$ counting with mathematical precision.
