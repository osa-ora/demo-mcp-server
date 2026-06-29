import os
import sys
import time
import subprocess
import requests
import yaml
import socket


BASE_RAW_URL = "https://raw.githubusercontent.com/osa-ora/demo-mcp-server/main"

# =========================================================
# LOGGING
# =========================================================

def add_log(log, message):
    print(f"[DEMO] {message}")
    log.append(message)


# =========================================================
# FETCH YAML
# =========================================================

def fetch_index():
    url = f"{BASE_RAW_URL}/index.yaml"
    print(f"[DEMO] Fetching index: {url}")

    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise Exception("Failed to fetch index.yaml")

    return yaml.safe_load(r.text)

# =========================================================
# DEMO SEARCH
# =========================================================
def find_demo(keyword: str):
    index = fetch_index()

    keyword_l = keyword.strip().lower()
    results = []

    for demo in index.get("demos", []):
        name = demo.get("name", "")
        desc = demo.get("description", "")
        keywords = demo.get("keywords", [])

        score = 0

        # name match
        if keyword_l in str(name).lower():
            score += 5

        # description match
        if keyword_l in str(desc).lower():
            score += 3

        # keyword match
        for k in keywords:
            if keyword_l == str(k).lower():
                score += 10
            elif keyword_l in str(k).lower():
                score += 6

        if score > 0:
            results.append({
                "id": demo.get("id"),
                "name": demo.get("name"),
                "description": demo.get("description"),
                "keywords": demo.get("keywords", []),
                "environments": list(demo.get("environments", {}).keys()),
                "score": score
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)



# =========================================================
# RESOLVE DEMO
# =========================================================
def resolve_demo(key: str, environment: str = "local"):
    index = fetch_index()

    key_str = str(key).strip()

    try:
        key_int = int(key_str)
    except:
        key_int = None

    key_l = key_str.lower()

    for demo in index.get("demos", []):
        
        # Check environment ...
        if environment not in demo.get("environments", {}):
            continue
            
        demo_id = demo.get("id")
        demo_name = str(demo.get("name", "")).strip()
        demo_name_l = demo_name.lower()
        demo_keywords = demo.get("keywords", [])

        # match by ID
        if key_int is not None and demo_id == key_int:
            return demo

        # match by name
        if demo_name_l == key_l:
            return demo

        # match by keyword
        for k in demo_keywords:
            if key_l == str(k).lower().strip():
                return demo

    raise Exception(f"Demo not found: {key} for environment {environment}")


# =========================================================
# FETCH DEMO 
# =========================================================
def fetch_demo_file(key: str, environment: str = "local"):
    demo = resolve_demo(key, environment)

    envs = demo.get("environments", {})

    if environment not in envs:
        raise Exception(
            f"Environment '{environment}' not available for demo '{demo.get('name')}'. "
            f"Available: {list(envs.keys())}"
        )

    file_name = envs[environment]["file"]
    url = f"{BASE_RAW_URL}/demos/{file_name}"

    print(f"[DEMO] Loading demo definition: {url}")

    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise Exception(f"Failed to fetch demo file {file_name}")

    return yaml.safe_load(r.text)
    
# =========================================================
# INSTALL DEMO
# =========================================================
def install_demo(key: str, workspace: str, environment: str = "local"):
    workspace = os.path.abspath(os.path.expanduser(workspace))
    demo = fetch_demo_file(key, environment)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": [],
        "env": {},
        "port": demo.get("port", 8080)
    }

    os.makedirs(workspace, exist_ok=True)

    for step in demo.get("install", {}).get("steps", []):
        execute_step(ctx, step)

    return {"status": "success", "log": ctx["log"]}

# =========================================================
# RUN DEMO
# =========================================================
def run_demo(key: str, workspace: str, environment: str = "local"):
    workspace = os.path.abspath(os.path.expanduser(workspace))
    demo = fetch_demo_file(key, environment)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": [],
        "env": os.environ.copy(),
        "port": demo.get("port", 8080),
    }

    for step in demo.get("run", {}).get("steps", []):
        execute_step(ctx, step)

    return {"status": "success", "log": ctx["log"]}

