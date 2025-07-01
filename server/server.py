#!/usr/bin/env python3

from fastapi import FastAPI, Request
import json
import os
import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from filelock import FileLock 

# ==== CONFIG ====
DD_SITE = "https://api.datadoghq.com"
DD_API_KEY = "{DD_API_KEY}"  # Replace this with your actual API key
METRIC_NAME = "custom.workshop.user_action"
ENV_TAG = "workshop"
TOTAL_PROBLEMS = 7

app = FastAPI()

USER_FILE = "users.json"
RESULT_FILE = "results.json"
LOCK_FILE = RESULT_FILE + ".lock"

# ==== DATADOG METRIC ====
def send_datadog_metric(value: float, tags: list):
    payload = {
        "series": [
            {
                "metric": METRIC_NAME,
                "points": [[int(time.time()), value]],
                "type": "gauge",
                "tags": tags
            }
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DD_API_KEY
    }
    try:
        res = requests.post(f"{DD_SITE}/api/v1/series", headers=headers, json=payload)
        res.raise_for_status()
    except Exception as e:
        print(f"[Datadog Error] {e}")

# ==== UTIL ====
def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.get("/health")
def health():
    return {"status": "ok"}

# ==== REGISTER ====
@app.post("/register")
async def register(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        if not name:
            return {"status": "error", "message": "name required"}

        users = load_json(USER_FILE)
        if name not in users:
            users.append(name)
            save_json(USER_FILE, users)

            print(f"[REGISTER] {name} has been successfully registered.")
            send_datadog_metric(0, [f"name:{name}", "action:register", f"env:{ENV_TAG}"])
            return {"status": "registered"}

        print(f"[REGISTER] {name} is already registered.")
        return {"status": "already_registered"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==== SUBMIT ====
@app.post("/submit")
async def submit(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        problem = data.get("problem")

        if not name or problem is None:
            return {"status": "error", "message": "name and problem required"}

        if not isinstance(problem, int) or not (1 <= problem <= TOTAL_PROBLEMS):
            return {"status": "error", "message": f"invalid problem number (1~{TOTAL_PROBLEMS})"}

        with FileLock(LOCK_FILE):
            results = load_json(RESULT_FILE)

            for r in results:
                if r["name"] == name and r["problem"] == problem:
                    print("[SUBMIT]")
                    print(f"  name    : {name}")
                    print(f"  problem : {problem}")
                    print(f"  result  : already submitted — ignored")
                    return {"status": "already_submitted"}

            submitted = [r for r in results if r["problem"] == problem]
            rank = len(submitted) + 1

            if rank == 1:
                score = 9
            elif rank == 2:
                score = 8
            elif rank == 3:
                score = 7
            else:
                score = 6

            result = {
                "name": name,
                "problem": problem,
                "score": score,
                "rank": rank,
                "timestamp": datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
            }
            results.append(result)
            save_json(RESULT_FILE, results)

        print("[SUBMIT]")
        print(f"  name    : {name}")
        print(f"  problem : {problem}")
        print(f"  result  : submitted")
        print(f"  score   : {score}")
        print(f"  rank    : {rank}")

        send_datadog_metric(score, [f"name:{name}", "action:submit", f"problem:{problem}", f"env:{ENV_TAG}"])

        return {"status": "submitted", "score": score, "rank": rank}

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/quiz")
async def quiz(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        if not name:
            return {"status": "error", "message": "name required"}

        score = 10
        send_datadog_metric(
            score,
            [f"name:{name}", "action:quiz", f"env:{ENV_TAG}"]
        )

        print("[SESSION]")
        print(f"  name   : {name}")
        print(f"  score  : {score}")
        print(f"  action : quiz")

        return {"status": "sent", "score": score, "action": "quiz"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
