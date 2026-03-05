"use client";

import { useCallback, useState } from "react";

import { api, ApiError } from "@/lib/api/client";
import type { FileUploadResponse } from "@/lib/api/types";

/**
 * Upload files to the backend and track the uploaded file IDs.
 */
export function useFileUpload() {
  const [uploadedFiles, setUploadedFiles] = useState<FileUploadResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadFiles = useCallback(async (files: File[]) => {
    setIsUploading(true);
    setError(null);
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
