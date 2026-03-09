import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1;
  static instances: MockWebSocket[] = [];
  static autoOpen = true;

  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  onclose: (() => void) | null = null;
  readyState = MockWebSocket.OPEN;
  closeCalled = false;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    if (MockWebSocket.autoOpen) {
      // Simulate async open
      setTimeout(() => this.onopen?.(), 0);
    }
  }

  close() {
    this.closeCalled = true;
    this.readyState = 3;
    this.onclose?.();
  }

  send(_data: string) {}

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateError() {
    this.onerror?.(new Event("error"));
  }
}

vi.stubGlobal("WebSocket", MockWebSocket);

beforeEach(() => {
  MockWebSocket.instances = [];
  MockWebSocket.autoOpen = true;
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("createReviewWebSocket", () => {
  it("connects to the correct URL", async () => {
    const { createReviewWebSocket } = await import("@/lib/api/websocket");

    createReviewWebSocket("review-123", () => {});

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain("/ws/reviews/review-123");
  });

  it("calls onEvent when a message is received", async () => {
    const { createReviewWebSocket } = await import("@/lib/api/websocket");
    const onEvent = vi.fn();

    createReviewWebSocket("r1", onEvent);
    const ws = MockWebSocket.instances[0];

    ws.simulateMessage({ type: "progress", step: "reviewing", progress: 50 });

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({ type: "progress", step: "reviewing" }),
    );
  });

  it("attempts to reconnect on unexpected close", async () => {
    const { createReviewWebSocket } = await import("@/lib/api/websocket");

    createReviewWebSocket("r2", () => {});
    const ws = MockWebSocket.instances[0];

    // Simulate unexpected close (not user-initiated)
    ws.onclose?.();
    vi.advanceTimersByTime(3000);

    // Should have created a new WebSocket instance for reconnection
    expect(MockWebSocket.instances.length).toBeGreaterThan(1);
  });

  it("calls onError with max_reconnects_exceeded after max retries", async () => {
    const { createReviewWebSocket } = await import("@/lib/api/websocket");
    const onError = vi.fn();
    const onClose = vi.fn();

    // First WS opens normally
    createReviewWebSocket("r3", () => {}, onError, onClose);
    vi.advanceTimersByTime(1); // fire initial onopen

    // Disable auto-open for reconnection attempts (simulating connection failure)
    MockWebSocket.autoOpen = false;

    // Simulate 5 reconnection failures (MAX_RECONNECTS = 5)
    for (let i = 0; i < 5; i++) {
      const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      ws.onclose?.();
      // Advance past the reconnect delay to trigger the setTimeout
      vi.advanceTimersByTime(20000);
    }
    // The 6th close should trigger max_reconnects_exceeded
    const lastWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
    lastWs.onclose?.();

    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ type: "max_reconnects_exceeded" }),
    );
  });
});
