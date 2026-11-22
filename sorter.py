"""
Bus Complaint Sorter - Main Classification Engine
CIT AI-Native Engineering Programme · Assessment 5 (Capstone Project)
"""

import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def load_env_file(filepath: str = ".env") -> None:
    """
    Loads environment variables from a .env file without external dependencies.
    """
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, mode="r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"[WARN] Failed to read .env file: {e}")


def load_routes(filepath: str) -> Dict[int, str]:
    """
    Reads routes.csv and returns a dictionary mapping route number to area name.
    Example: {1: 'Tambaram', 2: 'Velachery', ...}
    """
    routes = {}
    try:
        with open(filepath, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    route_num = int(row["route"].strip())
                    area_name = row["area"].strip()
                    routes[route_num] = area_name
                except (ValueError, KeyError) as e:
                    print(f"[WARN] Skipping invalid route row {row}: {e}")
    except FileNotFoundError:
        print(f"[ERROR] Route file not found at: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to read routes: {e}")
        sys.exit(1)
    return routes


def load_complaints(filepath: str) -> List[Dict[str, str]]:
    """
    Reads complaints.csv and returns a list of complaint records.
    Each record contains 'id', 'date', and 'complaint'.
    """
    complaints = []
    try:
        with open(filepath, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                complaints.append({
                    "id": row.get("id", "").strip(),
                    "date": row.get("date", "").strip(),
                    "complaint": row.get("complaint", "").strip()
                })
    except FileNotFoundError:
        print(f"[ERROR] Complaints file not found at: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to read complaints: {e}")
        sys.exit(1)
    return complaints


def is_valid(llm_data: Any) -> bool:
    """
    Validates whether the parsed LLM response adheres strictly to the required schema:
    - Must be a dictionary.
    - Must contain keys: 'category', 'urgent', 'route', 'summary'.
    - 'category' must be one of the 6 allowed values.
    - 'urgent' must be a boolean.
    - 'route' must be an integer or None.
    - 'summary' must be a string with 12 words or fewer.
    """
    if not isinstance(llm_data, dict):
        return False

    required_keys = {"category", "urgent", "route", "summary"}
    if not required_keys.issubset(llm_data.keys()):
        return False

    valid_categories = {"delay", "crowding", "driver", "vehicle", "route_request", "other"}
    if llm_data["category"] not in valid_categories:
        return False

    if not isinstance(llm_data["urgent"], bool):
        return False

    if llm_data["route"] is not None and not isinstance(llm_data["route"], int):
        return False

    if not isinstance(llm_data["summary"], str):
        return False

    # Summary constraint: 12 words or fewer
    words = llm_data["summary"].strip().split()
    if len(words) > 12:
        return False

    return True


def verify_route(llm_route: Optional[int], complaint_text: str, routes_dict: Dict[int, str]) -> Optional[int]:
    """
    Deterministic Python Route Verification:
    Keeps the route ONLY if:
      1. It is in routes.csv (routes_dict keys)
      2. The number actually appears as an isolated token in the raw complaint text.
    Otherwise sets route to None.
    """
    if llm_route is None:
        return None

    try:
        route_num = int(llm_route)
    except (ValueError, TypeError):
        return None

    # Condition 1: Must be in routes.csv
    if route_num not in routes_dict:
        return None

    # Condition 2: Must explicitly appear in complaint text
    pattern = r"\b" + str(route_num) + r"\b"
    if not re.search(pattern, complaint_text):
        return None

    return route_num


def _call_gemini_api(complaint_text: str, system_prompt: str, api_key: str) -> str:
    """
    Directly calls Google Gemini REST API using Python standard urllib.
    Forces application/json mode for 100% compliant JSON responses.
    """
    model = os.environ.get("LLM_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "parts": [{"text": f"Complaint text: {complaint_text}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "response_mime_type": "application/json"
        }
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp_data = json.loads(resp.read().decode("utf-8"))
        return resp_data["candidates"][0]["content"]["parts"][0]["text"]


def _call_llm_api(complaint_text: str, system_prompt: str, client: Any) -> str:
    """
    Calls LLM provider:
    1. Gemini API if GEMINI_API_KEY is present in environment.
    2. OpenAI API if client is an OpenAI client.
    3. Standalone heuristic simulator if no API key is provided.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        return _call_gemini_api(complaint_text, system_prompt, gemini_key)

    if client is not None and not isinstance(client, str):
        default_model = "moonshot-v1-8k" if os.environ.get("KIMI_API_KEY") else "gpt-4o-mini"
        model_name = os.environ.get("LLM_MODEL", default_model)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Complaint text: {complaint_text}"}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content

    # Standalone heuristic simulator if no API key is provided
    text_lower = complaint_text.lower()
    route_match = re.search(r"\b(?:route|bus)\s*(\d+)\b", text_lower)
    route_val = int(route_match.group(1)) if route_match else None

    # Urgent safety keywords
    urgent_words = ["fast", "rash", "phone", "brake", "door", "footboard", "smoke", "collided", "overtaking"]
    is_urgent = any(w in text_lower for w in urgent_words)

    if any(w in text_lower for w in ["phone", "fast", "shouting", "rash", "overtaking", "sudden brake"]):
        cat = "driver"
    elif any(w in text_lower for w in ["footboard", "crowd", "space"]):
        cat = "crowding"
    elif any(w in text_lower for w in ["door", "smoke", "brake", "ac", "seats", "leaking", "engine"]):
        cat = "vehicle"
    elif any(w in text_lower for w in ["late", "delayed", "timing", "delayed by", "skipped"]):
        cat = "delay"
    elif any(w in text_lower for w in ["stop", "extend", "add another bus", "route request"]):
        cat = "route_request"
    else:
        cat = "other"

    # Construct short summary (<= 12 words)
    words = complaint_text.split()[:8]
    summary_text = " ".join(words) if words else "Student complaint logged"

    simulated_response = {
        "category": cat,
        "urgent": is_urgent,
        "route": route_val,
        "summary": summary_text
    }
    return json.dumps(simulated_response)


def classify(
    complaint_text: str,
    routes_dict: Dict[int, str],
    client: Any = None,
    max_retries: int = 1,
    system_prompt: str = ""
) -> Dict[str, Any]:
    """
    Sends complaint to LLM, parses JSON, validates schema, handles retries,
    verifies route in Python, and falls back to 'needs_manual_review' on persistent failure.
    The program will NEVER crash halfway.
    """
    if not system_prompt:
        system_prompt = "Return valid JSON with category, urgent, route, summary."

    attempts = 0
    total_allowed_attempts = 1 + max_retries

    while attempts < total_allowed_attempts:
        attempts += 1
        try:
            raw_response = _call_llm_api(complaint_text, system_prompt, client)
            
            # Clean possible markdown formatting (e.g. ```json ... ```)
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            parsed = json.loads(cleaned)

            if is_valid(parsed):
                # Apply deterministic Python Route Verification
                verified_route = verify_route(parsed["route"], complaint_text, routes_dict)
                parsed["route"] = verified_route
                return parsed
            else:
                print(f"[WARN] Schema validation failed on attempt {attempts}. Retrying...")

        except (json.JSONDecodeError, Exception) as e:
            print(f"[WARN] Error parsing LLM reply on attempt {attempts}: {e}")

    # Fallback if all attempts fail
    return {
        "category": "needs_manual_review",
        "urgent": False,
        "route": None,
        "summary": "Manual review required"
    }


def write_reports(
    results: List[Dict[str, Any]],
    urgent_list: List[Dict[str, Any]],
    routes_dict: Dict[int, str],
    output_dir: str = "outputs"
) -> None:
    """
    Generates three required output files:
    1. results.csv: id, category, urgent, route, summary
    2. urgent.csv: id, date, route, area, complaint, summary
    3. summary.txt: category counts, sorted route counts with area names, and safety list.
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. results.csv
    results_path = os.path.join(output_dir, "results.csv")
    with open(results_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "category", "urgent", "route", "summary"])
        for r in results:
            writer.writerow([
                r["id"],
                r["category"],
                r["urgent"],
                r["route"] if r["route"] is not None else "",
                r["summary"]
            ])

    # 2. urgent.csv
    urgent_path = os.path.join(output_dir, "urgent.csv")
    with open(urgent_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "route", "area", "complaint", "summary"])
        for u in urgent_list:
            route_val = u["route"]
            area_val = routes_dict.get(route_val, "Unassigned/Unknown") if route_val else "Unassigned/Unknown"
            writer.writerow([
                u["id"],
                u["date"],
                route_val if route_val is not None else "",
                area_val,
                u["complaint"],
                u["summary"]
            ])

    # 3. summary.txt
    summary_path = os.path.join(output_dir, "summary.txt")
    total_complaints = len(results)
    total_urgent = len(urgent_list)

    # Category counts
    category_counts = Counter(r["category"] for r in results)

    # Route counts (only for complaints assigned a valid route)
    route_counts = Counter(r["route"] for r in results if r["route"] is not None)
    unassigned_count = sum(1 for r in results if r["route"] is None)

    # Sort routes descending by complaint count
    sorted_routes = sorted(
        routes_dict.keys(),
        key=lambda rt: route_counts.get(rt, 0),
        reverse=True
    )

    with open(summary_path, mode="w", encoding="utf-8") as f:
        f.write("=====================================================\n")
        f.write("        COLLEGE BUS COMPLAINT TRIAGE REPORT          \n")
        f.write("=====================================================\n\n")
        f.write(f"Total Complaints Processed : {total_complaints}\n")
        f.write(f"Safety Complaints (Urgent) : {total_urgent}\n")
        f.write(f"Unassigned / No Route      : {unassigned_count}\n\n")

        f.write("-----------------------------------------------------\n")
        f.write("1. COMPLAINTS PER CATEGORY\n")
        f.write("-----------------------------------------------------\n")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f" - {cat.ljust(22)} : {count}\n")
        f.write("\n")

        f.write("-----------------------------------------------------\n")
        f.write("2. COMPLAINTS PER ROUTE (Sorted by highest frequency)\n")
        f.write("-----------------------------------------------------\n")
        for rt in sorted_routes:
            count = route_counts.get(rt, 0)
            area = routes_dict.get(rt, "Unknown")
            f.write(f" - Route {str(rt).rjust(2)} ({area.ljust(14)}) : {count} complaint(s)\n")
        f.write("\n")

        f.write("-----------------------------------------------------\n")
        f.write("3. TRANSPORT OFFICER SAFETY QUEUE (Urgent Issues)\n")
        f.write("-----------------------------------------------------\n")
        if not urgent_list:
            f.write("No safety issues flagged.\n")
        else:
            for idx, u in enumerate(urgent_list, 1):
                rt_str = f"Route {u['route']}" if u['route'] else "Route Unassigned"
                area_str = routes_dict.get(u['route'], "Unknown Area") if u['route'] else "Unknown Area"
                f.write(f"[{idx}] ID: {u['id']} | Date: {u['date']} | {rt_str} ({area_str})\n")
                f.write(f"    Summary   : {u['summary']}\n")
                f.write(f"    Complaint : \"{u['complaint']}\"\n\n")

    print(f"\n[INFO] Successfully generated all 3 reports in '{output_dir}/':")
    print(f"  - {results_path}")
    print(f"  - {urgent_path}")
    print(f"  - {summary_path}")


