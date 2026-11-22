# Judgment Framework & Governance Architecture
**Project:** CIT Bus Complaint Sorter · Assessment 5  
**Domain:** College Student Transportation

---

## 1. System Governance & The Three Questions
Every component of the automated triage tool has been evaluated across three core operational governance questions:
1. **What is the cost of being wrong?** (Risk severity)
2. **Can it be verified without AI?** (Auditability & determinism)
3. **Who is accountable?** (Human ownership)

| System Component | Cost of Being Wrong | Can it be verified without AI? | Who is Accountable? |
| :--- | :--- | :--- | :--- |
| **Urgency Flagging (`urgent: true/false`)** | **CRITICAL (High):** A false negative (missing a brake failure, open door, or drunk/speeding driver) can lead to severe passenger injury or fatal road accidents. A false positive merely costs 30 seconds of officer triage time. | **Yes.** The Transport Officer reads the unedited raw complaint text in `urgent.csv` and cross-examines student submissions directly. | **Transport Officer.** The AI does not make decisions; it creates a prioritized triage queue. The officer is accountable for reviewing and verifying the queue. |
| **Route Extraction (`route: int / null`)** | **MODERATE:** A wrong route misallocates complaints in aggregate statistics and may cause maintenance teams to inspect the wrong vehicle. | **Yes.** Deterministically verified in Python by checking against `routes.csv` and regex pattern-matching the complaint text. | **Software Engineer / Python Verifier.** The verification logic guarantees no hallucinated route passes into the official report. |
| **Category Classification (`category`)** | **LOW:** A comfort complaint categorized as `delay` instead of `crowding` produces minor skew in weekly management charts but causes zero safety or physical risk. | **Yes.** Transport clerical staff can spot-check category distributions during weekly administrative reviews. | **Administrative / Transport Clerk.** Accountable for overall route analytics and service feedback reporting. |
| **Issue Summarization (`summary`)** | **LOW:** An inaccurate summary might slightly confuse the reader, but the full raw text is always preserved side-by-side in `urgent.csv`. | **Yes.** Human readers compare the 12-word summary against the original student text. | **Transport Officer.** Relies on the original complaint when contacting route supervisors. |

---

## 2. The Human Checkpoint: Guardrails & Non-Negotiable Boundaries

### A. The Separation of Triage and Action
The Bus Complaint Sorter is strictly a **decision-support filter**, not an autonomous agent.
- **The tool NEVER contacts drivers.**
- **The tool NEVER assigns legal or workplace fault.**
- **The tool NEVER issues penalties, notices, or route cancellations.**

### B. The Transport Officer Inspection Checkpoint
All high-stakes output flows directly into a dedicated human interface: `urgent.csv` and Section 3 of `summary.txt`.
```
[Raw Student Complaints] 
           │
           ▼
   [LLM + Python Filter] 
           │
           ▼
     [urgent.csv]  ◀─── HUMAN CHECKPOINT (Transport Officer)
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [Investigate Bus/Driver]         [Dismiss False Alarm]
```

### C. Fallback Accountability
If the LLM fails JSON parsing twice or returns erratic output, the program defaults to:
```json
{
  "category": "needs_manual_review",
  "urgent": false,
  "route": null,
  "summary": "Manual review required"
}
```
This ensures zero data loss, guarantees that no error crashes the system halfway, and creates a clear audit trail for human clerks to inspect unclassified rows manually.
