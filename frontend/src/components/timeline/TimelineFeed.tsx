"use client";

interface TimelineEvent {
  id: string;
  type: "episode" | "vital" | "medication" | "document";
  occurred_at: string;
  title: string;
  detail: Record<string, unknown>;
}

const TYPE_ICONS: Record<string, string> = {
  episode: "🩺",
  vital: "📊",
  medication: "💊",
  document: "📄",
};

const TYPE_COLORS: Record<string, string> = {
  episode: "border-l-orange-400",
  vital: "border-l-blue-400",
  medication: "border-l-green-400",
  document: "border-l-purple-400",
};

interface TimelineFeedProps {
  events: TimelineEvent[];
  onEpisodeClick?: (event: TimelineEvent) => void;
}

export function TimelineFeed({ events, onEpisodeClick }: TimelineFeedProps) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No timeline events yet.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div
          key={event.id}
          className={`border-l-4 pl-4 py-2 ${TYPE_COLORS[event.type]} ${
            event.type === "episode" ? "cursor-pointer hover:bg-accent/50 rounded-r" : ""
          }`}
          onClick={() => event.type === "episode" && onEpisodeClick?.(event)}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span>{TYPE_ICONS[event.type]}</span>
              <span className="text-sm font-medium">{event.title}</span>
            </div>
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {new Date(event.occurred_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