def main():
    print("=" * 60)
    print("   CIT Bus Complaint Sorter - Automated Triage Tool   ")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(base_dir, ".env")
    load_env_file(env_file)

    routes_file = os.path.join(base_dir, "routes.csv")
    complaints_file = os.path.join(base_dir, "complaints.csv")
    prompt_path = os.path.join(base_dir, "system_prompt.txt")
    output_dir = os.path.join(base_dir, "outputs")

    # 1. Load routes & complaints
    routes = load_routes(routes_file)
    print(f"[OK] Loaded {len(routes)} bus routes from {routes_file}")

    complaints = load_complaints(complaints_file)
    print(f"[OK] Loaded {len(complaints)} complaints from {complaints_file}")

    # 2. Load system prompt
    system_prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, mode="r", encoding="utf-8") as f:
            system_prompt = f.read()
        print("[OK] Loaded system prompt (5-Role Framework)")
    else:
        print("[WARN] system_prompt.txt not found, using default minimal prompt")

    # 3. Setup LLM client / API check
    force_local = (
        "--local" in sys.argv
        or "--offline" in sys.argv
        or os.environ.get("USE_LOCAL_SIMULATOR", "").lower() in ("true", "1")
    )

    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    kimi_key = os.environ.get("KIMI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    client = None

    if force_local:
        print("[INFO] Running in Local Intelligent Engine mode (Zero cost, no API key required).")
    elif gemini_key:
        masked = gemini_key[:6] + "..." + gemini_key[-4:] if len(gemini_key) > 10 else "***"
        print(f"[OK] Connected to Live Google Gemini API (Key: {masked})")
        client = "gemini"
    elif groq_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            masked = groq_key[:6] + "..." + groq_key[-4:] if len(groq_key) > 10 else "***"
            print(f"[OK] Connected to Live Groq API (Key: {masked}, Model: llama-3.3-70b)")
        except Exception as e:
            print(f"[WARN] Could not initialize Groq client ({e}). Running in local mode.")
    elif openrouter_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
            masked = openrouter_key[:6] + "..." + openrouter_key[-4:] if len(openrouter_key) > 10 else "***"
            print(f"[OK] Connected to Live OpenRouter API (Key: {masked})")
        except Exception as e:
            print(f"[WARN] Could not initialize OpenRouter client ({e}). Running in local mode.")
    elif kimi_key or openai_key:
        active_key = kimi_key if kimi_key else openai_key
        base_url = os.environ.get("LLM_BASE_URL")
        if kimi_key and not base_url:
            base_url = "https://api.moonshot.ai/v1"
        try:
            from openai import OpenAI
            client = OpenAI(api_key=active_key, base_url=base_url)
            provider_name = "Kimi / Moonshot AI" if kimi_key else "OpenAI"
            masked = active_key[:6] + "..." + active_key[-4:] if len(active_key) > 10 else "***"
            print(f"[OK] Connected to Live {provider_name} API (Key: {masked}, Base URL: {base_url or 'default'})")
        except Exception as e:
            print(f"[WARN] Could not initialize client ({e}). Running in fallback mode.")
    else:
        print("[INFO] No API key detected. Running in Local Intelligent Engine mode.")

    # 4. Process each complaint
    results = []
    urgent_list = []

    print("\nProcessing complaints...")
    for idx, item in enumerate(complaints, 1):
        c_id = item["id"]
        c_date = item["date"]
        c_text = item["complaint"]

        classification = classify(
            complaint_text=c_text,
            routes_dict=routes,
            client=client,
            max_retries=1,
            system_prompt=system_prompt
        )

        res_record = {
            "id": c_id,
            "category": classification["category"],
            "urgent": classification["urgent"],
            "route": classification["route"],
            "summary": classification["summary"]
        }
        results.append(res_record)

        if classification["urgent"]:
            urgent_record = {
                "id": c_id,
                "date": c_date,
                "route": classification["route"],
                "complaint": c_text,
                "summary": classification["summary"]
            }
            urgent_list.append(urgent_record)

        route_display = f"Route {classification['route']}" if classification['route'] else "No Route"
        urgent_flag = " [URGENT SAFETY]" if classification['urgent'] else ""
        print(f"[{idx:02d}/{len(complaints):02d}] {c_id}: {classification['category']} | {route_display}{urgent_flag}")

    # 5. Write reports
    write_reports(results, urgent_list, routes, output_dir=output_dir)
    print("\n[COMPLETE] Triage run finished cleanly.")


if __name__ == "__main__":
    main()
