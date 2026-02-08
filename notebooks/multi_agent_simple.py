# Databricks notebook source

# MAGIC %md
# MAGIC # Simple Multi-Agent System (No langgraph-supervisor dependency)
# MAGIC
# MAGIC A lightweight alternative that uses **ChatDatabricks with tool-calling** as the
# MAGIC supervisor. The LLM decides which tool (agent) to call based on the question.
# MAGIC
# MAGIC This approach is simpler, has fewer dependencies, and gives you full control.
# MAGIC
# MAGIC **Agents:**
# MAGIC - **Genie** — structured data queries (SQL)
# MAGIC - **Knowledge Assistant** — unstructured document queries

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies

# COMMAND ----------

%pip install -U -qqqq databricks-langchain databricks-agents mlflow langchain-core langgraph pyyaml
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Configuration

# COMMAND ----------

# ╔══════════════════════════════════════════════════════╗
# ║           ⚠️  FILL IN THE VALUES BELOW  ⚠️           ║
# ╚══════════════════════════════════════════════════════╝

# 📌 GENIE SPACE ID
# Where to find it: Databricks > Genie > open your space
#   → the ID is in the URL: /genie/rooms/<SPACE_ID>
GENIE_SPACE_ID = "01f10471a6bd1a59ab22df10a6edda2c"

# 📌 KNOWLEDGE AGENT ENDPOINT
# Where to find it: Databricks > Serving > Endpoints
#   → copy the endpoint name
KA_ENDPOINT_NAME = "ka-0b0f263d-endpoint"

# 📌 SUPERVISOR LLM ENDPOINT
# Where to find it: Databricks > Serving > Endpoints
#   → pick any Foundation Model endpoint
SUPERVISOR_LLM_ENDPOINT = "databricks-claude-sonnet-4"

# 📌 UNITY CATALOG MODEL NAME
# Where to find it: Databricks > Catalog
#   → pick a catalog.schema you have write access to
UC_MODEL_NAME = "users.hanane_oudnia.mas_model_sim"

# 📌 SERVING ENDPOINT NAME (for deployment)
# Choose a name for the new endpoint that will be created
ENDPOINT_NAME = "Ghouse_houd_mas_cust"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Setup MLflow Tracing

# COMMAND ----------

import mlflow

mlflow.langchain.autolog()

