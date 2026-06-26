# Demo Installation MCP Server
This MCP Server is dedicated to build my custom demos, either locally or on OpenShift cluster.

The MCP Server expose the following functions:
- list_demos
- get_demo
- get_demo_prerequisites
- install_demo
- run_demo
- health_check_demo

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

<img width="769" height="672" alt="Screenshot 2026-06-26 at 1 59 40 PM" src="https://github.com/user-attachments/assets/f4dd0bf9-718e-44b3-88ee-c27397e79504" />

5. Chat with the server:

You can try the following examples:

```text
List demos
What prerequisites for demo Local MCP Server Client Orchestrator
What prerequisites for demo 3
Details of Local HR MCP Server Demo
Install demo 3
Install Local Weather MCP Server Demo
Run demo 1 and 3 and 5
How many of the demos are local and how many are on openshift?
Health check demo number 3

```

<img width="777" height="674" alt="Screenshot 2026-06-26 at 2 15 46 PM" src="https://github.com/user-attachments/assets/fe614e7c-bffd-4c7f-a92d-2141dbbb9792" />


---

## 💡 Notes on Tools

* **Flexible Lookups:** Every tool takes a `key` parameter. The LLM can automatically look up your demos using either the string **Name** (e.g., `Local HR MCP Server Demo`) or the numeric **ID** (e.g., `3`).
* **Workspaces:** If you don't provide a custom workspace path to the install, run, or health check tools, they will automatically default to `/tmp/mcp-workspace`.


