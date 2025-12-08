"""Agent invocation and feedback endpoints."""

import logging
import uuid
from datetime import datetime
from typing import Optional, Type, Union

import mlflow
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from mlflow import MlflowClient
from pydantic import BaseModel

from ..agents.handlers import BaseDeploymentHandler, DatabricksEndpointHandler
from ..config_loader import config_loader

logger = logging.getLogger(__name__)
router = APIRouter()

# Feedback linking configuration
# NOTE: This is a workaround, not a final solution
# We search FORWARD from router trace creation because agent traces are always
# created AT or AFTER the router trace (never before)
# See docs/features/feedback.md for limitations and future improvements
TRACE_TIME_WINDOW_SECONDS = 3  # Time window for finding agent traces (forward-only)


def find_trace_for_feedback(
    client_request_id: str, agent_config: dict, mlflow_client: MlflowClient
) -> Optional[str]:
    """Find the appropriate MLflow trace for logging feedback.

    Strategy depends on deployment type:
    - databricks-endpoint: Time-proximity linking (finds agent's server-side trace)
    - Future types: May use direct trace linking

    Args:
      client_request_id: The client request ID to search for
      agent_config: Agent configuration from agents.json
      mlflow_client: MLflow client instance

    Returns:
      MLflow trace ID to log feedback to, or None if not found
    """
    deployment_type = agent_config.get("deployment_type", "databricks-endpoint")
    experiment_id = agent_config.get("mlflow_experiment_id")

    if not experiment_id:
        logger.error(f'Agent {agent_config.get("id")} has no mlflow_experiment_id')
        return None

    # Step 1: Find our router trace by client_request_id tag
    logger.info(
        f"Searching for router trace with client_request_id={client_request_id}"
    )
    router_traces = mlflow_client.search_traces(
        experiment_ids=[experiment_id],
        filter_string=f"tags.client_request_id = '{client_request_id}'",
        max_results=1,
    )

    if not router_traces:
        logger.warning(
            f"No router trace found with client_request_id={client_request_id}"
        )
        return None

    router_trace = router_traces[0]
    router_trace_id = router_trace.info.trace_id
    router_timestamp_ms = router_trace.info.timestamp_ms

    logger.info(
        f"Found router trace: {router_trace_id} at timestamp {router_timestamp_ms}"
    )

    # Deployment-specific linking logic
    if deployment_type == "databricks-endpoint":
        # For Databricks endpoints, find the agent's server-side trace by time proximity
        return _find_databricks_agent_trace(
            router_trace_id, router_timestamp_ms, experiment_id, mlflow_client
        )
    else:
        # For future deployment types (local agents, etc.), may use direct trace
        # For now, fallback to router trace
        logger.info(
            f"Deployment type {deployment_type}: using router trace for feedback"
        )
        return router_trace_id


