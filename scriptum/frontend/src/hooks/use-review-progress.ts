"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { ReviewEvent } from "@/lib/api/types";
import { createReviewWebSocket } from "@/lib/api/websocket";

export interface StepProgress {
  id: string;
  label: string;
  status: "pending" | "active" | "complete" | "failed";
  message?: string;
  result?: Record<string, unknown>;
}

export interface AgentProgress {
  name: string;
  progress: number;
  message?: string;
}

const STEP_ORDER = [
  { id: "document_processing", label: "Document Processing" },
  { id: "desk_check", label: "Desk Check" },
  { id: "gate_check", label: "Gate Check" },
  { id: "reviewing", label: "Independent Review" },
  { id: "aggregation", label: "Review Aggregation" },
  { id: "report_generation", label: "Report Generation" },
];

/**
 * Connect to the review WebSocket and track progress in real time.
 */
export function useReviewProgress(reviewId: string | null) {
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [steps, setSteps] = useState<StepProgress[]>(() =>
    STEP_ORDER.map((s) => ({ id: s.id, label: s.label, status: "pending" as const })),
  );
  const [agents, setAgents] = useState<Record<string, AgentProgress>>({});
  const [overallProgress, setOverallProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<{ close: () => void } | null>(null);

  const handleEvent = useCallback((event: ReviewEvent) => {
    setEvents((prev) => [...prev, event]);

    // Update overall progress
    if (event.progress != null) {
      setOverallProgress(Math.round(event.progress * 100));
    }

    // Update step states
    if (event.step) {
      setSteps((prev) =>
        prev.map((step) => {
          if (step.id !== event.step) return step;

          if (event.type === "step_complete") {
            return { ...step, status: "complete", message: event.message, result: event.result };
          }
          if (event.type === "error") {
            return { ...step, status: "failed", message: event.message };
          }
          if (event.type === "progress") {
            return {
              ...step,
              status: step.status === "complete" ? "complete" : "active",
              message: event.message,
            };
          }
          return step;
        }),
      );
    }

    // Update agent progress
    if (event.agent && event.step === "reviewing") {
      setAgents((prev) => ({
        ...prev,
        [event.agent!]: {
          name: event.agent!,
          progress: event.progress != null ? Math.round(event.progress * 100) : prev[event.agent!]?.progress ?? 0,
          message: event.message ?? prev[event.agent!]?.message,
        },
      }));
    }

    // Handle completion
    if (event.type === "complete") {
      setIsComplete(true);
      setOverallProgress(100);
    }

    // Handle top-level errors
    if (event.type === "error" && !event.step) {
      setError(event.message ?? "Review failed");
    }
  }, []);

  useEffect(() => {
    if (!reviewId) return;

    const ws = createReviewWebSocket(
      reviewId,
      handleEvent,
      () => setError("WebSocket connection error"),
      () => {
        /* closed */
      },
    );
    wsRef.current = ws;

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [reviewId, handleEvent]);

  return {
    events,
    steps,
    agents,
    overallProgress,
    isComplete,
    error,
  };
}
