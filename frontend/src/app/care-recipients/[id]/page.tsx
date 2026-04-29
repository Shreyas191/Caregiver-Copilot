'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function CareRecipientProfilePage() {
  const { id } = useParams();
  const { getToken } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const token = await getToken();
        const recipient = await api.careRecipients.get(token!, id as string);
        setData(recipient);
      } catch (err) {
        console.error(err);
        router.push('/dashboard');
      } finally {
        setLoading(false);
      }
    }
    if (id) {
      loadData();
    }
  }, [id, getToken, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-400">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-12 w-12 rounded-full border-t-2 border-b-2 border-blue-500 animate-spin mb-4"></div>
          <p>Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="flex items-center justify-between border-b border-gray-800 pb-6 mt-12">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              {data?.display_name}
            </h1>
            <p className="text-gray-400 mt-2">
              DOB: {data?.date_of_birth} • Sex: {data?.sex_at_birth}
            </p>
          </div>
          <div className="bg-gray-900/50 border border-gray-800 px-4 py-2 rounded-lg text-sm text-gray-300 shadow-sm capitalize">
            Consent: {data?.consent_basis.replace(/_/g, ' ')}
          </div>
        </div>
        
        <div className="p-8 bg-gray-900/30 border border-gray-800 rounded-xl">
          <p className="text-gray-400 text-center font-medium">
            Detailed profile dashboard coming soon in CC-013.
          </p>
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="p-4 border border-gray-800 rounded-lg">
                <h3 className="font-semibold text-gray-300 mb-2">Conditions</h3>
                {data?.conditions?.length > 0 ? (
                  <ul className="list-disc pl-5 text-sm text-gray-400">
                    {data.conditions.map((c: any, i: number) => <li key={i}>{c.name}</li>)}
                  </ul>
                ) : <span className="text-sm text-gray-500">None reported</span>}
             </div>
             <div className="p-4 border border-gray-800 rounded-lg">
                <h3 className="font-semibold text-gray-300 mb-2">Allergies</h3>
                {data?.allergies?.length > 0 ? (
                  <ul className="list-disc pl-5 text-sm text-gray-400">
                    {data.allergies.map((a: any, i: number) => <li key={i}>{a.substance}</li>)}
                  </ul>
                ) : <span className="text-sm text-gray-500">None reported</span>}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
