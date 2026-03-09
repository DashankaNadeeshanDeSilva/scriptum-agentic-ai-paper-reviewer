/**
 * WebSocket client for streaming review progress events.
 *
 * Connects to /ws/reviews/{reviewId} and auto-reconnects on disconnect.
 */

import type { ReviewEvent } from "./types";

const _apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
const WS_BASE = _apiUrl
  ? _apiUrl.replace(/^http/, "ws")
  : `ws://${typeof window !== "undefined" ? window.location.host : "localhost:8000"}`;

const MAX_RECONNECTS = 5;
const RECONNECT_DELAY_MS = 2000;

export interface ReviewWebSocket {
  close: () => void;
}

export function createReviewWebSocket(
  reviewId: string,
  onEvent: (event: ReviewEvent) => void,
  onError?: (error: Event) => void,
  onClose?: () => void,
): ReviewWebSocket {
  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  let closed = false;

  function connect() {
    ws = new WebSocket(`${WS_BASE}/ws/reviews/${reviewId}`);

    ws.onopen = () => {
      reconnectAttempts = 0;
    };

    ws.onmessage = (msg) => {
      try {
        const event: ReviewEvent = JSON.parse(msg.data);
        onEvent(event);
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onerror = (e) => {
      onError?.(e);
    };

    ws.onclose = () => {
      if (!closed && reconnectAttempts < MAX_RECONNECTS) {
        reconnectAttempts++;
        setTimeout(connect, RECONNECT_DELAY_MS * reconnectAttempts);
      } else if (!closed) {
        // Max reconnects exceeded — notify consumer before closing
        onError?.(new Event("max_reconnects_exceeded"));
        onClose?.();
      } else {
        onClose?.();
      }
    };
  }

  connect();

  return {
    close: () => {
      closed = true;
      ws?.close();
    },
  };
}
