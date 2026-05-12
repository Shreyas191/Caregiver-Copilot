'use client';

import { useCallback, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { consumeSSE } from '@/lib/sse';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
};

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') + '/api/v1';

export function useChatStream(careRecipientId: string) {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback(
    async (tid: string) => {
      const token = await getToken();
      if (!token) return;
      const res = await fetch(`${API_BASE}/chat/threads/${tid}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data: Array<{ id: string; role: string; content: string }> = await res.json();
      setMessages(
        data.map((m) => ({ id: m.id, role: m.role as 'user' | 'assistant', content: m.content })),
      );
    },
    [getToken],
  );

  // Load an existing thread: sets both threadId and messages so follow-up messages
  // are sent with the correct thread_id instead of creating a new orphan thread.
  const loadThread = useCallback(
    async (tid: string) => {
      setThreadId(tid);
      setMessages([]);
      const token = await getToken();
      if (!token) return;
      const res = await fetch(`${API_BASE}/chat/threads/${tid}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data: Array<{ id: string; role: string; content: string }> = await res.json();
      setMessages(
        data.map((m) => ({ id: m.id, role: m.role as 'user' | 'assistant', content: m.content })),
      );
    },
    [getToken],
  );

  const send = useCallback(
    async (content: string) => {
      const token = await getToken();
      if (!token || streaming) return;

      // Optimistic user message
      const userMsgId = crypto.randomUUID();
      setMessages((prev) => [...prev, { id: userMsgId, role: 'user', content }]);

      // Placeholder assistant message that will be filled by stream
      const assistantMsgId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        { id: assistantMsgId, role: 'assistant', content: '', streaming: true },
      ]);

      setStreaming(true);
      abortRef.current = new AbortController();

      try {
        await consumeSSE(
          `${API_BASE}/chat/${careRecipientId}/messages`,
          { content, thread_id: threadId },
          token,
          (raw) => {
            try {
              const parsed = JSON.parse(raw);
              if (parsed.thread_id) {
                setThreadId(parsed.thread_id);
                return;
              }
              if (parsed.token !== undefined) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, content: m.content + parsed.token }
                      : m,
                  ),
                );
              }
            } catch {
              // non-JSON lines are ignored
            }
          },
          abortRef.current.signal,
        );
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: 'Sorry, something went wrong. Please try again.', streaming: false }
                : m,
            ),
          );
        }
      } finally {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, streaming: false } : m)),
        );
        setStreaming(false);
      }
    },
    [getToken, careRecipientId, threadId, streaming],
  );

  const startNewThread = useCallback(() => {
    setThreadId(null);
    setMessages([]);
  }, []);

  return { messages, threadId, streaming, send, loadHistory, loadThread, startNewThread };
}
