"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";

interface UploadButtonProps {
  careRecipientId: string;
  onUploadComplete?: () => void;
}

export function UploadButton({ careRecipientId, onUploadComplete }: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setProgress("Uploading…");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", "other");

    try {
      const res = await fetch(
        `${apiUrl}/api/v1/care-recipients/${careRecipientId}/documents`,
        { method: "POST", body: formData }
      );

      if (res.ok) {
        setProgress("Uploaded successfully");
        onUploadComplete?.();
      } else {
        const error = await res.json();
        setProgress(`Error: ${error.detail || "Upload failed"}`);
      }
    } catch {
      setProgress("Upload failed. Please try again.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,image/*"
        className="hidden"
        onChange={handleFile}
      />
      <Button
        variant="outline"
        size="sm"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
      >
        {uploading ? "Uploading…" : "Upload Document"}
      </Button>
      {progress && (
        <span className="text-sm text-muted-foreground">{progress}</span>
      )}
    </div>
  );
}
