"""
Northwind Triage — Batch Runner & Scorer

Usage:
    python batch_run.py

Reads 05_Inbound_Messages.json, runs all 20 messages through the agent,
compares output to 06_Benchmark.json, prints accuracy scores, and saves
results to batch_results.json.
"""

import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from agent import triage_message

DATA_DIR = Path(__file__).parent.parent / "data"
MESSAGES_FILE = DATA_DIR / "05_Inbound_Messages.json"
BENCHMARK_FILE = DATA_DIR / "06_Benchmark.json"
RESULTS_FILE = Path(__file__).parent / "batch_results.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def normalise_route(route: str) -> str:
    """Lowercase + strip for comparison."""
    return route.lower().strip()


def score_route(agent_route: str, bench_route: str) -> float:
    """
    1.0 = exact match
    0.5 = primary team correct but cc missed
    0.0 = wrong
    """
    a = normalise_route(agent_route)
    b = normalise_route(bench_route)
    if a == b:
        return 1.0
    # Partial credit: primary team is the first team listed
    primary_bench = b.split("+")[0].strip()
    primary_agent = a.split("+")[0].strip()
    if primary_agent == primary_bench:
        return 0.5
    return 0.0


def run_batch():
    messages_data = load_json(MESSAGES_FILE)
    benchmark_data = load_json(BENCHMARK_FILE)

    messages = messages_data["messages"]
    bench_by_id = {d["id"]: d for d in benchmark_data["decisions"]}

    results = []
    scores = {
        "category": [],
        "priority": [],
        "route_to": [],
        "needs_human_review": [],
        "all_four": [],
    }

    print(f"\n{'='*60}")
    print("NORTHWIND TRIAGE — BATCH RUN")
    print(f"{'='*60}\n")

    for i, msg in enumerate(messages):
        msg_id = msg["id"]
        bench = bench_by_id.get(msg_id, {})

        print(f"[{i+1:02d}/20] {msg_id} — {msg.get('sender_name', '?')} — ", end="", flush=True)

        try:
            agent_out = triage_message(msg)
            print(f"{agent_out['category']} / {agent_out['priority']}")
        except Exception as e:
            print(f"ERROR: {e}")
            agent_out = {
                "id": msg_id,
                "category": "ERROR",
                "priority": "ERROR",
                "route_to": "ERROR",
                "needs_human_review": False,
                "draft_reply": "",
                "reasoning": str(e),
            }

        # Score
        cat_score = 1 if agent_out["category"] == bench.get("category") else 0
        pri_score = 1 if agent_out["priority"] == bench.get("priority") else 0
        route_score = score_route(agent_out["route_to"], bench.get("route_to", ""))
        review_score = 1 if agent_out["needs_human_review"] == bench.get("needs_human_review") else 0
        all_four = 1 if (cat_score == 1 and pri_score == 1 and route_score == 1.0 and review_score == 1) else 0

        scores["category"].append(cat_score)
        scores["priority"].append(pri_score)
        scores["route_to"].append(route_score)
        scores["needs_human_review"].append(review_score)
        scores["all_four"].append(all_four)

        results.append({
            "id": msg_id,
            "sender": msg.get("sender_name"),
            "agent": agent_out,
            "benchmark": {
                "category": bench.get("category"),
                "priority": bench.get("priority"),
                "route_to": bench.get("route_to"),
                "needs_human_review": bench.get("needs_human_review"),
            },
            "scores": {
                "category": cat_score,
                "priority": pri_score,
                "route_to": route_score,
                "needs_human_review": review_score,
                "all_four": all_four,
            },
            "benchmark_notes": bench.get("notes", ""),
        })

        # Small delay to avoid rate limits
        time.sleep(0.5)

    # Summary
    n = len(messages)
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Strict accuracy (all 4 fields): {sum(scores['all_four'])}/{n} = {sum(scores['all_four'])/n*100:.1f}%")
    print(f"Category accuracy:              {sum(scores['category'])}/{n} = {sum(scores['category'])/n*100:.1f}%")
    print(f"Priority accuracy:              {sum(scores['priority'])}/{n} = {sum(scores['priority'])/n*100:.1f}%")
    print(f"Route accuracy (w/ partial):    {sum(scores['route_to'])}/{n} = {sum(scores['route_to'])/n*100:.1f}%")
    print(f"Human review accuracy:          {sum(scores['needs_human_review'])}/{n} = {sum(scores['needs_human_review'])/n*100:.1f}%")

    print(f"\nFAILURES:")
    for r in results:
        if r["scores"]["all_four"] == 0:
            a = r["agent"]
            b = r["benchmark"]
            diffs = []
            if r["scores"]["category"] == 0:
                diffs.append(f"category: got {a['category']}, expected {b['category']}")
            if r["scores"]["priority"] == 0:
                diffs.append(f"priority: got {a['priority']}, expected {b['priority']}")
            if r["scores"]["route_to"] < 1.0:
                diffs.append(f"route: got '{a['route_to']}', expected '{b['route_to']}'")
            if r["scores"]["needs_human_review"] == 0:
                diffs.append(f"review: got {a['needs_human_review']}, expected {b['needs_human_review']}")
            print(f"  {r['id']} ({r['sender']}): {' | '.join(diffs)}")

    # Save full results
    with open(RESULTS_FILE, "w") as f:
        json.dump({
            "summary": {
                "strict_accuracy": f"{sum(scores['all_four'])/n*100:.1f}%",
                "category": f"{sum(scores['category'])/n*100:.1f}%",
                "priority": f"{sum(scores['priority'])/n*100:.1f}%",
                "route_to": f"{sum(scores['route_to'])/n*100:.1f}%",
                "needs_human_review": f"{sum(scores['needs_human_review'])/n*100:.1f}%",
            },
            "results": results
        }, f, indent=2)

    print(f"\nFull results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    run_batch()