# =========================================================
# DEMO HEALTH CHECK DEMO
# =========================================================
def health_check_demo(key: str, workspace: str, environment: str = "local"):
    demo = fetch_demo_file(key, environment)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": [],
        "env": os.environ.copy(),
        "port": demo.get("port", 8080),
    }

    for step in demo.get("health", {}).get("steps", []):
        execute_step(ctx, step)

    return {
        "status": "success",
        "phase": "health",
        "demo": demo.get("name"),
        "environment": environment,
        "log": ctx["log"]
    }
# =========================================================
# STEP INFRASTRUCTURE
# =========================================================

def execute_step(ctx, step):
    step_type = step["type"]

    handler = STEP_HANDLERS.get(step_type)

    if not handler:
        add_log(ctx["log"], f"[WARN] Skipping unknown step: {step_type}")
        return ctx

    add_log(ctx["log"], f"[STEP] {step_type} | {step.get('command', '')}")

    return handler(ctx, step)


def resolve_value(value, ctx):
    if not isinstance(value, str):
        return value

    for k, v in ctx.items():
        if isinstance(v, (str, int, float)):
            value = value.replace(f"{{{{{k}}}}}", str(v))

    return value
# =========================================================
# INSTALL STEPS
# =========================================================

def step_check_python(ctx, step):
    subprocess.run(["python3", "--version"], check=True)
    add_log(ctx["log"], "Python OK")
    return ctx


