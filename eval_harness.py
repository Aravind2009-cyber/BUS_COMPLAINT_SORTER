"""
Eval Harness for Bus Complaint Sorter
Component 4: Quantitative Evaluation on 5 Ground-Truth Test Cases
"""

import os
import sys

# Import functions from sorter.py
from sorter import classify, load_routes, is_valid, load_env_file


def run_evaluation():
    print("=" * 65)
    print("       EVALUATION HARNESS: 5 BENCHMARK TEST COMPLAINTS        ")
    print("=" * 65)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    load_env_file(os.path.join(base_dir, ".env"))
    routes_file = os.path.join(base_dir, "routes.csv")
    routes = load_routes(routes_file)

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
        print("[INFO] Evaluating with Local Intelligent Engine (No API key, zero cost).")
    elif gemini_key:
        client = "gemini"
        print("[INFO] Evaluating with Live Google Gemini API")
    elif groq_key:
        from openai import OpenAI
        client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
        print("[INFO] Evaluating with Live Groq API")
    elif openrouter_key:
        from openai import OpenAI
        client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
        print("[INFO] Evaluating with Live OpenRouter API")
    elif kimi_key or openai_key:
        active_key = kimi_key if kimi_key else openai_key
        base_url = os.environ.get("LLM_BASE_URL")
        if kimi_key and not base_url:
            base_url = "https://api.moonshot.ai/v1"
        from openai import OpenAI
        client = OpenAI(api_key=active_key, base_url=base_url)
        print("[INFO] Evaluating with Live Kimi / OpenAI API")
    else:
        print("[INFO] No API key detected. Evaluating with Local Engine.")

    # Ground-truth test dataset (5 complaints)
    test_cases = [
        {
            "id": "E01",
            "complaint": "Route 1 bus was 40 minutes late this morning due to traffic",
            "expected_category": "delay",
            "expected_urgent": False,
            "expected_route": 1
        },
        {
            "id": "E02",
            "complaint": "Driver on route 7 was talking on the phone while driving fast on GST road",
            "expected_category": "driver",
            "expected_urgent": True,
            "expected_route": 7
        },
        {
            "id": "E03",
            "complaint": "Bus 2 is so crowded that students are hanging on the footboard",
            "expected_category": "crowding",
            "expected_urgent": True,
            "expected_route": 2
        },
        {
            "id": "E04",
            "complaint": "Can we please extend route 11 to cover Sholinganallur junction?",
            "expected_category": "route_request",
            "expected_urgent": False,
            "expected_route": 11
        },
        {
            "id": "E05",
            "complaint": "ok thank you",
            "expected_category": "other",
            "expected_urgent": False,
            "expected_route": None
        }
    ]

    total = len(test_cases)
    cat_correct = 0
    urg_correct = 0
    rt_correct = 0
    all_correct = 0

    print(f"{'ID':<5} | {'Category':<15} | {'Urgent':<8} | {'Route':<8} | {'Status'}")
    print("-" * 65)

    for case in test_cases:
        res = classify(
            complaint_text=case["complaint"],
            routes_dict=routes,
            client=client,
            max_retries=1,
            system_prompt=system_prompt
        )

        c_match = (res["category"] == case["expected_category"])
        u_match = (res["urgent"] == case["expected_urgent"])
        r_match = (res["route"] == case["expected_route"])

        if c_match:
            cat_correct += 1
        if u_match:
            urg_correct += 1
        if r_match:
            rt_correct += 1

        passed = c_match and u_match and r_match
        if passed:
            all_correct += 1
            status = "PASS [✓]"
        else:
            status = "FAIL [✗]"

        cat_str = f"{res['category']}" if c_match else f"{res['category']} (exp {case['expected_category']})"
        urg_str = f"{res['urgent']}" if u_match else f"{res['urgent']} (exp {case['expected_urgent']})"
        rt_str = f"{res['route']}" if r_match else f"{res['route']} (exp {case['expected_route']})"

        print(f"{case['id']:<5} | {cat_str:<15} | {urg_str:<8} | {rt_str:<8} | {status}")

    print("=" * 65)
    print("EVALUATION SUMMARY METRICS:")
    print(f" - Category Accuracy : {cat_correct}/{total} ({cat_correct/total * 100:.1f}%)")
    print(f" - Urgency Accuracy  : {urg_correct}/{total} ({urg_correct/total * 100:.1f}%)")
    print(f" - Route Accuracy    : {rt_correct}/{total} ({rt_correct/total * 100:.1f}%)")
    print(f" - Exact Match Rate  : {all_correct}/{total} ({all_correct/total * 100:.1f}%)")
    print("=" * 65)


if __name__ == "__main__":
    run_evaluation()
