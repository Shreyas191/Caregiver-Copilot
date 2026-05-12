import { auth } from "@clerk/nextjs/server";
import { TimelineFeed } from "@/components/timeline/TimelineFeed";

interface Props {
  params: { id: string };
  searchParams: { types?: string; start?: string; end?: string };
}

async function getTimeline(careRecipientId: string, token: string, searchParams: Props["searchParams"]) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const qs = new URLSearchParams();
  if (searchParams.types) qs.set("types", searchParams.types);
  if (searchParams.start) qs.set("start", searchParams.start);
  if (searchParams.end) qs.set("end", searchParams.end);

  const res = await fetch(
    `${apiUrl}/api/v1/care-recipients/${careRecipientId}/timeline?${qs.toString()}`,
    { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }
  );
  if (!res.ok) return [];
  return res.json();
}

export default async function TimelinePage({ params, searchParams }: Props) {
  const { getToken } = auth();
  const token = await getToken();
  const events = token ? await getTimeline(params.id, token, searchParams) : [];

  return (
    <div className="container mx-auto max-w-3xl py-6 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">Timeline</h1>
        <a
          href={`/care-recipients/${params.id}`}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Back to profile
        </a>
      </div>

      <TimelineFeed events={events} />
    </div>
  );
}
