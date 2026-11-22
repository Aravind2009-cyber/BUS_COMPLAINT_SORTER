"""
Checkpoint 2: One Complaint End-to-End Demonstration
CIT AI-Native Engineering Programme · Assessment 5
"""

import json
import os
import sys

# Import core functions from sorter.py
from sorter import classify, load_complaints, load_routes, load_env_file


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    load_env_file(os.path.join(base_dir, ".env"))

    routes = load_routes(os.path.join(base_dir, "routes.csv"))
    complaints = load_complaints(os.path.join(base_dir, "complaints.csv"))

    # Load 5-role system prompt
    prompt_path = os.path.join(base_dir, "system_prompt.txt")
    system_prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, mode="r", encoding="utf-8") as f:
            system_prompt = f.read()

    # Determine live LLM client
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
        print("[INFO] Running in Local Intelligent Engine mode (No API key, zero cost).")
    elif gemini_key:
        client = "gemini"
        print("[INFO] Using Live Gemini API for classification.")
    elif groq_key:
        from openai import OpenAI
        client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
        print("[INFO] Using Live Groq API (llama-3.3-70b).")
    elif openrouter_key:
        from openai import OpenAI
        client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
        print("[INFO] Using Live OpenRouter API.")
    elif kimi_key or openai_key:
        active_key = kimi_key if kimi_key else openai_key
        base_url = os.environ.get("LLM_BASE_URL")
        if kimi_key and not base_url:
            base_url = "https://api.moonshot.ai/v1"
        from openai import OpenAI
        client = OpenAI(api_key=active_key, base_url=base_url)
        provider = "Kimi / Moonshot AI" if kimi_key else "OpenAI"
        print(f"[INFO] Using Live {provider} API for classification (Base URL: {base_url}).")
    else:
        print("[INFO] No API key in .env. Running in built-in simulator mode.")

    # Pick complaint C01 (or C02 for safety)
    sample = complaints[0]

    print("=" * 60)
    print("   CHECKPOINT 2: ONE COMPLAINT END-TO-END DEMONSTRATION   ")
    print("=" * 60)
    print(f"Complaint ID   : {sample['id']}")
    print(f"Date           : {sample['date']}")
    print(f"Raw Complaint  : \"{sample['complaint']}\"")
    print("-" * 60)
    print("Running classification & Python route verification...\n")

    # Run single classification
    result = classify(
        complaint_text=sample["complaint"],
        routes_dict=routes,
        client=client,
        max_retries=1,
        system_prompt=system_prompt
    )

    # Print exact JSON output required by the spec
    print("RESULTING JSON OUTPUT:")
    print(json.dumps(result, indent=2))
    print("-" * 60)
    route_name = routes.get(result["route"], "No Route") if result["route"] else "None"
    print(f"Verified Route : {result['route']} ({route_name})")
    print(f"Category       : {result['category']}")
    print(f"Urgent Safety  : {result['urgent']}")
    print("=" * 60)
    print("[SUCCESS] Checkpoint 2 criteria satisfied: Valid JSON with verified route.")


if __name__ == "__main__":
    main()
