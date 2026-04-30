"use client";

import { useState, useEffect } from "react";
import { Check, ChevronsUpDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useDebounce } from "@/hooks/useDebounce";
import { fetchWithAuth } from "@/lib/api";
import { useAuth } from "@clerk/nextjs";

export interface MedicationSuggestion {
  rxcui: string;
  name: string;
  score: number;
}

interface MedicationAutocompleteProps {
  onSelect: (medication: MedicationSuggestion | null) => void;
  value?: string;
  disabled?: boolean;
}

export function MedicationAutocomplete({
  onSelect,
  value = "",
  disabled = false,
}: MedicationAutocompleteProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);
  const [suggestions, setSuggestions] = useState<MedicationSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedName, setSelectedName] = useState(value);

  const { getToken } = useAuth();

  useEffect(() => {
    async function fetchSuggestions() {
      if (!debouncedSearch || debouncedSearch.length < 2) {
        setSuggestions([]);
        return;
      }
      
      setLoading(true);
      try {
        const token = await getToken();
        if (!token) return;
        
        const data = await fetchWithAuth(`/medications/search?q=${encodeURIComponent(debouncedSearch)}`, token);
        setSuggestions(data || []);
      } catch (error) {
        console.error("Failed to fetch medications", error);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }

    fetchSuggestions();
  }, [debouncedSearch, getToken]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between"
          disabled={disabled}
        >
          {selectedName || "Search for a medication..."}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput 
            placeholder="Type medication name..." 
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            {loading ? (
              <div className="py-6 text-center text-sm text-gray-500">Searching RxNav...</div>
            ) : suggestions.length === 0 && search.length >= 2 ? (
              <CommandEmpty>No medications found.</CommandEmpty>
            ) : suggestions.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-500">Start typing to search</div>
            ) : (
              <CommandGroup>
                {suggestions.map((med) => (
                  <CommandItem
                    key={med.rxcui}
                    value={med.rxcui}
                    onSelect={() => {
                      setSelectedName(med.name);
                      onSelect(med);
                      setOpen(false);
                      setSearch("");
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selectedName === med.name ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {med.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
