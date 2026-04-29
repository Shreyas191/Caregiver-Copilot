'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Trash2, Plus } from 'lucide-react';

import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

const formSchema = z.object({
  display_name: z.string().min(1, 'Name is required'),
  date_of_birth: z.string().min(1, 'Date of birth is required'),
  sex_at_birth: z.enum(['male', 'female', 'intersex', 'unknown']),
  conditions: z.array(
    z.object({
      name: z.string().min(1, 'Condition name is required'),
      icd10_code: z.string().optional(),
      diagnosed_date: z.string().optional(),
    })
  ),
  allergies: z.array(
    z.object({
      substance: z.string().min(1, 'Substance is required'),
      reaction: z.string().optional(),
      severity: z.string().optional(),
    })
  ),
  primary_provider_name: z.string().optional(),
  primary_provider_email: z.string().email('Invalid email').optional().or(z.literal('')),
  primary_provider_phone: z.string().optional(),
  emergency_contact_name: z.string().optional(),
  emergency_contact_phone: z.string().optional(),
  consent_basis: z.enum([
    'power_of_attorney',
    'healthcare_proxy',
    'parental_responsibility',
    'informal_arrangement',
    'self',
  ]),
  baseline_notes: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

export default function OnboardingForm() {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { getToken } = useAuth();
  const router = useRouter();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      display_name: '',
      date_of_birth: '',
      sex_at_birth: 'unknown',
      conditions: [],
      allergies: [],
      primary_provider_name: '',
      primary_provider_email: '',
      primary_provider_phone: '',
      emergency_contact_name: '',
      emergency_contact_phone: '',
      consent_basis: 'self',
      baseline_notes: '',
    },
  });

  const { fields: conditionFields, append: appendCondition, remove: removeCondition } = useFieldArray({
    control: form.control,
    name: 'conditions',
  });

  const { fields: allergyFields, append: appendAllergy, remove: removeAllergy } = useFieldArray({
    control: form.control,
    name: 'allergies',
  });

  const nextStep = async () => {
    let fieldsToValidate: any[] = [];
    if (step === 1) fieldsToValidate = ['display_name', 'date_of_birth', 'sex_at_birth'];
    if (step === 2) fieldsToValidate = ['conditions'];
    if (step === 3) fieldsToValidate = ['allergies'];
    if (step === 4) fieldsToValidate = [
      'primary_provider_name',
      'primary_provider_email',
      'primary_provider_phone',
      'emergency_contact_name',
      'emergency_contact_phone',
    ];

    const isValid = await form.trigger(fieldsToValidate);
    if (isValid) {
      setStep((s) => s + 1);
    }
  };

  const prevStep = () => setStep((s) => s - 1);

  const onSubmit = async (data: FormValues) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const token = await getToken();
      
      // Clean up empty strings to undefined to match schema Optionals
      const payload = {
        ...data,
        primary_provider_name: data.primary_provider_name || undefined,
        primary_provider_email: data.primary_provider_email || undefined,
        primary_provider_phone: data.primary_provider_phone || undefined,
        emergency_contact_name: data.emergency_contact_name || undefined,
        emergency_contact_phone: data.emergency_contact_phone || undefined,
        baseline_notes: data.baseline_notes || undefined,
      };

      const response = await api.careRecipients.create(token!, payload);
      router.push(`/care-recipients/${response.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create care recipient');
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto border-gray-800 bg-gray-950/50 backdrop-blur">
      <CardHeader>
        <CardTitle className="text-2xl font-semibold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
          Add Care Recipient
        </CardTitle>
        <CardDescription>Step {step} of 5</CardDescription>
        <div className="w-full h-1 bg-gray-800 rounded-full mt-4">
          <div 
            className="h-1 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-300"
            style={{ width: `${(step / 5) * 100}%` }}
          />
        </div>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* STEP 1 */}
            <div className={step === 1 ? 'block animate-in fade-in slide-in-from-right-4 duration-300' : 'hidden'}>
              <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="display_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Full Name *</FormLabel>
                      <FormControl>
                        <Input placeholder="John Doe" className="bg-gray-900 border-gray-800" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="date_of_birth"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Date of Birth *</FormLabel>
                      <FormControl>
                        <Input type="date" className="bg-gray-900 border-gray-800" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="sex_at_birth"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sex at Birth *</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-gray-900 border-gray-800">
                            <SelectValue placeholder="Select sex at birth" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="male">Male</SelectItem>
                          <SelectItem value="female">Female</SelectItem>
                          <SelectItem value="intersex">Intersex</SelectItem>
                          <SelectItem value="unknown">Unknown</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* STEP 2 */}
            <div className={step === 2 ? 'block animate-in fade-in slide-in-from-right-4 duration-300' : 'hidden'}>
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-medium text-gray-200 mb-1">Medical Conditions</h3>
                  <p className="text-sm text-gray-400 mb-4">Add known medical conditions, chronic illnesses, or recent diagnoses.</p>
                </div>
                {conditionFields.map((field, index) => (
                  <div key={field.id} className="flex gap-4 items-end border border-gray-800 bg-gray-900/50 p-4 rounded-md">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1">
                      <FormField
                        control={form.control}
                        name={`conditions.${index}.name`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">Condition Name *</FormLabel>
                            <FormControl>
                              <Input placeholder="e.g., Type 2 Diabetes" className="bg-gray-950 border-gray-800" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name={`conditions.${index}.icd10_code`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">ICD-10 (Optional)</FormLabel>
                            <FormControl>
                              <Input placeholder="E11.9" className="bg-gray-950 border-gray-800" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name={`conditions.${index}.diagnosed_date`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">Diagnosed (Optional)</FormLabel>
                            <FormControl>
                              <Input placeholder="YYYY or YYYY-MM" className="bg-gray-950 border-gray-800" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                    <Button type="button" variant="ghost" size="icon" onClick={() => removeCondition(index)} className="hover:bg-red-500/20 hover:text-red-400 text-gray-500">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="border-gray-800 bg-transparent hover:bg-gray-800 text-blue-400 border-dashed w-full py-6"
                  onClick={() => appendCondition({ name: '', icd10_code: '', diagnosed_date: '' })}
                >
                  <Plus className="h-4 w-4 mr-2" /> Add Condition
                </Button>
              </div>
            </div>

            {/* STEP 3 */}
            <div className={step === 3 ? 'block animate-in fade-in slide-in-from-right-4 duration-300' : 'hidden'}>
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-medium text-gray-200 mb-1">Allergies</h3>
                  <p className="text-sm text-gray-400 mb-4">Add known allergies to medications, food, or environment.</p>
                </div>
                {allergyFields.map((field, index) => (
                  <div key={field.id} className="flex gap-4 items-end border border-gray-800 bg-gray-900/50 p-4 rounded-md">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1">
                      <FormField
                        control={form.control}
                        name={`allergies.${index}.substance`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">Substance *</FormLabel>
                            <FormControl>
                              <Input placeholder="e.g., Penicillin" className="bg-gray-950 border-gray-800" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name={`allergies.${index}.reaction`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">Reaction</FormLabel>
                            <FormControl>
                              <Input placeholder="e.g., Hives" className="bg-gray-950 border-gray-800" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name={`allergies.${index}.severity`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">Severity</FormLabel>
                            <FormControl>
                              <Input placeholder="e.g., Severe" className="bg-gray-950 border-gray-800" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                    <Button type="button" variant="ghost" size="icon" onClick={() => removeAllergy(index)} className="hover:bg-red-500/20 hover:text-red-400 text-gray-500">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="border-gray-800 bg-transparent hover:bg-gray-800 text-blue-400 border-dashed w-full py-6"
                  onClick={() => appendAllergy({ substance: '', reaction: '', severity: '' })}
                >
                  <Plus className="h-4 w-4 mr-2" /> Add Allergy
                </Button>
              </div>
            </div>

            {/* STEP 4 */}
            <div className={step === 4 ? 'block animate-in fade-in slide-in-from-right-4 duration-300' : 'hidden'}>
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-200">Primary Care Provider</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="primary_provider_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Provider Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Dr. Smith" className="bg-gray-900 border-gray-800" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="primary_provider_phone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Phone Number</FormLabel>
                        <FormControl>
                          <Input placeholder="(555) 123-4567" className="bg-gray-900 border-gray-800" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="primary_provider_email"
                    render={({ field }) => (
                      <FormItem className="md:col-span-2">
                        <FormLabel>Email Address</FormLabel>
                        <FormControl>
                          <Input placeholder="dr.smith@clinic.com" className="bg-gray-900 border-gray-800" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <h3 className="text-lg font-medium text-gray-200 mt-6 pt-6 border-t border-gray-800">Emergency Contact</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="emergency_contact_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Contact Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Jane Doe" className="bg-gray-900 border-gray-800" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="emergency_contact_phone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Phone Number</FormLabel>
                        <FormControl>
                          <Input placeholder="(555) 987-6543" className="bg-gray-900 border-gray-800" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            </div>

            {/* STEP 5 */}
            <div className={step === 5 ? 'block animate-in fade-in slide-in-from-right-4 duration-300' : 'hidden'}>
              <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="consent_basis"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Consent Basis *</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-gray-900 border-gray-800">
                            <SelectValue placeholder="Select consent basis" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="self">Self (I am the recipient)</SelectItem>
                          <SelectItem value="power_of_attorney">Power of Attorney</SelectItem>
                          <SelectItem value="healthcare_proxy">Healthcare Proxy</SelectItem>
                          <SelectItem value="parental_responsibility">Parental Responsibility</SelectItem>
                          <SelectItem value="informal_arrangement">Informal Arrangement</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="baseline_notes"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Baseline Notes</FormLabel>
                      <FormControl>
                        <Textarea 
                          placeholder="Any general notes about the recipient's baseline health, mobility, or communication preferences..." 
                          className="min-h-32 bg-gray-900 border-gray-800 resize-none"
                          {...field} 
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {error && (
                  <div className="p-3 bg-red-900/30 border border-red-500/50 text-red-200 rounded-md text-sm">
                    {error}
                  </div>
                )}
              </div>
            </div>
          </form>
        </Form>
      </CardContent>
      <CardFooter className="flex justify-between border-t border-gray-800 pt-6">
        <Button
          variant="outline"
          className="border-gray-700 bg-transparent hover:bg-gray-800"
          onClick={prevStep}
          disabled={step === 1 || isSubmitting}
        >
          Previous
        </Button>
        {step < 5 ? (
          <Button onClick={nextStep} className="bg-blue-600 hover:bg-blue-500 text-white">Next</Button>
        ) : (
          <Button onClick={form.handleSubmit(onSubmit)} disabled={isSubmitting} className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0 shadow-[0_0_15px_rgba(59,130,246,0.5)]">
            {isSubmitting ? 'Saving...' : 'Complete Profile'}
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
