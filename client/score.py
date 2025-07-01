import os
import sys
import json
import subprocess
import requests
import yaml
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# === Load ENV ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
SERVER_URL = os.getenv("SERVER_URL")
STATE_FILE = os.path.join(SCRIPT_DIR, "user_state.json")

# === User State ===
def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)

def reset_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("[RESET] State has been cleared.")

def register(name):
    state = load_state()
    if state.get("name"):
        print("[REGISTER]")
        print(f"  current name : {state['name']}")
        print(f"  result       : already registered")
        return

    payload = {"name": name}
    try:
        res = requests.post(f"{SERVER_URL}/register", json=payload)
        res.raise_for_status()
        response = res.json()

        print("[REGISTER]")
        print(f"  name         : {name}")
        for key, value in response.items():
            print(f"    {key:<12}: {value}")

        state = {"name": name, "completed": []}
        save_state(state)
    except Exception as e:
        print(f"[ERROR] Failed to register: {e}")

# === Problem Checkers ===
def check_problem_1():
    path = os.path.expanduser("~/docker.env")
    if not os.path.exists(path): return "fail"
    with open(path) as f:
        return "pass" if any(line.strip().startswith("DD_API_KEY") for line in f) else "fail"

def check_problem_2():
    path = "/root/lab/challenge1/docker-compose.yaml"
    if not os.path.exists(path):
        return "fail"

    with open(path) as f:
        content = f.read()
        pattern = r"DD_SITE\s*=\s*datadoghq\.com"
        return "pass" if re.search(pattern, content) else "fail"

def check_problem_3():
    try:
        local = datetime.utcnow()
        result = subprocess.check_output("curl -s --head http://google.com | grep ^Date: | cut -d' ' -f3-", shell=True)
        google = datetime.strptime(result.decode().strip(), "%d %b %Y %H:%M:%S GMT")
        delta = abs((local - google).total_seconds())
        return "pass" if delta <= 120 else "fail"
    except:
        return "fail"

def check_problem_4():
    path = "/root/lab/challenge1/datadog/custom_check/conf.yaml"
    if not os.path.exists(path): return "fail"

    with open(path) as f:
        for line in f:
            if "url" in line and "http://www.datadog.com/blog/" in line:
                return "pass"

    return "fail"

def check_problem_5():
    dc = "/root/lab/challenge1/docker-compose.yaml"
    conf = "/root/lab/challenge1/datadog/custom_log/conf.yaml"

    try:
        with open(dc) as f:
            content = f.read()
            pattern = r"(/root/logs(?:/output\.log)?)\s*:\s*\1(?:\s*:\s*\w+)?"
            if not re.search(pattern, content):
                return "fail"

            data = yaml.safe_load(content)
            services = data.get("services", {})
            dd_agent = services.get("datadog-agent", {})
            env_list = dd_agent.get("environment", [])

            if not any(isinstance(item, str) and item.strip() == "DD_LOGS_ENABLED=true" for item in env_list):
                return "fail"

        with open(conf) as f:
            content = f.read()
            if "DEBUG|INFO|WARN" in content and "(?i)" not in content:
                return "pass"

    except:
        return "fail"

    return "fail"


def check_problem_6():
    path = "/root/lab/challenge2/docker-compose.yaml"
    if not os.path.exists(path): return "fail"

    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})
        redis = services.get("redis", {})
        env_vars = redis.get("environment", [])
        labels = redis.get("labels", {})

        redis_pass_env = None
        for item in env_vars:
            if item.startswith("REDIS_PASSWORD="):
                redis_pass_env = item.split("=", 1)[1].strip()

        if not redis_pass_env:
            return "fail"

        instances_str = labels.get("com.datadoghq.ad.instances")
        if not instances_str:
            return "fail"

        instances = json.loads(instances_str)[0]
        label_password = instances.get("password")
        if redis_pass_env != label_password:
            return "fail"

        if "networks" not in redis or "dd-net" not in redis["networks"]:
            return "fail"

        return "pass"

    except Exception:
        return "fail"

def check_problem_7():
    path = "/root/lab/challenge2/docker-compose.yaml"
    if not os.path.exists(path): return "fail"

    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})

        agent_image = services.get("datadog-agent", {}).get("image")
        if agent_image != "gcr.io/datadoghq/agent:latest-jmx":
            return "fail"

        tomcat_labels = services.get("tomcat", {}).get("labels", {})
        instances_raw = tomcat_labels.get("com.datadoghq.ad.instances")
        if not instances_raw:
            return "fail"

        instances = json.loads(instances_raw)
        if not instances or instances[0].get("port") != "9012":
            return "fail"

        init_configs_raw = tomcat_labels.get("com.datadoghq.ad.init_configs")
        if not init_configs_raw:
            return "fail"

        init_configs = yaml.safe_load(init_configs_raw)
        conf = init_configs[0].get("conf", [])
        if not conf:
            return "fail"

        exclude = conf[0].get("exclude", {})
        regex = exclude.get("bean_regex", "")
        parts = set(part.strip() for part in regex.strip("|").split("|") if part.strip())

        required = {"java\\.lang:type=Runtime", "java\\.lang:type=Compilation"}
        if not required.issubset(parts):
            return "fail"

        if any("Catalina:type=ThreadPool" in part for part in parts):
            return "fail"

        return "pass"

    except Exception:
        return "fail"

def run_checker(problem):
    if problem == 1:
        return check_problem_1()
    elif problem == 2:
        return check_problem_2()
    elif problem == 3:
        return check_problem_3()
    elif problem == 4:
        return check_problem_4()
    elif problem == 5:
        return check_problem_5()
    elif problem == 6:
        return check_problem_6()
    elif problem == 7:
        return check_problem_7()
    else:
        print(f"[ERROR] Unsupported problem number: {problem}")
        return None

# === Submission ===
def has_solved(problem):
    return problem in load_state().get("completed", [])

def mark_solved(problem):
    state = load_state()
    state.setdefault("completed", []).append(problem)
    save_state(state)

def submit(problem):
    state = load_state()
    name = state.get("name")
    if not name:
        print("[ERROR] Please register first using: check register <name>")
        return

    if has_solved(problem):
        print(f"[SKIP] Problem {problem} was already submitted.")
        return

    result = run_checker(problem)
    if result is None:
        return

    if result != "pass":
        print("[INFO] Incorrect answer. Try again.")
        return

    payload = {"name": name, "problem": problem}
    try:
        res = requests.post(f"{SERVER_URL}/submit", json=payload)
        res.raise_for_status()
        data = res.json()
        print("[SUBMIT]")
        print(f"  name    : {name}")
        print(f"  problem : {problem}")
        print("  response:")
        for key, value in data.items():
            print(f"    {key:<8}: {value}")
        if data.get("status") == "submitted":
            print("[SUCCESS] Congrats! You solved the problem 🎉")
            mark_solved(problem)
    except Exception as e:
        print(f"[ERROR] Failed to submit: {e}")

# === Entry Point ===
def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  check register <name>")
        print("  check <problem_number>")
        return

    cmd = sys.argv[1]

    if cmd == "register":
        if len(sys.argv) < 3:
            print("[ERROR] You must provide a name.")
            return
        register(sys.argv[2])
    elif cmd == "reset":
        reset_state()
    elif cmd.isdigit():
        submit(int(cmd))
    else:
        print("[ERROR] Invalid command.")

if __name__ == "__main__":
    main()
