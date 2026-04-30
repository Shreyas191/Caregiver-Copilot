'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { MessageSquarePlus } from 'lucide-react';
import { Button } from '@/components/ui/button';

type Thread = {
  id: string;
  title: string | null;
  updated_at: string;
};

type ThreadSidebarProps = {
  careRecipientId: string;
  activeThreadId: string | null;
  onSelectThread: (id: string) => void;
  onNewThread: () => void;
};

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') + '/api/v1';

export function ThreadSidebar({
  careRecipientId,
  activeThreadId,
  onSelectThread,
  onNewThread,
}: ThreadSidebarProps) {
  const { getToken } = useAuth();
  const [threads, setThreads] = useState<Thread[]>([]);

  useEffect(() => {
    async function load() {
      const token = await getToken();
      if (!token) return;
      const res = await fetch(`${API_BASE}/chat/${careRecipientId}/threads`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      setThreads(data);
    }
    load();
  }, [careRecipientId, getToken, activeThreadId]);

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  return (
    <aside className="w-60 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
      <div className="px-3 py-3 border-b border-gray-200">
        <Button variant="outline" size="sm" onClick={onNewThread} className="w-full gap-1.5 text-xs">
          <MessageSquarePlus className="h-3.5 w-3.5" />
          New chat
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {threads.length === 0 ? (
          <p className="px-3 py-4 text-xs text-muted-foreground text-center">No conversations yet</p>
        ) : (
          threads.map((t) => (
            <button
              key={t.id}
              onClick={() => onSelectThread(t.id)}
              className={`w-full text-left px-3 py-2.5 text-sm rounded-lg mx-1 transition-colors ${
                activeThreadId === t.id
                  ? 'bg-white shadow-sm text-gray-900 font-medium'
                  : 'text-gray-600 hover:bg-white hover:text-gray-900'
              }`}
            >
              <p className="truncate">{t.title ?? 'Untitled chat'}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{formatDate(t.updated_at)}</p>
            </button>
          ))
        )}
      </nav>
    </aside>
  );
}
