import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ErrorBoundary } from "@/components/error-boundary";

// A component that throws during render
function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test render error");
  }
  return <div>Child content</div>;
}

describe("ErrorBoundary", () => {
  beforeEach(() => {
    // Suppress React error boundary console.error noise in test output
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
  });

  it("renders children when no error occurs", () => {
    const { container } = render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(container.textContent).toContain("Child content");
  });

  it("renders fallback UI when a child throws", () => {
    const { container } = render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(container.textContent).toContain("Something went wrong");
    expect(container.textContent).toContain("Test render error");
  });

  it("shows a try again button in the fallback UI", () => {
    const { container } = render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );
    const btn = container.querySelector("button");
    expect(btn).not.toBeNull();
    expect(btn?.textContent).toContain("Try again");
  });
});
