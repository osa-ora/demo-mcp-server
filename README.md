# Demo Installation MCP Server
This MCP Server is dedicated to build my custom demos, either locally or on OpenShift cluster.

The MCP Server expose the following functions:
- list_demos
- find_demo
- get_demo_details
- get_demo_prerequisites
- install_demo
- run_demo
- health_check_demo


<img width="2816" height="1536" alt="component_diagram" src="https://github.com/user-attachments/assets/6c40dcbb-6b91-49c4-b7bf-16117251a772" />



The list of Demos are stored in the index.yaml file which in turn reference the demo detailed file inside the /demos folder.

---

## 🛠️ Configuration (.env)
Create a `.env` file in the root folder if you need to override the defaults, otherwise you can keep the defaults:

```
DEBUG=false
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_PORT=8085
```

---

## 🚀 The Easiest Way to Run It

1. Clone the repository to a local folder:

```bash
git clone https://github.com/osa-ora/demo-mcp-server.git
cd demo-mcp-server

```


2. Install the Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

3. Run the MCP server:

```bash
python demo_mcp_server.py

```

4. Open any chat client like ChatBox:

Configure the Ollama with a local model such as 'llama3.1:latest'
Configure the Demo MCP server as the following screen shot:

<img width="774" height="673" alt="Screenshot 2026-06-29 at 1 14 23 PM" src="https://github.com/user-attachments/assets/e21b72e4-2501-46e1-b513-56665fee6939" />

5. Chat with the server:

You can try the following examples:

```text
List all demos
List prerequisites for MCP Server Client Orchestrator on local environment
Details of HR demo
Details of demo: HR environment: openshift
What prerequisites for demo 3
Install Weather Demo on /tmp/demos/
Run Weather demo on /tmp/demos/
Can you list openshift demos?
```

<img width="1426" height="882" alt="Screenshot 2026-06-29 at 1 18 34 PM" src="https://github.com/user-attachments/assets/4f32f59e-385c-4d01-9f89-3bb97db36bf2" />

---

## 💡 Notes on Tools

* **Flexible Lookups:** Every tool takes a `key` parameter. The LLM can automatically look up your demos using either the string **Name** (e.g., `Local HR MCP Server Demo`) or the numeric **ID** (e.g., `3`) or even by **keywords** (e.g.,`HR`, `Weather`).

* **Workspaces:** If you don't provide a custom workspace path to the install, run, or health check tools, they will automatically default to `/tmp/mcp-workspace`.
* **Environments:** If you don't provide the target environment, it will automatically default to `local`.