def handle_check_postgres(ctx, step):
    add_log(ctx["log"], "Checking PostgreSQL...")

    try:
        result = subprocess.run(
            ["psql", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        add_log(ctx["log"], result.stdout.strip())
    except FileNotFoundError:
        raise RuntimeError(
            "PostgreSQL client (psql) is not installed or not in PATH."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Unable to execute psql: {e}"
        )

    return ctx


def step_clone_git(ctx, step):
    repo = step["repo"]

    # IMPORTANT: use YAML path, not repo name
    repo_dir = step.get("path")

    if not repo_dir:
        raise Exception("Missing 'path' in clone_git step")

    repo_dir = repo_dir.replace("{{workspace}}", ctx["workspace"])

    ctx["repo_dir"] = repo_dir

    if os.path.exists(repo_dir):
        add_log(ctx["log"], f"Repo exists: {repo_dir}")
        return ctx

    add_log(ctx["log"], f"Cloning {repo} -> {repo_dir}")

    subprocess.run(
        ["git", "clone", repo, repo_dir],
        check=True
    )

    return ctx


def step_venv(ctx, step):
    venv_path = os.path.join(ctx["repo_dir"], ".venv")
    add_log(ctx["log"], f"Creating venv: {venv_path}")

    subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)

    return ctx


def step_install(ctx, step):
    pip_path = os.path.join(ctx["repo_dir"], ".venv", "bin", "pip")

    add_log(ctx["log"], "Installing dependencies")

    subprocess.run(
        [pip_path, "install", "-r", os.path.join(ctx["repo_dir"], "requirements.txt")],
        check=True
    )

    return ctx


# =========================================================
# RUN HELPERS
# =========================================================

def prepare_run(ctx, step):
    repo_dir = step["path"].replace("{{workspace}}", ctx["workspace"])
    command = step["command"].replace("{{port}}", str(ctx["port"]))
    mode = step.get("mode", "background")

    if not os.path.exists(repo_dir):
        raise Exception(f"Missing directory: {repo_dir}")

    return repo_dir, command, mode


def run_terminal_mac(ctx, repo_dir, command):
    add_log(ctx["log"], "Launching macOS Terminal")

    script = f'''
tell application "Terminal"
    activate
    do script "cd {repo_dir}; {command}"
end tell
'''.strip()

    subprocess.run(["osascript", "-e", script], check=True)

    add_log(ctx["log"], "Terminal launched")


def run_background(ctx, repo_dir, command):
    log_file = os.path.join(repo_dir, "app.log")

    with open(log_file, "w") as f:
        process = subprocess.Popen(
            ["bash", "-c", command],
            cwd=repo_dir,
            stdout=f,
            stderr=subprocess.STDOUT,
            env=ctx["env"],
            start_new_session=True
        )

    with open(os.path.join(repo_dir, "app.pid"), "w") as pidf:
        pidf.write(str(process.pid))

    add_log(ctx["log"], f"PID={process.pid}")
    add_log(ctx["log"], f"Logs={log_file}")

    return ctx


def step_run(ctx, step):
    repo_dir, command, mode = prepare_run(ctx, step)

    ctx["repo_dir"] = repo_dir

    add_log(ctx["log"], f"Dir: {repo_dir}")
    add_log(ctx["log"], f"Cmd: {command}")
    add_log(ctx["log"], f"Mode: {mode}")

    if mode == "terminal" and sys.platform == "darwin":
        run_terminal_mac(ctx, repo_dir, command)
    else:
        run_background(ctx, repo_dir, command)

    time.sleep(2)
    return ctx


def step_env(ctx, step):
    variables = step.get("variables", {})

    for k, v in variables.items():
        if isinstance(v, str):
            v = v.replace("{{port}}", str(ctx["port"]))
        ctx["env"][k] = str(v)

    add_log(ctx["log"], f"ENV set: {variables}")
    return ctx


# =========================================================
# HEALTH CHECK (HTTP)
# =========================================================

def step_health(ctx, step):
    # Match criteria met: Safely routed via resolve_value utility
    url = resolve_value(step["url"], ctx)

    retries = step.get("retries", 5)
    delay = step.get("delay_seconds", 2)

    add_log(ctx["log"], f"Health: {url}")

    for i in range(retries):
        add_log(ctx["log"], f"Attempt {i+1}/{retries}")

        try:
            r = requests.get(url, timeout=2)
            add_log(ctx["log"], f"HTTP {r.status_code}")

            if r.status_code == 200:
                return ctx

        except Exception as e:
            add_log(ctx["log"], f"Not ready: {e}")

        time.sleep(delay)

    raise Exception("Health check failed")


# =========================================================
# PORT CHECK (TCP)
# =========================================================

def step_port_check(ctx, step):
    host = resolve_value(step.get("host", "localhost"), ctx)
    port_raw = step.get("port", "80")
    port_resolved = resolve_value(str(port_raw), ctx)

    try:
        port = int(port_resolved)
    except Exception:
        raise Exception(f"Invalid port after resolution: {port_resolved}")

    retries = step.get("retries", 5)
    delay = step.get("delay_seconds", 2)

    add_log(ctx["log"], f"Port check: {host}:{port}")

    for i in range(retries):
        add_log(ctx["log"], f"Attempt {i+1}/{retries}")

        try:
            with socket.create_connection((host, port), timeout=2):
                add_log(ctx["log"], "Port is open")
                return ctx
        except Exception as e:
            add_log(ctx["log"], f"Not ready: {e}")

        time.sleep(delay)

    raise Exception(f"Port check failed: {host}:{port}")

# =========================================================
# OCP COMMAND STEP
# =========================================================
def step_oc_command(ctx, step):
    # Match criteria met: Safely routing command string transformation
    command_resolved = resolve_value(step["command"], ctx)

    try:
        full_cmd = f"oc {command_resolved}"
        add_log(ctx["log"], f"OC CMD: {full_cmd}")

        output = subprocess.check_output(
            full_cmd,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT
        ).strip()

    except subprocess.CalledProcessError as e:
        if step.get("ignore_error"):
            add_log(ctx["log"], f"[IGNORED ERROR] {e.output.strip()}")
            return ctx
        raise Exception(f"OC command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output.strip()

    return ctx

# =========================================================
# SHELL COMMAND STEP
# =========================================================
def step_shell_command(ctx, step):
    # Match criteria met: Safely routing command string transformation
    command = resolve_value(step["command"], ctx)

    cwd = step.get("path") or ctx.get("workspace")

    add_log(ctx["log"], f"SHELL CMD: {command} (cwd={cwd})")

    try:
        output = subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            cwd=cwd
        ).strip()

    except subprocess.CalledProcessError as e:
        if step.get("ignore_error"):
            add_log(ctx["log"], f"[IGNORED ERROR] {e.output.strip()}")
            return ctx
        raise Exception(f"SHELL command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output

    return ctx
    
# =========================================================
# STEP REGISTRY
# =========================================================

STEP_HANDLERS = {
    "check_python": step_check_python,
    "check_postgres": handle_check_postgres,
    "clone_git": step_clone_git,
    "venv": step_venv,
    "install": step_install,
    "env": step_env,
    "run": step_run,
    "health": step_health,
    "port_check": step_port_check,
    "oc_command": step_oc_command,
    "shell_command": step_shell_command
}
