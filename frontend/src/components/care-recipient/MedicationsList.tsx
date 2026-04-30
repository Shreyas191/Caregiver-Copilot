import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

type Medication = {
  id: string;
  display_name: string;
  rxnorm_code?: string | null;
  dose?: string | null;
  frequency?: string | null;
  route?: string | null;
  started_at: string;
  stopped_at?: string | null;
  prescribed_for?: string | null;
  prescriber?: string | null;
};

type MedicationsListProps = {
  medications: Medication[];
  onAddClick: () => void;
};

export function MedicationsList({ medications, onAddClick }: MedicationsListProps) {
  const active = medications.filter((m) => !m.stopped_at);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{active.length} active medication{active.length !== 1 ? 's' : ''}</p>
        <Button size="sm" variant="outline" onClick={onAddClick} className="gap-1">
          <Plus className="h-3.5 w-3.5" />
          Add
        </Button>
      </div>

      {active.length > 0 ? (
        <div className="space-y-2">
          {active.map((med) => (
            <Card key={med.id} className="shadow-none">
              <CardContent className="p-4 flex justify-between items-start">
                <div className="space-y-1">
                  <p className="font-medium text-sm">{med.display_name}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {med.dose && <Badge variant="secondary" className="text-xs">{med.dose}</Badge>}
                    {med.frequency && <Badge variant="outline" className="text-xs">{med.frequency}</Badge>}
                    {med.route && med.route !== 'oral' && (
                      <Badge variant="outline" className="text-xs capitalize">{med.route}</Badge>
                    )}
                  </div>
                  {med.prescribed_for && (
                    <p className="text-xs text-muted-foreground">For: {med.prescribed_for}</p>
                  )}
                </div>
                <div className="text-right text-xs text-muted-foreground shrink-0 ml-4">
                  <p>Since {med.started_at}</p>
                  {med.prescriber && <p>{med.prescriber}</p>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg text-sm">
          No active medications recorded
        </div>
      )}
    </div>
  );
}
