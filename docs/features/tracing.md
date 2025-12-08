# Tracing Display

## Overview

The application displays execution traces for agent responses, showing function calls and outputs in a visual interface. For the current **databricks-endpoint** handler, traces are built **client-side from streaming data** - no MLflow API calls are made from the frontend.

## How It Works (Databricks Endpoint Handler)

### Data Collection During Streaming

As the agent streams its response (in `client/components/chat/ChatView.tsx`):

1. **Client Request ID** received first:
   - Backend emits `trace.client_request_id` event (line 437-443)
   - Used for feedback linking to MLflow traces

2. **Function Call Events** captured from stream:
   - `response.output_item.done` with `type: "function_call"` → Adds function call to collected list (lines 451-481)
   - `response.output_item.done` with `type: "function_call_output"` → Adds output to matching function call (lines 507-541)

3. **Function calls stored locally** in `collectedFunctionCalls` array during streaming (lines 220-225, 465-469, 517-522)

4. **Trace Summary Event** (optional from Databricks):
   - If Databricks sends `trace.summary` event, it contains trace metadata (lines 606-677)
   - Frontend **merges** collected function calls into trace summary (lines 623-640)
   - If no trace.summary received, frontend creates minimal summary with function calls only (lines 706-725)

5. **Data attached to message** for later display (lines 656-676, 736-760)

### What Gets Captured

**From streaming events:**
- Function call names and arguments
- Function call outputs
- Call IDs for linking calls to outputs
- Client request ID (for feedback)

**NOT captured (not in streaming events):**
- Duration/timing data
- LLM call details (prompts, tokens, model)
- Full span hierarchy
- Nested execution details

### Display in Trace Modal

When user clicks "View Trace" on a message (in `client/components/modals/TraceModal.tsx`):

1. **Opens modal with cached data** - no network calls
   - `functionCalls` from message's `traceSummary.function_calls`
   - `userMessage` and `assistantResponse` from message content

2. **Builds simple trace structure**:
   - Root: "Agent Execution" with user message input and assistant response output
   - Children: One entry per function call with arguments and output

3. **Renders list**:
   - Shows function call names
   - Displays arguments and outputs as formatted JSON
   - No timing information (always 0ms)
   - No nested spans or hierarchy

## Current Limitations (Databricks Endpoint)

### 1. No MLflow Backend Integration

**What's Missing:**
- Cannot fetch full MLflow trace from backend
- No access to complete span hierarchy
- No LLM call details (prompts, token counts per call)
- No timing/duration information

**Why:**
- Handler simply forwards Databricks streaming events (see `server/agents/handlers/databricks_endpoint.py:108`)
- No backend processing of traces
- No MLflow API integration

**Impact:**
- Trace shows function calls only, not full execution graph
- No nested span details
- Users must visit MLflow UI for complete traces

### 2. No Duration/Timing Data

**What's Missing:**
- Span durations always show as 0ms
- No execution timeline
- No performance metrics

**Why:**
- Databricks SSE stream doesn't include timing metadata in the events we capture

**Impact:** Cannot identify performance bottlenecks from UI

### 3. Limited to Streaming Responses

**What's Missing:**
- Non-streaming responses don't collect function call data
- No trace display for non-streaming mode

**Why:**
- Data collection happens during stream event processing (lines 334-706 in ChatView.tsx)
- Non-streaming mode uses different response format

**Impact:** Trace modal shows "No trace data available" for non-streaming responses

### 4. Stream-Based Only (No Historical Fetch)

**What's Missing:**
- Cannot fetch trace for old messages from MLflow
- Cannot refresh trace data
- Relies entirely on what was captured during streaming

**Why:**
- No backend endpoint to fetch traces from MLflow
- No integration with MLflow Tracking API

**Impact:**
- Trace data only available if message was streamed
- Cannot see traces for messages loaded from chat history (unless trace_summary was saved)

## Implementation Details

### Backend: Databricks Endpoint Handler

File: `server/agents/handlers/databricks_endpoint.py`

The handler performs **passthrough forwarding** of Databricks streaming events:

```python
# Line 76-112
async for line in response.aiter_lines():
    # ... parse SSE format ...

    try:
        event = json.loads(json_str)
        # Simply forward the event to frontend
        yield f'data: {json_str}\n\n'
    except json.JSONDecodeError as e:
        logger.warning(f'Failed to parse JSON from stream: {e}')
        continue
```

**What it does:**
1. Emits `trace.client_request_id` first (line 55-56)
2. Forwards all Databricks events as-is (line 108)
3. No trace processing or MLflow integration