# Get current user (notebook-safe)
current_user = dbutils.notebook.entry_point.getDbutils().notebook().getContext().userName().get()
experiment_path = f"/Users/{current_user}/multi_agent_simple"
mlflow.set_experiment(experiment_path)
print(f"✅ Experiment set: {experiment_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Define Agent Tools & Test Interactively

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from datetime import timedelta
from langchain_core.tools import tool
from mlflow.deployments import get_deploy_client

deploy_client = get_deploy_client("databricks")
ws_client = WorkspaceClient()


@tool
def query_data_analyst(question: str) -> str:
    """Query structured business data using natural language. Use this for questions
    about metrics, KPIs, sales figures, inventory, financial data, or anything
    that requires querying SQL tables and databases.

    Args:
        question: A natural language question about business data.

    Returns:
        The data analysis result, potentially including SQL queries and data tables.
    """
    try:
        msg = ws_client.genie.start_conversation_and_wait(
            space_id=GENIE_SPACE_ID,
            content=question,
            timeout=timedelta(minutes=3),
        )

        parts = []
        status = getattr(msg, "status", None)
        status_str = status.value if hasattr(status, "value") else str(status)

        if status_str == "FAILED":
            error = getattr(msg, "error", "Query failed")
            return f"Data query failed: {error}"

        attachments = getattr(msg, "attachments", None) or []
        conversation_id = getattr(msg, "conversation_id", "")
        message_id = getattr(msg, "message_id", "")
        query_attachment_id = None

        for att in attachments:
            text_obj = getattr(att, "text", None)
            if text_obj:
                content = getattr(text_obj, "content", None)
                if content:
                    parts.append(str(content))

            query_obj = getattr(att, "query", None)
            if query_obj:
                sql = getattr(query_obj, "query", None)
                if sql:
                    parts.append(f"\nSQL: {sql}")
                desc = getattr(query_obj, "description", None)
                if desc:
                    parts.append(str(desc))
                att_id = getattr(att, "id", None)
                if att_id:
                    query_attachment_id = str(att_id)

        if query_attachment_id and message_id:
            try:
                result = ws_client.genie.get_message_attachment_query_result(
                    space_id=GENIE_SPACE_ID,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    attachment_id=query_attachment_id,
                )
                stmt = getattr(result, "statement_response", None)
                if stmt:
                    manifest = getattr(stmt, "manifest", None)
                    schema = getattr(manifest, "schema", None) if manifest else None
                    columns = []
                    if schema:
                        schema_cols = getattr(schema, "columns", None) or []
                        columns = [getattr(c, "name", f"col_{i}") for i, c in enumerate(schema_cols)]
                    result_obj = getattr(stmt, "result", None)
                    data_array = getattr(result_obj, "data_array", None) if result_obj else None
                    if columns and data_array:
                        header = "| " + " | ".join(columns) + " |"
                        sep = "| " + " | ".join("---" for _ in columns) + " |"
                        rows = []
                        for row in list(data_array)[:50]:
                            rows.append("| " + " | ".join(str(v) if v is not None else "" for v in row) + " |")
                        table = "\n".join([header, sep] + rows)
                        if len(list(data_array)) > 50:
                            table += f"\n\n*Showing 50 of {len(list(data_array))} rows*"
                        parts.append(f"\nResults:\n{table}")
            except Exception as e:
                parts.append(f"\n(Could not fetch query results: {e})")

        return "\n".join(parts) if parts else "No results returned from data analysis."

    except Exception as e:
        return f"Error querying data: {str(e)}"


@tool
def query_knowledge_base(question: str) -> str:
    """Query the knowledge base for answers about product documentation, technical
    specifications, manuals, policies, procedures, and any unstructured content.

    Args:
        question: A question about documentation or knowledge base content.

    Returns:
        The knowledge base response.
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
            if isinstance(output, list):
                for msg in output:
                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                        return msg.get("content", "")
                return str(output)
            return str(output)
        return str(response)

    except Exception as e:
        return f"Error querying knowledge base: {str(e)}"


print("✅ Tools defined: query_data_analyst, query_knowledge_base")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Build & Test the Agent

# COMMAND ----------

from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent

llm = ChatDatabricks(endpoint=SUPERVISOR_LLM_ENDPOINT, temperature=0)

SYSTEM_PROMPT = """You are a helpful multi-agent assistant with access to two specialized tools:

1. **query_data_analyst** — Use this for questions about structured data, metrics, KPIs,
   sales figures, inventory, SQL queries, and database records.

2. **query_knowledge_base** — Use this for questions about documentation, technical specs,
   manuals, policies, procedures, and unstructured knowledge content.

Guidelines:
- Analyze the user's question and pick the most appropriate tool
- You may call both tools if the question spans multiple domains
- Synthesize tool results into a clear, well-formatted response
- If a tool returns an error, explain it and suggest alternatives
- Be precise, helpful, and professional
"""

agent = create_react_agent(
    model=llm,
    tools=[query_data_analyst, query_knowledge_base],
    prompt=SYSTEM_PROMPT,
)

print("✅ ReAct agent created with supervisor LLM + tools")

# COMMAND ----------

# DBTITLE 1,Test: General question
result = agent.invoke({
    "messages": [{"role": "user", "content": "What can you help me with?"}]
})

for msg in result["messages"]:
    role = getattr(msg, "type", "unknown")
    content = getattr(msg, "content", "")
    if content and isinstance(content, str) and role in ("ai", "human"):
        name = getattr(msg, "name", role)
        print(f"[{name}]: {content[:500]}")
        print("---")

# COMMAND ----------

# DBTITLE 1,Test: Knowledge question
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "How long does rust protection last with RustBlock Enamel?"}
    ]
})

for msg in result["messages"]:
    role = getattr(msg, "type", "unknown")
    content = getattr(msg, "content", "")
    if content and isinstance(content, str) and role == "ai":
        print(f"[Assistant]: {content[:1000]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Write the Standalone Agent File + Config
# MAGIC
# MAGIC MLflow's "models from code" requires a **self-contained Python file** that doesn't
# MAGIC use `spark`, `dbutils`, or `%pip`. We write it from this notebook cell.
# MAGIC
# MAGIC **Key fix**: Uses lazy initialization — the agent is only built on the first
# MAGIC `predict` call, NOT at module import time. This prevents load failures in serving.

# COMMAND ----------

# DBTITLE 1,Write agent_config.yaml
import yaml

config = {
    "genie_space_id": GENIE_SPACE_ID,
    "ka_endpoint_name": KA_ENDPOINT_NAME,
    "supervisor_llm_endpoint": SUPERVISOR_LLM_ENDPOINT,
}

config_path = "/tmp/multi_agent_config.yaml"
with open(config_path, "w") as f:
    yaml.dump(config, f)

print(f"✅ Config written to {config_path}")
print(yaml.dump(config))

# COMMAND ----------

# DBTITLE 1,Write agent_driver.py (self-contained, lazy init)
agent_driver_code = '''"""Self-contained multi-agent driver for MLflow model serving.

Uses LAZY initialization - the agent is only built on the first predict call,
not at module import time. This prevents load failures in serving containers.
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
config = mlflow.models.ModelConfig(development_config="/tmp/multi_agent_config.yaml")
GENIE_SPACE_ID = config.get("genie_space_id")
KA_ENDPOINT_NAME = config.get("ka_endpoint_name")
SUPERVISOR_LLM_ENDPOINT = config.get("supervisor_llm_endpoint")


def _build_agent():
    """Build the LangGraph agent. Called lazily on first predict call only."""
    from datetime import timedelta

    from databricks.sdk import WorkspaceClient
    from databricks_langchain import ChatDatabricks
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent
    from mlflow.deployments import get_deploy_client

    _deploy = get_deploy_client("databricks")
    _ws = WorkspaceClient()

    @tool
    def query_data(question: str) -> str:
        """Query structured business data using natural language via Genie.
        Use for metrics, KPIs, sales, inventory, SQL tables, and databases."""
        try:
            msg = _ws.genie.start_conversation_and_wait(
                space_id=GENIE_SPACE_ID,
                content=question,
                timeout=timedelta(minutes=3),
            )
            parts = []
            status = getattr(msg, "status", None)
            status_str = status.value if hasattr(status, "value") else str(status)
            if status_str == "FAILED":
                return f"Data query failed: {getattr(msg, 'error', 'Unknown error')}"

            attachments = getattr(msg, "attachments", None) or []
            conversation_id = getattr(msg, "conversation_id", "")
            message_id = getattr(msg, "message_id", "")
            query_attachment_id = None

            for att in attachments:
                text_obj = getattr(att, "text", None)
                if text_obj:
                    c = getattr(text_obj, "content", None)
                    if c:
                        parts.append(str(c))
                query_obj = getattr(att, "query", None)
                if query_obj:
                    sql = getattr(query_obj, "query", None)
                    if sql:
                        parts.append(f"SQL: {sql}")
                    desc = getattr(query_obj, "description", None)
                    if desc:
                        parts.append(str(desc))
                    att_id = getattr(att, "id", None)
                    if att_id:
                        query_attachment_id = str(att_id)

            if query_attachment_id and message_id:
                try:
                    qr = _ws.genie.get_message_attachment_query_result(
                        space_id=GENIE_SPACE_ID,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        attachment_id=query_attachment_id,
                    )
                    stmt = getattr(qr, "statement_response", None)
                    if stmt:
                        manifest = getattr(stmt, "manifest", None)
                        schema = getattr(manifest, "schema", None) if manifest else None
                        columns = []
                        if schema:
                            cols = getattr(schema, "columns", None) or []
                            columns = [getattr(c, "name", f"col_{i}") for i, c in enumerate(cols)]
                        result_obj = getattr(stmt, "result", None)
                        data_array = getattr(result_obj, "data_array", None) if result_obj else None
                        if columns and data_array:
                            header = "| " + " | ".join(columns) + " |"
                            sep = "| " + " | ".join("---" for _ in columns) + " |"
                            rows = []
                            for row in list(data_array)[:50]:
                                rows.append("| " + " | ".join(str(v) if v is not None else "" for v in row) + " |")
                            parts.append("Results:" + chr(10) + chr(10).join([header, sep] + rows))
                except Exception as e:
                    parts.append(f"(Could not fetch results: {e})")

            return chr(10).join(parts) or "No results returned."
        except Exception as e:
            return f"Error querying data: {e}"

    @tool
    def query_knowledge(question: str) -> str:
        """Query the knowledge base for documentation, technical specs,
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
            return f"Error querying knowledge base: {e}"

    _llm = ChatDatabricks(endpoint=SUPERVISOR_LLM_ENDPOINT, temperature=0)
    return create_react_agent(
        model=_llm,
        tools=[query_data, query_knowledge],
        prompt=(
            "You are a helpful multi-agent assistant." + chr(10)
            + "Use query_data for data/metrics/SQL/KPI questions." + chr(10)
            + "Use query_knowledge for documentation/knowledge questions." + chr(10)
            + "You may call both tools if needed. Synthesize clear responses."
        ),
    )


class SimpleMultiAgent(ResponsesAgent):
    """MLflow ResponsesAgent with LAZY initialization.

    The agent graph is NOT built at __init__ time.
    It is built on the first predict call via _get_agent().
    This ensures the model loads successfully in serving containers.
    """

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
            if getattr(m, "type", None) == "ai" and getattr(m, "content", ""):
                final = m.content
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


# Pass the CLASS (not an instance) so __init__ does NOT run at import time
mlflow.models.set_model(SimpleMultiAgent())
'''

driver_path = "/tmp/agent_driver.py"
with open(driver_path, "w") as f:
    f.write(agent_driver_code)

print(f"✅ Agent driver written to {driver_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Log the Agent to MLflow
# MAGIC
# MAGIC Now we log the **standalone agent file** (not the notebook), with the YAML config.

# COMMAND ----------

# DBTITLE 1,Log model to MLflow
import mlflow

with mlflow.start_run(run_name="multi_agent_simple"):
    model_info = mlflow.pyfunc.log_model(
        python_model="/tmp/agent_driver.py",
        artifact_path="multi_agent_simple",
        model_config="/tmp/multi_agent_config.yaml",
        pip_requirements=[
            "databricks-langchain>=0.14.0",
            "databricks-agents>=1.2.0",
            "mlflow>=3.1.3",
            "langgraph>=0.4",
            "langchain-core>=0.3",
            "pyyaml",
        ],
    )
    print(f"✅ Model logged: {model_info.model_uri}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Register in Unity Catalog

# COMMAND ----------

# DBTITLE 1,Register model in UC
mlflow.set_registry_uri("databricks-uc")
reg = mlflow.register_model(model_uri=model_info.model_uri, name=UC_MODEL_NAME)
print(f"✅ Registered: {UC_MODEL_NAME} v{reg.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Deploy to Model Serving Endpoint
# MAGIC
# MAGIC First deletes any stuck endpoint, then creates fresh.

# COMMAND ----------

# DBTITLE 1,Step 9a: Create secret scope + store token (one-time setup)
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Create a secret scope (skip if already exists)
try:
    w.secrets.create_scope(scope="multi-agent-scope")
    print("✅ Secret scope created: multi-agent-scope")
except Exception as e:
    print(f"Secret scope already exists (OK): {e}")

# Store your PAT as a secret
w.secrets.put_secret(
    scope="multi-agent-scope",
    key="serving-token",
    string_value=dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get(),
)
print("✅ Token stored in secret")

# COMMAND ----------

# DBTITLE 1,Step 9b: Deploy endpoint (delete-first strategy)
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput
from databricks.sdk.errors import ResourceDoesNotExist
import time

served_entity = ServedEntityInput(
    entity_name=UC_MODEL_NAME,
    entity_version=str(reg.version),
    scale_to_zero_enabled=True,
    workload_size="Small",
    environment_vars={
        "DATABRICKS_HOST": "https://e2-demo-west.cloud.databricks.com",
        "DATABRICKS_TOKEN": "{{secrets/multi-agent-scope/serving-token}}",
    },
)

# Step 1: Delete the endpoint if it exists (avoids UPDATE_FAILED issues)
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
# MAGIC ## 10. Test Deployed Endpoint

# COMMAND ----------

from mlflow.deployments import get_deploy_client

client = get_deploy_client("databricks")
resp = client.predict(
    endpoint=ENDPOINT_NAME,
    inputs={"input": [{"role": "user", "content": "What can you help me with?"}]},
)
print(resp)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Add to Your App
# MAGIC
# MAGIC Update `config/app.json`:
# MAGIC ```json
# MAGIC {
# MAGIC   "endpoint_name": "Ghouse_houd_mas_cust",
# MAGIC   "display_name": "Multi-Agent Assistant",
# MAGIC   "question_examples": ["What can you help me with?"]
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC The app's existing `DatabricksEndpointHandler` will handle it automatically —
# MAGIC no code changes needed in the app.
