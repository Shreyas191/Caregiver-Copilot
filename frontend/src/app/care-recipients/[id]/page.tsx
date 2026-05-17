'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, MessageSquare } from 'lucide-react';

import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ProfileSummary } from '@/components/care-recipient/ProfileSummary';
import { MedicationsList } from '@/components/care-recipient/MedicationsList';
import { VitalsList } from '@/components/care-recipient/VitalsList';
import { EpisodesList } from '@/components/care-recipient/EpisodesList';
import { MedicationForm } from '@/components/medications/MedicationForm';
import { UploadButton } from '@/components/documents/UploadButton';

export default function CareRecipientProfilePage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [profile, setProfile] = useState<any>(null);
  const [medications, setMedications] = useState<any[]>([]);
  const [vitals, setVitals] = useState<any[]>([]);
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [medDialogOpen, setMedDialogOpen] = useState(false);

  const fetchDocuments = useCallback(async () => {
    const token = await getToken();
    if (!token || !id) return;
    const base = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') + '/api/v1';
    try {
      const res = await fetch(`${base}/care-recipients/${id}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setDocuments(await res.json());
    } catch { /* non-critical */ }
  }, [getToken, id]);

  const fetchAll = useCallback(async () => {
    const token = await getToken();
    if (!token || !id) return;
    const [profileData, medsData, vitalsData, episodesData] = await Promise.all([
      api.careRecipients.get(token, id),
      api.careRecipients.medications(token, id),
      api.careRecipients.vitals(token, id, 10),
      api.careRecipients.episodes(token, id, 5),
    ]);
    setProfile(profileData);
    setMedications(medsData ?? []);
    setVitals(vitalsData ?? []);
    setEpisodes(episodesData ?? []);
  }, [getToken, id]);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchAll(), fetchDocuments()]).finally(() => setLoading(false));
  }, [fetchAll, fetchDocuments]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center text-muted-foreground">
        <div className="h-8 w-8 rounded-full border-2 border-t-transparent border-blue-600 animate-spin mr-3" />
        Loading profile…
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-muted-foreground">Care recipient not found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
                <ArrowLeft className="h-4 w-4" />
                Dashboard
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">{profile.display_name}</h1>
              <p className="text-sm text-muted-foreground capitalize">
                {profile.sex_at_birth} · DOB {profile.date_of_birth}
              </p>
            </div>
          </div>
          <Link href={`/chat/${id}`}>
            <Button className="gap-1.5">
              <MessageSquare className="h-4 w-4" />
              Open Chat
            </Button>
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-6">
        <Tabs defaultValue="profile">
          <TabsList className="mb-6">
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="medications">
              Medications {medications.filter((m) => !m.stopped_at).length > 0 && `(${medications.filter((m) => !m.stopped_at).length})`}
            </TabsTrigger>
            <TabsTrigger value="vitals">Recent Vitals</TabsTrigger>
            <TabsTrigger value="episodes">Episodes</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
          </TabsList>

          <TabsContent value="profile">
            <ProfileSummary
              displayName={profile.display_name}
              dateOfBirth={profile.date_of_birth}
              sexAtBirth={profile.sex_at_birth}
              conditions={profile.conditions ?? []}
              allergies={profile.allergies ?? []}
              baselineNotes={profile.baseline_notes}
              primaryProviderName={profile.primary_provider_name}
              primaryProviderPhone={profile.primary_provider_phone}
              primaryProviderEmail={profile.primary_provider_email}
              emergencyContactName={profile.emergency_contact_name}
              emergencyContactPhone={profile.emergency_contact_phone}
              consentBasis={profile.consent_basis}
            />
          </TabsContent>

          <TabsContent value="medications">
            <MedicationsList
              medications={medications}
              onAddClick={() => setMedDialogOpen(true)}
            />
          </TabsContent>

          <TabsContent value="vitals">
            <VitalsList vitals={vitals} />
          </TabsContent>

          <TabsContent value="episodes">
            <EpisodesList episodes={episodes} />
          </TabsContent>

          <TabsContent value="documents">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-base font-semibold text-gray-900">Clinical Documents</h2>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    Upload lab reports, discharge summaries, or after-visit notes (PDF or image).
                    The assistant can answer questions about uploaded documents.
                  </p>
                </div>
                <UploadButton careRecipientId={id} onUploadComplete={fetchDocuments} />
              </div>

              {documents.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No documents uploaded yet.
                </p>
              ) : (
                <ul className="divide-y divide-gray-100">
                  {documents.map((doc) => (
                    <li key={doc.id} className="flex items-center justify-between py-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {doc.original_filename}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {doc.document_type} · {(doc.file_size_bytes / 1024).toFixed(0)} KB ·{' '}
                          <span className={`capitalize ${doc.status === 'indexed' ? 'text-green-600' : doc.status === 'failed' ? 'text-red-500' : 'text-yellow-600'}`}>
                            {doc.status}
                          </span>
                          {' · '}{new Date(doc.uploaded_at).toLocaleDateString()}
                        </p>
                      </div>
                      <button
                        onClick={async () => {
                          const token = await getToken();
                          const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
                          const res = await fetch(
                            `${base}/api/v1/care-recipients/${id}/documents/${doc.id}/download`,
                            { headers: { Authorization: `Bearer ${token}` } },
                          );
                          if (res.ok) {
                            const { url } = await res.json();
                            window.open(url, '_blank');
                          }
                        }}
                        className="ml-4 text-xs text-blue-600 hover:underline shrink-0"
                      >
                        View
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </main>

      <Dialog open={medDialogOpen} onOpenChange={setMedDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Add Medication</DialogTitle>
            <DialogDescription>
              Search for a medication and fill in the prescription details.
            </DialogDescription>
          </DialogHeader>
          <MedicationForm
            careRecipientId={id}
            onSuccess={() => {
              setMedDialogOpen(false);
              fetchAll();
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
