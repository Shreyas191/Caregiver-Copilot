"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const { getToken } = useAuth();
  const [calendarConnected, setCalendarConnected] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    async function checkStatus() {
      const token = await getToken();
      const res = await fetch(`${apiUrl}/auth/google/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCalendarConnected(data.connected);
      }
    }
    checkStatus();
  }, [getToken]);

  async function handleDisconnect() {
    setLoading(true);
    const token = await getToken();
    await fetch(`${apiUrl}/auth/google/disconnect`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    setCalendarConnected(false);
    setLoading(false);
  }

  async function handleConnect() {
    const token = await getToken();
    const res = await fetch(`${apiUrl}/auth/google/connect`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const data = await res.json();
      window.location.href = data.authorization_url;
    }
  }

  return (
    <div className="container mx-auto max-w-2xl py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Google Calendar</CardTitle>
          <CardDescription>
            Connect Google Calendar to allow the assistant to set reminders and follow-up appointments.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {calendarConnected === null ? (
            <p className="text-sm text-muted-foreground">Checking status…</p>
          ) : calendarConnected ? (
            <div className="flex items-center gap-4">
              <span className="text-sm text-green-600 font-medium">✓ Connected</span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDisconnect}
                disabled={loading}
              >
                Disconnect
              </Button>
            </div>
          ) : (
            <Button onClick={handleConnect} disabled={loading}>
              Connect Google Calendar
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
