"""Test script to analyze MAS endpoint streaming response structure."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env.local'
load_dotenv(env_path)

DATABRICKS_HOST = os.getenv('DATABRICKS_HOST')
DATABRICKS_TOKEN = os.getenv('DATABRICKS_TOKEN')
MAS_ENDPOINT_NAME = 'mas-c58a2ef5-endpoint'


async def test_mas_streaming():
  """Test MAS endpoint and capture raw SSE events."""
  print('=' * 80)
  print('Testing MAS Endpoint Streaming Response')
  print('=' * 80)
  print(f'\nEndpoint: {MAS_ENDPOINT_NAME}')
  print(f'Host: {DATABRICKS_HOST}')
  print('Question: "total repairs by month for emirates"\n')
  print('=' * 80)

  # Build request
  url = f'{DATABRICKS_HOST}/serving-endpoints/{MAS_ENDPOINT_NAME}/invocations'
  headers = {
    'Authorization': f'Bearer {DATABRICKS_TOKEN}',
    'Content-Type': 'application/json',
  }
  payload = {
    'input': [
      {
        'role': 'user',
        'content': 'total repairs by month for emirates',
      }
    ],
    'stream': True,
  }

  event_count = 0
  function_call_events = []
  trace_events = []

  print('\n📡 Starting stream...\n')

  async with httpx.AsyncClient(timeout=300.0) as client:
    async with client.stream('POST', url, json=payload, headers=headers) as response:
      print(f'✅ Response status: {response.status_code}\n')
      response.raise_for_status()

      async for line in response.aiter_lines():
        if not line or not line.strip():
          continue

        # Handle [DONE] marker
        if line.strip() in ['data: [DONE]', '[DONE]']:
          print('\n🏁 Stream ended: [DONE]\n')
          continue

        # Extract JSON from SSE format
        json_str = line.strip()
        if json_str.startswith('data: '):
          json_str = json_str[6:].strip()
        elif json_str.startswith('data:'):
          json_str = json_str[5:].strip()

        if not json_str:
          continue

        try:
          event = json.loads(json_str)
          event_count += 1

          # Print event header
          event_type = event.get('type', 'unknown')
          print(f'\n{"─" * 80}')
          print(f'Event #{event_count}: {event_type}')
          print(f'{"─" * 80}')

          # Print full event structure
          print(json.dumps(event, indent=2))

          # Categorize events
          if 'function_call' in event_type.lower() or (
            'output_item' in event_type.lower()
            and event.get('item', {}).get('type') == 'function_call'
          ):
            function_call_events.append(event)
            print('🔧 [FUNCTION CALL EVENT]')

          if 'trace' in event_type.lower():
            trace_events.append(event)
            print('🔍 [TRACE EVENT]')

        except json.JSONDecodeError as e:
          print('\n⚠️  JSON Parse Error:')
          print(f'   Error: {e}')
          print(f'   Raw line: {json_str[:200]}...')

  # Summary
  print('\n' + '=' * 80)
  print('SUMMARY')
  print('=' * 80)
  print(f'Total events: {event_count}')
  print(f'Function call events: {len(function_call_events)}')
  print(f'Trace events: {len(trace_events)}')

  # Detailed analysis of function calls
  if function_call_events:
    print('\n' + '=' * 80)
    print('FUNCTION CALL ANALYSIS')
    print('=' * 80)
    for i, fc_event in enumerate(function_call_events, 1):
      print(f'\n--- Function Call #{i} ---')
      item = fc_event.get('item', {})
      print(f'Type: {item.get("type")}')
      print(f'Name: {item.get("name")}')
      print(f'Call ID: {item.get("call_id")}')

      # Check arguments format
      arguments = item.get('arguments')
      if arguments:
        print(f'\nArguments (raw type: {type(arguments).__name__}):')
        print(f'  {repr(arguments)[:200]}...')

        # Try to parse as JSON
        if isinstance(arguments, str):
          try:
            parsed_args = json.loads(arguments)
            print('  ✅ Valid JSON')
            print(f'  Parsed: {json.dumps(parsed_args, indent=4)}')
          except json.JSONDecodeError as e:
            print('  ❌ NOT valid JSON')
            print(f'  Error: {e}')
            print('  This is the issue! Plain string, not JSON.')

      # Check output format
      output = item.get('output')
      if output:
        print(f'\nOutput (raw type: {type(output).__name__}):')
        print(f'  {repr(output)[:200]}...')

        if isinstance(output, str):
          try:
            _ = json.loads(output)
            print('  ✅ Valid JSON')
          except json.JSONDecodeError as e:
            print('  ❌ NOT valid JSON')
            print(f'  Error: {e}')

  # Trace analysis
  if trace_events:
    print('\n' + '=' * 80)
    print('TRACE ANALYSIS')
    print('=' * 80)
    for i, trace_event in enumerate(trace_events, 1):
      print(f'\n--- Trace Event #{i} ---')
      print(f'Type: {trace_event.get("type")}')
      if 'trace_id' in trace_event:
        print(f'Trace ID: {trace_event["trace_id"]}')
      if 'client_request_id' in trace_event:
        print(f'Client Request ID: {trace_event["client_request_id"]}')
      if 'traceSummary' in trace_event:
        print('Has traceSummary: YES')
        print(f'Summary keys: {list(trace_event["traceSummary"].keys())}')

  print('\n' + '=' * 80)
  print('TEST COMPLETE')
  print('=' * 80)


if __name__ == '__main__':
  asyncio.run(test_mas_streaming())
