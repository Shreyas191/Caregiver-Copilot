import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

type Episode = {
  id: string;
  started_at: string;
  caregiver_description: string;
  agent_assessment?: string | null;
  urgency_level: string;
  status: string;
  symptoms: Array<{ name?: string; [key: string]: unknown }>;
};

type EpisodesListProps = {
  episodes: Episode[];
};

const urgencyBadge: Record<string, string> = {
  routine: 'bg-green-100 text-green-800',
  same_day: 'bg-yellow-100 text-yellow-800',
  urgent: 'bg-orange-100 text-orange-800',
  emergency: 'bg-red-100 text-red-800',
};

const statusBadge: Record<string, string> = {
  open: 'bg-blue-100 text-blue-800',
  monitoring: 'bg-purple-100 text-purple-800',
  resolved: 'bg-gray-100 text-gray-600',
  escalated: 'bg-red-100 text-red-800',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function EpisodesList({ episodes }: EpisodesListProps) {
  if (episodes.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg text-sm">
        No episodes recorded
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {episodes.map((ep) => (
        <Card key={ep.id} className="shadow-none">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium line-clamp-2">{ep.caregiver_description}</p>
              <p className="text-xs text-muted-foreground shrink-0">{formatDate(ep.started_at)}</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span
                className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${urgencyBadge[ep.urgency_level] ?? 'bg-gray-100 text-gray-700'}`}
              >
                {ep.urgency_level.replace(/_/g, ' ')}
              </span>
              <span
                className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${statusBadge[ep.status] ?? 'bg-gray-100 text-gray-700'}`}
              >
                {ep.status}
              </span>
            </div>
            {ep.agent_assessment && (
              <p className="text-xs text-muted-foreground line-clamp-2">{ep.agent_assessment}</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
