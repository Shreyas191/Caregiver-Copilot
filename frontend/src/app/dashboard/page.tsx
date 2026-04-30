'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { UserButton } from '@clerk/nextjs';
import Link from 'next/link';
import { MessageSquare, Plus, User } from 'lucide-react';

import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type CareRecipient = {
  id: string;
  display_name: string;
  date_of_birth: string;
  sex_at_birth: string;
  conditions: Array<{ name: string }>;
  consent_revoked_at?: string | null;
};

function calcAge(dob: string): number {
  const birth = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
  return age;
}

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [recipients, setRecipients] = useState<CareRecipient[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const token = await getToken();
        if (!token) return;
        const data = await api.careRecipients.list(token);
        setRecipients(data ?? []);
      } catch (err) {
        console.error('Failed to load care recipients', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [getToken]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Caregiver Co-Pilot</h1>
        <div className="flex items-center gap-3">
          <Link href="/care-recipients/new">
            <Button size="sm" className="gap-1.5">
              <Plus className="h-3.5 w-3.5" />
              Add Care Recipient
            </Button>
          </Link>
          <UserButton />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Your Care Recipients</h2>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            <div className="h-6 w-6 rounded-full border-2 border-t-transparent border-blue-600 animate-spin mr-3" />
            Loading…
          </div>
        ) : recipients.length === 0 ? (
          <div className="text-center py-16 border border-dashed rounded-xl bg-white">
            <User className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-lg font-medium text-gray-800 mb-1">No care recipients yet</p>
            <p className="text-sm text-muted-foreground mb-6">
              Add the person you're caring for to get started.
            </p>
            <Link href="/care-recipients/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Care Recipient
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {recipients.map((cr) => (
              <Card key={cr.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-start justify-between gap-2">
                    <Link href={`/care-recipients/${cr.id}`} className="hover:underline">
                      {cr.display_name}
                    </Link>
                    <span className="text-sm font-normal text-muted-foreground shrink-0">
                      {calcAge(cr.date_of_birth)} yrs
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {cr.conditions.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {cr.conditions.slice(0, 3).map((c, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">{c.name}</Badge>
                      ))}
                      {cr.conditions.length > 3 && (
                        <Badge variant="outline" className="text-xs">+{cr.conditions.length - 3} more</Badge>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">No conditions recorded</p>
                  )}
                  <div className="flex gap-2">
                    <Link href={`/chat/${cr.id}`} className="flex-1">
                      <Button size="sm" className="w-full gap-1.5">
                        <MessageSquare className="h-3.5 w-3.5" />
                        Open Chat
                      </Button>
                    </Link>
                    <Link href={`/care-recipients/${cr.id}`}>
                      <Button size="sm" variant="outline">View Profile</Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