def _find_databricks_agent_trace(
    router_trace_id: str,
    router_timestamp_ms: int,
    experiment_id: str,
    mlflow_client: MlflowClient,
) -> str:
    """Find the Databricks agent's server-side trace using time proximity.

    WORKAROUND: This is not a final solution - see docs/features/feedback.md

    The agent creates its own trace on Databricks servers. We find it by:
    1. Searching for traces created AFTER our router trace (forward-only search)
    2. Filtering out our router trace (has the client_request_id tag)
    3. Picking the closest trace by timestamp

    Why forward-only: Agent traces are always created AT or AFTER the router trace.
    Cold starts can delay agent trace creation by 30+ seconds.

    Args:
      router_trace_id: Our router trace ID (to exclude from search)
      router_timestamp_ms: Timestamp of router trace
      experiment_id: MLflow experiment ID
      mlflow_client: MLflow client instance

    Returns:
      Agent trace ID, or router trace ID as fallback
    """
    # Define time window (forward-only search)
    time_window_ms = TRACE_TIME_WINDOW_SECONDS * 1000
    start_time = router_timestamp_ms  # Start at router trace, not before
    end_time = router_timestamp_ms + time_window_ms

    logger.info(
        f"Searching for agent trace in time window: "
        f"{datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}"
    )

    # Search for all traces in the time window
    candidate_traces = mlflow_client.search_traces(
        experiment_ids=[experiment_id],
        filter_string=f"timestamp_ms >= {start_time} AND timestamp_ms <= {end_time}",
        max_results=20,  # Get multiple to filter
        order_by=["timestamp_ms ASC"],
    )

    logger.info(f"Found {len(candidate_traces)} candidate traces in time window")

    # Filter out our router trace and find agent traces
    agent_traces = []
    for trace in candidate_traces:
        # Skip our router trace
        if trace.info.trace_id == router_trace_id:
            continue

        # Skip traces that have our client_request_id tag (other router traces)
        trace_detail = mlflow_client.get_trace(trace.info.trace_id)
        if hasattr(trace_detail.info, "tags") and trace_detail.info.tags.get(
            "client_request_id"
        ):
            continue

        # Check if trace has content (agent traces have multiple spans with data)
        has_content = False
        if hasattr(trace_detail.data, "spans") and trace_detail.data.spans:
            # Agent traces typically have multiple spans
            if len(trace_detail.data.spans) > 1:
                has_content = True
            # Or check if spans have inputs/outputs
            for span in trace_detail.data.spans:
                if (hasattr(span, "inputs") and span.inputs) or (
                    hasattr(span, "outputs") and span.outputs
                ):
                    has_content = True
                    break

        if has_content:
            time_diff_ms = abs(trace.info.timestamp_ms - router_timestamp_ms)
            agent_traces.append((trace, time_diff_ms))

    if not agent_traces:
        logger.warning(
            f"No agent trace found in time window. Falling back to router trace: {router_trace_id}"
        )
        return router_trace_id

    # Sort by time proximity and pick closest
    agent_traces.sort(key=lambda x: x[1])
    closest_trace, time_diff_ms = agent_traces[0]
    agent_trace_id = closest_trace.info.trace_id

    logger.info(
        f"Found agent trace: {agent_trace_id} "
        f"(time offset: {time_diff_ms}ms from router trace)"
    )

    return agent_trace_id


# Handler registry: maps deployment_type to handler class
DEPLOYMENT_HANDLERS: dict[str, Type[BaseDeploymentHandler]] = {
    "databricks-endpoint": DatabricksEndpointHandler,
    # Future handlers can be added here:
    # 'agent-bricks-mas': AgentBricksMASHandler,
    # 'openai-compatible': OpenAIHandler,
    # 'local-agent': LocalAgentHandler,
    # 'custom-api': CustomAPIHandler,
}


class LogAssessmentRequest(BaseModel):
    """Request to log user feedback for a trace."""

    trace_id: str  # client_request_id (we'll search MLflow with this)
    agent_id: str  # Needed to find MLflow experiment
    assessment_name: str
    assessment_value: Union[str, int, float, bool]
    rationale: Optional[str] = None  # User's optional comment
    source_id: Optional[str] = "anonymous"  # User identifier


class InvokeEndpointRequest(BaseModel):
    """Request to invoke an agent endpoint."""

    agent_id: str
    messages: list[dict[str, str]]
    stream: bool = True  # Default to streaming


@router.post("/log_assessment")
async def log_feedback(options: LogAssessmentRequest):
    """Log user feedback (thumbs up/down) for an agent trace.

    Uses deployment-aware trace linking to find the correct trace:
    - For databricks-endpoint: Uses time-proximity to find agent's server-side trace
    - For other types: May use direct trace lookup

    Stores feedback in MLflow for model evaluation and improvement.
    """
    logger.info(
        f"📝 User feedback - client_request_id: {options.trace_id}, "
        f"Assessment: {options.assessment_name}={options.assessment_value}"
    )

    try:
        # Get agent config
        agent = config_loader.get_agent_by_id(options.agent_id)
        if not agent:
            raise HTTPException(
                status_code=404, detail=f"Agent {options.agent_id} not found"
            )

        experiment_id = agent.get("mlflow_experiment_id")
        if not experiment_id:
            raise HTTPException(
                status_code=400,
                detail=f"Agent {options.agent_id} has no mlflow_experiment_id configured",
            )

        # Use deployment-aware trace linking
        mlflow_client = MlflowClient()
        mlflow_trace_id = find_trace_for_feedback(
            options.trace_id, agent, mlflow_client
        )

        if not mlflow_trace_id:
            logger.error(
                f"Could not find trace for client_request_id={options.trace_id}"
            )
            raise HTTPException(status_code=404, detail="Trace not found for feedback")

        # Log feedback to MLflow
        mlflow.log_feedback(
            trace_id=mlflow_trace_id,
            name=options.assessment_name,
            value=options.assessment_value,
            source=mlflow.entities.AssessmentSource(
                source_type=mlflow.entities.AssessmentSourceType.HUMAN,
                source_id=options.source_id,
            ),
            rationale=options.rationale,
        )

        logger.info(
            f"✅ Feedback logged successfully to trace {mlflow_trace_id} "
            f"(client_request_id: {options.trace_id})"
        )
        return {"status": "success", "mlflow_trace_id": mlflow_trace_id}

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"❌ Failed to log feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to log feedback: {str(e)}")


