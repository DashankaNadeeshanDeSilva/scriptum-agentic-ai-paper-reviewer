"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";
import type { ChatMessage, ChatEvent } from "@/lib/api/types";

const _apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
const WS_BASE = _apiUrl
  ? _apiUrl.replace(/^http/, "ws")
  : `ws://${typeof window !== "undefined" ? window.location.host : "localhost:8000"}`;

interface UseReviewChatReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  sendMessage: (content: string) => void;
}

export function useReviewChat(reviewId: string): UseReviewChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamedContentRef = useRef("");

  // Load chat history on mount
  useEffect(() => {
    if (!reviewId?.trim()) return;

    api
      .get<ChatMessage[]>(`/reviews/${reviewId}/chat/history`)
      .then(setMessages)
      .catch(() => setError("Failed to load chat history"));
  }, [reviewId]);

  // Connect WebSocket on mount
  useEffect(() => {
    if (!reviewId?.trim()) return;

    const ws = new WebSocket(`${WS_BASE}/ws/reviews/${reviewId}/chat`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data: ChatEvent = JSON.parse(event.data);

        if (data.type === "token" && data.content) {
          streamedContentRef.current += data.content;
          // Update the last (assistant) message with accumulated content
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: streamedContentRef.current,
              };
            }
            return updated;
          });
        } else if (data.type === "complete") {
          setIsStreaming(false);
          streamedContentRef.current = "";
        } else if (data.type === "error") {
          setError(data.message ?? "An error occurred");
          setIsStreaming(false);
          streamedContentRef.current = "";
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onerror = () => {
      setError("Chat connection error");
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [reviewId]);

  const sendMessage = useCallback(
    (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      setError(null);

      // Add user message to state immediately
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };
      // Add placeholder assistant message for streaming
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      streamedContentRef.current = "";

      wsRef.current.send(JSON.stringify({ content: trimmed }));
    },
    [],
  );

  return { messages, isStreaming, error, sendMessage };
}
