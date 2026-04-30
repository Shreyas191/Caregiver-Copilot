"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { MedicationAutocomplete, MedicationSuggestion } from "./MedicationAutocomplete";
import { fetchWithAuth } from "@/lib/api";
import { useAuth } from "@clerk/nextjs";

const medicationFormSchema = z.object({
  display_name: z.string().min(1, "Medication name is required"),
  rxnorm_code: z.string().optional(),
  rxnorm_name: z.string().optional(),
  dose: z.string().optional(),
  frequency: z.string().optional(),
  route: z.string().optional(),
  started_at: z.string().min(1, "Start date is required"),
  prescribed_for: z.string().optional(),
  prescriber: z.string().optional(),
});

type MedicationFormValues = z.infer<typeof medicationFormSchema>;

interface MedicationFormProps {
  careRecipientId: string;
  onSuccess: () => void;
}

export function MedicationForm({ careRecipientId, onSuccess }: MedicationFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { getToken } = useAuth();

  const form = useForm<MedicationFormValues>({
    resolver: zodResolver(medicationFormSchema),
    defaultValues: {
      display_name: "",
      rxnorm_code: "",
      rxnorm_name: "",
      dose: "",
      frequency: "",
      route: "oral",
      started_at: new Date().toISOString().split("T")[0],
      prescribed_for: "",
      prescriber: "",
    },
  });

  async function onSubmit(data: MedicationFormValues) {
    setSubmitting(true);
    setError(null);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      
      await fetchWithAuth(`/care-recipients/${careRecipientId}/medications`, token, {
        method: "POST",
        body: JSON.stringify(data),
      });
      onSuccess();
    } catch (err: any) {
      setError(err.message || "Failed to add medication.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {error && <div className="text-red-500 text-sm p-3 bg-red-50 rounded-md border border-red-200">{error}</div>}

        <FormField
          control={form.control}
          name="display_name"
          render={({ field }) => (
            <FormItem className="flex flex-col">
              <FormLabel>Medication Name *</FormLabel>
              <MedicationAutocomplete
                onSelect={(med: MedicationSuggestion | null) => {
                  if (med) {
                    field.onChange(med.name);
                    form.setValue("rxnorm_code", med.rxcui);
                    form.setValue("rxnorm_name", med.name);
                  } else {
                    field.onChange("");
                    form.setValue("rxnorm_code", "");
                    form.setValue("rxnorm_name", "");
                  }
                }}
                value={field.value}
                disabled={submitting}
              />
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="dose"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dose</FormLabel>
                <FormControl>
                  <Input placeholder="e.g., 10mg" disabled={submitting} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="frequency"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Frequency</FormLabel>
                <FormControl>
                  <Input placeholder="e.g., twice daily" disabled={submitting} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="route"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Route</FormLabel>
                <FormControl>
                  <Input placeholder="e.g., oral" disabled={submitting} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="started_at"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Start Date *</FormLabel>
                <FormControl>
                  <Input type="date" disabled={submitting} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="prescriber"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Prescriber</FormLabel>
                <FormControl>
                  <Input placeholder="Dr. Smith" disabled={submitting} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="prescribed_for"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Reason for Medication</FormLabel>
                <FormControl>
                  <Input placeholder="e.g., Blood Pressure" disabled={submitting} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Saving..." : "Save Medication"}
        </Button>
      </form>
    </Form>
  );
}
