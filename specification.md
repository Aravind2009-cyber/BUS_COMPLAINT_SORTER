# Capstone Project Specification: Bus Complaint Sorter
**Course:** CIT AI-Native Engineering Programme · Semester 1 · Assessment 5  
**Domain:** Transport  
**Status:** Approved for Implementation (Checkpoint 1)

---

## 1. Problem Statement & Scope
The college operates 12 bus routes across Chennai. Students submit complaints via an online Google Form. The majority of submissions concern routine issues like delays or crowding; however, critical safety hazards—such as rash driving, non-functional doors, brake failures, or footboard travel—are frequently buried behind dozens of comfort complaints and sit unread for days.

The **Bus Complaint Sorter** is a console-based Python tool designed to automate complaint triage. It ingests raw complaint logs, leverages a Large Language Model (LLM) to classify each complaint and extract the route number, and places urgent safety risks in front of the Transport Officer immediately.
- **Human-in-the-Loop Constraint:** The system is purely an intake and triage assistant. It **never** contacts drivers directly, never decides driver fault, and never automates punitive actions. Operational decisions rest entirely with human staff.

---

## 2. System Inputs
1. **`complaints.csv`**: Contains student complaints with fields:
   - `id`: Unique identifier (e.g., `C01`, `C02`).
   - `date`: Submission date in `YYYY-MM-DD` format.
   - `complaint`: Free-form student text (English, Tanglish, or Tamil).
2. **`routes.csv`**: The ground-truth roster of 12 official college bus routes:
   - `route`: Integer route number (1 to 12).
   - `area`: The geographic locality served (e.g., Tambaram, Velachery, Porur).

---

## 3. LLM Output Contract & JSON Rules
The LLM must return a single raw JSON object matching this schema exactly:

```json
{
  "category": "driver",
  "urgent": true,
  "route": 7,
  "summary": "Route 7 driver used phone while driving"
}
```

### Schema & Field Rules:
| Field | Allowed Values | Rule |
| :--- | :--- | :--- |
| **`category`** | `delay`, `crowding`, `driver`, `vehicle`, `route_request`, `other` | Select the single category that best describes the core issue. |
| **`urgent`** | `true`, `false` | Set to `true` **only** if there is an active safety hazard. All non-safety complaints must be `false`. |
| **`route`** | Whole number ($1 \dots 12$), or `null` | The route number explicitly stated by the student. Set to `null` if omitted or ambiguous. Never guess. |
| **`summary`** | String ($\le 12$ words) | Concise synopsis of the issue without any personal names of drivers or students. |

### Urgency Definition Rubric:
- **`urgent: true`**: Rash/speeding driving, mobile phone use while driving, near misses, faulty brakes, non-closing doors, damaged tyres, burning smell/smoke, or students hanging on the footboard.
- **`urgent: false`**: Late arrivals, general overcrowding without footboard hanging, rude/unhelpful driver behavior, air conditioning/fan issues, seat comfort, cleanliness, and stop/route extension requests.

---

## 4. Deterministic Python Route Verification Rule
To prevent LLM hallucinations (e.g., mistaking times like "at 7 pm" or bus stops for route numbers), Python enforces a strict two-stage verification filter on the LLM's `route` output:
1. **Ground-Truth Check:** The extracted route number must exist in `routes.csv` (1 through 12).
2. **Raw Text Check:** The exact integer must explicitly appear as an isolated word/token in the raw complaint text (e.g., via regex `\b<route>\b`).
*If either check fails, Python overwrites the route to `null` (`None`).*

---

## 5. Resilience & Fallback Strategy
The pipeline must process batches without crashing:
1. Every LLM response is validated against the JSON schema and value domains (`is_valid()`).
2. If validation fails or an API/network error occurs, the pipeline retries **once**.
3. If the retry also fails, the record is flagged with category `"needs_manual_review"`, `"urgent": false`, `"route": null`, and `"summary": "Manual review required"`. Processing continues uninterrupted.

---

## 6. System Outputs
The script produces three output files in the `outputs/` folder:
1. **`results.csv`**: Comprehensive classification log:
   - Header: `id,category,urgent,route,summary`
2. **`urgent.csv`**: Priority safety queue for the Transport Officer:
   - Header: `id,date,route,area,complaint,summary`
   - *Note:* If `route` is `null`, `area` is labeled as `"Unassigned/Unknown"`.
3. **`summary.txt`**: Executive metrics report:
   - Total complaints count.
   - Complaints breakdown by category.
   - Route complaint frequency table (sorted descending, with route number and served area).
   - High-priority safety summary log.
