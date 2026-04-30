/**
 * Consume a Server-Sent Events stream returned by a POST request.
 * EventSource only supports GET and no custom headers, so we use fetch + ReadableStream.
 *
 * Calls `onToken` for each parsed `data:` line.
 * Stops when it sees the sentinel `data: [DONE]`.
 */
export async function consumeSSE(
  url: string,
  body: unknown,
  token: string,
  onToken: (raw: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    let detail = 'Stream request failed';
    try {
      const err = await response.json();
      detail = err.detail ?? detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }

  if (!response.body) throw new Error('No response body');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    // Keep the last (possibly incomplete) line in the buffer
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const data = line.slice('data:'.length).trim();
      if (data === '[DONE]') return;
      onToken(data);
    }
  }
}