### Frontend: Data Collection

File: `client/components/chat/ChatView.tsx`

**Function call collection** (lines 451-541):

```typescript
// Handle function call start
if (item?.type === "function_call") {
  collectedFunctionCalls.push({
    call_id: item.call_id,
    name: item.name,
    arguments: parseArguments(item.arguments),
  });
}

// Handle function call output
if (item?.type === "function_call_output") {
  const fcIndex = collectedFunctionCalls.findIndex(
    (fc) => fc.call_id === item.call_id
  );
  if (fcIndex !== -1) {
    collectedFunctionCalls[fcIndex].output = parseOutput(item.output);
  }
}
```

**Trace summary handling** (lines 606-677):

```typescript
if (event.type === "trace.summary") {
  traceSummary = event.traceSummary;

  // IMPORTANT: Merge our collected function calls
  // Databricks may not send detailed function_calls in trace.summary
  if (traceSummary && collectedFunctionCalls.length > 0) {
    traceSummary.function_calls = collectedFunctionCalls.map(fc => ({
      call_id: fc.call_id,
      name: fc.name,
      arguments: fc.arguments || {},
      output: fc.output || {},
    }));
  }
}
```

**Fallback if no trace.summary** (lines 706-725):

```typescript
// If we have function calls but no trace summary, create a minimal one
if (!traceSummary && collectedFunctionCalls.length > 0) {
  traceSummary = {
    trace_id: traceId || "",
    duration_ms: 0,
    status: "completed",
    function_calls: collectedFunctionCalls.map(fc => ({
      call_id: fc.call_id,
      name: fc.name,
      arguments: fc.arguments || {},
      output: fc.output || {},
    })),
    // ... other empty fields ...
  };
}
```

### Display: Trace Modal

File: `client/components/modals/TraceModal.tsx`

Displays a simple list of function calls with:
- Function name
- Arguments (formatted JSON)
- Output (formatted JSON)
- No duration data

## Possible Improvements

### Short-Term (Frontend Only)

1. **Show In-Progress Function Calls**
   - Display function calls as they execute (already tracked in `activeFunctionCalls` state)
   - Add "partial trace" view while streaming
   - Implementation: ~50 LOC in TraceModal.tsx

2. **Enhanced Empty State**
   - Distinguish between "no tools used" vs "non-streaming response" vs "no trace data"
   - Show helpful message directing to MLflow UI

### Medium-Term (Backend Integration)

3. **Fetch Full MLflow Trace**
   - Add backend endpoint: `GET /api/traces/{trace_id}`
   - Fetch complete span hierarchy with timing data from MLflow API
   - Fallback to cached data if backend unavailable
   - Implementation: ~200 LOC (backend + frontend)

4. **Show LLM Call Details**
   - Display prompts sent to LLM
   - Token counts per call
   - Model parameters used
   - Requires MLflow trace parsing on backend

5. **Duration and Performance Metrics**
   - Calculate span durations from MLflow data
   - Show execution timeline
   - Highlight slow operations

### Long-Term (Enhanced Features)

6. **Trace Comparison**
   - Compare traces across multiple responses
   - Identify patterns in function call usage

7. **Export Trace Data**
   - Download trace as JSON
   - Share with team for debugging

8. **Real-Time Trace Updates**
   - Stream trace data as function calls execute
   - Show progress indicator for each call

## Handler-Specific Behavior

The trace implementation described here applies to **databricks-endpoint** handler only.

**Other deployment types may differ:**
- **Local agents** (future): Could create traces directly with full control, including timing
- **Agent Bricks** (future): May have different streaming format or trace events
- **OpenAI-compatible** (future): Different event format, may not include function call details

When implementing new handlers, consider:
1. What trace data is available in that deployment type?
2. Does it include timing/duration information?
3. Can we fetch full traces from a backend API?
4. What events are emitted during streaming?

## Code References

**Backend:**
- `server/agents/handlers/databricks_endpoint.py:40-112` - Stream forwarding
- `server/routers/agent.py:306-326` - MLflow trace creation for feedback

**Frontend:**
- `client/components/chat/ChatView.tsx:216-225` - Function call array initialization
- `client/components/chat/ChatView.tsx:451-541` - Function call collection
- `client/components/chat/ChatView.tsx:606-677` - Trace summary handling
- `client/components/chat/ChatView.tsx:706-725` - Fallback trace creation
- `client/components/modals/TraceModal.tsx` - Trace display

**Types:**
- `client/lib/types.ts:39-71` - TraceSummary interface
- `server/chat_storage.py:24` - trace_summary field
