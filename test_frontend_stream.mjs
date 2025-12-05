// Test streaming through Next.js proxy
async function testStream() {
  console.log('🧪 Testing streaming through Next.js proxy (http://localhost:3000)...\n');

  try {
    const response = await fetch('http://localhost:3000/api/invoke_endpoint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: 'databricks-agent-01',
        messages: [{ role: 'user', content: 'Say hello briefly' }],
        stream: true
      })
    });

    console.log('📡 Response status:', response.status);
    console.log('📡 Content-Type:', response.headers.get('content-type'));

    if (!response.ok) {
      const text = await response.text();
      console.error('❌ Error response:', text);
      return;
    }

    if (!response.body) {
      console.error('❌ No response body!');
      return;
    }

    console.log('🌊 Starting to read stream...\n');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let eventCount = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        console.log('\n✅ Stream done');
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        if (!line.startsWith('data: ')) continue;

        const data = line.slice(6).trim();
        if (!data || data === '[DONE]') continue;

        try {
          const event = JSON.parse(data);
          eventCount++;

          if (event.type === 'response.output_text.delta') {
            console.log(`📝 Delta #${eventCount}:`, event.delta);
          } else {
            console.log(`📨 Event #${eventCount}:`, event.type);
          }
        } catch (e) {
          console.error('❌ JSON parse error:', e.message, 'Data:', data.substring(0, 100));
        }
      }
    }

    console.log(`\n✅ Test complete! Received ${eventCount} events`);
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

testStream();
