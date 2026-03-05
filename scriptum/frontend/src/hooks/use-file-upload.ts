"use client";

import { useCallback, useState } from "react";

import { api, ApiError } from "@/lib/api/client";
import type { FileUploadResponse } from "@/lib/api/types";

/* ------------------------------------------------------------------ */
/*  File validation                                                    */
/* ------------------------------------------------------------------ */

const MAX_PDF_SIZE = 50 * 1024 * 1024; // 50 MB
const MAX_TEX_SIZE = 10 * 1024 * 1024; // 10 MB

export function validateFile(file: File): string | null {
  const ext = file.name.toLowerCase().split(".").pop();

  if (ext !== "pdf" && ext !== "tex" && ext !== "bib") {
    return `"${file.name}" has an unsupported file type. Only .pdf, .tex, and .bib are accepted.`;
  }

  const maxSize = ext === "pdf" ? MAX_PDF_SIZE : MAX_TEX_SIZE;
  if (file.size > maxSize) {
    const maxMB = maxSize / (1024 * 1024);
    return `"${file.name}" exceeds the ${maxMB} MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`;
  }

  if (file.size === 0) {
    return `"${file.name}" is empty.`;
  }

  return null;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */

/**
 * Upload files to the backend and track the uploaded file IDs.
 */
export function useFileUpload() {
  const [uploadedFiles, setUploadedFiles] = useState<FileUploadResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadFiles = useCallback(async (files: File[]) => {
    setError(null);

    // Client-side validation before upload
    for (const file of files) {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    setIsUploading(true);
    try {
      const data = await api.upload<FileUploadResponse[]>("/files/upload", files);
      setUploadedFiles((prev) => [...prev, ...data]);
      return data;
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "File upload failed";
      setError(msg);
      throw err;
    } finally {
      setIsUploading(false);
    }
  }, []);

  const clearFiles = useCallback(() => {
    setUploadedFiles([]);
    setError(null);
  }, []);

  return {
    uploadedFiles,
    isUploading,
    error,
    uploadFiles,
    clearFiles,
  };
}
