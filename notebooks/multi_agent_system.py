# Databricks notebook source

# MAGIC %md
# MAGIC # Multi-Agent System with LangGraph Supervisor + Genie
# MAGIC
# MAGIC This notebook creates a **Multi-Agent Supervisor** that orchestrates:
# MAGIC - **Genie Agent** — queries structured data via natural language (your Genie space)
# MAGIC - **Knowledge Agent** — answers questions from unstructured documents (your existing KA endpoint)
# MAGIC
# MAGIC The supervisor (powered by an LLM) routes each user question to the most appropriate agent,
# MAGIC then synthesizes the final response.
# MAGIC
# MAGIC Once deployed as a **Model Serving endpoint**, you can plug it into your app's `config/app.json`
# MAGIC just like any other agent endpoint.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies

# COMMAND ----------

# DBTITLE 1,Install required packages
%pip install -U -qqqq databricks-langchain databricks-agents mlflow langgraph langgraph-supervisor langchain-core pyyaml
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Configuration
# MAGIC
# MAGIC Update these values to match your environment:

# COMMAND ----------

# DBTITLE 1,Configuration — update these values

# ╔══════════════════════════════════════════════════════════════╗
# ║              ⚠️  FILL IN THE VALUES BELOW  ⚠️               ║
# ╚══════════════════════════════════════════════════════════════╝

# 📌 GENIE SPACE
# Where to find it: Databricks > Genie > open your space
#   → the space ID is in the URL: /genie/rooms/<SPACE_ID>
GENIE_SPACE_ID = "01f10471a6bd1a59ab22df10a6edda2c"
GENIE_AGENT_NAME = "DataAnalyst"
GENIE_DESCRIPTION = (
    "Use this agent to answer questions about structured business data, "
    "metrics, KPIs, sales figures, inventory, and any data that lives in "
    "SQL tables. This agent can write and execute SQL queries."
)

# 📌 KNOWLEDGE AGENT (existing serving endpoint)
# Where to find it: Databricks > Serving > Endpoints
#   → copy the endpoint name
KA_ENDPOINT_NAME = "ka-0b0f263d-endpoint"
KA_AGENT_NAME = "KnowledgeAssistant"
KA_DESCRIPTION = (
    "Use this agent to answer questions about product documentation, "
    "technical specifications, manuals, policies, and any unstructured "
    "knowledge base content."
)

# 📌 SUPERVISOR LLM
# Where to find it: Databricks > Serving > Endpoints
#   → pick any Foundation Model endpoint
SUPERVISOR_LLM_ENDPOINT = "databricks-claude-sonnet-4"

# 📌 UNITY CATALOG MODEL NAME
# Where to find it: Databricks > Catalog
#   → format: "catalog.schema.model_name"
UC_MODEL_NAME = "users.hanane_oudnia.mas_supervisor_v2"

# 📌 SERVING ENDPOINT NAME (for deployment)
ENDPOINT_NAME = "Ghouse_houd_mas_supervisor_v2"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Enable MLflow Tracing

# COMMAND ----------

# DBTITLE 1,Enable MLflow autologging for LangChain/LangGraph
import mlflow

mlflow.langchain.autolog()

