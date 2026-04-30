import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type Condition = { name: string; icd10_code?: string | null; diagnosed_date?: string | null };
type Allergy = { substance: string; reaction?: string | null; severity?: string | null };

type ProfileSummaryProps = {
  displayName: string;
  dateOfBirth: string;
  sexAtBirth: string;
  conditions: Condition[];
  allergies: Allergy[];
  baselineNotes?: string | null;
  primaryProviderName?: string | null;
  primaryProviderPhone?: string | null;
  primaryProviderEmail?: string | null;
  emergencyContactName?: string | null;
  emergencyContactPhone?: string | null;
  consentBasis: string;
};

function calcAge(dob: string): number {
  const birthDate = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const m = today.getMonth() - birthDate.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) age--;
  return age;
}

const severityColor: Record<string, string> = {
  mild: 'bg-yellow-100 text-yellow-800',
  moderate: 'bg-orange-100 text-orange-800',
  severe: 'bg-red-100 text-red-800',
};

export function ProfileSummary({
  displayName,
  dateOfBirth,
  sexAtBirth,
  conditions,
  allergies,
  baselineNotes,
  primaryProviderName,
  primaryProviderPhone,
  primaryProviderEmail,
  emergencyContactName,
  emergencyContactPhone,
  consentBasis,
}: ProfileSummaryProps) {
  const age = calcAge(dateOfBirth);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Demographics</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Date of Birth</p>
            <p className="font-medium">{dateOfBirth} ({age} years old)</p>
          </div>
          <div>
            <p className="text-muted-foreground">Sex at Birth</p>
            <p className="font-medium capitalize">{sexAtBirth}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Consent Basis</p>
            <p className="font-medium capitalize">{consentBasis.replace(/_/g, ' ')}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Conditions</CardTitle>
          </CardHeader>
          <CardContent>
            {conditions.length > 0 ? (
              <ul className="space-y-2">
                {conditions.map((c, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                    <span className="font-medium">{c.name}</span>
                    {c.icd10_code && (
                      <Badge variant="outline" className="text-xs">{c.icd10_code}</Badge>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No conditions recorded</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Allergies</CardTitle>
          </CardHeader>
          <CardContent>
            {allergies.length > 0 ? (
              <ul className="space-y-2">
                {allergies.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0 mt-1" />
                    <div>
                      <span className="font-medium">{a.substance}</span>
                      {a.reaction && <span className="text-muted-foreground"> — {a.reaction}</span>}
                      {a.severity && (
                        <span
                          className={`ml-2 inline-block px-1.5 py-0.5 rounded text-xs font-medium ${severityColor[a.severity.toLowerCase()] ?? 'bg-gray-100 text-gray-700'}`}
                        >
                          {a.severity}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No allergies recorded</p>
            )}
          </CardContent>
        </Card>
      </div>

      {(primaryProviderName || emergencyContactName) && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Contacts</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            {primaryProviderName && (
              <div>
                <p className="text-muted-foreground font-medium mb-1">Primary Care Provider</p>
                <p className="font-medium">{primaryProviderName}</p>
                {primaryProviderPhone && <p className="text-muted-foreground">{primaryProviderPhone}</p>}
                {primaryProviderEmail && <p className="text-muted-foreground">{primaryProviderEmail}</p>}
              </div>
            )}
            {emergencyContactName && (
              <div>
                <p className="text-muted-foreground font-medium mb-1">Emergency Contact</p>
                <p className="font-medium">{emergencyContactName}</p>
                {emergencyContactPhone && <p className="text-muted-foreground">{emergencyContactPhone}</p>}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {baselineNotes && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Baseline Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground whitespace-pre-line">{baselineNotes}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
