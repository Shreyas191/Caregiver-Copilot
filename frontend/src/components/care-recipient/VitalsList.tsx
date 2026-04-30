import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

type Vital = {
  id: string;
  type: string;
  value_numeric?: number | null;
  value_systolic?: number | null;
  value_diastolic?: number | null;
  value_text?: string | null;
  unit: string;
  recorded_at: string;
  notes?: string | null;
};

type VitalsListProps = {
  vitals: Vital[];
};

const typeLabels: Record<string, string> = {
  blood_pressure: 'Blood Pressure',
  heart_rate: 'Heart Rate',
  glucose: 'Glucose',
  weight: 'Weight',
  temperature: 'Temperature',
  oxygen_saturation: 'O₂ Saturation',
  respiratory_rate: 'Respiratory Rate',
  pain_score: 'Pain Score',
};

function formatValue(v: Vital): string {
  if (v.type === 'blood_pressure' && v.value_systolic != null && v.value_diastolic != null) {
    return `${v.value_systolic}/${v.value_diastolic} ${v.unit}`;
  }
  if (v.value_numeric != null) return `${v.value_numeric} ${v.unit}`;
  if (v.value_text) return v.value_text;
  return '—';
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function VitalsList({ vitals }: VitalsListProps) {
  if (vitals.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg text-sm">
        No vitals recorded
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {vitals.map((v) => (
        <Card key={v.id} className="shadow-none">
          <CardContent className="p-4 flex justify-between items-center">
            <div className="space-y-0.5">
              <Badge variant="secondary" className="text-xs mb-1">
                {typeLabels[v.type] ?? v.type.replace(/_/g, ' ')}
              </Badge>
              <p className="font-semibold text-sm">{formatValue(v)}</p>
              {v.notes && <p className="text-xs text-muted-foreground">{v.notes}</p>}
            </div>
            <p className="text-xs text-muted-foreground shrink-0 ml-4">{formatDate(v.recorded_at)}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