current_user = dbutils.notebook.entry_point.getDbutils().notebook().getContext().userName().get()
experiment_path = f"/Users/{current_user}/multi_agent_supervisor"
mlflow.set_experiment(experiment_path)
print(f"✅ Experiment set: {experiment_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Create the Genie Agent
# MAGIC
# MAGIC Uses `databricks-langchain`'s `GenieAgent` which wraps the Databricks Genie API
# MAGIC into a LangGraph-compatible node.

# COMMAND ----------

# DBTITLE 1,Create the Genie agent
from databricks_langchain.genie import GenieAgent

genie_agent = GenieAgent(
    space_id=GENIE_SPACE_ID,
    genie_agent_name=GENIE_AGENT_NAME,
    description=GENIE_DESCRIPTION,
)

print(f"✅ Genie agent created: {GENIE_AGENT_NAME} (space: {GENIE_SPACE_ID})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Create the Knowledge Agent (wrapping existing endpoint)

# COMMAND ----------

# DBTITLE 1,Create KA wrapper as a LangGraph tool
from langchain_core.tools import tool
from mlflow.deployments import get_deploy_client

deploy_client = get_deploy_client("databricks")


@tool
def knowledge_assistant(question: str) -> str:
    """Query the Knowledge Assistant for answers about product documentation,
    technical specs, manuals, policies, and unstructured knowledge base content.

    Args:
        question: The user's question to send to the knowledge assistant.

    Returns:
        The knowledge assistant's response text.
    """
    try:
        response = deploy_client.predict(
            endpoint=KA_ENDPOINT_NAME,
            inputs={
                "input": [{"role": "user", "content": question}],
                "databricks_options": {"return_trace": True},
            },
        )

        if isinstance(response, dict):
            output = response.get("output", "")
            if isinstance(output, str):
                return output
            if isinstance(output, dict):
                return output.get("content", str(output))
            if isinstance(output, list):
                for msg in output:
                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                        return msg.get("content", "")
                return str(output)
            return str(output)
        return str(response)

    except Exception as e:
        return f"Error querying Knowledge Assistant: {str(e)}"


print(f"✅ Knowledge Agent tool created: {KA_AGENT_NAME} (endpoint: {KA_ENDPOINT_NAME})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Build the KA Agent Node + Multi-Agent Supervisor

# COMMAND ----------

# DBTITLE 1,Create supervisor multi-agent graph
from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

# KA Agent (LLM + tool)
ka_llm = ChatDatabricks(endpoint=SUPERVISOR_LLM_ENDPOINT, temperature=0)
ka_agent = create_react_agent(
    model=ka_llm,
    tools=[knowledge_assistant],
    name=KA_AGENT_NAME,
    prompt=(
        "You are a Knowledge Assistant. Use the knowledge_assistant tool "
        "to answer questions from the document knowledge base."
    ),
)

# Supervisor
supervisor_llm = ChatDatabricks(endpoint=SUPERVISOR_LLM_ENDPOINT, temperature=0)
supervisor_graph = create_supervisor(
    agents=[genie_agent, ka_agent],
    model=supervisor_llm,
    prompt=(
        "You are a supervisor managing a team of specialized agents. "
        "Based on the user's question, decide which agent is best suited to answer:\n\n"
        f"1. **{GENIE_AGENT_NAME}**: {GENIE_DESCRIPTION}\n"
        f"2. **{KA_AGENT_NAME}**: {KA_DESCRIPTION}\n\n"
        "Rules:\n"
        "- Route data/metrics/SQL questions to the DataAnalyst\n"
        "- Route documentation/knowledge questions to the KnowledgeAssistant\n"
        "- If unsure, try the KnowledgeAssistant first\n"
        "- You may call multiple agents if the question spans both domains\n"
        "- Synthesize a clear, unified response from the agent outputs\n"
        "- Always be helpful and precise"
    ),
)

multi_agent = supervisor_graph.compile()
print("✅ Multi-agent supervisor graph compiled successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Test the Multi-Agent System

# COMMAND ----------

# DBTITLE 1,Test: General question
result = multi_agent.invoke({
    "messages": [{"role": "user", "content": "What can you help me with?"}]
})

for msg in result["messages"]:
    if hasattr(msg, "content") and msg.content:
        print(f"[{getattr(msg, 'name', msg.type)}]: {msg.content[:500]}")
        print("---")

# COMMAND ----------

# DBTITLE 1,Test: Knowledge question
result = multi_agent.invoke({
    "messages": [
        {"role": "user", "content": "How long does the rust protection last with RustBlock Enamel?"}
    ]
})

for msg in result["messages"]:
    if hasattr(msg, "content") and msg.content:
        print(f"[{getattr(msg, 'name', msg.type)}]: {msg.content[:500]}")
        print("---")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Write the Standalone Agent File + Config
# MAGIC
# MAGIC MLflow's "models from code" requires a **self-contained Python file** that doesn't
# MAGIC use `spark`, `dbutils`, or `%pip`. We write it from this notebook cell.
# MAGIC
# MAGIC Uses lazy initialization to prevent load failures in serving containers.

# COMMAND ----------

# DBTITLE 1,Write agent_config.yaml
import yaml

config = {
    "genie_space_id": GENIE_SPACE_ID,
    "genie_agent_name": GENIE_AGENT_NAME,
    "genie_description": GENIE_DESCRIPTION,
    "ka_endpoint_name": KA_ENDPOINT_NAME,
    "ka_agent_name": KA_AGENT_NAME,
    "ka_description": KA_DESCRIPTION,
    "supervisor_llm_endpoint": SUPERVISOR_LLM_ENDPOINT,
}

config_path = "/tmp/mas_supervisor_config.yaml"
with open(config_path, "w") as f:
    yaml.dump(config, f)

print(f"✅ Config written to {config_path}")
print(yaml.dump(config))

# COMMAND ----------

# DBTITLE 1,Write agent_driver.py (self-contained, lazy init)
agent_driver_code = '''"""Self-contained multi-agent supervisor driver for MLflow model serving.

Uses LAZY initialization - the agent graph is only built on the first predict call,
not at module import time. This prevents load failures in serving containers.

Uses langgraph-supervisor for the supervisor pattern with GenieAgent.
"""

import uuid
from typing import Generator, Optional

import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

# Load configuration from ModelConfig (YAML bundled with the model)
config = mlflow.models.ModelConfig(development_config="/tmp/mas_supervisor_config.yaml")
GENIE_SPACE_ID = config.get("genie_space_id")
GENIE_AGENT_NAME = config.get("genie_agent_name")
GENIE_DESCRIPTION = config.get("genie_description")
KA_ENDPOINT_NAME = config.get("ka_endpoint_name")
KA_AGENT_NAME = config.get("ka_agent_name")
KA_DESCRIPTION = config.get("ka_description")
SUPERVISOR_LLM_ENDPOINT = config.get("supervisor_llm_endpoint")


def _build_agent():
    """Build the multi-agent supervisor graph. Called lazily on first predict."""
    from databricks_langchain import ChatDatabricks
    from databricks_langchain.genie import GenieAgent
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent
    from langgraph_supervisor import create_supervisor
    from mlflow.deployments import get_deploy_client

    _deploy = get_deploy_client("databricks")

    # Genie Agent
    _genie_agent = GenieAgent(
        space_id=GENIE_SPACE_ID,
        genie_agent_name=GENIE_AGENT_NAME,
        description=GENIE_DESCRIPTION,
    )

    # KA Tool
    @tool
    def knowledge_assistant(question: str) -> str:
        """Query the Knowledge Assistant for documentation, technical specs,
        manuals, policies, and unstructured content."""
        try:
            resp = _deploy.predict(
                endpoint=KA_ENDPOINT_NAME,
                inputs={
                    "input": [{"role": "user", "content": question}],
                    "databricks_options": {"return_trace": True},
                },
            )
            if isinstance(resp, dict):
                out = resp.get("output", "")
                if isinstance(out, str):
                    return out
                if isinstance(out, list):
                    for m in out:
                        if isinstance(m, dict) and m.get("role") == "assistant":
                            return m.get("content", "")
                    return str(out)
                return str(out)
            return str(resp)
        except Exception as e:
            return f"Error: {e}"

    # KA Agent
    _ka_llm = ChatDatabricks(endpoint=SUPERVISOR_LLM_ENDPOINT, temperature=0)
    _ka_agent = create_react_agent(
        model=_ka_llm,
        tools=[knowledge_assistant],
        name=KA_AGENT_NAME,
        prompt=(
            "You are a Knowledge Assistant. Use the knowledge_assistant tool "
            "to answer questions from the document knowledge base."
        ),
    )

    # Supervisor
    _supervisor_llm = ChatDatabricks(endpoint=SUPERVISOR_LLM_ENDPOINT, temperature=0)
    _graph = create_supervisor(
        agents=[_genie_agent, _ka_agent],
        model=_supervisor_llm,
        prompt=(
            "You are a supervisor managing specialized agents. "
            "Route data/metrics/SQL questions to " + GENIE_AGENT_NAME + ". "
            "Route documentation/knowledge questions to " + KA_AGENT_NAME + ". "
            "Synthesize clear, unified responses."
        ),
    )
    return _graph.compile()


class MultiAgentSupervisor(ResponsesAgent):
    """MLflow ResponsesAgent with LAZY initialization for multi-agent supervisor."""

    def __init__(self):
        self._agent = None

    def _get_agent(self):
        if self._agent is None:
            self._agent = _build_agent()
        return self._agent

    def _extract_text_content(self, content):
        """Convert Responses API content to a plain string.

        The AI Playground sends assistant messages with content as a list
        of ResponseInputTextParam objects. LangGraph needs plain strings.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("text", str(item)))
                elif hasattr(item, "text"):
                    parts.append(item.text)
                else:
                    parts.append(str(item))
            return chr(10).join(parts)
        return str(content) if content else ""

    def _invoke_agent(self, request):
        """Shared logic: parse input, invoke agent, return final text."""
        agent = self._get_agent()

        messages = []
        for msg in request.input:
            if hasattr(msg, "role"):
                role = msg.role if hasattr(msg, "role") else "user"
                content = self._extract_text_content(
                    msg.content if hasattr(msg, "content") else ""
                )
                messages.append({"role": role, "content": content})
            elif isinstance(msg, dict):
                role = msg.get("role", "user")
                content = self._extract_text_content(msg.get("content", ""))
                messages.append({"role": role, "content": content})

        result = agent.invoke({"messages": messages})

        final = ""
        for m in reversed(result.get("messages", [])):
            msg_type = getattr(m, "type", None)
            if msg_type == "ai" and getattr(m, "content", ""):
                content = m.content
                if isinstance(content, str):
                    final = content
                    break

        return final or "I could not process your request."

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        final = self._invoke_agent(request)
        item_id = str(uuid.uuid4())
        output_item = self.create_text_output_item(text=final, id=item_id)
        return ResponsesAgentResponse(output=[output_item])

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        final = self._invoke_agent(request)
        item_id = str(uuid.uuid4())

        chunk_size = 50
        for i in range(0, len(final), chunk_size):
            yield ResponsesAgentStreamEvent(
                **self.create_text_delta(delta=final[i : i + chunk_size], item_id=item_id)
            )
        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=final, id=item_id),
        )


# Instance with lightweight __init__ (just self._agent = None)
mlflow.models.set_model(MultiAgentSupervisor())
'''

driver_path = "/tmp/mas_supervisor_driver.py"
with open(driver_path, "w") as f:
    f.write(agent_driver_code)

print(f"✅ Agent driver written to {driver_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Log the Agent to MLflow

# COMMAND ----------

# DBTITLE 1,Log model to MLflow
import mlflow

with mlflow.start_run(run_name="multi_agent_supervisor"):
    model_info = mlflow.pyfunc.log_model(
        python_model="/tmp/mas_supervisor_driver.py",
        artifact_path="multi_agent_supervisor",
        model_config="/tmp/mas_supervisor_config.yaml",
        pip_requirements=[
            "databricks-langchain>=0.14.0",
            "databricks-agents>=1.2.0",
            "mlflow>=3.1.3",
            "langgraph>=0.4",
            "langgraph-supervisor>=0.0.10",
            "langchain-core>=0.3",
            "pyyaml",
        ],
    )
    print(f"✅ Model logged: {model_info.model_uri}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Register in Unity Catalog

# COMMAND ----------

# DBTITLE 1,Register model in UC
mlflow.set_registry_uri("databricks-uc")
registered_model = mlflow.register_model(model_uri=model_info.model_uri, name=UC_MODEL_NAME)
print(f"✅ Registered: {UC_MODEL_NAME} v{registered_model.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Deploy to Model Serving Endpoint

# COMMAND ----------

# DBTITLE 1,Step 11a: Create secret scope + store token (one-time setup)
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

try:
    w.secrets.create_scope(scope="multi-agent-scope")
    print("✅ Secret scope created: multi-agent-scope")
except Exception as e:
    print(f"Secret scope already exists (OK): {e}")

w.secrets.put_secret(
    scope="multi-agent-scope",
    key="serving-token",
    string_value=dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get(),
)
print("✅ Token stored in secret")

# COMMAND ----------

# DBTITLE 1,Step 11b: Deploy endpoint (delete-first strategy)
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput
from databricks.sdk.errors import ResourceDoesNotExist
import time

served_entity = ServedEntityInput(
    entity_name=UC_MODEL_NAME,
    entity_version=str(registered_model.version),
    scale_to_zero_enabled=True,
    workload_size="Small",
    environment_vars={
        "DATABRICKS_HOST": "https://e2-demo-west.cloud.databricks.com",
        "DATABRICKS_TOKEN": "{{secrets/multi-agent-scope/serving-token}}",
    },
)

# Step 1: Delete the endpoint if it exists
try:
    existing = w.serving_endpoints.get(ENDPOINT_NAME)
    print(f"⚠️  Endpoint '{ENDPOINT_NAME}' exists (state: {existing.state}). Deleting...")
    w.serving_endpoints.delete(ENDPOINT_NAME)
    print("Waiting for deletion to complete...")
    for i in range(30):
        try:
            w.serving_endpoints.get(ENDPOINT_NAME)
            time.sleep(5)
        except ResourceDoesNotExist:
            print("✅ Endpoint deleted.")
            break
    else:
        print("⚠️  Deletion may still be in progress. Proceeding anyway...")
except ResourceDoesNotExist:
    print(f"No existing endpoint '{ENDPOINT_NAME}'. Creating fresh.")

# Step 2: Create from scratch
print(f"Creating endpoint: {ENDPOINT_NAME}")
w.serving_endpoints.create_and_wait(
    name=ENDPOINT_NAME,
    config=EndpointCoreConfigInput(
        name=ENDPOINT_NAME,
        served_entities=[served_entity],
    ),
)

print(f"✅ Endpoint ready: {ENDPOINT_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Test Deployed Endpoint

# COMMAND ----------

# DBTITLE 1,Test the deployed endpoint
from mlflow.deployments import get_deploy_client

client = get_deploy_client("databricks")

response = client.predict(
    endpoint=ENDPOINT_NAME,
    inputs={
        "input": [{"role": "user", "content": "What can you help me with?"}],
    },
)

print("Endpoint response:")
print(response)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Add to Your App
# MAGIC
# MAGIC Update `config/app.json`:
# MAGIC ```json
# MAGIC {
# MAGIC   "endpoint_name": "<your-endpoint-name>",
# MAGIC   "display_name": "Multi-Agent Supervisor",
# MAGIC   "question_examples": ["What can you help me with?"]
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC The app's existing `DatabricksEndpointHandler` will handle it automatically.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Architecture Summary
# MAGIC
# MAGIC ```
# MAGIC User Question
# MAGIC       │
# MAGIC       ▼
# MAGIC ┌─────────────────────┐
# MAGIC │   Supervisor LLM    │  ← Routes based on question type
# MAGIC │  (Claude/Llama/etc) │
# MAGIC └──────┬──────┬───────┘
# MAGIC        │      │
# MAGIC   ┌────▼──┐ ┌─▼─────────┐
# MAGIC   │ Genie │ │ Knowledge  │
# MAGIC   │ Agent │ │   Agent    │
# MAGIC   │(SQL)  │ │  (Docs)    │
# MAGIC   └───────┘ └────────────┘
# MAGIC        │      │
# MAGIC        ▼      ▼
# MAGIC ┌─────────────────────┐
# MAGIC │  Synthesized Answer │
# MAGIC └─────────────────────┘
# MAGIC ```