@router.post("/invoke_endpoint")
async def invoke_endpoint(options: InvokeEndpointRequest, request: Request):
    """Invoke an agent endpoint.

    Supports multiple deployment types via handler pattern.
    Each deployment type has its own handler for request/response formatting.
    Supports both streaming and non-streaming modes.
    Creates MLflow trace with client_request_id for feedback linking.

    Args:
      options: Request payload with agent_id, messages, and stream flag
      request: FastAPI Request object (provides access to auth headers)
    """
    # Generate unique client request ID for trace linking
    client_request_id = f"req-{uuid.uuid4().hex[:16]}"

    logger.info(f"🎯 Invoking agent: {options.agent_id} (stream={options.stream})")
    logger.info(f"📋 client_request_id: {client_request_id}")

    # Look up agent configuration
    agent = config_loader.get_agent_by_id(options.agent_id)

    if not agent:
        logger.error(f"Agent not found: {options.agent_id}")
        return {
            "error": f"Agent not found: {options.agent_id}",
            "message": "Please check your agent configuration",
        }

    # Set experiment for trace
    experiment_id = agent.get("mlflow_experiment_id")
    if experiment_id:
        mlflow.set_experiment(experiment_id=experiment_id)

    # Create trace with mlflow.start_span for synchronous control
    # Note: @mlflow.trace doesn't work well with async streaming responses
    with mlflow.start_span(
        name="[Router] Feedback Linking Trace", span_type="AGENT"
    ) as span:
        trace_id = span.request_id

        # Store in trace.info.client_request_id (not searchable)
        mlflow.update_current_trace(
            client_request_id=client_request_id,
            metadata={
                "mlflow.source.type": "ROUTER",
                "mlflow.source.name": "FastAPI Router",
            },
        )

        # Store in trace.info.tags (searchable via filter_string)
        mlflow_client = MlflowClient()
        mlflow_client.set_trace_tag(trace_id, "client_request_id", client_request_id)

        # Add descriptive metadata to help identify this as a router trace
        mlflow_client.set_trace_tag(trace_id, "trace_type", "router")
        mlflow_client.set_trace_tag(trace_id, "purpose", "feedback_linking")

        logger.info(
            f"✅ Tagged trace {trace_id} with client_request_id: {client_request_id}"
        )

    deployment_type = agent.get("deployment_type", "databricks-endpoint")
    logger.info(f"Agent deployment type: {deployment_type}")

    # Get the appropriate handler for this deployment type
    handler_class = DEPLOYMENT_HANDLERS.get(deployment_type)

    if not handler_class:
        logger.error(f"Unsupported deployment_type: {deployment_type}")
        supported_types = ", ".join(DEPLOYMENT_HANDLERS.keys())
        return {
            "error": "Unsupported deployment type",
            "message": (
                f'Deployment type "{deployment_type}" is not supported. Supported types: {supported_types}'
            ),
        }

    try:
        # Instantiate the handler with agent configuration
        handler = handler_class(agent)

        # Use streaming or non-streaming based on request
        if options.stream:
            return StreamingResponse(
                handler.invoke_stream(
                    messages=options.messages,
                    client_request_id=client_request_id,
                    request=request,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )
        else:
            return handler.invoke(
                messages=options.messages,
                client_request_id=client_request_id,
                request=request,
            )

    except Exception as e:
        logger.error(f"❌ Error invoking agent {options.agent_id}: {str(e)}")
        raise
