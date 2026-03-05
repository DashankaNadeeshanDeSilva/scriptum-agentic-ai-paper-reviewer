"use client";

import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api/client";
import type {
  SettingsResponse,
  SettingsUpdateRequest,
  TestConnectionRequest,
  TestConnectionResponse,
} from "@/lib/api/types";

/**
 * Load, save, and test settings via the backend API.
 */
export function useSettings() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const fetchSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<SettingsResponse>("/settings");
      setSettings(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load settings");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const saveSettings = useCallback(async (payload: SettingsUpdateRequest) => {
    setIsSaving(true);
    setError(null);
    try {
      const data = await api.put<SettingsResponse>("/settings", payload);
      setSettings(data);
      return data;
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "Failed to save settings";
      setError(msg);
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  const testConnection = useCallback(async (req: TestConnectionRequest) => {
    try {
      return await api.post<TestConnectionResponse>("/settings/test-connection", req);
    } catch (err) {
      if (err instanceof ApiError) {
        return { success: false, latency_ms: null, model_info: null, error: err.detail };
      }
      return { success: false, latency_ms: null, model_info: null, error: "Connection test failed" };
    }
  }, []);

  const fetchOllamaModels = useCallback(async () => {
    try {
      const data = await api.get<{ models: string[]; error?: string }>("/settings/ollama/models");
      return data.models ?? [];
    } catch {
      return [];
    }
  }, []);

  return {
    settings,
    isLoading,
    error,
    isSaving,
    fetchSettings,
    saveSettings,
    testConnection,
    fetchOllamaModels,
  };
}
