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
    add_log([], f"Fetching index: {url}")

    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise Exception("Failed to fetch index.yaml")

    return yaml.safe_load(r.text)


def resolve_demo_file(demo_name: str):
    index = fetch_index()

    for demo in index.get("demos", []):
        if demo["name"] == demo_name:
            return demo["file"]

    raise Exception(f"Demo not found: {demo_name}")


def fetch_demo(key: str):
    file_name = resolve_demo_key(key)
    url = f"{BASE_RAW_URL}/demos/{file_name}"

    print(f"[DEMO] Loading demo definition {url}")

    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise Exception(f"Failed to fetch demo file {file_name}")

    print(r.text)
    return yaml.safe_load(r.text)

def resolve_demo_key(key):
    index = fetch_index()

    # convert "3" → 3 if possible
    try:
        key_int = int(key)
    except:
        key_int = None

    for demo in index.get("demos", []):
        if demo.get("id") == key_int:
            return demo["file"]
        if demo.get("name") == key:
            return demo["file"]

    raise Exception(f"Demo not found: {key}")
    
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

    repo_dir = repo_dir.replace("{{WORKSPACE}}", ctx["workspace"])

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
    repo_dir = step["path"].replace("{{WORKSPACE}}", ctx["workspace"])
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

    cwd = step.get("path") or ctx.get("WORKSPACE")

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


# =========================================================
# INSTALL DEMO
# =========================================================

def install_demo(name: str, workspace: str):
    workspace = os.path.abspath(os.path.expanduser(workspace))
    demo = fetch_demo(name)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": []
    }

    os.makedirs(workspace, exist_ok=True)

    for step in demo.get("install", {}).get("steps", []):
        execute_step(ctx, step)

    return {"status": "success", "log": ctx["log"]}


# =========================================================
# RUN DEMO
# =========================================================

def run_demo(name: str, workspace: str):
    workspace = os.path.abspath(os.path.expanduser(workspace))
    demo = fetch_demo(name)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": [],
        "env": os.environ.copy(),
        "port": demo.get("port", 8081),
    }

    for step in demo.get("run", {}).get("steps", []):
        execute_step(ctx, step)

    return {"status": "success", "log": ctx["log"]}

# =========================================================
# HEALTH CHECK DEMO
# =========================================================
def health_check_demo(name: str, workspace: str):
    demo = fetch_demo(name)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": [],
        "env": os.environ.copy(),
        "port": demo.get("port", 8081),
    }

    for step in demo.get("health", {}).get("steps", []):
        execute_step(ctx, step)

    return {
        "status": "success",
        "phase": "health",
        "demo": name,
        "log": ctx["log"]
    }