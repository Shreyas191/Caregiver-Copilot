'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '@clerk/nextjs';

import { Button } from '@/components/ui/button';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { ThreadSidebar } from '@/components/chat/ThreadSidebar';
import { useChatStream } from '@/hooks/useChatStream';
import { api } from '@/lib/api';

export default function ChatPage() {
  const { careRecipientId } = useParams<{ careRecipientId: string }>();
  const { getToken } = useAuth();
  const [recipientName, setRecipientName] = useState<string>('');

  const { messages, threadId, streaming, send, loadThread, startNewThread } =
    useChatStream(careRecipientId);

  // Load care recipient name for the header
  useEffect(() => {
    async function loadName() {
      try {
        const token = await getToken();
        if (!token) return;
        const cr = await api.careRecipients.get(token, careRecipientId);
        setRecipientName(cr.display_name ?? '');
      } catch {
        // non-critical
      }
    }
    loadName();
  }, [careRecipientId, getToken]);

  const handleSelectThread = useCallback(
    async (tid: string) => {
      await loadThread(tid);
    },
    [loadThread],
  );

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3 shrink-0">
        <Link href={`/care-recipients/${careRecipientId}`}>
          <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
            <ArrowLeft className="h-4 w-4" />
            Profile
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-sm font-semibold text-gray-900">
            {recipientName ? `Chat — ${recipientName}` : 'Chat'}
          </h1>
          {streaming && (
            <p className="text-xs text-blue-600">Assistant is responding…</p>
          )}
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        <ThreadSidebar
          careRecipientId={careRecipientId}
          activeThreadId={threadId}
          onSelectThread={handleSelectThread}
          onNewThread={startNewThread}
        />

        {/* Main chat area */}
        <div className="flex flex-col flex-1 min-w-0">
          <MessageList messages={messages} />
          <MessageInput onSend={send} disabled={streaming} />
        </div>
      </div>
    </div>
  );
}
